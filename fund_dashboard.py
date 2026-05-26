import io
import re
import json
import time
import math
import datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots


# ============================================================
# 基础设置
# ============================================================
st.set_page_config(
    page_title="基金智能分析平台",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

CHINA_TZ = ZoneInfo("Asia/Shanghai")
CACHE_DIR = Path(".fund_live_cache")
CACHE_DIR.mkdir(exist_ok=True)
POSITION_FILE = CACHE_DIR / "positions.csv"
COMPONENT_FILE = CACHE_DIR / "components.csv"


# ============================================================
# 界面样式
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
        radial-gradient(circle at top right, rgba(20, 184, 166, 0.13), transparent 22%),
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
button[data-baseweb="tab"] {
    color: #CFE0F5 !important;
    font-weight: 760 !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #FFFFFF !important;
}
button[data-baseweb="tab-highlight"] {
    background: linear-gradient(90deg, #38BDF8, #60A5FA) !important;
    height: 3px !important;
    border-radius: 999px !important;
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
div[role="listbox"] {
    background: #0D1630 !important;
    border: 1px solid rgba(88,213,255,0.25) !important;
    border-radius: 14px !important;
}
div[role="option"] {
    color: #ECF4FF !important;
    background: transparent !important;
}
div[role="option"]:hover {
    background: rgba(88,213,255,0.12) !important;
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
# 市场模块池
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
        "石油基金": "162719",
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
for module, items in FUND_MODULES.items():
    ALL_FUNDS.update(items)


# ============================================================
# 工具函数
# ============================================================
def china_now():
    return dt.datetime.now(CHINA_TZ)


def now_text():
    return china_now().strftime("%Y-%m-%d %H:%M:%S")


def is_china_trading_time():
    now = china_now()
    if now.weekday() >= 5:
        return False
    t = now.time()
    return (dt.time(9, 30) <= t <= dt.time(11, 30)) or (dt.time(13, 0) <= t <= dt.time(15, 0))


def is_pre_market_time():
    now = china_now()
    if now.weekday() >= 5:
        return False
    return dt.time(9, 0) <= now.time() < dt.time(9, 30)


def clean_code(code):
    text = str(code).strip().replace(".0", "")
    digits = re.sub(r"\D", "", text)
    if not digits:
        return ""
    return digits.zfill(6)[-6:]


def safe_num(x, default=np.nan):
    try:
        if pd.isna(x):
            return default
        if isinstance(x, str):
            x = x.replace("%", "").replace(",", "").strip()
        return float(x)
    except Exception:
        return default


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


def is_exchange_fund(code):
    code = clean_code(code)
    return code.startswith(
        (
            "15", "16", "18",
            "50", "51", "52", "53", "56", "58",
            "159", "160", "161", "162", "163", "164", "165", "166", "167", "168", "169",
            "511",
        )
    )


def detect_market(code):
    code = clean_code(code)
    if code.startswith(("5", "6", "9")):
        return "SH"
    return "SZ"


def stock_market(code):
    code = clean_code(code)
    if code.startswith(("6", "5", "9")):
        return "SH"
    return "SZ"


def secid_for_fund(code):
    code = clean_code(code)
    return f"1.{code}" if detect_market(code) == "SH" else f"0.{code}"


def secid_for_stock(code):
    code = clean_code(code)
    return f"1.{code}" if stock_market(code) == "SH" else f"0.{code}"


def request_get(url, params=None, timeout=8, text=False):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json,text/plain,*/*",
        "Referer": "https://quote.eastmoney.com/",
    }
    r = requests.get(url, params=params, headers=headers, timeout=timeout)
    r.raise_for_status()
    if text:
        r.encoding = "utf-8"
        return r.text
    return r.json()


# ============================================================
# 东方财富真实行情：基金/ETF
# ============================================================
@st.cache_data(ttl=10, show_spinner=False)
def fetch_exchange_spot(codes_tuple):
    codes = [clean_code(c) for c in list(codes_tuple) if clean_code(c)]
    codes = [c for c in dict.fromkeys(codes) if is_exchange_fund(c)]

    if not codes:
        return pd.DataFrame(), "无场内实时代码", ""

    url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
    params = {
        "fltt": "2",
        "secids": ",".join(secid_for_fund(c) for c in codes),
        "fields": "f12,f14,f2,f3,f4,f5,f6",
        "_": int(time.time() * 1000),
    }

    try:
        data = request_get(url, params=params, timeout=6)
        diff = data.get("data", {}).get("diff", [])
        rows = []
        for item in diff:
            rows.append(
                {
                    "code": clean_code(item.get("f12", "")),
                    "name": item.get("f14", ""),
                    "price": safe_num(item.get("f2")),
                    "pct_change": safe_num(item.get("f3")),
                    "change": safe_num(item.get("f4")),
                    "volume": safe_num(item.get("f5")),
                    "amount": safe_num(item.get("f6")),
                    "update_time": now_text(),
                    "source": "东方财富场内实时行情",
                }
            )
        df = pd.DataFrame(rows)
        if df.empty:
            return pd.DataFrame(), "场内实时行情为空", "接口返回为空"
        return df, "东方财富场内实时行情", ""
    except Exception as e:
        return pd.DataFrame(), "场内实时行情获取失败", str(e)


@st.cache_data(ttl=60, show_spinner=False)
def fetch_exchange_history(code, days=240):
    code = clean_code(code)
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "secid": secid_for_fund(code),
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",
        "fqt": "0",
        "beg": "20000101",
        "end": china_now().strftime("%Y%m%d"),
        "lmt": str(max(days * 2, 600)),
        "_": int(time.time() * 1000),
    }

    try:
        data = request_get(url, params=params, timeout=8)
        klines = data.get("data", {}).get("klines", [])
        rows = []
        for line in klines:
            p = line.split(",")
            if len(p) < 9:
                continue
            rows.append(
                {
                    "date": p[0],
                    "open": safe_num(p[1]),
                    "close": safe_num(p[2]),
                    "high": safe_num(p[3]),
                    "low": safe_num(p[4]),
                    "volume": safe_num(p[5]),
                    "amount": safe_num(p[6]),
                    "pct_change": safe_num(p[8]),
                    "source": "东方财富场内历史K线",
                }
            )
        df = pd.DataFrame(rows)
        if df.empty:
            return pd.DataFrame(), "场内历史K线为空", "接口返回为空"
        df["date"] = pd.to_datetime(df["date"])
        return df.sort_values("date").tail(days).reset_index(drop=True), "东方财富场内历史K线", ""
    except Exception as e:
        return pd.DataFrame(), "场内历史K线获取失败", str(e)


def apply_spot_to_history(history, spot_row):
    if history is None or history.empty or spot_row is None:
        return history, ""

    price = safe_num(spot_row.get("price"))
    pct = safe_num(spot_row.get("pct_change"))
    amount = safe_num(spot_row.get("amount"))
    volume = safe_num(spot_row.get("volume"))

    if pd.isna(price) or price <= 0:
        return history, "实时价格无效，未更新K线"

    df = history.copy()
    today = pd.Timestamp(china_now().date())
    last_date = pd.to_datetime(df.iloc[-1]["date"]).normalize()

    if last_date == today:
        idx = df.index[-1]
        old_high = safe_num(df.loc[idx, "high"], price)
        old_low = safe_num(df.loc[idx, "low"], price)
        df.loc[idx, "close"] = price
        df.loc[idx, "pct_change"] = pct if pd.notna(pct) else df.loc[idx, "pct_change"]
        df.loc[idx, "amount"] = amount if pd.notna(amount) and amount > 0 else df.loc[idx, "amount"]
        df.loc[idx, "volume"] = volume if pd.notna(volume) and volume > 0 else df.loc[idx, "volume"]
        df.loc[idx, "high"] = max(old_high, price)
        df.loc[idx, "low"] = min(old_low, price)
        df.loc[idx, "source"] = "东方财富实时快照更新"
        return df, f"已用实时快照更新今日K线：{now_text()}"

    last_close = safe_num(df.iloc[-1]["close"], price)
    open_price = last_close if pd.notna(last_close) and last_close > 0 else price
    new_row = {
        "date": today,
        "open": open_price,
        "close": price,
        "high": max(open_price, price),
        "low": min(open_price, price),
        "volume": volume if pd.notna(volume) else 0,
        "amount": amount if pd.notna(amount) else 0,
        "pct_change": pct if pd.notna(pct) else ((price / open_price - 1) * 100 if open_price > 0 else 0),
        "source": "东方财富实时快照追加",
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    return df, f"历史K线未到今日，已用实时快照追加今日数据：{now_text()}"


# ============================================================
# 东方财富真实行情：股票实时行情
# ============================================================
@st.cache_data(ttl=10, show_spinner=False)
def fetch_stock_spot(stock_codes_tuple):
    codes = [clean_code(c) for c in list(stock_codes_tuple) if clean_code(c)]
    codes = list(dict.fromkeys(codes))

    if not codes:
        return pd.DataFrame(), "无股票代码", ""

    url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
    params = {
        "fltt": "2",
        "secids": ",".join(secid_for_stock(c) for c in codes),
        "fields": "f12,f14,f2,f3,f4,f5,f6",
        "_": int(time.time() * 1000),
    }

    try:
        data = request_get(url, params=params, timeout=8)
        diff = data.get("data", {}).get("diff", [])
        rows = []
        for item in diff:
            rows.append(
                {
                    "stock_code": clean_code(item.get("f12", "")),
                    "stock_name": item.get("f14", ""),
                    "price": safe_num(item.get("f2")),
                    "pct_change": safe_num(item.get("f3")),
                    "change": safe_num(item.get("f4")),
                    "volume": safe_num(item.get("f5")),
                    "amount": safe_num(item.get("f6")),
                    "quote_time": now_text(),
                    "quote_source": "东方财富股票实时行情",
                }
            )
        df = pd.DataFrame(rows)
        if df.empty:
            return pd.DataFrame(), "股票实时行情为空", "接口返回为空"
        return df, "东方财富股票实时行情", ""
    except Exception as e:
        return pd.DataFrame(), "股票实时行情获取失败", str(e)


# ============================================================
# 场内穿透：成分/持仓数据
# ============================================================
def normalize_component_columns(raw):
    if raw is None or raw.empty:
        return pd.DataFrame(columns=["fund_code", "stock_code", "stock_name", "weight", "industry", "source"])

    df = raw.copy()
    rename = {}

    for col in df.columns:
        c = str(col).strip()
        c_low = c.lower()

        if c in ["基金代码", "fund_code", "ETF代码", "etf_code"]:
            rename[col] = "fund_code"
        elif c in ["股票代码", "证券代码", "成分券代码", "stock_code", "code"]:
            rename[col] = "stock_code"
        elif c in ["股票名称", "证券简称", "证券名称", "成分券名称", "stock_name", "name"]:
            rename[col] = "stock_name"
        elif c in ["权重", "占净值比例", "占比", "weight", "比例", "持仓占比"] or "权重" in c or "比例" in c:
            rename[col] = "weight"
        elif c in ["行业", "申万行业", "industry"]:
            rename[col] = "industry"

    df = df.rename(columns=rename)

    for col in ["fund_code", "stock_code", "stock_name", "weight", "industry", "source"]:
        if col not in df.columns:
            df[col] = ""

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
        .replace({"": np.nan, "-": np.nan})
    )
    df["weight"] = pd.to_numeric(df["weight"], errors="coerce")

    # 如果权重是 0-1 小数，转为百分数；如果本来就是百分数，不动
    if df["weight"].dropna().max() is not None and df["weight"].dropna().max() <= 1.2:
        df["weight"] = df["weight"] * 100

    df = df[df["stock_code"].str.len() == 6].copy()
    df = df[df["weight"].notna()].copy()

    if "source" not in df.columns or df["source"].astype(str).str.strip().eq("").all():
        df["source"] = "用户导入成分/PCF"

    return df[["fund_code", "stock_code", "stock_name", "weight", "industry", "source"]].reset_index(drop=True)


def save_components(df):
    df.to_csv(COMPONENT_FILE, index=False, encoding="utf-8-sig")


def load_components():
    if COMPONENT_FILE.exists():
        try:
            return normalize_component_columns(pd.read_csv(COMPONENT_FILE))
        except Exception:
            return pd.DataFrame(columns=["fund_code", "stock_code", "stock_name", "weight", "industry", "source"])
    return pd.DataFrame(columns=["fund_code", "stock_code", "stock_name", "weight", "industry", "source"])


@st.cache_data(ttl=60 * 60, show_spinner=False)
def fetch_eastmoney_fund_holdings(code):
    """
    免费兜底：尝试从东方财富基金持仓页面读取披露持仓。
    这不是实时PCF，只是持仓披露数据；股票行情仍会实时更新。
    """
    code = clean_code(code)
    url = f"https://fundf10.eastmoney.com/ccmx_{code}.html"

    try:
        tables = pd.read_html(url)
    except Exception as e:
        return pd.DataFrame(), "东方财富基金持仓读取失败", str(e)

    candidates = []
    for table in tables:
        cols = [str(c) for c in table.columns]
        text = " ".join(cols)
        if ("股票代码" in text or "代码" in text) and ("占净值" in text or "比例" in text or "持仓" in text):
            candidates.append(table)

    if not candidates:
        return pd.DataFrame(), "未找到基金持仓表", "页面未解析到持仓表"

    raw = candidates[0].copy()
    rename = {}
    for col in raw.columns:
        c = str(col)
        if "股票代码" in c or c == "代码":
            rename[col] = "stock_code"
        elif "股票名称" in c or "股票简称" in c or c == "名称":
            rename[col] = "stock_name"
        elif "占净值" in c or "比例" in c or "持仓占比" in c:
            rename[col] = "weight"
    raw = raw.rename(columns=rename)

    if "stock_code" not in raw.columns:
        # 尝试从任意列中提取6位股票代码
        for col in raw.columns:
            tmp = raw[col].astype(str).str.extract(r"(\d{6})")[0]
            if tmp.notna().sum() >= 3:
                raw["stock_code"] = tmp
                break

    if "stock_name" not in raw.columns:
        raw["stock_name"] = ""

    if "weight" not in raw.columns:
        return pd.DataFrame(), "未找到权重列", "持仓表无权重字段"

    raw["fund_code"] = code
    raw["industry"] = ""
    raw["source"] = "东方财富基金持仓披露"
    out = normalize_component_columns(raw)

    if out.empty:
        return pd.DataFrame(), "持仓表解析为空", "持仓代码或权重解析失败"

    return out, "东方财富基金持仓披露", ""


def get_components_for_fund(code):
    code = clean_code(code)
    uploaded_components = load_components()
    hit = uploaded_components[uploaded_components["fund_code"] == code].copy()

    if not hit.empty:
        return hit, "用户导入PCF/成分清单", ""

    east_df, source, error = fetch_eastmoney_fund_holdings(code)
    if not east_df.empty:
        return east_df, source, error

    return pd.DataFrame(columns=["fund_code", "stock_code", "stock_name", "weight", "industry", "source"]), source, error


def calculate_lookthrough(fund_code, components):
    if components is None or components.empty:
        return pd.DataFrame(), "无成分数据", "请导入PCF/成分清单，或检查东方财富持仓披露是否可读取"

    stock_codes = components["stock_code"].dropna().astype(str).unique().tolist()
    stock_quotes, quote_source, quote_error = fetch_stock_spot(tuple(stock_codes))

    if stock_quotes.empty:
        return pd.DataFrame(), quote_source, quote_error

    df = components.merge(stock_quotes, on="stock_code", how="left", suffixes=("", "_quote"))
    df["stock_name"] = np.where(
        df["stock_name"].astype(str).str.strip() == "",
        df["stock_name_quote"],
        df["stock_name"],
    )

    df["weight"] = pd.to_numeric(df["weight"], errors="coerce")
    df["pct_change"] = pd.to_numeric(df["pct_change"], errors="coerce")
    df["contribution_pct"] = df["weight"] / 100 * df["pct_change"]

    df = df.sort_values("contribution_pct", ascending=False).reset_index(drop=True)
    return df, quote_source, quote_error


def calculate_portfolio_lookthrough(position_detail):
    if position_detail is None or position_detail.empty:
        return pd.DataFrame(), "无实仓", ""

    total_value = position_detail["current_value"].sum()
    if total_value <= 0:
        return pd.DataFrame(), "实仓市值无效", ""

    rows = []
    messages = []

    for _, pos in position_detail.iterrows():
        fund_code = clean_code(pos["code"])
        fund_weight = safe_num(pos["current_value"]) / total_value * 100

        comps, comp_source, comp_error = get_components_for_fund(fund_code)
        if comps.empty:
            messages.append(f"{fund_code} 无穿透数据")
            continue

        comps = comps.copy()
        comps["fund_code"] = fund_code
        comps["fund_name"] = pos["name"]
        comps["fund_weight"] = fund_weight
        comps["portfolio_exposure"] = fund_weight * comps["weight"] / 100
        rows.append(comps)

    if not rows:
        return pd.DataFrame(), "实仓穿透失败", "；".join(messages)

    all_df = pd.concat(rows, ignore_index=True)
    grouped = (
        all_df.groupby(["stock_code", "stock_name"], as_index=False)
        .agg(
            exposure=("portfolio_exposure", "sum"),
            source_funds=("fund_code", lambda x: "、".join(sorted(set(x.astype(str))))),
        )
        .sort_values("exposure", ascending=False)
    )
    return grouped, "实仓底层穿透", "；".join(messages)


# ============================================================
# 指标与图表
# ============================================================
def enrich_indicators(df):
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    for col in ["open", "close", "high", "low", "volume", "amount", "pct_change"]:
        if col not in df.columns:
            df[col] = np.nan
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["close"] = df["close"].ffill().bfill()
    df["pct_change"] = df["pct_change"].fillna(df["close"].pct_change() * 100).fillna(0)
    df["amount"] = df["amount"].fillna(0)
    df["volume"] = df["volume"].fillna(0)

    df["ma5"] = df["close"].rolling(5, min_periods=2).mean()
    df["ma10"] = df["close"].rolling(10, min_periods=3).mean()
    df["ma20"] = df["close"].rolling(20, min_periods=5).mean()
    df["ma60"] = df["close"].rolling(60, min_periods=10).mean()

    df["amount_ma20"] = df["amount"].rolling(20, min_periods=5).mean()
    df["volume_ratio"] = np.where(df["amount_ma20"] > 0, df["amount"] / df["amount_ma20"], np.nan)

    df["ma5_dev"] = (df["close"] / df["ma5"] - 1) * 100
    df["ma20_dev"] = (df["close"] / df["ma20"] - 1) * 100
    df["ma60_dev"] = (df["close"] / df["ma60"] - 1) * 100

    df["money_strength"] = df["pct_change"] * df["amount"] / 1e8
    return df


def compute_summary(df):
    if df is None or df.empty:
        return {
            "trend_score": 0,
            "trend_label": "无数据",
            "risk_label": "无法判断",
            "action": "等待真实数据",
            "comment": "未获取到真实行情，无法分析。",
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

    bias20 = safe_num(latest["ma20_dev"])
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
        f"当前趋势评分为 {score}/5，处于“{trend}”状态。"
        f"价格相对MA20偏离 {bias20:.2f}% ，风险位置为“{risk}”。"
        f"若实时穿透估算涨跌明显低于ETF场内涨跌，需要观察是否存在溢价或追涨情绪。"
        f"当前策略更偏向“{action}”。"
    )

    return {
        "trend_score": score,
        "trend_label": trend,
        "risk_label": risk,
        "action": action,
        "comment": comment,
    }


def make_five_day_chart(df, title):
    if df is None or df.empty:
        fig = go.Figure()
        fig.update_layout(
            title="未获取到真实五日数据",
            template="plotly_dark",
            height=420,
            paper_bgcolor="#0F172A",
            plot_bgcolor="#0F172A",
            font=dict(color="#F8FAFC"),
        )
        return fig

    d = df.copy().tail(5)
    d["base"] = d["close"].iloc[0]
    d["five_day_return"] = (d["close"] / d["base"] - 1) * 100

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=d["date"],
            y=d["five_day_return"],
            mode="lines+markers",
            name="五日涨跌幅",
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


def make_price_chart(df, title):
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
    fig.add_trace(go.Bar(x=df["date"], y=df["amount"] / 1e8, name="成交额/亿", marker_color=colors, opacity=0.72), row=2, col=1)
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


def make_contribution_bar(look_df):
    if look_df is None or look_df.empty:
        fig = go.Figure()
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

    fig = go.Figure()
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


def make_treemap(look_df):
    if look_df is None or look_df.empty:
        fig = go.Figure()
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
# 实仓处理
# ============================================================
def normalize_positions(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=["code", "name", "shares", "cost_price", "buy_date", "account_type", "notes"])

    df = df.copy()
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
    df["shares"] = pd.to_numeric(df["shares"], errors="coerce").fillna(0)
    df["cost_price"] = pd.to_numeric(df["cost_price"], errors="coerce").fillna(0)
    df["name"] = df["name"].astype(str)

    return df[df["code"].str.len() == 6][["code", "name", "shares", "cost_price", "buy_date", "account_type", "notes"]]


def load_positions():
    if POSITION_FILE.exists():
        try:
            return normalize_positions(pd.read_csv(POSITION_FILE))
        except Exception:
            return pd.DataFrame(columns=["code", "name", "shares", "cost_price", "buy_date", "account_type", "notes"])
    return pd.DataFrame(columns=["code", "name", "shares", "cost_price", "buy_date", "account_type", "notes"])


def save_positions(df):
    df.to_csv(POSITION_FILE, index=False, encoding="utf-8-sig")


def current_price_for_code(code, spot_df):
    code = clean_code(code)

    if spot_df is not None and not spot_df.empty:
        hit = spot_df[spot_df["code"].astype(str) == code]
        if not hit.empty:
            r = hit.iloc[0]
            return safe_num(r["price"]), r.get("name", f"基金{code}"), "场内实时行情"

    hist, source, err = fetch_exchange_history(code, 20)
    if not hist.empty:
        return safe_num(hist.iloc[-1]["close"]), f"基金{code}", source

    return np.nan, f"基金{code}", "真实价格获取失败"


def compute_position_detail(positions, spot_df):
    if positions is None or positions.empty:
        return pd.DataFrame()

    rows = []
    for _, p in positions.iterrows():
        code = clean_code(p["code"])
        price, real_name, source = current_price_for_code(code, spot_df)

        shares = safe_num(p["shares"], 0)
        cost = safe_num(p["cost_price"], 0)
        current_value = shares * price if pd.notna(price) else np.nan
        cost_value = shares * cost if cost > 0 else np.nan
        profit = current_value - cost_value if pd.notna(current_value) and pd.notna(cost_value) else np.nan
        profit_rate = profit / cost_value * 100 if pd.notna(profit) and cost_value > 0 else np.nan

        rows.append(
            {
                "code": code,
                "name": p["name"] if str(p["name"]).strip() else real_name,
                "shares": shares,
                "cost_price": cost,
                "current_price": price,
                "current_value": current_value,
                "cost_value": cost_value,
                "profit": profit,
                "profit_rate": profit_rate,
                "price_source": source,
                "buy_date": p.get("buy_date", ""),
                "notes": p.get("notes", ""),
            }
        )

    df = pd.DataFrame(rows)
    if not df.empty:
        total = df["current_value"].sum()
        df["weight"] = df["current_value"] / total * 100 if total > 0 else np.nan
    return df


# ============================================================
# 侧边栏
# ============================================================
st.sidebar.markdown("## 📊 基金智能分析平台")
st.sidebar.caption("实盘导入 · 五日曲线 · 场内实时穿透")

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
    st.sidebar.success("A股交易时段：实时行情刷新")
elif is_pre_market_time():
    st.sidebar.info("盘前时段：可低频刷新")
else:
    st.sidebar.warning("非交易时段：行情可能不更新")


# ============================================================
# 全局数据准备
# ============================================================
positions = load_positions()
watch_codes = list(module_items.values())
if selected_code not in watch_codes:
    watch_codes.insert(0, selected_code)
if not positions.empty:
    for c in positions["code"].tolist():
        c = clean_code(c)
        if c and c not in watch_codes:
            watch_codes.append(c)

spot_df, spot_source, spot_error = fetch_exchange_spot(tuple(watch_codes))
hist_df, hist_source, hist_error = fetch_exchange_history(selected_code, days)

realtime_note = ""
if not hist_df.empty and not spot_df.empty:
    hit = spot_df[spot_df["code"] == selected_code]
    if not hit.empty:
        hist_df, realtime_note = apply_spot_to_history(hist_df, hit.iloc[0])

hist_df = enrich_indicators(hist_df)
summary = compute_summary(hist_df)

fund_name = selected_display_name
if not spot_df.empty:
    hit = spot_df[spot_df["code"] == selected_code]
    if not hit.empty and str(hit.iloc[0].get("name", "")).strip():
        fund_name = hit.iloc[0]["name"]

latest = hist_df.iloc[-1] if not hist_df.empty else pd.Series(dtype="object")


# ============================================================
# 顶部标题
# ============================================================
st.markdown('<div class="main-title">FundPilot Pro ｜ 基金智能分析平台</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">实盘导入 · 真实行情 · 五日曲线 · 场内实时穿透 · 底层资产暴露</div>',
    unsafe_allow_html=True,
)

if spot_error or hist_error:
    st.markdown(
        f'<div class="status-danger">真实数据提示：{spot_source} / {hist_source}；{spot_error or hist_error}</div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f'<div class="status-ok">真实数据源：{spot_source}；{hist_source}；{realtime_note}</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# 页面一：基金分析
# ============================================================
if page == "基金分析":
    if hist_df.empty:
        st.error("未获取到该基金真实行情，请检查代码或稍后重试。")
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
            数据源：{hist_source}；{realtime_note}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab1, tab2, tab3 = st.tabs(["📈 五日曲线", "📊 专业趋势图", "🧠 专业解读"])

    with tab1:
        st.plotly_chart(
            make_five_day_chart(hist_df, f"{fund_name} 五日曲线"),
            use_container_width=True,
        )

    with tab2:
        st.plotly_chart(
            make_price_chart(hist_df, f"{fund_name} 真实行情趋势分析"),
            use_container_width=True,
        )

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
# 页面二：场内实时穿透
# ============================================================
elif page == "场内实时穿透":
    st.markdown(
        f"""
        <div class="panel">
            <div class="panel-title">{fund_name}（{selected_code}）场内实时穿透</div>
            <div class="panel-subtitle">
            计算逻辑：ETF实时价格 + 成分/PCF权重 + 成分股实时行情 → 实时估算涨跌、贡献度与底层暴露。
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="status-warn">
        权重数据优先使用你导入的PCF/成分清单；若未导入，则尝试读取东方财富基金持仓披露。
        免费披露持仓可能滞后；成分股行情为东方财富实时行情。
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded_comp = st.file_uploader(
        "上传PCF/成分清单 Excel或CSV",
        type=["xlsx", "xls", "csv"],
        help="推荐字段：基金代码、股票代码、股票名称、权重、行业。权重可填百分数，如8.5。",
    )

    if uploaded_comp is not None:
        try:
            if uploaded_comp.name.lower().endswith(".csv"):
                raw_comp = pd.read_csv(uploaded_comp)
            else:
                raw_comp = pd.read_excel(uploaded_comp)
            comp_df = normalize_component_columns(raw_comp)
            if comp_df.empty:
                st.error("未识别到有效成分数据，请检查列名。")
            else:
                old = load_components()
                old = old[old["fund_code"] != selected_code]
                new_all = pd.concat([old, comp_df], ignore_index=True)
                save_components(new_all)
                st.success(f"已导入 {len(comp_df)} 条成分/PCF数据")
        except Exception as e:
            st.error(f"导入失败：{e}")

    components, comp_source, comp_error = get_components_for_fund(selected_code)
    look_df, quote_source, quote_error = calculate_lookthrough(selected_code, components)

    etf_pct = safe_num(latest.get("pct_change"), np.nan)
    estimated_pct = look_df["contribution_pct"].sum() if not look_df.empty else np.nan
    gap = etf_pct - estimated_pct if pd.notna(etf_pct) and pd.notna(estimated_pct) else np.nan

    concentration10 = look_df.head(10)["weight"].sum() if not look_df.empty else np.nan
    max_pos = look_df.iloc[0] if not look_df.empty else None
    max_neg = look_df.sort_values("contribution_pct").iloc[0] if not look_df.empty else None

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("ETF场内涨跌", format_pct(etf_pct))
    c2.metric("底层估算涨跌", format_pct(estimated_pct))
    c3.metric("估算偏离", format_pct(gap))
    c4.metric("成分数量", len(look_df))
    c5.metric("前10集中度", format_pct(concentration10))

    c6, c7, c8 = st.columns(3)
    c6.metric("权重来源", comp_source)
    c7.metric("行情来源", quote_source)
    c8.metric("更新时间", now_text())

    if comp_error:
        st.warning(f"成分数据提示：{comp_error}")
    if quote_error:
        st.error(f"成分股行情提示：{quote_error}")

    tab1, tab2, tab3, tab4 = st.tabs(["📈 五日曲线", "🧬 贡献度", "🔥 热力图", "📋 成分明细"])

    with tab1:
        st.plotly_chart(
            make_five_day_chart(hist_df, f"{fund_name} 五日场内走势"),
            use_container_width=True,
        )

    with tab2:
        st.plotly_chart(make_contribution_bar(look_df), use_container_width=True)

        if max_pos is not None and max_neg is not None:
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
            st.error("未获取到穿透明细。请导入PCF/成分清单，或稍后重试东方财富持仓披露读取。")
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
                    "quote_time": "行情时间",
                    "source": "权重来源",
                }
            )

            keep_cols = ["股票代码", "股票名称", "行业", "权重", "现价", "实时涨跌", "贡献度", "成交额", "行情时间", "权重来源"]
            keep_cols = [c for c in keep_cols if c in show.columns]
            st.dataframe(show[keep_cols], use_container_width=True, height=620, hide_index=True)


# ============================================================
# 页面三：实盘导入与计算
# ============================================================
elif page == "实盘导入与计算":
    st.markdown(
        """
        <div class="panel">
            <div class="panel-title">实盘导入与实时计算</div>
            <div class="panel-subtitle">
            支持Excel/CSV导入实仓，实时计算持仓市值、盈亏、仓位占比，并可进一步做底层股票穿透。
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

    all_pos_codes = positions["code"].tolist() if not positions.empty else []
    spot_pos, spot_pos_source, spot_pos_error = fetch_exchange_spot(tuple(all_pos_codes))
    pos_detail = compute_position_detail(positions, spot_pos)

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
        portfolio_lt, p_source, p_error = calculate_portfolio_lookthrough(pos_detail)

        if portfolio_lt.empty:
            st.warning(f"暂未形成实盘底层穿透：{p_error}")
        else:
            st.success("已根据实盘仓位与基金成分权重计算底层股票暴露。")
            stock_quotes, sq_source, sq_error = fetch_stock_spot(tuple(portfolio_lt["stock_code"].tolist()))
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
            st.dataframe(table[keep2].head(80), use_container_width=True, height=520, hide_index=True)


# ============================================================
# 页面四：市场模块
# ============================================================
elif page == "市场模块":
    st.markdown(
        f"""
        <div class="panel">
            <div class="panel-title">{module_name} 模块行情</div>
            <div class="panel-subtitle">模块内场内基金实时行情与全模块清单。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    module_df = pd.DataFrame(
        [{"模块": module_name, "名称": n, "代码": c, "是否场内": "是" if is_exchange_fund(c) else "否"} for n, c in module_items.items()]
    )

    if not spot_df.empty:
        s = spot_df.copy()
        s["成交额"] = s["amount"].apply(format_money)
        s = s.rename(columns={"code": "代码", "name": "名称", "price": "最新价", "pct_change": "涨跌幅", "change": "涨跌额", "update_time": "更新时间"})
        st.dataframe(s[["代码", "名称", "最新价", "涨跌幅", "涨跌额", "成交额", "更新时间"]].sort_values("涨跌幅", ascending=False), use_container_width=True, height=380, hide_index=True)
    else:
        st.warning(f"模块实时行情未获取：{spot_source}；{spot_error}")

    st.subheader("当前模块基金清单")
    st.dataframe(module_df, use_container_width=True, height=380, hide_index=True)

    all_rows = []
    for m, items in FUND_MODULES.items():
        for n, c in items.items():
            all_rows.append({"模块": m, "名称": n, "代码": c, "是否场内": "是" if is_exchange_fund(c) else "否"})
    st.subheader("全模块基金清单")
    st.dataframe(pd.DataFrame(all_rows), use_container_width=True, height=520, hide_index=True)


# ============================================================
# 页面五：自定义搜索
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
            all_rows.append({"模块": m, "名称": n, "代码": c, "是否场内": "是" if is_exchange_fund(c) else "否"})
    all_df = pd.DataFrame(all_rows)

    if keyword:
        kw = keyword.strip()
        result = all_df[
            all_df["模块"].str.contains(kw, case=False, na=False)
            | all_df["名称"].str.contains(kw, case=False, na=False)
            | all_df["代码"].astype(str).str.contains(kw, case=False, na=False)
        ]

        if result.empty and kw.isdigit() and len(kw) == 6:
            result = pd.DataFrame([{"模块": "用户自查", "名称": f"自查基金{kw}", "代码": kw, "是否场内": "是" if is_exchange_fund(kw) else "否"}])

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
