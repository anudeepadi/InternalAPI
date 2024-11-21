from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uvicorn

from claudesync.configmanager import InMemoryConfigManager
from claudesync.providers.claude_ai import ClaudeAIProvider
from claudesync.exceptions import ProviderError, ConfigurationError

app = FastAPI(title="ClaudeSync API")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Pydantic models for request/response
from pydantic import validator

class LoginRequest(BaseModel):
    session_key: str
    expires: Optional[str] = None  # Optional expiry date
    
    @validator('session_key')
    def validate_session_key(cls, v):
        if not v.startswith('sk-ant-'):
            raise ValueError('Session key must start with sk-ant-')
        return v

    @validator('expires')
    def validate_expires(cls, v):
        if v is None:
            return v
        try:
            # Try to parse the date if provided
            datetime.strptime(v, "%a, %d %b %Y %H:%M:%S %Z")
            return v
        except ValueError:
            raise ValueError('Invalid date format. Use format: Mon, 01 Jan 2025 00:00:00 UTC')

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
    if not provider:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return provider

@app.post("/auth/login", response_model=LoginResponse)
async def login(login_data: LoginRequest):
    global provider
    try:
        config.set("claude_api_url", "https://api.claude.ai/api")
        provider = ClaudeAIProvider(config)
        
        # Set default expiry to 1 year from now if not provided
        if login_data.expires:
            expiry = datetime.strptime(login_data.expires, "%a, %d %b %Y %H:%M:%S %Z")
        else:
            expiry = datetime.now(timezone.utc) + timedelta(days=365)
            login_data.expires = expiry.strftime("%a, %d %b %Y %H:%M:%S UTC")
        
        # Store session key
        config.set_session_key("claude.ai", login_data.session_key, expiry)
        
        # Verify the session key works by making a test request
        try:
            orgs = provider.get_organizations()
            if not orgs:
                raise HTTPException(status_code=401, detail="Invalid session key")
        except ProviderError:
            raise HTTPException(status_code=401, detail="Invalid session key")
        
        return LoginResponse(
            message="Successfully authenticated with claude.ai",
            session_key=login_data.session_key,
            expires=login_data.expires
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/organizations", response_model=List[Organization])
async def get_organizations(provider: ClaudeAIProvider = Depends(get_provider)):
    try:
        orgs = provider.get_organizations()
        return orgs
    except ProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/organizations/{org_id}/projects", response_model=List[Project])
async def get_projects(
    org_id: str,
    include_archived: bool = False,
    provider: ClaudeAIProvider = Depends(get_provider)
):
    try:
        projects = provider.get_projects(org_id, include_archived)
        return projects
    except ProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/organizations/{org_id}/projects")
async def create_project(
    org_id: str,
    project_data: ProjectCreate,
    provider: ClaudeAIProvider = Depends(get_provider)
):
    try:
        project = provider.create_project(
            org_id,
            project_data.name,
            project_data.description
        )
        return project
    except ProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/organizations/{org_id}/chats")
async def create_chat(
    org_id: str,
    chat_data: ChatCreate,
    provider: ClaudeAIProvider = Depends(get_provider)
):
    try:
        chat = provider.create_chat(
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
    provider: ClaudeAIProvider = Depends(get_provider)
):
    try:
        chats = provider.get_chat_conversations(org_id)
        return chats
    except ProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/organizations/{org_id}/chats/{chat_id}")
async def get_chat(
    org_id: str,
    chat_id: str,
    provider: ClaudeAIProvider = Depends(get_provider)
):
    try:
        chat = provider.get_chat_conversation(org_id, chat_id)
        return chat
    except ProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Quick chat without project
@app.post("/organizations/{org_id}/chat")
async def quick_chat(
    org_id: str,
    message: ChatMessage,
    provider: ClaudeAIProvider = Depends(get_provider)
):
    try:
        # Create a new chat first
        chat = provider.create_chat(org_id)
        chat_id = chat["uuid"]
        
        # Then send the message
        async def message_stream():
            for event in provider.send_message(org_id, chat_id, message.prompt, message.timezone):
                yield f"data: {json.dumps(event)}\n\n"
                
        return StreamingResponse(
            message_stream(),
            media_type="text/event-stream"
        )
    except ProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/organizations/{org_id}/chats/{chat_id}/messages")
async def send_message(
    org_id: str,
    chat_id: str,
    message: ChatMessage,
    provider: ClaudeAIProvider = Depends(get_provider)
):
    try:
        # Create StreamingResponse for the message stream
        async def message_stream():
            for event in provider.send_message(org_id, chat_id, message.prompt, message.timezone):
                yield f"data: {json.dumps(event)}\n\n"
                
        return StreamingResponse(
            message_stream(),
            media_type="text/event-stream"
        )
    except ProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/organizations/{org_id}/chats")
async def delete_chats(
    org_id: str,
    chat_ids: List[str],
    provider: ClaudeAIProvider = Depends(get_provider)
):
    try:
        result = provider.delete_chat(org_id, chat_ids)
        return result
    except ProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)