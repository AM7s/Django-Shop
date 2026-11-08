"""
Админка магазина (пункты 7, 8, 9, 10).
"""
import logging

from django.contrib import admin, messages
from django.contrib.admin import ModelAdmin
from django.db.models import Count, F, Sum
from django.utils.html import format_html
from django.utils.translation import ngettext_lazy

from shop.admin_site import shop_admin_site
from shop.filters import OrderStatusFilter, StockAvailabilityFilter, TotalSumFilter
from shop.models import Order, OrderItem, Product, ProductImage

logger = logging.getLogger('shop.admin')


# ============================================================
# Inline: изображения товара (пункт 2)
# ============================================================
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'thumbnail_preview', 'is_main')
    readonly_fields = ('thumbnail_preview',)

    def thumbnail_preview(self, obj):
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="height:60px;border:1px solid #ccc;" />',
                obj.thumbnail.url,
            )
        return '—'
    thumbnail_preview.short_description = 'Превью'


# ============================================================
# Товары
# ============================================================
class ProductAdmin(ModelAdmin):
    list_display = ('name', 'price', 'stock', 'is_active', 'images_count', 'created_at')
    list_filter = (StockAvailabilityFilter, 'is_active', 'created_at')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = (ProductImageInline,)
    readonly_fields = ('created_at', 'updated_at')

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_images_count=Count('images'))

    @admin.display(description='Изображений', ordering='_images_count')
    def images_count(self, obj):
        return obj._images_count

    # --- Действия (пункт 9) ---
    actions = ('activate_products', 'deactivate_products')

    @admin.action(description='Активировать выбранные товары')
    def activate_products(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            ngettext_lazy(
                'Активирован %d товар.',
                'Активировано %d товаров.',
                updated,
            ) % updated,
            messages.SUCCESS,
        )
        logger.info('Пользователь %s активировал %s товаров', request.user, updated)

    @admin.action(description='Деактивировать выбранные товары')
    def deactivate_products(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            ngettext_lazy(
                'Деактивирован %d товар.',
                'Деактивировано %d товаров.',
                updated,
            ) % updated,
            messages.WARNING,
        )
        logger.info('Пользователь %s деактивировал %s товаров', request.user, updated)


# ============================================================
# Inline: позиции заказа (пункт 8)
# ============================================================
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ('product', 'quantity', 'price', 'subtotal_display')
    readonly_fields = ('subtotal_display',)

    def subtotal_display(self, obj):
        if obj.pk:
            return f'{obj.subtotal:.2f} ₽'
        return '—'
    subtotal_display.short_description = 'Сумма'


# ============================================================
# Заказы (пункты 8, 9, 10)
# ============================================================
class OrderAdmin(ModelAdmin):
    list_display = (
        'id', 'customer_name', 'customer_email',
        'status', 'total_sum_display', 'items_count', 'created_at',
    )
    list_filter = (OrderStatusFilter, 'status', TotalSumFilter, 'created_at')
    search_fields = ('customer_name', 'customer_email', 'id')
    inlines = (OrderItemInline,)
    readonly_fields = ('created_at', 'updated_at', 'total_sum_display')

    # --- Пункт 8: подсчёт общей суммы ---
    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .annotate(
                _total=Sum(F('items__price') * F('items__quantity')),
                _items_count=Count('items'),
            )
        )

    @admin.display(description='Сумма заказа', ordering='_total')
    def total_sum_display(self, obj):
        total = obj._total if hasattr(obj, '_total') else obj.total_sum
        return f'{total or 0:.2f} ₽'

    @admin.display(description='Позиций', ordering='_items_count')
    def items_count(self, obj):
        return obj._items_count

    # --- Пункт 10: массовая смена статуса + логирование ---
    actions = ('mark_as_paid', 'mark_as_shipped', 'mark_as_cancelled')

    def _bulk_status_change(self, request, queryset, new_status, label):
        updated = queryset.update(status=new_status)
        for order in queryset:
            logger.info(
                'Пользователь %s сменил статус заказа #%s на «%s»',
                request.user, order.pk, label,
            )
        self.message_user(
            request,
            ngettext_lazy(
                '%d заказ переведён в статус «%s».',
                '%d заказов переведены в статус «%s».',
                updated,
            ) % (updated, label),
            messages.SUCCESS,
        )

    @admin.action(description='Пометить как «Оплачен»')
    def mark_as_paid(self, request, queryset):
        self._bulk_status_change(request, queryset, Order.STATUS_PAID, 'Оплачен')

    @admin.action(description='Пометить как «Отправлен»')
    def mark_as_shipped(self, request, queryset):
        self._bulk_status_change(request, queryset, Order.STATUS_SHIPPED, 'Отправлен')

    @admin.action(description='Пометить как «Отменён»')
    def mark_as_cancelled(self, request, queryset):
        self._bulk_status_change(request, queryset, Order.STATUS_CANCELLED, 'Отменён')


# ============================================================
# Регистрация в основном и кастомном AdminSite
# ============================================================
admin.site.register(Product, ProductAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(ProductImage)
admin.site.register(OrderItem)

shop_admin_site.register(Product, ProductAdmin)
shop_admin_site.register(Order, OrderAdmin)
shop_admin_site.register(ProductImage)
shop_admin_site.register(OrderItem)

# Кастомизация стандартного заголовка
admin.site.site_header = 'Управление магазином'
admin.site.site_title = 'Магазин · Админка'
admin.site.index_title = 'Панель управления магазином'