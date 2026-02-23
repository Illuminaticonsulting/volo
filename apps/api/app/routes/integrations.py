"""
VOLO — Integrations Route
Handles connecting and managing external service integrations.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class IntegrationConnect(BaseModel):
    type: str  # github, gmail, alpaca, etc.
    credentials: dict  # encrypted credentials
    config: Optional[dict] = {}


class IntegrationStatus(BaseModel):
    id: str
    type: str
    category: str
    name: str
    status: str
    last_sync_at: Optional[str] = None


# Available integration definitions
AVAILABLE_INTEGRATIONS = [
    {
        "type": "github",
        "category": "code",
        "name": "GitHub",
        "description": "Access repositories, PRs, issues, and CI/CD",
        "required_fields": ["access_token"],
        "oauth_supported": True,
    },
    {
        "type": "gmail",
        "category": "communication",
        "name": "Gmail",
        "description": "Read, draft, and send emails. Auto-categorize inbox.",
        "required_fields": ["oauth_token"],
        "oauth_supported": True,
    },
    {
        "type": "google_calendar",
        "category": "communication",
        "name": "Google Calendar",
        "description": "Schedule events, detect conflicts, prepare meeting briefs",
        "required_fields": ["oauth_token"],
        "oauth_supported": True,
    },
    {
        "type": "slack",
        "category": "communication",
        "name": "Slack",
        "description": "Read channels, send messages, summarize threads",
        "required_fields": ["bot_token"],
        "oauth_supported": True,
    },
    {
        "type": "alpaca",
        "category": "finance",
        "name": "Alpaca Trading",
        "description": "Stock trading, portfolio management, market data",
        "required_fields": ["api_key", "secret_key"],
        "oauth_supported": False,
    },
    {
        "type": "coinbase",
        "category": "finance",
        "name": "Coinbase",
        "description": "Crypto trading, wallet management, DeFi access",
        "required_fields": ["api_key", "api_secret"],
        "oauth_supported": True,
    },
    {
        "type": "binance",
        "category": "finance",
        "name": "Binance",
        "description": "Crypto spot & futures trading",
        "required_fields": ["api_key", "api_secret"],
        "oauth_supported": False,
    },
    {
        "type": "plaid",
        "category": "finance",
        "name": "Plaid (Banking)",
        "description": "Connect bank accounts for cash flow tracking and expense categorization",
        "required_fields": ["public_token"],
        "oauth_supported": True,
    },
    {
        "type": "twitter",
        "category": "social",
        "name": "Twitter / X",
        "description": "Post, schedule, monitor mentions and DMs",
        "required_fields": ["bearer_token"],
        "oauth_supported": True,
    },
    {
        "type": "linkedin",
        "category": "social",
        "name": "LinkedIn",
        "description": "Post content, manage connections, inbox management",
        "required_fields": ["oauth_token"],
        "oauth_supported": True,
    },
    {
        "type": "remote_machine",
        "category": "machine",
        "name": "Remote Machine",
        "description": "Execute commands, access files on your computers",
        "required_fields": ["machine_token"],
        "oauth_supported": False,
    },
    {
        "type": "ethereum_wallet",
        "category": "web3",
        "name": "Ethereum Wallet",
        "description": "Track ETH/ERC-20 balances, DeFi positions, NFTs",
        "required_fields": ["wallet_address"],
        "oauth_supported": False,
    },
    {
        "type": "solana_wallet",
        "category": "web3",
        "name": "Solana Wallet",
        "description": "Track SOL/SPL balances, DeFi positions, NFTs",
        "required_fields": ["wallet_address"],
        "oauth_supported": False,
    },
]


@router.get("/integrations")
async def list_integrations():
    """List all available integrations and their connection status."""
    return {
        "available": AVAILABLE_INTEGRATIONS,
        "connected": [],  # TODO: pull from database
    }


@router.post("/integrations/connect")
async def connect_integration(integration: IntegrationConnect):
    """Connect a new integration."""
    # Validate integration type
    valid_types = [i["type"] for i in AVAILABLE_INTEGRATIONS]
    if integration.type not in valid_types:
        return {"error": f"Unknown integration type: {integration.type}"}

    # TODO: Encrypt credentials and store in database
    # TODO: Validate the credentials actually work (test connection)

    return {
        "success": True,
        "integration": {
            "type": integration.type,
            "status": "connected",
            "message": f"{integration.type} connected successfully. Volo now has access.",
        },
    }


@router.delete("/integrations/{integration_id}")
async def disconnect_integration(integration_id: str):
    """Disconnect an integration."""
    # TODO: Remove from database, revoke tokens
    return {
        "success": True,
        "message": f"Integration {integration_id} disconnected.",
    }


@router.post("/integrations/{integration_id}/sync")
async def sync_integration(integration_id: str):
    """Trigger a manual sync for an integration."""
    return {
        "success": True,
        "message": f"Sync started for {integration_id}",
    }
