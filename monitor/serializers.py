# app/serializers.py
from rest_framework import serializers
from .models import IncomingMessage


class IncomingSmsPayloadSerializer(serializers.Serializer):
    """Payload sent by device (ESP32/SIM800)."""
    token = serializers.CharField(source="token")
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
