"""
Сервисный слой: атомарное оформление заказа (пункты 5, 6).
"""
import logging

from django.core.exceptions import ValidationError
from django.db import transaction

from shop.models import Order, OrderItem, Product

logger = logging.getLogger('shop.services')


def checkout(customer_name, customer_email, cart_items):
    """
    Атомарное создание заказа со списанием остатков.
    Защита от гонок данных через select_for_update().

    :param cart_items: [{'product_id': int, 'quantity': int}, ...]
    :return: Order
    """
    if not cart_items:
        raise ValidationError('Корзина пуста.')

    # Упорядочиваем по product_id, чтобы избежать deadlock
    # (единый порядок захвата блокировок во всех транзакциях)
    sorted_items = sorted(cart_items, key=lambda x: x['product_id'])

    with transaction.atomic():
        order = Order.objects.create(
            customer_name=customer_name,
            customer_email=customer_email,
        )

        for item in sorted_items:
            # Пункт 6: блокировка строки товара до конца транзакции
            try:
                product = (
                    Product.objects
                    .select_for_update()
                    .get(pk=item['product_id'], is_active=True)
                )
            except Product.DoesNotExist:
                raise ValidationError(
                    f"Товар с id={item['product_id']} не найден или недоступен."
                )

            if product.stock < item['quantity']:
                raise ValidationError(
                    f"Недостаточно товара «{product.name}»: "
                    f"на складе {product.stock}, требуется {item['quantity']}."
                )

            # Списание остатков
            product.stock -= item['quantity']
            product.save(update_fields=['stock'])

            # Создание позиции заказа
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item['quantity'],
                price=product.price,
            )

            logger.info(
                'Списано %s ед. товара «%s» (остаток: %s)',
                item['quantity'], product.name, product.stock,
            )

        logger.info(
            'Создан заказ #%s на сумму %s',
            order.pk, order.total_sum,
        )
        return order