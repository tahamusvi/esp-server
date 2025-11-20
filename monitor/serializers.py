# app/serializers.py
from rest_framework import serializers
from .models import IncomingMessage,SimEndpoint


class IncomingSmsPayloadSerializer(serializers.Serializer):
    """Payload sent by device (ESP32/SIM800)."""
    from_ = serializers.CharField(source="from_number")  # maps to model field
    to = serializers.CharField(source="to_number")
    token = serializers.CharField()
    body = serializers.CharField()
    received_at = serializers.DateTimeField(required=False)


class IncomingMessageSerializer(serializers.ModelSerializer):
    """Read-only representation of stored IncomingMessage."""
    class Meta:
        model = IncomingMessage
        fields = [
            "id",
            "project",
            "endpoint",
            "from_number",
            "to_number",
            "body",
            "received_at",
            "created_at",
        ]
        read_only_fields = fields




from rest_framework import serializers

class SimEndpointSerializer(serializers.ModelSerializer):
    """
    Serializer for listing SimEndpoints on the dashboard.
    Includes calculated fields like signal strength and last connection time.
    """
    # فیلدهای اضافی برای داشبورد که در مدل اصلی نیستند (فرضی)
    signal_strength_percentage = serializers.SerializerMethodField()
    signal_strength_dbm = serializers.SerializerMethodField()
    last_connected_at = serializers.SerializerMethodField()
    
    # برای نمایش نام پروژه در صورت نیاز
    project_slug = serializers.CharField(source='project.slug', read_only=True)

    class Meta:
        model = SimEndpoint
        fields = (
            "id",
            "project_slug",
            "name",
            "phone_number",
            "imei",
            "is_active",
            # فیلدهای داشبورد
            "signal_strength_percentage",
            "signal_strength_dbm",
            "last_connected_at",
            "created_at",
        )
        read_only_fields = fields # در لیست GET نباید قابل تغییر باشند


    def get_signal_strength_percentage(self, obj: SimEndpoint) -> str:
        # TODO: این منطق را بر اساس آخرین گزارش وضعیت (مثلاً از یک مدل ConnectionStatus) پیاده سازی کنید.
        # مثلاً: status = obj.connection_statuses.order_by('-created_at').first()
        # return f"{status.signal_percent}%" if status else "N/A"
        # مثال ثابت:
        if obj.id.int % 2 == 0:
            return "85%"
        return "0%"

    def get_signal_strength_dbm(self, obj: SimEndpoint) -> str:
        # TODO: پیاده سازی منطق دریافت قدرت سیگنال بر حسب dBm
        if obj.id.int % 2 == 0:
            return "-dBM"
        return "-dBM" # یا یک مقدار واقعی مثل -85 dBm

    def get_last_connected_at(self, obj: SimEndpoint) -> str:
        # TODO: پیاده سازی منطق دریافت تاریخ آخرین اتصال (Last Connected)
        # return obj.connection_statuses.order_by('-created_at').first().created_at
        # مثال ثابت:
        return "۱۴۰۴/۰۲/۲۳، ۲۰:۰۲:۲۲"