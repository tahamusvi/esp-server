from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from django.core.cache import cache
from .behaviors import flashcall , send_bale_message,send_telegram_message

