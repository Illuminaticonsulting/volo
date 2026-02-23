"""
VOLO — Onboarding Route
Handles the conversational onboarding flow.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class OnboardingStep(BaseModel):
    step: int
    data: dict


class OnboardingStatus(BaseModel):
    completed: bool
    current_step: int
    steps_total: int = 5
    collected_data: dict = {}


@router.get("/onboarding/status")
async def get_onboarding_status():
    """Get current onboarding status for the user."""
    return OnboardingStatus(
        completed=False,
        current_step=0,
        steps_total=5,
        collected_data={},
    )


@router.post("/onboarding/step")
async def submit_onboarding_step(step: OnboardingStep):
    """Submit a step in the onboarding process."""
    # The onboarding is primarily conversational (through the chat),
    # but this endpoint handles structured data collection
    return {
        "success": True,
        "step": step.step,
        "next_step": step.step + 1,
        "message": "Step completed. Continue chatting with Volo to set up more.",
    }


@router.post("/onboarding/complete")
async def complete_onboarding():
    """Mark onboarding as complete."""
    return {
        "success": True,
        "message": "Welcome to Volo! Your agent is fully configured and ready.",
    }
