"""
VOLO — Google OAuth & Services Routes
Handles Google sign-in flow and service discovery.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
import httpx

from app.auth import get_current_user, CurrentUser
from app.services.google_auth import google_auth

router = APIRouter()


class GoogleCallbackRequest(BaseModel):
    code: str
    state: Optional[str] = None


@router.get("/google/auth-url")
async def get_google_auth_url():
    """Get the Google OAuth consent URL to redirect the user to."""
    url = google_auth.get_auth_url()
    return {"auth_url": url}


@router.post("/google/callback")
async def google_callback(body: GoogleCallbackRequest, current_user: CurrentUser = Depends(get_current_user)):
    """Exchange Google OAuth code for tokens and discover services."""
    try:
        result = await google_auth.exchange_code(body.code, user_id=current_user.user_id)
        return {
            "success": True,
            "user_id": result["user_id"],
            "profile": result["profile"],
            "services": result["services"],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth exchange failed: {str(e)}")


@router.get("/google/services")
async def get_google_services(current_user: CurrentUser = Depends(get_current_user)):
    """Get discovered Google services for the authenticated user."""
    # Try sync cache first, then async DB load, then token refresh
    token = google_auth.get_access_token(current_user.user_id)
    if not token:
        token_data = await google_auth._load_tokens(current_user.user_id)
        if token_data:
            token = token_data.get("access_token")
    if not token:
        token = await google_auth.refresh_token(current_user.user_id)

    if token:
        services = await google_auth.discover_services(token)
        # If all services failed (token expired), try one refresh
        if all(s.get("status") != "active" for s in services):
            refreshed = await google_auth.refresh_token(current_user.user_id)
            if refreshed:
                services = await google_auth.discover_services(refreshed)
        return {"services": services, "connected": True}

    # Not connected — return service list as disconnected (no demo badge)
    return {
        "connected": False,
        "services": [
            {"id": "gmail", "name": "Gmail", "icon": "mail", "connected": False, "status": "disconnected"},
            {"id": "calendar", "name": "Google Calendar", "icon": "calendar", "connected": False, "status": "disconnected"},
            {"id": "drive", "name": "Google Drive", "icon": "cloud", "connected": False, "status": "disconnected"},
            {"id": "youtube", "name": "YouTube", "icon": "video", "connected": False, "status": "disconnected"},
            {"id": "contacts", "name": "Google Contacts", "icon": "contacts", "connected": False, "status": "disconnected"},
            {"id": "photos", "name": "Google Photos", "icon": "image", "connected": False, "status": "disconnected"},
            {"id": "tasks", "name": "Google Tasks", "icon": "tasks", "connected": False, "status": "disconnected"},
            {"id": "fitness", "name": "Google Fit", "icon": "fitness", "connected": False, "status": "disconnected"},
        ],
    }


@router.get("/google/profile")
async def get_google_profile(current_user: CurrentUser = Depends(get_current_user)):
    """Get stored Google profile for the authenticated user."""
    profile = google_auth.get_user_profile(current_user.user_id)
    if profile:
        return profile

    # Try async load from DB
    token_data = await google_auth._load_tokens(current_user.user_id)
    if token_data and token_data.get("profile"):
        return token_data["profile"]

    # Not connected — return empty so frontend knows
    return {"name": None, "email": None, "picture": None}


@router.get("/google/gmail/messages")
async def get_gmail_messages(
    current_user: CurrentUser = Depends(get_current_user),
    max_results: int = Query(default=20, le=50),
):
    """Fetch recent Gmail messages for the authenticated user."""
    token = await _get_valid_token(current_user.user_id)
    if not token:
        raise HTTPException(status_code=401, detail="Google account not connected. Please connect via Google Services.")

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Get message list
        resp = await client.get(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages?maxResults={max_results}&labelIds=INBOX",
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="Failed to fetch Gmail messages")

        message_list = resp.json().get("messages", [])
        total = resp.json().get("resultSizeEstimate", 0)

        # Fetch each message's metadata
        emails = []
        for msg in message_list[:max_results]:
            msg_resp = await client.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg['id']}?format=metadata&metadataHeaders=Subject&metadataHeaders=From&metadataHeaders=Date",
                headers={"Authorization": f"Bearer {token}"},
            )
            if msg_resp.status_code == 200:
                msg_data = msg_resp.json()
                headers = {h["name"].lower(): h["value"] for h in msg_data.get("payload", {}).get("headers", [])}
                emails.append({
                    "id": msg_data["id"],
                    "thread_id": msg_data.get("threadId"),
                    "subject": headers.get("subject", "(no subject)"),
                    "from": headers.get("from", ""),
                    "date": headers.get("date", ""),
                    "snippet": msg_data.get("snippet", ""),
                    "unread": "UNREAD" in msg_data.get("labelIds", []),
                })

    # Get unread count
    unread_count = sum(1 for e in emails if e.get("unread"))

    return {"emails": emails, "total": total, "unread_count": unread_count}


@router.get("/google/calendar/events")
async def get_calendar_events(
    current_user: CurrentUser = Depends(get_current_user),
    max_results: int = Query(default=10, le=50),
):
    """Fetch upcoming calendar events for the authenticated user."""
    token = await _get_valid_token(current_user.user_id)
    if not token:
        raise HTTPException(status_code=401, detail="Google account not connected. Please connect via Google Services.")

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            params={
                "maxResults": max_results,
                "timeMin": now,
                "singleEvents": "true",
                "orderBy": "startTime",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="Failed to fetch calendar events")

        data = resp.json()
        events = []
        for item in data.get("items", []):
            start = item.get("start", {})
            end = item.get("end", {})
            events.append({
                "id": item.get("id"),
                "summary": item.get("summary", "(No title)"),
                "description": item.get("description", ""),
                "start": start.get("dateTime") or start.get("date"),
                "end": end.get("dateTime") or end.get("date"),
                "location": item.get("location", ""),
                "status": item.get("status", "confirmed"),
                "html_link": item.get("htmlLink", ""),
            })

    return {"events": events, "count": len(events)}


async def _get_valid_token(user_id: str) -> Optional[str]:
    """Get a valid Google access token, refreshing if needed."""
    token = google_auth.get_access_token(user_id)
    if not token:
        token_data = await google_auth._load_tokens(user_id)
        if token_data:
            token = token_data.get("access_token")
    if not token:
        token = await google_auth.refresh_token(user_id)
    return token
