# app/serializers.py
from rest_framework import serializers
from .models import *



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
            "from_number",
            "to_number",
            "body",
            "received_at",
            "created_at",
            "processed",
        ]
        read_only_fields = fields


class DeliveryAttemptSerializer(serializers.ModelSerializer):
    """
    Serializer for the Delivery History page.
    Includes nested data like channel and rule names.
    """
    channel_name = serializers.CharField(source='channel.name', read_only=True)
    rule_name = serializers.CharField(source='rule.name', read_only=True)
    message_content = serializers.SerializerMethodField()

    class Meta:
        model = DeliveryAttempt
        fields = (
            'id', 
            'status', 
            'channel_name', 
            'rule_name', 
            'last_attempt_at', 
            'created_at',
            'error', 
            'provider_message_id',
            'retry_count',
            'message_content'
        )
    
    def get_message_content(self, obj):
        body = obj.message.body
        return body[:50] + '...' if len(body) > 50 else body

class ForwardRuleSerializer(serializers.ModelSerializer):
    destination_channels = serializers.SerializerMethodField()
    class Meta:
        model = ForwardRule
        fields = ['id', 'name', 'filters', 'is_enabled', 'destination_channels']

    def get_destination_channels(self, obj):
        actions = obj.actions.all()
        return [
            {
                "id": action.channel.id,
                "name": action.channel.name,
                "type": action.channel.type
            } 
            for action in actions
        ]
        
            
class DestinationChannelCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DestinationChannel
        fields = ['id','type', 'name', 'config', 'is_enabled']

        extra_kwargs = {
            'id': {'read_only': True},
            'type': {'required': True},
            'name': {'required': True},
            'config': {'required': True},
            'is_enabled': {'required': False},
        }  
        
class RuleDestinationCreateSerializer(serializers.ModelSerializer):
    rule_id = serializers.UUIDField(write_only=True)
    channel_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = RuleDestination
        fields = ("rule_id", "channel_id")

    def validate(self, attrs):
        rule_id = attrs.get("rule_id")
        channel_id = attrs.get("channel_id")

        try:
            rule = ForwardRule.objects.get(id=rule_id)
        except ForwardRule.DoesNotExist:
            raise serializers.ValidationError({"rule_id": "Rule not found"})

        try:
            channel = DestinationChannel.objects.get(id=channel_id)
        except DestinationChannel.DoesNotExist:
            raise serializers.ValidationError({"channel_id": "Channel not found"})

        if RuleDestination.objects.filter(rule=rule, channel=channel).exists():
            raise serializers.ValidationError(
                "This channel is already assigned to this rule"
            )

        attrs["rule"] = rule
        attrs["channel"] = channel
        return attrs

    def create(self, validated_data):
        validated_data.pop("rule_id")
        validated_data.pop("channel_id")

        return RuleDestination.objects.create(
            rule=validated_data["rule"],
            channel=validated_data["channel"],
            is_enabled=True,
        )              

class RuleDestinationDeleteSerializer(serializers.Serializer):
    rule_id = serializers.UUIDField()
    channel_id = serializers.UUIDField()        