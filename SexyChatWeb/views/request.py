import json
import os
from django.shortcuts import render
from django.http import JsonResponse


# 母版
def template(request):
    return render(request, 'template.html')


# 首页
def index(request):
    return render(request, '页面/首页/index.html')


# ============================================================
# 商品卡片 API（JSON 文件驱动，按国家过滤）
# 前端调用：GET /api/cards/<country>/?page=1&count=20
# 返回结构匹配前端 SexyChatCardList 期望的 item 字段：
#   id / imageUrl / watermark / district / province / title /
#   likes / favorites / views / price / link
# 数据来源：SexyChatWeb/data/{国家代码}.json
#   新增国家只需在该目录下创建对应 JSON 文件即可。
#   JSON 格式为顶层数组，每项为卡片对象，详见已有示例文件。
# ============================================================

# 数据文件目录
_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

# 单次请求允许的最大 count（防滥用）
_MAX_COUNT_PER_PAGE = 50

# 内存缓存：_load_country_items 读取一次后缓存，避免每次请求都读磁盘
_cache = {}


def _get_supported_countries():
    """扫描 data 目录获取支持的国家列表

    返回：按文件名（不含后缀）排序的国家代码列表
    """
    supported = []
    if not os.path.isdir(_DATA_DIR):
        return supported
    for fname in os.listdir(_DATA_DIR):
        if fname.endswith(".json"):
            code = fname[:-5].upper()
            if code:
                supported.append(code)
    return sorted(supported)


def _load_country_items(country):
    """从 JSON 文件加载指定国家的全部卡片数据

    读取一次后缓存到 _cache，避免重复磁盘 I/O。
    若文件不存在或解析失败，返回空列表。
    """
    country_upper = country.upper()
    if country_upper in _cache:
        return _cache[country_upper]

    filepath = os.path.join(_DATA_DIR, f"{country_upper}.json")
    if not os.path.isfile(filepath):
        return []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            items = json.load(f)
        if not isinstance(items, list):
            items = []
        _cache[country_upper] = items
        return items
    except (json.JSONDecodeError, IOError):
        return []


def _parse_positive_int(value, default, max_value=None):
    """解析查询参数为正整数，非法时回退到默认值"""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    if n < 1:
        return default
    if max_value is not None:
        n = min(n, max_value)
    return n


def product_cards_api(request, country):
    """商品卡片 API：按国家从 JSON 文件读取分页数据

    URL: GET /api/cards/<country>/?page=1&count=20&style=loli
    可选参数 style：按风格过滤（loli/queen/hot/pure），不传则返回全部
    响应结构：
        {
            "country": "CN",
            "page": 1, "count": 20, "total": 80, "hasMore": true,
            "items": [{ id, imageUrl, watermark, district, province, style,
                        title, likes, favorites, views, price, link }, ...]
        }
    国家不支持时返回 400 + 支持列表
    """
    country = (country or "").upper()
    supported = _get_supported_countries()
    if country not in supported:
        return JsonResponse({
            "error": "unsupported country: " + country,
            "supported": supported,
        }, status=400)

    page = _parse_positive_int(request.GET.get("page"), default=1)
    count = _parse_positive_int(
        request.GET.get("count"), default=20, max_value=_MAX_COUNT_PER_PAGE
    )
    style_filter = (request.GET.get("style") or "").strip().lower()

    all_items = _load_country_items(country)

    # 按风格过滤
    if style_filter:
        filtered = [item for item in all_items if item.get("style") == style_filter]
    else:
        filtered = all_items

    total = len(filtered)

    base = (page - 1) * count
    items = filtered[base:base + count]
    has_more = (base + count) < total

    return JsonResponse({
        "country": country,
        "page": page,
        "count": len(items),
        "total": total,
        "hasMore": has_more,
        "items": items,
    })
