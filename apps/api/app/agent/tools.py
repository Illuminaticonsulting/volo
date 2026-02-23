"""
VOLO — Tool Registry
Defines all tools available to the agent.
Each tool is a capability the agent can invoke during conversation.
"""

from typing import Any


class Tool:
    """Base class for agent tools."""

    def __init__(self, name: str, description: str, parameters: dict, category: str):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.category = category

    def to_anthropic_format(self) -> dict:
        """Convert to Anthropic tool format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": self.parameters,
                "required": [k for k, v in self.parameters.items() if v.get("required", False)],
            },
        }

    async def execute(self, **kwargs) -> Any:
        """Execute the tool. Override in subclasses."""
        raise NotImplementedError


class ToolRegistry:
    """Registry of all available tools."""

    def __init__(self):
        self.tools: dict[str, Tool] = {}
        self._register_builtin_tools()

    def register(self, tool: Tool):
        """Register a new tool."""
        self.tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self.tools.get(name)

    def get_tool_definitions(self) -> list[dict]:
        """Get all tool definitions for the LLM."""
        return [tool.to_anthropic_format() for tool in self.tools.values()]

    async def execute(self, name: str, **kwargs) -> Any:
        """Execute a tool by name."""
        tool = self.get(name)
        if not tool:
            return {"error": f"Tool '{name}' not found"}
        try:
            return await tool.execute(**kwargs)
        except Exception as e:
            return {"error": str(e)}

    def _register_builtin_tools(self):
        """Register all built-in tools."""

        # ---- Memory Tools ----
        self.register(Tool(
            name="store_memory",
            description="Store a fact, preference, or piece of information about the user for future reference. Use this when the user shares something you should remember.",
            parameters={
                "category": {
                    "type": "string",
                    "enum": ["fact", "preference", "relationship", "project", "decision", "goal"],
                    "description": "Category of the memory",
                    "required": True,
                },
                "content": {
                    "type": "string",
                    "description": "The information to remember",
                    "required": True,
                },
                "source": {
                    "type": "string",
                    "description": "Where this information came from (e.g., 'user told me', 'inferred from conversation')",
                },
            },
            category="memory",
        ))

        self.register(Tool(
            name="search_memory",
            description="Search your memory for information about the user, their projects, preferences, or past decisions.",
            parameters={
                "query": {
                    "type": "string",
                    "description": "What to search for in memory",
                    "required": True,
                },
            },
            category="memory",
        ))

        # ---- GitHub Tools ----
        self.register(Tool(
            name="github_list_repos",
            description="List all GitHub repositories for the connected user. Shows repo name, language, description, and last updated time.",
            parameters={
                "sort": {
                    "type": "string",
                    "enum": ["updated", "created", "pushed", "name"],
                    "description": "How to sort the repositories",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of repos to return",
                },
            },
            category="code",
        ))

        self.register(Tool(
            name="github_get_repo",
            description="Get detailed information about a specific GitHub repository including README, file tree, and recent activity.",
            parameters={
                "repo": {
                    "type": "string",
                    "description": "Repository name in 'owner/repo' format",
                    "required": True,
                },
            },
            category="code",
        ))

        self.register(Tool(
            name="github_list_prs",
            description="List pull requests for a repository.",
            parameters={
                "repo": {
                    "type": "string",
                    "description": "Repository name in 'owner/repo' format",
                    "required": True,
                },
                "state": {
                    "type": "string",
                    "enum": ["open", "closed", "all"],
                    "description": "Filter by PR state",
                },
            },
            category="code",
        ))

        # ---- Email Tools ----
        self.register(Tool(
            name="email_list_inbox",
            description="List recent emails from the user's inbox. Can filter by read/unread, category, or sender.",
            parameters={
                "filter": {
                    "type": "string",
                    "enum": ["all", "unread", "important", "needs_reply"],
                    "description": "Filter type",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of emails to return",
                },
            },
            category="communication",
        ))

        self.register(Tool(
            name="email_draft",
            description="Draft an email for the user to review before sending. Never send without explicit approval.",
            parameters={
                "to": {
                    "type": "string",
                    "description": "Recipient email address",
                    "required": True,
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject line",
                    "required": True,
                },
                "body": {
                    "type": "string",
                    "description": "Email body content",
                    "required": True,
                },
            },
            category="communication",
        ))

        # ---- Calendar Tools ----
        self.register(Tool(
            name="calendar_list_events",
            description="List upcoming calendar events.",
            parameters={
                "days": {
                    "type": "integer",
                    "description": "Number of days ahead to look (default 7)",
                },
            },
            category="communication",
        ))

        self.register(Tool(
            name="calendar_schedule",
            description="Schedule a new calendar event. Checks for conflicts automatically.",
            parameters={
                "title": {
                    "type": "string",
                    "description": "Event title",
                    "required": True,
                },
                "datetime": {
                    "type": "string",
                    "description": "Event date/time in ISO format",
                    "required": True,
                },
                "duration_minutes": {
                    "type": "integer",
                    "description": "Duration in minutes",
                    "required": True,
                },
                "attendees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of attendee email addresses",
                },
            },
            category="communication",
        ))

        # ---- Trading Tools ----
        self.register(Tool(
            name="trading_portfolio",
            description="Get the user's current trading portfolio — positions, P&L, allocation.",
            parameters={
                "account": {
                    "type": "string",
                    "enum": ["all", "stocks", "crypto"],
                    "description": "Which account to show",
                },
            },
            category="finance",
        ))

        self.register(Tool(
            name="trading_quote",
            description="Get a real-time quote for a stock or cryptocurrency.",
            parameters={
                "symbol": {
                    "type": "string",
                    "description": "Ticker symbol (e.g., AAPL, BTC-USD)",
                    "required": True,
                },
            },
            category="finance",
        ))

        self.register(Tool(
            name="trading_place_order",
            description="Place a trading order. ALWAYS requires user approval before execution.",
            parameters={
                "symbol": {
                    "type": "string",
                    "description": "Ticker symbol",
                    "required": True,
                },
                "side": {
                    "type": "string",
                    "enum": ["buy", "sell"],
                    "required": True,
                },
                "quantity": {
                    "type": "number",
                    "description": "Number of shares/units",
                    "required": True,
                },
                "order_type": {
                    "type": "string",
                    "enum": ["market", "limit", "stop", "stop_limit"],
                    "description": "Order type",
                    "required": True,
                },
                "limit_price": {
                    "type": "number",
                    "description": "Limit price (required for limit orders)",
                },
            },
            category="finance",
        ))

        # ---- Machine Control Tools ----
        self.register(Tool(
            name="machine_run_command",
            description="Execute a shell command on the user's connected remote machine. Use with caution.",
            parameters={
                "command": {
                    "type": "string",
                    "description": "Shell command to execute",
                    "required": True,
                },
                "machine_id": {
                    "type": "string",
                    "description": "ID of the connected machine (default: primary)",
                },
            },
            category="machine",
        ))

        self.register(Tool(
            name="machine_list_files",
            description="List files in a directory on the user's connected machine.",
            parameters={
                "path": {
                    "type": "string",
                    "description": "Directory path to list",
                    "required": True,
                },
            },
            category="machine",
        ))

        self.register(Tool(
            name="machine_read_file",
            description="Read a file from the user's connected machine.",
            parameters={
                "path": {
                    "type": "string",
                    "description": "File path to read",
                    "required": True,
                },
            },
            category="machine",
        ))

        # ---- Web3 Tools ----
        self.register(Tool(
            name="web3_wallet_balance",
            description="Get the balance of a connected crypto wallet across all tokens.",
            parameters={
                "chain": {
                    "type": "string",
                    "enum": ["ethereum", "solana", "polygon", "arbitrum", "base"],
                    "description": "Blockchain network",
                    "required": True,
                },
            },
            category="web3",
        ))

        self.register(Tool(
            name="web3_defi_positions",
            description="Get the user's DeFi positions — lending, borrowing, LP positions, yields.",
            parameters={
                "protocol": {
                    "type": "string",
                    "description": "Specific protocol (e.g., 'aave', 'uniswap') or 'all'",
                },
            },
            category="web3",
        ))

        self.register(Tool(
            name="web3_gas_price",
            description="Get current gas prices for a blockchain network.",
            parameters={
                "chain": {
                    "type": "string",
                    "enum": ["ethereum", "polygon", "arbitrum", "base"],
                    "description": "Blockchain network",
                    "required": True,
                },
            },
            category="web3",
        ))
