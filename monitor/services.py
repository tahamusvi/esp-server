# monitor/services.py

import requests
import json
from django.utils import timezone
from django.db import transaction
from monitor.models import IncomingMessage, ForwardRule, DeliveryAttempt, DestinationChannel
from django.core.exceptions import ValidationError
from .behaviors import send_bale_message,send_telegram_message
from paho.mqtt import publish
import paho.mqtt.client as mqtt
from config.settings import MQTT_BROKER_HOST


def _execute_delivery_attempt(attempt: DeliveryAttempt, message: IncomingMessage):
    """
    Dispatcher function to execute the actual delivery based on the channel type.
    Updates the DeliveryAttempt status (SENT/FAILED).
    """
    channel = attempt.channel
    cfg = channel.config or {}

    local_time = timezone.localtime(message.received_at)
    time_str = local_time.strftime('%Y-%m-%d %H:%M:%S')

    
    text = (
        f"از شماره: {message.from_number}\n"
        f"به شماره: {message.to_number}\n"
         f"تاریخ و زمان: {time_str}\n"
        f"==================================\n"
        f"متن پیام:\n"
        f"{message.body}"
    )
    try:
        if channel.type == DestinationChannel.ChannelType.TELEGRAM:
            token = cfg.get("token")
            chat_id = cfg.get("chat_id")
            if not token or not chat_id:
                raise ValueError("Telegram token or chat_id is missing in config.")
                
            result = send_telegram_message(token, chat_id, text)
            provider_id = result.get("message_id")

        elif channel.type == DestinationChannel.ChannelType.Bale:
            token = cfg.get("token")
            chat_id = cfg.get("chat_id")
            if not token or not chat_id:
                raise ValueError("Bale token or chat_id is missing in config.")
                
            result = send_bale_message(token, chat_id, text)
            provider_id = result.get("message_id")

        elif channel.type == DestinationChannel.ChannelType.SMS:
            target_phone = cfg.get("phone") 
            if not target_phone:
                raise ValueError("Target phone number is missing in SMS channel config.")

            mqtt_payload = f"SEND_SMS:{target_phone}:{message.body}"
            command_topic = f"device/MC60/commands" 
            
            publish.single(
                command_topic,
                payload=mqtt_payload,
                hostname=MQTT_BROKER_HOST,
                port=1883,
                qos=1
            )
            
            provider_id = f"MQTT_SENT_{timezone.now().timestamp()}"

        elif channel.type == DestinationChannel.ChannelType.WEBHOOK:
            url = cfg.get("url")
            if not url:
                raise ValueError("Webhook URL is missing in config.")
            
            payload = {
                "from": message.from_number,
                "to": message.to_number,
                "body": message.body,
            }
            r = requests.post(url, json=payload, timeout=8)
            r.raise_for_status()
            provider_id = f"HTTP_{r.status_code}"

        else:
            raise NotImplementedError(f"Channel type {channel.type} not supported yet.")

        attempt.status = DeliveryAttempt.Status.SENT
        attempt.provider_message_id = str(provider_id)
        attempt.last_attempt_at = timezone.now()
        attempt.save()

    except Exception as e:
        error_msg = f"Delivery failed: {e}"
        print(error_msg)
        attempt.status = DeliveryAttempt.Status.FAILED
        attempt.error = error_msg[:500]
        attempt.retry_count += 1
        attempt.last_attempt_at = timezone.now()
        attempt.save()


def _check_message_filters(message: IncomingMessage, filters: dict) -> bool:
    """
    Checks if the incoming message matches the JSON filters defined in the ForwardRule.
    A simplified version: checks if 'body_contains' text is present in the message body.
    """
    if body_contains := filters.get("body_contains"):
        if body_contains.lower() not in message.body.lower():
            return False

    if from_number_is := filters.get("from_number_is"):
        if from_number_is != message.from_number:
            return False
            

    return True


@transaction.atomic
def process_incoming_message(message: IncomingMessage) -> int:
    """
    The core service logic: finds matching rules and creates delivery attempts.
    """
    deliveries_created = 0

    rules_qs = ForwardRule.objects.filter(
        is_enabled=True
    )


    for rule in rules_qs:
        if not _check_message_filters(message, rule.filters):
            continue

        rule_actions = rule.actions.filter(is_enabled=True)

        for rule_action in rule_actions:
            attempt = DeliveryAttempt.objects.create(
                message=message,
                rule=rule,
                channel=rule_action.channel,
                status=DeliveryAttempt.Status.PENDING,
            )
            deliveries_created += 1
            
            _execute_delivery_attempt(attempt, message)

        if rule.stop_processing:
            break
            
    message.processed = True
    message.save()
    
    return deliveries_created