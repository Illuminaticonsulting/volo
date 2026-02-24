"""
VOLO — Unified Social Feed Routes
Aggregated social media from Twitter, Instagram, LinkedIn, Reddit, TikTok, Facebook.
"""

from fastapi import APIRouter, Query, Depends
from typing import Optional

from app.auth import get_current_user, CurrentUser
from app.services.social_feed import SocialFeedService

router = APIRouter()
social_feed = SocialFeedService()


@router.get("/social/feed")
async def get_unified_feed(
    platforms: Optional[str] = Query(None, description="Comma-separated platform list"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get unified social feed from all connected platforms."""
    platform_list = platforms.split(",") if platforms else None
    posts = await social_feed.get_unified_feed(platform_list, user_id=current_user.user_id)
    return {
        "posts": posts,
        "total": len(posts),
        "platforms": await social_feed.get_connected_platforms(current_user.user_id),
    }


@router.get("/social/feed/{platform}")
async def get_platform_feed(
    platform: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get feed from a specific social platform."""
    fetchers = {
        "twitter": lambda: social_feed.twitter_timeline(user_id=current_user.user_id),
        "instagram": lambda: social_feed.instagram_feed(user_id=current_user.user_id),
        "linkedin": lambda: social_feed.linkedin_feed(user_id=current_user.user_id),
        "reddit": lambda: social_feed.reddit_feed(user_id=current_user.user_id),
        "tiktok": lambda: social_feed.tiktok_feed(user_id=current_user.user_id),
        "facebook": lambda: social_feed.facebook_feed(user_id=current_user.user_id),
    }

    fetcher = fetchers.get(platform)
    if not fetcher:
        return {"error": f"Unknown platform: {platform}", "posts": []}

    posts = await fetcher()
    return {"platform": platform, "posts": posts, "total": len(posts)}


@router.get("/social/platforms")
async def get_social_platforms(current_user: CurrentUser = Depends(get_current_user)):
    """Get list of social platforms and their connection status."""
    return {"platforms": await social_feed.get_connected_platforms(current_user.user_id)}
