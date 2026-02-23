"""
VOLO — AI Life Operating System
Main FastAPI Application
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from app.routes import chat, integrations, memory, onboarding, health, whitelabel
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    print("🚀 Volo API starting up...")
    await init_db()
    print("✅ Database initialized")
    print("🧠 Agent orchestrator ready")
    yield
    print("👋 Volo API shutting down...")


app = FastAPI(
    title="Volo API",
    description="AI Life Operating System — One agent, total control.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_URL", "http://localhost:3000"),
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(health.router, tags=["Health"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(onboarding.router, prefix="/api", tags=["Onboarding"])
app.include_router(integrations.router, prefix="/api", tags=["Integrations"])
app.include_router(memory.router, prefix="/api", tags=["Memory"])
app.include_router(whitelabel.router, prefix="/api", tags=["White Label"])


@app.get("/")
async def root():
    return {
        "name": "Volo API",
        "version": "0.1.0",
        "status": "operational",
        "agent": "ready",
    }
