import uuid
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True



class IncomingMessage(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Sms Info
    from_number = models.CharField(max_length=32)
    to_number = models.CharField(max_length=32)
    body = models.TextField()
    received_at = models.DateTimeField()

    # MetaData
    raw_payload = models.JSONField(default=dict, blank=True)
    processed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.to_number} <- {self.from_number}"


class DestinationChannel(TimeStampedModel):
    class ChannelType(models.TextChoices):
        SMS = "sms", "SMS"
        TELEGRAM = "telegram", "Telegram"
        WEBHOOK = "webhook", "Webhook"
        EMAIL = "email", "Email"
        Bale = "bale", "Bale"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    type = models.CharField(max_length=32, choices=ChannelType.choices)
    name = models.CharField(max_length=128)
    is_enabled = models.BooleanField(default=True)

    config = models.JSONField(default=dict, blank=True)


    def __str__(self):
        return f"{self.project.slug}:{self.type}:{self.name}"


class ForwardRule(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=128)
    is_enabled = models.BooleanField(default=True)

    filters = models.JSONField(default=dict, blank=True)

    stop_processing = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.project.slug}:Rule:{self.name}"

class RuleDestination(TimeStampedModel):
    rule = models.ForeignKey(
        ForwardRule,
        on_delete=models.CASCADE,
        related_name="actions",
    )
    channel = models.ForeignKey(
        DestinationChannel,
        on_delete=models.CASCADE,
        related_name="actions",
    )

    is_enabled = models.BooleanField(default=True)

    class Meta:
        unique_together = ("rule", "channel")

    def __str__(self):
        return f"{self.rule} -> {self.channel}"



class DeliveryAttempt(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(IncomingMessage, on_delete=models.CASCADE, related_name="deliveries")
    rule = models.ForeignKey(ForwardRule, on_delete=models.SET_NULL, null=True, blank=True)
    channel = models.ForeignKey(DestinationChannel, on_delete=models.CASCADE, related_name="deliveries")

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    provider_message_id = models.CharField(max_length=128, blank=True)
    error = models.TextField(blank=True)

    last_attempt_at = models.DateTimeField(null=True, blank=True)
    retry_count = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.message.id} -> {self.channel} [{self.status}]"
