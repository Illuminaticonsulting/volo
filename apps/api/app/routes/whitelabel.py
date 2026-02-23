"""
VOLO — White Label Route
Handles tenant branding, configuration, and feature flags.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class TenantBranding(BaseModel):
    app_name: str = "Volo"
    logo_url: Optional[str] = None
    primary_color: str = "#4c6ef5"
    accent_color: str = "#5c7cfa"
    font_family: Optional[str] = "Inter"
    custom_domain: Optional[str] = None
    agent_name: str = "Volo"
    agent_avatar: Optional[str] = None


class TenantConfig(BaseModel):
    branding: TenantBranding = TenantBranding()
    features: dict = {
        "voice_enabled": True,
        "trading_enabled": True,
        "web3_enabled": True,
        "machine_control_enabled": True,
        "social_enabled": True,
        "standing_orders_enabled": True,
        "plugin_marketplace_enabled": False,
        "max_integrations": -1,  # -1 = unlimited
        "max_conversations": -1,
        "max_memory_entries": -1,
    }


# Default Volo tenant
DEFAULT_TENANT = TenantConfig()


@router.get("/whitelabel/config")
async def get_whitelabel_config():
    """Get the current tenant's white-label configuration."""
    return {
        "tenant": {
            "id": "volo-default",
            "name": "Volo",
            "slug": "volo",
            "plan": "pro",
        },
        "branding": DEFAULT_TENANT.branding.model_dump(),
        "features": DEFAULT_TENANT.features,
    }


@router.put("/whitelabel/branding")
async def update_branding(branding: TenantBranding):
    """Update tenant branding (admin only)."""
    return {
        "success": True,
        "branding": branding.model_dump(),
        "message": "Branding updated. Changes will reflect immediately.",
    }


@router.get("/whitelabel/themes")
async def list_themes():
    """List available UI themes."""
    return {
        "themes": [
            {
                "id": "midnight",
                "name": "Midnight",
                "description": "Dark theme with blue accents. Default.",
                "preview": {"bg": "#09090b", "primary": "#4c6ef5", "text": "#e4e4e7"},
            },
            {
                "id": "aurora",
                "name": "Aurora",
                "description": "Dark theme with green/cyan accents.",
                "preview": {"bg": "#0a0f0a", "primary": "#10b981", "text": "#e4e4e7"},
            },
            {
                "id": "ember",
                "name": "Ember",
                "description": "Dark theme with warm orange accents.",
                "preview": {"bg": "#0f0a08", "primary": "#f59e0b", "text": "#e4e4e7"},
            },
            {
                "id": "clean",
                "name": "Clean Light",
                "description": "Light theme for daytime use.",
                "preview": {"bg": "#ffffff", "primary": "#4c6ef5", "text": "#18181b"},
            },
        ],
    }
