"""
Отдельный AdminSite для магазина (пункт 7).
"""
from django.contrib.admin import AdminSite


class ShopAdminSite(AdminSite):
    site_header = 'Управление магазином'
    site_title = 'Магазин · Админка'
    index_title = 'Панель управления магазином'

    # Дополнительные атрибуты оформления
    site_url = '/'


shop_admin_site = ShopAdminSite(name='shop_admin')