import os

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import F, Sum
from PIL import Image


# ============================================================
# Товар (пункты 1, 2)
# ============================================================
class Product(models.Model):
    name = models.CharField('Название', max_length=200)
    slug = models.SlugField('Слаг', max_length=200, unique=True)
    description = models.TextField('Описание', blank=True)
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField('Остаток', default=0)
    is_active = models.BooleanField('Активен', default=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлён', auto_now=True)

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ('-created_at',)

    def __str__(self):
        return self.name


# ============================================================
# Изображения товара (пункты 1, 2, 3)
# ============================================================
class ProductImage(models.Model):
    THUMBNAIL_SIZE = (300, 300)

    product = models.ForeignKey(
        Product,
        related_name='images',
        on_delete=models.CASCADE,
        verbose_name='Товар',
    )
    image = models.ImageField('Изображение', upload_to='products/%Y/%m/')
    thumbnail = models.ImageField(
        'Превью',
        upload_to='products/thumbs/%Y/%m/',
        blank=True,
        editable=False,
    )
    is_main = models.BooleanField('Главное', default=False)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Изображение товара'
        verbose_name_plural = 'Изображения товаров'
        ordering = ('-is_main', 'created_at')

    def __str__(self):
        return f'Изображение для {self.product.name}'

    # --- Пункт 1: автоматическое изменение размера и сохранение превью ---
    def save(self, *args, **kwargs):
        # Если изображение новое — генерируем превью
        if not self.pk or (self.pk and self.__class__.objects.get(pk=self.pk).image != self.image):
            super().save(*args, **kwargs)
            self._generate_thumbnail()
            # Сохраняем только поле thumbnail без вызова save()
            super().save(update_fields=['thumbnail'] if self.thumbnail else None)
        else:
            super().save(*args, **kwargs)

    def _generate_thumbnail(self):
        """Создаёт превью и перезаписывает оригинал при превышении размера."""
        if not self.image:
            return
        try:
            img = Image.open(self.image)
            img = img.convert('RGB')

            # Уменьшение оригинала, если оно больше 1920px по длинной стороне
            if max(img.size) > 1920:
                img.thumbnail((1920, 1920))
                self.image.save(
                    os.path.basename(self.image.name),
                    self._img_to_content(img),
                    save=False,
                )
                img = Image.open(self.image)

            # Генерация превью
            thumb = img.copy()
            thumb.thumbnail(self.THUMBNAIL_SIZE)
            self.thumbnail.save(
                f'thumb_{os.path.basename(self.image.name)}',
                self._img_to_content(thumb),
                save=False,
            )
        except Exception as exc:
            raise ValidationError(f'Ошибка обработки изображения: {exc}')

    @staticmethod
    def _img_to_content(img):
        from io import BytesIO
        from django.core.files.base import ContentFile

        buf = BytesIO()
        img.save(buf, format='JPEG', quality=85)
        return ContentFile(buf.getvalue())

    # --- Пункт 3: удаление файлов при удалении записи ---
    def delete(self, *args, **kwargs):
        image_name = self.image.name if self.image else None
        thumb_name = self.thumbnail.name if self.thumbnail else None

        result = super().delete(*args, **kwargs)

        storage = self.image.storage if self.image else None
        if storage:
            if image_name:
                storage.delete(image_name)
            if thumb_name:
                storage.delete(thumb_name)
        return result


# ============================================================
# Заказ и позиции (пункты 5, 6)
# ============================================================
class Order(models.Model):
    STATUS_NEW = 'new'
    STATUS_PAID = 'paid'
    STATUS_SHIPPED = 'shipped'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_NEW, 'Новый'),
        (STATUS_PAID, 'Оплачен'),
        (STATUS_SHIPPED, 'Отправлен'),
        (STATUS_CANCELLED, 'Отменён'),
    ]

    customer_name = models.CharField('Имя покупателя', max_length=200)
    customer_email = models.EmailField('E-mail')
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_NEW,
    )
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлён', auto_now=True)

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ('-created_at',)

    def __str__(self):
        return f'Заказ #{self.pk} от {self.created_at:%d.%m.%Y}'

    # --- Пункт 8: подсчёт общей суммы ---
    @property
    def total_sum(self):
        return self.items.aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0

    # --- Пункт 5: атомарное оформление заказа ---
    @classmethod
    def create_with_items(cls, customer_name, customer_email, cart_items):
        """
        cart_items — список словарей вида:
        [{'product_id': 1, 'quantity': 2}, ...]
        """
        from shop.services import checkout

        return checkout(
            customer_name=customer_name,
            customer_email=customer_email,
            cart_items=cart_items,
        )


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        related_name='items',
        on_delete=models.CASCADE,
        verbose_name='Заказ',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        verbose_name='Товар',
    )
    quantity = models.PositiveIntegerField('Количество')
    price = models.DecimalField('Цена на момент заказа', max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказа'

    def __str__(self):
        return f'{self.product.name} × {self.quantity}'

    @property
    def subtotal(self):
        return self.price * self.quantity