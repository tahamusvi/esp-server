from django.contrib import admin

from .models import (
    IncomingMessage,
    DestinationChannel,
    ForwardRule,
    RuleDestination,
    DeliveryAttempt,
    FailedLog,
)


class TimeStampedReadonlyMixin:
    """Adds created_at and updated_at as read-only fields."""
    readonly_fields = ("created_at", "updated_at")


# ======================
# RuleDestination inline (actions of a rule)
# ======================
class RuleDestinationInline(admin.TabularInline):
    model = RuleDestination
    extra = 1
    verbose_name = "Action"
    verbose_name_plural = "Rule actions"
    autocomplete_fields = ("channel",)



# ======================
# DestinationChannel admin
# ======================
@admin.register(DestinationChannel)
class DestinationChannelAdmin(TimeStampedReadonlyMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "type",
        "is_enabled",
        "created_at",
    )
    list_filter = ("type", "is_enabled")
    search_fields = ("name",)
    ordering = ( "type", "name")

    fieldsets = (
        ("Basic info", {
            "fields": (
                "name",
                "type",
                "is_enabled",
            ),
        }),
        ("Configuration", {
            "fields": ("config",),
            "description": "Channel-specific configuration (Telegram bot token, webhook URL, etc.).",
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )


# ======================
# ForwardRule admin
# ======================
@admin.register(ForwardRule)
class ForwardRuleAdmin(TimeStampedReadonlyMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "is_enabled",
        "stop_processing",
        "created_at",
    )
    list_filter = ( "is_enabled", "stop_processing")
    search_fields = ("name", "filters")
    ordering = ("name",)
    inlines = (RuleDestinationInline,)

    fieldsets = (
        ("Basic info", {
            "fields": (
                "name",
                "is_enabled",
                "stop_processing",
            ),
        }),
        ("Scope & filters", {
            "fields": ("filters",),
            "description": "JSON filters to match incoming messages. Empty means match-all.",
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )


# ======================
# IncomingMessage admin
# ======================
@admin.register(IncomingMessage)
class IncomingMessageAdmin(TimeStampedReadonlyMixin, admin.ModelAdmin):
    list_display = (
        "from_number",
        "to_number",
        "processed",
        "received_at",
        "created_at",
    )
    list_filter = ("processed",)
    search_fields = ("from_number", "to_number", "body")
    date_hierarchy = "received_at"
    ordering = ("-received_at",)

    readonly_fields = TimeStampedReadonlyMixin.readonly_fields + ("raw_payload",)

    fieldsets = (
        ("Message", {
            "fields": (
                "from_number",
                "to_number",
                "body",
                "received_at",
                "processed",
            ),
        }),
        ("Raw payload", {
            "fields": ("raw_payload",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )


# ======================
# DeliveryAttempt admin
# ======================
@admin.register(DeliveryAttempt)
class DeliveryAttemptAdmin(TimeStampedReadonlyMixin, admin.ModelAdmin):
    list_display = (
        "message",
        "channel",
        "rule",
        "status",
        "retry_count",
        "last_attempt_at",
        "created_at",
    )
    list_filter = ("status", "channel__type",)
    search_fields = ("message__body", "error", "provider_message_id")
    list_select_related = ("message", "channel", "rule")
    ordering = ("-created_at",)

    fieldsets = (
        ("Delivery info", {
            "fields": (
                "message",
                "channel",
                "rule",
                "status",
                "provider_message_id",
                "retry_count",
                "last_attempt_at",
                "error",
            ),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )


# ======================
# RuleDestination admin (optional, if you want to see it separately)
# ======================
@admin.register(RuleDestination)
class RuleDestinationAdmin(TimeStampedReadonlyMixin, admin.ModelAdmin):
    list_display = (
        "rule",
        "channel",
        "is_enabled",
        "created_at",
    )
    list_filter = ("is_enabled", "channel__type")
    search_fields = ("rule__name", "channel__name")
    list_select_related = ("rule", "channel")
    ordering = ("rule", "channel")

    fieldsets = (
        ("Action mapping", {
            "fields": (
                "rule",
                "channel",
                "is_enabled",
            ),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )


# ======================
# FailedLog inline
# ======================

@admin.register(FailedLog)
class FailedLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'short_error', 'source_tag', 'created_at')
    
    list_filter = ('source_tag', 'created_at')
    search_fields = ('error_message', 'raw_data')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'raw_data', 'error_message', 'source_tag', 'created_at', 'updated_at')

    def short_error(self, obj):
        if obj.error_message:
            return obj.error_message[:50] + "..." if len(obj.error_message) > 50 else obj.error_message
        return "No error message"
    short_error.short_description = 'Error Summary'