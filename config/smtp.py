from django.core.mail import EmailMessage
from django.core.mail.backends.smtp import EmailBackend
from dotenv import load_dotenv
import os

load_dotenv("./.env")
env = os.environ.get


class FailoverSMTPBackend(EmailBackend):
    def __init__(
        self,
        host=None,
        port=None,
        username=None,
        password=None,
        use_tls=None,
        fail_silently=False,
        **kwargs,
    ):
        count = int(env("EMAIL_COUNT"))
        self.hosts = [
            {
                "host": env("EMAIL_HOST"),
                "port": env("EMAIL_PORT"),
                "use_tls": env("EMAIL_USE_TLS"),
                "username": env(f"EMAIL_HOST_USER{i}"),
                "password": env(f"EMAIL_HOST_PASSWORD{i}"),
            }
            for i in range(1, count + 1)
        ]
        super().__init__(fail_silently=fail_silently, **kwargs)

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        num_sent = 0
        for message in email_messages:
            for host_info in self.hosts:
                self.host = host_info["host"]
                self.port = host_info["port"]
                self.username = host_info["username"]
                self.password = host_info["password"]
                self.use_tls = host_info["use_tls"]

                try:
                    sent = self._send(message)
                    if sent:
                        num_sent += 1
                        break  # Successfully sent, no need to try more servers
                except Exception as e:
                    continue  # Failed to send, try the next server

        return num_sent

    def _send(self, email_message):
        if not email_message.recipients():
            return False
        try:
            self.open()
            self.connection.sendmail(
                email_message.from_email,
                email_message.recipients(),
                email_message.message().as_bytes(linesep="\r\n"),
            )
            return True
        except Exception as e:
            if not self.fail_silently:
                raise
            return False
        finally:
            self.close()
