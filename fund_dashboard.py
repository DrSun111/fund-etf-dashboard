import io
import re
import json
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
# 基础路径
# ============================================================
CACHE_DIR = Path(".fund_real_cache")
CACHE_DIR.mkdir(exist_ok=True)

POSITION_FILE = CACHE_DIR / "positions.csv"


# ============================================================
# 深色专业界面 CSS
# ============================================================
CUSTOM_CSS = """
<style>
[data-testid="stHeader"] {
    background: rgba(5, 8, 22, 0) !important;
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

html, body, [data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at top left, rgba(37, 99, 235, 0.20), transparent 25%),
        radial-gradient(circle at top right, rgba(20, 184, 166, 0.12), transparent 22%),
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
    border-right: 1px solid rgba(88, 213, 255, 0.16);
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

.status-ok {
    background: linear-gradient(90deg, rgba(20, 83, 45, 0.86), rgba(6, 78, 59, 0.86));
    border: 1px solid rgba(74, 222, 128, 0.24);
    color: #D9FFF2 !important;
    padding: 13px 18px;
    border-radius: 16px;
    font-weight: 750;
    margin-bottom: 14px;
}

.status-warn {
    background: linear-gradient(90deg, rgba(113, 63, 18, 0.88), rgba(92, 52, 12, 0.88));
    border: 1px solid rgba(251, 191, 36, 0.26);
    color: #FFF4CF !important;
    padding: 13px 18px;
    border-radius: 16px;
    font-weight: 750;
    margin-bottom: 14px;
}

.status-danger {
    background: linear-gradient(90deg, rgba(127, 29, 29, 0.90), rgba(76, 29, 49, 0.88));
    border: 1px solid rgba(248, 113, 113, 0.28);
    color: #FFE4E6 !important;
    padding: 13px 18px;
    border-radius: 16px;
    font-weight: 750;
    margin-bottom: 14px;
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
    "场外基金示例": {
        "易方达蓝筹精选": "005827",
        "中欧医疗健康A": "003095",
        "诺安成长混合": "320007",
        "兴全合润混合": "163406",
        "招商中证白酒A": "161725",
    },
}

ALL_PRESET_FUNDS = {}
for m, items in FUND_MODULES.items():
    ALL_PRESET_FUNDS.update(items)


# ============================================================
# 基础工具函数
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


def request_get(url, params=None, timeout=8, text=False):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json,text/plain,*/*",
        "Referer": "https://fund.eastmoney.com/",
    }

    r = requests.get(url, params=params, headers=headers, timeout=timeout)
    r.raise_for_status()

    if text:
        r.encoding = "utf-8"
        return r.text
    return r.json()


def detect_market(code: str):
    code = str(code).strip()
    if code.startswith(("5", "6", "9")):
        return "SH"
    return "SZ"


def secid(code: str):
    code = str(code).strip()
    return f"1.{code}" if detect_market(code) == "SH" else f"0.{code}"


def is_exchange_fund(code: str):
    """
    判断是否优先作为场内基金/ETF/LOF处理。
    场内基金通常可以用东方财富 push2 / push2his 接口。
    """
    code = str(code).strip()
    prefixes = (
        "15", "16", "18",
        "50", "51", "52", "56", "58",
        "159", "160", "161", "162", "163", "164", "165", "166", "167", "168", "169",
        "511",
    )
    return code.startswith(prefixes)


def clean_code(code: str):
    return str(code).strip().replace(".0", "").zfill(6)


# ============================================================
# 东方财富真实数据：场内基金 / ETF
# ============================================================
def fetch_exchange_spot(codes):
    codes = [clean_code(c) for c in codes if str(c).strip()]
    codes = list(dict.fromkeys(codes))

    if not codes:
        return pd.DataFrame()

    url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
    params = {
        "fltt": "2",
        "secids": ",".join(secid(c) for c in codes),
        "fields": "f12,f14,f2,f3,f4,f5,f6",
    }

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
                "data_type": "场内实时行情",
                "update_time": now_text(),
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("东方财富场内实时行情返回为空")
    return df


def fetch_exchange_history(code: str, days: int = 240):
    code = clean_code(code)

    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "secid": secid(code),
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",
        "fqt": "0",
        "beg": "20000101",
        "end": dt.datetime.now().strftime("%Y%m%d"),
        "lmt": str(max(days * 2, 600)),
    }

    data = request_get(url, params=params, timeout=8)
    klines = data.get("data", {}).get("klines", [])

    if not klines:
        raise RuntimeError("东方财富场内历史K线返回为空")

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
                "data_type": "场内历史K线",
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("东方财富场内历史K线解析为空")

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df.tail(days).reset_index(drop=True)


def apply_exchange_spot_to_history(history: pd.DataFrame, spot_row: pd.Series):
    """
    用场内实时价格更新或追加今日K线。
    """
    if history is None or history.empty or spot_row is None:
        return history, "未应用实时快照"

    price = safe_num(spot_row.get("price"))
    pct = safe_num(spot_row.get("pct_change"))
    amount = safe_num(spot_row.get("amount"))
    volume = safe_num(spot_row.get("volume"))

    if pd.isna(price) or price <= 0:
        return history, "实时价格无效"

    df = history.copy()
    today = pd.Timestamp.today().normalize()
    last_date = pd.to_datetime(df.iloc[-1]["date"]).normalize()

    if last_date == today:
        idx = df.index[-1]
        df.loc[idx, "close"] = price
        df.loc[idx, "pct_change"] = pct if pd.notna(pct) else df.loc[idx, "pct_change"]
        df.loc[idx, "amount"] = amount if pd.notna(amount) and amount > 0 else df.loc[idx, "amount"]
        df.loc[idx, "volume"] = volume if pd.notna(volume) and volume > 0 else df.loc[idx, "volume"]
        df.loc[idx, "high"] = max(safe_num(df.loc[idx, "high"]), price)
        df.loc[idx, "low"] = min(safe_num(df.loc[idx, "low"]), price)
        return df, f"已用实时快照更新今日K线：{now_text()}"

    last_close = safe_num(df.iloc[-1]["close"])
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
        "data_type": "场内实时快照追加",
    }

    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    return df, f"历史K线未到今日，已用实时快照追加今日数据：{now_text()}"


# ============================================================
# 东方财富真实数据：场外基金净值
# ============================================================
def fetch_otc_fund_history(code: str, days: int = 240):
    """
    场外基金真实净值数据。
    来源：东方财富基金页面 pingzhongdata。
    注意：场外基金不是盘中实时价格，通常是最新公布净值。
    """
    code = clean_code(code)
    url = f"https://fund.eastmoney.com/pingzhongdata/{code}.js"

    text = request_get(url, timeout=8, text=True)

    name_match = re.search(r'var fS_name = "(.+?)";', text)
    name = name_match.group(1) if name_match else f"基金{code}"

    nav_match = re.search(r"var Data_netWorthTrend = (\[.*?\]);", text, re.S)
    if not nav_match:
        raise RuntimeError("未解析到场外基金净值数据")

    raw = json.loads(nav_match.group(1))

    rows = []
    for item in raw:
        t = item.get("x")
        y = item.get("y")
        equity_return = item.get("equityReturn", np.nan)

        if t is None or y is None:
            continue

        rows.append(
            {
                "date": pd.to_datetime(t, unit="ms"),
                "open": safe_num(y),
                "close": safe_num(y),
                "high": safe_num(y),
                "low": safe_num(y),
                "volume": 0,
                "amount": 0,
                "pct_change": safe_num(equity_return),
                "data_type": "场外基金净值",
                "fund_name": name,
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("场外基金净值数据为空")

    df["pct_change"] = df["pct_change"].fillna(df["close"].pct_change() * 100).fillna(0)
    df = df.sort_values("date").reset_index(drop=True)
    return df.tail(days).reset_index(drop=True), name


# ============================================================
# 统一真实数据入口
# ============================================================
@st.cache_data(ttl=20, show_spinner=False)
def get_real_spot_for_codes(codes_tuple):
    """
    仅对场内基金/ETF获取实时行情。
    场外基金不做伪实时。
    """
    codes = [clean_code(c) for c in list(codes_tuple)]
    exchange_codes = [c for c in codes if is_exchange_fund(c)]

    if not exchange_codes:
        return pd.DataFrame(), "无场内实时代码", ""

    try:
        df = fetch_exchange_spot(exchange_codes)
        return df, "东方财富场内实时行情", ""
    except Exception as e:
        return pd.DataFrame(), "场内实时行情获取失败", str(e)


@st.cache_data(ttl=60, show_spinner=False)
def get_real_history(code: str, days: int = 240):
    """
    真实数据入口：
    场内基金优先使用场内K线；
    若失败，再尝试场外净值；
    场外基金直接使用场外净值。
    不生成虚拟行情。
    """
    code = clean_code(code)

    errors = []

    if is_exchange_fund(code):
        try:
            df = fetch_exchange_history(code, days)
            return df, "东方财富场内历史K线", ""
        except Exception as e:
            errors.append(f"场内K线失败：{e}")

        try:
            df, name = fetch_otc_fund_history(code, days)
            return df, f"东方财富基金净值：{name}", "；".join(errors)
        except Exception as e:
            errors.append(f"基金净值失败：{e}")
    else:
        try:
            df, name = fetch_otc_fund_history(code, days)
            return df, f"东方财富基金净值：{name}", ""
        except Exception as e:
            errors.append(f"基金净值失败：{e}")

        try:
            df = fetch_exchange_history(code, days)
            return df, "东方财富场内历史K线", "；".join(errors)
        except Exception as e:
            errors.append(f"场内K线失败：{e}")

    return pd.DataFrame(), "真实数据获取失败", "；".join(errors)


def build_analysis_data(code: str, days: int, spot_df: pd.DataFrame):
    """
    统一分析数据。
    不使用虚拟数据。
    """
    code = clean_code(code)
    history, source, error = get_real_history(code, days)

    if history.empty:
        return pd.DataFrame(), source, error, ""

    note = ""

    if is_exchange_fund(code) and spot_df is not None and not spot_df.empty:
        hit = spot_df[spot_df["code"].astype(str) == code]
        if not hit.empty:
            history, note = apply_exchange_spot_to_history(history, hit.iloc[0])

    history = enrich_indicators(history)
    return history, source, error, note


# ============================================================
# 指标系统
# ============================================================
def classify_money_signal(row):
    pct = safe_num(row.get("pct_change"))
    ratio = safe_num(row.get("volume_ratio"))

    if pd.isna(pct):
        return "数据不足"

    # 场外基金没有成交额时，不能强行判断资金流入流出
    if pd.isna(ratio) or ratio == 0 or row.get("amount", 0) == 0:
        if pct > 0.8:
            return "净值上涨"
        elif pct < -0.8:
            return "净值回落"
        else:
            return "净值平稳"

    if pct > 1.2 and ratio >= 1.25:
        return "强流入"
    if pct > 0.3 and ratio >= 1.05:
        return "温和流入"
    if pct < -1.2 and ratio >= 1.25:
        return "强撤出"
    if pct < -0.3 and ratio >= 1.05:
        return "温和撤出"
    if abs(pct) < 0.3 and ratio >= 1.3:
        return "分歧放量"
    if ratio < 0.75:
        return "缩量观望"
    return "中性"


def enrich_indicators(df: pd.DataFrame):
    df = df.copy()

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    for col in ["open", "close", "high", "low", "volume", "amount", "pct_change"]:
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

    df["volume_ratio"] = np.where(
        df["amount_ma20"] > 0,
        df["amount"] / df["amount_ma20"],
        np.nan,
    )

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
        return {
            "trend_score": 0,
            "trend_label": "无数据",
            "risk_label": "无法判断",
            "money_signal": "无数据",
            "action": "等待真实数据",
            "comment": "当前未获取到真实行情数据，无法进行专业分析。",
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
        trend_label = "趋势偏强"
    elif score == 3:
        trend_label = "趋势修复"
    elif score == 2:
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

    if trend_label in ["趋势偏强", "趋势修复"] and money_signal in ["强流入", "温和流入", "净值上涨"]:
        action = "继续持有观察"
    elif trend_label == "趋势偏弱" and money_signal in ["强撤出", "温和撤出", "净值回落"]:
        action = "谨慎防守"
    elif risk_label in ["回调区", "深度回调"] and money_signal not in ["强撤出", "净值回落"]:
        action = "小额观察"
    elif risk_label == "短期过热":
        action = "不宜追高"
    else:
        action = "震荡观察"

    comment = generate_commentary(latest, trend_label, risk_label, money_signal, action)

    return {
        "trend_score": score,
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
        lines.append("价格位于5日均线上方，短线动能尚可。" if close > latest["ma5"] else "价格低于5日均线，短线动能偏弱。")

    if pd.notna(latest["ma20"]):
        lines.append("价格站上20日均线，短期结构相对健康。" if close > latest["ma20"] else "价格低于20日均线，短期趋势仍需观察。")

    if pd.notna(latest["ma60"]):
        lines.append("价格处于60日均线上方，中期结构相对稳定。" if close > latest["ma60"] else "价格低于60日均线，中期趋势偏弱。")

    ratio = safe_num(latest["volume_ratio"])
    amount = safe_num(latest.get("amount", 0))

    if amount > 0 and pd.notna(ratio):
        if ratio >= 1.5:
            lines.append(f"当前成交额约为20日均值的 {ratio:.2f} 倍，属于明显放量。")
        elif ratio >= 1.1:
            lines.append(f"当前成交额约为20日均值的 {ratio:.2f} 倍，量能有所放大。")
        elif ratio < 0.75:
            lines.append(f"当前成交额约为20日均值的 {ratio:.2f} 倍，市场参与度偏低。")
        else:
            lines.append(f"当前成交额约为20日均值的 {ratio:.2f} 倍，量能处于正常区间。")
    else:
        lines.append("该基金为净值型数据，无法使用成交额判断资金强弱，主要参考净值趋势与均线结构。")

    if money_signal in ["强流入", "温和流入", "净值上涨"]:
        lines.append("当前价格/净值表现偏积极，短期情绪有所改善。")
    elif money_signal in ["强撤出", "温和撤出", "净值回落"]:
        lines.append("当前价格/净值表现偏弱，需要观察是否继续回落。")
    elif money_signal == "缩量观望":
        lines.append("当前缩量明显，说明市场参与意愿不足。")

    lines.append(f"综合判断：{trend_label}，风险状态为{risk_label}，策略更偏向“{action}”。")

    return "\n\n".join(lines)


# ============================================================
# 图表
# ============================================================
def make_price_chart(df: pd.DataFrame, title: str):
    if df is None or df.empty:
        fig = go.Figure()
        fig.update_layout(
            title="未获取到真实行情数据",
            template="plotly_dark",
            height=520,
            paper_bgcolor="#0F172A",
            plot_bgcolor="#0F172A",
            font=dict(color="#F8FAFC"),
        )
        return fig

    has_amount = df["amount"].sum() > 0

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.07,
        row_heights=[0.60, 0.22, 0.18],
        subplot_titles=("价格/净值趋势与均线结构", "成交额/净值变化", "资金行为强度/趋势强弱"),
    )

    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["close"],
            name="价格/净值",
            mode="lines",
            line=dict(color="#F8FAFC", width=2.8),
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(x=df["date"], y=df["ma5"], name="MA5", mode="lines", line=dict(color="#38BDF8", width=1.5)),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=df["date"], y=df["ma20"], name="MA20", mode="lines", line=dict(color="#FBBF24", width=1.6)),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=df["date"], y=df["ma60"], name="MA60", mode="lines", line=dict(color="#A78BFA", width=1.6)),
        row=1,
        col=1,
    )

    colors = np.where(df["pct_change"] >= 0, "#22C55E", "#EF4444")

    if has_amount:
        fig.add_trace(
            go.Bar(x=df["date"], y=df["amount"] / 1e8, name="成交额/亿", marker_color=colors, opacity=0.72),
            row=2,
            col=1,
        )
        fig.add_trace(
            go.Scatter(x=df["date"], y=df["amount_ma20"] / 1e8, name="成交额MA20/亿", mode="lines", line=dict(color="#FBBF24", width=1.5)),
            row=2,
            col=1,
        )
    else:
        fig.add_trace(
            go.Bar(x=df["date"], y=df["pct_change"], name="日涨跌幅/%", marker_color=colors, opacity=0.72),
            row=2,
            col=1,
        )

    fig.add_trace(
        go.Bar(x=df["date"], y=df["money_strength"], name="资金行为强度", marker_color=colors, opacity=0.75),
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


# ============================================================
# 实仓处理
# ============================================================
def normalize_positions(df: pd.DataFrame):
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

    df["code"] = df["code"].astype(str).str.replace(".0", "", regex=False).apply(clean_code)
    df["shares"] = pd.to_numeric(df["shares"], errors="coerce").fillna(0)
    df["cost_price"] = pd.to_numeric(df["cost_price"], errors="coerce").fillna(0)
    df["name"] = df["name"].astype(str)

    return df[["code", "name", "shares", "cost_price", "buy_date", "account_type", "notes"]]


def current_price_for_code(code: str, spot_df: pd.DataFrame):
    code = clean_code(code)

    if is_exchange_fund(code) and spot_df is not None and not spot_df.empty:
        hit = spot_df[spot_df["code"].astype(str) == code]
        if not hit.empty:
            row = hit.iloc[0]
            return safe_num(row["price"]), row.get("name", f"基金{code}"), "场内实时"

    hist, source, err = get_real_history(code, 30)
    if not hist.empty:
        name = hist.get("fund_name", pd.Series([f"基金{code}"])).iloc[-1] if "fund_name" in hist.columns else f"基金{code}"
        return safe_num(hist.iloc[-1]["close"]), name, source

    return np.nan, f"基金{code}", "获取失败"


def compute_position_detail(positions: pd.DataFrame, spot_df: pd.DataFrame):
    if positions is None or positions.empty:
        return pd.DataFrame()

    rows = []

    for _, p in positions.iterrows():
        code = clean_code(p["code"])
        price, real_name, source = current_price_for_code(code, spot_df)

        shares = safe_num(p["shares"], 0)
        cost_price = safe_num(p["cost_price"], 0)

        current_value = shares * price if pd.notna(price) else np.nan
        cost_value = shares * cost_price if cost_price > 0 else np.nan
        profit = current_value - cost_value if pd.notna(current_value) and pd.notna(cost_value) else np.nan
        profit_rate = profit / cost_value * 100 if pd.notna(profit) and cost_value > 0 else np.nan

        rows.append(
            {
                "code": code,
                "name": p["name"] if str(p["name"]).strip() else real_name,
                "shares": shares,
                "cost_price": cost_price,
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
# 页面状态渲染
# ============================================================
def render_data_status(source, error):
    if "失败" in source or "失败" in str(error):
        st.markdown(
            f'<div class="status-danger">真实数据获取异常：{source}；{error}</div>',
            unsafe_allow_html=True,
        )
    elif "净值" in source:
        st.markdown(
            f'<div class="status-warn">当前数据源：{source}。场外基金通常不是盘中实时，而是最新公布净值。</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="status-ok">当前数据源：{source}。场内基金已尝试使用东方财富实时行情更新。</div>',
            unsafe_allow_html=True,
        )


# ============================================================
# 侧边栏
# ============================================================
st.sidebar.markdown("## 📊 基金智能分析平台")
st.sidebar.caption("真实行情 · 实仓导入 · 自定义基金分析")

page = st.sidebar.radio(
    "功能导航",
    ["基金分析", "实仓导入与分析", "市场模块", "自定义搜索"],
    index=0,
)

st.sidebar.divider()

module_name = st.sidebar.selectbox("选择市场模块", list(FUND_MODULES.keys()), index=2)
module_items = FUND_MODULES[module_name]
selected_name = st.sidebar.selectbox("选择模块内基金", list(module_items.keys()), index=0)

manual_mode = st.sidebar.checkbox("用户自查：输入任意6位基金代码", value=False)

if manual_mode:
    selected_code = clean_code(st.sidebar.text_input("输入基金代码", value=module_items[selected_name]))
    selected_display_name = f"自查基金 {selected_code}"
else:
    selected_code = module_items[selected_name]
    selected_display_name = selected_name

days = st.sidebar.slider("历史分析周期", 80, 520, 240, 20)

if st.sidebar.button("刷新真实数据缓存"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.caption(f"页面时间：{now_text()}")


# ============================================================
# 页面标题
# ============================================================
st.markdown('<div class="main-title">FundPilot Pro ｜ 基金智能分析平台</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">实仓导入 · 真实行情 · 趋势分析 · 专业解读 · 全模块自查</div>',
    unsafe_allow_html=True,
)


# ============================================================
# 全局数据
# ============================================================
watch_codes = list(module_items.values())
if selected_code not in watch_codes:
    watch_codes.insert(0, selected_code)

# 如果已有实仓，把实仓代码也加入场内实时请求
if POSITION_FILE.exists():
    try:
        cached_pos = normalize_positions(pd.read_csv(POSITION_FILE))
        for c in cached_pos["code"].tolist():
            if c not in watch_codes:
                watch_codes.append(c)
    except Exception:
        pass

spot_df, spot_source, spot_error = get_real_spot_for_codes(tuple(watch_codes))
analysis_df, data_source, data_error, realtime_note = build_analysis_data(selected_code, days, spot_df)

summary = compute_summary(analysis_df)

if not analysis_df.empty:
    latest = analysis_df.iloc[-1]
else:
    latest = pd.Series(dtype="object")

fund_name = selected_display_name

if not analysis_df.empty and "fund_name" in analysis_df.columns:
    try:
        fund_name = str(analysis_df["fund_name"].dropna().iloc[-1])
    except Exception:
        pass

if not spot_df.empty:
    hit = spot_df[spot_df["code"].astype(str) == clean_code(selected_code)]
    if not hit.empty and str(hit.iloc[0].get("name", "")).strip():
        fund_name = hit.iloc[0]["name"]


# ============================================================
# 基金分析页面
# ============================================================
if page == "基金分析":
    render_data_status(data_source, data_error)

    if realtime_note:
        st.markdown(f'<div class="status-ok">{realtime_note}</div>', unsafe_allow_html=True)

    if analysis_df.empty:
        st.error("未获取到该基金的真实数据。请检查代码是否正确，或稍后重试。")
        st.stop()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("基金名称", fund_name)
    c2.metric("最新价格/净值", f"{safe_num(latest['close']):.4f}")
    c3.metric("最新涨跌幅", format_pct(latest["pct_change"]))
    c4.metric("成交额/数据属性", format_money(latest["amount"]) if safe_num(latest["amount"], 0) > 0 else "净值型")
    c5.metric("资金/净值信号", summary["money_signal"])

    c6, c7, c8, c9, c10 = st.columns(5)
    c6.metric("趋势评分", f"{summary['trend_score']} / 5")
    c7.metric("趋势状态", summary["trend_label"])
    c8.metric("风险状态", summary["risk_label"])
    c9.metric("量能倍率", f"{safe_num(latest['volume_ratio']):.2f}x" if pd.notna(safe_num(latest["volume_ratio"])) else "净值型")
    c10.metric("策略提示", summary["action"])

    st.markdown(
        f"""
        <div class="panel">
            <div class="panel-title">{fund_name}（{selected_code}）</div>
            <div class="panel-subtitle">
            当前模块：{module_name}；数据源：{data_source}；
            最新数据日期：{pd.to_datetime(latest['date']).strftime('%Y-%m-%d') if not analysis_df.empty else '无'}；
            页面时间：{now_text()}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab1, tab2, tab3 = st.tabs(["📈 专业图表", "🧠 专业解读", "📋 信号明细"])

    with tab1:
        st.plotly_chart(
            make_price_chart(analysis_df, f"{fund_name}（{selected_code}）真实行情分析"),
            use_container_width=True,
        )

    with tab2:
        st.markdown(
            f"""
            <div class="signal-card">
                <div class="signal-title">专业分析解读</div>
                <div class="signal-text">{summary["comment"].replace(chr(10), "<br>")}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if safe_num(latest.get("amount", 0), 0) == 0:
            st.warning("该基金当前显示为净值型数据，不能用成交额判断盘中资金流入流出，建议重点参考净值趋势、均线结构和回撤位置。")

    with tab3:
        detail = analysis_df[
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
        detail["volume_ratio"] = detail["volume_ratio"].map(lambda x: f"{x:.2f}x" if pd.notna(x) else "净值型")
        detail["money_strength"] = detail["money_strength"].map(lambda x: f"{x:.2f}" if pd.notna(x) else "暂无")
        detail["ma5_dev"] = detail["ma5_dev"].apply(format_pct)
        detail["ma20_dev"] = detail["ma20_dev"].apply(format_pct)
        detail["ma60_dev"] = detail["ma60_dev"].apply(format_pct)

        detail = detail.rename(
            columns={
                "date": "日期",
                "close": "收盘/净值",
                "pct_change": "日涨跌幅",
                "amount": "成交额",
                "volume_ratio": "量能倍率",
                "money_strength": "资金行为强度",
                "money_signal": "资金/净值信号",
                "ma5_dev": "均线偏离_MA5",
                "ma20_dev": "均线偏离_MA20",
                "ma60_dev": "均线偏离_MA60",
            }
        )

        st.dataframe(detail.sort_values("日期", ascending=False), use_container_width=True, height=560, hide_index=True)


# ============================================================
# 实仓导入与分析
# ============================================================
elif page == "实仓导入与分析":
    st.markdown(
        """
        <div class="panel">
            <div class="panel-title">实仓导入与组合分析</div>
            <div class="panel-subtitle">支持 Excel / CSV 导入，也支持手动录入。导入后使用真实行情或真实净值分析持仓。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader("上传实仓文件：Excel / CSV", type=["xlsx", "xls", "csv"])

    if uploaded is not None:
        try:
            if uploaded.name.endswith(".csv"):
                raw = pd.read_csv(uploaded)
            else:
                raw = pd.read_excel(uploaded)

            positions = normalize_positions(raw)
            positions.to_csv(POSITION_FILE, index=False, encoding="utf-8-sig")
            st.success("实仓导入成功")
        except Exception as e:
            st.error(f"导入失败：{e}")

    if POSITION_FILE.exists():
        positions = normalize_positions(pd.read_csv(POSITION_FILE))
    else:
        st.info("当前未导入实仓。你可以上传文件，或在下方手动录入。")
        positions = pd.DataFrame(
            columns=["code", "name", "shares", "cost_price", "buy_date", "account_type", "notes"]
        )

    st.subheader("实仓编辑器")

    edited = st.data_editor(
        positions,
        use_container_width=True,
        num_rows="dynamic",
        height=300,
    )

    if st.button("保存实仓"):
        edited = normalize_positions(edited)
        edited.to_csv(POSITION_FILE, index=False, encoding="utf-8-sig")
        st.success("实仓已保存")
        st.rerun()

    positions = normalize_positions(edited)

    if not positions.empty:
        all_codes = positions["code"].tolist()
        spot_pos, _, _ = get_real_spot_for_codes(tuple(all_codes))
        position_detail = compute_position_detail(positions, spot_pos)

        if not position_detail.empty:
            total_asset = position_detail["current_value"].sum()
            total_cost = position_detail["cost_value"].sum()
            profit = total_asset - total_cost
            profit_rate = profit / total_cost * 100 if total_cost > 0 else np.nan

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("组合当前市值", format_money(total_asset))
            c2.metric("投入成本", format_money(total_cost))
            c3.metric("浮动盈亏", format_money(profit), format_pct(profit_rate))
            c4.metric("最大单只仓位", format_pct(position_detail["weight"].max()))

            show = position_detail.copy()
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
                    "current_price": "当前价/净值",
                    "price_source": "价格来源",
                    "buy_date": "买入日期",
                }
            )

            keep = [
                "代码",
                "名称",
                "份额",
                "成本价",
                "当前价/净值",
                "当前市值",
                "成本金额",
                "浮盈亏",
                "收益率",
                "仓位占比",
                "价格来源",
                "买入日期",
            ]

            st.dataframe(show[keep], use_container_width=True, height=520, hide_index=True)

            st.markdown(
                """
                <div class="signal-card">
                    <div class="signal-title">组合诊断提示</div>
                    <div class="signal-text">
                    若单一基金仓位超过30%，或同一赛道基金合计超过50%，组合波动风险会明显提升。<br>
                    场外基金使用最新公布净值，场内ETF使用实时行情或日K数据。
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ============================================================
# 市场模块
# ============================================================
elif page == "市场模块":
    st.markdown(
        f"""
        <div class="panel">
            <div class="panel-title">{module_name} 模块基金池</div>
            <div class="panel-subtitle">场内基金显示实时行情；场外基金显示净值数据。支持在左侧切换模块或自查代码。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    module_df = pd.DataFrame(
        [{"模块": module_name, "名称": n, "代码": c, "类型": "场内" if is_exchange_fund(c) else "场外净值"} for n, c in module_items.items()]
    )

    if not spot_df.empty:
        spot_show = spot_df.rename(
            columns={
                "code": "代码",
                "name": "名称",
                "price": "最新价",
                "pct_change": "涨跌幅",
                "change": "涨跌额",
                "amount": "成交额",
                "update_time": "更新时间",
            }
        ).copy()

        spot_show["成交额"] = spot_show["成交额"].apply(format_money)
        st.subheader("模块内场内基金实时行情")
        st.dataframe(
            spot_show[["代码", "名称", "最新价", "涨跌幅", "涨跌额", "成交额", "更新时间"]].sort_values("涨跌幅", ascending=False),
            use_container_width=True,
            height=360,
            hide_index=True,
        )

    st.subheader("当前模块基金清单")
    st.dataframe(module_df, use_container_width=True, height=420, hide_index=True)

    all_rows = []
    for m, items in FUND_MODULES.items():
        for n, c in items.items():
            all_rows.append({"模块": m, "名称": n, "代码": c, "类型": "场内" if is_exchange_fund(c) else "场外净值"})
    st.subheader("全模块基金清单")
    st.dataframe(pd.DataFrame(all_rows), use_container_width=True, height=520, hide_index=True)


# ============================================================
# 自定义搜索
# ============================================================
elif page == "自定义搜索":
    st.markdown(
        """
        <div class="panel">
            <div class="panel-title">自定义基金搜索</div>
            <div class="panel-subtitle">输入基金代码、名称或模块关键词。若没有预设，直接输入6位代码即可自查。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    keyword = st.text_input("搜索基金", placeholder="例如：515030、新能源、半导体、005827")

    all_rows = []
    for m, items in FUND_MODULES.items():
        for n, c in items.items():
            all_rows.append({"模块": m, "名称": n, "代码": c, "类型": "场内" if is_exchange_fund(c) else "场外净值"})
    all_df = pd.DataFrame(all_rows)

    if keyword:
        kw = keyword.strip()
        result = all_df[
            all_df["模块"].str.contains(kw, case=False, na=False)
            | all_df["名称"].str.contains(kw, case=False, na=False)
            | all_df["代码"].astype(str).str.contains(kw, case=False, na=False)
        ]

        if result.empty and kw.isdigit() and len(kw) == 6:
            result = pd.DataFrame(
                [{"模块": "用户自查", "名称": f"自查基金{kw}", "代码": kw, "类型": "场内" if is_exchange_fund(kw) else "场外净值"}]
            )

        if result.empty:
            st.warning("未找到预设基金。若是基金代码，请输入完整6位代码。")
        else:
            st.dataframe(result, use_container_width=True, height=420, hide_index=True)

            if kw.isdigit() and len(kw) == 6:
                st.info("请在左侧勾选“用户自查”，输入该6位代码，即可进入基金分析页面。")
    else:
        st.info("请输入基金代码、名称或模块关键词。")
