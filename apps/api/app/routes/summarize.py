"""
VOLO — AI Summarize Routes
Generic summarization endpoint for any content (emails, messages, posts, articles).
"""

import os
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from app.auth import get_current_user, CurrentUser

logger = logging.getLogger("volo.summarize")
router = APIRouter()


class SummarizeRequest(BaseModel):
    content: str
    content_type: Optional[str] = "general"  # email, message, post, article, thread, general
    style: Optional[str] = "concise"  # concise, detailed, bullet_points, action_items


@router.post("/ai/summarize")
async def summarize_content(
    body: SummarizeRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Summarize any content using AI."""
    if not body.content.strip():
        return {"summary": "", "error": "No content provided"}

    type_instructions = {
        "email": "Summarize this email. Highlight the sender's key requests, deadlines, and action items.",
        "message": "Summarize this conversation/message thread. Highlight the main topics discussed and any decisions made.",
        "post": "Summarize this social media post/thread. Capture the main point and any notable reactions.",
        "article": "Summarize this article. Provide the key arguments, findings, and conclusions.",
        "thread": "Summarize this message thread/conversation. Identify the main topics and outcomes.",
        "general": "Summarize the following content clearly and concisely.",
    }

    style_instructions = {
        "concise": "Keep it to 2-3 sentences.",
        "detailed": "Provide a thorough summary with key details.",
        "bullet_points": "Format as a bulleted list of key points.",
        "action_items": "Extract action items and next steps as a checklist.",
    }

    prompt = f"""{type_instructions.get(body.content_type, type_instructions['general'])}
{style_instructions.get(body.style, style_instructions['concise'])}

Content:
{body.content[:6000]}"""

    try:
        import anthropic

        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            # Try OpenAI fallback
            import openai

            openai_key = os.getenv("OPENAI_API_KEY", "")
            if not openai_key:
                return {
                    "summary": _fallback_summary(body.content, body.content_type),
                    "model": "fallback",
                }

            client = openai.OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=512,
            )
            summary = response.choices[0].message.content
            return {"summary": summary, "model": "gpt-4o-mini"}

        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        summary = msg.content[0].text
        return {"summary": summary, "model": "claude-sonnet"}

    except Exception as e:
        logger.exception("Summarize error")
        return {
            "summary": _fallback_summary(body.content, body.content_type),
            "model": "fallback",
            "error": str(e),
        }


def _fallback_summary(content: str, content_type: str) -> str:
    """Generate a basic extractive summary when no AI API is available."""
    sentences = content.replace("\n", " ").split(". ")
    if len(sentences) <= 3:
        return content[:500]
    # Take first and last meaningful sentences
    summary_parts = sentences[:2] + sentences[-1:]
    return ". ".join(s.strip() for s in summary_parts if s.strip())[:500] + "..."
