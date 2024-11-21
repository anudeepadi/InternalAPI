from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import os
import json
from fastapi.responses import StreamingResponse

from claudesync.configmanager import InMemoryConfigManager
from claudesync.providers.claude_ai import ClaudeAIProvider
from claudesync.exceptions import ProviderError

app = FastAPI(title="ClaudeSync API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this with your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API key header scheme
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

# Load environment variables
API_KEY = os.getenv("API_KEY")
DEFAULT_SESSION_KEY = os.getenv("CLAUDE_SESSION_KEY")
DEFAULT_SESSION_EXPIRY = os.getenv("CLAUDE_SESSION_EXPIRY")

# Pydantic models for request validation
class ChatMessage(BaseModel):
    message: str
    timezone: str = "UTC"

class ChatCreate(BaseModel):
    chat_name: str = ""
    project_uuid: Optional[str] = None

# Authentication dependency
async def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )
    return api_key

# Provider instance management
def get_provider():
    """Initialize Claude provider with session key from environment"""
    config = InMemoryConfigManager()
    config.set("claude_api_url", "https://api.claude.ai/api")
    
    # Use environment variables for session key if not provided
    session_key = DEFAULT_SESSION_KEY
    if not session_key:
        raise HTTPException(status_code=401, detail="Claude session key not configured")
    
    # Parse expiry date or use default
    try:
        if DEFAULT_SESSION_EXPIRY:
            expiry = datetime.strptime(DEFAULT_SESSION_EXPIRY, "%a, %d %b %Y %H:%M:%S %Z")
        else:
            expiry = datetime.now(timezone.utc) + timedelta(days=365)
    except ValueError:
        expiry = datetime.now(timezone.utc) + timedelta(days=365)
    
    config.set_session_key("claude.ai", session_key, expiry)
    return ClaudeAIProvider(config)

@app.get("/api/organizations", response_model=List[Organization])
async def get_organizations(
    api_key: str = Depends(verify_api_key)
):
    """Get list of organizations"""
    try:
        provider = get_provider()
        orgs = provider.get_organizations()
        return orgs
    except ProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/organizations/{org_id}/projects", response_model=List[Project])
async def get_projects(
    org_id: str,
    include_archived: bool = False,
    api_key: str = Depends(verify_api_key)
):
    """Get list of projects"""
    try:
        provider = get_provider()
        projects = provider.get_projects(org_id, include_archived)
        return projects
    except ProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/organizations/{org_id}/chats")
async def get_chats(
    org_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get list of chat conversations"""
    try:
        provider = get_provider()
        chats = provider.get_chat_conversations(org_id)
        return chats
    except ProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/organizations/{org_id}/chat")
async def quick_chat(
    org_id: str,
    message: ChatMessage,
    api_key: str = Depends(verify_api_key)
):
    """Start a new chat and send a message"""
    try:
        provider = get_provider()
        # Create a new chat
        chat = provider.create_chat(org_id)
        chat_id = chat["uuid"]
        
        # Stream the response
        async def message_stream():
            for event in provider.send_message(org_id, chat_id, message.prompt, message.timezone):
                yield f"data: {json.dumps(event)}\n\n"
                
        return StreamingResponse(
            message_stream(),
            media_type="text/event-stream"
        )
    except ProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))