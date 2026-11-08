"""
Кастомные фильтры для админки (пункт 9).
"""
from django.contrib.admin import SimpleListFilter
from django.utils.translation import gettext_lazy as _


class StockAvailabilityFilter(SimpleListFilter):
    """Фильтр товаров по наличию на складе."""
    title = _('Наличие на складе')
    parameter_name = 'stock_availability'

    def lookups(self, request, model_admin):
        return (
            ('in_stock', _('В наличии')),
            ('out_of_stock', _('Нет в наличии')),
            ('low', _('Мало (≤ 5)')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'in_stock':
            return queryset.filter(stock__gt=0)
        if self.value() == 'out_of_stock':
            return queryset.filter(stock=0)
        if self.value() == 'low':
            return queryset.filter(stock__lte=5, stock__gt=0)
        return queryset


class OrderStatusFilter(SimpleListFilter):
    """Фильтр заказов по статусу (с группировкой)."""
    title = _('Статус (расширенный)')
    parameter_name = 'order_status'

    def lookups(self, request, model_admin):
        return (
            ('active', _('Активные (не отменённые)')),
            ('paid_or_shipped', _('Оплачен / Отправлен')),
            ('cancelled', _('Отменённые')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'active':
            return queryset.exclude(status='cancelled')
        if self.value() == 'paid_or_shipped':
            return queryset.filter(status__in=['paid', 'shipped'])
        if self.value() == 'cancelled':
            return queryset.filter(status='cancelled')
        return queryset


class TotalSumFilter(SimpleListFilter):
    """Фильтр заказов по сумме (пример кастомного фильтра)."""
    title = _('Сумма заказа')
    parameter_name = 'total_sum'

    def lookups(self, request, model_admin):
        return (
            ('small', _('До 1000')),
            ('medium', _('1000 – 5000')),
            ('large', _('Свыше 5000')),
        )

    def queryset(self, request, queryset):
        from django.db.models import F, Sum

        annotated = queryset.annotate(
            _total=Sum(F('items__price') * F('items__quantity'))
        )
        if self.value() == 'small':
            return annotated.filter(_total__lt=1000)
        if self.value() == 'medium':
            return annotated.filter(_total__gte=1000, _total__lte=5000)
        if self.value() == 'large':
            return annotated.filter(_total__gt=5000)
        return queryset