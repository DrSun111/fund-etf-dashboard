# -*- coding: utf-8 -*-
"""
基金智能分析平台
稳定数据源版：Tushare Pro

核心功能：
1. 实盘导入
2. ETF真实实时行情
3. 五日曲线
4. 场内实时穿透
5. 成分股实时贡献
6. 实仓底层资产暴露
7. 支持任意6位场内基金自查

运行：
streamlit run fund_dashboard.py

requirements.txt:
streamlit
pandas
numpy
plotly
requests
openpyxl
tushare
"""

from __future__ import annotations

import os
import re
import time
import datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import tushare as ts
from plotly.subplots import make_subplots


# ============================================================
# 页面配置
# ============================================================
st.set_page_config(
    page_title="基金智能分析平台",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# 全局路径与时区
# ============================================================
CHINA_TZ = ZoneInfo("Asia/Shanghai")

CACHE_DIR = Path(".fund_platform_cache")
CACHE_DIR.mkdir(exist_ok=True)

POSITION_FILE = CACHE_DIR / "positions.csv"
COMPONENT_FILE = CACHE_DIR / "components.csv"


# ============================================================
# CSS界面
# ============================================================
CUSTOM_CSS = """
<style>
[data-testid="stHeader"] {
    background: rgba(5, 8, 22, 0) !important;
    height: 0rem !important;
}
[data-testid="stToolbar"], [data-testid="stDecoration"] {
    display: none !important;
}
header {
    visibility: hidden !important;
    height: 0px !important;
}
html, body, [data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at top left, rgba(37, 99, 235, 0.20), transparent 25%),
        radial-gradient(circle at top right, rgba(20, 184, 166, 0.14), transparent 22%),
        linear-gradient(135deg, #050816 0%, #071126 48%, #030712 100%) !important;
    color: #F8FAFC !important;
}
.block-container {
    padding-top: 1rem !important;
    padding-bottom: 2.5rem !important;
    max-width: 96% !important;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #06112A 0%, #050A1B 100%) !important;
    border-right: 1px solid rgba(88, 213, 255, 0.18);
}
[data-testid="stSidebar"] * {
    color: #F8FAFC !important;
}
.main-title {
    font-size: 34px;
    font-weight: 900;
    color: #FFFFFF !important;
    letter-spacing: 0.4px;
    margin-bottom: 0.25rem;
    text-shadow: 0 0 22px rgba(88, 213, 255, 0.22);
}
.sub-title {
    color: #B7C5DA !important;
    font-size: 15px;
    margin-bottom: 1rem;
}
.panel {
    background: linear-gradient(135deg, rgba(10,16,34,0.96), rgba(13,25,52,0.95));
    border: 1px solid rgba(88,213,255,0.16);
    border-radius: 22px;
    padding: 18px 22px;
    margin-bottom: 16px;
    box-shadow: 0 12px 40px rgba(0,0,0,0.25);
}
.panel-title {
    font-size: 20px;
    font-weight: 850;
    color: #FFFFFF !important;
    margin-bottom: 5px;
}
.panel-subtitle {
    font-size: 13px;
    color: #AFC2DE !important;
}
.status-ok {
    background: linear-gradient(90deg, rgba(20, 83, 45, 0.86), rgba(6, 78, 59, 0.86));
    border: 1px solid rgba(74, 222, 128, 0.25);
    color: #D9FFF2 !important;
    padding: 13px 18px;
    border-radius: 16px;
    font-weight: 760;
    margin-bottom: 14px;
}
.status-warn {
    background: linear-gradient(90deg, rgba(113, 63, 18, 0.88), rgba(92, 52, 12, 0.88));
    border: 1px solid rgba(251, 191, 36, 0.28);
    color: #FFF4CF !important;
    padding: 13px 18px;
    border-radius: 16px;
    font-weight: 760;
    margin-bottom: 14px;
}
.status-danger {
    background: linear-gradient(90deg, rgba(127, 29, 29, 0.90), rgba(76, 29, 49, 0.88));
    border: 1px solid rgba(248, 113, 113, 0.30);
    color: #FFE4E6 !important;
    padding: 13px 18px;
    border-radius: 16px;
    font-weight: 760;
    margin-bottom: 14px;
}
.signal-card {
    padding: 18px 20px;
    border-radius: 18px;
    background: linear-gradient(135deg, rgba(12,20,40,0.96), rgba(15,23,42,0.96));
    border: 1px solid rgba(88,213,255,0.12);
    margin-bottom: 12px;
    box-shadow: 0 10px 28px rgba(0,0,0,0.20);
}
.signal-title {
    font-size: 17px;
    font-weight: 800;
    color: #FFFFFF !important;
    margin-bottom: 8px;
}
.signal-text {
    font-size: 14px;
    line-height: 1.75;
    color: #EAF1FF !important;
}
.good { color: #4ADE80 !important; font-weight: 800; }
.bad { color: #F87171 !important; font-weight: 800; }
.warn { color: #FBBF24 !important; font-weight: 800; }
.neutral { color: #CBD5E1 !important; font-weight: 800; }
div[data-testid="stMetric"] {
    background: linear-gradient(135deg, rgba(10,16,34,0.96), rgba(14,24,48,0.96)) !important;
    border: 1px solid rgba(88,213,255,0.14) !important;
    border-radius: 18px !important;
    padding: 16px 18px !important;
    min-height: 108px;
    box-shadow: 0 8px 26px rgba(0,0,0,0.18);
}
div[data-testid="stMetricLabel"] {
    color: #AFC2DE !important;
    font-size: 13px !important;
    font-weight: 650 !important;
}
div[data-testid="stMetricValue"] {
    color: #FFFFFF !important;
    font-size: 25px !important;
    font-weight: 900 !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] [data-baseweb="input"] > div,
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] textarea {
    background: linear-gradient(180deg, rgba(11,19,38,0.98), rgba(14,24,48,0.98)) !important;
    color: #F8FAFC !important;
    border: 1px solid rgba(88,213,255,0.25) !important;
    border-radius: 14px !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] span,
[data-testid="stSidebar"] [data-baseweb="select"] div,
[data-testid="stSidebar"] [data-baseweb="input"] input {
    color: #F8FAFC !important;
}
.stButton button {
    background: linear-gradient(90deg, rgba(24,38,73,0.98), rgba(20,31,60,0.98)) !important;
    color: #F8FAFC !important;
    border: 1px solid rgba(88,213,255,0.24) !important;
    border-radius: 12px !important;
}
.stButton button:hover {
    border-color: rgba(88,213,255,0.50) !important;
    box-shadow: 0 0 18px rgba(88,213,255,0.13) !important;
}
h1, h2, h3, h4, h5, h6, p, span, label {
    color: #F8FAFC !important;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ============================================================
# 市场模块
# ============================================================
FUND_MODULES = {
    "宽基指数": {
        "沪深300ETF": "510300",
        "上证50ETF": "510050",
        "中证500ETF": "510500",
        "中证1000ETF": "512100",
        "创业板ETF": "159915",
        "科创50ETF": "588000",
        "双创50ETF": "159781",
        "红利ETF": "510880",
    },
    "科技成长": {
        "半导体ETF": "512480",
        "芯片ETF": "159995",
        "人工智能ETF": "515980",
        "云计算ETF": "516510",
        "软件ETF": "515230",
        "通信ETF": "515880",
        "5GETF": "515050",
        "机器人ETF": "562500",
        "智能车ETF": "159888",
    },
    "电气电力与新能源": {
        "新能源车ETF": "515030",
        "光伏ETF": "515790",
        "电池ETF": "561910",
        "储能电池ETF": "159566",
        "绿色电力ETF": "562960",
        "电力ETF": "561560",
        "新能源ETF": "516160",
        "碳中和ETF": "159790",
        "央企能源ETF": "562850",
    },
    "资源周期与大宗商品": {
        "有色金属ETF": "512400",
        "稀土ETF": "516780",
        "钢铁ETF": "515210",
        "煤炭ETF": "515220",
        "能源ETF": "159930",
        "化工ETF": "516020",
        "石油基金LOF": "162719",
        "黄金ETF": "518880",
        "豆粕ETF": "159985",
    },
    "金融地产": {
        "证券ETF": "512880",
        "银行ETF": "512800",
        "保险证券ETF": "515630",
        "地产ETF": "512200",
        "金融ETF": "510230",
    },
    "消费医药农业": {
        "消费ETF": "159928",
        "酒ETF": "512690",
        "食品饮料ETF": "515170",
        "医药ETF": "512010",
        "医疗ETF": "512170",
        "创新药ETF": "159992",
        "养殖ETF": "159865",
        "农业ETF": "159825",
    },
    "港股与海外": {
        "恒生科技ETF": "513130",
        "恒生互联网ETF": "513330",
        "港股通互联网ETF": "159792",
        "恒生ETF": "159920",
        "纳指ETF": "513100",
        "标普500ETF": "513500",
        "德国ETF": "513030",
        "日经ETF": "513520",
    },
    "债券货币": {
        "短债ETF": "511360",
        "十年国债ETF": "511260",
        "国债ETF": "511010",
        "政金债ETF": "511520",
        "可转债ETF": "511380",
        "货币ETF": "511990",
    },
}

ALL_FUNDS = {}
for module_name, items in FUND_MODULES.items():
    ALL_FUNDS.update(items)


# ============================================================
# 基础工具
# ============================================================
def china_now() -> dt.datetime:
    return dt.datetime.now(CHINA_TZ)


def now_text() -> str:
    return china_now().strftime("%Y-%m-%d %H:%M:%S")


def trade_date_today() -> str:
    return china_now().strftime("%Y%m%d")


def is_china_trading_time() -> bool:
    now = china_now()
    if now.weekday() >= 5:
        return False
    t = now.time()
    return (dt.time(9, 30) <= t <= dt.time(11, 30)) or (dt.time(13, 0) <= t <= dt.time(15, 0))


def is_pre_market_time() -> bool:
    now = china_now()
    if now.weekday() >= 5:
        return False
    return dt.time(9, 0) <= now.time() < dt.time(9, 30)


def clean_code(code) -> str:
    text = str(code).strip().replace(".0", "")
    digits = re.sub(r"\D", "", text)
    if not digits:
        return ""
    return digits.zfill(6)[-6:]


def safe_num(x, default=np.nan) -> float:
    try:
        if pd.isna(x):
            return default
        if isinstance(x, str):
            x = x.replace("%", "").replace(",", "").strip()
        return float(x)
    except Exception:
        return default


def format_money(x) -> str:
    x = safe_num(x)
    if pd.isna(x):
        return "暂无"
    if abs(x) >= 1e8:
        return f"{x / 1e8:.2f} 亿"
    if abs(x) >= 1e4:
        return f"{x / 1e4:.2f} 万"
    return f"{x:.2f}"


def format_pct(x) -> str:
    x = safe_num(x)
    if pd.isna(x):
        return "暂无"
    return f"{x:.2f}%"


def fund_ts_code(code: str) -> str:
    code = clean_code(code)
    if code.startswith(("5", "6", "9")):
        return f"{code}.SH"
    return f"{code}.SZ"


def stock_ts_code(code: str) -> str:
    code = clean_code(code)
    if code.startswith(("6", "5", "9")):
        return f"{code}.SH"
    return f"{code}.SZ"


def ts_to_plain_code(ts_code: str) -> str:
    return clean_code(str(ts_code).split(".")[0])


def get_tushare_token() -> str:
    token = ""
    try:
        token = st.secrets.get("TUSHARE_TOKEN", "")
    except Exception:
        token = ""
    token = token or os.environ.get("TUSHARE_TOKEN", "")
    return token.strip()


def get_pro_client():
    token = get_tushare_token()
    if not token:
        return None
    ts.set_token(token)
    return ts.pro_api(token)


# ============================================================
# Tushare数据层
# ============================================================
@st.cache_data(ttl=10, show_spinner=False)
def fetch_tushare_etf_realtime(code: str, token: str):
    code = clean_code(code)
    ts_code = fund_ts_code(code)

    if not token:
        return pd.DataFrame(), "未配置Tushare Token", "请在 Streamlit secrets 中配置 TUSHARE_TOKEN"

    try:
        ts.set_token(token)
        pro = ts.pro_api(token)

        topic_candidates = ["HQ_FND_TICK", "HQ_ETF_TICK", ""]
        last_error = ""

        for topic in topic_candidates:
            try:
                if topic:
                    df = pro.rt_etf_k(ts_code=ts_code, topic=topic)
                else:
                    df = pro.rt_etf_k(ts_code=ts_code)

                if df is not None and not df.empty:
                    out = df.copy()
                    out["code"] = out["ts_code"].map(ts_to_plain_code)
                    out["name"] = out.get("name", "")
                    out["close"] = pd.to_numeric(out["close"], errors="coerce")
                    out["pre_close"] = pd.to_numeric(out.get("pre_close", np.nan), errors="coerce")
                    out["open"] = pd.to_numeric(out.get("open", np.nan), errors="coerce")
                    out["high"] = pd.to_numeric(out.get("high", np.nan), errors="coerce")
                    out["low"] = pd.to_numeric(out.get("low", np.nan), errors="coerce")
                    out["vol"] = pd.to_numeric(out.get("vol", np.nan), errors="coerce")
                    out["amount"] = pd.to_numeric(out.get("amount", np.nan), errors="coerce")
                    out["pct_change"] = np.where(
                        out["pre_close"] > 0,
                        (out["close"] / out["pre_close"] - 1) * 100,
                        np.nan,
                    )
                    out["trade_time"] = out.get("trade_time", now_text())
                    out["source"] = "Tushare rt_etf_k"
                    return out, "Tushare ETF实时日线", ""
            except Exception as e:
                last_error = str(e)

        return pd.DataFrame(), "Tushare ETF实时日线失败", last_error

    except Exception as e:
        return pd.DataFrame(), "Tushare连接失败", str(e)


@st.cache_data(ttl=60, show_spinner=False)
def fetch_tushare_etf_daily(code: str, start_date: str, end_date: str, token: str):
    code = clean_code(code)
    ts_code = fund_ts_code(code)

    if not token:
        return pd.DataFrame(), "未配置Tushare Token", "请配置 TUSHARE_TOKEN"

    try:
        ts.set_token(token)
        pro = ts.pro_api(token)
        df = pro.fund_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)

        if df is None or df.empty:
            return pd.DataFrame(), "Tushare ETF日线为空", f"{ts_code} 未返回历史日线"

        out = df.copy()
        out["date"] = pd.to_datetime(out["trade_date"])
        out["open"] = pd.to_numeric(out["open"], errors="coerce")
        out["high"] = pd.to_numeric(out["high"], errors="coerce")
        out["low"] = pd.to_numeric(out["low"], errors="coerce")
        out["close"] = pd.to_numeric(out["close"], errors="coerce")
        out["pre_close"] = pd.to_numeric(out.get("pre_close", np.nan), errors="coerce")
        out["change"] = pd.to_numeric(out.get("change", np.nan), errors="coerce")
        out["pct_change"] = pd.to_numeric(out.get("pct_chg", np.nan), errors="coerce")
        out["vol"] = pd.to_numeric(out.get("vol", np.nan), errors="coerce")
        out["amount"] = pd.to_numeric(out.get("amount", np.nan), errors="coerce")
        out["source"] = "Tushare fund_daily"
        out = out.sort_values("date").reset_index(drop=True)

        return out, "Tushare ETF历史日线", ""

    except Exception as e:
        return pd.DataFrame(), "Tushare ETF历史日线失败", str(e)


@st.cache_data(ttl=10, show_spinner=False)
def fetch_tushare_stock_realtime(stock_codes_tuple, token: str):
    codes = [clean_code(c) for c in list(stock_codes_tuple)]
    codes = [c for c in dict.fromkeys(codes) if c]
    if not codes:
        return pd.DataFrame(), "无股票代码", ""

    if not token:
        return pd.DataFrame(), "未配置Tushare Token", "请配置 TUSHARE_TOKEN"

    rows = []
    errors = []

    try:
        ts.set_token(token)
        pro = ts.pro_api(token)

        for code in codes:
            ts_code = stock_ts_code(code)
            try:
                df = pro.rt_k(ts_code=ts_code)
                if df is not None and not df.empty:
                    one = df.iloc[0].to_dict()
                    close = safe_num(one.get("close"))
                    pre_close = safe_num(one.get("pre_close"))
                    pct = (close / pre_close - 1) * 100 if pd.notna(close) and pd.notna(pre_close) and pre_close > 0 else np.nan
                    rows.append(
                        {
                            "stock_code": code,
                            "ts_code": ts_code,
                            "stock_name": one.get("name", ""),
                            "price": close,
                            "pre_close": pre_close,
                            "open": safe_num(one.get("open")),
                            "high": safe_num(one.get("high")),
                            "low": safe_num(one.get("low")),
                            "pct_change": pct,
                            "vol": safe_num(one.get("vol")),
                            "amount": safe_num(one.get("amount")),
                            "trade_time": one.get("trade_time", now_text()),
                            "source": "Tushare rt_k",
                        }
                    )
                else:
                    errors.append(f"{ts_code} 实时行情为空")
            except Exception as e:
                errors.append(f"{ts_code}: {e}")

        out = pd.DataFrame(rows)
        if out.empty:
            return pd.DataFrame(), "Tushare股票实时行情失败", "；".join(errors[:8])

        return out, "Tushare股票实时行情", "；".join(errors[:5])

    except Exception as e:
        return pd.DataFrame(), "Tushare股票实时行情连接失败", str(e)


@st.cache_data(ttl=60 * 60, show_spinner=False)
def fetch_tushare_fund_portfolio(code: str, token: str):
    code = clean_code(code)
    ts_code = fund_ts_code(code)

    if not token:
        return pd.DataFrame(), "未配置Tushare Token", "请配置 TUSHARE_TOKEN"

    try:
        ts.set_token(token)
        pro = ts.pro_api(token)
        df = pro.fund_portfolio(ts_code=ts_code)

        if df is None or df.empty:
            return pd.DataFrame(), "Tushare基金持仓为空", f"{ts_code} 未返回基金持仓"

        out = df.copy()
        out["fund_code"] = code
        out["stock_code"] = out["symbol"].map(ts_to_plain_code)
        out["stock_name"] = out["symbol"].astype(str)
        out["weight"] = pd.to_numeric(out.get("stk_mkv_ratio", np.nan), errors="coerce")
        out["industry"] = ""
        out["report_date"] = out.get("end_date", "")
        out["source"] = "Tushare fund_portfolio 季度持仓"

        out = out[out["stock_code"].str.len() == 6].copy()
        out = out[out["weight"].notna()].copy()
        out = out.sort_values(["report_date", "weight"], ascending=[False, False])
        latest_period = out["report_date"].dropna().astype(str).max()
        if latest_period:
            out = out[out["report_date"].astype(str) == latest_period].copy()

        return out[["fund_code", "stock_code", "stock_name", "weight", "industry", "report_date", "source"]], "Tushare基金季度持仓", ""

    except Exception as e:
        return pd.DataFrame(), "Tushare基金持仓失败", str(e)


# ============================================================
# 数据整合
# ============================================================
def merge_realtime_into_history(history: pd.DataFrame, realtime: pd.DataFrame):
    if history is None or history.empty:
        return history, ""

    if realtime is None or realtime.empty:
        return history, ""

    row = realtime.iloc[0]
    price = safe_num(row.get("close"))
    pre_close = safe_num(row.get("pre_close"))
    amount = safe_num(row.get("amount"))
    vol = safe_num(row.get("vol"))

    if pd.isna(price) or price <= 0:
        return history, "实时价无效，未合并"

    today = pd.Timestamp(china_now().date())
    df = history.copy()
    last_date = pd.to_datetime(df.iloc[-1]["date"]).normalize()

    pct = (price / pre_close - 1) * 100 if pd.notna(pre_close) and pre_close > 0 else np.nan

    if last_date == today:
        idx = df.index[-1]
        df.loc[idx, "close"] = price
        df.loc[idx, "pct_change"] = pct if pd.notna(pct) else df.loc[idx, "pct_change"]
        df.loc[idx, "high"] = max(safe_num(df.loc[idx, "high"], price), price)
        df.loc[idx, "low"] = min(safe_num(df.loc[idx, "low"], price), price)
        df.loc[idx, "amount"] = amount if pd.notna(amount) else df.loc[idx, "amount"]
        df.loc[idx, "vol"] = vol if pd.notna(vol) else df.loc[idx, "vol"]
        df.loc[idx, "source"] = "Tushare实时合并"
        return df, f"已用Tushare实时行情更新今日K线：{now_text()}"

    open_price = pre_close if pd.notna(pre_close) and pre_close > 0 else safe_num(df.iloc[-1]["close"], price)

    new_row = {
        "date": today,
        "open": open_price,
        "high": max(open_price, price),
        "low": min(open_price, price),
        "close": price,
        "pre_close": pre_close,
        "change": price - pre_close if pd.notna(pre_close) else np.nan,
        "pct_change": pct,
        "vol": vol,
        "amount": amount,
        "source": "Tushare实时追加",
    }

    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    return df, f"历史日线未到今日，已追加Tushare实时行情：{now_text()}"


def enrich_indicators(df: pd.DataFrame):
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])
    out = out.sort_values("date").reset_index(drop=True)

    for col in ["open", "high", "low", "close", "vol", "amount", "pct_change"]:
        if col not in out.columns:
            out[col] = np.nan
        out[col] = pd.to_numeric(out[col], errors="coerce")

    out["close"] = out["close"].ffill().bfill()
    out["pct_change"] = out["pct_change"].fillna(out["close"].pct_change() * 100).fillna(0)
    out["amount"] = out["amount"].fillna(0)
    out["vol"] = out["vol"].fillna(0)

    out["ma5"] = out["close"].rolling(5, min_periods=2).mean()
    out["ma10"] = out["close"].rolling(10, min_periods=3).mean()
    out["ma20"] = out["close"].rolling(20, min_periods=5).mean()
    out["ma60"] = out["close"].rolling(60, min_periods=10).mean()

    out["amount_ma20"] = out["amount"].rolling(20, min_periods=5).mean()
    out["volume_ratio"] = np.where(out["amount_ma20"] > 0, out["amount"] / out["amount_ma20"], np.nan)

    out["ma5_dev"] = (out["close"] / out["ma5"] - 1) * 100
    out["ma20_dev"] = (out["close"] / out["ma20"] - 1) * 100
    out["ma60_dev"] = (out["close"] / out["ma60"] - 1) * 100
    out["money_strength"] = out["pct_change"] * out["amount"] / 1e5

    return out


def compute_summary(df: pd.DataFrame):
    if df is None or df.empty:
        return {
            "trend_score": 0,
            "trend_label": "无数据",
            "risk_label": "无法判断",
            "action": "等待真实数据",
            "comment": "当前未获取到真实行情，无法分析。",
        }

    latest = df.iloc[-1]
    close = safe_num(latest["close"])

    score = 0
    if pd.notna(latest["ma5"]) and close > latest["ma5"]:
        score += 1
    if pd.notna(latest["ma20"]) and close > latest["ma20"]:
        score += 1
    if pd.notna(latest["ma60"]) and close > latest["ma60"]:
        score += 1
    if pd.notna(latest["ma5"]) and pd.notna(latest["ma20"]) and latest["ma5"] > latest["ma20"]:
        score += 1
    if pd.notna(latest["ma20"]) and pd.notna(latest["ma60"]) and latest["ma20"] > latest["ma60"]:
        score += 1

    if score >= 4:
        trend = "趋势偏强"
    elif score == 3:
        trend = "趋势修复"
    elif score == 2:
        trend = "震荡偏弱"
    else:
        trend = "趋势偏弱"

    bias20 = safe_num(latest.get("ma20_dev"))
    if pd.isna(bias20):
        risk = "风险不明"
    elif bias20 > 8:
        risk = "短期过热"
    elif bias20 > 4:
        risk = "略偏高"
    elif bias20 < -8:
        risk = "深度回调"
    elif bias20 < -4:
        risk = "回调区"
    else:
        risk = "正常波动"

    if trend in ["趋势偏强", "趋势修复"] and risk != "短期过热":
        action = "继续持有观察"
    elif risk == "短期过热":
        action = "不宜追高"
    elif trend == "趋势偏弱":
        action = "谨慎防守"
    else:
        action = "震荡观察"

    comment = (
        f"当前趋势评分为 {score}/5，处于“{trend}”。"
        f"价格相对MA20偏离 {bias20:.2f}% ，风险状态为“{risk}”。"
        f"若ETF场内涨跌明显高于底层成分估算涨跌，可能存在溢价或追涨情绪；"
        f"若明显低于底层估算涨跌，则可能存在折价或流动性折让。"
        f"当前策略更偏向“{action}”。"
    )

    return {
        "trend_score": score,
        "trend_label": trend,
        "risk_label": risk,
        "action": action,
        "comment": comment,
    }


# ============================================================
# 成分/PCF处理
# ============================================================
def normalize_components(raw: pd.DataFrame, default_fund_code: str = ""):
    if raw is None or raw.empty:
        return pd.DataFrame(columns=["fund_code", "stock_code", "stock_name", "weight", "industry", "source"])

    df = raw.copy()
    rename = {}

    for col in df.columns:
        c = str(col).strip()
        c_low = c.lower()

        if c in ["基金代码", "ETF代码", "fund_code", "etf_code"]:
            rename[col] = "fund_code"
        elif c in ["股票代码", "证券代码", "成分券代码", "stock_code", "code", "symbol"]:
            rename[col] = "stock_code"
        elif c in ["股票名称", "证券简称", "证券名称", "成分券名称", "stock_name", "name"]:
            rename[col] = "stock_name"
        elif c in ["权重", "占比", "持仓占比", "占净值比例", "weight", "stk_mkv_ratio"] or "权重" in c or "比例" in c:
            rename[col] = "weight"
        elif c in ["行业", "industry", "申万行业"]:
            rename[col] = "industry"

    df = df.rename(columns=rename)

    for col in ["fund_code", "stock_code", "stock_name", "weight", "industry", "source"]:
        if col not in df.columns:
            df[col] = ""

    if default_fund_code:
        df["fund_code"] = np.where(
            df["fund_code"].astype(str).str.strip() == "",
            clean_code(default_fund_code),
            df["fund_code"],
        )

    df["fund_code"] = df["fund_code"].astype(str).map(clean_code)
    df["stock_code"] = df["stock_code"].astype(str).map(clean_code)
    df["stock_name"] = df["stock_name"].astype(str)
    df["industry"] = df["industry"].astype(str)

    df["weight"] = (
        df["weight"]
        .astype(str)
        .str.replace("%", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
        .replace({"": np.nan, "-": np.nan, "nan": np.nan})
    )
    df["weight"] = pd.to_numeric(df["weight"], errors="coerce")

    if not df["weight"].dropna().empty and df["weight"].dropna().max() <= 1.2:
        df["weight"] = df["weight"] * 100

    df = df[df["fund_code"].str.len() == 6].copy()
    df = df[df["stock_code"].str.len() == 6].copy()
    df = df[df["weight"].notna()].copy()

    df["source"] = np.where(
        df["source"].astype(str).str.strip() == "",
        "用户导入PCF/成分清单",
        df["source"],
    )

    return df[["fund_code", "stock_code", "stock_name", "weight", "industry", "source"]].reset_index(drop=True)


def load_components():
    if COMPONENT_FILE.exists():
        try:
            return normalize_components(pd.read_csv(COMPONENT_FILE))
        except Exception:
            return pd.DataFrame(columns=["fund_code", "stock_code", "stock_name", "weight", "industry", "source"])
    return pd.DataFrame(columns=["fund_code", "stock_code", "stock_name", "weight", "industry", "source"])


def save_components(df: pd.DataFrame):
    df.to_csv(COMPONENT_FILE, index=False, encoding="utf-8-sig")


def get_components_for_fund(code: str, token: str):
    code = clean_code(code)

    local = load_components()
    hit = local[local["fund_code"] == code].copy()

    if not hit.empty:
        return hit, "用户导入PCF/成分清单", ""

    q_df, q_source, q_error = fetch_tushare_fund_portfolio(code, token)
    if not q_df.empty:
        return q_df, q_source, q_error

    return pd.DataFrame(), q_source, q_error


def calculate_lookthrough(code: str, token: str):
    comps, comp_source, comp_error = get_components_for_fund(code, token)

    if comps.empty:
        return pd.DataFrame(), comp_source, comp_error

    stock_codes = comps["stock_code"].dropna().astype(str).unique().tolist()
    quotes, quote_source, quote_error = fetch_tushare_stock_realtime(tuple(stock_codes), token)

    if quotes.empty:
        return pd.DataFrame(), quote_source, quote_error

    df = comps.merge(quotes, on="stock_code", how="left", suffixes=("", "_quote"))

    df["stock_name"] = np.where(
        df["stock_name"].astype(str).str.strip() == "",
        df["stock_name_quote"],
        df["stock_name"],
    )

    df["weight"] = pd.to_numeric(df["weight"], errors="coerce")
    df["pct_change"] = pd.to_numeric(df["pct_change"], errors="coerce")
    df["contribution_pct"] = df["weight"] / 100 * df["pct_change"]

    df = df.sort_values("contribution_pct", ascending=False).reset_index(drop=True)
    return df, f"{comp_source} + {quote_source}", quote_error or comp_error


# ============================================================
# 实仓
# ============================================================
def normalize_positions(raw: pd.DataFrame):
    if raw is None or raw.empty:
        return pd.DataFrame(columns=["code", "name", "shares", "cost_price", "buy_date", "account_type", "notes"])

    df = raw.copy()
    rename = {}

    for col in df.columns:
        c = str(col).strip()
        if c in ["基金代码", "代码", "ETF代码", "fund_code", "code"]:
            rename[col] = "code"
        elif c in ["基金名称", "名称", "fund_name", "name"]:
            rename[col] = "name"
        elif c in ["份额", "持有份额", "shares"]:
            rename[col] = "shares"
        elif c in ["成本价", "持仓成本", "买入成本", "cost_price"]:
            rename[col] = "cost_price"
        elif c in ["买入日期", "buy_date"]:
            rename[col] = "buy_date"
        elif c in ["账户类型", "account_type"]:
            rename[col] = "account_type"
        elif c in ["备注", "notes"]:
            rename[col] = "notes"

    df = df.rename(columns=rename)

    for col in ["code", "name", "shares", "cost_price", "buy_date", "account_type", "notes"]:
        if col not in df.columns:
            df[col] = ""

    df["code"] = df["code"].astype(str).map(clean_code)
    df["name"] = df["name"].astype(str)
    df["shares"] = pd.to_numeric(df["shares"], errors="coerce").fillna(0)
    df["cost_price"] = pd.to_numeric(df["cost_price"], errors="coerce").fillna(0)

    df = df[df["code"].str.len() == 6].copy()
    return df[["code", "name", "shares", "cost_price", "buy_date", "account_type", "notes"]].reset_index(drop=True)


def load_positions():
    if POSITION_FILE.exists():
        try:
            return normalize_positions(pd.read_csv(POSITION_FILE))
        except Exception:
            return pd.DataFrame(columns=["code", "name", "shares", "cost_price", "buy_date", "account_type", "notes"])
    return pd.DataFrame(columns=["code", "name", "shares", "cost_price", "buy_date", "account_type", "notes"])


def save_positions(df: pd.DataFrame):
    df.to_csv(POSITION_FILE, index=False, encoding="utf-8-sig")


def current_price_for_fund(code: str, token: str):
    rt, source, error = fetch_tushare_etf_realtime(code, token)
    if rt is not None and not rt.empty:
        row = rt.iloc[0]
        return safe_num(row.get("close")), str(row.get("name", f"基金{code}")), source

    today = trade_date_today()
    start_date = (china_now() - dt.timedelta(days=30)).strftime("%Y%m%d")
    hist, h_source, h_error = fetch_tushare_etf_daily(code, start_date, today, token)

    if hist is not None and not hist.empty:
        return safe_num(hist.iloc[-1]["close"]), f"基金{code}", h_source

    return np.nan, f"基金{code}", f"{source}; {error}; {h_source}; {h_error}"


def compute_position_detail(positions: pd.DataFrame, token: str):
    if positions is None or positions.empty:
        return pd.DataFrame()

    rows = []
    for _, pos in positions.iterrows():
        code = clean_code(pos["code"])
        price, real_name, price_source = current_price_for_fund(code, token)

        shares = safe_num(pos["shares"], 0)
        cost = safe_num(pos["cost_price"], 0)

        current_value = shares * price if pd.notna(price) else np.nan
        cost_value = shares * cost if cost > 0 else np.nan
        profit = current_value - cost_value if pd.notna(current_value) and pd.notna(cost_value) else np.nan
        profit_rate = profit / cost_value * 100 if pd.notna(profit) and cost_value > 0 else np.nan

        rows.append(
            {
                "code": code,
                "name": pos["name"] if str(pos["name"]).strip() else real_name,
                "shares": shares,
                "cost_price": cost,
                "current_price": price,
                "current_value": current_value,
                "cost_value": cost_value,
                "profit": profit,
                "profit_rate": profit_rate,
                "price_source": price_source,
                "buy_date": pos.get("buy_date", ""),
                "notes": pos.get("notes", ""),
            }
        )

    df = pd.DataFrame(rows)
    if not df.empty:
        total = df["current_value"].sum()
        df["weight"] = df["current_value"] / total * 100 if total > 0 else np.nan

    return df


def calculate_portfolio_lookthrough(position_detail: pd.DataFrame, token: str):
    if position_detail is None or position_detail.empty:
        return pd.DataFrame(), "无实仓", ""

    total_value = position_detail["current_value"].sum()
    if total_value <= 0:
        return pd.DataFrame(), "实仓市值无效", ""

    pieces = []
    errors = []

    for _, pos in position_detail.iterrows():
        code = clean_code(pos["code"])
        fund_weight = safe_num(pos["current_value"]) / total_value * 100

        comps, source, err = get_components_for_fund(code, token)
        if comps.empty:
            errors.append(f"{code} 无穿透数据：{err}")
            continue

        c = comps.copy()
        c["fund_code"] = code
        c["fund_name"] = pos["name"]
        c["fund_weight"] = fund_weight
        c["portfolio_exposure"] = fund_weight * c["weight"] / 100
        pieces.append(c)

    if not pieces:
        return pd.DataFrame(), "实仓穿透失败", "；".join(errors)

    all_df = pd.concat(pieces, ignore_index=True)

    grouped = (
        all_df.groupby(["stock_code", "stock_name"], as_index=False)
        .agg(
            exposure=("portfolio_exposure", "sum"),
            source_funds=("fund_code", lambda x: "、".join(sorted(set(x.astype(str))))),
        )
        .sort_values("exposure", ascending=False)
    )

    return grouped, "实仓底层穿透", "；".join(errors)


# ============================================================
# 图表
# ============================================================
def make_five_day_chart(df: pd.DataFrame, title: str):
    fig = go.Figure()

    if df is None or df.empty:
        fig.update_layout(
            title="未获取到真实五日行情",
            template="plotly_dark",
            height=420,
            paper_bgcolor="#0F172A",
            plot_bgcolor="#0F172A",
            font=dict(color="#F8FAFC"),
        )
        return fig

    d = df.copy().tail(5)
    d["five_day_return"] = (d["close"] / d["close"].iloc[0] - 1) * 100

    fig.add_trace(
        go.Scatter(
            x=d["date"],
            y=d["five_day_return"],
            mode="lines+markers",
            name="五日累计涨跌幅",
            line=dict(color="#58D5FF", width=3),
            marker=dict(size=8, color="#F8FAFC"),
            fill="tozeroy",
            fillcolor="rgba(88,213,255,0.16)",
        )
    )

    fig.add_hline(y=0, line_dash="dot", line_color="#94A3B8")

    fig.update_layout(
        title=title,
        template="plotly_dark",
        height=420,
        paper_bgcolor="#0F172A",
        plot_bgcolor="#0F172A",
        font=dict(color="#F8FAFC"),
        hovermode="x unified",
        margin=dict(l=30, r=30, t=60, b=30),
    )
    fig.update_xaxes(gridcolor="rgba(148,163,184,0.16)")
    fig.update_yaxes(title="五日累计涨跌幅/%", gridcolor="rgba(148,163,184,0.16)")
    return fig


def make_price_chart(df: pd.DataFrame, title: str):
    if df is None or df.empty:
        fig = go.Figure()
        fig.update_layout(
            title="未获取到真实行情",
            template="plotly_dark",
            height=620,
            paper_bgcolor="#0F172A",
            plot_bgcolor="#0F172A",
            font=dict(color="#F8FAFC"),
        )
        return fig

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.07,
        row_heights=[0.60, 0.22, 0.18],
        subplot_titles=("价格走势与均线", "成交额", "资金行为强度"),
    )

    fig.add_trace(go.Scatter(x=df["date"], y=df["close"], name="价格", line=dict(color="#F8FAFC", width=2.8)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["date"], y=df["ma5"], name="MA5", line=dict(color="#38BDF8", width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["date"], y=df["ma20"], name="MA20", line=dict(color="#FBBF24", width=1.6)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["date"], y=df["ma60"], name="MA60", line=dict(color="#A78BFA", width=1.6)), row=1, col=1)

    colors = np.where(df["pct_change"] >= 0, "#22C55E", "#EF4444")
    fig.add_trace(go.Bar(x=df["date"], y=df["amount"], name="成交额", marker_color=colors, opacity=0.72), row=2, col=1)
    fig.add_trace(go.Bar(x=df["date"], y=df["money_strength"], name="资金强度", marker_color=colors, opacity=0.75), row=3, col=1)
    fig.add_hline(y=0, line_width=1, line_dash="dot", line_color="#94A3B8", row=3, col=1)

    fig.update_layout(
        title=title,
        height=820,
        template="plotly_dark",
        plot_bgcolor="#0F172A",
        paper_bgcolor="#0F172A",
        font=dict(color="#F8FAFC", size=13),
        hovermode="x unified",
        legend=dict(orientation="h", y=1.08, x=0, bgcolor="rgba(15,23,42,0.78)"),
        margin=dict(l=28, r=28, t=95, b=35),
    )
    fig.update_xaxes(gridcolor="rgba(148,163,184,0.16)")
    fig.update_yaxes(gridcolor="rgba(148,163,184,0.16)")
    return fig


def make_contribution_bar(look_df: pd.DataFrame):
    fig = go.Figure()

    if look_df is None or look_df.empty:
        fig.update_layout(
            title="未获取到穿透贡献数据",
            template="plotly_dark",
            height=460,
            paper_bgcolor="#0F172A",
            plot_bgcolor="#0F172A",
            font=dict(color="#F8FAFC"),
        )
        return fig

    d = look_df.copy().sort_values("contribution_pct", ascending=True).tail(15)
    colors = np.where(d["contribution_pct"] >= 0, "#22C55E", "#EF4444")

    fig.add_trace(
        go.Bar(
            x=d["contribution_pct"],
            y=d["stock_name"],
            orientation="h",
            marker_color=colors,
            text=d["contribution_pct"].map(lambda x: f"{x:.3f}%"),
            textposition="auto",
            name="贡献度",
        )
    )

    fig.update_layout(
        title="成分股实时贡献度 Top 15",
        template="plotly_dark",
        height=520,
        paper_bgcolor="#0F172A",
        plot_bgcolor="#0F172A",
        font=dict(color="#F8FAFC"),
        margin=dict(l=30, r=30, t=60, b=30),
    )
    fig.update_xaxes(title="贡献度/%", gridcolor="rgba(148,163,184,0.16)")
    fig.update_yaxes(gridcolor="rgba(148,163,184,0.16)")
    return fig


def make_treemap(look_df: pd.DataFrame):
    fig = go.Figure()

    if look_df is None or look_df.empty:
        fig.update_layout(
            title="未获取到穿透热力图数据",
            template="plotly_dark",
            height=520,
            paper_bgcolor="#0F172A",
            plot_bgcolor="#0F172A",
            font=dict(color="#F8FAFC"),
        )
        return fig

    d = look_df.copy().head(50)
    d["color_value"] = d["contribution_pct"].fillna(0)

    fig = go.Figure(
        go.Treemap(
            labels=d["stock_name"],
            parents=[""] * len(d),
            values=d["weight"].clip(lower=0.01),
            marker=dict(
                colors=d["color_value"],
                colorscale=[[0, "#EF4444"], [0.5, "#0F172A"], [1, "#22C55E"]],
                cmid=0,
                line=dict(color="rgba(255,255,255,0.18)", width=1),
            ),
            textinfo="label+value",
            hovertemplate="股票：%{label}<br>权重：%{value:.2f}%<extra></extra>",
        )
    )

    fig.update_layout(
        title="成分股权重与贡献热力图",
        template="plotly_dark",
        height=520,
        paper_bgcolor="#0F172A",
        plot_bgcolor="#0F172A",
        font=dict(color="#F8FAFC"),
        margin=dict(l=10, r=10, t=60, b=10),
    )
    return fig


# ============================================================
# 侧边栏
# ============================================================
token = get_tushare_token()

st.sidebar.markdown("## 📊 基金智能分析平台")
st.sidebar.caption("Tushare Pro稳定数据源版")

page = st.sidebar.radio(
    "功能导航",
    ["基金分析", "场内实时穿透", "实盘导入与计算", "市场模块", "自定义搜索"],
    index=0,
)

st.sidebar.divider()

module_name = st.sidebar.selectbox("选择市场模块", list(FUND_MODULES.keys()), index=2)
module_items = FUND_MODULES[module_name]
selected_name = st.sidebar.selectbox("选择模块基金", list(module_items.keys()), index=0)

manual_mode = st.sidebar.checkbox("用户自查：输入任意6位场内基金代码", value=False)
if manual_mode:
    selected_code = clean_code(st.sidebar.text_input("输入代码", value=module_items[selected_name]))
    selected_display_name = f"自查基金 {selected_code}"
else:
    selected_code = module_items[selected_name]
    selected_display_name = selected_name

days = st.sidebar.slider("历史周期", 80, 520, 240, 20)

auto_refresh = st.sidebar.checkbox("交易时段自动刷新", value=False)

if st.sidebar.button("清理缓存并刷新"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.caption(f"北京时间：{now_text()}")

if is_china_trading_time():
    st.sidebar.success("A股交易时段：实时刷新")
elif is_pre_market_time():
    st.sidebar.info("盘前时段")
else:
    st.sidebar.warning("非交易时段：实时行情可能不更新")

if not token:
    st.sidebar.error("未配置 TUSHARE_TOKEN")


# ============================================================
# 顶部
# ============================================================
st.markdown('<div class="main-title">FundPilot Pro ｜ 基金智能分析平台</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">实盘导入 · Tushare实时行情 · 五日曲线 · 场内实时穿透 · 底层资产暴露</div>',
    unsafe_allow_html=True,
)

if not token:
    st.markdown(
        """
        <div class="status-danger">
        未检测到 TUSHARE_TOKEN。请在 Streamlit Cloud 的 Secrets 中加入：<br>
        TUSHARE_TOKEN = "你的Tushare Pro Token"
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()


# ============================================================
# 全局数据
# ============================================================
positions = load_positions()

start_date = (china_now() - dt.timedelta(days=days * 2)).strftime("%Y%m%d")
end_date = trade_date_today()

rt_df, rt_source, rt_error = fetch_tushare_etf_realtime(selected_code, token)
hist_df, hist_source, hist_error = fetch_tushare_etf_daily(selected_code, start_date, end_date, token)

merge_note = ""
if not hist_df.empty and not rt_df.empty:
    hist_df, merge_note = merge_realtime_into_history(hist_df, rt_df)

hist_df = enrich_indicators(hist_df)
summary = compute_summary(hist_df)
latest = hist_df.iloc[-1] if not hist_df.empty else pd.Series(dtype="object")

fund_name = selected_display_name
if not rt_df.empty:
    try:
        fund_name = str(rt_df.iloc[0].get("name", selected_display_name))
    except Exception:
        pass

if rt_error or hist_error:
    st.markdown(
        f'<div class="status-warn">数据提示：{rt_source}；{rt_error}；{hist_source}；{hist_error}</div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f'<div class="status-ok">数据源正常：{rt_source}；{hist_source}；{merge_note}</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# 基金分析
# ============================================================
if page == "基金分析":
    if hist_df.empty:
        st.error("未获取到该基金真实行情。请检查 Tushare 权限、Token 或基金代码。")
        st.stop()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("基金名称", fund_name)
    c2.metric("最新价", f"{safe_num(latest['close']):.4f}")
    c3.metric("最新涨跌幅", format_pct(latest["pct_change"]))
    c4.metric("成交额", format_money(latest["amount"]))
    c5.metric("趋势评分", f"{summary['trend_score']} / 5")

    c6, c7, c8, c9, c10 = st.columns(5)
    c6.metric("趋势状态", summary["trend_label"])
    c7.metric("风险状态", summary["risk_label"])
    c8.metric("策略提示", summary["action"])
    c9.metric("MA20偏离", format_pct(latest["ma20_dev"]))
    c10.metric("北京时间", now_text())

    st.markdown(
        f"""
        <div class="panel">
            <div class="panel-title">{fund_name}（{selected_code}）</div>
            <div class="panel-subtitle">
            当前模块：{module_name}；最新数据日期：{pd.to_datetime(latest['date']).strftime('%Y-%m-%d')}；
            数据源：{hist_source}；{merge_note}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab1, tab2, tab3 = st.tabs(["📈 五日曲线", "📊 专业趋势图", "🧠 专业解读"])

    with tab1:
        st.plotly_chart(make_five_day_chart(hist_df, f"{fund_name} 五日曲线"), use_container_width=True)

    with tab2:
        st.plotly_chart(make_price_chart(hist_df, f"{fund_name} 真实行情趋势分析"), use_container_width=True)

    with tab3:
        st.markdown(
            f"""
            <div class="signal-card">
                <div class="signal-title">专业解读</div>
                <div class="signal-text">{summary["comment"]}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# 场内实时穿透
# ============================================================
elif page == "场内实时穿透":
    st.markdown(
        f"""
        <div class="panel">
            <div class="panel-title">{fund_name}（{selected_code}）场内实时穿透</div>
            <div class="panel-subtitle">
            计算逻辑：ETF实时行情 + PCF/成分权重 + 成分股实时行情 → 实时估算涨跌、贡献度与底层暴露。
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="status-warn">
        精确穿透建议上传当日PCF/成分清单；若未上传，将使用Tushare基金季度持仓作为兜底，季度持仓不等于当日ETF申赎清单。
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded_comp = st.file_uploader(
        "上传PCF/成分清单 Excel或CSV",
        type=["xlsx", "xls", "csv"],
        help="推荐字段：基金代码、股票代码、股票名称、权重、行业。权重填写百分数，如8.5。",
    )

    if uploaded_comp is not None:
        try:
            if uploaded_comp.name.lower().endswith(".csv"):
                raw_comp = pd.read_csv(uploaded_comp)
            else:
                raw_comp = pd.read_excel(uploaded_comp)

            comp_df = normalize_components(raw_comp, default_fund_code=selected_code)

            if comp_df.empty:
                st.error("未识别到有效成分数据，请检查列名。")
            else:
                old = load_components()
                old = old[old["fund_code"] != clean_code(selected_code)]
                new_all = pd.concat([old, comp_df], ignore_index=True)
                save_components(new_all)
                st.success(f"已导入 {len(comp_df)} 条成分/PCF数据")
                st.rerun()

        except Exception as e:
            st.error(f"导入失败：{e}")

    look_df, look_source, look_error = calculate_lookthrough(selected_code, token)

    etf_pct = safe_num(latest.get("pct_change"), np.nan)
    estimated_pct = look_df["contribution_pct"].sum() if not look_df.empty else np.nan
    gap = etf_pct - estimated_pct if pd.notna(etf_pct) and pd.notna(estimated_pct) else np.nan
    concentration10 = look_df.head(10)["weight"].sum() if not look_df.empty else np.nan

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("ETF场内涨跌", format_pct(etf_pct))
    c2.metric("底层估算涨跌", format_pct(estimated_pct))
    c3.metric("估算偏离", format_pct(gap))
    c4.metric("成分数量", len(look_df))
    c5.metric("前10集中度", format_pct(concentration10))

    c6, c7, c8 = st.columns(3)
    c6.metric("穿透数据源", look_source)
    c7.metric("更新时间", now_text())
    c8.metric("Token状态", "已配置")

    if look_error:
        st.warning(f"穿透提示：{look_error}")

    tab1, tab2, tab3, tab4 = st.tabs(["📈 五日曲线", "🧬 贡献度", "🔥 热力图", "📋 成分明细"])

    with tab1:
        st.plotly_chart(make_five_day_chart(hist_df, f"{fund_name} 五日场内走势"), use_container_width=True)

    with tab2:
        st.plotly_chart(make_contribution_bar(look_df), use_container_width=True)

        if not look_df.empty:
            max_pos = look_df.sort_values("contribution_pct", ascending=False).iloc[0]
            max_neg = look_df.sort_values("contribution_pct", ascending=True).iloc[0]

            st.markdown(
                f"""
                <div class="signal-card">
                    <div class="signal-title">实时贡献解读</div>
                    <div class="signal-text">
                    最大正贡献：<span class="good">{max_pos['stock_name']}</span>，
                    权重 {max_pos['weight']:.2f}%，涨跌 {max_pos['pct_change']:.2f}%，贡献 {max_pos['contribution_pct']:.3f}%。<br>
                    最大负贡献：<span class="bad">{max_neg['stock_name']}</span>，
                    权重 {max_neg['weight']:.2f}%，涨跌 {max_neg['pct_change']:.2f}%，贡献 {max_neg['contribution_pct']:.3f}%。<br>
                    ETF场内涨跌与底层估算涨跌之差为 {gap:.3f}%。
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with tab3:
        st.plotly_chart(make_treemap(look_df), use_container_width=True)

    with tab4:
        if look_df.empty:
            st.error("未获取到穿透明细。请上传PCF/成分清单，或检查Tushare基金持仓权限。")
        else:
            show = look_df.copy()
            show["权重"] = show["weight"].apply(format_pct)
            show["实时涨跌"] = show["pct_change"].apply(format_pct)
            show["贡献度"] = show["contribution_pct"].map(lambda x: f"{x:.4f}%")
            show["成交额"] = show["amount"].apply(format_money)

            show = show.rename(
                columns={
                    "stock_code": "股票代码",
                    "stock_name": "股票名称",
                    "industry": "行业",
                    "price": "现价",
                    "trade_time": "行情时间",
                    "source_x": "权重来源",
                }
            )

            keep_cols = ["股票代码", "股票名称", "行业", "权重", "现价", "实时涨跌", "贡献度", "成交额", "行情时间"]
            keep_cols = [c for c in keep_cols if c in show.columns]
            st.dataframe(show[keep_cols], use_container_width=True, height=620, hide_index=True)


# ============================================================
# 实盘导入与计算
# ============================================================
elif page == "实盘导入与计算":
    st.markdown(
        """
        <div class="panel">
            <div class="panel-title">实盘导入与实时计算</div>
            <div class="panel-subtitle">
            支持Excel/CSV导入实仓，实时计算持仓市值、盈亏、仓位占比，并进一步做底层股票穿透。
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded_pos = st.file_uploader(
        "上传实盘文件",
        type=["xlsx", "xls", "csv"],
        help="推荐字段：基金代码、基金名称、持有份额、持仓成本、买入日期、账户类型、备注。",
    )

    if uploaded_pos is not None:
        try:
            if uploaded_pos.name.lower().endswith(".csv"):
                raw_pos = pd.read_csv(uploaded_pos)
            else:
                raw_pos = pd.read_excel(uploaded_pos)

            pos = normalize_positions(raw_pos)
            save_positions(pos)
            st.success(f"已导入 {len(pos)} 条实盘持仓")
            st.rerun()
        except Exception as e:
            st.error(f"导入失败：{e}")

    positions = load_positions()

    st.subheader("实盘编辑器")
    edited = st.data_editor(
        positions,
        use_container_width=True,
        num_rows="dynamic",
        height=300,
        column_config={
            "code": st.column_config.TextColumn("基金代码"),
            "name": st.column_config.TextColumn("基金名称"),
            "shares": st.column_config.NumberColumn("持有份额", min_value=0.0, step=100.0),
            "cost_price": st.column_config.NumberColumn("持仓成本", min_value=0.0, step=0.001, format="%.4f"),
            "buy_date": st.column_config.TextColumn("买入日期"),
            "account_type": st.column_config.TextColumn("账户类型"),
            "notes": st.column_config.TextColumn("备注"),
        },
    )

    if st.button("保存实盘"):
        pos = normalize_positions(edited)
        save_positions(pos)
        st.success("实盘已保存")
        st.rerun()

    positions = normalize_positions(edited)
    pos_detail = compute_position_detail(positions, token)

    if pos_detail.empty:
        st.info("暂无实盘数据。请导入或手动录入。")
    else:
        total_asset = pos_detail["current_value"].sum()
        total_cost = pos_detail["cost_value"].sum()
        profit = total_asset - total_cost
        profit_rate = profit / total_cost * 100 if total_cost > 0 else np.nan

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("组合当前市值", format_money(total_asset))
        c2.metric("投入成本", format_money(total_cost))
        c3.metric("浮动盈亏", format_money(profit), format_pct(profit_rate))
        c4.metric("最大单只仓位", format_pct(pos_detail["weight"].max()))

        show = pos_detail.copy()
        show["当前市值"] = show["current_value"].apply(format_money)
        show["成本金额"] = show["cost_value"].apply(format_money)
        show["浮盈亏"] = show["profit"].apply(format_money)
        show["收益率"] = show["profit_rate"].apply(format_pct)
        show["仓位占比"] = show["weight"].apply(format_pct)

        show = show.rename(
            columns={
                "code": "代码",
                "name": "名称",
                "shares": "份额",
                "cost_price": "成本价",
                "current_price": "当前价",
                "price_source": "价格来源",
                "buy_date": "买入日期",
            }
        )

        keep = ["代码", "名称", "份额", "成本价", "当前价", "当前市值", "成本金额", "浮盈亏", "收益率", "仓位占比", "价格来源", "买入日期"]
        st.dataframe(show[keep], use_container_width=True, height=460, hide_index=True)

        st.subheader("实盘底层股票穿透")

        portfolio_lt, p_source, p_error = calculate_portfolio_lookthrough(pos_detail, token)

        if portfolio_lt.empty:
            st.warning(f"暂未形成实盘底层穿透：{p_error}")
        else:
            st.success("已根据实盘仓位与基金成分权重计算底层股票暴露。")

            stock_quotes, sq_source, sq_error = fetch_tushare_stock_realtime(tuple(portfolio_lt["stock_code"].tolist()), token)
            merged = portfolio_lt.merge(stock_quotes, on="stock_code", how="left")
            merged["realtime_contribution"] = merged["exposure"] / 100 * merged["pct_change"]

            table = merged.copy()
            table["底层暴露"] = table["exposure"].apply(format_pct)
            table["实时涨跌"] = table["pct_change"].apply(format_pct)
            table["组合贡献"] = table["realtime_contribution"].map(lambda x: f"{x:.4f}%" if pd.notna(x) else "暂无")

            table = table.rename(
                columns={
                    "stock_code": "股票代码",
                    "stock_name": "股票名称",
                    "source_funds": "来源基金",
                    "price": "现价",
                }
            )

            keep2 = ["股票代码", "股票名称", "底层暴露", "现价", "实时涨跌", "组合贡献", "来源基金"]
            st.dataframe(table[keep2].head(100), use_container_width=True, height=560, hide_index=True)


# ============================================================
# 市场模块
# ============================================================
elif page == "市场模块":
    st.markdown(
        f"""
        <div class="panel">
            <div class="panel-title">{module_name} 模块行情</div>
            <div class="panel-subtitle">模块内基金列表。点击左侧切换基金后进入基金分析或穿透分析。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    rows = []
    for name, code in module_items.items():
        rt_one, src, err = fetch_tushare_etf_realtime(code, token)
        if rt_one.empty:
            rows.append(
                {
                    "模块": module_name,
                    "名称": name,
                    "代码": code,
                    "最新价": np.nan,
                    "涨跌幅": np.nan,
                    "成交额": np.nan,
                    "数据源": src,
                    "错误": err,
                }
            )
        else:
            r = rt_one.iloc[0]
            rows.append(
                {
                    "模块": module_name,
                    "名称": r.get("name", name),
                    "代码": code,
                    "最新价": safe_num(r.get("close")),
                    "涨跌幅": safe_num(r.get("pct_change")),
                    "成交额": safe_num(r.get("amount")),
                    "数据源": src,
                    "错误": err,
                }
            )

    module_df = pd.DataFrame(rows)
    show = module_df.copy()
    show["涨跌幅"] = show["涨跌幅"].apply(format_pct)
    show["成交额"] = show["成交额"].apply(format_money)
    st.dataframe(show, use_container_width=True, height=420, hide_index=True)

    all_rows = []
    for m, items in FUND_MODULES.items():
        for n, c in items.items():
            all_rows.append({"模块": m, "名称": n, "代码": c})

    st.subheader("全模块基金清单")
    st.dataframe(pd.DataFrame(all_rows), use_container_width=True, height=520, hide_index=True)


# ============================================================
# 自定义搜索
# ============================================================
elif page == "自定义搜索":
    st.markdown(
        """
        <div class="panel">
            <div class="panel-title">自定义搜索</div>
            <div class="panel-subtitle">输入基金代码、名称或模块关键词。若没有预设，直接输入6位场内基金代码自查。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    keyword = st.text_input("搜索基金", placeholder="例如：515030、新能源、半导体、518880、513100")

    all_rows = []
    for m, items in FUND_MODULES.items():
        for n, c in items.items():
            all_rows.append({"模块": m, "名称": n, "代码": c})

    all_df = pd.DataFrame(all_rows)

    if keyword:
        kw = keyword.strip()
        result = all_df[
            all_df["模块"].str.contains(kw, case=False, na=False)
            | all_df["名称"].str.contains(kw, case=False, na=False)
            | all_df["代码"].astype(str).str.contains(kw, case=False, na=False)
        ]

        if result.empty and kw.isdigit() and len(kw) == 6:
            result = pd.DataFrame([{"模块": "用户自查", "名称": f"自查基金{kw}", "代码": kw}])

        if result.empty:
            st.warning("未找到结果。若是基金代码，请输入完整6位代码。")
        else:
            st.dataframe(result, use_container_width=True, height=420, hide_index=True)

            if kw.isdigit() and len(kw) == 6:
                st.info("请在左侧勾选“用户自查”，输入该6位代码，即可进入基金分析与场内穿透页面。")
    else:
        st.info("请输入基金代码、名称或模块关键词。")


# ============================================================
# 自动刷新
# ============================================================
if auto_refresh:
    if is_china_trading_time():
        time.sleep(15)
        st.rerun()
    elif is_pre_market_time():
        time.sleep(60)
        st.rerun()
    else:
        st.info("当前为中国非交易时段，已暂停自动刷新。")
