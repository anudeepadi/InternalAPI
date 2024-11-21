from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import json
import os
from datetime import datetime, timezone, timedelta

from claudesync.configmanager import InMemoryConfigManager
from claudesync.providers.claude_ai import ClaudeAIProvider
from claudesync.exceptions import ProviderError

router = APIRouter(prefix="/api", tags=["chat"])

# Pydantic models for request validation
class ChatMessage(BaseModel):
    message: str
    timezone: str = "UTC"

class ChatCreate(BaseModel):
    chat_name: str = ""
    project_uuid: Optional[str] = None

# Global config and provider setup
config = InMemoryConfigManager()
config.set("claude_api_url", "https://api.claude.ai/api")

def initialize_provider():
    """Initialize Claude provider with session key from environment"""
    session_key = os.getenv("CLAUDE_SESSION_KEY")
    if not session_key:
        raise HTTPException(status_code=500, detail="Claude session key not configured")
    
    try:
        # Set default expiry to 30 days if not specified
        expiry_str = os.getenv("CLAUDE_SESSION_EXPIRY")
        if expiry_str:
            expiry = datetime.strptime(expiry_str, "%a, %d %b %Y %H:%M:%S %Z")
        else:
            expiry = datetime.now(timezone.utc) + timedelta(days=30)
        
        config.set_session_key("claude.ai", session_key, expiry)
        return ClaudeAIProvider(config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_provider():
    """Dependency to get Claude provider instance"""
    try:
        return initialize_provider()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/organizations")
async def get_organizations(provider: ClaudeAIProvider = Depends(get_provider)):
    """Get list of organizations"""
    try:
        return provider.get_organizations()
    except ProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/organizations/{org_id}/chats")
async def get_chats(
    org_id: str,
    provider: ClaudeAIProvider = Depends(get_provider)
):
    """Get list of chat conversations for an organization"""
    try:
        return provider.get_chat_conversations(org_id)
    except ProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/organizations/{org_id}/chats")
async def create_chat(
    org_id: str,
    chat_data: ChatCreate,
    provider: ClaudeAIProvider = Depends(get_provider)
):
    """Create a new chat conversation"""
    try:
        return provider.create_chat(
            org_id, 
            chat_name=chat_data.chat_name,
            project_uuid=chat_data.project_uuid
        )
    except ProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/organizations/{org_id}/chats/{chat_id}")
async def get_chat(
    org_id: str,
    chat_id: str,
    provider: ClaudeAIProvider = Depends(get_provider)
):
    """Get a specific chat conversation and its messages"""
    try:
        return provider.get_chat_conversation(org_id, chat_id)
    except ProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/organizations/{org_id}/chats")
async def delete_chats(
    org_id: str,
    chat_ids: List[str],
    provider: ClaudeAIProvider = Depends(get_provider)
):
    """Delete one or more chat conversations"""
    try:
        return provider.delete_chat(org_id, chat_ids)
    except ProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/organizations/{org_id}/chat")
async def quick_chat(
    org_id: str,
    message: ChatMessage,
    provider: ClaudeAIProvider = Depends(get_provider)
):
    """Start a new chat and send a message in one request"""
    try:
        # Create a new chat
        chat = provider.create_chat(org_id)
        chat_id = chat["uuid"]
        
        # Stream the response
        async def message_stream():
            for event in provider.send_message(org_id, chat_id, message.message, message.timezone):
                yield f"data: {json.dumps(event)}\n\n"
        
        return StreamingResponse(
            message_stream(),
            media_type="text/event-stream"
        )
    except ProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/organizations/{org_id}/chats/{chat_id}/messages")
async def send_message(
    org_id: str,
    chat_id: str,
    message: ChatMessage,
    provider: ClaudeAIProvider = Depends(get_provider)
):
    """Send a message in an existing chat conversation"""
    try:
        async def message_stream():
            for event in provider.send_message(
                org_id,
                chat_id,
                message.message,
                message.timezone
            ):
                yield f"data: {json.dumps(event)}\n\n"
        
        return StreamingResponse(
            message_stream(),
            media_type="text/event-stream"
        )
    except ProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))