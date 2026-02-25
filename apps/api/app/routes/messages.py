"""
VOLO — Unified Messaging Routes
Aggregated inbox across Telegram, WhatsApp, iMessage, Signal, Discord, Slack, Twitter DMs.
Auto-2FA: When a platform needs a TOTP code, Volo pulls it from the vault.
"""

import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
import httpx

from app.services.messaging import MessagingService
from app.services.authenticator import authenticator_vault
from app.services.social_oauth import social_oauth
from app.auth import get_current_user, CurrentUser

logger = logging.getLogger("volo.messages")
router = APIRouter()
messaging = MessagingService()


class SendMessageRequest(BaseModel):
    platform: str  # telegram, whatsapp, whatsapp_business, signal, discord, slack, twitter
    to: str  # chat_id, phone number, or channel_id
    text: str
    template: Optional[str] = None  # For WhatsApp Business templates


async def _fetch_twitter_dms(user_id: str) -> list[dict]:
    """Fetch Twitter/X DMs for a user using their stored OAuth token."""
    token = await social_oauth.get_access_token(user_id, "twitter")
    if not token:
        return []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Twitter API v2 DM events
            resp = await client.get(
                "https://api.twitter.com/2/dm_events",
                params={
                    "dm_event.fields": "id,text,created_at,sender_id,dm_conversation_id",
                    "max_results": 50,
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code != 200:
                logger.warning(f"Twitter DMs fetch failed: {resp.status_code}")
                return []

            data = resp.json()
            messages = []
            for event in data.get("data", []):
                messages.append({
                    "platform": "twitter",
                    "id": event.get("id", ""),
                    "from": event.get("sender_id", "Unknown"),
                    "from_username": "",
                    "avatar": None,
                    "content": event.get("text", ""),
                    "timestamp": event.get("created_at", ""),
                    "chat_id": event.get("dm_conversation_id", ""),
                    "chat_title": f"DM {event.get('dm_conversation_id', '')[:8]}",
                    "read": True,
                    "type": "text",
                    "is_from_me": False,
                })
            return messages
    except Exception:
        logger.exception("Error fetching Twitter DMs")
        return []


@router.get("/messages")
async def get_all_messages(current_user: CurrentUser = Depends(get_current_user)):
    """Get unified inbox — all messages from all platforms including Twitter DMs."""
    messages = await messaging.get_all_messages()

    # Also fetch Twitter DMs if connected
    twitter_dms = await _fetch_twitter_dms(current_user.user_id)
    if twitter_dms:
        messages.extend(twitter_dms)

    platforms = messaging.get_connected_platforms()
    # Add Twitter to platforms if connected
    twitter_token = await social_oauth.get_access_token(current_user.user_id, "twitter")
    if twitter_token:
        platforms.append({
            "id": "twitter",
            "name": "Twitter / X",
            "connected": True,
            "color": "#1DA1F2",
        })

    return {
        "messages": messages,
        "total": len(messages),
        "platforms": platforms,
    }


@router.get("/messages/{platform}")
async def get_platform_messages(platform: str, current_user: CurrentUser = Depends(get_current_user)):
    """Get messages from a specific platform."""
    # Handle Twitter DMs separately
    if platform == "twitter":
        dms = await _fetch_twitter_dms(current_user.user_id)
        return {"platform": "twitter", "messages": dms, "total": len(dms)}

    fetchers = {
        "telegram": messaging.telegram_get_updates,
        "whatsapp": messaging.whatsapp_get_messages,
        "whatsapp_business": messaging.whatsapp_biz_get_messages,
        "imessage": messaging.imessage_get_messages,
        "signal": messaging.signal_get_messages,
        "discord": messaging.discord_get_messages,
        "slack": messaging.slack_get_messages,
    }

    fetcher = fetchers.get(platform)
    if not fetcher:
        return {"error": f"Unknown platform: {platform}", "messages": []}

    messages = await fetcher()
    return {"platform": platform, "messages": messages, "total": len(messages)}


@router.post("/messages/send")
async def send_message(body: SendMessageRequest, current_user: CurrentUser = Depends(get_current_user)):
    """Send a message on a specific platform."""
    if body.platform == "telegram":
        result = await messaging.telegram_send(body.to, body.text)
    elif body.platform == "whatsapp":
        result = await messaging.whatsapp_send(body.to, body.text)
    elif body.platform == "whatsapp_business":
        result = await messaging.whatsapp_biz_send(body.to, body.text, body.template)
    elif body.platform == "discord":
        result = await messaging.discord_send(body.to, body.text)
    elif body.platform == "slack":
        result = await messaging.slack_send(body.to, body.text)
    else:
        return {"error": f"Send not supported for {body.platform}"}

    return {"platform": body.platform, "result": result}


@router.get("/messages/platforms")
async def get_messaging_platforms(current_user: CurrentUser = Depends(get_current_user)):
    """Get list of messaging platforms and their connection status + 2FA availability."""
    platforms = messaging.get_connected_platforms()

    # Check which platforms have TOTP configured in the vault
    totp_accounts = await authenticator_vault.list_accounts(user_id=current_user.user_id)
    totp_services = {a["service"] for a in totp_accounts}

    for p in platforms:
        p["has_2fa"] = p["id"] in totp_services

    return {"platforms": platforms}


@router.get("/messages/{platform}/2fa")
async def get_platform_2fa(platform: str, current_user: CurrentUser = Depends(get_current_user)):
    """
    Get the current 2FA code for a messaging platform.
    Called automatically when logging in or re-authenticating.

    Example: GET /api/messages/telegram/2fa
    Returns: {"code": "482901", "remaining_seconds": 17}

    This is the magic — set up Telegram 2FA in Volo's authenticator once,
    and the messaging page auto-fills it. No more opening Google Authenticator
    and copy-pasting codes.
    """
    result = await authenticator_vault.get_code(user_id=current_user.user_id, service=platform)
    if not result:
        return {
            "platform": platform,
            "has_2fa": False,
            "message": f"No authenticator configured for {platform}. "
                       f"Add one at POST /api/authenticator/add with service='{platform}'",
        }
    return {
        "platform": platform,
        "has_2fa": True,
        **result,
    }
