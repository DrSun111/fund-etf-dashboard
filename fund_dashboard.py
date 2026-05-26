import datetime as dt
import importlib.util
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import streamlit as st
from PIL import Image
import plotly.graph_objects as go
from plotly.subplots import make_subplots


st.set_page_config(
    page_title="基金/ETF实时分析看板",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


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


CUSTOM_CSS = """
<style>
:root {
    --bg: #0b1020;
    --surface: rgba(18, 25, 43, 0.92);
    --surface-soft: rgba(25, 35, 58, 0.86);
    --line: rgba(149, 164, 190, 0.18);
    --text: #eef3fb;
    --muted: #9eabc0;
    --accent: #60a5fa;
    --good: #34d399;
    --warn: #fbbf24;
    --bad: #fb7185;
}

html, body, [data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at 10% 0%, rgba(37, 99, 235, 0.15), transparent 28%),
        linear-gradient(180deg, #0b1020 0%, #0d1222 45%, #090d18 100%) !important;
    color: var(--text) !important;
}

[data-testid="stHeader"] {
    background: rgba(11, 16, 32, 0.78) !important;
    border-bottom: 1px solid rgba(149, 164, 190, 0.12);
}

[data-testid="stSidebar"] {
    background: #0a0f1d !important;
    border-right: 1px solid rgba(149, 164, 190, 0.14);
}

[data-testid="stSidebar"] * {
    color: var(--text) !important;
}

.block-container {
    max-width: 1500px;
    padding-top: 1.2rem;
    padding-bottom: 2.2rem;
}

.app-title {
    font-size: 32px;
    line-height: 1.2;
    font-weight: 760;
    letter-spacing: 0;
    color: #ffffff !important;
    margin-bottom: 0.25rem;
}

.app-subtitle {
    color: var(--muted) !important;
    font-size: 14px;
    margin-bottom: 1.05rem;
}

.section-shell {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 16px 18px;
    margin-bottom: 14px;
}

.section-title {
    font-size: 17px;
    font-weight: 720;
    color: #ffffff !important;
    margin-bottom: 4px;
}

.section-note {
    font-size: 13px;
    line-height: 1.65;
    color: var(--muted) !important;
}

.status-ok, .status-warn, .status-bad {
    border-radius: 8px;
    padding: 12px 14px;
    font-weight: 680;
    margin: 10px 0 16px;
    border: 1px solid var(--line);
}
.status-ok { background: rgba(16, 76, 69, 0.72); color: #d9fff4 !important; }
.status-warn { background: rgba(84, 63, 16, 0.72); color: #fff2ca !important; }
.status-bad { background: rgba(85, 33, 47, 0.72); color: #ffe0e7 !important; }

.signal-card {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 16px 18px;
    margin-bottom: 12px;
}

.signal-card strong {
    color: #ffffff !important;
}

.signal-text {
    color: #e7edf8 !important;
    line-height: 1.75;
    font-size: 14px;
}

.good { color: var(--good) !important; font-weight: 720; }
.warn { color: var(--warn) !important; font-weight: 720; }
.bad { color: var(--bad) !important; font-weight: 720; }
.neutral { color: #bfccdd !important; font-weight: 720; }

h1, h2, h3, h4, h5, h6, p, span, label {
    color: var(--text) !important;
}

div[data-testid="stMetric"] {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 14px 16px !important;
    min-height: 98px;
}

div[data-testid="stMetricLabel"] {
    color: var(--muted) !important;
    font-weight: 620;
}

div[data-testid="stMetricValue"] {
    color: #ffffff !important;
    font-weight: 760;
}

[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] [data-baseweb="input"] > div,
[data-testid="stSidebar"] textarea,
[data-testid="stSidebar"] input {
    background: #111827 !important;
    color: #f8fafc !important;
    border: 1px solid rgba(149, 164, 190, 0.26) !important;
    border-radius: 8px !important;
}

div[role="listbox"] {
    background: #111827 !important;
    border: 1px solid rgba(149, 164, 190, 0.26) !important;
}

button[data-baseweb="tab"] {
    color: #cbd5e1 !important;
    font-weight: 680 !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #ffffff !important;
}

.stButton button {
    background: #172033 !important;
    color: #f8fafc !important;
    border: 1px solid rgba(149, 164, 190, 0.24) !important;
    border-radius: 8px !important;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


ETF_MODULES = {
    "宽基指数": {
        "沪深300ETF": "510300", "上证50ETF": "510050", "中证500ETF": "510500", "中证1000ETF": "512100",
        "创业板ETF": "159915", "科创50ETF": "588000", "双创50ETF": "159781", "红利ETF": "510880",
    },
    "科技与高端制造": {
        "半导体ETF": "512480", "芯片ETF": "159995", "人工智能ETF": "515980", "云计算ETF": "516510",
        "软件ETF": "515230", "通信ETF": "515880", "5GETF": "515050", "机器人ETF": "562500",
        "智能车ETF": "159888", "军工ETF": "512660",
    },
    "电气电力与新能源": {
        "新能源车ETF": "515030", "光伏ETF": "515790", "电池ETF": "561910", "储能电池ETF": "159566",
        "绿色电力ETF": "562960", "电力ETF": "561560", "新能源ETF": "516160", "碳中和ETF": "159790",
        "央企能源ETF": "562850",
    },
    "资源周期与大宗商品": {
        "有色金属ETF": "512400", "稀土ETF": "516780", "钢铁ETF": "515210", "煤炭ETF": "515220",
        "能源ETF": "159930", "化工ETF": "516020", "石油基金": "162719", "黄金ETF": "518880", "豆粕ETF": "159985",
    },
    "金融地产": {
        "证券ETF": "512880", "银行ETF": "512800", "保险证券ETF": "515630", "地产ETF": "512200", "金融ETF": "510230",
    },
    "消费医药农业": {
        "消费ETF": "159928", "酒ETF": "512690", "食品饮料ETF": "515170", "医药ETF": "512010",
        "医疗ETF": "512170", "创新药ETF": "159992", "养殖ETF": "159865", "农业ETF": "159825",
    },
    "港股与海外": {
        "恒生科技ETF": "513130", "恒生互联网ETF": "513330", "港股通互联网ETF": "159792", "恒生ETF": "159920",
        "纳指ETF": "513100", "标普500ETF": "513500", "德国ETF": "513030", "日经ETF": "513520",
    },
}

DEFAULT_ETFS = {name: code for items in ETF_MODULES.values() for name, code in items.items()}
CODE_TO_NAME = {code: name for name, code in DEFAULT_ETFS.items()}


def safe_num(x):
    try:
        if pd.isna(x):
            return np.nan
        if isinstance(x, str):
            x = x.replace("%", "").replace(",", "").replace("，", "").strip()
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
    symbol = str(symbol).strip()
    return f"1.{symbol}" if symbol.startswith(("5", "6", "9")) else f"0.{symbol}"


def request_json_fast(url: str, params: dict, timeout: int = 6):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
        "Accept": "application/json,text/plain,*/*",
        "Referer": "https://quote.eastmoney.com/",
    }
    response = requests.get(url, params=params, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.json()


def fetch_spot_from_eastmoney(codes) -> pd.DataFrame:
    unique_codes = []
    for code in codes:
        code = str(code).strip()
        if re.fullmatch(r"\d{6}", code) and code not in unique_codes:
            unique_codes.append(code)
    if not unique_codes:
        return pd.DataFrame()

    url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
    params = {
        "fltt": "2",
        "secids": ",".join(get_sec_id(code) for code in unique_codes),
        "fields": "f12,f14,f2,f3,f4,f5,f6",
    }
    data = request_json_fast(url, params=params, timeout=6)
    diff = data.get("data", {}).get("diff", [])
    if not diff:
        raise RuntimeError("东方财富实时行情接口返回为空")

    df = pd.DataFrame([{
        "代码": str(item.get("f12", "")),
        "名称": item.get("f14", ""),
        "最新价": item.get("f2", np.nan),
        "涨跌幅": item.get("f3", np.nan),
        "涨跌额": item.get("f4", np.nan),
        "成交量": item.get("f5", np.nan),
        "成交额": item.get("f6", np.nan),
    } for item in diff])
    for col in ["最新价", "涨跌幅", "涨跌额", "成交量", "成交额"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def fetch_history_from_eastmoney(symbol: str, days: int = 240) -> pd.DataFrame:
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "secid": get_sec_id(symbol),
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",
        "fqt": "0",
        "beg": "20000101",
        "end": dt.datetime.now().strftime("%Y%m%d"),
        "lmt": str(max(days * 2, 600)),
    }
    data = request_json_fast(url, params=params, timeout=8)
    klines = data.get("data", {}).get("klines", [])
    if not klines:
        raise RuntimeError("东方财富历史行情接口返回为空")

    rows = []
    for line in klines:
        parts = line.split(",")
        if len(parts) >= 7:
            rows.append({
                "日期": parts[0], "开盘": parts[1], "收盘": parts[2], "最高": parts[3], "最低": parts[4],
                "成交量": parts[5], "成交额": parts[6], "涨跌幅": parts[8] if len(parts) > 8 else np.nan,
            })
    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("东方财富历史行情解析后为空")
    df["日期"] = pd.to_datetime(df["日期"])
    for col in ["开盘", "收盘", "最高", "最低", "成交量", "成交额", "涨跌幅"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_values("日期").tail(days).reset_index(drop=True)


def get_base_price(symbol: str) -> float:
    base_price_map = {
        "510300": 3.8, "510050": 2.7, "510500": 5.8, "512100": 2.3, "159915": 1.8, "588000": 0.9,
        "159781": 0.8, "510880": 3.0, "512480": 0.8, "159995": 0.9, "515980": 0.9, "516510": 0.8,
        "515230": 0.7, "515880": 1.1, "515050": 1.0, "562500": 1.0, "159888": 1.0, "512660": 1.0,
        "515030": 1.1, "515790": 0.75, "561910": 0.8, "159566": 1.0, "562960": 1.0, "561560": 1.0,
        "516160": 0.8, "159790": 0.8, "562850": 1.0, "512400": 1.2, "516780": 1.0, "515210": 1.0,
        "515220": 1.3, "159930": 1.0, "516020": 0.75, "162719": 1.0, "518880": 5.2, "159985": 1.0,
        "512880": 0.9, "512800": 1.1, "515630": 0.9, "512200": 0.8, "510230": 1.0, "159928": 0.9,
        "512690": 0.8, "515170": 0.8, "512010": 0.45, "512170": 0.4, "159992": 0.6, "159865": 0.8,
        "159825": 0.8, "513130": 0.55, "513330": 0.5, "159792": 0.6, "159920": 1.0, "513100": 1.6,
        "513500": 1.6, "513030": 1.0, "513520": 1.0,
    }
    return base_price_map.get(str(symbol), 1.0)


def generate_fallback_history(symbol: str, days: int = 240) -> pd.DataFrame:
    rng = np.random.default_rng(abs(hash(str(symbol))) % (2**32))
    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=days)
    base_price = get_base_price(symbol)
    returns = rng.normal(loc=0.0002, scale=0.013, size=len(dates))
    trend = np.linspace(-0.02, 0.04, len(dates))
    prices = base_price * np.cumprod(1 + returns) * (1 + trend)
    open_prices = prices * (1 + rng.normal(0, 0.004, len(dates)))
    high_prices = np.maximum(open_prices, prices) * (1 + rng.uniform(0.002, 0.016, len(dates)))
    low_prices = np.minimum(open_prices, prices) * (1 - rng.uniform(0.002, 0.016, len(dates)))
    amount = rng.uniform(1.2e8, 16e8, len(dates))
    volume = amount / np.maximum(prices, 0.01) / 100
    df = pd.DataFrame({
        "日期": dates, "开盘": open_prices, "收盘": prices, "最高": high_prices, "最低": low_prices,
        "成交量": volume, "成交额": amount,
    })
    df["涨跌幅"] = df["收盘"].pct_change().fillna(0) * 100
    return df


def generate_fallback_spot(codes=None) -> pd.DataFrame:
    rng = np.random.default_rng(int(pd.Timestamp.today().strftime("%Y%m%d")))
    code_set = {str(x) for x in codes or DEFAULT_ETFS.values()}
    rows = []
    for name, code in DEFAULT_ETFS.items():
        if str(code) not in code_set:
            continue
        base = get_base_price(code)
        pct = rng.normal(0, 1.1)
        latest = base * (1 + pct / 100)
        rows.append({
            "代码": code, "名称": name, "最新价": round(latest, 3), "涨跌幅": round(pct, 2),
            "涨跌额": round(latest - base, 3), "成交额": rng.uniform(1e8, 20e8),
        })
    return pd.DataFrame(rows)


def add_indicators(df):
    df = df.copy()
    df["MA5"] = df["收盘"].rolling(5).mean()
    df["MA10"] = df["收盘"].rolling(10).mean()
    df["MA20"] = df["收盘"].rolling(20).mean()
    df["MA60"] = df["收盘"].rolling(60).mean()
    df["日涨跌幅"] = df["收盘"].pct_change() * 100
    df["成交额"] = df["成交额"] if "成交额" in df.columns else np.nan
    df["成交额_MA5"] = df["成交额"].rolling(5).mean()
    df["成交额_MA20"] = df["成交额"].rolling(20).mean()
    df["量能倍率"] = df["成交额"] / df["成交额_MA20"]
    volume = df["成交量"].fillna(0) if "成交量" in df.columns else df["成交额"].fillna(0)
    direction = np.sign(df["收盘"].diff()).fillna(0)
    df["OBV"] = (direction * volume).cumsum()
    df["OBV_MA10"] = df["OBV"].rolling(10).mean()
    df["资金行为强度"] = df["日涨跌幅"] * df["成交额"] / 1e8
    for ma in ["MA5", "MA20", "MA60"]:
        df[f"均线偏离_{ma}"] = (df["收盘"] / df[ma] - 1) * 100
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
    if pct > 0.3 and vol_ratio >= 1.05:
        return "温和流入"
    if pct < -1.2 and vol_ratio >= 1.25 and obv_weak:
        return "强撤出"
    if pct < -0.3 and vol_ratio >= 1.05:
        return "温和撤出"
    if abs(pct) < 0.3 and vol_ratio >= 1.3:
        return "分歧放量"
    if vol_ratio < 0.75:
        return "缩量观望"
    return "中性"


@st.cache_data(ttl=30, show_spinner=False)
def get_etf_spot(codes_tuple):
    codes = list(codes_tuple)
    try:
        df = fetch_spot_from_eastmoney(codes)
        save_df_cache(df, SPOT_CACHE_FILE)
        return df, "东方财富实时行情"
    except Exception as e:
        cached = load_df_cache(SPOT_CACHE_FILE)
        if not cached.empty and "代码" in cached.columns:
            cached["代码"] = cached["代码"].astype(str)
            cached = cached[cached["代码"].isin([str(x) for x in codes])]
            if not cached.empty:
                return cached, f"缓存实时行情，东方财富错误：{e}"
        return generate_fallback_spot(codes), f"备用展示数据，东方财富错误：{e}"


@st.cache_data(ttl=120, show_spinner=False)
def get_etf_history(symbol: str, days: int = 240):
    cache_file = history_cache_file(symbol)
    try:
        df = fetch_history_from_eastmoney(symbol, days)
        save_df_cache(df, cache_file)
        return add_indicators(df).tail(days).reset_index(drop=True), "东方财富历史行情"
    except Exception as e:
        cached = load_df_cache(cache_file)
        if not cached.empty:
            cached["日期"] = pd.to_datetime(cached["日期"])
            for col in ["开盘", "收盘", "最高", "最低", "成交量", "成交额", "涨跌幅"]:
                if col in cached.columns:
                    cached[col] = pd.to_numeric(cached[col], errors="coerce")
            return add_indicators(cached).tail(days).reset_index(drop=True), f"缓存历史行情，东方财富错误：{e}"
        return add_indicators(generate_fallback_history(symbol, days)).tail(days).reset_index(drop=True), f"备用展示数据，东方财富错误：{e}"


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
        elif col in ["涨跌额", "成交额", "成交量"]:
            mapping[col] = col
    return df.rename(columns=mapping)


def compute_summary(hist):
    if hist is None or hist.empty or len(hist) < 60:
        return {"trend_score": 0, "trend_label": "数据不足", "risk_label": "无法判断", "money_label": "无法判断", "action_label": "观察", "comment": "历史数据不足，暂无法形成稳定判断。"}
    latest = hist.iloc[-1]
    close = latest["收盘"]
    trend_score = 0
    trend_score += int(pd.notna(latest["MA5"]) and close > latest["MA5"])
    trend_score += int(pd.notna(latest["MA20"]) and close > latest["MA20"])
    trend_score += int(pd.notna(latest["MA60"]) and close > latest["MA60"])
    trend_score += int(pd.notna(latest["MA5"]) and pd.notna(latest["MA20"]) and latest["MA5"] > latest["MA20"])
    trend_score += int(pd.notna(latest["MA20"]) and pd.notna(latest["MA60"]) and latest["MA20"] > latest["MA60"])
    trend_label = "趋势偏强" if trend_score >= 4 else "趋势修复" if trend_score == 3 else "震荡偏弱" if trend_score == 2 else "趋势偏弱"

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

    money_signal = latest["资金信号"]
    if trend_label in ["趋势偏强", "趋势修复"] and money_signal in ["强流入", "温和流入"]:
        action_label = "持有观察 / 不宜追高"
    elif trend_label == "趋势偏弱" and money_signal in ["强撤出", "温和撤出"]:
        action_label = "谨慎观望"
    elif risk_label in ["深度回调", "回调区"] and money_signal != "强撤出":
        action_label = "适合小额定投观察"
    elif risk_label == "短期过热":
        action_label = "避免一次性追高"
    else:
        action_label = "震荡观察"
    return {
        "trend_score": trend_score,
        "trend_label": trend_label,
        "risk_label": risk_label,
        "money_label": money_signal,
        "action_label": action_label,
        "comment": generate_commentary(latest, trend_label, risk_label, money_signal, action_label),
    }


def generate_commentary(latest, trend_label, risk_label, money_label, action_label):
    close = latest["收盘"]
    lines = []
    if pd.notna(latest["MA5"]):
        lines.append("价格位于5日均线上方，短线动能尚可。" if close > latest["MA5"] else "价格低于5日均线，短线动能偏弱。")
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
        lines.append("资金行为代理指标偏流入，短线情绪有所改善。")
    elif money_label in ["强撤出", "温和撤出"]:
        lines.append("资金行为代理指标偏撤出，短线需要警惕继续回落。")
    elif money_label == "分歧放量":
        lines.append("当前属于放量分歧状态，多空力量博弈较强。")
    elif money_label == "缩量观望":
        lines.append("当前缩量明显，资金参与意愿不足。")
    lines.append(f"综合判断：{trend_label}，风险状态为{risk_label}，当前策略更偏向“{action_label}”。")
    return "\n\n".join(lines)


def draw_professional_chart(hist):
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.075,
        row_heights=[0.58, 0.22, 0.20],
        subplot_titles=("价格/净值走势与均线结构", "成交额与量能变化", "资金行为强度代理指标"),
    )
    fig.add_trace(go.Scatter(x=hist["日期"], y=hist["收盘"], mode="lines", name="收盘价/净值", line=dict(width=2.8, color="#f8fafc")), row=1, col=1)
    fig.add_trace(go.Scatter(x=hist["日期"], y=hist["MA5"], mode="lines", name="MA5", line=dict(width=1.6, color="#38bdf8")), row=1, col=1)
    fig.add_trace(go.Scatter(x=hist["日期"], y=hist["MA20"], mode="lines", name="MA20", line=dict(width=1.8, color="#fbbf24")), row=1, col=1)
    fig.add_trace(go.Scatter(x=hist["日期"], y=hist["MA60"], mode="lines", name="MA60", line=dict(width=1.8, color="#a78bfa")), row=1, col=1)

    marker_specs = [("强流入", "#22c55e", "triangle-up", 10), ("强撤出", "#ef4444", "triangle-down", 10), ("温和流入", "#86efac", "circle", 7), ("温和撤出", "#fca5a5", "circle", 7)]
    for signal, color, symbol, size in marker_specs:
        points = hist[hist["资金信号"] == signal]
        if not points.empty:
            fig.add_trace(go.Scatter(x=points["日期"], y=points["收盘"], mode="markers", name=signal, marker=dict(size=size, color=color, symbol=symbol)), row=1, col=1)

    amount_colors = np.where(hist["日涨跌幅"] >= 0, "#22c55e", "#ef4444")
    fig.add_trace(go.Bar(x=hist["日期"], y=hist["成交额"] / 1e8, name="成交额/亿", marker_color=amount_colors, opacity=0.68), row=2, col=1)
    fig.add_trace(go.Scatter(x=hist["日期"], y=hist["成交额_MA20"] / 1e8, mode="lines", name="成交额MA20/亿", line=dict(width=1.6, color="#fbbf24")), row=2, col=1)

    money_colors = np.where(hist["资金行为强度"] >= 0, "#22c55e", "#ef4444")
    fig.add_trace(go.Bar(x=hist["日期"], y=hist["资金行为强度"], name="资金行为强度", marker_color=money_colors, opacity=0.76), row=3, col=1)
    fig.add_hline(y=0, line_width=1, line_dash="dot", line_color="#94a3b8", row=3, col=1)
    fig.update_layout(
        height=820,
        hovermode="x unified",
        plot_bgcolor="#111827",
        paper_bgcolor="#111827",
        font=dict(color="#f8fafc", size=13),
        legend=dict(orientation="h", yanchor="bottom", y=1.08, xanchor="left", x=0, bgcolor="rgba(17,24,39,0.80)"),
        margin=dict(l=30, r=30, t=92, b=32),
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(148, 163, 184, 0.14)", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(148, 163, 184, 0.14)", zeroline=False)
    fig.update_yaxes(title_text="价格/净值", row=1, col=1)
    fig.update_yaxes(title_text="成交额/亿", row=2, col=1)
    fig.update_yaxes(title_text="强度", row=3, col=1)
    for ann in fig["layout"]["annotations"]:
        ann["font"] = dict(size=15, color="#f8fafc")
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


def ocr_image_to_text(image: Image.Image) -> tuple[str, str]:
    if importlib.util.find_spec("pytesseract"):
        try:
            import pytesseract
            text = pytesseract.image_to_string(image, lang="chi_sim+eng")
            return text, "pytesseract"
        except Exception as e:
            return "", f"pytesseract不可用：{e}"
    return "", "当前环境未检测到OCR组件。可先手动粘贴识别文本，或安装 pytesseract/Tesseract 后启用自动识别。"


def parse_amount(text: str) -> float:
    if not text:
        return np.nan
    cleaned = text.replace(",", "").replace("，", "").replace("￥", "").replace("元", "").strip()
    match = re.search(r"[-+]?\d+(?:\.\d+)?", cleaned)
    if not match:
        return np.nan
    value = float(match.group())
    if "万" in cleaned:
        value *= 10000
    elif "亿" in cleaned:
        value *= 100000000
    return value


def extract_holdings_from_text(text: str) -> pd.DataFrame:
    rows = []
    seen = set()
    lines = [line.strip() for line in re.split(r"[\r\n]+", text or "") if line.strip()]
    context_lines = []
    for idx, line in enumerate(lines):
        context = " ".join(lines[max(0, idx - 1): min(len(lines), idx + 2)])
        context_lines.append(context)
        codes = re.findall(r"(?<!\d)(?:1|5|6|9)\d{5}(?!\d)", context)
        for code in codes:
            if code in seen:
                continue
            seen.add(code)
            amount_candidates = re.findall(r"(?:持有|市值|金额|资产|参考市值|持仓)[^\d-]*([-+]?\d[\d,，]*(?:\.\d+)?\s*[万亿]?)", context)
            if not amount_candidates:
                amount_candidates = re.findall(r"[-+]?\d[\d,，]*(?:\.\d+)?\s*[万亿]?", context)
            amount = np.nan
            numeric_candidates = [parse_amount(x) for x in amount_candidates]
            numeric_candidates = [x for x in numeric_candidates if pd.notna(x) and x > 10 and abs(x - int(code)) > 1]
            if numeric_candidates:
                amount = max(numeric_candidates)
            rows.append({"代码": code, "名称": CODE_TO_NAME.get(code, ""), "持仓金额": amount, "识别来源": "代码识别"})

    for name, code in DEFAULT_ETFS.items():
        if code in seen or name not in text:
            continue
        for context in context_lines:
            if name in context:
                amount_candidates = re.findall(r"[-+]?\d[\d,，]*(?:\.\d+)?\s*[万亿]?", context)
                numeric_candidates = [parse_amount(x) for x in amount_candidates]
                numeric_candidates = [x for x in numeric_candidates if pd.notna(x) and x > 10]
                rows.append({"代码": code, "名称": name, "持仓金额": max(numeric_candidates) if numeric_candidates else np.nan, "识别来源": "名称识别"})
                seen.add(code)
                break

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["代码", "名称", "持仓金额", "识别来源"])
    df["持仓金额"] = pd.to_numeric(df["持仓金额"], errors="coerce")
    return df.drop_duplicates(subset=["代码"], keep="first").reset_index(drop=True)


def enrich_holdings(holdings_df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    if holdings_df is None or holdings_df.empty:
        return pd.DataFrame(), "暂无持仓"
    df = holdings_df.copy()
    df["代码"] = df["代码"].astype(str).str.extract(r"(\d{6})")[0]
    df = df.dropna(subset=["代码"])
    df["持仓金额"] = pd.to_numeric(df["持仓金额"], errors="coerce")
    codes = tuple(df["代码"].dropna().unique().tolist())
    spot, source = get_etf_spot(codes)
    spot = normalize_spot_columns(spot)
    if not spot.empty:
        spot["代码"] = spot["代码"].astype(str)
        df = df.merge(spot[["代码", "名称", "最新价", "涨跌幅"]], on="代码", how="left", suffixes=("", "_行情"))
        df["名称"] = df["名称"].where(df["名称"].astype(str).str.len() > 0, df["名称_行情"])
        df = df.drop(columns=[c for c in ["名称_行情"] if c in df.columns])
    else:
        df["最新价"] = np.nan
        df["涨跌幅"] = np.nan
    df["估算今日盈亏"] = df["持仓金额"] * df["涨跌幅"] / 100
    df["估算收盘后金额"] = df["持仓金额"] + df["估算今日盈亏"]
    return df, source


def render_status(spot_source: str, hist_source: str):
    if "备用展示" in hist_source or "备用展示" in spot_source:
        st.markdown('<div class="status-bad">当前启用了备用展示数据：仅用于保证看板可打开，不是真实行情，不作为投资参考。</div>', unsafe_allow_html=True)
    elif "缓存" in hist_source or "缓存" in spot_source:
        st.markdown('<div class="status-warn">当前部分数据来自最近一次成功缓存，公开行情接口可能暂时不稳定。</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-ok">当前数据源状态：东方财富真实行情接口正常。</div>', unsafe_allow_html=True)


st.markdown('<div class="app-title">基金 / ETF 实时分析看板</div>', unsafe_allow_html=True)
st.markdown('<div class="app-subtitle">行情监控、趋势结构、资金行为代理与持仓当日盈亏估算</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("看板设置")
    module_name = st.selectbox("选择基金模块", list(ETF_MODULES.keys()), index=list(ETF_MODULES.keys()).index("电气电力与新能源"))
    module_etfs = ETF_MODULES[module_name]
    selected_name = st.selectbox("选择模块内基金/ETF", list(module_etfs.keys()), index=0)
    st.divider()
    custom_mode = st.checkbox("手动输入基金/ETF代码", value=False)
    if custom_mode:
        selected_code = st.text_input("输入6位基金/ETF代码", value=module_etfs[selected_name]).strip()
        selected_display_name = f"自查基金/ETF {selected_code}"
        watch_codes = list(dict.fromkeys([selected_code] + list(module_etfs.values())))
    else:
        selected_code = module_etfs[selected_name]
        selected_display_name = selected_name
        watch_codes = list(module_etfs.values())
    days = st.slider("历史分析周期", min_value=80, max_value=520, value=240, step=20)
    st.divider()
    auto_refresh = st.checkbox("自动刷新", value=False)
    refresh_seconds = st.slider("刷新间隔/秒", min_value=30, max_value=600, value=90, step=30)
    st.divider()
    if st.button("清除页面缓存并刷新"):
        st.cache_data.clear()
        st.rerun()
    st.caption("数据来自东方财富公开行情接口；接口失败时优先读取缓存，仍失败则展示模拟数据。")


try:
    with st.spinner("正在获取行情数据..."):
        spot_df, spot_source = get_etf_spot(tuple(watch_codes))
        spot_norm = normalize_spot_columns(spot_df)
        hist, hist_source = get_etf_history(selected_code, days=days)

    if hist.empty:
        st.warning("未获取到历史行情，请检查代码是否正确，或稍后重试。")
        st.stop()

    render_status(spot_source, hist_source)
    summary = compute_summary(hist)
    latest = hist.iloc[-1]

    selected_spot = pd.DataFrame()
    if "代码" in spot_norm.columns:
        spot_norm["代码"] = spot_norm["代码"].astype(str)
        selected_spot = spot_norm[spot_norm["代码"] == str(selected_code)]

    if not selected_spot.empty:
        spot_row = selected_spot.iloc[0]
        real_name = spot_row.get("名称", selected_display_name)
        latest_price = spot_row.get("最新价", latest["收盘"])
        today_pct = spot_row.get("涨跌幅", latest.get("日涨跌幅", np.nan))
        today_amount = spot_row.get("成交额", latest.get("成交额", np.nan))
    else:
        real_name = selected_display_name
        latest_price = latest["收盘"]
        today_pct = latest.get("日涨跌幅", np.nan)
        today_amount = latest.get("成交额", np.nan)

    top_cols = st.columns(5)
    top_cols[0].metric("基金/ETF", real_name)
    top_cols[1].metric("当前价/净值", f"{safe_num(latest_price):.3f}" if pd.notna(safe_num(latest_price)) else "暂无")
    top_cols[2].metric("今日涨跌幅", format_pct(today_pct))
    top_cols[3].metric("成交额", format_money(today_amount))
    top_cols[4].metric("资金信号", summary["money_label"])

    sub_cols = st.columns(5)
    sub_cols[0].metric("趋势评分", f"{summary['trend_score']} / 5")
    sub_cols[1].metric("趋势状态", summary["trend_label"])
    sub_cols[2].metric("风险状态", summary["risk_label"])
    sub_cols[3].metric("量能倍率", f"{latest['量能倍率']:.2f}x" if pd.notna(latest["量能倍率"]) else "暂无")
    sub_cols[4].metric("策略提示", summary["action_label"])

    st.markdown(
        f"""
        <div class="section-shell">
            <div class="section-note">
            当前模块：{module_name}；实时行情：{spot_source}；历史行情：{hist_source}；
            历史数据最后日期：{latest['日期'].strftime('%Y-%m-%d') if pd.notna(latest['日期']) else '未知'}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["看盘图", "自动解读", "持仓导入", "模块行情池", "信号明细", "全模块速览"])

    with tab1:
        st.markdown(
            f"""
            <div class="section-shell">
                <div class="section-title">{real_name}（{selected_code}）</div>
                <div class="section-note">均线结构、成交额变化与资金行为代理信号。图中信号来自价格、成交额与OBV的组合判断。</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.plotly_chart(draw_professional_chart(hist), use_container_width=True)

    with tab2:
        left, right = st.columns([1.2, 1])
        with left:
            st.markdown(
                f"""
                <div class="signal-card">
                    <strong>自动分析结论</strong>
                    <div class="signal-text">{summary["comment"].replace(chr(10), "<br>")}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown(
                """
                <div class="signal-card">
                    <strong>信号解释</strong>
                    <div class="signal-text">
                    <span class="good">强流入</span>：上涨幅度较大，同时成交额明显放大，OBV强于短期均值。<br>
                    <span class="bad">强撤出</span>：下跌幅度较大，同时成交额明显放大，OBV弱于短期均值。<br>
                    <span class="warn">分歧放量</span>：涨跌不大但成交额明显放大，说明多空分歧增强。<br>
                    <span class="neutral">缩量观望</span>：成交额低于近期均值，说明资金参与度不足。
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with right:
            key_df = pd.DataFrame({
                "指标": ["收盘价/净值", "MA5", "MA20", "MA60", "相对MA5偏离", "相对MA20偏离", "相对MA60偏离", "成交额", "成交额MA20", "量能倍率", "资金行为强度"],
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
                    f"{latest['资金行为强度']:.2f}" if pd.notna(latest["资金行为强度"]) else "暂无",
                ],
            })
            st.dataframe(key_df, use_container_width=True, hide_index=True)

    with tab3:
        st.markdown(
            """
            <div class="section-shell">
                <div class="section-title">持仓截图导入与今日盈亏估算</div>
                <div class="section-note">上传基金持仓页截图后，系统会尽量识别6位基金/ETF代码与持仓金额。识别结果可手动修正，最终盈亏按“持仓金额 × 当日涨跌幅”估算。</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        uploaded = st.file_uploader("上传持仓截图", type=["png", "jpg", "jpeg", "webp"])
        manual_text = ""
        recognized_df = pd.DataFrame(columns=["代码", "名称", "持仓金额", "识别来源"])
        if uploaded:
            image = Image.open(uploaded)
            st.image(image, caption="已上传的持仓截图", use_container_width=True)
            ocr_text, ocr_source = ocr_image_to_text(image)
            st.caption(f"OCR状态：{ocr_source}")
            manual_text = st.text_area("识别文本，可在这里修正后重新解析", value=ocr_text, height=160)
            recognized_df = extract_holdings_from_text(manual_text)
        else:
            manual_text = st.text_area("也可以直接粘贴持仓页文字", placeholder="示例：新能源车ETF 515030 持仓金额 12000.00", height=140)
            if manual_text.strip():
                recognized_df = extract_holdings_from_text(manual_text)

        if recognized_df.empty:
            recognized_df = pd.DataFrame([{"代码": selected_code, "名称": real_name, "持仓金额": np.nan, "识别来源": "手动补充"}])

        edited = st.data_editor(
            recognized_df,
            use_container_width=True,
            num_rows="dynamic",
            hide_index=True,
            column_config={
                "代码": st.column_config.TextColumn("代码", help="6位基金/ETF代码"),
                "名称": st.column_config.TextColumn("名称"),
                "持仓金额": st.column_config.NumberColumn("持仓金额", min_value=0.0, step=100.0, format="%.2f"),
                "识别来源": st.column_config.TextColumn("识别来源"),
            },
        )
        portfolio_df, portfolio_source = enrich_holdings(edited)
        if not portfolio_df.empty:
            total_amount = portfolio_df["持仓金额"].sum(skipna=True)
            total_pnl = portfolio_df["估算今日盈亏"].sum(skipna=True)
            avg_pct = total_pnl / total_amount * 100 if total_amount else np.nan
            p1, p2, p3, p4 = st.columns(4)
            p1.metric("持仓市值", format_money(total_amount))
            p2.metric("估算今日盈亏", format_money(total_pnl))
            p3.metric("组合今日收益率", format_pct(avg_pct))
            p4.metric("行情来源", portfolio_source.split("，")[0])
            show_df = portfolio_df.copy()
            for col in ["持仓金额", "估算今日盈亏", "估算收盘后金额"]:
                show_df[col] = show_df[col].apply(format_money)
            show_df["涨跌幅"] = show_df["涨跌幅"].apply(format_pct)
            st.dataframe(show_df[["代码", "名称", "持仓金额", "涨跌幅", "估算今日盈亏", "估算收盘后金额"]], use_container_width=True, hide_index=True)
            st.caption("估算结果使用实时涨跌幅线性计算，未考虑申赎费、分红、场外基金净值延迟和盘中净值偏差。")

    with tab4:
        market_table = build_market_table(spot_df, watch_codes)
        if market_table.empty:
            st.warning("暂未获取到模块行情表。")
        else:
            if "涨跌幅" in market_table.columns:
                market_table = market_table.sort_values("涨跌幅", ascending=False)
            st.subheader(f"{module_name} 模块实时强弱排名")
            st.dataframe(market_table, use_container_width=True, height=520, hide_index=True)
            if "涨跌幅" in market_table.columns and len(market_table) >= 2:
                best = market_table.iloc[0]
                worst = market_table.iloc[-1]
                st.info(f"当前模块中，最强为 {best.get('名称', '')}，涨跌幅 {safe_num(best.get('涨跌幅', np.nan)):.2f}%；最弱为 {worst.get('名称', '')}，涨跌幅 {safe_num(worst.get('涨跌幅', np.nan)):.2f}%。")

    with tab5:
        signal_df = hist[["日期", "收盘", "日涨跌幅", "成交额", "量能倍率", "资金行为强度", "资金信号", "均线偏离_MA5", "均线偏离_MA20", "均线偏离_MA60"]].copy()
        signal_df["日期"] = signal_df["日期"].dt.strftime("%Y-%m-%d")
        signal_df["成交额"] = signal_df["成交额"].apply(format_money)
        signal_df["日涨跌幅"] = signal_df["日涨跌幅"].apply(format_pct)
        signal_df["量能倍率"] = signal_df["量能倍率"].map(lambda x: f"{x:.2f}x" if pd.notna(x) else "暂无")
        signal_df["资金行为强度"] = signal_df["资金行为强度"].map(lambda x: f"{x:.2f}" if pd.notna(x) else "暂无")
        for col in ["均线偏离_MA5", "均线偏离_MA20", "均线偏离_MA60"]:
            signal_df[col] = signal_df[col].apply(format_pct)
        st.subheader("历史资金行为信号明细")
        st.dataframe(signal_df.sort_values("日期", ascending=False), use_container_width=True, height=520, hide_index=True)

    with tab6:
        module_rows = [{"模块": mod, "名称": name, "代码": code} for mod, items in ETF_MODULES.items() for name, code in items.items()]
        st.subheader("全模块基金池")
        st.dataframe(pd.DataFrame(module_rows), use_container_width=True, height=560, hide_index=True)
        st.info("如果这里没有你要看的基金，打开左侧手动输入6位基金/ETF代码即可。")

except Exception as e:
    st.error("看板运行失败。")
    st.exception(e)


if auto_refresh:
    time.sleep(refresh_seconds)
    st.rerun()
