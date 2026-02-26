"""
VOLO — Webhook Routes
Receive and dispatch webhooks from external services.
"""

import uuid
import os
import json
import hmac
import hashlib
import time
import logging
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
import httpx

from app.config import settings

logger = logging.getLogger("volo.webhooks")

router = APIRouter()

# In-memory webhook store
_webhooks: list[dict] = []
_webhook_events: list[dict] = []


class WebhookCreate(BaseModel):
    url: str
    events: list[str]
    secret: str = ""


class WebhookEvent(BaseModel):
    source: str
    event_type: str
    payload: dict


@router.post("/webhooks")
async def create_webhook(body: WebhookCreate):
    """Register a new outbound webhook."""
    webhook = {
        "id": str(uuid.uuid4()),
        "url": body.url,
        "events": body.events,
        "secret": body.secret or str(uuid.uuid4()),
        "active": True,
        "created_at": datetime.utcnow().isoformat(),
    }
    _webhooks.append(webhook)
    return webhook


@router.get("/webhooks")
async def list_webhooks():
    """List all registered webhooks."""
    return {"webhooks": _webhooks}


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str):
    """Delete a webhook."""
    global _webhooks
    _webhooks = [w for w in _webhooks if w["id"] != webhook_id]
    return {"deleted": True}


# ── Inbound Webhooks ────────────────────────

def _verify_github_signature(body: bytes, signature_header: str, secret: str) -> bool:
    """Verify GitHub webhook HMAC-SHA256 signature."""
    if not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    received = signature_header[len("sha256="):]
    return hmac.compare_digest(expected, received)


@router.post("/webhooks/github")
async def github_webhook(request: Request):
    """Receive GitHub webhook events (push, PR, issue, etc.)."""
    body = await request.body()

    if settings.github_webhook_secret:
        sig = request.headers.get("X-Hub-Signature-256", "")
        if not _verify_github_signature(body, sig, settings.github_webhook_secret):
            raise HTTPException(401, "Invalid webhook signature")

    event_type = request.headers.get("X-GitHub-Event", "unknown")
    delivery_id = request.headers.get("X-GitHub-Delivery", "")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON payload")

    event = {
        "id": delivery_id or str(uuid.uuid4()),
        "source": "github",
        "type": event_type,
        "summary": _summarize_github_event(event_type, payload),
        "received_at": datetime.utcnow().isoformat(),
    }
    _webhook_events.append(event)
    logger.info(f"GitHub webhook: {event_type} — {event['summary']}")

    return {"received": True, "event_type": event_type}


def _verify_stripe_signature(body: bytes, signature_header: str, secret: str) -> bool:
    """
    Verify Stripe webhook signature.
    Stripe signs: f"{timestamp}.{body}" with HMAC-SHA256.
    Header format: "t=<ts>,v1=<sig>[,v1=<sig2>...]"
    """
    parts = {k: v for k, v in (item.split("=", 1) for item in signature_header.split(",") if "=" in item)}
    ts = parts.get("t", "")
    v1 = parts.get("v1", "")
    if not ts or not v1:
        return False
    # Reject events older than 5 minutes
    try:
        if abs(time.time() - int(ts)) > 300:
            return False
    except ValueError:
        return False
    signed_payload = f"{ts}.{body.decode()}"
    expected = hmac.new(secret.encode(), signed_payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, v1)


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Receive Stripe webhook events (subscription, payment, etc.)."""
    body = await request.body()

    if settings.stripe_webhook_secret:
        sig = request.headers.get("Stripe-Signature", "")
        if not _verify_stripe_signature(body, sig, settings.stripe_webhook_secret):
            raise HTTPException(401, "Invalid webhook signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON payload")

    event_type = payload.get("type", "unknown")
    event = {
        "id": payload.get("id", str(uuid.uuid4())),
        "source": "stripe",
        "type": event_type,
        "received_at": datetime.utcnow().isoformat(),
    }
    _webhook_events.append(event)
    logger.info(f"Stripe webhook: {event_type}")

    return {"received": True, "event_type": event_type}


def _verify_slack_signature(body: bytes, timestamp: str, signature_header: str, secret: str) -> bool:
    """Verify Slack webhook signing secret (v0 scheme)."""
    try:
        if abs(time.time() - int(timestamp)) > 300:
            return False
    except ValueError:
        return False
    basestring = f"v0:{timestamp}:{body.decode()}"
    expected = "v0=" + hmac.new(secret.encode(), basestring.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


@router.post("/webhooks/slack")
async def slack_webhook(request: Request):
    """Receive Slack event subscriptions."""
    body = await request.body()

    if settings.slack_signing_secret:
        ts = request.headers.get("X-Slack-Request-Timestamp", "")
        sig = request.headers.get("X-Slack-Signature", "")
        if not _verify_slack_signature(body, ts, sig, settings.slack_signing_secret):
            raise HTTPException(401, "Invalid webhook signature")

    body = json.loads(body)

    # Slack URL verification challenge
    if body.get("type") == "url_verification":
        return {"challenge": body.get("challenge")}

    event = body.get("event", {})
    _webhook_events.append({
        "id": str(uuid.uuid4()),
        "source": "slack",
        "type": event.get("type", "unknown"),
        "received_at": datetime.utcnow().isoformat(),
    })

    return {"ok": True}


# ===== WhatsApp Cloud API Webhook =====

@router.get("/webhooks/whatsapp")
async def whatsapp_webhook_verify(request: Request):
    """WhatsApp webhook verification (GET). Meta sends hub.challenge to verify."""
    params = request.query_params
    mode = params.get("hub.mode", "")
    token = params.get("hub.verify_token", "")
    challenge = params.get("hub.challenge", "")

    verify_token = os.environ.get("WHATSAPP_VERIFY_TOKEN", "volo-whatsapp-verify")

    if mode == "subscribe" and token == verify_token:
        logger.info("WhatsApp webhook verified")
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(challenge)

    raise HTTPException(403, "Verification failed")


@router.post("/webhooks/whatsapp")
async def whatsapp_webhook_receive(request: Request):
    """
    Receive WhatsApp Cloud API webhook events (inbound messages).
    Meta sends message events here when users message your WhatsApp number.
    """
    body = await request.json()

    entries = body.get("entry", [])
    for entry in entries:
        for change in entry.get("changes", []):
            value = change.get("value", {})
            messages = value.get("messages", [])
            contacts = value.get("contacts", [])

            contact_map = {}
            for c in contacts:
                contact_map[c.get("wa_id", "")] = c.get("profile", {}).get("name", "Unknown")

            for msg in messages:
                msg_type = msg.get("type", "text")
                content = ""
                if msg_type == "text":
                    content = msg.get("text", {}).get("body", "")
                elif msg_type == "image":
                    content = "[Image]"
                elif msg_type == "video":
                    content = "[Video]"
                elif msg_type == "audio":
                    content = "[Audio]"
                elif msg_type == "document":
                    content = "[Document]"
                elif msg_type == "location":
                    loc = msg.get("location", {})
                    content = f"[Location: {loc.get('latitude')}, {loc.get('longitude')}]"
                else:
                    content = f"[{msg_type}]"

                sender = msg.get("from", "")
                sender_name = contact_map.get(sender, sender)

                _webhook_events.append({
                    "id": msg.get("id", str(uuid.uuid4())),
                    "source": "whatsapp",
                    "type": "message",
                    "from": sender,
                    "from_name": sender_name,
                    "content": content,
                    "timestamp": msg.get("timestamp", ""),
                    "received_at": datetime.utcnow().isoformat(),
                })
                logger.info(f"WhatsApp message from {sender_name}: {content[:50]}")

    return {"status": "ok"}


# ===== Telegram Bot Webhook =====

@router.post("/webhooks/telegram")
async def telegram_webhook_receive(request: Request):
    """
    Receive Telegram bot webhook updates.
    Set this URL via: POST https://api.telegram.org/bot<TOKEN>/setWebhook?url=<YOUR_URL>/api/webhooks/telegram
    """
    body = await request.json()

    msg = body.get("message", {})
    if msg:
        chat = msg.get("chat", {})
        from_user = msg.get("from", {})
        text = msg.get("text", "")

        _webhook_events.append({
            "id": str(msg.get("message_id", uuid.uuid4())),
            "source": "telegram",
            "type": "message",
            "from": from_user.get("first_name", "Unknown"),
            "from_username": from_user.get("username", ""),
            "chat_id": str(chat.get("id", "")),
            "content": text or "[media]",
            "received_at": datetime.utcnow().isoformat(),
        })
        logger.info(f"Telegram message from {from_user.get('first_name', 'Unknown')}: {text[:50] if text else '[media]'}")

    return {"ok": True}


@router.post("/webhooks/telegram/setup")
async def telegram_setup_webhook(request: Request):
    """
    Set up the Telegram bot webhook.
    Body: { "bot_token": "...", "webhook_url": "https://your-domain.com/api/webhooks/telegram" }
    """
    body = await request.json()
    bot_token = body.get("bot_token", "")
    webhook_url = body.get("webhook_url", "")

    if not bot_token or not webhook_url:
        raise HTTPException(400, "Missing bot_token or webhook_url")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.telegram.org/bot{bot_token}/setWebhook",
            json={"url": webhook_url},
        )
        data = resp.json()
        if not data.get("ok"):
            return {"error": data.get("description", "Failed to set webhook")}

    return {"success": True, "message": f"Telegram webhook set to {webhook_url}"}


@router.get("/webhooks/events")
async def list_webhook_events(limit: int = 50):
    """List recent webhook events."""
    return {"events": list(reversed(_webhook_events))[:limit]}


def _summarize_github_event(event_type: str, payload: dict) -> str:
    repo = payload.get("repository", {}).get("full_name", "")
    if event_type == "push":
        commits = payload.get("commits", [])
        return f"{len(commits)} commit(s) pushed to {repo}"
    elif event_type == "pull_request":
        action = payload.get("action", "")
        pr = payload.get("pull_request", {})
        return f"PR #{pr.get('number', '?')} {action}: {pr.get('title', '')}"
    elif event_type == "issues":
        action = payload.get("action", "")
        issue = payload.get("issue", {})
        return f"Issue #{issue.get('number', '?')} {action}: {issue.get('title', '')}"
    return f"{event_type} event for {repo}"
