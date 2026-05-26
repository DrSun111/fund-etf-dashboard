# -*- coding: utf-8 -*-
"""
基金智能分析平台｜免费多源容错版

核心功能：
1. 实盘导入与实时计算
2. ETF/LOF 实时行情
3. 五日曲线
4. 场内实时穿透
5. 成分股实时贡献
6. 实仓底层股票暴露
7. 支持任意6位场内基金代码自查

数据逻辑：
- 不生成虚拟行情
- 东方财富优先
- AkShare备用
- 最近真实缓存兜底
"""

from __future__ import annotations

import re
import time
import datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots

try:
    import akshare as ak
except Exception:
    ak = None


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

CACHE_DIR = Path(".fund_free_cache")
CACHE_DIR.mkdir(exist_ok=True)

POSITION_FILE = CACHE_DIR / "positions.csv"
COMPONENT_FILE = CACHE_DIR / "components.csv"
SPOT_CACHE_FILE = CACHE_DIR / "fund_spot_cache.csv"
STOCK_SPOT_CACHE_FILE = CACHE_DIR / "stock_spot_cache.csv"


# ============================================================
# 页面样式
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
for m, items in FUND_MODULES.items():
    ALL_FUNDS.update(items)


# ============================================================
# 基础工具函数
# ============================================================
def china_now() -> dt.datetime:
    return dt.datetime.now(CHINA_TZ)


def now_text() -> str:
    return china_now().strftime("%Y-%m-%d %H:%M:%S")


def today_yyyymmdd() -> str:
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


def is_exchange_fund(code: str) -> bool:
    code = clean_code(code)
    return code.startswith(
        (
            "15", "16", "18",
            "50", "51", "52", "53", "56", "58",
            "159", "160", "161", "162", "163", "164", "165", "166", "167", "168", "169",
            "511",
        )
    )


def fund_market(code: str) -> str:
    code = clean_code(code)
    if code.startswith(("5", "6", "9")):
        return "SH"
    return "SZ"


def stock_market(code: str) -> str:
    code = clean_code(code)
    if code.startswith(("6", "5", "9")):
        return "SH"
    return "SZ"


def fund_secid(code: str) -> str:
    code = clean_code(code)
    return f"1.{code}" if fund_market(code) == "SH" else f"0.{code}"


def stock_secid(code: str) -> str:
    code = clean_code(code)
    return f"1.{code}" if stock_market(code) == "SH" else f"0.{code}"


def cache_history_file(code: str) -> Path:
    return CACHE_DIR / f"history_{clean_code(code)}.csv"


def save_csv_cache(df: pd.DataFrame, path: Path):
    try:
        if df is not None and not df.empty:
            df.to_csv(path, index=False, encoding="utf-8-sig")
    except Exception:
        pass


def load_csv_cache(path: Path) -> pd.DataFrame:
    try:
        if path.exists():
            return pd.read_csv(path)
    except Exception:
        pass
    return pd.DataFrame()


def request_json(url: str, params=None, timeout=8, max_retry=2):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json,text/plain,*/*",
        "Referer": "https://quote.eastmoney.com/",
        "Connection": "close",
    }

    last_error = None

    for i in range(max_retry + 1):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last_error = e
            time.sleep(0.5 + i * 0.7)

    raise last_error


# ============================================================
# 东方财富实时行情：基金
# ============================================================
def em_fund_spot_batch(codes: list[str]) -> pd.DataFrame:
    codes = [clean_code(c) for c in codes if clean_code(c)]
    codes = [c for c in dict.fromkeys(codes) if is_exchange_fund(c)]

    if not codes:
        return pd.DataFrame()

    rows = []

    for i in range(0, len(codes), 3):
        batch = codes[i:i + 3]
        url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
        params = {
            "fltt": "2",
            "secids": ",".join(fund_secid(c) for c in batch),
            "fields": "f12,f14,f2,f3,f4,f5,f6",
            "_": int(time.time() * 1000),
        }

        try:
            data = request_json(url, params=params, timeout=6, max_retry=1)
            diff = data.get("data", {}).get("diff", [])

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
                        "source": "东方财富批量实时行情",
                    }
                )
        except Exception:
            continue

    return pd.DataFrame(rows)


def em_fund_spot_single(code: str) -> pd.DataFrame:
    code = clean_code(code)
    url = "https://push2.eastmoney.com/api/qt/stock/get"
    params = {
        "secid": fund_secid(code),
        "fields": "f12,f14,f43,f47,f48,f57,f58,f60,f169,f170",
        "_": int(time.time() * 1000),
    }

    data = request_json(url, params=params, timeout=6, max_retry=1)
    d = data.get("data") or {}

    if not d:
        return pd.DataFrame()

    raw_price = safe_num(d.get("f43"))
    raw_pre_close = safe_num(d.get("f60"))

    def normalize_price(x, reference=np.nan):
        x = safe_num(x)
        if pd.isna(x) or x <= 0:
            return np.nan
        candidates = [x, x / 10, x / 100, x / 1000, x / 10000]
        if pd.notna(reference) and reference > 0:
            return min(candidates, key=lambda v: abs(v - reference))
        reasonable = [v for v in candidates if 0.01 <= v <= 300]
        return reasonable[0] if reasonable else x

    pre_close = normalize_price(raw_pre_close)
    price = normalize_price(raw_price, pre_close)

    pct = safe_num(d.get("f170"))
    if pd.notna(pct) and abs(pct) > 100:
        pct = pct / 100

    change = safe_num(d.get("f169"))
    if pd.notna(change) and abs(change) > 50:
        change = change / 1000

    return pd.DataFrame(
        [
            {
                "code": code,
                "name": d.get("f58") or d.get("f14") or f"基金{code}",
                "price": price,
                "pct_change": pct,
                "change": change,
                "volume": safe_num(d.get("f47")),
                "amount": safe_num(d.get("f48")),
                "update_time": now_text(),
                "source": "东方财富单只实时行情",
            }
        ]
    )


def ak_fund_spot(codes: list[str]) -> pd.DataFrame:
    if ak is None:
        return pd.DataFrame()

    try:
        raw = ak.fund_etf_spot_em()
    except Exception:
        return pd.DataFrame()

    if raw is None or raw.empty:
        return pd.DataFrame()

    df = raw.copy()

    col_map = {}
    for col in df.columns:
        c = str(col)
        if c in ["代码", "基金代码"]:
            col_map[col] = "code"
        elif c in ["名称", "基金简称", "基金名称"]:
            col_map[col] = "name"
        elif c in ["最新价", "最新价元", "收盘价"]:
            col_map[col] = "price"
        elif c in ["涨跌幅", "涨跌幅%"]:
            col_map[col] = "pct_change"
        elif c in ["涨跌额"]:
            col_map[col] = "change"
        elif c in ["成交量"]:
            col_map[col] = "volume"
        elif c in ["成交额"]:
            col_map[col] = "amount"

    df = df.rename(columns=col_map)

    for col in ["code", "name", "price", "pct_change", "change", "volume", "amount"]:
        if col not in df.columns:
            df[col] = np.nan

    df["code"] = df["code"].astype(str).map(clean_code)
    codes = [clean_code(c) for c in codes]
    df = df[df["code"].isin(codes)].copy()

    for col in ["price", "pct_change", "change", "volume", "amount"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["update_time"] = now_text()
    df["source"] = "AkShare ETF实时行情"
    return df[["code", "name", "price", "pct_change", "change", "volume", "amount", "update_time", "source"]]


@st.cache_data(ttl=10, show_spinner=False)
def get_fund_spot(codes_tuple):
    codes = [clean_code(c) for c in list(codes_tuple) if clean_code(c)]
    codes = [c for c in dict.fromkeys(codes) if is_exchange_fund(c)]

    if not codes:
        return pd.DataFrame(), "无场内代码", ""

    errors = []
    pieces = []

    try:
        batch_df = em_fund_spot_batch(codes)
        if not batch_df.empty:
            pieces.append(batch_df)
    except Exception as e:
        errors.append(f"东方财富批量失败：{e}")

    got = set()
    if pieces:
        got = set(pd.concat(pieces)["code"].astype(str).tolist())

    missing = [c for c in codes if c not in got]
    for code in missing:
        try:
            one = em_fund_spot_single(code)
            if not one.empty:
                pieces.append(one)
        except Exception as e:
            errors.append(f"东方财富单只失败 {code}：{e}")

    if pieces:
        df = pd.concat(pieces, ignore_index=True)
        df = df.drop_duplicates("code", keep="last")
        df["price"] = pd.to_numeric(df["price"], errors="coerce")
        df = df[df["price"].notna() & (df["price"] > 0)].copy()

        if not df.empty:
            save_csv_cache(df, SPOT_CACHE_FILE)
            source = "东方财富实时行情"
            if errors:
                source = "东方财富实时行情，部分接口已容错"
            return df.reset_index(drop=True), source, "；".join(errors[:5])

    try:
        ak_df = ak_fund_spot(codes)
        if not ak_df.empty:
            save_csv_cache(ak_df, SPOT_CACHE_FILE)
            return ak_df.reset_index(drop=True), "AkShare ETF实时行情", "；".join(errors[:5])
    except Exception as e:
        errors.append(f"AkShare实时行情失败：{e}")

    cache = load_csv_cache(SPOT_CACHE_FILE)
    if not cache.empty and "code" in cache.columns:
        cache["code"] = cache["code"].astype(str).map(clean_code)
        cache = cache[cache["code"].isin(codes)].copy()
        if not cache.empty:
            cache["source"] = "最近一次真实缓存"
            return cache.reset_index(drop=True), "最近一次真实缓存", "；".join(errors[:5])

    return pd.DataFrame(), "实时行情获取失败", "；".join(errors[:8])


# ============================================================
# 历史K线
# ============================================================
def em_fund_history(code: str, days: int = 240) -> pd.DataFrame:
    code = clean_code(code)

    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "secid": fund_secid(code),
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",
        "fqt": "0",
        "beg": "20000101",
        "end": today_yyyymmdd(),
        "lmt": str(max(days * 2, 600)),
        "_": int(time.time() * 1000),
    }

    data = request_json(url, params=params, timeout=8, max_retry=2)
    klines = data.get("data", {}).get("klines", [])

    rows = []
    for line in klines:
        p = str(line).split(",")
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
                "source": "东方财富历史K线",
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").tail(days).reset_index(drop=True)


def ak_fund_history(code: str, days: int = 240) -> pd.DataFrame:
    if ak is None:
        return pd.DataFrame()

    code = clean_code(code)

    try:
        raw = ak.fund_etf_hist_em(symbol=code, period="daily", adjust="")
    except Exception:
        return pd.DataFrame()

    if raw is None or raw.empty:
        return pd.DataFrame()

    df = raw.copy()
    col_map = {}

    for col in df.columns:
        c = str(col)
        if c in ["日期"]:
            col_map[col] = "date"
        elif c in ["开盘", "开盘价"]:
            col_map[col] = "open"
        elif c in ["收盘", "收盘价"]:
            col_map[col] = "close"
        elif c in ["最高", "最高价"]:
            col_map[col] = "high"
        elif c in ["最低", "最低价"]:
            col_map[col] = "low"
        elif c in ["成交量"]:
            col_map[col] = "volume"
        elif c in ["成交额"]:
            col_map[col] = "amount"
        elif c in ["涨跌幅"]:
            col_map[col] = "pct_change"

    df = df.rename(columns=col_map)

    for col in ["date", "open", "close", "high", "low", "volume", "amount", "pct_change"]:
        if col not in df.columns:
            df[col] = np.nan

    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    for col in ["open", "close", "high", "low", "volume", "amount", "pct_change"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df[df["date"].notna()].copy()
    df["source"] = "AkShare历史K线"
    return df.sort_values("date").tail(days).reset_index(drop=True)


@st.cache_data(ttl=60, show_spinner=False)
def get_fund_history(code: str, days: int = 240):
    code = clean_code(code)
    errors = []

    try:
        df = em_fund_history(code, days)
        if not df.empty:
            save_csv_cache(df, cache_history_file(code))
            return df, "东方财富历史K线", ""
    except Exception as e:
        errors.append(f"东方财富历史K线失败：{e}")

    try:
        df = ak_fund_history(code, days)
        if not df.empty:
            save_csv_cache(df, cache_history_file(code))
            return df, "AkShare历史K线", "；".join(errors[:3])
    except Exception as e:
        errors.append(f"AkShare历史K线失败：{e}")

    cache = load_csv_cache(cache_history_file(code))
    if not cache.empty:
        try:
            cache["date"] = pd.to_datetime(cache["date"])
            cache["source"] = "最近一次真实历史缓存"
            return cache.tail(days).reset_index(drop=True), "最近一次真实历史缓存", "；".join(errors[:5])
        except Exception:
            pass

    return pd.DataFrame(), "历史行情获取失败", "；".join(errors[:8])


def apply_spot_to_history(history: pd.DataFrame, spot_row: pd.Series):
    if history is None or history.empty or spot_row is None:
        return history, ""

    price = safe_num(spot_row.get("price"))
    pct = safe_num(spot_row.get("pct_change"))
    amount = safe_num(spot_row.get("amount"))
    volume = safe_num(spot_row.get("volume"))

    if pd.isna(price) or price <= 0:
        return history, "实时价格无效，未合并"

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
        df.loc[idx, "source"] = "实时行情合并"
        return df, f"已用实时行情更新今日K线：{now_text()}"

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
        "source": "实时行情追加",
    }

    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    return df, f"历史K线未到今日，已用实时行情追加：{now_text()}"


# ============================================================
# 股票实时行情
# ============================================================
def em_stock_spot_batch(stock_codes: list[str]) -> pd.DataFrame:
    codes = [clean_code(c) for c in stock_codes if clean_code(c)]
    codes = list(dict.fromkeys(codes))

    if not codes:
        return pd.DataFrame()

    rows = []

    for i in range(0, len(codes), 30):
        batch = codes[i:i + 30]
        url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
        params = {
            "fltt": "2",
            "secids": ",".join(stock_secid(c) for c in batch),
            "fields": "f12,f14,f2,f3,f4,f5,f6",
            "_": int(time.time() * 1000),
        }

        try:
            data = request_json(url, params=params, timeout=8, max_retry=1)
            diff = data.get("data", {}).get("diff", [])

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
        except Exception:
            continue

    return pd.DataFrame(rows)


@st.cache_data(ttl=10, show_spinner=False)
def get_stock_spot(stock_codes_tuple):
    codes = [clean_code(c) for c in list(stock_codes_tuple) if clean_code(c)]
    codes = list(dict.fromkeys(codes))

    if not codes:
        return pd.DataFrame(), "无股票代码", ""

    errors = []

    try:
        df = em_stock_spot_batch(codes)
        if not df.empty:
            df = df.drop_duplicates("stock_code", keep="last")
            df["price"] = pd.to_numeric(df["price"], errors="coerce")
            df = df[df["price"].notna() & (df["price"] > 0)].copy()
            if not df.empty:
                save_csv_cache(df, STOCK_SPOT_CACHE_FILE)
                return df.reset_index(drop=True), "东方财富股票实时行情", ""
    except Exception as e:
        errors.append(f"东方财富股票实时行情失败：{e}")

    cache = load_csv_cache(STOCK_SPOT_CACHE_FILE)
    if not cache.empty and "stock_code" in cache.columns:
        cache["stock_code"] = cache["stock_code"].astype(str).map(clean_code)
        cache = cache[cache["stock_code"].isin(codes)].copy()
        if not cache.empty:
            cache["quote_source"] = "最近一次真实股票行情缓存"
            return cache.reset_index(drop=True), "最近一次真实股票行情缓存", "；".join(errors[:5])

    return pd.DataFrame(), "股票实时行情获取失败", "；".join(errors[:8])


# ============================================================
# 穿透权重：用户上传 / 东方财富披露 / 缓存
# ============================================================
def normalize_components(raw: pd.DataFrame, default_fund_code: str = "") -> pd.DataFrame:
    if raw is None or raw.empty:
        return pd.DataFrame(columns=["fund_code", "stock_code", "stock_name", "weight", "industry", "source"])

    df = raw.copy()
    rename = {}

    for col in df.columns:
        c = str(col).strip()

        if c in ["基金代码", "ETF代码", "fund_code", "etf_code"]:
            rename[col] = "fund_code"
        elif c in ["股票代码", "证券代码", "成分券代码", "stock_code", "code", "symbol"]:
            rename[col] = "stock_code"
        elif c in ["股票名称", "证券简称", "证券名称", "成分券名称", "stock_name", "name"]:
            rename[col] = "stock_name"
        elif c in ["权重", "占比", "持仓占比", "占净值比例", "weight", "比例"] or "权重" in c or "比例" in c or "占净值" in c:
            rename[col] = "weight"
        elif c in ["行业", "申万行业", "industry"]:
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


def load_components() -> pd.DataFrame:
    if COMPONENT_FILE.exists():
        try:
            return normalize_components(pd.read_csv(COMPONENT_FILE))
        except Exception:
            return pd.DataFrame(columns=["fund_code", "stock_code", "stock_name", "weight", "industry", "source"])
    return pd.DataFrame(columns=["fund_code", "stock_code", "stock_name", "weight", "industry", "source"])


def save_components(df: pd.DataFrame):
    save_csv_cache(df, COMPONENT_FILE)


@st.cache_data(ttl=60 * 60, show_spinner=False)
def em_fund_holdings(code: str):
    code = clean_code(code)
    url = f"https://fundf10.eastmoney.com/ccmx_{code}.html"

    try:
        tables = pd.read_html(url)
    except Exception as e:
        return pd.DataFrame(), "东方财富基金持仓披露读取失败", str(e)

    candidates = []
    for t in tables:
        joined = " ".join([str(c) for c in t.columns])
        if ("股票代码" in joined or "代码" in joined) and ("占净值" in joined or "比例" in joined or "持仓" in joined):
            candidates.append(t)

    if not candidates:
        return pd.DataFrame(), "未解析到持仓表", "东方财富页面未返回可识别持仓表"

    raw = candidates[0].copy()
    raw["fund_code"] = code
    raw["source"] = "东方财富基金持仓披露"

    comp = normalize_components(raw, default_fund_code=code)
    if comp.empty:
        return pd.DataFrame(), "持仓表解析为空", "代码或权重字段无法识别"

    return comp, "东方财富基金持仓披露", ""


def get_components_for_fund(code: str):
    code = clean_code(code)

    local = load_components()
    hit = local[local["fund_code"] == code].copy()

    if not hit.empty:
        return hit, "用户导入PCF/成分清单", ""

    comp, src, err = em_fund_holdings(code)
    if not comp.empty:
        old = load_components()
        old = old[old["fund_code"] != code]
        save_components(pd.concat([old, comp], ignore_index=True))
        return comp, src, err

    local = load_components()
    hit = local[local["fund_code"] == code].copy()
    if not hit.empty:
        hit["source"] = "最近一次真实成分缓存"
        return hit, "最近一次真实成分缓存", err

    return pd.DataFrame(), src, err


def calculate_lookthrough(code: str):
    comps, comp_source, comp_error = get_components_for_fund(code)

    if comps.empty:
        return pd.DataFrame(), comp_source, comp_error

    stock_codes = comps["stock_code"].dropna().astype(str).unique().tolist()
    quotes, quote_source, quote_error = get_stock_spot(tuple(stock_codes))

    if quotes.empty:
        return pd.DataFrame(), quote_source, quote_error or comp_error

    df = comps.merge(quotes, on="stock_code", how="left", suffixes=("", "_quote"))

    if "stock_name_quote" in df.columns:
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
# 指标系统
# ============================================================
def enrich_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])
    out = out.sort_values("date").reset_index(drop=True)

    for col in ["open", "high", "low", "close", "volume", "amount", "pct_change"]:
        if col not in out.columns:
            out[col] = np.nan
        out[col] = pd.to_numeric(out[col], errors="coerce")

    out["close"] = out["close"].ffill().bfill()
    out["open"] = out["open"].fillna(out["close"])
    out["high"] = out["high"].fillna(out[["open", "close"]].max(axis=1))
    out["low"] = out["low"].fillna(out[["open", "close"]].min(axis=1))
    out["amount"] = out["amount"].fillna(0)
    out["volume"] = out["volume"].fillna(0)
    out["pct_change"] = out["pct_change"].fillna(out["close"].pct_change() * 100).fillna(0)

    out["ma5"] = out["close"].rolling(5, min_periods=2).mean()
    out["ma10"] = out["close"].rolling(10, min_periods=3).mean()
    out["ma20"] = out["close"].rolling(20, min_periods=5).mean()
    out["ma60"] = out["close"].rolling(60, min_periods=10).mean()

    out["amount_ma20"] = out["amount"].rolling(20, min_periods=5).mean()
    out["volume_ratio"] = np.where(out["amount_ma20"] > 0, out["amount"] / out["amount_ma20"], np.nan)

    out["ma5_dev"] = (out["close"] / out["ma5"] - 1) * 100
    out["ma20_dev"] = (out["close"] / out["ma20"] - 1) * 100
    out["ma60_dev"] = (out["close"] / out["ma60"] - 1) * 100

    out["money_strength"] = out["pct_change"] * out["amount"] / 1e8

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
        f"若ETF场内涨跌明显高于底层估算涨跌，可能存在溢价或追涨情绪；"
        f"若明显低于底层估算涨跌，则可能存在折价、流动性折让或权重数据滞后。"
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
# 实盘
# ============================================================
def normalize_positions(raw: pd.DataFrame) -> pd.DataFrame:
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


def load_positions() -> pd.DataFrame:
    if POSITION_FILE.exists():
        try:
            return normalize_positions(pd.read_csv(POSITION_FILE))
        except Exception:
            return pd.DataFrame(columns=["code", "name", "shares", "cost_price", "buy_date", "account_type", "notes"])
    return pd.DataFrame(columns=["code", "name", "shares", "cost_price", "buy_date", "account_type", "notes"])


def save_positions(df: pd.DataFrame):
    save_csv_cache(df, POSITION_FILE)


def current_price_for_fund(code: str, spot_df: pd.DataFrame):
    code = clean_code(code)

    if spot_df is not None and not spot_df.empty:
        hit = spot_df[spot_df["code"].astype(str) == code]
        if not hit.empty:
            r = hit.iloc[0]
            return safe_num(r["price"]), r.get("name", f"基金{code}"), r.get("source", "实时行情")

    hist, src, err = get_fund_history(code, 30)
    if hist is not None and not hist.empty:
        return safe_num(hist.iloc[-1]["close"]), f"基金{code}", src

    return np.nan, f"基金{code}", "真实价格获取失败"


def compute_position_detail(positions: pd.DataFrame, spot_df: pd.DataFrame) -> pd.DataFrame:
    if positions is None or positions.empty:
        return pd.DataFrame()

    rows = []

    for _, pos in positions.iterrows():
        code = clean_code(pos["code"])
        price, real_name, price_source = current_price_for_fund(code, spot_df)

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


def calculate_portfolio_lookthrough(position_detail: pd.DataFrame):
    if position_detail is None or position_detail.empty:
        return pd.DataFrame(), "无实仓", ""

    total_value = position_detail["current_value"].sum()
    if total_value <= 0:
        return pd.DataFrame(), "实仓市值无效", ""

    parts = []
    errors = []

    for _, pos in position_detail.iterrows():
        code = clean_code(pos["code"])
        fund_weight = safe_num(pos["current_value"]) / total_value * 100

        comps, src, err = get_components_for_fund(code)
        if comps.empty:
            errors.append(f"{code} 无穿透数据：{err}")
            continue

        c = comps.copy()
        c["fund_code"] = code
        c["fund_name"] = pos["name"]
        c["fund_weight"] = fund_weight
        c["portfolio_exposure"] = fund_weight * c["weight"] / 100
        parts.append(c)

    if not parts:
        return pd.DataFrame(), "实仓穿透失败", "；".join(errors)

    all_df = pd.concat(parts, ignore_index=True)

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

    if d.empty:
        return fig

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
st.sidebar.markdown("## 📊 基金智能分析平台")
st.sidebar.caption("免费多源容错版｜东方财富 + AkShare + 真实缓存")

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
    st.sidebar.warning("非交易时段：行情可能不更新")


# ============================================================
# 全局数据
# ============================================================
positions = load_positions()

watch_codes = [selected_code]

if not positions.empty:
    for c in positions["code"].tolist()[:10]:
        c = clean_code(c)
        if c and c not in watch_codes:
            watch_codes.append(c)

spot_df, spot_source, spot_error = get_fund_spot(tuple(watch_codes))
hist_df, hist_source, hist_error = get_fund_history(selected_code, days)

merge_note = ""
if not hist_df.empty and not spot_df.empty:
    hit = spot_df[spot_df["code"].astype(str) == selected_code]
    if not hit.empty:
        hist_df, merge_note = apply_spot_to_history(hist_df, hit.iloc[0])

hist_df = enrich_indicators(hist_df)
summary = compute_summary(hist_df)
latest = hist_df.iloc[-1] if not hist_df.empty else pd.Series(dtype="object")

fund_name = selected_display_name

if not spot_df.empty:
    hit = spot_df[spot_df["code"].astype(str) == selected_code]
    if not hit.empty and str(hit.iloc[0].get("name", "")).strip():
        fund_name = hit.iloc[0]["name"]


# ============================================================
# 顶部
# ============================================================
st.markdown('<div class="main-title">FundPilot Pro ｜ 基金智能分析平台</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">实盘导入 · 免费真实行情 · 五日曲线 · 场内实时穿透 · 底层资产暴露</div>',
    unsafe_allow_html=True,
)

if "缓存" in spot_source or "缓存" in hist_source:
    st.markdown(
        f'<div class="status-warn">当前使用真实缓存数据：{spot_source}；{hist_source}。接口错误：{spot_error or hist_error}</div>',
        unsafe_allow_html=True,
    )
elif spot_error or hist_error:
    st.markdown(
        f'<div class="status-warn">数据源提示：{spot_source}；{hist_source}；{spot_error or hist_error}</div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f'<div class="status-ok">真实数据源正常：{spot_source}；{hist_source}；{merge_note}</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# 页面一：基金分析
# ============================================================
if page == "基金分析":
    if hist_df.empty:
        st.error("未获取到该基金真实行情，也没有可用缓存。请检查代码、网络或稍后重试。")
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
            行情来源：{hist_source}；{merge_note}
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
# 页面二：场内实时穿透
# ============================================================
elif page == "场内实时穿透":
    st.markdown(
        f"""
        <div class="panel">
            <div class="panel-title">{fund_name}（{selected_code}）场内实时穿透</div>
            <div class="panel-subtitle">
            计算逻辑：ETF实时价格 + PCF/成分权重 + 成分股实时行情 → 实时估算涨跌、贡献度与底层暴露。
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="status-warn">
        精确穿透建议上传当日PCF/成分清单；未上传时会尝试使用东方财富基金持仓披露作为兜底，披露持仓可能滞后。
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
                save_components(pd.concat([old, comp_df], ignore_index=True))
                st.success(f"已导入 {len(comp_df)} 条PCF/成分数据")
                st.rerun()
        except Exception as e:
            st.error(f"导入失败：{e}")

    look_df, look_source, look_error = calculate_lookthrough(selected_code)

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
    c8.metric("数据模式", "免费多源容错")

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
            st.error("未获取到穿透明细。请上传PCF/成分清单，或稍后重试东方财富持仓披露读取。")
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
                    "quote_source": "行情来源",
                }
            )

            keep = ["股票代码", "股票名称", "行业", "权重", "现价", "实时涨跌", "贡献度", "成交额", "行情时间", "权重来源", "行情来源"]
            keep = [c for c in keep if c in show.columns]
            st.dataframe(show[keep], use_container_width=True, height=620, hide_index=True)


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
    pos_spot_df, pos_spot_source, pos_spot_error = get_fund_spot(tuple(all_pos_codes))
    pos_detail = compute_position_detail(positions, pos_spot_df)

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

            stock_quotes, sq_source, sq_error = get_stock_spot(tuple(portfolio_lt["stock_code"].tolist()))
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
# 页面四：市场模块
# ============================================================
elif page == "市场模块":
    st.markdown(
        f"""
        <div class="panel">
            <div class="panel-title">{module_name} 模块行情</div>
            <div class="panel-subtitle">
            当前页面才会批量请求模块行情，避免首页/分析页因批量接口失败而崩。
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    module_codes = list(module_items.values())
    module_spot, module_src, module_err = get_fund_spot(tuple(module_codes))

    if module_spot.empty:
        st.warning(f"模块行情暂不可用：{module_src}；{module_err}")
    else:
        show = module_spot.copy()
        show["成交额"] = show["amount"].apply(format_money)
        show["涨跌幅"] = show["pct_change"].apply(format_pct)

        show = show.rename(
            columns={
                "code": "代码",
                "name": "名称",
                "price": "最新价",
                "change": "涨跌额",
                "update_time": "更新时间",
                "source": "来源",
            }
        )

        keep = ["代码", "名称", "最新价", "涨跌幅", "涨跌额", "成交额", "更新时间", "来源"]
        keep = [c for c in keep if c in show.columns]

        st.dataframe(show[keep].sort_values("涨跌幅", ascending=False), use_container_width=True, height=420, hide_index=True)

    st.subheader("当前模块基金清单")
    module_list = pd.DataFrame([{"模块": module_name, "名称": n, "代码": c} for n, c in module_items.items()])
    st.dataframe(module_list, use_container_width=True, height=300, hide_index=True)

    st.subheader("全模块基金清单")
    all_rows = []
    for m, items in FUND_MODULES.items():
        for n, c in items.items():
            all_rows.append({"模块": m, "名称": n, "代码": c})
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
