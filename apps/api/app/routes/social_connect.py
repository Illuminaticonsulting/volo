"""
VOLO — Social Connect Routes
OAuth connection flows for Twitter/X, Instagram, TikTok, Facebook.
Users connect their social accounts to read feeds and perform actions.
"""

import hashlib
import base64
import secrets
import logging

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import RedirectResponse

from app.auth import get_current_user, CurrentUser
from app.config import settings
from app.services.social_oauth import social_oauth, _store_state, _pop_state

logger = logging.getLogger("volo.social_connect")
router = APIRouter()


# ── Connection Status ────────────────────────────────────────────────

@router.get("/social/connect/status")
async def get_social_connection_status(current_user: CurrentUser = Depends(get_current_user)):
    """Get connection status for all social platforms."""
    status = await social_oauth.get_connection_status(current_user.user_id)

    # Also check which platform OAuth apps are configured
    configured = {
        "twitter": bool(settings.twitter_client_id),
        "instagram": bool(settings.instagram_client_id or settings.facebook_app_id),
        "tiktok": bool(settings.tiktok_client_key),
        "facebook": bool(settings.facebook_app_id),
        "reddit": True,  # Reddit works without OAuth (public API)
        "linkedin": False,  # LinkedIn requires special approval
    }

    platforms = []
    meta = {
        "twitter": {"name": "Twitter / X", "color": "#1DA1F2", "icon": "twitter"},
        "instagram": {"name": "Instagram", "color": "#E4405F", "icon": "instagram"},
        "tiktok": {"name": "TikTok", "color": "#000000", "icon": "tiktok"},
        "facebook": {"name": "Facebook", "color": "#1877F2", "icon": "facebook"},
        "reddit": {"name": "Reddit", "color": "#FF4500", "icon": "reddit"},
        "linkedin": {"name": "LinkedIn", "color": "#0A66C2", "icon": "linkedin"},
    }

    for p_id, m in meta.items():
        s = status.get(p_id, {})
        platforms.append({
            "id": p_id,
            "name": m["name"],
            "icon": m["icon"],
            "color": m["color"],
            "configured": configured.get(p_id, False),
            "connected": s.get("connected", False),
            "username": s.get("username", ""),
            "avatar": s.get("avatar", ""),
        })

    return {"platforms": platforms}


# ── Disconnect ───────────────────────────────────────────────────────

@router.delete("/social/connect/{platform}")
async def disconnect_social(platform: str, current_user: CurrentUser = Depends(get_current_user)):
    """Disconnect a social platform."""
    success = await social_oauth.disconnect(current_user.user_id, platform)
    if not success:
        raise HTTPException(404, f"{platform} was not connected")
    return {"status": "disconnected", "platform": platform}


# ── Twitter / X ──────────────────────────────────────────────────────

@router.get("/social/connect/twitter")
async def twitter_social_connect(current_user: CurrentUser = Depends(get_current_user)):
    """Start Twitter/X OAuth to connect social account (expanded scopes)."""
    if not settings.twitter_client_id:
        raise HTTPException(501, "Twitter OAuth not configured. Set TWITTER_CLIENT_ID in env.")

    code_verifier = secrets.token_urlsafe(64)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode()

    state = await _store_state("twitter", {
        "code_verifier": code_verifier,
        "user_id": current_user.user_id,
    })
    auth_url = social_oauth.twitter_auth_url(state, code_challenge)
    return {"url": auth_url, "state": state}


@router.get("/social/connect/twitter/callback")
async def twitter_social_callback(code: str = "", state: str = ""):
    """Handle Twitter OAuth callback for social connection."""
    try:
        if not code or not state:
            return _social_error_redirect("Missing code or state")
        state_data = await _pop_state(state, "twitter")
        user_id = state_data.get("user_id")
        if not user_id:
            return _social_error_redirect("Missing user context")

        result = await social_oauth.twitter_exchange(code, state_data["code_verifier"])
        await social_oauth.store_tokens(user_id, "twitter", result["tokens"], result["profile"])

        frontend = settings.frontend_url.rstrip("/")
        return RedirectResponse(url=f"{frontend}/social?connected=twitter", status_code=302)
    except Exception as e:
        logger.exception("Twitter social connect error")
        return _social_error_redirect(str(e))


# ── Instagram ────────────────────────────────────────────────────────

@router.get("/social/connect/instagram")
async def instagram_social_connect(current_user: CurrentUser = Depends(get_current_user)):
    """Start Instagram OAuth (via Meta/Facebook)."""
    client_id = settings.instagram_client_id or settings.facebook_app_id
    if not client_id:
        raise HTTPException(501, "Instagram OAuth not configured. Set INSTAGRAM_CLIENT_ID or FACEBOOK_APP_ID in env.")

    state = await _store_state("instagram", {"user_id": current_user.user_id})
    auth_url = social_oauth.instagram_auth_url(state)
    return {"url": auth_url, "state": state}


@router.get("/social/connect/instagram/callback")
async def instagram_social_callback(code: str = "", state: str = ""):
    """Handle Instagram OAuth callback."""
    try:
        if not code or not state:
            return _social_error_redirect("Missing code or state")
        state_data = await _pop_state(state, "instagram")
        user_id = state_data.get("user_id")
        if not user_id:
            return _social_error_redirect("Missing user context")

        result = await social_oauth.instagram_exchange(code)
        await social_oauth.store_tokens(user_id, "instagram", result["tokens"], result["profile"])

        frontend = settings.frontend_url.rstrip("/")
        return RedirectResponse(url=f"{frontend}/social?connected=instagram", status_code=302)
    except Exception as e:
        logger.exception("Instagram social connect error")
        return _social_error_redirect(str(e))


# ── TikTok ───────────────────────────────────────────────────────────

@router.get("/social/connect/tiktok")
async def tiktok_social_connect(current_user: CurrentUser = Depends(get_current_user)):
    """Start TikTok OAuth."""
    if not settings.tiktok_client_key:
        raise HTTPException(501, "TikTok OAuth not configured. Set TIKTOK_CLIENT_KEY in env.")

    state = await _store_state("tiktok", {"user_id": current_user.user_id})
    auth_url = social_oauth.tiktok_auth_url(state)
    return {"url": auth_url, "state": state}


@router.get("/social/connect/tiktok/callback")
async def tiktok_social_callback(code: str = "", state: str = ""):
    """Handle TikTok OAuth callback."""
    try:
        if not code or not state:
            return _social_error_redirect("Missing code or state")
        state_data = await _pop_state(state, "tiktok")
        user_id = state_data.get("user_id")
        if not user_id:
            return _social_error_redirect("Missing user context")

        result = await social_oauth.tiktok_exchange(code)
        await social_oauth.store_tokens(user_id, "tiktok", result["tokens"], result["profile"])

        frontend = settings.frontend_url.rstrip("/")
        return RedirectResponse(url=f"{frontend}/social?connected=tiktok", status_code=302)
    except Exception as e:
        logger.exception("TikTok social connect error")
        return _social_error_redirect(str(e))


# ── Facebook ─────────────────────────────────────────────────────────

@router.get("/social/connect/facebook")
async def facebook_social_connect(current_user: CurrentUser = Depends(get_current_user)):
    """Start Facebook OAuth."""
    if not settings.facebook_app_id:
        raise HTTPException(501, "Facebook OAuth not configured. Set FACEBOOK_APP_ID in env.")

    state = await _store_state("facebook", {"user_id": current_user.user_id})
    auth_url = social_oauth.facebook_auth_url(state)
    return {"url": auth_url, "state": state}


@router.get("/social/connect/facebook/callback")
async def facebook_social_callback(code: str = "", state: str = ""):
    """Handle Facebook OAuth callback."""
    try:
        if not code or not state:
            return _social_error_redirect("Missing code or state")
        state_data = await _pop_state(state, "facebook")
        user_id = state_data.get("user_id")
        if not user_id:
            return _social_error_redirect("Missing user context")

        result = await social_oauth.facebook_exchange(code)
        await social_oauth.store_tokens(user_id, "facebook", result["tokens"], result["profile"])

        frontend = settings.frontend_url.rstrip("/")
        return RedirectResponse(url=f"{frontend}/social?connected=facebook", status_code=302)
    except Exception as e:
        logger.exception("Facebook social connect error")
        return _social_error_redirect(str(e))


# ── Helpers ──────────────────────────────────────────────────────────

def _social_error_redirect(message: str) -> RedirectResponse:
    from urllib.parse import quote
    frontend = settings.frontend_url.rstrip("/")
    return RedirectResponse(url=f"{frontend}/social?error={quote(message)}", status_code=302)
