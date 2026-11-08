"""
Сигналы: удаление файлов при удалении товара/изображения (пункт 3).
"""
import logging

from django.db.models.signals import pre_save, post_delete
from django.dispatch import receiver

from shop.models import ProductImage

logger = logging.getLogger('shop.admin')


def _delete_file(field_file):
    """Безопасное удаление файла из хранилища."""
    if not field_file:
        return
    storage = field_file.storage
    name = field_file.name
    if name and storage.exists(name):
        storage.delete(name)


# --- Замена файла: удаляем старый перед сохранением нового ---
@receiver(pre_save, sender=ProductImage)
def delete_old_files_on_update(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    if old.image and old.image.name != instance.image.name:
        logger.info('Замена основного файла: %s', old.image.name)
        _delete_file(old.image)

    if old.thumbnail and old.thumbnail.name != instance.thumbnail.name:
        _delete_file(old.thumbnail)


# --- Удаление записи: удаляем связанные файлы ---
@receiver(post_delete, sender=ProductImage)
def delete_files_on_delete(sender, instance, **kwargs):
    logger.info('Удаление файлов изображения #%s', instance.pk)
    _delete_file(instance.image)
    _delete_file(instance.thumbnail)