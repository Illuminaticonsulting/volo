"""
VOLO — Agent Orchestrator
The brain of Volo. Routes user intent to specialized sub-agents,
manages tool calls, memory, and multi-step planning.
"""

import os
import json
from typing import AsyncGenerator
from datetime import datetime

from app.agent.tools import ToolRegistry
from app.agent.memory import MemoryManager
from app.agent.prompts import SYSTEM_PROMPT, ONBOARDING_PROMPT


class AgentOrchestrator:
    """
    Core agent that:
    1. Classifies user intent
    2. Retrieves relevant memory/context
    3. Calls the LLM with appropriate tools
    4. Streams response back
    5. Stores new memories from the conversation
    """

    def __init__(self):
        self.tool_registry = ToolRegistry()
        self.memory = MemoryManager()
        self.model = os.getenv("DEFAULT_MODEL", "claude-sonnet-4-20250514")
        self._client = None

    @property
    def client(self):
        """Lazy-initialize the Anthropic client."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(
                    api_key=os.getenv("ANTHROPIC_API_KEY", "")
                )
            except Exception:
                self._client = None
        return self._client

    async def run(
        self,
        message: str,
        conversation_id: str,
        history: list[dict] = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Main agent loop. Processes a user message and yields response chunks.
        """
        history = history or []

        # 1. Retrieve relevant memories
        relevant_memories = await self.memory.search(message)
        memory_context = self._format_memories(relevant_memories)

        # 2. Determine if this is onboarding
        is_onboarding = len(history) <= 2
        system_prompt = ONBOARDING_PROMPT if is_onboarding else SYSTEM_PROMPT

        if memory_context:
            system_prompt += f"\n\n## Your Memory (things you know about this user):\n{memory_context}"

        # 3. Build messages for the LLM
        messages = self._build_messages(history, message)

        # 4. Get available tools
        tools = self.tool_registry.get_tool_definitions()

        # 5. Call LLM and stream response
        if self.client:
            async for chunk in self._call_anthropic(system_prompt, messages, tools):
                yield chunk
        else:
            # Fallback: intelligent response without API key
            async for chunk in self._fallback_response(message, is_onboarding):
                yield chunk

        # 6. Extract and store new memories from this interaction
        # (async background task — don't block the response)
        # await self.memory.extract_and_store(message, response_text)

    async def _call_anthropic(
        self,
        system_prompt: str,
        messages: list[dict],
        tools: list[dict],
    ) -> AsyncGenerator[dict, None]:
        """Call Anthropic API with streaming."""
        try:
            with self.client.messages.stream(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                messages=messages,
                tools=tools if tools else None,
            ) as stream:
                for text in stream.text_stream:
                    yield {"content": text}
        except Exception as e:
            yield {"content": f"\n\n*Error communicating with AI model: {str(e)}*"}

    async def _fallback_response(
        self, message: str, is_onboarding: bool
    ) -> AsyncGenerator[dict, None]:
        """
        Intelligent fallback when no API key is configured.
        Acts as the onboarding agent.
        """
        msg_lower = message.lower()

        if is_onboarding or "get started" in msg_lower or "set up" in msg_lower:
            response = """Welcome to **Volo** — your AI Life Operating System. 🧠

I'm here to be your single point of control for everything: code, trading, communications, and more.

Let's get you set up. I'll ask you a few questions to configure everything:

**1. What's your name?** (so I know what to call you)

**2. What do you primarily do?** For example:
   - 💻 Software development
   - 📈 Trading / investing
   - 🏢 Business management
   - 🎨 Content creation
   - All of the above

**3. Which tools do you use most?** I can connect to:
   - **GitHub** — manage all your code projects
   - **Gmail/Outlook** — email triage and auto-drafts
   - **Google Calendar** — scheduling and meeting prep
   - **Alpaca/Coinbase** — trading and portfolio tracking
   - **Slack/Discord** — messaging
   - **Twitter/LinkedIn** — social media management

Just tell me about yourself and I'll configure everything step by step. No forms, no setup wizards — just a conversation. ✨"""
        elif "github" in msg_lower or "repo" in msg_lower or "code" in msg_lower:
            response = """Great — let's connect your **GitHub** account.

I'll need a **Personal Access Token** to access your repositories. Here's how to create one:

1. Go to [github.com/settings/tokens](https://github.com/settings/tokens)
2. Click **"Generate new token (classic)"**
3. Give it a name like "Volo Agent"
4. Select these scopes: `repo`, `read:org`, `read:user`
5. Generate and paste the token here

Once connected, I'll be able to:
- 📂 See all your repos and understand your codebase
- 🔍 Find shared modules across projects
- 🔄 Review PRs, manage issues, trigger deployments
- 📊 Track project health and tech debt

**Paste your GitHub token when ready** (it will be encrypted and stored securely)."""
        elif "trading" in msg_lower or "portfolio" in msg_lower or "stock" in msg_lower or "crypto" in msg_lower:
            response = """Let's set up your **trading & finance** integrations.

I support these platforms:

**Stocks & Options:**
- 🟢 **Alpaca** — commission-free trading API
- 🔵 **Interactive Brokers** — professional-grade access

**Crypto:**
- 🟡 **Coinbase** — spot + DeFi
- 🟠 **Binance** — spot + futures

**Banking:**
- 🏦 **Plaid** — connect bank accounts for cash flow tracking

**Market Data:**
- 📊 Real-time quotes, screeners, and alerts

Which platform(s) do you use? I'll walk you through connecting each one.

Once set up, I can:
- Show your portfolio in real-time
- Execute trades with your approval
- Alert you on price movements
- Track P&L across all platforms
- Generate tax reports"""
        elif "email" in msg_lower or "calendar" in msg_lower or "gmail" in msg_lower:
            response = """Let's connect your **email and calendar**.

**Email** (choose one):
- 📧 **Gmail** — full inbox management, auto-categorize, draft replies
- 📧 **Outlook** — same capabilities for Microsoft accounts

**Calendar** (choose one):
- 📅 **Google Calendar** — scheduling, conflict detection, meeting prep
- 📅 **Outlook Calendar** — same for Microsoft

Once connected, I'll:
- Triage your inbox (urgent / needs reply / FYI)
- Draft replies in your writing style
- Prepare meeting briefs before each call
- Find open time slots for scheduling
- Track follow-ups ("You said you'd reply to X by Friday")

Want to start with **Gmail** or **Outlook**?"""
        elif "name" in msg_lower or "call me" in msg_lower:
            # Extract name
            response = """Got it! I'll remember that. 

What do you primarily work on? This helps me prioritize which integrations to set up first and how to organize your workspace.

For example:
- If you're a **developer**, I'll prioritize GitHub, CI/CD, and project management
- If you're a **trader**, I'll focus on brokerage connections and market data
- If you're a **business owner**, I'll set up email, calendar, and financial tracking first
- If you're **all of the above** — we'll do it all! 🚀"""
        else:
            response = f"""I hear you! I'm Volo, your AI Life Operating System.

Right now I'm running in **setup mode** — I need an AI model API key to unlock my full capabilities.

**To activate full AI:**
1. Get an API key from [Anthropic](https://console.anthropic.com/) or [OpenAI](https://platform.openai.com/)
2. Add it to your `.env` file:
   ```
   ANTHROPIC_API_KEY=your-key-here
   ```
3. Restart the API server

**Even without an API key, I can still help you:**
- Set up integrations (GitHub, email, trading)
- Configure your preferences
- Walk through the onboarding flow

What would you like to do?"""

        # Stream character by character for a natural effect
        words = response.split(' ')
        chunk_size = 3  # Send 3 words at a time for snappy feel
        for i in range(0, len(words), chunk_size):
            chunk = ' '.join(words[i:i + chunk_size])
            if i > 0:
                chunk = ' ' + chunk
            yield {"content": chunk}

    def _build_messages(self, history: list[dict], current_message: str) -> list[dict]:
        """Build the messages array for the LLM."""
        messages = []

        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": current_message})
        return messages

    def _format_memories(self, memories: list) -> str:
        """Format retrieved memories into context string."""
        if not memories:
            return ""

        lines = []
        for m in memories:
            lines.append(f"- [{m.get('category', 'fact')}] {m.get('content', '')}")
        return "\n".join(lines)
