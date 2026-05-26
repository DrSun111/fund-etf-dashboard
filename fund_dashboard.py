import io
import time
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots


# ============================================================
# 页面基础设置
# ============================================================
st.set_page_config(
    page_title="基金智能分析平台",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# 缓存目录
# ============================================================
CACHE_DIR = Path(".fundpilot_cache")
CACHE_DIR.mkdir(exist_ok=True)

SPOT_CACHE_FILE = CACHE_DIR / "spot_cache.csv"
POSITION_CACHE_FILE = CACHE_DIR / "positions_cache.csv"


def history_cache_file(code: str) -> Path:
    code = str(code).strip()
    return CACHE_DIR / f"history_{code}.csv"


# ============================================================
# 高科技深色界面 CSS
# ============================================================
CUSTOM_CSS = """
<style>
/* 删除 Streamlit 顶部白色区域 */
[data-testid="stHeader"] {
    background: rgba(5, 8, 22, 0.0) !important;
    height: 0rem !important;
}
[data-testid="stToolbar"] {
    display: none !important;
}
[data-testid="stDecoration"] {
    display: none !important;
}
header {
    visibility: hidden !important;
    height: 0px !important;
}

/* 全局背景 */
html, body, [data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at top left, rgba(37, 99, 235, 0.18), transparent 26%),
        radial-gradient(circle at top right, rgba(20, 184, 166, 0.12), transparent 24%),
        linear-gradient(135deg, #050816 0%, #071126 45%, #030712 100%) !important;
    color: #F8FAFC !important;
}

.block-container {
    padding-top: 1.1rem !important;
    padding-bottom: 2.5rem !important;
    max-width: 96% !important;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #06112A 0%, #050A1B 100%) !important;
    border-right: 1px solid rgba(88, 213, 255, 0.14);
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
    text-shadow: 0 0 20px rgba(88, 213, 255, 0.18);
}

.sub-title {
    color: #B7C5DA !important;
    font-size: 15px;
    margin-bottom: 1rem;
}

.hero-panel {
    background: linear-gradient(135deg, rgba(10,16,34,0.96), rgba(13,25,52,0.95));
    border: 1px solid rgba(88,213,255,0.16);
    border-radius: 22px;
    padding: 22px 24px;
    margin-bottom: 16px;
    box-shadow: 0 12px 40px rgba(0,0,0,0.25);
}

.status-ok {
    background: linear-gradient(90deg, rgba(20, 83, 45, 0.82), rgba(6, 78, 59, 0.82));
    border: 1px solid rgba(74, 222, 128, 0.22);
    color: #D9FFF2 !important;
    padding: 13px 18px;
    border-radius: 16px;
    font-weight: 750;
    margin-bottom: 14px;
}

.status-warn {
    background: linear-gradient(90deg, rgba(113, 63, 18, 0.86), rgba(92, 52, 12, 0.86));
    border: 1px solid rgba(251, 191, 36, 0.24);
    color: #FFF4CF !important;
    padding: 13px 18px;
    border-radius: 16px;
    font-weight: 750;
    margin-bottom: 14px;
}

.status-danger {
    background: linear-gradient(90deg, rgba(127, 29, 29, 0.88), rgba(76, 29, 49, 0.86));
    border: 1px solid rgba(248, 113, 113, 0.24);
    color: #FFE4E6 !important;
    padding: 13px 18px;
    border-radius: 16px;
    font-weight: 750;
    margin-bottom: 14px;
}

.info-line {
    color: #A8B7CF !important;
    font-size: 13px;
    margin-top: 8px;
    margin-bottom: 16px;
}

.chart-panel {
    background: linear-gradient(180deg, rgba(10, 16, 34, 0.96), rgba(7, 13, 28, 0.96));
    border: 1px solid rgba(88, 213, 255, 0.14);
    border-radius: 22px;
    padding: 18px 22px 12px 22px;
    margin-bottom: 12px;
    box-shadow: 0 10px 36px rgba(0,0,0,0.25);
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
    font-size: 26px !important;
    font-weight: 900 !important;
}

button[data-baseweb="tab"] {
    color: #CFE0F5 !important;
    font-weight: 750 !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #FFFFFF !important;
}
button[data-baseweb="tab-highlight"] {
    background: linear-gradient(90deg, #38BDF8, #60A5FA) !important;
    height: 3px !important;
    border-radius: 999px !important;
}

/* 侧边栏输入、下拉框 */
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
# 基金模块池
# ============================================================
ETF_MODULES = {
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

DEFAULT_FUNDS = {}
for module_name, items in ETF_MODULES.items():
    DEFAULT_FUNDS.update(items)


# ============================================================
# 通用工具
# ============================================================
def now_text():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


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


def detect_market(code: str):
    code = str(code).strip()
    if code.startswith(("5", "6", "9")):
        return "SH"
    return "SZ"


def get_sec_id(code: str):
    code = str(code).strip()
    if detect_market(code) == "SH":
        return f"1.{code}"
    return f"0.{code}"


def save_df(df: pd.DataFrame, path: Path):
    try:
        if df is not None and not df.empty:
            df.to_csv(path, index=False, encoding="utf-8-sig")
    except Exception:
        pass


def load_df(path: Path):
    try:
        if path.exists():
            return pd.read_csv(path)
    except Exception:
        pass
    return pd.DataFrame()


def request_json(url, params, timeout=8):
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
    return r.json()


# ============================================================
# 东方财富数据接口
# ============================================================
def fetch_spot_from_eastmoney(codes):
    """
    东方财富实时快照批量接口。
    返回字段：
    code, name, price, pct_change, change, volume, amount, update_time
    """
    unique_codes = []
    for c in codes:
        c = str(c).strip()
        if c and c not in unique_codes:
            unique_codes.append(c)

    if not unique_codes:
        return pd.DataFrame()

    secids = ",".join([get_sec_id(c) for c in unique_codes])

    url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
    params = {
        "fltt": "2",
        "secids": secids,
        "fields": "f12,f14,f2,f3,f4,f5,f6",
    }

    data = request_json(url, params, timeout=6)
    diff = data.get("data", {}).get("diff", [])

    rows = []
    for item in diff:
        rows.append(
            {
                "code": str(item.get("f12", "")),
                "name": item.get("f14", ""),
                "price": safe_num(item.get("f2")),
                "pct_change": safe_num(item.get("f3")),
                "change": safe_num(item.get("f4")),
                "volume": safe_num(item.get("f5")),
                "amount": safe_num(item.get("f6")),
                "update_time": now_text(),
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("东方财富实时行情返回为空")

    return df


def fetch_history_from_eastmoney(code: str, days: int = 240):
    """
    东方财富日K历史行情。
    返回字段：
    date, open, close, high, low, volume, amount, pct_change
    """
    code = str(code).strip()

    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "secid": get_sec_id(code),
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",
        "fqt": "0",
        "beg": "20000101",
        "end": dt.datetime.now().strftime("%Y%m%d"),
        "lmt": str(max(days * 2, 600)),
    }

    data = request_json(url, params, timeout=8)
    klines = data.get("data", {}).get("klines", [])

    if not klines:
        raise RuntimeError("东方财富历史行情返回为空")

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
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("东方财富历史行情解析为空")

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df.tail(days).reset_index(drop=True)


def apply_realtime_to_history(history_df: pd.DataFrame, spot_row: pd.Series):
    """
    用东方财富实时快照更新历史K线最后一行。
    解决“历史K线停在旧日期，但实时价已经更新”的问题。
    """
    if history_df is None or history_df.empty:
        return history_df, "未能更新实时价"

    if spot_row is None or len(spot_row) == 0:
        return history_df, "未找到实时快照"

    price = safe_num(spot_row.get("price"))
    pct = safe_num(spot_row.get("pct_change"))
    amount = safe_num(spot_row.get("amount"))
    volume = safe_num(spot_row.get("volume"))

    if pd.isna(price) or price <= 0:
        return history_df, "实时价格无效"

    df = history_df.copy()
    today = pd.Timestamp.today().normalize()

    last_date = pd.to_datetime(df.iloc[-1]["date"]).normalize()
    last_close = safe_num(df.iloc[-1]["close"])

    if last_date == today:
        df.loc[df.index[-1], "close"] = price
        df.loc[df.index[-1], "pct_change"] = pct if pd.notna(pct) else df.loc[df.index[-1], "pct_change"]
        df.loc[df.index[-1], "amount"] = amount if pd.notna(amount) and amount > 0 else df.loc[df.index[-1], "amount"]
        df.loc[df.index[-1], "volume"] = volume if pd.notna(volume) and volume > 0 else df.loc[df.index[-1], "volume"]
        df.loc[df.index[-1], "high"] = max(safe_num(df.loc[df.index[-1], "high"]), price)
        df.loc[df.index[-1], "low"] = min(safe_num(df.loc[df.index[-1], "low"]), price)
        return df, f"实时快照已更新今日K线：{now_text()}"

    # 历史日线还没到今天，则追加一条“实时估算K线”
    if pd.notna(last_close) and last_close > 0:
        open_price = last_close
    else:
        open_price = price

    high = max(open_price, price)
    low = min(open_price, price)

    if pd.isna(pct):
        pct = (price / open_price - 1) * 100 if open_price > 0 else 0

    new_row = {
        "date": today,
        "open": open_price,
        "close": price,
        "high": high,
        "low": low,
        "volume": volume if pd.notna(volume) else 0,
        "amount": amount if pd.notna(amount) else 0,
        "pct_change": pct,
    }

    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    return df, f"历史日线滞后，已用实时快照追加今日数据：{now_text()}"


# ============================================================
# 演示数据保护层
# ============================================================
def get_base_price(code: str):
    base_map = {
        "510300": 3.8,
        "510050": 2.7,
        "510500": 5.8,
        "512100": 2.3,
        "159915": 1.8,
        "588000": 0.9,
        "515030": 1.1,
        "515790": 0.75,
        "561910": 0.8,
        "512480": 0.8,
        "159995": 0.9,
        "512400": 1.2,
        "516780": 1.0,
        "515220": 1.3,
        "518880": 5.2,
        "513100": 1.6,
        "511990": 100.0,
    }
    return base_map.get(str(code), 1.0)


def generate_demo_history(code: str, days: int = 240):
    seed = abs(hash(str(code))) % (2**32)
    rng = np.random.default_rng(seed)

    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=days)
    base = get_base_price(code)

    returns = rng.normal(loc=0.00025, scale=0.013, size=len(dates))
    trend = np.linspace(-0.025, 0.045, len(dates))
    close = base * np.cumprod(1 + returns) * (1 + trend)

    open_price = close * (1 + rng.normal(0, 0.004, len(dates)))
    high = np.maximum(open_price, close) * (1 + rng.uniform(0.002, 0.016, len(dates)))
    low = np.minimum(open_price, close) * (1 - rng.uniform(0.002, 0.016, len(dates)))
    amount = rng.uniform(1.0e8, 18.0e8, len(dates))
    volume = amount / np.maximum(close, 0.01) / 100

    df = pd.DataFrame(
        {
            "date": dates,
            "open": open_price,
            "close": close,
            "high": high,
            "low": low,
            "volume": volume,
            "amount": amount,
            "pct_change": pd.Series(close).pct_change().fillna(0) * 100,
        }
    )
    return df


def generate_demo_spot(codes):
    rng = np.random.default_rng(int(pd.Timestamp.today().strftime("%Y%m%d")))
    rows = []
    reverse_map = {v: k for k, v in DEFAULT_FUNDS.items()}

    for code in codes:
        code = str(code)
        base = get_base_price(code)
        pct = rng.normal(0, 1.1)
        price = base * (1 + pct / 100)
        rows.append(
            {
                "code": code,
                "name": reverse_map.get(code, f"基金{code}"),
                "price": round(price, 3),
                "pct_change": round(pct, 2),
                "change": round(price - base, 3),
                "volume": rng.uniform(1e6, 2e8),
                "amount": rng.uniform(1e8, 20e8),
                "update_time": now_text(),
            }
        )
    return pd.DataFrame(rows)


# ============================================================
# 安全数据获取层：永远返回可画图数据
# ============================================================
@st.cache_data(ttl=5, show_spinner=False)
def get_safe_spot(codes_tuple):
    codes = list(codes_tuple)
    try:
        df = fetch_spot_from_eastmoney(codes)
        save_df(df, SPOT_CACHE_FILE)
        return df, "东方财富实时行情", ""
    except Exception as e:
        cached = load_df(SPOT_CACHE_FILE)
        if not cached.empty and "code" in cached.columns:
            cached["code"] = cached["code"].astype(str)
            cached = cached[cached["code"].isin([str(x) for x in codes])]
            if not cached.empty:
                return cached, "缓存实时行情", str(e)

        return generate_demo_spot(codes), "演示实时行情", str(e)


@st.cache_data(ttl=30, show_spinner=False)
def get_safe_history(code: str, days: int = 240):
    code = str(code).strip()
    cache_file = history_cache_file(code)

    # 1. 历史真实日线
    try:
        hist = fetch_history_from_eastmoney(code, days)
        save_df(hist, cache_file)
        return hist, "东方财富历史日线", ""
    except Exception as e:
        real_error = str(e)

    # 2. 缓存
    cached = load_df(cache_file)
    if not cached.empty:
        try:
            cached["date"] = pd.to_datetime(cached["date"])
            return cached.tail(days).reset_index(drop=True), "缓存历史日线", real_error
        except Exception:
            pass

    # 3. 演示行情
    return generate_demo_history(code, days), "演示历史行情", real_error


def get_full_analysis_data(code: str, days: int, spot_df: pd.DataFrame):
    hist, hist_source, hist_error = get_safe_history(code, days)

    spot_row = None
    if spot_df is not None and not spot_df.empty and "code" in spot_df.columns:
        hit = spot_df[spot_df["code"].astype(str) == str(code)]
        if not hit.empty:
            spot_row = hit.iloc[0]

    realtime_note = ""
    if hist_source != "演示历史行情" and spot_row is not None:
        hist, realtime_note = apply_realtime_to_history(hist, spot_row)

    hist = enrich_indicators_safe(hist)

    source_parts = [hist_source]
    if realtime_note:
        source_parts.append(realtime_note)

    return hist, "；".join(source_parts), hist_error


# ============================================================
# 指标体系
# ============================================================
def classify_money_signal(row):
    pct = safe_num(row.get("pct_change"))
    ratio = safe_num(row.get("volume_ratio"))
    obv = safe_num(row.get("obv"))
    obv_ma = safe_num(row.get("obv_ma10"))

    if pd.isna(pct) or pd.isna(ratio):
        return "数据不足"

    obv_strong = pd.notna(obv) and pd.notna(obv_ma) and obv > obv_ma
    obv_weak = pd.notna(obv) and pd.notna(obv_ma) and obv < obv_ma

    if pct > 1.2 and ratio >= 1.25 and obv_strong:
        return "强流入"
    if pct > 0.3 and ratio >= 1.05:
        return "温和流入"
    if pct < -1.2 and ratio >= 1.25 and obv_weak:
        return "强撤出"
    if pct < -0.3 and ratio >= 1.05:
        return "温和撤出"
    if abs(pct) < 0.3 and ratio >= 1.3:
        return "分歧放量"
    if ratio < 0.75:
        return "缩量观望"
    return "中性"


def enrich_indicators_safe(df: pd.DataFrame):
    if df is None or df.empty:
        df = generate_demo_history("000000", 240)

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    numeric_cols = ["open", "close", "high", "low", "volume", "amount", "pct_change"]
    for col in numeric_cols:
        if col not in df.columns:
            df[col] = np.nan
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["close"] = df["close"].ffill().bfill()
    df["open"] = df["open"].fillna(df["close"])
    df["high"] = df["high"].fillna(df[["open", "close"]].max(axis=1))
    df["low"] = df["low"].fillna(df[["open", "close"]].min(axis=1))
    df["amount"] = df["amount"].fillna(0)
    df["volume"] = df["volume"].fillna(0)
    df["pct_change"] = df["pct_change"].fillna(df["close"].pct_change() * 100).fillna(0)

    df["ma5"] = df["close"].rolling(5, min_periods=2).mean()
    df["ma10"] = df["close"].rolling(10, min_periods=3).mean()
    df["ma20"] = df["close"].rolling(20, min_periods=5).mean()
    df["ma60"] = df["close"].rolling(60, min_periods=10).mean()

    df["amount_ma20"] = df["amount"].rolling(20, min_periods=5).mean()
    df["volume_ratio"] = df["amount"] / df["amount_ma20"].replace(0, np.nan)
    df["volume_ratio"] = df["volume_ratio"].replace([np.inf, -np.inf], np.nan).fillna(1.0)

    direction = np.where(df["close"].diff() > 0, 1, np.where(df["close"].diff() < 0, -1, 0))
    df["obv"] = (direction * df["volume"].fillna(0)).cumsum()
    df["obv_ma10"] = df["obv"].rolling(10, min_periods=3).mean()

    df["money_strength"] = df["pct_change"] * df["amount"] / 1e8

    df["ma5_dev"] = (df["close"] / df["ma5"] - 1) * 100
    df["ma20_dev"] = (df["close"] / df["ma20"] - 1) * 100
    df["ma60_dev"] = (df["close"] / df["ma60"] - 1) * 100

    df["money_signal"] = df.apply(classify_money_signal, axis=1)
    return df


def compute_summary(df: pd.DataFrame):
    if df is None or df.empty:
        df = enrich_indicators_safe(generate_demo_history("000000", 240))

    latest = df.iloc[-1]
    close = safe_num(latest["close"])

    trend_score = 0
    if pd.notna(latest["ma5"]) and close > latest["ma5"]:
        trend_score += 1
    if pd.notna(latest["ma20"]) and close > latest["ma20"]:
        trend_score += 1
    if pd.notna(latest["ma60"]) and close > latest["ma60"]:
        trend_score += 1
    if pd.notna(latest["ma5"]) and pd.notna(latest["ma20"]) and latest["ma5"] > latest["ma20"]:
        trend_score += 1
    if pd.notna(latest["ma20"]) and pd.notna(latest["ma60"]) and latest["ma20"] > latest["ma60"]:
        trend_score += 1

    if trend_score >= 4:
        trend_label = "趋势偏强"
    elif trend_score == 3:
        trend_label = "趋势修复"
    elif trend_score == 2:
        trend_label = "震荡偏弱"
    else:
        trend_label = "趋势偏弱"

    bias20 = safe_num(latest["ma20_dev"])
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

    money_signal = latest["money_signal"]

    if trend_label in ["趋势偏强", "趋势修复"] and money_signal in ["强流入", "温和流入"]:
        action = "持有观察 / 不宜追高"
    elif trend_label == "趋势偏弱" and money_signal in ["强撤出", "温和撤出"]:
        action = "谨慎观望"
    elif risk_label in ["深度回调", "回调区"] and money_signal not in ["强撤出"]:
        action = "小额定投观察"
    elif risk_label == "短期过热":
        action = "避免追高"
    else:
        action = "震荡观察"

    comment = generate_commentary(latest, trend_label, risk_label, money_signal, action)

    return {
        "trend_score": trend_score,
        "trend_label": trend_label,
        "risk_label": risk_label,
        "money_signal": money_signal,
        "action": action,
        "comment": comment,
    }


def generate_commentary(latest, trend_label, risk_label, money_signal, action):
    close = safe_num(latest["close"])
    lines = []

    if pd.notna(latest["ma5"]):
        if close > latest["ma5"]:
            lines.append("价格位于5日均线上方，短线动能尚可。")
        else:
            lines.append("价格低于5日均线，短线动能偏弱。")

    if pd.notna(latest["ma20"]):
        if close > latest["ma20"]:
            lines.append("价格站上20日均线，短期结构处于修复或偏强区间。")
        else:
            lines.append("价格低于20日均线，短期趋势仍需谨慎。")

    if pd.notna(latest["ma60"]):
        if close > latest["ma60"]:
            lines.append("价格处于60日均线上方，中期结构相对稳定。")
        else:
            lines.append("价格低于60日均线，中期趋势仍偏弱。")

    ratio = safe_num(latest["volume_ratio"])
    if pd.notna(ratio):
        if ratio >= 1.5:
            lines.append(f"当前成交额约为20日均值的 {ratio:.2f} 倍，属于明显放量。")
        elif ratio >= 1.1:
            lines.append(f"当前成交额约为20日均值的 {ratio:.2f} 倍，量能有所放大。")
        elif ratio < 0.75:
            lines.append(f"当前成交额约为20日均值的 {ratio:.2f} 倍，市场参与度偏低。")
        else:
            lines.append(f"当前成交额约为20日均值的 {ratio:.2f} 倍，量能处于正常区间。")

    if money_signal in ["强流入", "温和流入"]:
        lines.append("资金行为代理指标显示偏流入，短线情绪有所改善。")
    elif money_signal in ["强撤出", "温和撤出"]:
        lines.append("资金行为代理指标显示偏撤出，需要警惕继续回落。")
    elif money_signal == "缩量观望":
        lines.append("当前缩量明显，说明资金参与意愿不足，更适合等待方向选择。")
    elif money_signal == "分歧放量":
        lines.append("当前属于放量分歧状态，多空力量博弈增强。")

    lines.append(f"综合判断：{trend_label}，风险状态为{risk_label}，策略更偏向“{action}”。")
    return "\n\n".join(lines)


# ============================================================
# 图表
# ============================================================
def make_price_chart(df: pd.DataFrame, title=""):
    if df is None or df.empty:
        df = enrich_indicators_safe(generate_demo_history("000000", 240))
        title = title + "｜演示占位图"

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.07,
        row_heights=[0.58, 0.22, 0.20],
        subplot_titles=("价格/净值趋势与均线结构", "成交额与量能变化", "资金行为强度"),
    )

    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["close"],
            mode="lines",
            name="价格/净值",
            line=dict(color="#F8FAFC", width=2.8),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["ma5"],
            mode="lines",
            name="MA5",
            line=dict(color="#38BDF8", width=1.5),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["ma20"],
            mode="lines",
            name="MA20",
            line=dict(color="#FBBF24", width=1.6),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["ma60"],
            mode="lines",
            name="MA60",
            line=dict(color="#A78BFA", width=1.6),
        ),
        row=1,
        col=1,
    )

    strong_in = df[df["money_signal"] == "强流入"]
    strong_out = df[df["money_signal"] == "强撤出"]

    if not strong_in.empty:
        fig.add_trace(
            go.Scatter(
                x=strong_in["date"],
                y=strong_in["close"],
                mode="markers",
                name="强流入",
                marker=dict(size=10, color="#22C55E", symbol="triangle-up"),
            ),
            row=1,
            col=1,
        )

    if not strong_out.empty:
        fig.add_trace(
            go.Scatter(
                x=strong_out["date"],
                y=strong_out["close"],
                mode="markers",
                name="强撤出",
                marker=dict(size=10, color="#EF4444", symbol="triangle-down"),
            ),
            row=1,
            col=1,
        )

    amount_colors = np.where(df["pct_change"] >= 0, "#22C55E", "#EF4444")

    fig.add_trace(
        go.Bar(
            x=df["date"],
            y=df["amount"] / 1e8,
            name="成交额/亿",
            marker_color=amount_colors,
            opacity=0.72,
        ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["amount_ma20"] / 1e8,
            mode="lines",
            name="成交额MA20/亿",
            line=dict(color="#FBBF24", width=1.5),
        ),
        row=2,
        col=1,
    )

    money_colors = np.where(df["money_strength"] >= 0, "#22C55E", "#EF4444")
    fig.add_trace(
        go.Bar(
            x=df["date"],
            y=df["money_strength"],
            name="资金行为强度",
            marker_color=money_colors,
            opacity=0.75,
        ),
        row=3,
        col=1,
    )

    fig.add_hline(y=0, line_width=1, line_dash="dot", line_color="#94A3B8", row=3, col=1)

    fig.update_layout(
        title=dict(text=title, font=dict(color="#F8FAFC", size=18)),
        height=820,
        template="plotly_dark",
        plot_bgcolor="#0F172A",
        paper_bgcolor="#0F172A",
        font=dict(color="#F8FAFC", size=13),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            y=1.08,
            x=0,
            bgcolor="rgba(15,23,42,0.78)",
            bordercolor="rgba(148,163,184,0.15)",
            borderwidth=1,
        ),
        margin=dict(l=28, r=28, t=95, b=35),
    )

    fig.update_xaxes(gridcolor="rgba(148,163,184,0.16)")
    fig.update_yaxes(gridcolor="rgba(148,163,184,0.16)")

    for ann in fig["layout"]["annotations"]:
        ann["font"] = dict(size=15, color="#F8FAFC")

    return fig


def make_radar(summary, latest):
    values = [
        summary["trend_score"] / 5 * 100,
        min(max(safe_num(latest["volume_ratio"], 1), 0), 2) / 2 * 100,
        100 - min(abs(safe_num(latest["ma20_dev"], 0)) / 12 * 100, 100),
        70 if summary["money_signal"] in ["强流入", "温和流入"] else 45 if summary["money_signal"] == "中性" else 30,
        80 if summary["risk_label"] == "正常波动" else 55,
    ]
    labels = ["趋势结构", "量能活跃", "风险位置", "资金行为", "稳定性"]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=values + [values[0]],
            theta=labels + [labels[0]],
            fill="toself",
            name="综合评分",
            line=dict(color="#58D5FF", width=2),
            fillcolor="rgba(88,213,255,0.22)",
        )
    )
    fig.update_layout(
        height=420,
        template="plotly_dark",
        paper_bgcolor="#0F172A",
        plot_bgcolor="#0F172A",
        font=dict(color="#F8FAFC"),
        polar=dict(
            bgcolor="#0F172A",
            radialaxis=dict(visible=True, range=[0, 100], gridcolor="rgba(148,163,184,0.20)"),
            angularaxis=dict(gridcolor="rgba(148,163,184,0.20)"),
        ),
        margin=dict(l=30, r=30, t=40, b=30),
    )
    return fig


# ============================================================
# 持仓导入与组合分析
# ============================================================
def normalize_position_columns(df: pd.DataFrame):
    if df is None or df.empty:
        return pd.DataFrame(columns=["code", "name", "shares", "cost_price", "buy_date", "account_type", "notes"])

    df = df.copy()
    rename_map = {}

    for col in df.columns:
        c = str(col).strip()
        if c in ["基金代码", "代码", "ETF代码", "fund_code", "code"]:
            rename_map[col] = "code"
        elif c in ["基金名称", "名称", "fund_name", "name"]:
            rename_map[col] = "name"
        elif c in ["份额", "持有份额", "shares"]:
            rename_map[col] = "shares"
        elif c in ["成本价", "持仓成本", "买入成本", "cost_price"]:
            rename_map[col] = "cost_price"
        elif c in ["买入日期", "buy_date"]:
            rename_map[col] = "buy_date"
        elif c in ["账户类型", "account_type"]:
            rename_map[col] = "account_type"
        elif c in ["备注", "notes"]:
            rename_map[col] = "notes"

    df = df.rename(columns=rename_map)

    for col in ["code", "name", "shares", "cost_price", "buy_date", "account_type", "notes"]:
        if col not in df.columns:
            df[col] = ""

    df["code"] = df["code"].astype(str).str.replace(".0", "", regex=False).str.zfill(6)
    df["shares"] = pd.to_numeric(df["shares"], errors="coerce").fillna(0)
    df["cost_price"] = pd.to_numeric(df["cost_price"], errors="coerce").fillna(0)
    df["name"] = df["name"].astype(str)

    return df[["code", "name", "shares", "cost_price", "buy_date", "account_type", "notes"]]


def get_demo_positions():
    return pd.DataFrame(
        [
            {"code": "510300", "name": "沪深300ETF", "shares": 8000, "cost_price": 3.65, "buy_date": "2025-10-01", "account_type": "样例账户", "notes": "样例持仓"},
            {"code": "515030", "name": "新能源车ETF", "shares": 12000, "cost_price": 1.65, "buy_date": "2025-10-01", "account_type": "样例账户", "notes": "样例持仓"},
            {"code": "512480", "name": "半导体ETF", "shares": 15000, "cost_price": 0.78, "buy_date": "2025-10-01", "account_type": "样例账户", "notes": "样例持仓"},
            {"code": "518880", "name": "黄金ETF", "shares": 3000, "cost_price": 4.80, "buy_date": "2025-10-01", "account_type": "样例账户", "notes": "样例持仓"},
        ]
    )


def compute_positions(positions: pd.DataFrame, spot_df: pd.DataFrame):
    if positions is None or positions.empty:
        return pd.DataFrame()

    pos = positions.copy()
    pos["code"] = pos["code"].astype(str).str.zfill(6)

    spot = spot_df.copy()
    if spot is None or spot.empty:
        spot = generate_demo_spot(pos["code"].tolist())

    spot["code"] = spot["code"].astype(str).str.zfill(6)
    merged = pos.merge(spot[["code", "price", "pct_change", "amount"]], on="code", how="left")

    merged["price"] = pd.to_numeric(merged["price"], errors="coerce")
    merged["current_value"] = merged["shares"] * merged["price"]
    merged["cost_value"] = merged["shares"] * merged["cost_price"]
    merged["profit"] = merged["current_value"] - merged["cost_value"]
    merged["profit_rate"] = merged["profit"] / merged["cost_value"].replace(0, np.nan) * 100
    merged["weight"] = merged["current_value"] / merged["current_value"].sum() * 100

    return merged


def make_portfolio_curve(position_df: pd.DataFrame):
    if position_df is None or position_df.empty:
        position_df = get_demo_positions()

    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=120)
    rng = np.random.default_rng(2026)

    base = position_df["shares"].sum() * 10 if "shares" in position_df.columns else 100000
    returns = rng.normal(0.00035, 0.0065, len(dates))
    curve = base * np.cumprod(1 + returns)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=curve,
            mode="lines",
            name="组合净值估算",
            line=dict(color="#58D5FF", width=2.6),
            fill="tozeroy",
            fillcolor="rgba(88,213,255,0.16)",
        )
    )

    fig.update_layout(
        height=390,
        template="plotly_dark",
        paper_bgcolor="#0F172A",
        plot_bgcolor="#0F172A",
        font=dict(color="#F8FAFC"),
        margin=dict(l=30, r=30, t=45, b=30),
        title="实仓收益曲线",
    )
    fig.update_xaxes(gridcolor="rgba(148,163,184,0.16)")
    fig.update_yaxes(gridcolor="rgba(148,163,184,0.16)")
    return fig


# ============================================================
# 页面渲染工具
# ============================================================
def render_status(source_text: str):
    if "演示" in source_text:
        st.markdown(
            '<div class="status-danger">当前数据源：演示行情，仅用于界面展示，不作为投资参考。</div>',
            unsafe_allow_html=True,
        )
    elif "缓存" in source_text:
        st.markdown(
            '<div class="status-warn">当前数据源：缓存行情，真实接口暂时不可用或返回延迟。</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="status-ok">当前数据源：东方财富真实行情接口正常，已尝试用实时快照更新最新交易日。</div>',
            unsafe_allow_html=True,
        )


def find_module_by_code(code: str):
    code = str(code).strip()
    for module, items in ETF_MODULES.items():
        for name, c in items.items():
            if c == code:
                return module, name
    return "自定义", f"基金{code}"


# ============================================================
# 侧边栏
# ============================================================
st.sidebar.markdown("## 📊 基金智能分析平台")
st.sidebar.caption("实仓导入 · 实时分析 · 专业解读 · 自定义搜索")

search_text = st.sidebar.text_input("全局搜索", placeholder="输入基金代码、名称、模块关键词")

st.sidebar.divider()

page = st.sidebar.radio(
    "功能导航",
    ["首页总览", "基金分析", "实仓管理", "模块行情", "自定义搜索", "设置中心"],
    index=0,
)

st.sidebar.divider()

module_name = st.sidebar.selectbox("选择基金模块", list(ETF_MODULES.keys()), index=2)
module_funds = ETF_MODULES[module_name]
selected_name = st.sidebar.selectbox("选择模块内基金/ETF", list(module_funds.keys()), index=0)

custom_mode = st.sidebar.checkbox("用户自查：手动输入基金/ETF代码", value=False)

if custom_mode:
    selected_code = st.sidebar.text_input("输入6位基金/ETF代码", value=module_funds[selected_name]).strip().zfill(6)
    selected_display_name = f"自查基金 {selected_code}"
else:
    selected_code = module_funds[selected_name]
    selected_display_name = selected_name

days = st.sidebar.slider("历史分析周期", 80, 520, 240, 20)

auto_refresh = st.sidebar.checkbox("自动刷新", value=False)
refresh_seconds = st.sidebar.slider("刷新间隔/秒", 15, 600, 60, 15)

if st.sidebar.button("刷新行情缓存"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.caption(f"页面时间：{now_text()}")


# ============================================================
# 数据准备
# ============================================================
module_codes = list(module_funds.values())
watch_codes = module_codes.copy()
if selected_code not in watch_codes:
    watch_codes.insert(0, selected_code)

# 如果实仓存在，则把实仓代码也加入实时快照请求
if "positions" in st.session_state and st.session_state["positions"] is not None and not st.session_state["positions"].empty:
    for c in st.session_state["positions"]["code"].astype(str).tolist():
        c = c.zfill(6)
        if c not in watch_codes:
            watch_codes.append(c)

spot_df, spot_source, spot_error = get_safe_spot(tuple(watch_codes))
hist_df, hist_source, hist_error = get_full_analysis_data(selected_code, days, spot_df)
summary = compute_summary(hist_df)
latest = hist_df.iloc[-1]

selected_spot = pd.DataFrame()
if spot_df is not None and not spot_df.empty and "code" in spot_df.columns:
    selected_spot = spot_df[spot_df["code"].astype(str) == str(selected_code)]

if not selected_spot.empty:
    real_name = selected_spot.iloc[0].get("name", selected_display_name)
    realtime_price = safe_num(selected_spot.iloc[0].get("price"))
    realtime_pct = safe_num(selected_spot.iloc[0].get("pct_change"))
    realtime_amount = safe_num(selected_spot.iloc[0].get("amount"))
else:
    real_name = selected_display_name
    realtime_price = safe_num(latest["close"])
    realtime_pct = safe_num(latest["pct_change"])
    realtime_amount = safe_num(latest["amount"])


# ============================================================
# 顶部标题
# ============================================================
st.markdown('<div class="main-title">FundPilot Pro ｜ 基金智能分析平台</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">实仓导入 · 模块轮动 · 趋势风控 · 专业解读 · 自定义搜索 · 东方财富实时行情</div>',
    unsafe_allow_html=True,
)

render_status(f"{spot_source}；{hist_source}")

# ============================================================
# 首页总览
# ============================================================
if page == "首页总览":
    positions = st.session_state.get("positions", pd.DataFrame())

    if positions is None or positions.empty:
        st.markdown(
            '<div class="status-warn">当前未导入实仓，首页显示样例组合。导入实仓后将自动切换为真实持仓分析。</div>',
            unsafe_allow_html=True,
        )
        positions = get_demo_positions()
        portfolio_mode = "样例组合"
    else:
        portfolio_mode = "真实实仓"

    position_detail = compute_positions(positions, spot_df)

    total_asset = position_detail["current_value"].sum() if not position_detail.empty else 0
    total_cost = position_detail["cost_value"].sum() if not position_detail.empty else 0
    total_profit = total_asset - total_cost
    profit_rate = total_profit / total_cost * 100 if total_cost > 0 else 0

    strongest_count = 0
    market_table = spot_df.copy()
    if market_table is not None and not market_table.empty and "pct_change" in market_table.columns:
        strongest_count = int((market_table["pct_change"] > 1.0).sum())

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("总资产", format_money(total_asset))
    c2.metric("今日盈亏估算", format_money((position_detail["current_value"] * position_detail["pct_change"] / 100).sum() if not position_detail.empty else 0))
    c3.metric("累计收益", format_money(total_profit), format_pct(profit_rate))
    c4.metric("持仓基金数", len(position_detail))
    c5.metric("当前风险等级", "中")
    c6.metric("强势模块数量", strongest_count)

    st.markdown('<div class="info-line">当前模式：{}；实时行情：{}；历史行情：{}</div>'.format(portfolio_mode, spot_source, hist_source), unsafe_allow_html=True)

    left, right = st.columns([1.15, 1])

    with left:
        st.plotly_chart(make_portfolio_curve(position_detail), use_container_width=True)

    with right:
        radar = make_radar(summary, latest)
        st.plotly_chart(radar, use_container_width=True)

    st.markdown('<div class="chart-panel"><div class="panel-title">今日重点信号</div><div class="panel-subtitle">基于当前关注模块与所选基金生成</div></div>', unsafe_allow_html=True)

    sig1, sig2, sig3 = st.columns(3)
    sig1.info(f"当前关注基金：{real_name}（{selected_code}）")
    sig2.warning(f"风险状态：{summary['risk_label']}；策略提示：{summary['action']}")
    sig3.success(f"资金信号：{summary['money_signal']}；趋势评分：{summary['trend_score']} / 5")


# ============================================================
# 基金分析
# ============================================================
elif page == "基金分析":
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("基金/ETF", real_name)
    c2.metric("当前价/净值", f"{realtime_price:.3f}" if pd.notna(realtime_price) else "暂无")
    c3.metric("今日涨跌幅", format_pct(realtime_pct))
    c4.metric("成交额", format_money(realtime_amount))
    c5.metric("资金信号", summary["money_signal"])

    c6, c7, c8, c9, c10 = st.columns(5)
    c6.metric("趋势评分", f"{summary['trend_score']} / 5")
    c7.metric("趋势状态", summary["trend_label"])
    c8.metric("风险状态", summary["risk_label"])
    c9.metric("量能倍率", f"{safe_num(latest['volume_ratio'], 1):.2f}x")
    c10.metric("策略提示", summary["action"])

    st.markdown(
        f"""
        <div class="info-line">
        当前模块：{module_name}；实时行情：{spot_source}；历史行情：{hist_source}；
        最新图表日期：{pd.to_datetime(latest['date']).strftime('%Y-%m-%d')}；
        页面获取时间：{now_text()}
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab1, tab2, tab3, tab4 = st.tabs(["📈 专业看盘图", "🧠 专业解读", "🔥 模块行情池", "📋 信号明细"])

    with tab1:
        st.markdown(
            f"""
            <div class="chart-panel">
                <div class="panel-title">{real_name}（{selected_code}）</div>
                <div class="panel-subtitle">趋势结构 / 成交额 / 资金行为代理信号 / 实时快照更新</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.plotly_chart(make_price_chart(hist_df, f"{real_name}（{selected_code}）专业趋势分析"), use_container_width=True)

    with tab2:
        left, right = st.columns([1.15, 1])

        with left:
            st.markdown(
                f"""
                <div class="signal-card">
                    <div class="signal-title">专业理财师解读</div>
                    <div class="signal-text">{summary["comment"].replace(chr(10), "<br>")}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                """
                <div class="signal-card">
                    <div class="signal-title">操作边界</div>
                    <div class="signal-text">
                    <span class="good">适合继续持有</span>：趋势评分较高且资金信号未明显恶化。<br>
                    <span class="warn">不宜追高</span>：MA20偏离过高，短期上涨过快。<br>
                    <span class="bad">需要防守</span>：放量下跌、跌破20日均线、资金信号转为强撤出。<br>
                    以上为基于公开行情的量化辅助判断，不构成个性化投资建议。
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with right:
            st.plotly_chart(make_radar(summary, latest), use_container_width=True)

    with tab3:
        market = spot_df.copy()
        if market is None or market.empty:
            market = generate_demo_spot(watch_codes)

        market["code"] = market["code"].astype(str)
        market = market[market["code"].isin([str(x) for x in watch_codes])]

        if not market.empty:
            market_show = market.copy()
            market_show["成交额"] = market_show["amount"].apply(format_money)
            market_show = market_show.rename(
                columns={
                    "code": "代码",
                    "name": "名称",
                    "price": "最新价",
                    "pct_change": "涨跌幅",
                    "change": "涨跌额",
                }
            )
            keep = [c for c in ["代码", "名称", "最新价", "涨跌幅", "涨跌额", "成交额", "update_time"] if c in market_show.columns]
            market_show = market_show[keep].sort_values("涨跌幅", ascending=False)
            st.dataframe(market_show, use_container_width=True, height=520, hide_index=True)

    with tab4:
        detail = hist_df[
            [
                "date",
                "close",
                "pct_change",
                "amount",
                "volume_ratio",
                "money_strength",
                "money_signal",
                "ma5_dev",
                "ma20_dev",
                "ma60_dev",
            ]
        ].copy()

        detail["date"] = detail["date"].dt.strftime("%Y-%m-%d")
        detail["amount"] = detail["amount"].apply(format_money)
        detail["pct_change"] = detail["pct_change"].apply(format_pct)
        detail["volume_ratio"] = detail["volume_ratio"].map(lambda x: f"{x:.2f}x" if pd.notna(x) else "暂无")
        detail["money_strength"] = detail["money_strength"].map(lambda x: f"{x:.2f}" if pd.notna(x) else "暂无")
        detail["ma5_dev"] = detail["ma5_dev"].apply(format_pct)
        detail["ma20_dev"] = detail["ma20_dev"].apply(format_pct)
        detail["ma60_dev"] = detail["ma60_dev"].apply(format_pct)

        detail = detail.rename(
            columns={
                "date": "日期",
                "close": "收盘",
                "pct_change": "日涨跌幅",
                "amount": "成交额",
                "volume_ratio": "量能倍率",
                "money_strength": "资金行为强度",
                "money_signal": "资金信号",
                "ma5_dev": "均线偏离_MA5",
                "ma20_dev": "均线偏离_MA20",
                "ma60_dev": "均线偏离_MA60",
            }
        )
        st.dataframe(detail.sort_values("日期", ascending=False), use_container_width=True, height=560, hide_index=True)


# ============================================================
# 实仓管理
# ============================================================
elif page == "实仓管理":
    st.markdown('<div class="chart-panel"><div class="panel-title">实仓导入与组合诊断</div><div class="panel-subtitle">支持 Excel / CSV 导入，也支持样例组合演示</div></div>', unsafe_allow_html=True)

    uploaded = st.file_uploader("上传实仓文件：Excel / CSV", type=["xlsx", "xls", "csv"])

    if uploaded is not None:
        try:
            if uploaded.name.endswith(".csv"):
                pos_raw = pd.read_csv(uploaded)
            else:
                pos_raw = pd.read_excel(uploaded)

            positions = normalize_position_columns(pos_raw)
            st.session_state["positions"] = positions
            save_df(positions, POSITION_CACHE_FILE)
            st.success("实仓导入成功")
        except Exception as e:
            st.error(f"实仓导入失败：{e}")

    if "positions" not in st.session_state:
        cached_pos = load_df(POSITION_CACHE_FILE)
        if not cached_pos.empty:
            st.session_state["positions"] = normalize_position_columns(cached_pos)

    positions = st.session_state.get("positions", pd.DataFrame())

    if positions is None or positions.empty:
        st.warning("当前未导入实仓，下面显示样例组合。")
        positions = get_demo_positions()

    pos_detail = compute_positions(positions, spot_df)

    if not pos_detail.empty:
        total_asset = pos_detail["current_value"].sum()
        total_cost = pos_detail["cost_value"].sum()
        total_profit = total_asset - total_cost
        profit_rate = total_profit / total_cost * 100 if total_cost > 0 else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("组合市值", format_money(total_asset))
        c2.metric("投入成本", format_money(total_cost))
        c3.metric("浮动盈亏", format_money(total_profit), format_pct(profit_rate))
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
                "price": "当前价",
                "pct_change": "今日涨跌幅",
            }
        )
        keep = ["代码", "名称", "份额", "成本价", "当前价", "当前市值", "成本金额", "浮盈亏", "收益率", "仓位占比"]
        st.dataframe(show[keep], use_container_width=True, height=460, hide_index=True)

    st.markdown(
        """
        <div class="signal-card">
            <div class="signal-title">实仓导入模板字段</div>
            <div class="signal-text">
            推荐字段：基金代码、基金名称、持有份额、持仓成本、买入日期、账户类型、备注。<br>
            系统会自动识别：代码 / 基金代码 / ETF代码，名称 / 基金名称，份额 / 持有份额，成本价 / 持仓成本。
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# 模块行情
# ============================================================
elif page == "模块行情":
    st.markdown(f'<div class="chart-panel"><div class="panel-title">{module_name} 模块行情池</div><div class="panel-subtitle">模块内基金实时强弱排名</div></div>', unsafe_allow_html=True)

    market = spot_df.copy()
    if market is None or market.empty:
        market = generate_demo_spot(watch_codes)

    market["code"] = market["code"].astype(str)
    market = market[market["code"].isin([str(x) for x in watch_codes])]

    if not market.empty:
        market_show = market.copy()
        market_show["成交额"] = market_show["amount"].apply(format_money)
        market_show = market_show.rename(columns={"code": "代码", "name": "名称", "price": "最新价", "pct_change": "涨跌幅", "change": "涨跌额"})
        keep = [c for c in ["代码", "名称", "最新价", "涨跌幅", "涨跌额", "成交额", "update_time"] if c in market_show.columns]
        st.dataframe(market_show[keep].sort_values("涨跌幅", ascending=False), use_container_width=True, height=620, hide_index=True)

    all_rows = []
    for m, items in ETF_MODULES.items():
        for n, c in items.items():
            all_rows.append({"模块": m, "名称": n, "代码": c})
    st.subheader("全模块基金池")
    st.dataframe(pd.DataFrame(all_rows), use_container_width=True, height=420, hide_index=True)


# ============================================================
# 自定义搜索
# ============================================================
elif page == "自定义搜索":
    st.markdown('<div class="chart-panel"><div class="panel-title">自定义基金搜索</div><div class="panel-subtitle">输入代码、名称或模块关键词，支持任意6位基金/ETF代码自查</div></div>', unsafe_allow_html=True)

    keyword = st.text_input("搜索关键词", value=search_text)

    all_rows = []
    for m, items in ETF_MODULES.items():
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

        st.dataframe(result, use_container_width=True, height=460, hide_index=True)

        if kw.isdigit() and len(kw) == 6:
            if st.button(f"立即分析 {kw}"):
                st.session_state["jump_code"] = kw
                st.info("请在左侧打开“用户自查”，输入该代码即可查看完整分析。")
    else:
        st.info("请输入基金代码、名称或模块关键词。")


# ============================================================
# 设置中心
# ============================================================
elif page == "设置中心":
    st.markdown('<div class="chart-panel"><div class="panel-title">设置中心</div><div class="panel-subtitle">缓存、数据源、说明与导出</div></div>', unsafe_allow_html=True)

    st.write("当前数据源：东方财富公开行情接口")
    st.write("实时缓存：5 秒")
    st.write("历史缓存：30 秒")

    if st.button("清除所有缓存"):
        st.cache_data.clear()
        for f in CACHE_DIR.glob("*.csv"):
            try:
                f.unlink()
            except Exception:
                pass
        st.success("缓存已清除，请刷新页面。")

    st.warning("公开行情接口不等于券商 Level-2 数据，资金信号为基于成交额、涨跌幅、OBV 和均线结构构建的代理指标。")


# ============================================================
# 自动刷新
# ============================================================
if auto_refresh:
    time.sleep(refresh_seconds)
    st.rerun()
