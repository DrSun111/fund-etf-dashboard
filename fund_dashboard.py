# -*- coding: utf-8 -*-
"""
FundPilot Pro | 基金智能分析平台

运行方式:
    streamlit run fundpilot_pro.py

依赖建议:
    streamlit pandas numpy plotly requests openpyxl

说明:
    1. 优先使用东方财富公开行情接口获取 ETF/LOF K 线与部分场外基金净值。
    2. 当网络、接口或代码类型不可用时，自动生成稳定的演示行情，保证界面可预览。
    3. 本原型聚焦产品闭环: 实仓导入、模块行情、趋势风控、搜索、自定义模块、专业解读。
"""

from __future__ import annotations

import io
import json
import math
import re
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
import streamlit.components.v1 as components
from plotly.subplots import make_subplots


APP_NAME = "FundPilot Pro"
APP_SUBTITLE = "实仓导入 · 模块轮动 · 趋势风控 · AI专业解读 · 自定义基金搜索"

THEME = {
    "bg": "#07111F",
    "bg2": "#0B1A2F",
    "panel": "#101B2D",
    "panel2": "#16243A",
    "border": "rgba(88, 213, 255, 0.26)",
    "text": "#F8FBFF",
    "muted": "#D6E2F3",
    "blue": "#58D5FF",
    "green": "#22C55E",
    "red": "#EF4444",
    "yellow": "#FBBF24",
    "purple": "#A78BFA",
}

PLOTLY_TEMPLATE = "plotly_dark"
CHART_CONFIG = {
    "displayModeBar": True,
    "displaylogo": False,
    "scrollZoom": True,
    "responsive": True,
    "toImageButtonOptions": {
        "format": "png",
        "filename": "fundpilot_chart",
        "height": 1080,
        "width": 1920,
        "scale": 2,
    },
}
DATA_MODE_OPTIONS = ["东方财富实时行情 + 日线兜底", "仅演示行情"]
REFRESH_OPTIONS = ["实时 15秒", "30秒", "1分钟", "5分钟", "15分钟", "30分钟", "60分钟", "手动刷新"]


MODULE_TAXONOMY: Dict[str, List[str]] = {
    "宽基指数": ["沪深300", "中证500", "中证1000", "上证50", "创业板", "科创50", "双创50", "红利指数", "央企指数"],
    "科技成长": ["人工智能", "云计算", "软件", "通信", "5G", "机器人", "智能车", "数字经济", "信创", "数据中心"],
    "人工智能与数字经济": ["人工智能", "数字经济", "云计算", "软件", "数据中心", "信创", "传媒游戏", "算力"],
    "半导体与芯片": ["半导体", "芯片", "集成电路", "电子", "消费电子", "科创芯片"],
    "电气电力与新能源": ["新能源车", "光伏", "电池", "储能", "绿色电力", "电力", "新能源", "碳中和", "风电", "核电", "智能电网"],
    "资源周期与大宗商品": ["有色金属", "稀土", "钢铁", "煤炭", "能源", "化工", "石油", "黄金", "豆粕", "农业资源"],
    "金融地产": ["证券", "银行", "保险", "金融", "地产", "基建", "央企金融"],
    "消费医药农业": ["消费", "酒", "食品饮料", "医药", "医疗", "创新药", "中药", "养殖", "农业"],
    "港股与海外": ["恒生科技", "恒生互联网", "港股通互联网", "恒生指数", "纳斯达克", "标普500", "德国", "日经", "印度", "越南"],
    "债券与货币": ["短债", "中短债", "纯债", "可转债", "货币基金", "同业存单", "政金债", "国债"],
    "商品与避险资产": ["黄金", "豆粕", "能源", "原油", "有色", "大宗商品"],
    "红利与低波动": ["红利指数", "红利低波", "央企红利", "高股息", "低波动"],
}


FUND_SEEDS: List[Dict[str, Any]] = [
    # 宽基指数
    {"fund_code": "510300", "fund_name": "沪深300ETF", "module_level_1": "宽基指数", "module_level_2": "沪深300", "market": "SH", "asset_type": "ETF", "risk_level": "中"},
    {"fund_code": "510500", "fund_name": "中证500ETF", "module_level_1": "宽基指数", "module_level_2": "中证500", "market": "SH", "asset_type": "ETF", "risk_level": "中"},
    {"fund_code": "512100", "fund_name": "中证1000ETF", "module_level_1": "宽基指数", "module_level_2": "中证1000", "market": "SH", "asset_type": "ETF", "risk_level": "中高"},
    {"fund_code": "510050", "fund_name": "上证50ETF", "module_level_1": "宽基指数", "module_level_2": "上证50", "market": "SH", "asset_type": "ETF", "risk_level": "中"},
    {"fund_code": "159915", "fund_name": "创业板ETF", "module_level_1": "宽基指数", "module_level_2": "创业板", "market": "SZ", "asset_type": "ETF", "risk_level": "中高"},
    {"fund_code": "588000", "fund_name": "科创50ETF", "module_level_1": "宽基指数", "module_level_2": "科创50", "market": "SH", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "159781", "fund_name": "双创50ETF", "module_level_1": "宽基指数", "module_level_2": "双创50", "market": "SZ", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "510880", "fund_name": "红利ETF", "module_level_1": "宽基指数", "module_level_2": "红利指数", "market": "SH", "asset_type": "ETF", "risk_level": "中"},
    {"fund_code": "512950", "fund_name": "央企改革ETF", "module_level_1": "宽基指数", "module_level_2": "央企指数", "market": "SH", "asset_type": "ETF", "risk_level": "中"},
    # 科技成长 / AI
    {"fund_code": "515070", "fund_name": "人工智能AIETF", "module_level_1": "科技成长", "module_level_2": "人工智能", "market": "SH", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "159819", "fund_name": "人工智能ETF", "module_level_1": "人工智能与数字经济", "module_level_2": "人工智能", "market": "SZ", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "516510", "fund_name": "云计算ETF", "module_level_1": "科技成长", "module_level_2": "云计算", "market": "SH", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "515230", "fund_name": "软件ETF", "module_level_1": "科技成长", "module_level_2": "软件", "market": "SH", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "515880", "fund_name": "通信ETF", "module_level_1": "科技成长", "module_level_2": "通信", "market": "SH", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "515050", "fund_name": "5GETF", "module_level_1": "科技成长", "module_level_2": "5G", "market": "SH", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "562500", "fund_name": "机器人ETF", "module_level_1": "科技成长", "module_level_2": "机器人", "market": "SH", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "515250", "fund_name": "智能汽车ETF", "module_level_1": "科技成长", "module_level_2": "智能车", "market": "SH", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "560800", "fund_name": "数字经济ETF", "module_level_1": "人工智能与数字经济", "module_level_2": "数字经济", "market": "SH", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "159537", "fund_name": "信创ETF", "module_level_1": "人工智能与数字经济", "module_level_2": "信创", "market": "SZ", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "516000", "fund_name": "数据ETF", "module_level_1": "人工智能与数字经济", "module_level_2": "数据中心", "market": "SH", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "516190", "fund_name": "文娱传媒ETF", "module_level_1": "人工智能与数字经济", "module_level_2": "传媒游戏", "market": "SH", "asset_type": "ETF", "risk_level": "高"},
    # 半导体与芯片
    {"fund_code": "512480", "fund_name": "半导体ETF", "module_level_1": "半导体与芯片", "module_level_2": "半导体", "market": "SH", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "159995", "fund_name": "芯片ETF", "module_level_1": "半导体与芯片", "module_level_2": "芯片", "market": "SZ", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "562820", "fund_name": "集成电路ETF", "module_level_1": "半导体与芯片", "module_level_2": "集成电路", "market": "SH", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "515260", "fund_name": "电子ETF", "module_level_1": "半导体与芯片", "module_level_2": "电子", "market": "SH", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "159732", "fund_name": "消费电子ETF", "module_level_1": "半导体与芯片", "module_level_2": "消费电子", "market": "SZ", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "588200", "fund_name": "科创芯片ETF", "module_level_1": "半导体与芯片", "module_level_2": "科创芯片", "market": "SH", "asset_type": "ETF", "risk_level": "高"},
    # 电气电力与新能源
    {"fund_code": "515030", "fund_name": "新能源车ETF", "module_level_1": "电气电力与新能源", "module_level_2": "新能源车", "market": "SH", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "515790", "fund_name": "光伏ETF", "module_level_1": "电气电力与新能源", "module_level_2": "光伏", "market": "SH", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "159755", "fund_name": "电池ETF", "module_level_1": "电气电力与新能源", "module_level_2": "电池", "market": "SZ", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "159863", "fund_name": "储能ETF", "module_level_1": "电气电力与新能源", "module_level_2": "储能", "market": "SZ", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "562960", "fund_name": "绿色电力ETF", "module_level_1": "电气电力与新能源", "module_level_2": "绿色电力", "market": "SH", "asset_type": "ETF", "risk_level": "中高"},
    {"fund_code": "159611", "fund_name": "电力ETF", "module_level_1": "电气电力与新能源", "module_level_2": "电力", "market": "SZ", "asset_type": "ETF", "risk_level": "中高"},
    {"fund_code": "516160", "fund_name": "新能源ETF", "module_level_1": "电气电力与新能源", "module_level_2": "新能源", "market": "SH", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "159790", "fund_name": "碳中和ETF", "module_level_1": "电气电力与新能源", "module_level_2": "碳中和", "market": "SZ", "asset_type": "ETF", "risk_level": "中高"},
    {"fund_code": "159862", "fund_name": "风电ETF", "module_level_1": "电气电力与新能源", "module_level_2": "风电", "market": "SZ", "asset_type": "ETF", "risk_level": "中高"},
    {"fund_code": "561760", "fund_name": "电力设备ETF", "module_level_1": "电气电力与新能源", "module_level_2": "智能电网", "market": "SH", "asset_type": "ETF", "risk_level": "中高"},
    # 资源周期与商品
    {"fund_code": "512400", "fund_name": "有色金属ETF", "module_level_1": "资源周期与大宗商品", "module_level_2": "有色金属", "market": "SH", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "516780", "fund_name": "稀土ETF", "module_level_1": "资源周期与大宗商品", "module_level_2": "稀土", "market": "SH", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "515210", "fund_name": "钢铁ETF", "module_level_1": "资源周期与大宗商品", "module_level_2": "钢铁", "market": "SH", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "515220", "fund_name": "煤炭ETF", "module_level_1": "资源周期与大宗商品", "module_level_2": "煤炭", "market": "SH", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "159930", "fund_name": "能源ETF", "module_level_1": "资源周期与大宗商品", "module_level_2": "能源", "market": "SZ", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "516020", "fund_name": "化工ETF", "module_level_1": "资源周期与大宗商品", "module_level_2": "化工", "market": "SH", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "162411", "fund_name": "华宝油气", "module_level_1": "资源周期与大宗商品", "module_level_2": "石油", "market": "FUND", "asset_type": "QDII", "risk_level": "高"},
    {"fund_code": "518880", "fund_name": "黄金ETF", "module_level_1": "资源周期与大宗商品", "module_level_2": "黄金", "market": "SH", "asset_type": "ETF", "risk_level": "中高"},
    {"fund_code": "159985", "fund_name": "豆粕ETF", "module_level_1": "资源周期与大宗商品", "module_level_2": "豆粕", "market": "SZ", "asset_type": "ETF", "risk_level": "中高"},
    {"fund_code": "159825", "fund_name": "农业ETF", "module_level_1": "资源周期与大宗商品", "module_level_2": "农业资源", "market": "SZ", "asset_type": "ETF", "risk_level": "中高"},
    # 金融地产
    {"fund_code": "512880", "fund_name": "证券ETF", "module_level_1": "金融地产", "module_level_2": "证券", "market": "SH", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "512800", "fund_name": "银行ETF", "module_level_1": "金融地产", "module_level_2": "银行", "market": "SH", "asset_type": "ETF", "risk_level": "中"},
    {"fund_code": "512070", "fund_name": "保险ETF", "module_level_1": "金融地产", "module_level_2": "保险", "market": "SH", "asset_type": "ETF", "risk_level": "中高"},
    {"fund_code": "510230", "fund_name": "金融ETF", "module_level_1": "金融地产", "module_level_2": "金融", "market": "SH", "asset_type": "ETF", "risk_level": "中"},
    {"fund_code": "512200", "fund_name": "地产ETF", "module_level_1": "金融地产", "module_level_2": "地产", "market": "SH", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "516950", "fund_name": "基建ETF", "module_level_1": "金融地产", "module_level_2": "基建", "market": "SH", "asset_type": "ETF", "risk_level": "中高"},
    {"fund_code": "512950", "fund_name": "央企改革ETF", "module_level_1": "金融地产", "module_level_2": "央企金融", "market": "SH", "asset_type": "ETF", "risk_level": "中"},
    # 消费医药农业
    {"fund_code": "159928", "fund_name": "消费ETF", "module_level_1": "消费医药农业", "module_level_2": "消费", "market": "SZ", "asset_type": "ETF", "risk_level": "中高"},
    {"fund_code": "512690", "fund_name": "酒ETF", "module_level_1": "消费医药农业", "module_level_2": "酒", "market": "SH", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "515170", "fund_name": "食品饮料ETF", "module_level_1": "消费医药农业", "module_level_2": "食品饮料", "market": "SH", "asset_type": "ETF", "risk_level": "中高"},
    {"fund_code": "512010", "fund_name": "医药ETF", "module_level_1": "消费医药农业", "module_level_2": "医药", "market": "SH", "asset_type": "ETF", "risk_level": "中高"},
    {"fund_code": "512170", "fund_name": "医疗ETF", "module_level_1": "消费医药农业", "module_level_2": "医疗", "market": "SH", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "159992", "fund_name": "创新药ETF", "module_level_1": "消费医药农业", "module_level_2": "创新药", "market": "SZ", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "562390", "fund_name": "中药ETF", "module_level_1": "消费医药农业", "module_level_2": "中药", "market": "SH", "asset_type": "ETF", "risk_level": "中高"},
    {"fund_code": "159865", "fund_name": "养殖ETF", "module_level_1": "消费医药农业", "module_level_2": "养殖", "market": "SZ", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "159825", "fund_name": "农业ETF", "module_level_1": "消费医药农业", "module_level_2": "农业", "market": "SZ", "asset_type": "ETF", "risk_level": "中高"},
    # 港股与海外
    {"fund_code": "513180", "fund_name": "恒生科技ETF", "module_level_1": "港股与海外", "module_level_2": "恒生科技", "market": "SH", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "513330", "fund_name": "恒生互联网ETF", "module_level_1": "港股与海外", "module_level_2": "恒生互联网", "market": "SH", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "513040", "fund_name": "港股通互联网ETF", "module_level_1": "港股与海外", "module_level_2": "港股通互联网", "market": "SH", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "159920", "fund_name": "恒生ETF", "module_level_1": "港股与海外", "module_level_2": "恒生指数", "market": "SZ", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "513100", "fund_name": "纳指ETF", "module_level_1": "港股与海外", "module_level_2": "纳斯达克", "market": "SH", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "513500", "fund_name": "标普500ETF", "module_level_1": "港股与海外", "module_level_2": "标普500", "market": "SH", "asset_type": "ETF", "risk_level": "中高"},
    {"fund_code": "513030", "fund_name": "德国ETF", "module_level_1": "港股与海外", "module_level_2": "德国", "market": "SH", "asset_type": "ETF", "risk_level": "中高"},
    {"fund_code": "513520", "fund_name": "日经ETF", "module_level_1": "港股与海外", "module_level_2": "日经", "market": "SH", "asset_type": "ETF", "risk_level": "中高"},
    {"fund_code": "164824", "fund_name": "印度基金LOF", "module_level_1": "港股与海外", "module_level_2": "印度", "market": "FUND", "asset_type": "LOF/QDII", "risk_level": "高"},
    {"fund_code": "008763", "fund_name": "越南市场基金", "module_level_1": "港股与海外", "module_level_2": "越南", "market": "FUND", "asset_type": "QDII", "risk_level": "高"},
    # 债券与货币
    {"fund_code": "511360", "fund_name": "短融ETF", "module_level_1": "债券与货币", "module_level_2": "短债", "market": "SH", "asset_type": "ETF", "risk_level": "低"},
    {"fund_code": "511260", "fund_name": "十年国债ETF", "module_level_1": "债券与货币", "module_level_2": "中短债", "market": "SH", "asset_type": "ETF", "risk_level": "低"},
    {"fund_code": "511010", "fund_name": "国债ETF", "module_level_1": "债券与货币", "module_level_2": "国债", "market": "SH", "asset_type": "ETF", "risk_level": "低"},
    {"fund_code": "511380", "fund_name": "可转债ETF", "module_level_1": "债券与货币", "module_level_2": "可转债", "market": "SH", "asset_type": "ETF", "risk_level": "中"},
    {"fund_code": "511880", "fund_name": "银华日利ETF", "module_level_1": "债券与货币", "module_level_2": "货币基金", "market": "SH", "asset_type": "货币ETF", "risk_level": "低"},
    {"fund_code": "511520", "fund_name": "政金债ETF", "module_level_1": "债券与货币", "module_level_2": "政金债", "market": "SH", "asset_type": "ETF", "risk_level": "低"},
    {"fund_code": "511090", "fund_name": "30年国债ETF", "module_level_1": "债券与货币", "module_level_2": "纯债", "market": "SH", "asset_type": "ETF", "risk_level": "低"},
    # 商品避险、红利低波
    {"fund_code": "518880", "fund_name": "黄金ETF", "module_level_1": "商品与避险资产", "module_level_2": "黄金", "market": "SH", "asset_type": "ETF", "risk_level": "中高"},
    {"fund_code": "159985", "fund_name": "豆粕ETF", "module_level_1": "商品与避险资产", "module_level_2": "豆粕", "market": "SZ", "asset_type": "ETF", "risk_level": "中高"},
    {"fund_code": "501018", "fund_name": "南方原油", "module_level_1": "商品与避险资产", "module_level_2": "原油", "market": "FUND", "asset_type": "QDII", "risk_level": "高"},
    {"fund_code": "159980", "fund_name": "有色ETF", "module_level_1": "商品与避险资产", "module_level_2": "有色", "market": "SZ", "asset_type": "ETF", "risk_level": "高"},
    {"fund_code": "510880", "fund_name": "红利ETF", "module_level_1": "红利与低波动", "module_level_2": "红利指数", "market": "SH", "asset_type": "ETF", "risk_level": "中"},
    {"fund_code": "515080", "fund_name": "中证红利ETF", "module_level_1": "红利与低波动", "module_level_2": "高股息", "market": "SH", "asset_type": "ETF", "risk_level": "中"},
    {"fund_code": "512890", "fund_name": "红利低波ETF", "module_level_1": "红利与低波动", "module_level_2": "红利低波", "market": "SH", "asset_type": "ETF", "risk_level": "中"},
    {"fund_code": "561580", "fund_name": "央企红利ETF", "module_level_1": "红利与低波动", "module_level_2": "央企红利", "market": "SH", "asset_type": "ETF", "risk_level": "中"},
]


DEFAULT_POSITIONS = pd.DataFrame(
    [
        {
            "fund_code": "515030",
            "fund_name": "新能源车ETF",
            "shares": 18500.0,
            "cost_price": 1.108,
            "buy_date": "2024-10-18",
            "account_type": "主账户",
            "notes": "长期观察仓",
        },
        {
            "fund_code": "512480",
            "fund_name": "半导体ETF",
            "shares": 16000.0,
            "cost_price": 0.892,
            "buy_date": "2024-12-06",
            "account_type": "主账户",
            "notes": "高波动赛道",
        },
        {
            "fund_code": "510300",
            "fund_name": "沪深300ETF",
            "shares": 6200.0,
            "cost_price": 3.780,
            "buy_date": "2023-08-23",
            "account_type": "长期账户",
            "notes": "核心底仓",
        },
        {
            "fund_code": "518880",
            "fund_name": "黄金ETF",
            "shares": 3200.0,
            "cost_price": 4.680,
            "buy_date": "2024-03-15",
            "account_type": "防守账户",
            "notes": "避险配置",
        },
    ]
)


POSITION_TEMPLATE = "fund_code,fund_name,shares,cost_price,buy_date,account_type,notes\n"


COLUMN_ALIASES = {
    "fund_code": ["fund_code", "基金代码", "代码", "ETF代码", "基金编号", "证券代码"],
    "fund_name": ["fund_name", "基金名称", "名称", "证券名称"],
    "shares": ["shares", "持有份额", "份额", "基金份额", "持仓份额"],
    "cost_price": ["cost_price", "持仓成本", "买入成本", "成本", "成本价", "买入价"],
    "current_value": ["current_value", "当前持仓金额", "持仓金额", "市值", "当前市值"],
    "buy_date": ["buy_date", "买入日期", "建仓日期", "持仓日期"],
    "account_type": ["account_type", "账户类型", "账户", "组合"],
    "notes": ["notes", "备注", "说明", "投资逻辑"],
}


@dataclass
class FundSnapshot:
    fund_code: str
    fund_name: str
    module_level_1: str
    module_level_2: str
    close: float
    pct_change: float
    amount: float
    volume_ratio: float
    trend_score: int
    trend_label: str
    money_signal: str
    risk_label: str
    action_label: str
    ma20_deviation: float
    source: str


def rerun_app() -> None:
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


def apply_page_config() -> None:
    st.set_page_config(
        page_title="FundPilot Pro | 基金智能分析平台",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def inject_css() -> None:
    st.markdown(
        """
        <style>
        html, body, #root, .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"],
        section.main {
            background:
                radial-gradient(circle at 12% 0%, rgba(88, 213, 255, 0.12), transparent 30%),
                linear-gradient(135deg, #07111F 0%, #0B1A2F 48%, #101B2D 100%) !important;
        }
        [data-testid="stHeader"] {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
            min-height: 0 !important;
            background: transparent !important;
        }
        [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"], header, footer {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
        }
        .block-container {
            padding-top: 0.65rem !important;
        }

        :root {
            --bg: #07111F;
            --bg2: #0B1A2F;
            --panel: #101B2D;
            --panel2: #16243A;
            --panel3: #1B2B44;
            --border: rgba(124, 214, 255, 0.40);
            --text: #F8FBFF;
            --muted: #D6E2F3;
            --muted2: #9FB4D0;
            --blue: #58D5FF;
            --green: #22C55E;
            --red: #EF4444;
            --yellow: #FBBF24;
            --purple: #A78BFA;
        }
        .stApp {
            background:
                radial-gradient(circle at 12% 0%, rgba(88, 213, 255, 0.12), transparent 30%),
                linear-gradient(135deg, #07111F 0%, #0B1A2F 48%, #101B2D 100%);
            color: var(--text);
        }
        .stApp, .stApp p, .stApp li, .stApp label,
        .stApp span:not([class*="plotly"]):not([class*="modebar"]) {
            color: var(--text);
        }
        .stCaptionContainer, .stCaptionContainer p,
        [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {
            color: var(--muted2) !important;
        }
        [data-testid="stSidebar"] {
            background:
                linear-gradient(180deg, rgba(12, 28, 50, .98), rgba(7, 17, 31, .98));
            border-right: 1px solid rgba(124, 214, 255, 0.28);
        }
        [data-testid="stSidebar"] * {
            color: var(--text) !important;
        }
        [data-testid="stMetricValue"] {
            color: var(--text);
        }
        [data-testid="stMetricDelta"] svg {
            display: none;
        }
        .block-container {
            padding-top: 1.1rem;
            padding-bottom: 2rem;
            max-width: 1680px;
        }
        h1, h2, h3 {
            letter-spacing: 0;
        }
        .hero {
            border: 1px solid rgba(124, 214, 255, 0.42);
            background:
                linear-gradient(120deg, rgba(18, 35, 57, 0.98), rgba(11, 26, 47, 0.95)),
                linear-gradient(90deg, rgba(88, 213, 255, 0.18), rgba(167, 139, 250, 0.14));
            border-radius: 8px;
            padding: 18px 20px;
            box-shadow: 0 0 28px rgba(88, 213, 255, 0.13);
            margin-bottom: 14px;
        }
        .hero h1 {
            margin: 0;
            font-size: clamp(1.35rem, 2.2vw, 2.3rem);
            line-height: 1.15;
        }
        .hero p {
            margin: 8px 0 0;
            color: var(--muted);
            font-size: .95rem;
        }
        .metric-card, .panel, .signal-card, .result-card {
            border: 1px solid rgba(124, 214, 255, 0.34);
            background:
                linear-gradient(180deg, rgba(24, 39, 62, 0.96), rgba(14, 27, 46, 0.98));
            border-radius: 8px;
            box-shadow: 0 0 22px rgba(88, 213, 255, 0.10);
        }
        .metric-card {
            min-height: 118px;
            padding: 15px 15px 12px;
        }
        .metric-label {
            color: var(--muted);
            font-size: .82rem;
            font-weight: 650;
            margin-bottom: 8px;
        }
        .metric-value {
            color: var(--text);
            font-size: clamp(1.15rem, 2.1vw, 1.9rem);
            font-weight: 700;
            line-height: 1.1;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .metric-delta {
            margin-top: 8px;
            font-size: .82rem;
            font-weight: 650;
        }
        .panel {
            padding: 15px;
            margin-bottom: 13px;
        }
        .panel-title {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 10px;
            color: var(--text);
            font-weight: 750;
        }
        .panel-subtitle {
            color: var(--muted);
            font-size: .82rem;
            font-weight: 500;
        }
        .pill {
            display: inline-flex;
            align-items: center;
            padding: 3px 8px;
            border-radius: 999px;
            border: 1px solid rgba(124, 214, 255, 0.46);
            color: #DDF7FF !important;
            background: rgba(88, 213, 255, 0.16);
            font-size: .74rem;
            font-weight: 750;
            margin: 0 5px 5px 0;
        }
        .risk-high {
            color: #FFE0E0 !important;
            border-color: rgba(248, 113, 113, 0.62);
            background: rgba(239, 68, 68, 0.18);
        }
        .risk-mid {
            color: #FFF1B8 !important;
            border-color: rgba(251, 191, 36, 0.62);
            background: rgba(251, 191, 36, 0.16);
        }
        .risk-low {
            color: #C8FAD7 !important;
            border-color: rgba(34, 197, 94, 0.58);
            background: rgba(34, 197, 94, 0.16);
        }
        .signal-card, .result-card {
            padding: 12px;
            margin-bottom: 10px;
        }
        .result-card strong {
            color: var(--text);
        }
        .small-muted {
            color: var(--muted) !important;
            font-size: .82rem;
        }
        .terminal-line {
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
            color: #E5EDFF;
            font-size: .82rem;
        }
        .dataframe {
            border-radius: 8px;
        }
        div[data-testid="stDataFrame"] {
            border: 1px solid rgba(88, 213, 255, 0.12);
            border-radius: 8px;
        }
        .stButton button, .stDownloadButton button {
            border-radius: 8px;
            border: 1px solid rgba(124, 214, 255, 0.48);
            background: linear-gradient(180deg, rgba(88, 213, 255, 0.18), rgba(31, 91, 129, 0.25));
            color: var(--text) !important;
            font-weight: 750;
        }
        .stButton button:hover, .stDownloadButton button:hover {
            border-color: rgba(88, 213, 255, 0.8);
            background: rgba(88, 213, 255, 0.28);
            color: white !important;
        }
        .stButton button:disabled, .stDownloadButton button:disabled {
            opacity: 1 !important;
            color: #9FB4D0 !important;
            background: rgba(20, 35, 58, 0.72) !important;
            border-color: rgba(124, 214, 255, 0.18) !important;
        }
        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div,
        textarea {
            border-radius: 8px !important;
            border-color: rgba(124, 214, 255, 0.46) !important;
            background-color: rgba(22, 36, 58, 0.96) !important;
            color: var(--text) !important;
        }
        input, textarea,
        div[data-baseweb="select"] span,
        div[data-baseweb="select"] div {
            color: var(--text) !important;
            -webkit-text-fill-color: var(--text) !important;
        }
        input::placeholder, textarea::placeholder {
            color: #B8C8DD !important;
            opacity: 1 !important;
            -webkit-text-fill-color: #B8C8DD !important;
        }
        [data-testid="stWidgetLabel"] p,
        [data-testid="stWidgetLabel"] label,
        [data-testid="stRadio"] label,
        [data-testid="stSelectbox"] label,
        [data-testid="stTextInput"] label {
            color: #EAF2FF !important;
            font-weight: 720 !important;
        }
        [data-testid="stExpander"] {
            border: 1px solid rgba(124, 214, 255, 0.20);
            background: rgba(16, 27, 45, 0.72);
            border-radius: 8px;
        }
        [data-testid="stAlert"] {
            background: rgba(24, 39, 62, 0.96);
            color: var(--text);
        }
        .chart-toolbar {
            display: flex;
            justify-content: flex-end;
            margin: -4px 0 8px;
        }
        .fullscreen-chart-stage {
            position: fixed;
            inset: 18px;
            z-index: 999999;
            background: linear-gradient(135deg, #07111F 0%, #0B1A2F 100%);
            border: 1px solid rgba(124, 214, 255, 0.55);
            border-radius: 8px;
            padding: 14px 16px 20px;
            box-shadow: 0 24px 80px rgba(0, 0, 0, 0.52);
            overflow: auto;
        }
        .realtime-strip {
            display: flex;
            flex-wrap: wrap;
            gap: 8px 12px;
            align-items: center;
            color: #EAF2FF;
            border: 1px solid rgba(124, 214, 255, 0.28);
            background: rgba(88, 213, 255, 0.09);
            padding: 8px 10px;
            border-radius: 8px;
            margin: 0 0 12px;
            font-size: .84rem;
            font-weight: 650;
        }
        @media (max-width: 820px) {
            .metric-card {
                min-height: 100px;
            }
            .hero {
                padding: 14px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_state() -> None:
    defaults = {
        "positions": DEFAULT_POSITIONS.copy(),
        "watchlist": ["515030", "512480", "510300", "518880", "513100"],
        "custom_modules": pd.DataFrame(
            columns=["module_id", "module_name", "fund_code", "fund_name", "created_at"]
        ),
        "selected_fund": "515030",
        "data_mode": "东方财富实时行情 + 日线兜底",
        "refresh_frequency": "手动刷新",
        "last_refresh_ts": time.time(),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    if st.session_state.get("data_mode") in {"东方财富优先 + 演示兜底", "东方财富日线 + 演示兜底", "东方财富日线行情 + 净值兜底"}:
        st.session_state["data_mode"] = "东方财富实时行情 + 日线兜底"
    if st.session_state.get("data_mode") not in DATA_MODE_OPTIONS:
        st.session_state["data_mode"] = "东方财富实时行情 + 日线兜底"
    if st.session_state.get("refresh_frequency") not in REFRESH_OPTIONS:
        st.session_state["refresh_frequency"] = "手动刷新"


def refresh_interval_seconds(value: str) -> Optional[int]:
    mapping = {
        "实时 15秒": 15,
        "30秒": 30,
        "1分钟": 60,
        "5分钟": 5 * 60,
        "15分钟": 15 * 60,
        "30分钟": 30 * 60,
        "60分钟": 60 * 60,
        "手动刷新": None,
    }
    return mapping.get(value)


def schedule_auto_refresh() -> None:
    seconds = refresh_interval_seconds(st.session_state.get("refresh_frequency", "手动刷新"))
    if not seconds:
        return
    components.html(
        f"""
        <script>
        const delay = {seconds * 1000};
        window.setTimeout(() => {{
            window.parent.location.reload();
        }}, delay);
        </script>
        """,
        height=0,
        width=0,
    )


def fmt_money(value: float, digits: int = 2) -> str:
    if pd.isna(value):
        return "--"
    sign = "-" if value < 0 else ""
    value = abs(float(value))
    if value >= 1e8:
        return f"{sign}{value / 1e8:.{digits}f}亿"
    if value >= 1e4:
        return f"{sign}{value / 1e4:.{digits}f}万"
    return f"{sign}{value:.{digits}f}"


def fmt_pct(value: float, digits: int = 2) -> str:
    if pd.isna(value):
        return "--"
    return f"{float(value):+.{digits}f}%"


def fmt_num(value: float, digits: int = 3) -> str:
    if pd.isna(value):
        return "--"
    return f"{float(value):.{digits}f}"


def badge(text: str, tone: str = "info") -> str:
    css = {"high": "risk-high", "mid": "risk-mid", "low": "risk-low"}.get(tone, "")
    return f'<span class="pill {css}">{text}</span>'


def section_title(title: str, subtitle: str = "") -> None:
    subtitle_html = f'<span class="panel-subtitle">{subtitle}</span>' if subtitle else ""
    st.markdown(
        f'<div class="panel-title"><span>{title}</span>{subtitle_html}</div>',
        unsafe_allow_html=True,
    )


def render_plotly_chart(fig: go.Figure, key: str, fullscreen_height: int = 900) -> None:
    full_key = f"{key}_fullscreen"
    is_full = bool(st.session_state.get(full_key, False))
    toolbar_cols = st.columns([1, 0.18])
    with toolbar_cols[1]:
        label = "退出全屏" if is_full else "全屏放大"
        if st.button(label, key=f"{key}_fullscreen_button", use_container_width=True):
            st.session_state[full_key] = not is_full
            rerun_app()
    chart_fig = go.Figure(fig)
    chart_fig.update_layout(
        font=dict(color="#EAF2FF", size=12),
        title_font=dict(color="#F8FBFF", size=16),
        legend=dict(font=dict(color="#EAF2FF")),
    )
    chart_fig.update_xaxes(tickfont=dict(color="#D6E2F3"), title_font=dict(color="#EAF2FF"), linecolor="rgba(214,226,243,.28)")
    chart_fig.update_yaxes(tickfont=dict(color="#D6E2F3"), title_font=dict(color="#EAF2FF"), linecolor="rgba(214,226,243,.28)")
    if st.session_state.get(full_key, False):
        st.markdown('<div class="fullscreen-chart-stage">', unsafe_allow_html=True)
        top_cols = st.columns([1, 0.12])
        with top_cols[0]:
            st.markdown("### 全屏图表")
        with top_cols[1]:
            if st.button("关闭", key=f"{key}_fullscreen_close", use_container_width=True):
                st.session_state[full_key] = False
                rerun_app()
        chart_fig.update_layout(height=fullscreen_height)
        st.plotly_chart(chart_fig, use_container_width=True, config=CHART_CONFIG)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.plotly_chart(chart_fig, use_container_width=True, config=CHART_CONFIG)


def render_hero() -> None:
    st.markdown(
        f"""
        <div class="hero">
            <h1>{APP_NAME}｜基金智能分析平台</h1>
            <p>{APP_SUBTITLE}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(label: str, value: str, delta: str = "", tone: str = "info") -> None:
    color = {
        "green": THEME["green"],
        "red": THEME["red"],
        "yellow": THEME["yellow"],
        "purple": THEME["purple"],
        "info": THEME["blue"],
    }.get(tone, THEME["blue"])
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-delta" style="color:{color};">{delta}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def normalize_code(code: Any) -> str:
    if pd.isna(code):
        return ""
    raw = str(code).strip().replace(".0", "")
    digits = re.sub(r"\D", "", raw)
    return digits.zfill(6)[-6:] if digits else raw[:6]


def infer_market(code: str) -> str:
    code = normalize_code(code)
    if code.startswith(("5", "6", "9")):
        return "SH"
    if code.startswith(("0", "1", "2", "3")):
        return "SZ"
    return "FUND"


def secid_for_code(code: str) -> str:
    market = infer_market(code)
    prefix = "1" if market == "SH" else "0"
    return f"{prefix}.{normalize_code(code)}"


def safe_float(value: Any, default: float = np.nan) -> float:
    try:
        if value in (None, "-", ""):
            return default
        return float(value)
    except Exception:
        return default


@st.cache_data(ttl=60 * 60)
def base_catalog() -> pd.DataFrame:
    df = pd.DataFrame(FUND_SEEDS).copy()
    df["fund_code"] = df["fund_code"].map(normalize_code)
    df["search_text"] = (
        df["fund_code"]
        + " "
        + df["fund_name"]
        + " "
        + df["module_level_1"]
        + " "
        + df["module_level_2"]
    ).str.lower()
    return df


def build_catalog() -> pd.DataFrame:
    catalog = base_catalog().copy()
    custom = st.session_state.get("custom_modules", pd.DataFrame())
    if not custom.empty:
        custom_rows = []
        for _, row in custom.iterrows():
            code = normalize_code(row.get("fund_code", ""))
            if not code:
                continue
            known = catalog[catalog["fund_code"] == code]
            fund_name = row.get("fund_name") or (known.iloc[0]["fund_name"] if not known.empty else f"自定义基金{code}")
            custom_rows.append(
                {
                    "fund_code": code,
                    "fund_name": fund_name,
                    "module_level_1": "用户自定义模块",
                    "module_level_2": row.get("module_name", "自定义"),
                    "market": infer_market(code),
                    "asset_type": "自定义",
                    "risk_level": "待评估",
                    "search_text": f"{code} {fund_name} 用户自定义模块 {row.get('module_name', '')}".lower(),
                }
            )
        if custom_rows:
            catalog = pd.concat([catalog, pd.DataFrame(custom_rows)], ignore_index=True)
    return catalog


def find_fund_meta(code: str, catalog: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    code = normalize_code(code)
    catalog = build_catalog() if catalog is None else catalog
    hit = catalog[catalog["fund_code"] == code]
    if not hit.empty:
        return hit.iloc[0].to_dict()
    return {
        "fund_code": code,
        "fund_name": f"自查基金{code}",
        "module_level_1": "用户自查",
        "module_level_2": "未归类",
        "market": infer_market(code),
        "asset_type": "自查",
        "risk_level": "待评估",
        "search_text": code,
    }


def search_funds(query: str, catalog: Optional[pd.DataFrame] = None, limit: int = 30) -> pd.DataFrame:
    catalog = build_catalog() if catalog is None else catalog
    q = (query or "").strip().lower()
    if not q:
        return catalog.head(limit).copy()
    mask = catalog["search_text"].str.contains(re.escape(q), case=False, na=False)
    result = catalog[mask].copy()
    if len(q) == 6 and q.isdigit() and normalize_code(q) not in set(result["fund_code"]):
        meta = find_fund_meta(q, catalog)
        result = pd.concat([pd.DataFrame([meta]), result], ignore_index=True)
    return result.head(limit)


@st.cache_data(ttl=30, show_spinner=False)
def fetch_etf_kline(code: str, days: int = 420) -> pd.DataFrame:
    code = normalize_code(code)
    end = datetime.today().strftime("%Y%m%d")
    beg = (datetime.today() - timedelta(days=max(days * 2, 800))).strftime("%Y%m%d")
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "secid": secid_for_code(code),
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",
        "fqt": "1",
        "beg": beg,
        "end": end,
        "_": int(time.time() * 1000),
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, params=params, headers=headers, timeout=8)
    resp.raise_for_status()
    payload = resp.json()
    klines = payload.get("data", {}).get("klines") or []
    rows = []
    for item in klines:
        parts = item.split(",")
        if len(parts) < 11:
            continue
        rows.append(
            {
                "date": pd.to_datetime(parts[0]),
                "open": safe_float(parts[1]),
                "close": safe_float(parts[2]),
                "high": safe_float(parts[3]),
                "low": safe_float(parts[4]),
                "volume": safe_float(parts[5]),
                "amount": safe_float(parts[6]),
                "amplitude": safe_float(parts[7]),
                "pct_change": safe_float(parts[8]),
                "change": safe_float(parts[9]),
                "turnover": safe_float(parts[10]),
                "source": "东方财富ETF/场内行情",
            }
        )
    df = pd.DataFrame(rows)
    if df.empty:
        raise ValueError("empty kline")
    return df.dropna(subset=["date", "close"]).tail(days).reset_index(drop=True)


@st.cache_data(ttl=120, show_spinner=False)
def fetch_fund_nav(code: str, days: int = 420) -> pd.DataFrame:
    code = normalize_code(code)
    url = f"https://fund.eastmoney.com/pingzhongdata/{code}.js"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, params={"v": int(time.time() * 1000)}, headers=headers, timeout=8)
    resp.raise_for_status()
    text = resp.text
    name_match = re.search(r'var fS_name = "([^"]+)"', text)
    trend_match = re.search(r"var Data_netWorthTrend = (\[.*?\]);", text, re.S)
    if not trend_match:
        raise ValueError("empty fund nav")
    records = json.loads(trend_match.group(1))
    rows = []
    for item in records:
        close = safe_float(item.get("y"))
        pct = safe_float(item.get("equityReturn"), 0.0)
        dt = pd.to_datetime(item.get("x"), unit="ms", errors="coerce")
        if pd.isna(dt) or pd.isna(close):
            continue
        rows.append(
            {
                "date": dt,
                "open": close,
                "close": close,
                "high": close,
                "low": close,
                "volume": 0.0,
                "amount": 0.0,
                "amplitude": abs(pct),
                "pct_change": pct,
                "change": np.nan,
                "turnover": np.nan,
                "source": "东方财富场外基金净值",
                "fund_name_remote": name_match.group(1) if name_match else "",
            }
        )
    df = pd.DataFrame(rows)
    if df.empty:
        raise ValueError("empty nav df")
    df["amount"] = synthetic_amount_series(code, len(df), df["pct_change"].to_numpy())
    df["volume"] = df["amount"] / df["close"].replace(0, np.nan)
    return df.dropna(subset=["date", "close"]).tail(days).reset_index(drop=True)


@st.cache_data(ttl=3, show_spinner=False)
def fetch_realtime_quote(code: str) -> Dict[str, Any]:
    """
    交易所基金实时快照。
    只用于 SH/SZ 场内基金、ETF、LOF。场外基金净值没有真正盘中实时价。
    """
    code = normalize_code(code)
    if infer_market(code) not in {"SH", "SZ"}:
        raise ValueError("该代码不是SH/SZ场内品种，无法获取盘中实时快照")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Referer": "https://quote.eastmoney.com/",
        "Accept": "application/json,text/plain,*/*",
    }

    errors = []

    # 方案1：单证券实时快照
    try:
        url = "https://push2.eastmoney.com/api/qt/stock/get"
        params = {
            "secid": secid_for_code(code),
            "fields": "f43,f44,f45,f46,f47,f48,f57,f58,f60,f86,f124,f168,f169,f170,f171",
            "_": int(time.time() * 1000),
        }
        resp = requests.get(url, params=params, headers=headers, timeout=5)
        resp.raise_for_status()
        data = resp.json().get("data") or {}
        if data and safe_float(data.get("f43"), np.nan) > 0:
            data["_realtime_fetch_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            data["_realtime_api"] = "qt/stock/get"
            return data
        errors.append("qt/stock/get返回为空或价格无效")
    except Exception as exc:
        errors.append(f"qt/stock/get失败：{exc}")

    # 方案2：列表实时快照备用
    try:
        url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
        params = {
            "fltt": "2",
            "secids": secid_for_code(code),
            "fields": "f12,f14,f2,f3,f4,f5,f6,f15,f16,f17,f18,f124",
            "_": int(time.time() * 1000),
        }
        resp = requests.get(url, params=params, headers=headers, timeout=5)
        resp.raise_for_status()
        diff = (resp.json().get("data") or {}).get("diff") or []
        if diff:
            item = diff[0]
            # 统一映射到 stock/get 的字段名，便于下游函数复用
            data = {
                "f43": item.get("f2"),
                "f44": item.get("f15"),
                "f45": item.get("f16"),
                "f46": item.get("f17"),
                "f47": item.get("f5"),
                "f48": item.get("f6"),
                "f57": item.get("f12"),
                "f58": item.get("f14"),
                "f60": item.get("f18"),
                "f124": item.get("f124"),
                "f170": item.get("f3"),
                "f169": item.get("f4"),
                "_realtime_fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "_realtime_api": "qt/ulist.np/get",
            }
            if safe_float(data.get("f43"), np.nan) > 0:
                return data
        errors.append("qt/ulist.np/get返回为空或价格无效")
    except Exception as exc:
        errors.append(f"qt/ulist.np/get失败：{exc}")

    raise ValueError("；".join(errors))


def normalize_quote_price(value: Any, reference: float = np.nan) -> float:
    raw = safe_float(value, np.nan)
    if pd.isna(raw) or raw <= 0:
        return np.nan
    candidates = [raw, raw / 10, raw / 100, raw / 1000, raw / 10000]
    if pd.notna(reference) and reference > 0:
        return min(candidates, key=lambda item: abs(math.log(max(item, 1e-9) / reference)))
    reasonable = [item for item in candidates if 0.05 <= item <= 100]
    return reasonable[0] if reasonable else raw


def normalize_quote_pct(value: Any, price: float, prev_close: float) -> float:
    raw = safe_float(value, np.nan)
    if pd.notna(raw):
        if abs(raw) > 100:
            return raw / 100
        if abs(raw) > 30:
            return raw / 10
        return raw
    if pd.notna(price) and pd.notna(prev_close) and prev_close > 0:
        return (price / prev_close - 1) * 100
    return np.nan


def parse_quote_time(data: Dict[str, Any]) -> pd.Timestamp:
    for key in ["f124", "f86"]:
        raw = data.get(key)
        if raw in (None, "", "-"):
            continue
        text = str(raw).strip()
        try:
            numeric = int(float(text))
        except Exception:
            continue
        if numeric > 10_000_000_000:
            parsed = pd.to_datetime(str(numeric), format="%Y%m%d%H%M%S", errors="coerce")
            if pd.notna(parsed):
                return pd.Timestamp(parsed)
        if numeric > 1_000_000_000:
            return pd.Timestamp(datetime.fromtimestamp(numeric))
    return pd.Timestamp.now()


def apply_realtime_quote(df: pd.DataFrame, code: str, data_mode: str = "") -> pd.DataFrame:
    """
    将东方财富实时快照合并到历史日线末端。
    修正点：如果实时接口成功，不再只依赖日线日期，而是用页面实际获取时间追加/替换最后一行，避免界面一直停在旧日线日期。
    """
    out = df.copy().sort_values("date").reset_index(drop=True)
    if out.empty or "仅演示" in data_mode:
        return out

    if infer_market(code) not in {"SH", "SZ"}:
        if not out.empty:
            out.at[out.index[-1], "source"] = str(out.iloc[-1].get("source", "")) + "；场外基金无盘中实时快照"
        return out

    try:
        quote = fetch_realtime_quote(code)
    except Exception as exc:
        if not out.empty:
            out.at[out.index[-1], "source"] = f"实时接口失败，使用历史日线；错误：{exc}"
        return out

    ref_close = safe_float(out.iloc[-1].get("close"), np.nan)
    prev_close = normalize_quote_price(quote.get("f60"), ref_close)
    if pd.isna(prev_close):
        prev_close = ref_close

    price = normalize_quote_price(quote.get("f43"), prev_close)
    if pd.isna(price) or price <= 0:
        out.at[out.index[-1], "source"] = "实时接口返回价格无效，使用历史日线"
        return out

    open_price = normalize_quote_price(quote.get("f46"), prev_close)
    high_price = normalize_quote_price(quote.get("f44"), price)
    low_price = normalize_quote_price(quote.get("f45"), price)
    pct_change = normalize_quote_pct(quote.get("f170"), price, prev_close)
    amount = safe_float(quote.get("f48"), safe_float(out.iloc[-1].get("amount"), 0))
    volume = safe_float(quote.get("f47"), np.nan)
    if pd.isna(volume) or volume <= 0:
        volume = amount / price if price > 0 else 0

    api_time = parse_quote_time(quote)
    fetch_time_text = quote.get("_realtime_fetch_time") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fetch_time = pd.Timestamp(fetch_time_text)
    api_name = quote.get("_realtime_api", "东方财富实时接口")

    high_candidates = [v for v in [high_price, price, open_price, prev_close] if pd.notna(v)]
    low_candidates = [v for v in [low_price, price, open_price, prev_close] if pd.notna(v)]

    realtime_row = {
        "date": fetch_time,
        "open": open_price if pd.notna(open_price) else prev_close,
        "close": price,
        "high": max(high_candidates) if high_candidates else price,
        "low": min(low_candidates) if low_candidates else price,
        "volume": volume,
        "amount": amount,
        "amplitude": ((max(high_candidates) - min(low_candidates)) / prev_close * 100) if high_candidates and low_candidates and pd.notna(prev_close) and prev_close > 0 else np.nan,
        "pct_change": pct_change,
        "change": price - prev_close if pd.notna(prev_close) else np.nan,
        "turnover": safe_float(quote.get("f168"), np.nan),
        "source": f"东方财富实时价格快照 · 获取时间 {fetch_time_text} · API时间 {api_time.strftime('%Y-%m-%d %H:%M:%S')} · {api_name}",
    }
    if "fund_name_remote" in out.columns:
        realtime_row["fund_name_remote"] = str(quote.get("f58") or out.iloc[-1].get("fund_name_remote", ""))

    # 如果同一天，替换末行；如果历史日线停留在旧交易日，追加一个实时快照行。
    last_day = pd.Timestamp(out.iloc[-1]["date"]).normalize()
    fetch_day = fetch_time.normalize()
    if last_day == fetch_day:
        for key, value in realtime_row.items():
            out.at[out.index[-1], key] = value
    else:
        out = pd.concat([out, pd.DataFrame([realtime_row])], ignore_index=True)

    return out.sort_values("date").reset_index(drop=True)


def synthetic_amount_series(code: str, n: int, pct_change: np.ndarray) -> np.ndarray:
    seed = int(normalize_code(code) or "1") % (2**32 - 1)
    rng = np.random.default_rng(seed)
    base = rng.uniform(4.5e7, 9.5e8)
    noise = rng.normal(1.0, 0.18, n).clip(0.32, 2.4)
    momentum = 1 + np.abs(np.nan_to_num(pct_change)) / 7
    return base * noise * momentum


@st.cache_data(ttl=60 * 60, show_spinner=False)
def synthetic_history(code: str, days: int = 420) -> pd.DataFrame:
    code = normalize_code(code)
    seed = int(code or "1") % (2**32 - 1)
    rng = np.random.default_rng(seed)
    end = pd.Timestamp.today().normalize()
    dates = pd.bdate_range(end=end, periods=days)
    base_price = 0.65 + (seed % 700) / 170.0
    drift = ((seed % 17) - 8) / 10000
    volatility = 0.010 + ((seed % 13) / 1000)
    shocks = rng.normal(drift, volatility, len(dates))
    trend_wave = np.sin(np.linspace(0, 8 * np.pi, len(dates))) * volatility * 0.25
    returns = shocks + trend_wave
    close = base_price * np.exp(np.cumsum(returns))
    open_ = close * (1 + rng.normal(0, 0.004, len(dates)))
    high = np.maximum(open_, close) * (1 + rng.random(len(dates)) * 0.014)
    low = np.minimum(open_, close) * (1 - rng.random(len(dates)) * 0.014)
    pct_change = pd.Series(close).pct_change().fillna(0).to_numpy() * 100
    amount = synthetic_amount_series(code, len(dates), pct_change)
    volume = amount / close
    return pd.DataFrame(
        {
            "date": dates,
            "open": open_,
            "close": close,
            "high": high,
            "low": low,
            "volume": volume,
            "amount": amount,
            "amplitude": (high - low) / close * 100,
            "pct_change": pct_change,
            "change": np.r_[0, np.diff(close)],
            "turnover": rng.uniform(0.4, 5.0, len(dates)),
            "source": "离线演示行情",
        }
    )


@st.cache_data(ttl=30, show_spinner=False)
def load_price_history(code: str, days: int = 420, data_mode: str = "") -> pd.DataFrame:
    code = normalize_code(code)
    if "仅演示" not in data_mode:
        try:
            if infer_market(code) in {"SH", "SZ"}:
                return fetch_etf_kline(code, days)
        except Exception:
            pass
        try:
            return fetch_fund_nav(code, days)
        except Exception:
            pass
    return synthetic_history(code, days)


def enrich_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().sort_values("date").reset_index(drop=True)
    for window in [5, 20, 60]:
        out[f"ma{window}"] = out["close"].rolling(window, min_periods=max(2, window // 3)).mean()
    out["amount_ma20"] = out["amount"].rolling(20, min_periods=5).mean()
    out["volume_ratio"] = out["amount"] / out["amount_ma20"].replace(0, np.nan)
    direction = np.sign(out["close"].diff().fillna(0))
    out["obv"] = (direction * out["volume"].fillna(0)).cumsum()
    out["obv_ma10"] = out["obv"].rolling(10, min_periods=3).mean()
    out["ma20_deviation"] = (out["close"] / out["ma20"] - 1) * 100
    out["trend_score"] = out.apply(calc_trend_score, axis=1)
    out["trend_label"] = out["trend_score"].map(trend_label)
    out["risk_label"] = out["ma20_deviation"].map(risk_label)
    out["money_strength"] = calc_money_strength(out)
    out["money_signal"] = out.apply(classify_money_signal, axis=1)
    out["action_label"] = out.apply(action_label, axis=1)
    return out


def calc_trend_score(row: pd.Series) -> int:
    score = 0
    close = row.get("close", np.nan)
    ma5 = row.get("ma5", np.nan)
    ma20 = row.get("ma20", np.nan)
    ma60 = row.get("ma60", np.nan)
    if pd.notna(close) and pd.notna(ma5) and close > ma5:
        score += 1
    if pd.notna(close) and pd.notna(ma20) and close > ma20:
        score += 1
    if pd.notna(close) and pd.notna(ma60) and close > ma60:
        score += 1
    if pd.notna(ma5) and pd.notna(ma20) and ma5 > ma20:
        score += 1
    if pd.notna(ma20) and pd.notna(ma60) and ma20 > ma60:
        score += 1
    return int(score)


def trend_label(score: int) -> str:
    if score >= 5:
        return "强趋势"
    if score == 4:
        return "趋势偏强"
    if score == 3:
        return "趋势修复"
    if score == 2:
        return "震荡偏弱"
    return "趋势偏弱"


def risk_label(deviation: float) -> str:
    if pd.isna(deviation):
        return "待观察"
    if deviation > 8:
        return "短期过热"
    if deviation > 4:
        return "略偏高"
    if deviation >= -4:
        return "正常波动"
    if deviation >= -8:
        return "回调区"
    return "深度回调"


def calc_money_strength(df: pd.DataFrame) -> pd.Series:
    pct_part = df["pct_change"].fillna(0).clip(-6, 6) / 6
    vol_part = (df["volume_ratio"].fillna(1) - 1).clip(-1.2, 1.8) / 1.8
    obv_delta = (df["obv"] - df["obv_ma10"]).fillna(0)
    obv_part = np.sign(obv_delta) * np.minimum(np.abs(obv_delta) / (df["volume"].rolling(20, min_periods=5).mean().replace(0, np.nan)), 1)
    obv_part = pd.Series(obv_part).fillna(0).to_numpy()
    strength = (pct_part * 55 + vol_part * 30 + obv_part * 15).clip(-100, 100)
    return pd.Series(strength, index=df.index)


def classify_money_signal(row: pd.Series) -> str:
    pct = safe_float(row.get("pct_change"), 0)
    vr = safe_float(row.get("volume_ratio"), 1)
    strength = safe_float(row.get("money_strength"), 0)
    if abs(pct) <= 0.6 and vr >= 1.55:
        return "分歧放量"
    if pct > 0 and vr >= 1.5 and strength > 28:
        return "强流入"
    if pct > 0 and vr >= 1.1:
        return "温和流入"
    if pct < 0 and vr >= 1.5 and strength < -28:
        return "强撤出"
    if pct < 0 and vr >= 1.1:
        return "温和撤出"
    if vr < 0.75:
        return "缩量观望"
    return "中性"


def action_label(row: pd.Series) -> str:
    trend = int(row.get("trend_score", 0))
    risk = row.get("risk_label", "")
    money = row.get("money_signal", "")
    if risk == "短期过热" and trend >= 4:
        return "进入止盈观察区"
    if trend >= 4 and money in {"强流入", "温和流入", "中性"}:
        return "适合继续持有"
    if trend == 3 and risk in {"正常波动", "回调区"}:
        return "等待回踩确认"
    if trend <= 2 and money in {"强撤出", "温和撤出"}:
        return "需要减仓防守"
    if risk in {"略偏高", "短期过热"}:
        return "不宜追高"
    if risk in {"回调区", "深度回调"} and trend >= 2:
        return "适合小额定投观察"
    return "趋势破位谨慎" if trend <= 1 else "继续观察"


@st.cache_data(ttl=5, show_spinner=False)
def analyze_fund_cached(code: str, data_mode: str = "") -> Tuple[pd.DataFrame, Dict[str, Any]]:
    code = normalize_code(code)
    raw = load_price_history(code, 420, data_mode)
    raw = apply_realtime_quote(raw, code, data_mode)
    enriched = enrich_indicators(raw)
    latest = enriched.iloc[-1].to_dict()
    return enriched, latest


def analyze_fund(code: str, catalog: Optional[pd.DataFrame] = None) -> Tuple[pd.DataFrame, FundSnapshot]:
    catalog = build_catalog() if catalog is None else catalog
    meta = find_fund_meta(code, catalog)
    df, latest = analyze_fund_cached(meta["fund_code"], st.session_state.get("data_mode", ""))
    latest_name = df.iloc[-1].get("fund_name_remote", "") if "fund_name_remote" in df.columns else ""
    fund_name = meta.get("fund_name") or latest_name or f"基金{meta['fund_code']}"
    snapshot = FundSnapshot(
        fund_code=meta["fund_code"],
        fund_name=fund_name,
        module_level_1=meta.get("module_level_1", "用户自查"),
        module_level_2=meta.get("module_level_2", "未归类"),
        close=safe_float(latest.get("close")),
        pct_change=safe_float(latest.get("pct_change"), 0),
        amount=safe_float(latest.get("amount"), 0),
        volume_ratio=safe_float(latest.get("volume_ratio"), 1),
        trend_score=int(latest.get("trend_score", 0)),
        trend_label=str(latest.get("trend_label", "待观察")),
        money_signal=str(latest.get("money_signal", "中性")),
        risk_label=str(latest.get("risk_label", "待观察")),
        action_label=str(latest.get("action_label", "继续观察")),
        ma20_deviation=safe_float(latest.get("ma20_deviation"), 0),
        source=str(latest.get("source", "未知")),
    )
    return df, snapshot


def snapshot_row(code: str, catalog: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    _, snap = analyze_fund(code, catalog)
    return {
        "模块": snap.module_level_1,
        "细分": snap.module_level_2,
        "基金名称": snap.fund_name,
        "基金代码": snap.fund_code,
        "当前价格": snap.close,
        "今日涨跌幅": snap.pct_change,
        "成交额": snap.amount,
        "量能倍率": snap.volume_ratio,
        "趋势评分": snap.trend_score,
        "趋势状态": snap.trend_label,
        "资金信号": snap.money_signal,
        "风险状态": snap.risk_label,
        "操作提示": snap.action_label,
        "数据源": snap.source,
    }


def build_pool_snapshot(catalog: pd.DataFrame, codes: Iterable[str], limit: int = 40) -> pd.DataFrame:
    rows = []
    seen = set()
    for code in list(codes)[:limit]:
        code = normalize_code(code)
        if not code or code in seen:
            continue
        seen.add(code)
        try:
            rows.append(snapshot_row(code, catalog))
        except Exception:
            continue
    return pd.DataFrame(rows)


def find_alias_column(df: pd.DataFrame, aliases: List[str]) -> Optional[str]:
    normalized = {str(c).strip().lower(): c for c in df.columns}
    for alias in aliases:
        key = alias.strip().lower()
        if key in normalized:
            return normalized[key]
    for col in df.columns:
        col_text = str(col).strip().lower()
        if any(alias.lower() in col_text for alias in aliases):
            return col
    return None


def standardize_positions(raw: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame()
    for target, aliases in COLUMN_ALIASES.items():
        col = find_alias_column(raw, aliases)
        if col is not None:
            out[target] = raw[col]
    for col, default in [
        ("fund_code", ""),
        ("fund_name", ""),
        ("shares", 0.0),
        ("cost_price", 0.0),
        ("buy_date", ""),
        ("account_type", "默认账户"),
        ("notes", ""),
    ]:
        if col not in out.columns:
            out[col] = default
    out["fund_code"] = out["fund_code"].map(normalize_code)
    out["fund_name"] = out["fund_name"].fillna("").astype(str)
    out["shares"] = pd.to_numeric(out["shares"], errors="coerce").fillna(0)
    out["cost_price"] = pd.to_numeric(out["cost_price"], errors="coerce").fillna(0)
    out["buy_date"] = pd.to_datetime(out["buy_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    out["buy_date"] = out["buy_date"].replace("NaT", "")
    out["account_type"] = out["account_type"].fillna("默认账户").astype(str)
    out["notes"] = out["notes"].fillna("").astype(str)
    out = out[out["fund_code"].str.len() == 6].copy()
    out = out.reset_index(drop=True)
    return out[["fund_code", "fund_name", "shares", "cost_price", "buy_date", "account_type", "notes"]]


def portfolio_positions(catalog: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    catalog = build_catalog() if catalog is None else catalog
    positions = st.session_state.get("positions", pd.DataFrame()).copy()
    if positions.empty:
        return positions
    positions = standardize_positions(positions)
    rows = []
    for idx, pos in positions.iterrows():
        code = normalize_code(pos["fund_code"])
        meta = find_fund_meta(code, catalog)
        try:
            _, snap = analyze_fund(code, catalog)
            current_price = snap.close
            pct_change = snap.pct_change
            trend = snap.trend_label
            money = snap.money_signal
            action = snap.action_label
            risk = snap.risk_label
        except Exception:
            current_price = np.nan
            pct_change = 0
            trend = money = action = risk = "待观察"
        shares = safe_float(pos["shares"], 0)
        cost_price = safe_float(pos["cost_price"], 0)
        current_value = shares * current_price if pd.notna(current_price) else 0
        cost_value = shares * cost_price
        pnl = current_value - cost_value
        ret = pnl / cost_value * 100 if cost_value > 0 else np.nan
        buy_dt = pd.to_datetime(pos["buy_date"], errors="coerce")
        hold_days = (pd.Timestamp.today().normalize() - buy_dt).days if pd.notna(buy_dt) else np.nan
        rows.append(
            {
                "position_id": idx + 1,
                "基金代码": code,
                "基金名称": pos["fund_name"] or meta["fund_name"],
                "模块": meta.get("module_level_1", "用户自查"),
                "细分": meta.get("module_level_2", "未归类"),
                "持仓份额": shares,
                "成本价": cost_price,
                "当前价": current_price,
                "持仓金额": current_value,
                "持仓成本": cost_value,
                "浮盈亏": pnl,
                "收益率": ret,
                "今日涨跌幅": pct_change,
                "持仓天数": hold_days,
                "趋势状态": trend,
                "资金信号": money,
                "风险状态": risk,
                "操作提示": action,
                "账户类型": pos["account_type"],
                "备注": pos["notes"],
            }
        )
    df = pd.DataFrame(rows)
    total_value = df["持仓金额"].sum()
    df["仓位占比"] = np.where(total_value > 0, df["持仓金额"] / total_value * 100, 0)
    return df


def portfolio_summary(pos_df: pd.DataFrame) -> Dict[str, Any]:
    if pos_df.empty:
        return {
            "total_value": 0,
            "total_cost": 0,
            "total_pnl": 0,
            "total_ret": 0,
            "today_pnl": 0,
            "fund_count": 0,
            "risk_level": "待导入",
            "strong_modules": 0,
            "max_fund_weight": 0,
            "max_module_weight": 0,
            "risk_score": 0,
        }
    total_value = pos_df["持仓金额"].sum()
    total_cost = pos_df["持仓成本"].sum()
    total_pnl = total_value - total_cost
    total_ret = total_pnl / total_cost * 100 if total_cost > 0 else 0
    today_pnl = (pos_df["持仓金额"] * pos_df["今日涨跌幅"].fillna(0) / 100).sum()
    fund_count = pos_df["基金代码"].nunique()
    max_fund_weight = pos_df["仓位占比"].max()
    module_weight = pos_df.groupby("模块")["持仓金额"].sum() / total_value * 100 if total_value > 0 else pd.Series(dtype=float)
    max_module_weight = module_weight.max() if not module_weight.empty else 0
    hot_funds = (pos_df["风险状态"].isin(["短期过热", "略偏高"]) & (pos_df["仓位占比"] > 12)).sum()
    weak_funds = (pos_df["趋势状态"].isin(["趋势偏弱", "震荡偏弱"]) & (pos_df["仓位占比"] > 10)).sum()
    risk_score = min(100, max_module_weight * 0.55 + max_fund_weight * 0.35 + hot_funds * 8 + weak_funds * 10)
    risk_level_value = "高" if risk_score >= 65 else "中" if risk_score >= 35 else "低"
    strong_modules = pos_df[pos_df["趋势状态"].isin(["强趋势", "趋势偏强"])]["模块"].nunique()
    return {
        "total_value": total_value,
        "total_cost": total_cost,
        "total_pnl": total_pnl,
        "total_ret": total_ret,
        "today_pnl": today_pnl,
        "fund_count": fund_count,
        "risk_level": risk_level_value,
        "strong_modules": strong_modules,
        "max_fund_weight": max_fund_weight,
        "max_module_weight": max_module_weight,
        "risk_score": risk_score,
    }


def build_portfolio_curve(pos_df: pd.DataFrame, catalog: pd.DataFrame, days: int = 120) -> pd.DataFrame:
    if pos_df.empty:
        return pd.DataFrame()
    pieces = []
    for _, row in pos_df.iterrows():
        code = row["基金代码"]
        shares = row["持仓份额"]
        try:
            hist, _ = analyze_fund(code, catalog)
            part = hist[["date", "close"]].tail(days).copy()
            part[code] = part["close"] * shares
            pieces.append(part[["date", code]])
        except Exception:
            continue
    if not pieces:
        return pd.DataFrame()
    curve = pieces[0]
    for part in pieces[1:]:
        curve = curve.merge(part, on="date", how="outer")
    curve = curve.sort_values("date").ffill().dropna(how="all", subset=[c for c in curve.columns if c != "date"])
    value_cols = [c for c in curve.columns if c != "date"]
    curve["组合市值"] = curve[value_cols].sum(axis=1)
    curve["累计收益率"] = (curve["组合市值"] / curve["组合市值"].iloc[0] - 1) * 100
    return curve[["date", "组合市值", "累计收益率"]]


def make_price_chart(df: pd.DataFrame, title: str) -> go.Figure:
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.54, 0.25, 0.21],
        specs=[[{"secondary_y": False}], [{"secondary_y": False}], [{"secondary_y": False}]],
    )
    fig.add_trace(go.Scatter(x=df["date"], y=df["close"], name="价格/净值", line=dict(color="#F8FAFC", width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["date"], y=df["ma5"], name="MA5", line=dict(color="#58D5FF", width=1.4)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["date"], y=df["ma20"], name="MA20", line=dict(color="#FBBF24", width=1.4)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["date"], y=df["ma60"], name="MA60", line=dict(color="#A78BFA", width=1.4)), row=1, col=1)
    amount_colors = np.where(df["pct_change"].fillna(0) >= 0, "#22C55E", "#EF4444")
    fig.add_trace(go.Bar(x=df["date"], y=df["amount"], name="成交额", marker_color=amount_colors, opacity=0.62), row=2, col=1)
    fig.add_trace(go.Scatter(x=df["date"], y=df["amount_ma20"], name="成交额MA20", line=dict(color="#58D5FF", width=1.2)), row=2, col=1)
    strength_colors = np.where(df["money_strength"].fillna(0) >= 0, "#22C55E", "#EF4444")
    fig.add_trace(go.Bar(x=df["date"], y=df["money_strength"], name="资金行为强度", marker_color=strength_colors, opacity=0.75), row=3, col=1)
    strong_in = df[df["money_signal"] == "强流入"].tail(12)
    strong_out = df[df["money_signal"] == "强撤出"].tail(12)
    fig.add_trace(
        go.Scatter(
            x=strong_in["date"],
            y=strong_in["close"],
            mode="markers",
            name="强流入",
            marker=dict(symbol="triangle-up", size=10, color="#22C55E"),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=strong_out["date"],
            y=strong_out["close"],
            mode="markers",
            name="强撤出",
            marker=dict(symbol="triangle-down", size=10, color="#EF4444"),
        ),
        row=1,
        col=1,
    )
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        title=title,
        height=660,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(12,26,46,0.94)",
        margin=dict(l=20, r=20, t=48, b=20),
        legend=dict(orientation="h", y=1.04, x=0, font=dict(size=11)),
        hovermode="x unified",
    )
    fig.update_yaxes(gridcolor="rgba(214,226,243,.16)", row=1, col=1)
    fig.update_yaxes(gridcolor="rgba(214,226,243,.16)", row=2, col=1, tickformat=".2s")
    fig.update_yaxes(gridcolor="rgba(214,226,243,.16)", row=3, col=1, range=[-100, 100])
    fig.update_xaxes(gridcolor="rgba(214,226,243,.12)")
    return fig


def make_portfolio_curve_chart(curve: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if not curve.empty:
        fig.add_trace(
            go.Scatter(
                x=curve["date"],
                y=curve["组合市值"],
                mode="lines",
                name="组合市值",
                line=dict(color="#58D5FF", width=2.2),
                fill="tozeroy",
                fillcolor="rgba(88, 213, 255, 0.12)",
            )
        )
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        height=360,
        margin=dict(l=18, r=18, t=28, b=18),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(12,26,46,0.92)",
        legend=dict(orientation="h"),
    )
    fig.update_yaxes(gridcolor="rgba(214,226,243,.16)", tickformat=".2s")
    fig.update_xaxes(gridcolor="rgba(214,226,243,.12)")
    return fig


def make_module_heatmap(pool_df: pd.DataFrame) -> go.Figure:
    if pool_df.empty:
        z = np.array([[0]])
        x = ["暂无"]
        y = ["暂无"]
    else:
        pivot = pool_df.pivot_table(index="模块", columns="细分", values="趋势评分", aggfunc="mean").fillna(0)
        z = pivot.values
        x = pivot.columns
        y = pivot.index
    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=x,
            y=y,
            colorscale=[
                [0, "#111827"],
                [0.25, "#26324A"],
                [0.5, "#FBBF24"],
                [0.75, "#22C55E"],
                [1, "#58D5FF"],
            ],
            zmin=0,
            zmax=5,
            colorbar=dict(title="趋势"),
        )
    )
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        height=360,
        margin=dict(l=18, r=18, t=28, b=18),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(12,26,46,0.92)",
    )
    return fig


def make_module_radar(pos_df: pd.DataFrame) -> go.Figure:
    if pos_df.empty:
        values = [0, 0, 0, 0, 0, 0]
    else:
        total = max(pos_df["持仓金额"].sum(), 1)
        trend_score = (
            pos_df["趋势状态"].map({"强趋势": 100, "趋势偏强": 80, "趋势修复": 60, "震荡偏弱": 35, "趋势偏弱": 20}).fillna(50)
            * pos_df["持仓金额"]
            / total
        ).sum()
        money_score = (
            pos_df["资金信号"].map({"强流入": 100, "温和流入": 78, "中性": 55, "缩量观望": 45, "分歧放量": 42, "温和撤出": 25, "强撤出": 10}).fillna(50)
            * pos_df["持仓金额"]
            / total
        ).sum()
        risk_score = (
            pos_df["风险状态"].map({"正常波动": 90, "略偏高": 62, "短期过热": 38, "回调区": 60, "深度回调": 30, "待观察": 50}).fillna(50)
            * pos_df["持仓金额"]
            / total
        ).sum()
        balance_score = max(10, 100 - pos_df.groupby("模块")["持仓金额"].sum().max() / total * 100)
        profit_score = min(100, max(0, 50 + pos_df["收益率"].fillna(0).mean() * 2))
        volatility_score = max(10, 100 - pos_df["风险状态"].isin(["短期过热", "深度回调"]).mean() * 55)
        values = [trend_score, money_score, risk_score, balance_score, profit_score, volatility_score]
    labels = ["趋势结构", "资金行为", "风险位置", "仓位均衡", "收益贡献", "波动韧性"]
    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=values + [values[0]],
            theta=labels + [labels[0]],
            fill="toself",
            name="组合画像",
            line=dict(color="#58D5FF", width=2),
            fillcolor="rgba(88, 213, 255, 0.18)",
        )
    )
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        height=360,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=30, b=20),
        polar=dict(
            bgcolor="rgba(12,26,46,0.82)",
            radialaxis=dict(range=[0, 100], showticklabels=False, gridcolor="rgba(214,226,243,.18)"),
            angularaxis=dict(gridcolor="rgba(214,226,243,.18)"),
        ),
        showlegend=False,
    )
    return fig


def make_structure_charts(pos_df: pd.DataFrame) -> Tuple[go.Figure, go.Figure, go.Figure]:
    if pos_df.empty:
        empty = pd.DataFrame({"分类": ["暂无"], "金额": [1]})
        pie = px.pie(empty, names="分类", values="金额", template=PLOTLY_TEMPLATE)
        bar = px.bar(empty, x="分类", y="金额", template=PLOTLY_TEMPLATE)
        risk = px.bar(empty, x="分类", y="金额", template=PLOTLY_TEMPLATE)
        return pie, bar, risk
    module = pos_df.groupby("模块", as_index=False)["持仓金额"].sum().sort_values("持仓金额", ascending=False)
    pie = px.pie(module, names="模块", values="持仓金额", hole=0.52, template=PLOTLY_TEMPLATE, color_discrete_sequence=px.colors.qualitative.Set3)
    pie.update_layout(height=330, margin=dict(l=10, r=10, t=28, b=10), paper_bgcolor="rgba(0,0,0,0)")
    sub = pos_df.groupby("细分", as_index=False)["持仓金额"].sum().sort_values("持仓金额", ascending=True).tail(12)
    bar = px.bar(sub, x="持仓金额", y="细分", orientation="h", template=PLOTLY_TEMPLATE, color="持仓金额", color_continuous_scale="Blues")
    bar.update_layout(height=330, margin=dict(l=10, r=10, t=28, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(12,26,46,0.92)", showlegend=False)
    risk_df = pos_df.groupby("风险状态", as_index=False)["持仓金额"].sum()
    risk = px.bar(risk_df, x="风险状态", y="持仓金额", template=PLOTLY_TEMPLATE, color="风险状态", color_discrete_map={"短期过热": "#EF4444", "略偏高": "#FBBF24", "正常波动": "#22C55E", "回调区": "#A78BFA", "深度回调": "#EF4444"})
    risk.update_layout(height=330, margin=dict(l=10, r=10, t=28, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(12,26,46,0.92)", showlegend=False)
    return pie, bar, risk


def generate_fund_interpretation(snap: FundSnapshot, hist: pd.DataFrame, position: Optional[pd.Series] = None) -> str:
    latest = hist.iloc[-1]
    trend = (
        f"该基金当前趋势评分为 {snap.trend_score}/5，处于「{snap.trend_label}」状态。"
        f"价格相对 MA20 偏离 {snap.ma20_deviation:.2f}%，风险位置判断为「{snap.risk_label}」。"
    )
    money = (
        f"成交额相对 20 日均额为 {snap.volume_ratio:.2f} 倍，资金行为信号为「{snap.money_signal}」。"
        f"若后续资金强度连续转弱，需要降低对短期延续性的预期。"
    )
    risk = "当前位置适合以趋势线作为观察边界，重点看 MA20 得失、量能是否异常放大，以及资金信号是否从流入转为撤出。"
    action = f"策略提示为「{snap.action_label}」。"
    if snap.risk_label == "短期过热":
        risk = "短期位置已经偏热，继续上涨时更适合做止盈观察，不适合在放量急涨后追高。"
    elif snap.risk_label in {"回调区", "深度回调"}:
        risk = "基金进入回调观察区，应优先确认趋势是否企稳；若仍在 MA20 下方运行，定投或加仓需要降低频率。"
    if snap.money_signal in {"强撤出", "温和撤出"}:
        action = "资金信号偏弱，若叠加跌破 MA20 或 MA60，应优先控制仓位与回撤。"
    position_text = ""
    if position is not None and not position.empty:
        cost_price = safe_float(position.get("成本价"), np.nan)
        ret = safe_float(position.get("收益率"), np.nan)
        weight = safe_float(position.get("仓位占比"), np.nan)
        if pd.notna(cost_price):
            position_text = (
                f"你的持仓成本为 {cost_price:.3f}，当前价格为 {snap.close:.3f}，"
                f"浮动收益率约 {ret:.2f}%，组合仓位占比约 {weight:.1f}%。"
            )
            if ret > 20:
                position_text += " 已进入较明显盈利区，可考虑保留核心仓位并分批锁定部分收益。"
            elif ret < -10:
                position_text += " 当前亏损幅度较大，需要复盘买入逻辑是否仍成立，避免用加仓替代风控。"
            elif snap.close < cost_price and snap.trend_score <= 2:
                position_text += " 当前价格低于成本且趋势偏弱，建议先观察趋势修复再考虑加仓。"
    next_watch = (
        f"下一步重点关注: 收盘价是否守住 MA20（{safe_float(latest.get('ma20')):.3f}）、"
        f"量能倍率是否继续维持在 1.10 以上，以及资金信号是否重新回到流入侧。"
    )
    return "\n\n".join([trend, money, risk, position_text, action, next_watch]).strip()


def generate_portfolio_diagnosis(pos_df: pd.DataFrame, summary: Dict[str, Any]) -> List[str]:
    if pos_df.empty:
        return ["尚未导入实仓。可以先使用模板导入，或在实仓管理页手动录入持仓。"]
    notes = []
    module_weight = pos_df.groupby("模块")["持仓金额"].sum().sort_values(ascending=False)
    total = max(pos_df["持仓金额"].sum(), 1)
    top_module = module_weight.index[0]
    top_weight = module_weight.iloc[0] / total * 100
    if top_weight > 50:
        notes.append(f"当前组合中「{top_module}」仓位占比 {top_weight:.1f}%，单一模块集中度偏高。")
    elif top_weight > 35:
        notes.append(f"组合明显偏向「{top_module}」，仓位占比 {top_weight:.1f}%，需要关注市场风格切换。")
    else:
        notes.append(f"组合最大模块为「{top_module}」，仓位占比 {top_weight:.1f}%，结构相对可控。")
    high_risk = pos_df[pos_df["风险状态"].isin(["短期过热", "略偏高"])]
    if not high_risk.empty:
        names = "、".join(high_risk.sort_values("仓位占比", ascending=False)["基金名称"].head(3))
        notes.append(f"{names} 处于偏高或过热位置，适合进入止盈和回撤观察。")
    weak = pos_df[pos_df["趋势状态"].isin(["趋势偏弱", "震荡偏弱"])]
    if not weak.empty:
        names = "、".join(weak.sort_values("仓位占比", ascending=False)["基金名称"].head(3))
        notes.append(f"{names} 趋势结构偏弱，若继续跌破中期均线，应降低补仓冲动。")
    overlap = pos_df.groupby("细分")["基金代码"].nunique()
    overlap = overlap[overlap >= 2]
    if not overlap.empty:
        notes.append(f"存在底层资产可能重叠的细分方向: {'、'.join(overlap.index[:4])}，需要检查是否重复暴露。")
    if {"电气电力与新能源", "半导体与芯片", "科技成长"}.intersection(set(module_weight.index)):
        growth_weight = module_weight[module_weight.index.intersection(["电气电力与新能源", "半导体与芯片", "科技成长", "人工智能与数字经济"])].sum() / total * 100
        if growth_weight > 45:
            notes.append(f"成长风格暴露约 {growth_weight:.1f}%，市场波动放大时组合净值弹性会明显上升。")
    if summary["risk_level"] == "高":
        notes.append("组合风险等级偏高，建议保留核心仓位，降低同方向追涨型加仓。")
    return notes


def generate_alerts(pos_df: pd.DataFrame, catalog: pd.DataFrame) -> Dict[str, List[str]]:
    alerts = {"今日需要关注": [], "风险升高": [], "可以继续观察": [], "建议复盘": []}
    if pos_df.empty:
        alerts["建议复盘"].append("尚未导入实仓，组合风险与收益归因无法计算。")
        return alerts
    total_value = max(pos_df["持仓金额"].sum(), 1)
    module_weight = pos_df.groupby("模块")["持仓金额"].sum() / total_value * 100
    for module, weight in module_weight.items():
        if weight > 50:
            alerts["风险升高"].append(f"{module} 模块仓位 {weight:.1f}%，超过 50% 集中度阈值。")
    for _, row in pos_df.iterrows():
        code = row["基金代码"]
        try:
            hist, snap = analyze_fund(code, catalog)
            latest = hist.iloc[-1]
            prev = hist.iloc[-2] if len(hist) > 1 else latest
            if latest["close"] < latest["ma20"] and prev["close"] >= prev["ma20"]:
                alerts["今日需要关注"].append(f"{row['基金名称']} 跌破 MA20，观察是否放量。")
            if latest["ma5"] < latest["ma20"] and prev["ma5"] >= prev["ma20"]:
                alerts["风险升高"].append(f"{row['基金名称']} 出现 MA5 下穿 MA20。")
            if snap.ma20_deviation > 8:
                alerts["风险升高"].append(f"{row['基金名称']} MA20 偏离 {snap.ma20_deviation:.1f}%，短期过热。")
            last3 = hist.tail(3)
            if len(last3) == 3 and (last3["pct_change"] < 0).all() and (last3["volume_ratio"] > 1.1).sum() >= 2:
                alerts["风险升高"].append(f"{row['基金名称']} 近三日放量下跌，需要控制回撤。")
            if row["仓位占比"] > 30:
                alerts["风险升高"].append(f"{row['基金名称']} 单只仓位 {row['仓位占比']:.1f}%，超过 30%。")
            if row["收益率"] > 20:
                alerts["可以继续观察"].append(f"{row['基金名称']} 盈利 {row['收益率']:.1f}%，进入止盈观察区。")
            if row["收益率"] < -10:
                alerts["建议复盘"].append(f"{row['基金名称']} 亏损 {abs(row['收益率']):.1f}%，需要复盘买入逻辑。")
            if row["当前价"] < row["成本价"]:
                alerts["建议复盘"].append(f"{row['基金名称']} 已跌破成本价。")
            if snap.action_label in {"适合继续持有", "等待回踩确认"}:
                alerts["可以继续观察"].append(f"{row['基金名称']} 当前策略标签: {snap.action_label}。")
        except Exception:
            continue
    for key in alerts:
        if not alerts[key]:
            alerts[key].append("暂无触发项。")
        alerts[key] = alerts[key][:6]
    return alerts


def render_sidebar(catalog: pd.DataFrame) -> str:
    with st.sidebar:
        st.markdown(f"### {APP_NAME}")
        st.caption("基金智能分析平台")
        query = st.text_input("全局搜索", placeholder="输入基金代码、名称、模块或关键词")
        if query:
            results = search_funds(query, catalog, limit=5)
            for _, row in results.iterrows():
                label = f"{row['fund_name']} · {row['fund_code']}"
                if st.button(label, key=f"side_pick_{row['fund_code']}_{row['module_level_2']}", use_container_width=True):
                    st.session_state["selected_fund"] = row["fund_code"]
                    st.session_state["nav"] = "基金分析"
                    rerun_app()
        st.divider()
        nav_options = ["首页驾驶舱", "基金分析", "实仓管理", "模块行情", "自定义搜索", "设置中心"]
        nav = st.radio("功能模块", nav_options, key="nav", label_visibility="collapsed")
        st.divider()
        st.caption("数据源")
        st.selectbox(
            "行情模式",
            DATA_MODE_OPTIONS,
            key="data_mode",
            label_visibility="collapsed",
        )
        st.caption("自动刷新")
        st.selectbox(
            "自动刷新",
            REFRESH_OPTIONS,
            key="refresh_frequency",
            label_visibility="collapsed",
        )
        if st.button("刷新行情缓存", use_container_width=True):
            st.cache_data.clear()
            st.session_state["last_refresh_ts"] = time.time()
            rerun_app()
        st.caption(f"页面时间: {datetime.now().strftime('%H:%M:%S')} | 缓存刷新: {datetime.fromtimestamp(st.session_state['last_refresh_ts']).strftime('%H:%M:%S')}")
    return nav


def page_dashboard(catalog: pd.DataFrame) -> None:
    render_hero()
    pos_df = portfolio_positions(catalog)
    summary = portfolio_summary(pos_df)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        render_metric_card("总资产", fmt_money(summary["total_value"]), f"投入 {fmt_money(summary['total_cost'])}", "info")
    with c2:
        tone = "green" if summary["today_pnl"] >= 0 else "red"
        render_metric_card("今日盈亏", fmt_money(summary["today_pnl"]), "按持仓涨跌估算", tone)
    with c3:
        tone = "green" if summary["total_pnl"] >= 0 else "red"
        render_metric_card("累计收益", fmt_money(summary["total_pnl"]), fmt_pct(summary["total_ret"]), tone)
    with c4:
        render_metric_card("持仓基金数", str(summary["fund_count"]), f"最大单基 {summary['max_fund_weight']:.1f}%", "purple")
    with c5:
        tone = "red" if summary["risk_level"] == "高" else "yellow" if summary["risk_level"] == "中" else "green"
        render_metric_card("当前风险等级", summary["risk_level"], f"评分 {summary['risk_score']:.0f}/100", tone)
    with c6:
        render_metric_card("强势模块数量", str(summary["strong_modules"]), f"最大模块 {summary['max_module_weight']:.1f}%", "info")

    left, right = st.columns([1.36, 1])
    with left:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        section_title("实仓收益曲线", "按导入持仓份额与历史净值/价格估算")
        curve = build_portfolio_curve(pos_df, catalog)
        render_plotly_chart(make_portfolio_curve_chart(curve), "dashboard_portfolio_curve", fullscreen_height=880)
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        section_title("组合强弱雷达", "趋势 · 资金 · 风险 · 均衡")
        render_plotly_chart(make_module_radar(pos_df), "dashboard_module_radar", fullscreen_height=860)
        st.markdown("</div>", unsafe_allow_html=True)

    pool_codes = catalog["fund_code"].drop_duplicates().head(36)
    pool_df = build_pool_snapshot(catalog, pool_codes, limit=36)
    left2, right2 = st.columns([1.2, 1])
    with left2:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        section_title("模块强弱热力图", "数值越高代表趋势结构越强")
        render_plotly_chart(make_module_heatmap(pool_df), "dashboard_module_heatmap", fullscreen_height=860)
        st.markdown("</div>", unsafe_allow_html=True)
    with right2:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        section_title("今日重点信号", "由趋势、量能、资金与实仓仓位联合触发")
        alerts = generate_alerts(pos_df, catalog)
        for group, items in alerts.items():
            tone = "high" if group in {"风险升高", "今日需要关注"} else "mid" if group == "建议复盘" else "low"
            st.markdown(badge(group, tone), unsafe_allow_html=True)
            for item in items[:4]:
                st.markdown(f'<div class="terminal-line">· {item}</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    section_title("需要关注的基金", "按风险位置、资金信号与仓位占比排序")
    if pos_df.empty:
        st.info("暂无实仓。可以在实仓管理页导入 Excel / CSV 或手动录入。")
    else:
        focus = pos_df.sort_values(["风险状态", "仓位占比"], ascending=[True, False])
        show_df = focus[
            [
                "基金名称",
                "基金代码",
                "模块",
                "持仓金额",
                "浮盈亏",
                "收益率",
                "仓位占比",
                "趋势状态",
                "资金信号",
                "风险状态",
                "操作提示",
            ]
        ].copy()
        st.dataframe(
            show_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "持仓金额": st.column_config.NumberColumn(format="￥%.2f"),
                "浮盈亏": st.column_config.NumberColumn(format="￥%.2f"),
                "收益率": st.column_config.NumberColumn(format="%.2f%%"),
                "仓位占比": st.column_config.NumberColumn(format="%.2f%%"),
            },
        )
    st.markdown("</div>", unsafe_allow_html=True)


def page_fund_analysis(catalog: pd.DataFrame) -> None:
    render_hero()
    left, main, right = st.columns([0.78, 1.72, 0.92])
    with left:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        section_title("模块选择")
        module_l1 = st.selectbox("一级模块", ["全部"] + list(MODULE_TAXONOMY.keys()))
        if module_l1 == "全部":
            sub_options = ["全部"]
            subset = catalog.copy()
        else:
            sub_options = ["全部"] + MODULE_TAXONOMY.get(module_l1, [])
            subset = catalog[catalog["module_level_1"] == module_l1].copy()
        module_l2 = st.selectbox("二级模块", sub_options)
        if module_l2 != "全部":
            subset = subset[subset["module_level_2"] == module_l2]
        search = st.text_input("搜索基金", placeholder="例如 515030 / 半导体 / 黄金")
        if search:
            subset = search_funds(search, catalog, limit=50)
        if subset.empty:
            st.caption("当前筛选无结果，可以直接输入 6 位代码自查。")
        else:
            options = [f"{r.fund_name} | {r.fund_code} | {r.module_level_2}" for r in subset.itertuples()]
            selected_label = st.selectbox("基金池", options)
            selected_code = selected_label.split("|")[1].strip()
            if st.button("设为当前分析", use_container_width=True):
                st.session_state["selected_fund"] = selected_code
                rerun_app()
        custom_code = st.text_input("6位代码自查", placeholder="任意基金/ETF代码")
        if st.button("自查该基金", use_container_width=True, disabled=not bool(custom_code)):
            st.session_state["selected_fund"] = normalize_code(custom_code)
            rerun_app()
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="panel">', unsafe_allow_html=True)
        section_title("模块体系")
        for module, subs in MODULE_TAXONOMY.items():
            with st.expander(module, expanded=False):
                st.caption(" / ".join(subs))
        st.markdown("</div>", unsafe_allow_html=True)

    code = st.session_state.get("selected_fund", "515030")
    hist, snap = analyze_fund(code, catalog)
    pos_df = portfolio_positions(catalog)
    position_hit = pos_df[pos_df["基金代码"] == snap.fund_code]
    position = position_hit.iloc[0] if not position_hit.empty else None

    with main:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        section_title(f"{snap.fund_name} · {snap.fund_code}", f"{snap.module_level_1} / {snap.module_level_2} / {snap.source}")
        latest_dt = pd.to_datetime(hist.iloc[-1]["date"], errors="coerce")
        latest_text = latest_dt.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(latest_dt) else "待更新"
        realtime_badge = "实时快照" if "实时行情" in snap.source else "日线/兜底"
        st.markdown(
            f"""
            <div class="realtime-strip">
                <span>{realtime_badge}</span>
                <span>最新时间：{latest_text}</span>
                <span>刷新频率：{st.session_state.get('refresh_frequency', '手动刷新')}</span>
                <span>数据源：{snap.source}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            render_metric_card("当前价格/净值", fmt_num(snap.close), fmt_pct(snap.pct_change), "green" if snap.pct_change >= 0 else "red")
        with k2:
            render_metric_card("成交额", fmt_money(snap.amount), f"量能 {snap.volume_ratio:.2f}x", "info")
        with k3:
            render_metric_card("趋势评分", f"{snap.trend_score}/5", snap.trend_label, "purple")
        with k4:
            tone = "red" if snap.risk_label == "短期过热" else "yellow" if snap.risk_label in {"略偏高", "回调区"} else "green"
            render_metric_card("风险状态", snap.risk_label, snap.action_label, tone)
        render_plotly_chart(make_price_chart(hist.tail(180), f"{snap.fund_name} 三层专业图表"), "fund_price_chart", fullscreen_height=920)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="panel">', unsafe_allow_html=True)
        section_title("信号明细表", "最近 20 个交易日")
        detail = hist.tail(20)[
            [
                "date",
                "close",
                "pct_change",
                "ma5",
                "ma20",
                "ma60",
                "volume_ratio",
                "money_signal",
                "trend_score",
                "risk_label",
                "action_label",
            ]
        ].copy()
        detail["date"] = detail["date"].dt.strftime("%Y-%m-%d")
        st.dataframe(
            detail.rename(
                columns={
                    "date": "日期",
                    "close": "价格/净值",
                    "pct_change": "涨跌幅",
                    "ma5": "MA5",
                    "ma20": "MA20",
                    "ma60": "MA60",
                    "volume_ratio": "量能倍率",
                    "money_signal": "资金信号",
                    "trend_score": "趋势评分",
                    "risk_label": "风险状态",
                    "action_label": "操作提示",
                }
            ),
            use_container_width=True,
            hide_index=True,
            column_config={
                "涨跌幅": st.column_config.NumberColumn(format="%.2f%%"),
                "量能倍率": st.column_config.NumberColumn(format="%.2fx"),
            },
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        section_title("AI专业解读", "规则模型生成，适合投研复盘")
        st.markdown(generate_fund_interpretation(snap, hist, position))
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="panel">', unsafe_allow_html=True)
        section_title("策略标签")
        tone = "low" if snap.action_label == "适合继续持有" else "mid" if snap.action_label in {"不宜追高", "进入止盈观察区", "等待回踩确认"} else "high"
        st.markdown(badge(snap.action_label, tone), unsafe_allow_html=True)
        st.markdown(badge(snap.money_signal, "low" if "流入" in snap.money_signal else "high" if "撤出" in snap.money_signal else "mid"), unsafe_allow_html=True)
        st.markdown(badge(snap.trend_label, "low" if snap.trend_score >= 4 else "mid" if snap.trend_score == 3 else "high"), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="panel">', unsafe_allow_html=True)
        section_title("快捷操作")
        if st.button("加入观察池", use_container_width=True):
            watch = set(st.session_state.get("watchlist", []))
            watch.add(snap.fund_code)
            st.session_state["watchlist"] = list(watch)
            st.success("已加入观察池")
        if st.button("加入实仓", use_container_width=True):
            new_row = pd.DataFrame(
                [
                    {
                        "fund_code": snap.fund_code,
                        "fund_name": snap.fund_name,
                        "shares": 0.0,
                        "cost_price": snap.close,
                        "buy_date": date.today().strftime("%Y-%m-%d"),
                        "account_type": "待录入",
                        "notes": "从基金分析页添加",
                    }
                ]
            )
            st.session_state["positions"] = pd.concat([st.session_state["positions"], new_row], ignore_index=True)
            st.success("已加入实仓草稿，可到实仓管理页补充份额")
        module_name = st.text_input("加入自定义模块", placeholder="例如 准备止盈")
        if st.button("保存到自定义模块", use_container_width=True, disabled=not bool(module_name)):
            add_custom_module(module_name, snap.fund_code, snap.fund_name)
            st.success("已加入自定义模块")
        st.markdown("</div>", unsafe_allow_html=True)


def add_custom_module(module_name: str, code: str, fund_name: str = "") -> None:
    custom = st.session_state.get("custom_modules", pd.DataFrame()).copy()
    row = {
        "module_id": f"custom_{int(time.time() * 1000)}",
        "module_name": module_name.strip(),
        "fund_code": normalize_code(code),
        "fund_name": fund_name,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    custom = pd.concat([custom, pd.DataFrame([row])], ignore_index=True)
    custom = custom.drop_duplicates(["module_name", "fund_code"], keep="last")
    st.session_state["custom_modules"] = custom


def page_positions(catalog: pd.DataFrame) -> None:
    render_hero()
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    section_title("实仓导入", "支持 Excel / CSV、手动录入与模板下载")
    up1, up2, up3 = st.columns([1.1, 1, 1])
    with up1:
        uploaded = st.file_uploader("上传实仓文件", type=["csv", "xlsx", "xls"])
        if uploaded is not None:
            try:
                if uploaded.name.lower().endswith(".csv"):
                    raw = pd.read_csv(uploaded)
                else:
                    raw = pd.read_excel(uploaded)
                parsed = standardize_positions(raw)
                if parsed.empty:
                    st.warning("没有识别到有效的 6 位基金代码。")
                else:
                    st.session_state["positions"] = parsed
                    st.success(f"已导入 {len(parsed)} 条持仓")
            except Exception as exc:
                st.error(f"导入失败: {exc}")
    with up2:
        st.download_button(
            "下载标准模板",
            data=POSITION_TEMPLATE.encode("utf-8-sig"),
            file_name="fund_position_template.csv",
            mime="text/csv",
            use_container_width=True,
        )
        if st.button("恢复演示实仓", use_container_width=True):
            st.session_state["positions"] = DEFAULT_POSITIONS.copy()
            rerun_app()
    with up3:
        if st.button("清空实仓", use_container_width=True):
            st.session_state["positions"] = pd.DataFrame(columns=DEFAULT_POSITIONS.columns)
            rerun_app()
        st.caption("字段可自动识别: 代码、基金代码、ETF代码、成本、份额、市值、买入日期等。")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    section_title("手动录入 / 编辑")
    editable = st.session_state.get("positions", DEFAULT_POSITIONS).copy()
    editable = standardize_positions(editable) if not editable.empty else DEFAULT_POSITIONS.head(0).copy()
    edited = st.data_editor(
        editable,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "fund_code": st.column_config.TextColumn("基金代码", help="6 位代码"),
            "fund_name": st.column_config.TextColumn("基金名称"),
            "shares": st.column_config.NumberColumn("持有份额", min_value=0.0, step=100.0),
            "cost_price": st.column_config.NumberColumn("持仓成本", min_value=0.0, step=0.001, format="%.4f"),
            "buy_date": st.column_config.TextColumn("买入日期"),
            "account_type": st.column_config.TextColumn("账户类型"),
            "notes": st.column_config.TextColumn("备注"),
        },
    )
    if st.button("保存实仓", use_container_width=True):
        st.session_state["positions"] = standardize_positions(edited)
        st.success("实仓已保存")
    st.markdown("</div>", unsafe_allow_html=True)

    pos_df = portfolio_positions(catalog)
    summary = portfolio_summary(pos_df)
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        render_metric_card("总市值", fmt_money(summary["total_value"]), "", "info")
    with c2:
        render_metric_card("总投入", fmt_money(summary["total_cost"]), "", "purple")
    with c3:
        render_metric_card("总浮盈", fmt_money(summary["total_pnl"]), fmt_pct(summary["total_ret"]), "green" if summary["total_pnl"] >= 0 else "red")
    with c4:
        render_metric_card("今日盈亏", fmt_money(summary["today_pnl"]), "", "green" if summary["today_pnl"] >= 0 else "red")
    with c5:
        render_metric_card("最大单只仓位", f"{summary['max_fund_weight']:.1f}%", "", "yellow")
    with c6:
        render_metric_card("风险评分", f"{summary['risk_score']:.0f}", summary["risk_level"], "red" if summary["risk_level"] == "高" else "yellow")

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    section_title("持仓表", "结合当前行情、趋势、资金与操作提示")
    if pos_df.empty:
        st.info("暂无实仓数据。")
    else:
        show = pos_df[
            [
                "基金代码",
                "基金名称",
                "模块",
                "持仓份额",
                "成本价",
                "当前价",
                "持仓金额",
                "浮盈亏",
                "收益率",
                "仓位占比",
                "趋势状态",
                "资金信号",
                "操作提示",
            ]
        ].copy()
        st.dataframe(
            show,
            use_container_width=True,
            hide_index=True,
            column_config={
                "持仓份额": st.column_config.NumberColumn(format="%.2f"),
                "成本价": st.column_config.NumberColumn(format="%.4f"),
                "当前价": st.column_config.NumberColumn(format="%.4f"),
                "持仓金额": st.column_config.NumberColumn(format="￥%.2f"),
                "浮盈亏": st.column_config.NumberColumn(format="￥%.2f"),
                "收益率": st.column_config.NumberColumn(format="%.2f%%"),
                "仓位占比": st.column_config.NumberColumn(format="%.2f%%"),
            },
        )
    st.markdown("</div>", unsafe_allow_html=True)

    g1, g2, g3 = st.columns(3)
    pie, bar, risk = make_structure_charts(pos_df)
    with g1:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        section_title("模块仓位")
        render_plotly_chart(pie, "position_module_pie", fullscreen_height=820)
        st.markdown("</div>", unsafe_allow_html=True)
    with g2:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        section_title("行业集中度")
        render_plotly_chart(bar, "position_concentration_bar", fullscreen_height=820)
        st.markdown("</div>", unsafe_allow_html=True)
    with g3:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        section_title("风险分布")
        render_plotly_chart(risk, "position_risk_bar", fullscreen_height=820)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    section_title("组合诊断", "理财师式提示")
    for note in generate_portfolio_diagnosis(pos_df, summary):
        st.markdown(f'<div class="signal-card">{note}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def page_module_market(catalog: pd.DataFrame) -> None:
    render_hero()
    top = st.columns([1, 1, 1, 1])
    with top[0]:
        module_l1 = st.selectbox("一级模块", list(MODULE_TAXONOMY.keys()), key="pool_l1")
    with top[1]:
        module_l2 = st.selectbox("二级模块", ["全部"] + MODULE_TAXONOMY.get(module_l1, []), key="pool_l2")
    with top[2]:
        sort_by = st.selectbox("排序", ["今日涨跌幅", "成交额", "趋势评分", "资金信号", "风险状态"], key="pool_sort")
    with top[3]:
        filter_by = st.selectbox("筛选", ["全部", "只看强流入", "只看短期过热", "只看回调区", "只看趋势评分4分以上", "只看缩量观望"], key="pool_filter")

    subset = catalog[catalog["module_level_1"] == module_l1].copy()
    if module_l2 != "全部":
        subset = subset[subset["module_level_2"] == module_l2]
    pool_df = build_pool_snapshot(catalog, subset["fund_code"], limit=80)
    if not pool_df.empty:
        if filter_by == "只看强流入":
            pool_df = pool_df[pool_df["资金信号"] == "强流入"]
        elif filter_by == "只看短期过热":
            pool_df = pool_df[pool_df["风险状态"] == "短期过热"]
        elif filter_by == "只看回调区":
            pool_df = pool_df[pool_df["风险状态"].isin(["回调区", "深度回调"])]
        elif filter_by == "只看趋势评分4分以上":
            pool_df = pool_df[pool_df["趋势评分"] >= 4]
        elif filter_by == "只看缩量观望":
            pool_df = pool_df[pool_df["资金信号"] == "缩量观望"]
        ascending = sort_by in {"风险状态"}
        if sort_by in pool_df.columns:
            pool_df = pool_df.sort_values(sort_by, ascending=ascending)

    left, right = st.columns([1.32, 1])
    with left:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        section_title("模块行情池", f"{module_l1} / {module_l2}")
        if pool_df.empty:
            st.info("当前模块暂无基金样本。可以在自定义搜索页添加基金到模块。")
        else:
            st.dataframe(
                pool_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "当前价格": st.column_config.NumberColumn(format="%.4f"),
                    "今日涨跌幅": st.column_config.NumberColumn(format="%.2f%%"),
                    "成交额": st.column_config.NumberColumn(format="￥%.2f"),
                    "量能倍率": st.column_config.NumberColumn(format="%.2fx"),
                },
            )
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        section_title("强弱热力图")
        render_plotly_chart(make_module_heatmap(pool_df), "pool_module_heatmap", fullscreen_height=860)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="panel">', unsafe_allow_html=True)
        section_title("资金信号分布")
        if pool_df.empty:
            st.caption("暂无数据")
        else:
            signal_df = pool_df["资金信号"].value_counts().reset_index()
            signal_df.columns = ["资金信号", "数量"]
            fig = px.bar(signal_df, x="资金信号", y="数量", template=PLOTLY_TEMPLATE, color="资金信号")
            fig.update_layout(height=270, margin=dict(l=10, r=10, t=20, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(12,26,46,0.92)", showlegend=False)
            render_plotly_chart(fig, "pool_money_signal_bar", fullscreen_height=760)
        st.markdown("</div>", unsafe_allow_html=True)


def render_search_result(row: pd.Series, catalog: pd.DataFrame, index: int) -> None:
    code = row["fund_code"]
    try:
        _, snap = analyze_fund(code, catalog)
    except Exception:
        snap = FundSnapshot(
            fund_code=code,
            fund_name=row["fund_name"],
            module_level_1=row.get("module_level_1", "用户自查"),
            module_level_2=row.get("module_level_2", "未归类"),
            close=np.nan,
            pct_change=0,
            amount=0,
            volume_ratio=1,
            trend_score=0,
            trend_label="待观察",
            money_signal="中性",
            risk_label="待观察",
            action_label="继续观察",
            ma20_deviation=0,
            source="待获取",
        )
    st.markdown(
        f"""
        <div class="result-card">
            <strong>{snap.fund_name}</strong>
            <span class="small-muted"> · {snap.fund_code} · {snap.module_level_1}/{snap.module_level_2}</span><br>
            {badge('涨跌 ' + fmt_pct(snap.pct_change), 'low' if snap.pct_change >= 0 else 'high')}
            {badge('成交额 ' + fmt_money(snap.amount), 'info')}
            {badge(snap.trend_label, 'low' if snap.trend_score >= 4 else 'mid' if snap.trend_score == 3 else 'high')}
            {badge(snap.money_signal, 'low' if '流入' in snap.money_signal else 'high' if '撤出' in snap.money_signal else 'mid')}
            {badge(snap.risk_label, 'high' if snap.risk_label == '短期过热' else 'mid' if snap.risk_label in {'略偏高', '回调区'} else 'low')}
        </div>
        """,
        unsafe_allow_html=True,
    )
    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("加入观察池", key=f"watch_{code}_{index}", use_container_width=True):
            watch = set(st.session_state.get("watchlist", []))
            watch.add(code)
            st.session_state["watchlist"] = list(watch)
            st.success("已加入观察池")
    with b2:
        if st.button("加入实仓", key=f"pos_{code}_{index}", use_container_width=True):
            new_row = pd.DataFrame(
                [
                    {
                        "fund_code": code,
                        "fund_name": snap.fund_name,
                        "shares": 0.0,
                        "cost_price": snap.close if pd.notna(snap.close) else 0.0,
                        "buy_date": date.today().strftime("%Y-%m-%d"),
                        "account_type": "待录入",
                        "notes": "从搜索页添加",
                    }
                ]
            )
            st.session_state["positions"] = pd.concat([st.session_state["positions"], new_row], ignore_index=True)
            st.success("已加入实仓草稿")
    with b3:
        if st.button("查看详情", key=f"detail_{code}_{index}", use_container_width=True):
            st.session_state["selected_fund"] = code
            st.session_state["nav"] = "基金分析"
            rerun_app()


def page_custom_search(catalog: pd.DataFrame) -> None:
    render_hero()
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    section_title("自定义基金搜索", "支持代码、名称、关键词、模块名称与任意 6 位代码自查")
    query = st.text_input("搜索", placeholder="515030 / 新能源 / 半导体 / 黄金 / 煤炭 / 恒生")
    results = search_funds(query, catalog, limit=20) if query else catalog.head(12)
    st.caption("当系统模块没有该基金时，可直接输入任意 6 位代码，系统会自动判断市场并尝试生成分析图表。")
    st.markdown("</div>", unsafe_allow_html=True)

    left, right = st.columns([1.35, 0.9])
    with left:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        section_title("搜索结果")
        if results.empty:
            st.info("暂无匹配结果。")
        else:
            for idx, row in results.iterrows():
                render_search_result(row, catalog, int(idx))
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        section_title("用户自定义模块")
        module_name = st.text_input("模块名称", placeholder="我的长期持仓 / 准备止盈 / 高波动赛道")
        fund_code = st.text_input("基金代码", placeholder="6 位代码")
        fund_name = st.text_input("基金名称", placeholder="可留空自动识别")
        if st.button("添加到模块", use_container_width=True, disabled=not (module_name and fund_code)):
            add_custom_module(module_name, fund_code, fund_name)
            st.success("已添加")
            rerun_app()
        custom = st.session_state.get("custom_modules", pd.DataFrame())
        if custom.empty:
            st.caption("暂无自定义模块。")
        else:
            st.dataframe(custom[["module_name", "fund_code", "fund_name", "created_at"]], use_container_width=True, hide_index=True)
            if st.button("清空自定义模块", use_container_width=True):
                st.session_state["custom_modules"] = custom.head(0)
                rerun_app()
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="panel">', unsafe_allow_html=True)
        section_title("观察池")
        watch = st.session_state.get("watchlist", [])
        if not watch:
            st.caption("暂无观察基金。")
        else:
            rows = []
            for code in watch:
                try:
                    rows.append(snapshot_row(code, catalog))
                except Exception:
                    continue
            if rows:
                watch_df = pd.DataFrame(rows)
                st.dataframe(
                    watch_df[["基金名称", "基金代码", "今日涨跌幅", "趋势评分", "资金信号", "风险状态"]],
                    use_container_width=True,
                    hide_index=True,
                    column_config={"今日涨跌幅": st.column_config.NumberColumn(format="%.2f%%")},
                )
        st.markdown("</div>", unsafe_allow_html=True)


def page_settings(catalog: pd.DataFrame) -> None:
    render_hero()
    left, right = st.columns([1, 1])
    with left:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        section_title("数据源设置")
        st.selectbox(
            "行情模式",
            DATA_MODE_OPTIONS,
            key="data_mode",
        )
        st.selectbox("刷新频率", REFRESH_OPTIONS, key="refresh_frequency")
        st.caption("场内 ETF/LOF 会优先读取东方财富实时快照，并以 15 秒缓存刷新；接口不可用时自动回退到日线或演示行情。")
        if st.button("清理缓存并刷新", use_container_width=True):
            st.cache_data.clear()
            st.session_state["last_refresh_ts"] = time.time()
            st.success("缓存已清理")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="panel">', unsafe_allow_html=True)
        section_title("基金基础表")
        st.dataframe(
            catalog[["fund_code", "fund_name", "module_level_1", "module_level_2", "market", "asset_type", "risk_level"]],
            use_container_width=True,
            hide_index=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        section_title("实仓数据管理")
        positions = st.session_state.get("positions", pd.DataFrame())
        if positions.empty:
            st.caption("暂无实仓数据。")
        else:
            csv = standardize_positions(positions).to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "导出实仓 CSV",
                data=csv,
                file_name=f"fundpilot_positions_{date.today().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        pos_df = portfolio_positions(catalog)
        summary = portfolio_summary(pos_df)
        diagnosis = "\n".join(generate_portfolio_diagnosis(pos_df, summary))
        report = io.StringIO()
        report.write("FundPilot Pro 组合诊断报告\n")
        report.write(f"生成日期,{date.today().strftime('%Y-%m-%d')}\n")
        report.write(f"总市值,{summary['total_value']:.2f}\n")
        report.write(f"总浮盈,{summary['total_pnl']:.2f}\n")
        report.write(f"收益率,{summary['total_ret']:.2f}%\n")
        report.write(f"风险等级,{summary['risk_level']}\n")
        report.write("\n组合诊断\n")
        report.write(diagnosis)
        st.download_button(
            "导出诊断报告",
            data=report.getvalue().encode("utf-8-sig"),
            file_name=f"fundpilot_report_{date.today().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="panel">', unsafe_allow_html=True)
        section_title("数据结构")
        st.markdown(
            """
            <div class="terminal-line">fund_base: fund_code, fund_name, module_level_1, module_level_2, market, asset_type, risk_level</div>
            <div class="terminal-line">market_data: date, fund_code, open, close, high, low, volume, amount, pct_change</div>
            <div class="terminal-line">indicator: ma5, ma20, ma60, amount_ma20, volume_ratio, obv, money_signal, trend_score, risk_label</div>
            <div class="terminal-line">position: position_id, fund_code, shares, cost_price, buy_date, account_type, notes</div>
            <div class="terminal-line">custom_module: module_id, module_name, fund_code, fund_name, created_at</div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)


def main() -> None:
    apply_page_config()
    inject_css()
    init_state()
    catalog = build_catalog()
    nav = render_sidebar(catalog)
    schedule_auto_refresh()
    if nav == "首页驾驶舱":
        page_dashboard(catalog)
    elif nav == "基金分析":
        page_fund_analysis(catalog)
    elif nav == "实仓管理":
        page_positions(catalog)
    elif nav == "模块行情":
        page_module_market(catalog)
    elif nav == "自定义搜索":
        page_custom_search(catalog)
    elif nav == "设置中心":
        page_settings(catalog)


if __name__ == "__main__":
    main()
