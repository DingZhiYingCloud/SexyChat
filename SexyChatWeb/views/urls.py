# 色站-前端 服务 网站 路由
from django.urls import path, include
from SexyChatWeb.views import request

# 域名前缀: /
urlpatterns = [
    path('template/', request.template),
    # 商品卡片 API（按国家过滤，mock 数据）
    path('api/cards/<str:country>/', request.product_cards_api),
    path('', request.index),
]
