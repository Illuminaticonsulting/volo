"""
VOLO — Shared OAuth Utilities
Find-or-create user from OAuth profile, issue JWT, redirect to frontend.
State management for all OAuth flows (shared between auth and social_oauth).
"""

import json
import secrets
import uuid
from datetime import datetime
from urllib.parse import urlencode, quote

from sqlalchemy import select

from app.auth import create_access_token, create_refresh_token
from app.database import async_session, User, Integration
from app.config import settings

# ── OAuth state helpers (Redis-backed, multi-worker safe) ─────────────────────

_OAUTH_STATE_TTL = 600  # 10 minutes


async def store_oauth_state(
    provider: str,
    extra: dict | None = None,
    key_prefix: str = "oauth_state",
) -> str:
    """
    Generate a CSRF state token and persist it in Redis.
    Returns the state string to embed in the OAuth redirect URL.
    """
    from app.services.cache import cache
    state = secrets.token_urlsafe(32)
    payload = {
        "provider": provider,
        "created_at": datetime.utcnow().isoformat(),
        **(extra or {}),
    }
    await cache.set(f"{key_prefix}:{state}", json.dumps(payload), ttl=_OAUTH_STATE_TTL)
    return state


async def pop_oauth_state(
    state: str,
    provider: str,
    key_prefix: str = "oauth_state",
) -> dict:
    """
    Retrieve and delete an OAuth state from Redis.
    Raises ValueError on missing, expired, or provider-mismatched state.
    """
    from app.services.cache import cache
    raw = await cache.get(f"{key_prefix}:{state}")
    await cache.delete(f"{key_prefix}:{state}")
    if not raw:
        raise ValueError("Invalid or expired OAuth state")
    data = json.loads(raw)
    if data.get("provider") != provider:
        raise ValueError("OAuth state provider mismatch")
    return data


async def find_or_create_oauth_user(
    *,
    provider: str,
    provider_id: str,
    email: str,
    name: str,
    avatar_url: str | None = None,
    access_token: str | None = None,
    refresh_token: str | None = None,
) -> dict:
    """
    Find an existing user by provider+provider_id or email.
    If not found, create a new user.
    Returns dict with user info + JWT tokens.
    """
    async with async_session() as session:
        # 1. Try to find by provider + provider_id
        result = await session.execute(
            select(User).where(
                User.provider == provider,
                User.provider_id == provider_id,
            )
        )
        user = result.scalar_one_or_none()

        # 2. If not found, try by email (link accounts)
        if not user and email:
            result = await session.execute(
                select(User).where(User.email == email)
            )
            user = result.scalar_one_or_none()
            # Update existing user with OAuth provider info
            if user:
                user.provider = user.provider or provider
                user.provider_id = user.provider_id or provider_id
                if avatar_url and not user.avatar_url:
                    user.avatar_url = avatar_url

        # 3. Create new user
        if not user:
            user_id = str(uuid.uuid4())
            user = User(
                id=user_id,
                tenant_id="volo-default",
                email=email,
                name=name,
                avatar_url=avatar_url,
                provider=provider,
                provider_id=provider_id,
                role="owner",
            )
            session.add(user)
            await session.flush()

        # 4. Update last_active_at
        user.last_active_at = datetime.utcnow()

        # 5. Upsert integration if we have OAuth tokens
        if access_token:
            int_result = await session.execute(
                select(Integration).where(
                    Integration.user_id == user.id,
                    Integration.type == provider,
                )
            )
            existing_int = int_result.scalar_one_or_none()

            if existing_int:
                existing_int.config = {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                }
                existing_int.status = "connected"
            else:
                session.add(Integration(
                    user_id=user.id,
                    type=provider,
                    category="social" if provider in ("twitter", "discord", "facebook") else "auth",
                    name=provider.title(),
                    status="connected",
                    config={
                        "access_token": access_token,
                        "refresh_token": refresh_token,
                    },
                ))

        await session.commit()

        # Build response
        jwt_access = create_access_token(user.id, user.tenant_id or "volo-default", user.role or "owner")
        jwt_refresh = create_refresh_token(user.id)

        return {
            "user_id": user.id,
            "email": user.email,
            "name": user.name,
            "avatar": user.avatar_url or "",
            "provider": provider,
            "onboarding_completed": bool(getattr(user, 'onboarding_completed', False)),
            "access_token": jwt_access,
            "refresh_token": jwt_refresh,
        }


def build_frontend_redirect(user_data: dict) -> str:
    """Build the frontend redirect URL with auth params."""
    frontend_url = settings.frontend_url.rstrip("/")
    params = {
        "auth_token": user_data["access_token"],
        "provider": user_data["provider"],
        "user_id": user_data["user_id"],
        "name": user_data["name"],
        "email": user_data.get("email", ""),
        "avatar": user_data.get("avatar", ""),
        "onboarding_done": "1" if user_data.get("onboarding_completed") else "0",
    }
    return f"{frontend_url}/?{urlencode(params, quote_via=quote)}"
