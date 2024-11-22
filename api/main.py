from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, validator
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import uvicorn
import json
import asyncio

from claudesync.configmanager import InMemoryConfigManager
from claudesync.providers.claude_ai import ClaudeAIProvider
from claudesync.exceptions import ProviderError, ConfigurationError

app = FastAPI(title="ClaudeSync API")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Pydantic models
class LoginRequest(BaseModel):
    session_key: str
    expires: Optional[str] = None
    
    @validator('session_key')
    def validate_session_key(cls, v):
        if not v.startswith('sk-ant-'):
            raise ValueError('Session key must start with sk-ant-')
        return v

class LoginResponse(BaseModel):
    message: str
    session_key: str
    expires: str

class Organization(BaseModel):
    id: str
    name: str

class Project(BaseModel):
    id: str
    name: str
    archived_at: Optional[str] = None

class ProjectCreate(BaseModel):
    name: str
    description: str = ""

class ChatMessage(BaseModel):
    prompt: str
    timezone: str = "UTC"

class ChatCreate(BaseModel):
    chat_name: str = ""
    project_uuid: Optional[str] = None

# Global config and provider instances
config = InMemoryConfigManager()
provider = None

def get_provider():
    global provider
    if not provider:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return provider

async def stream_chat_response(org_id: str, chat_id: str, message: ChatMessage, provider: ClaudeAIProvider):
    try:
        async def generate():
            for event in provider.send_message(org_id, chat_id, message.prompt, message.timezone):
                if isinstance(event, dict):
                    yield f"data: {json.dumps(event)}\n\n"
                else:
                    yield f"data: {json.dumps({'text': str(event)})}\n\n"
            yield "data: [DONE]\n\n"
    
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/auth/login", response_model=LoginResponse)
async def login(login_data: LoginRequest):
    global provider
    try:
        config.set("claude_api_url", "https://api.claude.ai/api")
        provider = ClaudeAIProvider(config)
        
        expiry = datetime.now(timezone.utc) + timedelta(days=365) if not login_data.expires else \
                datetime.strptime(login_data.expires, "%a, %d %b %Y %H:%M:%S %Z")
        
        config.set_session_key("claude.ai", login_data.session_key, expiry)
        
        # Verify the session key
        try:
            orgs = provider.get_organizations()
            if not orgs:
                raise HTTPException(status_code=401, detail="Invalid session key")
        except ProviderError:
            raise HTTPException(status_code=401, detail="Invalid session key")
        
        return LoginResponse(
            message="Successfully authenticated with claude.ai",
            session_key=login_data.session_key,
            expires=expiry.strftime("%a, %d %b %Y %H:%M:%S UTC")
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/organizations")
async def get_organizations(current_provider: ClaudeAIProvider = Depends(get_provider)):
    try:
        orgs = current_provider.get_organizations()
        return orgs
    except ProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/organizations/{org_id}/projects")
async def get_projects(
    org_id: str,
    include_archived: bool = False,
    current_provider: ClaudeAIProvider = Depends(get_provider)
):
    try:
        projects = current_provider.get_projects(org_id, include_archived)
        return projects
    except ProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/organizations/{org_id}/chats")
async def create_chat(
    org_id: str,
    chat_data: ChatCreate,
    current_provider: ClaudeAIProvider = Depends(get_provider)
):
    try:
        chat = current_provider.create_chat(
            org_id,
            chat_data.chat_name,
            chat_data.project_uuid
        )
        return chat
    except ProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/organizations/{org_id}/chats")
async def get_chats(
    org_id: str,
    current_provider: ClaudeAIProvider = Depends(get_provider)
):
    try:
        chats = current_provider.get_chat_conversations(org_id)
        return chats
    except ProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/organizations/{org_id}/chat")
async def quick_chat(
    org_id: str,
    message: ChatMessage,
    current_provider: ClaudeAIProvider = Depends(get_provider)
):
    try:
        # Create a new chat
        chat = current_provider.create_chat(org_id)
        if not chat:
            raise HTTPException(status_code=500, detail="Failed to create chat")
        
        chat_id = chat["uuid"]
        return await stream_chat_response(org_id, chat_id, message, current_provider)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/organizations/{org_id}/chats/{chat_id}/messages")
async def send_message(
    org_id: str,
    chat_id: str,
    message: ChatMessage,
    current_provider: ClaudeAIProvider = Depends(get_provider)
):
    return await stream_chat_response(org_id, chat_id, message, current_provider)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)