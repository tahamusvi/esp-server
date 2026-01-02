import time
import json
import logging
import paho.mqtt.client as mqtt
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import DatabaseError, close_old_connections
from ...models import IncomingMessage,FailedLog
from config.settings import MQTT_BROKER_HOST
from django.utils import timezone

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "MQTT Consumer for MC60 Gateway SMS Integration"

    TOPIC = "device/MC60/sms_rx"
    BROKER_HOST = MQTT_BROKER_HOST
    BROKER_PORT = 1883

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(f"[*] Starting MQTT Consumer for MC60 Gateway"))

        client = mqtt.Client(client_id="Django_Gateway_Worker", clean_session=False)
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        
        while True:
            try:
                self.stdout.write(f"Connecting to MQTT Broker ({self.BROKER_HOST})...")
                client.connect(self.BROKER_HOST, self.BROKER_PORT, 60)
                client.loop_forever()
            except Exception as e:
                print(f"MQTT Connection lost: {e}. Retrying in 5s...")
                time.sleep(5)

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.stdout.write(self.style.SUCCESS("Connected to MQTT Broker!!"))
            client.subscribe(self.TOPIC, qos=1)
        else:
            print(f"[Error] Connection failed with code {rc}")

    def on_message(self, client, userdata, msg):
        close_old_connections()
        raw_body = msg.payload.decode("utf-8")
        
        try:
            if ":" not in raw_body:
                raise ValueError("Invalid message format from MC60")

            sender, content = raw_body.split(":", 1)

            decoded_content = content
            if all(c in '0123456789ABCDEFabcdef' for c in content) and len(content) > 4:
                try:
                    decoded_content = bytes.fromhex(content).decode('utf-16-be')
                except:
                    pass

            IncomingMessage.objects.create(
                from_number=sender,
                to_number="MC60_GATEWAY",
                body=decoded_content,
                received_at=timezone.now(),
            )

            print(f"Saved SMS from {sender}!")

        except DatabaseError as db_e:
            print(f"Database Error: {db_e}")
        except Exception as e:
            print(f"Error processing message: {e}")
            FailedLog.objects.create(
                raw_data=msg.payload.decode("utf-8"),
                error_message=str(e),
                source_tag="mc60_mqtt"
            )