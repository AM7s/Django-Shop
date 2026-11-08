"""
Демонстрационные представления (не обязательны для ДЗ,
но удобны для проверки оформления заказа).
"""
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from shop.models import Order


@require_POST
def checkout_view(request):
    """
    Простейший демонстрационный checkout.
    Ожидает POST-параметры:
      customer_name, customer_email, cart (JSON-строка)
    """
    import json

    try:
        cart = json.loads(request.POST.get('cart', '[]'))
        order = Order.create_with_items(
            customer_name=request.POST.get('customer_name', 'Гость'),
            customer_email=request.POST.get('customer_email', 'guest@example.com'),
            cart_items=cart,
        )
    except Exception as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=400)

    return JsonResponse({
        'ok': True,
        'order_id': order.pk,
        'total': str(order.total_sum),
    })