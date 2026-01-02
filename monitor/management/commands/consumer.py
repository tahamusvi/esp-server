import time
import json
import logging
import paho.mqtt.client as mqtt
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import DatabaseError, close_old_connections
from ...models import Log, FailedLog
from services.tokens import ServiceAccessToken

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "MQTT Consumer for MC60 Gateway SMS Integration"

    TOPIC = "device/MC60/sms_rx"
    BROKER_HOST = "YOUR_PUBLIC_IP"
    BROKER_PORT = 1883

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(f"[*] Starting MQTT Consumer for MC60 Gateway"))

        # تعریف کلاینت MQTT
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
            self.stdout.write(self.style.SUCCESS("✅ Connected to MQTT Broker"))
            client.subscribe(self.TOPIC, qos=1)
        else:
            print(f"❌ Connection failed with code {rc}")

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

            # پیدا کردن توکن (مشابه کد قبلی‌تان)
            # نکته: اینجا باید مشخص کنید که توکن MC60 چیست. 
            # می‌توانید یک توکن ثابت در دیتابیس برای این دستگاه بسازید.
            try:
                token = ServiceAccessToken.objects.get(name="MC60_GATEWAY")
            except ServiceAccessToken.DoesNotExist:
                print("Error: MC60 Token not found in database")
                return

            # ذخیره در جدول Log (دقیقاً با فیلدهای کد خودتان)
            Log.objects.create(
                user=token.user,
                token=token,
                created_at=datetime.now(),
                source=sender,
                destination="GATEWAY", # مقصد خود ماژول است
                status="s",
                is_mock=False,
                payload={"raw": content, "text": decoded_content}
            )

            print(f"💾 Saved SMS from {sender}: {decoded_content[:20]}...")

        except DatabaseError as db_e:
            print(f"Database Error: {db_e}")
            # در MQTT مفهوم Requeue مثل RabbitMQ متفاوت است، 
            # اما با QoS 1 اگر ACK ندهیم، دوباره تلاش می‌شود.
        except Exception as e:
            print(f"Unexpected Error: {e}")
            FailedLog.objects.create(raw_data=raw_body, error_message=str(e))