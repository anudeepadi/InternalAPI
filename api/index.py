from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from dotenv import load_dotenv
from pathlib import Path
import os

# Load environment variables from .env.local
env_path = Path('.') / '.env.local'
load_dotenv(dotenv_path=env_path)

from .routes import chat

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include chat routes
app.include_router(chat.router)

@app.get("/api/health")
async def health_check():
    session_key = os.getenv("CLAUDE_SESSION_KEY")
    if not session_key or session_key == "your-session-key-here":
        raise HTTPException(
            status_code=500,
            detail="Claude session key not configured. Please set CLAUDE_SESSION_KEY in .env.local"
        )
    return {
        "status": "healthy",
        "claude_session_key": "configured"
    }

# Handler for AWS Lambda/Vercel
handler = Mangum(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)