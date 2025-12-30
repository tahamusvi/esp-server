from django.contrib import admin

from .models import (
    Project,
    SimEndpoint,
    IncomingMessage,
    DestinationChannel,
    ForwardRule,
    RuleDestination,
    DeliveryAttempt,
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
# Project admin
# ======================
@admin.register(Project)
class ProjectAdmin(TimeStampedReadonlyMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "user",
        "slug",
        "environment",
        "timezone",
        "is_active",
        "created_at",
    )
    list_filter = ("environment", "is_active")
    search_fields = ("name", "slug")
    ordering = ("name",)

    fieldsets = (
        ("Basic info", {
            "fields": (
                "name",
                "slug",
                "environment",
                "description",
                "timezone",
                "is_active",
            ),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )


# ======================
# SimEndpoint admin
# ======================
@admin.register(SimEndpoint)
class SimEndpointAdmin(TimeStampedReadonlyMixin, admin.ModelAdmin):
    list_display = (
        "name",
        "phone_number",
        "project",
        "is_active",
        "api_token",
        "created_at",
    )
    list_filter = ("project", "is_active")
    search_fields = ("name", "phone_number", "imei", "api_token")
    list_select_related = ("project",)
    ordering = ("project", "name")

    fieldsets = (
        ("Basic info", {
            "fields": (
                "project",
                "name",
                "phone_number",
                "imei",
                "is_active",
            ),
        }),
        ("Auth", {
            "fields": ("api_token",),
            "description": "API token used by the device (ESP32/SIM800) to authenticate.",
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )


# ======================
# DestinationChannel admin
# ======================
@admin.register(DestinationChannel)
class DestinationChannelAdmin(TimeStampedReadonlyMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "type",
        "project",
        "is_enabled",
        "created_at",
    )
    list_filter = ("type", "project", "is_enabled")
    search_fields = ("name",)
    list_select_related = ("project",)
    ordering = ("project", "type", "name")

    fieldsets = (
        ("Basic info", {
            "fields": (
                "project",
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
        "name",
        "project",
        "is_enabled",
        "stop_processing",
        "created_at",
    )
    list_filter = ("project", "is_enabled", "stop_processing")
    search_fields = ("name", "filters")
    list_select_related = ("project",)
    ordering = ("project", "name")
    inlines = (RuleDestinationInline,)

    fieldsets = (
        ("Basic info", {
            "fields": (
                "project",
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
        "project",
        "endpoint",
        "processed",
        "received_at",
        "created_at",
    )
    list_filter = ("project", "endpoint", "processed")
    search_fields = ("from_number", "to_number", "body")
    list_select_related = ("project", "endpoint")
    date_hierarchy = "received_at"
    ordering = ("-received_at",)

    readonly_fields = TimeStampedReadonlyMixin.readonly_fields + ("raw_payload",)

    fieldsets = (
        ("Message", {
            "fields": (
                "project",
                "endpoint",
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
    list_filter = ("status", "channel__type", "channel__project")
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
    list_filter = ("is_enabled", "channel__type", "rule__project")
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
        ("Templates & config", {
            "fields": (
                "override_text_template",
                "action_config",
            ),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )
