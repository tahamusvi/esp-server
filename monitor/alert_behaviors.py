import requests
import json


def flashcall(cfg):
    numbers = []
    for number in cfg.get("destination"):
        numbers.append(cfg.get("destination")[number])

    url = cfg.get("url")
    if not url:
        raise ValueError("webhook.url not configured")
    headers = cfg.get("headers") or {}
    for x in numbers:
        payload = {
            "action": "flashcall",
            "destination": x,
            "payload": {"code":cfg.get("code"),},
            "token":cfg.get("token"),
        }
        r = requests.post(url, json=payload, headers=headers, timeout=8)

    resp_code = r.status_code
    if r.status_code >= 300:
        raise RuntimeError(f"webhook responded {r.status_code}: {r.text[:200]}")






def send_bale_message(token: str, chat_id: str | int, text: str, reply_to_message_id: int | None = None):

    url = f"https://tapi.bale.ai/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
    }
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id

    try:
        response = requests.post(url, json=payload, timeout=8)
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                return data["result"]
            else:
                raise RuntimeError(f"Bale API error: {data}")
        else:
            raise RuntimeError(f"Bale HTTP {response.status_code}: {response.text[:200]}")
    except Exception as e:
        raise RuntimeError(f"Bale sendMessage failed: {e}")




def send_telegram_message(token: str, chat_id: int | str, text: str,
                          parse_mode: str | None = None,
                          reply_to_message_id: int | None = None,
                          disable_web_page_preview: bool | None = None):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id
    if disable_web_page_preview is not None:
        payload["disable_web_page_preview"] = disable_web_page_preview

    r = requests.post(url, json=payload, timeout=10)
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram error: {data}")
    return data["result"]
