import time
import datetime as dt
from pathlib import Path

import akshare as ak
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots


# =========================
# 页面基础设置
# =========================
st.set_page_config(
    page_title="基金/ETF专业实时分析看板",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =========================
# 缓存目录
# =========================
CACHE_DIR = Path(".etf_cache")
CACHE_DIR.mkdir(exist_ok=True)

SPOT_CACHE_FILE = CACHE_DIR / "etf_spot_cache.csv"


def history_cache_file(symbol: str) -> Path:
    safe_symbol = str(symbol).replace("/", "_").replace("\\", "_")
    return CACHE_DIR / f"hist_{safe_symbol}.csv"


def save_df_cache(df: pd.DataFrame, file_path: Path):
    try:
        if df is not None and not df.empty:
            df.to_csv(file_path, index=False, encoding="utf-8-sig")
    except Exception:
        pass


def load_df_cache(file_path: Path) -> pd.DataFrame:
    try:
        if file_path.exists():
            return pd.read_csv(file_path)
    except Exception:
        pass
    return pd.DataFrame()


# =========================
# 页面样式
# =========================
CUSTOM_CSS = """
<style>
.block-container {
    padding-top: 1.2rem;
    padding-bottom: 2rem;
}

.main-title {
    font-size: 34px;
    font-weight: 800;
    letter-spacing: 0.5px;
    margin-bottom: 0.2rem;
}

.sub-title {
    font-size: 15px;
    color: #8A8F98;
    margin-bottom: 1.2rem;
}

.signal-card {
    padding: 18px 20px;
    border-radius: 18px;
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.92), rgba(15, 23, 42, 0.92));
    border: 1px solid rgba(148, 163, 184, 0.22);
    box-shadow: 0 10px 28px rgba(15, 23, 42, 0.16);
    margin-bottom: 12px;
}

.signal-title {
    font-size: 17px;
    font-weight: 700;
    color: #F8FAFC;
    margin-bottom: 8px;
}

.signal-text {
    font-size: 14px;
    line-height: 1.75;
    color: #CBD5E1;
}

.good {
    color: #22c55e;
    font-weight: 700;
}

.warn {
    color: #f59e0b;
    font-weight: 700;
}

.bad {
    color: #ef4444;
    font-weight: 700;
}

.neutral {
    color: #94a3b8;
    font-weight: 700;
}

div[data-testid="stMetricValue"] {
    font-size: 24px;
    font-weight: 800;
}

div[data-testid="stMetricLabel"] {
    font-size: 14px;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# =========================
# 默认 ETF 池
# =========================
DEFAULT_ETFS = {
    "沪深300ETF": "510300",
    "创业板ETF": "159915",
    "科创50ETF": "588000",
    "半导体ETF": "512480",
    "芯片ETF": "159995",
    "证券ETF": "512880",
    "医药ETF": "512010",
    "新能源车ETF": "515030",
    "光伏ETF": "515790",
    "有色金属ETF": "512400",
    "军工ETF": "512660",
    "恒生科技ETF": "513130",
    "纳指ETF": "513100",
    "黄金ETF": "518880",
}


# =========================
# 基础工具函数
# =========================
def safe_num(x):
    try:
        if pd.isna(x):
            return np.nan
        if isinstance(x, str):
            x = x.replace("%", "").replace(",", "").strip()
        return float(x)
    except Exception:
        return np.nan


def format_money(x):
    x = safe_num(x)
    if pd.isna(x):
        return "暂无"
    if abs(x) >= 1e8:
        return f"{x / 1e8:.2f} 亿"
    if abs(x) >= 1e4:
        return f"{x / 1e4:.2f} 万"
    return f"{x:.2f}"


def format_pct(x):
    x = safe_num(x)
    if pd.isna(x):
        return "暂无"
    return f"{x:.2f}%"


def get_sec_id(symbol: str) -> str:
    """
    东方财富 secid：
    上海：1.xxxxxx
    深圳：0.xxxxxx
    """
    symbol = str(symbol).strip()
    if symbol.startswith(("5", "6", "9")):
        return f"1.{symbol}"
    return f"0.{symbol}"


def request_json(url, params=None, timeout=12):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json,text/plain,*/*",
        "Referer": "https://quote.eastmoney.com/"
    }

    last_error = None

    for _ in range(3):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=timeout)
            r.raise_for_status()
            return r.json(), None
        except Exception as e:
            last_error = e
            time.sleep(1.5)

    return None, last_error


# =========================
# 备用数据源：东方财富直连
# =========================
def fetch_history_from_eastmoney(symbol: str, days: int = 240) -> pd.DataFrame:
    """
    直接请求东方财富日 K 数据，作为 AkShare 失败后的备用源。
    """
    secid = get_sec_id(symbol)

    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "secid": secid,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",
        "fqt": "0",
        "beg": "20000101",
        "end": dt.datetime.now().strftime("%Y%m%d"),
        "lmt": str(max(days * 2, 600))
    }

    data, error = request_json(url, params=params)

    if not data:
        raise RuntimeError(f"东方财富历史行情接口失败：{error}")

    klines = data.get("data", {}).get("klines", [])

    if not klines:
        raise RuntimeError("东方财富历史行情接口返回为空")

    rows = []

    for item in klines:
        parts = item.split(",")
        if len(parts) < 7:
            continue

        rows.append({
            "日期": parts[0],
            "开盘": parts[1],
            "收盘": parts[2],
            "最高": parts[3],
            "最低": parts[4],
            "成交量": parts[5],
            "成交额": parts[6],
            "振幅": parts[7] if len(parts) > 7 else np.nan,
            "涨跌幅": parts[8] if len(parts) > 8 else np.nan,
            "涨跌额": parts[9] if len(parts) > 9 else np.nan,
            "换手率": parts[10] if len(parts) > 10 else np.nan,
        })

    df = pd.DataFrame(rows)

    if df.empty:
        raise RuntimeError("东方财富历史行情解析后为空")

    df["日期"] = pd.to_datetime(df["日期"])

    numeric_cols = ["开盘", "收盘", "最高", "最低", "成交量", "成交额", "涨跌幅"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.sort_values("日期").reset_index(drop=True)
    return df.tail(days).reset_index(drop=True)


def fetch_spot_from_eastmoney(codes) -> pd.DataFrame:
    """
    直接请求东方财富实时行情，作为 AkShare 失败后的备用源。
    """
    secids = ",".join([get_sec_id(code) for code in codes])

    url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
    params = {
        "fltt": "2",
        "secids": secids,
        "fields": "f12,f14,f2,f3,f4,f5,f6"
    }

    data, error = request_json(url, params=params)

    if not data:
        raise RuntimeError(f"东方财富实时行情接口失败：{error}")

    diff = data.get("data", {}).get("diff", [])

    if not diff:
        raise RuntimeError("东方财富实时行情接口返回为空")

    rows = []
    for item in diff:
        rows.append({
            "代码": str(item.get("f12", "")),
            "名称": item.get("f14", ""),
            "最新价": item.get("f2", np.nan),
            "涨跌幅": item.get("f3", np.nan),
            "涨跌额": item.get("f4", np.nan),
            "成交量": item.get("f5", np.nan),
            "成交额": item.get("f6", np.nan),
        })

    df = pd.DataFrame(rows)

    for col in ["最新价", "涨跌幅", "涨跌额", "成交量", "成交额"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


# =========================
# AkShare 数据源
# =========================
def fetch_history_from_akshare(symbol: str, days: int = 240) -> pd.DataFrame:
    end_date = dt.datetime.now().strftime("%Y%m%d")
    start_date = (dt.datetime.now() - dt.timedelta(days=days * 2)).strftime("%Y%m%d")

    df = ak.fund_etf_hist_em(
        symbol=str(symbol),
        period="daily",
        start_date=start_date,
        end_date=end_date,
        adjust=""
    )

    if df is None or df.empty:
        raise RuntimeError("AkShare 历史行情返回为空")

    df["日期"] = pd.to_datetime(df["日期"])
    df = df.sort_values("日期").reset_index(drop=True)

    numeric_cols = ["开盘", "收盘", "最高", "最低", "成交量", "成交额", "涨跌幅"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df.tail(days).reset_index(drop=True)


def fetch_spot_from_akshare() -> pd.DataFrame:
    df = ak.fund_etf_spot_em()
    if df is None or df.empty:
        raise RuntimeError("AkShare 实时行情返回为空")
    return df


def normalize_spot_columns(df):
    if df is None or df.empty:
        return pd.DataFrame()

    mapping = {}
    for col in df.columns:
        if col in ["代码", "基金代码"]:
            mapping[col] = "代码"
        elif col in ["名称", "基金简称", "基金名称"]:
            mapping[col] = "名称"
        elif col in ["最新价", "最新净值", "单位净值"]:
            mapping[col] = "最新价"
        elif col in ["涨跌幅", "日增长率"]:
            mapping[col] = "涨跌幅"
        elif col in ["涨跌额"]:
            mapping[col] = "涨跌额"
        elif col in ["成交额"]:
            mapping[col] = "成交额"
        elif col in ["成交量"]:
            mapping[col] = "成交量"

    return df.rename(columns=mapping)


# =========================
# 稳定行情获取
# =========================
@st.cache_data(ttl=45, show_spinner=False)
def get_etf_spot_stable():
    codes = list(DEFAULT_ETFS.values())
    errors = []

    # 第一层：AkShare
    for _ in range(2):
        try:
            df = fetch_spot_from_akshare()
            df = normalize_spot_columns(df)
            save_df_cache(df, SPOT_CACHE_FILE)
            return df, "AkShare实时数据", ""
        except Exception as e:
            errors.append(f"AkShare实时行情失败：{e}")
            time.sleep(1.5)

    # 第二层：东方财富直连
    for _ in range(2):
        try:
            df = fetch_spot_from_eastmoney(codes)
            save_df_cache(df, SPOT_CACHE_FILE)
            return df, "东方财富实时数据", ""
        except Exception as e:
            errors.append(f"东方财富实时行情失败：{e}")
            time.sleep(1.5)

    # 第三层：缓存
    cached = load_df_cache(SPOT_CACHE_FILE)
    if not cached.empty:
        return cached, "缓存实时行情", "；".join(errors)

    return pd.DataFrame(), "实时行情不可用", "；".join(errors)


@st.cache_data(ttl=180, show_spinner=False)
def get_etf_history_stable(symbol: str, days: int = 240):
    cache_file = history_cache_file(symbol)
    errors = []

    # 第一层：AkShare
    for _ in range(2):
        try:
            df = fetch_history_from_akshare(symbol, days)
            save_df_cache(df, cache_file)
            df = add_indicators(df)
            return df, "AkShare历史行情", ""
        except Exception as e:
            errors.append(f"AkShare历史行情失败：{e}")
            time.sleep(1.5)

    # 第二层：东方财富直连
    for _ in range(2):
        try:
            df = fetch_history_from_eastmoney(symbol, days)
            save_df_cache(df, cache_file)
            df = add_indicators(df)
            return df, "东方财富历史行情", ""
        except Exception as e:
            errors.append(f"东方财富历史行情失败：{e}")
            time.sleep(1.5)

    # 第三层：缓存
    cached = load_df_cache(cache_file)
    if not cached.empty:
        try:
            cached["日期"] = pd.to_datetime(cached["日期"])
            numeric_cols = ["开盘", "收盘", "最高", "最低", "成交量", "成交额", "涨跌幅"]
            for col in numeric_cols:
                if col in cached.columns:
                    cached[col] = pd.to_numeric(cached[col], errors="coerce")
            cached = add_indicators(cached)
            return cached.tail(days).reset_index(drop=True), "缓存历史行情", "；".join(errors)
        except Exception as e:
            errors.append(f"缓存读取失败：{e}")

    return pd.DataFrame(), "历史行情不可用", "；".join(errors)


# =========================
# 指标计算
# =========================
def add_indicators(df):
    df = df.copy()

    df["MA5"] = df["收盘"].rolling(5).mean()
    df["MA10"] = df["收盘"].rolling(10).mean()
    df["MA20"] = df["收盘"].rolling(20).mean()
    df["MA60"] = df["收盘"].rolling(60).mean()

    df["日涨跌幅"] = df["收盘"].pct_change() * 100

    if "成交额" in df.columns:
        df["成交额_MA5"] = df["成交额"].rolling(5).mean()
        df["成交额_MA20"] = df["成交额"].rolling(20).mean()
        df["量能倍率"] = df["成交额"] / df["成交额_MA20"]
    else:
        df["成交额"] = np.nan
        df["成交额_MA5"] = np.nan
        df["成交额_MA20"] = np.nan
        df["量能倍率"] = np.nan

    if "成交量" in df.columns:
        volume = df["成交量"].fillna(0)
    else:
        volume = df["成交额"].fillna(0)

    price_diff = df["收盘"].diff()
    direction = np.where(price_diff > 0, 1, np.where(price_diff < 0, -1, 0))
    df["OBV"] = (direction * volume).cumsum()
    df["OBV_MA10"] = df["OBV"].rolling(10).mean()

    df["资金行为强度"] = df["日涨跌幅"] * df["成交额"] / 1e8

    df["均线偏离_MA5"] = (df["收盘"] / df["MA5"] - 1) * 100
    df["均线偏离_MA20"] = (df["收盘"] / df["MA20"] - 1) * 100
    df["均线偏离_MA60"] = (df["收盘"] / df["MA60"] - 1) * 100

    df["资金信号"] = df.apply(classify_money_signal, axis=1)

    return df


def classify_money_signal(row):
    pct = row.get("日涨跌幅", np.nan)
    vol_ratio = row.get("量能倍率", np.nan)
    obv = row.get("OBV", np.nan)
    obv_ma = row.get("OBV_MA10", np.nan)

    if pd.isna(pct) or pd.isna(vol_ratio):
        return "数据不足"

    obv_strong = pd.notna(obv) and pd.notna(obv_ma) and obv > obv_ma
    obv_weak = pd.notna(obv) and pd.notna(obv_ma) and obv < obv_ma

    if pct > 1.2 and vol_ratio >= 1.25 and obv_strong:
        return "强流入"
    elif pct > 0.3 and vol_ratio >= 1.05:
        return "温和流入"
    elif pct < -1.2 and vol_ratio >= 1.25 and obv_weak:
        return "强撤出"
    elif pct < -0.3 and vol_ratio >= 1.05:
        return "温和撤出"
    elif abs(pct) < 0.3 and vol_ratio >= 1.3:
        return "分歧放量"
    elif vol_ratio < 0.75:
        return "缩量观望"
    else:
        return "中性"


# =========================
# 综合判断
# =========================
def compute_summary(hist):
    if hist is None or hist.empty or len(hist) < 60:
        return {
            "trend_score": 0,
            "trend_label": "数据不足",
            "risk_label": "无法判断",
            "money_label": "无法判断",
            "action_label": "观察",
            "comment": "历史数据不足，暂无法形成稳定判断。"
        }

    latest = hist.iloc[-1]
    close = latest["收盘"]

    trend_score = 0

    if pd.notna(latest["MA5"]) and close > latest["MA5"]:
        trend_score += 1
    if pd.notna(latest["MA20"]) and close > latest["MA20"]:
        trend_score += 1
    if pd.notna(latest["MA60"]) and close > latest["MA60"]:
        trend_score += 1
    if pd.notna(latest["MA5"]) and pd.notna(latest["MA20"]) and latest["MA5"] > latest["MA20"]:
        trend_score += 1
    if pd.notna(latest["MA20"]) and pd.notna(latest["MA60"]) and latest["MA20"] > latest["MA60"]:
        trend_score += 1

    if trend_score >= 4:
        trend_label = "趋势偏强"
    elif trend_score == 3:
        trend_label = "趋势修复"
    elif trend_score == 2:
        trend_label = "震荡偏弱"
    else:
        trend_label = "趋势偏弱"

    bias20 = latest["均线偏离_MA20"]
    if pd.isna(bias20):
        risk_label = "风险不明"
    elif bias20 > 8:
        risk_label = "短期过热"
    elif bias20 > 4:
        risk_label = "略偏高"
    elif bias20 < -8:
        risk_label = "深度回调"
    elif bias20 < -4:
        risk_label = "回调区"
    else:
        risk_label = "正常波动"

    money_label = latest["资金信号"]

    if trend_label in ["趋势偏强", "趋势修复"] and money_label in ["强流入", "温和流入"]:
        action_label = "持有观察 / 不宜追高"
    elif trend_label == "趋势偏弱" and money_label in ["强撤出", "温和撤出"]:
        action_label = "谨慎观望"
    elif risk_label in ["深度回调", "回调区"] and money_label not in ["强撤出"]:
        action_label = "适合小额定投观察"
    elif risk_label == "短期过热":
        action_label = "避免一次性追高"
    else:
        action_label = "震荡观察"

    comment = generate_commentary(latest, trend_label, risk_label, money_label, action_label)

    return {
        "trend_score": trend_score,
        "trend_label": trend_label,
        "risk_label": risk_label,
        "money_label": money_label,
        "action_label": action_label,
        "comment": comment
    }


def generate_commentary(latest, trend_label, risk_label, money_label, action_label):
    close = latest["收盘"]
    lines = []

    if pd.notna(latest["MA5"]):
        lines.append("价格位于5日均线上方，说明超短期动能尚可。" if close > latest["MA5"] else "价格低于5日均线，说明超短期动能偏弱。")

    if pd.notna(latest["MA20"]):
        lines.append("价格站上20日均线，短期结构有修复迹象。" if close > latest["MA20"] else "价格仍低于20日均线，短期趋势尚未完全扭转。")

    if pd.notna(latest["MA60"]):
        lines.append("价格处于60日均线上方，中期结构相对稳定。" if close > latest["MA60"] else "价格低于60日均线，中期趋势仍需谨慎。")

    vol_ratio = latest["量能倍率"]
    if pd.notna(vol_ratio):
        if vol_ratio >= 1.5:
            lines.append(f"当前成交额约为20日均值的 {vol_ratio:.2f} 倍，属于明显放量。")
        elif vol_ratio >= 1.1:
            lines.append(f"当前成交额约为20日均值的 {vol_ratio:.2f} 倍，量能有所放大。")
        elif vol_ratio < 0.75:
            lines.append(f"当前成交额约为20日均值的 {vol_ratio:.2f} 倍，市场参与度偏低。")
        else:
            lines.append(f"当前成交额约为20日均值的 {vol_ratio:.2f} 倍，量能处于正常区间。")

    if money_label in ["强流入", "温和流入"]:
        lines.append("资金行为代理指标显示偏流入，短线情绪有所改善。")
    elif money_label in ["强撤出", "温和撤出"]:
        lines.append("资金行为代理指标显示偏撤出，短线需要警惕继续回落。")
    elif money_label == "分歧放量":
        lines.append("当前属于放量分歧状态，说明多空力量博弈较强，不宜只看单日涨跌。")
    elif money_label == "缩量观望":
        lines.append("当前缩量明显，说明资金参与意愿不足，更适合等待方向选择。")

    lines.append(f"综合判断：{trend_label}，风险状态为{risk_label}，当前策略更偏向“{action_label}”。")

    return "\n\n".join(lines)


# =========================
# 绘图
# =========================
def draw_professional_chart(hist, title):
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        row_heights=[0.58, 0.22, 0.20],
        subplot_titles=("价格/净值走势与均线结构", "成交额与量能变化", "资金行为强度代理指标")
    )

    fig.add_trace(go.Scatter(x=hist["日期"], y=hist["收盘"], mode="lines", name="收盘价/净值", line=dict(width=2.8, color="#E5E7EB")), row=1, col=1)
    fig.add_trace(go.Scatter(x=hist["日期"], y=hist["MA5"], mode="lines", name="MA5", line=dict(width=1.5, color="#38BDF8")), row=1, col=1)
    fig.add_trace(go.Scatter(x=hist["日期"], y=hist["MA20"], mode="lines", name="MA20", line=dict(width=1.8, color="#FBBF24")), row=1, col=1)
    fig.add_trace(go.Scatter(x=hist["日期"], y=hist["MA60"], mode="lines", name="MA60", line=dict(width=1.8, color="#A78BFA")), row=1, col=1)

    amount_colors = np.where(hist["日涨跌幅"] >= 0, "#22C55E", "#EF4444")
    fig.add_trace(go.Bar(x=hist["日期"], y=hist["成交额"] / 1e8, name="成交额/亿", marker_color=amount_colors, opacity=0.72), row=2, col=1)
    fig.add_trace(go.Scatter(x=hist["日期"], y=hist["成交额_MA20"] / 1e8, mode="lines", name="成交额MA20/亿", line=dict(width=1.8, color="#FBBF24")), row=2, col=1)

    money_colors = np.where(hist["资金行为强度"] >= 0, "#22C55E", "#EF4444")
    fig.add_trace(go.Bar(x=hist["日期"], y=hist["资金行为强度"], name="资金行为强度", marker_color=money_colors, opacity=0.78), row=3, col=1)
    fig.add_hline(y=0, line_width=1, line_dash="dot", line_color="#94A3B8", row=3, col=1)

    fig.update_layout(
        title=dict(text=title, font=dict(size=22, color="#F8FAFC")),
        height=820,
        hovermode="x unified",
        plot_bgcolor="#0F172A",
        paper_bgcolor="#0F172A",
        font=dict(color="#CBD5E1"),
        legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="right", x=1),
        margin=dict(l=25, r=25, t=85, b=35)
    )

    fig.update_xaxes(showgrid=True, gridcolor="rgba(148, 163, 184, 0.14)", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(148, 163, 184, 0.14)", zeroline=False)

    fig.update_yaxes(title_text="价格/净值", row=1, col=1)
    fig.update_yaxes(title_text="成交额/亿", row=2, col=1)
    fig.update_yaxes(title_text="强度", row=3, col=1)

    return fig


def build_market_table(spot_df, watch_codes):
    df = normalize_spot_columns(spot_df).copy()

    if df.empty or "代码" not in df.columns:
        return pd.DataFrame()

    df["代码"] = df["代码"].astype(str)

    if watch_codes:
        df = df[df["代码"].isin([str(x) for x in watch_codes])]

    for col in ["涨跌幅", "成交额", "最新价", "涨跌额"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    keep_cols = [c for c in ["代码", "名称", "最新价", "涨跌幅", "涨跌额", "成交额"] if c in df.columns]
    df = df[keep_cols].copy()

    if "成交额" in df.columns:
        df["成交额显示"] = df["成交额"].apply(format_money)

    return df


# =========================
# 页面标题
# =========================
st.markdown('<div class="main-title">📊 基金 / ETF 专业实时分析看板</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">趋势结构 · 5/20/60日均线 · 成交额异动 · 资金行为代理 · 自动策略解读</div>', unsafe_allow_html=True)


# =========================
# 侧边栏
# =========================
with st.sidebar:
    st.header("🎛️ 看板设置")

    selected_name = st.selectbox("选择关注基金/ETF", list(DEFAULT_ETFS.keys()), index=3)
    selected_code = st.text_input("基金/ETF代码", value=DEFAULT_ETFS[selected_name])

    days = st.slider("历史分析周期", min_value=80, max_value=520, value=240, step=20)

    st.divider()

    auto_refresh = st.checkbox("自动刷新", value=False)
    refresh_seconds = st.slider("刷新间隔/秒", min_value=30, max_value=600, value=120, step=30)

    st.divider()

    if st.button("清除页面缓存并刷新"):
        st.cache_data.clear()
        st.rerun()

    st.caption(
        "说明：公开数据接口无法等同于券商Level-2逐笔主力数据。"
        "本看板使用成交额、涨跌幅、OBV和均线结构构建资金行为代理信号。"
    )


# =========================
# 主程序
# =========================
try:
    with st.spinner("正在获取行情数据，请稍候..."):
        spot_df, spot_source, spot_error = get_etf_spot_stable()
        hist, hist_source, hist_error = get_etf_history_stable(selected_code, days=days)

    if "缓存" in spot_source or "缓存" in hist_source:
        st.warning("当前部分数据来自最近一次成功缓存，公开行情接口可能暂时不稳定。")

    if spot_source == "实时行情不可用":
        st.warning(f"实时行情暂时不可用。错误信息：{spot_error}")

    if hist.empty:
        st.error("历史行情数据暂时不可用。请稍后刷新，或更换 ETF 代码。")
        if hist_error:
            st.caption(f"错误信息：{hist_error}")
        st.stop()

    spot_norm = normalize_spot_columns(spot_df)

    summary = compute_summary(hist)
    latest = hist.iloc[-1]

    selected_spot = pd.DataFrame()
    if not spot_norm.empty and "代码" in spot_norm.columns:
        spot_norm["代码"] = spot_norm["代码"].astype(str)
        selected_spot = spot_norm[spot_norm["代码"] == str(selected_code)]

    if not selected_spot.empty:
        spot_row = selected_spot.iloc[0]
        real_name = spot_row.get("名称", selected_name)
        latest_price = spot_row.get("最新价", latest["收盘"])
        today_pct = spot_row.get("涨跌幅", latest.get("日涨跌幅", np.nan))
        today_amount = spot_row.get("成交额", latest.get("成交额", np.nan))
    else:
        real_name = selected_name
        latest_price = latest["收盘"]
        today_pct = latest.get("日涨跌幅", np.nan)
        today_amount = latest.get("成交额", np.nan)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("基金/ETF", real_name)
    c2.metric("当前价/净值", f"{safe_num(latest_price):.3f}" if pd.notna(safe_num(latest_price)) else "暂无")
    c3.metric("今日涨跌幅", format_pct(today_pct))
    c4.metric("成交额", format_money(today_amount))
    c5.metric("资金信号", summary["money_label"])

    c6, c7, c8, c9, c10 = st.columns(5)
    c6.metric("趋势评分", f"{summary['trend_score']} / 5")
    c7.metric("趋势状态", summary["trend_label"])
    c8.metric("风险状态", summary["risk_label"])
    c9.metric("量能倍率", f"{latest['量能倍率']:.2f}x" if pd.notna(latest["量能倍率"]) else "暂无")
    c10.metric("策略提示", summary["action_label"])

    st.caption(
        f"数据状态：实时行情 = {spot_source}；历史行情 = {hist_source}；"
        f"历史数据最后日期 = {latest['日期'].strftime('%Y-%m-%d') if pd.notna(latest['日期']) else '未知'}"
    )

    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs(["📈 专业分析图", "🧠 自动解读", "🔥 实时行情池", "📋 信号明细"])

    with tab1:
        fig = draw_professional_chart(hist, title=f"{real_name}（{selected_code}）专业趋势与资金行为分析")
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        left, right = st.columns([1.2, 1])

        with left:
            st.markdown(
                f"""
                <div class="signal-card">
                    <div class="signal-title">🧠 自动分析结论</div>
                    <div class="signal-text">{summary["comment"].replace(chr(10), "<br>")}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown(
                """
                <div class="signal-card">
                    <div class="signal-title">📌 信号解释</div>
                    <div class="signal-text">
                    <span class="good">强流入</span>：上涨幅度较大，同时成交额明显放大，OBV强于短期均值。<br>
                    <span class="bad">强撤出</span>：下跌幅度较大，同时成交额明显放大，OBV弱于短期均值。<br>
                    <span class="warn">分歧放量</span>：涨跌不大但成交额明显放大，说明多空分歧增强。<br>
                    <span class="neutral">缩量观望</span>：成交额低于近期均值，说明资金参与度不足。
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with right:
            st.subheader("关键位置")
            key_df = pd.DataFrame({
                "指标": [
                    "收盘价/净值", "MA5", "MA20", "MA60",
                    "相对MA5偏离", "相对MA20偏离", "相对MA60偏离",
                    "成交额", "成交额MA20", "量能倍率", "资金行为强度"
                ],
                "数值": [
                    f"{latest['收盘']:.4f}",
                    f"{latest['MA5']:.4f}" if pd.notna(latest["MA5"]) else "暂无",
                    f"{latest['MA20']:.4f}" if pd.notna(latest["MA20"]) else "暂无",
                    f"{latest['MA60']:.4f}" if pd.notna(latest["MA60"]) else "暂无",
                    format_pct(latest["均线偏离_MA5"]),
                    format_pct(latest["均线偏离_MA20"]),
                    format_pct(latest["均线偏离_MA60"]),
                    format_money(latest["成交额"]),
                    format_money(latest["成交额_MA20"]),
                    f"{latest['量能倍率']:.2f}x" if pd.notna(latest["量能倍率"]) else "暂无",
                    f"{latest['资金行为强度']:.2f}" if pd.notna(latest["资金行为强度"]) else "暂无"
                ]
            })
            st.dataframe(key_df, use_container_width=True, hide_index=True)

    with tab3:
        market_table = build_market_table(spot_df, list(DEFAULT_ETFS.values()))

        if market_table.empty:
            st.warning("暂未获取到实时行情表。若公开接口不稳定，请稍后刷新。")
        else:
            if "涨跌幅" in market_table.columns:
                market_table = market_table.sort_values("涨跌幅", ascending=False)

            st.subheader("关注ETF实时强弱排名")
            st.dataframe(market_table, use_container_width=True, height=480, hide_index=True)

            if "涨跌幅" in market_table.columns and len(market_table) >= 2:
                best = market_table.iloc[0]
                worst = market_table.iloc[-1]
                st.info(
                    f"当前关注池中，最强为 **{best.get('名称', '')}**，涨跌幅 {safe_num(best.get('涨跌幅', np.nan)):.2f}%；"
                    f"最弱为 **{worst.get('名称', '')}**，涨跌幅 {safe_num(worst.get('涨跌幅', np.nan)):.2f}%。"
                )

    with tab4:
        signal_df = hist[[
            "日期", "收盘", "日涨跌幅", "成交额", "量能倍率",
            "资金行为强度", "资金信号",
            "均线偏离_MA5", "均线偏离_MA20", "均线偏离_MA60"
        ]].copy()

        signal_df["日期"] = pd.to_datetime(signal_df["日期"]).dt.strftime("%Y-%m-%d")
        signal_df["成交额"] = signal_df["成交额"].apply(format_money)
        signal_df["日涨跌幅"] = signal_df["日涨跌幅"].map(lambda x: f"{x:.2f}%" if pd.notna(x) else "暂无")
        signal_df["量能倍率"] = signal_df["量能倍率"].map(lambda x: f"{x:.2f}x" if pd.notna(x) else "暂无")
        signal_df["资金行为强度"] = signal_df["资金行为强度"].map(lambda x: f"{x:.2f}" if pd.notna(x) else "暂无")
        signal_df["均线偏离_MA5"] = signal_df["均线偏离_MA5"].map(format_pct)
        signal_df["均线偏离_MA20"] = signal_df["均线偏离_MA20"].map(format_pct)
        signal_df["均线偏离_MA60"] = signal_df["均线偏离_MA60"].map(format_pct)

        st.subheader("历史资金行为信号明细")
        st.dataframe(signal_df.sort_values("日期", ascending=False), use_container_width=True, height=520, hide_index=True)

except Exception as e:
    st.error("看板运行失败，但这不是安装包问题，而是网页后台运行异常。")
    st.exception(e)


if auto_refresh:
    time.sleep(refresh_seconds)
    st.rerun()
