"""
VOLO — YouTube Service
Fetch video metadata, transcripts, and generate AI summaries.
"""

import re
import httpx
from typing import Optional


class YouTubeService:
    """YouTube data + AI summary service."""

    def __init__(self, access_token: str = ""):
        self.access_token = access_token
        self.headers = {"Authorization": f"Bearer {access_token}"} if access_token else {}

    def _extract_video_id(self, url_or_id: str) -> str:
        """Extract video ID from various YouTube URL formats."""
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/shorts/)([a-zA-Z0-9_-]{11})',
            r'^([a-zA-Z0-9_-]{11})$',
        ]
        for pattern in patterns:
            match = re.search(pattern, url_or_id)
            if match:
                return match.group(1)
        return url_or_id

    async def get_video_info(self, url_or_id: str) -> dict:
        """Get video metadata."""
        video_id = self._extract_video_id(url_or_id)
        async with httpx.AsyncClient() as client:
            # Try YouTube Data API if we have auth
            if self.access_token:
                resp = await client.get(
                    f"https://www.googleapis.com/youtube/v3/videos"
                    f"?part=snippet,statistics,contentDetails&id={video_id}",
                    headers=self.headers,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("items"):
                        item = data["items"][0]
                        snippet = item["snippet"]
                        stats = item.get("statistics", {})
                        return {
                            "id": video_id,
                            "title": snippet.get("title", ""),
                            "channel": snippet.get("channelTitle", ""),
                            "description": snippet.get("description", ""),
                            "published_at": snippet.get("publishedAt", ""),
                            "duration": item.get("contentDetails", {}).get("duration", ""),
                            "views": int(stats.get("viewCount", 0)),
                            "likes": int(stats.get("likeCount", 0)),
                            "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
                            "url": f"https://youtube.com/watch?v={video_id}",
                        }

            # Fallback: return basic info
            return {
                "id": video_id,
                "title": f"Video {video_id}",
                "url": f"https://youtube.com/watch?v={video_id}",
                "thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
            }

    async def get_transcript(self, url_or_id: str) -> Optional[str]:
        """Get video transcript/captions via youtube-transcript-api (no auth required)."""
        import asyncio
        from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled

        video_id = self._extract_video_id(url_or_id)

        try:
            # Run the synchronous library in a thread so we don't block the event loop
            transcript_list = await asyncio.to_thread(
                YouTubeTranscriptApi.get_transcript, video_id, languages=["en", "en-US", "en-GB"]
            )
            return " ".join(part["text"] for part in transcript_list)
        except (NoTranscriptFound, TranscriptsDisabled):
            pass
        except Exception:
            pass

        # Fallback: try any available language
        try:
            transcripts = await asyncio.to_thread(YouTubeTranscriptApi.list_transcripts, video_id)
            transcript = await asyncio.to_thread(transcripts.find_transcript, ["en"])
            fetched = await asyncio.to_thread(transcript.fetch)
            return " ".join(part["text"] for part in fetched)
        except Exception:
            pass

        return None

    async def search_videos(self, query: str, max_results: int = 10) -> list[dict]:
        """Search YouTube videos."""
        if not self.access_token:
            return []

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://www.googleapis.com/youtube/v3/search"
                f"?part=snippet&q={query}&maxResults={max_results}&type=video",
                headers=self.headers,
            )
            if resp.status_code == 200:
                data = resp.json()
                return [
                    {
                        "id": item["id"]["videoId"],
                        "title": item["snippet"]["title"],
                        "channel": item["snippet"]["channelTitle"],
                        "thumbnail": item["snippet"]["thumbnails"]["high"]["url"],
                        "published_at": item["snippet"]["publishedAt"],
                        "url": f"https://youtube.com/watch?v={item['id']['videoId']}",
                    }
                    for item in data.get("items", [])
                ]
        return []

    async def get_subscriptions(self, max_results: int = 50) -> list[dict]:
        """Get user's YouTube subscriptions."""
        if not self.access_token:
            return []

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://www.googleapis.com/youtube/v3/subscriptions"
                f"?part=snippet&mine=true&maxResults={max_results}",
                headers=self.headers,
            )
            if resp.status_code == 200:
                data = resp.json()
                return [
                    {
                        "channel_id": item["snippet"]["resourceId"]["channelId"],
                        "title": item["snippet"]["title"],
                        "thumbnail": item["snippet"]["thumbnails"]["default"]["url"],
                    }
                    for item in data.get("items", [])
                ]
        return []

    async def get_watch_history(self, max_results: int = 20) -> list[dict]:
        """Get recent watch history via liked/uploaded playlists."""
        if not self.access_token:
            return []

        async with httpx.AsyncClient() as client:
            # Get liked videos as proxy for activity
            resp = await client.get(
                f"https://www.googleapis.com/youtube/v3/videos"
                f"?part=snippet&myRating=like&maxResults={max_results}",
                headers=self.headers,
            )
            if resp.status_code == 200:
                data = resp.json()
                return [
                    {
                        "id": item["id"],
                        "title": item["snippet"]["title"],
                        "channel": item["snippet"]["channelTitle"],
                        "thumbnail": item["snippet"]["thumbnails"]["high"]["url"],
                        "url": f"https://youtube.com/watch?v={item['id']}",
                    }
                    for item in data.get("items", [])
                ]
        return []
