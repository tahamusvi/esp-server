import time
import json
import logging
import uuid

import paho.mqtt.client as mqtt
from django.core.management.base import BaseCommand
from django.db import DatabaseError, close_old_connections
from django.utils import timezone

from ...models import IncomingMessage, FailedLog
from ...services import process_incoming_message

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "MQTT Consumer using HiveMQ Public Broker"

    TOPIC = "device/MC60/sms_rx"

    BROKER_HOST = "broker.hivemq.com"
    BROKER_PORT = 1883
    KEEP_ALIVE = 60

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS("[*] Starting MQTT Consumer (HiveMQ)")
        )

        client_id = f"django-mc60-{uuid.uuid4()}"
        client = mqtt.Client(
            client_id=client_id,
            clean_session=True,
            protocol=mqtt.MQTTv311,
        )

        client.on_connect = self.on_connect
        client.on_disconnect = self.on_disconnect
        client.on_message = self.on_message

        # reconnect settings
        client.reconnect_delay_set(min_delay=1, max_delay=30)

        while True:
            try:
                self.stdout.write(
                    f"Connecting to HiveMQ ({self.BROKER_HOST}:{self.BROKER_PORT}) ..."
                )
                client.connect(self.BROKER_HOST, self.BROKER_PORT, self.KEEP_ALIVE)
                client.loop_forever()
            except Exception as e:
                logger.exception("MQTT connection error")
                print(f"MQTT error: {e} | retrying in 5 seconds...")
                time.sleep(5)

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.stdout.write(
                self.style.SUCCESS("✅ Connected to HiveMQ Broker")
            )
            client.subscribe(self.TOPIC, qos=1)
            print(f"Subscribed to topic: {self.TOPIC}")
        else:
            print(f"❌ Connection failed, rc={rc}")

    def on_disconnect(self, client, userdata, rc):
        print(f"⚠️ Disconnected from MQTT broker (rc={rc})")

    def on_message(self, client, userdata, msg):
        close_old_connections()

        raw_body = msg.payload.decode("utf-8", errors="ignore")

        try:
            if ":" not in raw_body:
                raise ValueError("Invalid message format from MC60")

            sender, content = raw_body.split(":", 1)

            decoded_content = content
            if (
                all(c in "0123456789ABCDEFabcdef" for c in content)
                and len(content) > 4
            ):
                try:
                    decoded_content = bytes.fromhex(content).decode("utf-16-be")
                except Exception:
                    pass

            incoming_msg = IncomingMessage.objects.create(
                from_number=sender,
                to_number="MC60_GATEWAY",
                body=decoded_content,
                received_at=timezone.now(),
                raw_payload=raw_body,
            )

            try:
                deliveries_created = process_incoming_message(incoming_msg)
                print(
                    f"Message saved. {deliveries_created} delivery attempts initiated."
                )
            except Exception as e:
                print(f"Message saved, but processing failed: {e}")

            print(f"📩 Saved SMS from {sender}")

        except DatabaseError as db_e:
            print(f"Database Error: {db_e}")
        except Exception as e:
            print(f"Error processing message: {e}")
            FailedLog.objects.create(
                raw_data=raw_body,
                error_message=str(e),
                source_tag="mc60_mqtt_hivemq",
            )
