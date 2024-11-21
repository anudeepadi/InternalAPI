import subprocess
import sys
import os
import signal
import platform
from threading import Thread
from pathlib import Path

def get_npm_path():
    """Get the full path to npm executable"""
    if platform.system() == "Windows":
        npm_path = subprocess.check_output(['where', 'npm'], text=True).strip().split('\n')[0]
    else:
        npm_path = subprocess.check_output(['which', 'npm'], text=True).strip()
    return npm_path

def run_fastapi():
    """Run the FastAPI server"""
    try:
        subprocess.run(
            [sys.executable, "-m", "uvicorn", "api.index:app", "--reload", "--port", "8000"],
            check=True
        )
    except KeyboardInterrupt:
        pass

def run_nextjs():
    """Run the Next.js development server"""
    try:
        # Get npm path
        npm_path = get_npm_path()
        print(f"Using npm from: {npm_path}")
        
        # Use shell=True on Windows
        if platform.system() == "Windows":
            subprocess.run(
                f'"{npm_path}" run dev',
                shell=True,
                check=True
            )
        else:
            subprocess.run(
                [npm_path, "run", "dev"],
                check=True
            )
    except subprocess.CalledProcessError as e:
        print(f"Error running Next.js: {e}")
    except KeyboardInterrupt:
        pass

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print("\nShutting down servers...")
    if platform.system() == "Windows":
        subprocess.run(['taskkill', '/F', '/IM', 'node.exe'], capture_output=True)
    else:
        subprocess.run(['pkill', '-f', 'node'], capture_output=True)
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Start FastAPI in a separate thread
        api_thread = Thread(target=run_fastapi)
        api_thread.daemon = True
        api_thread.start()

        # Run Next.js in the main thread
        run_nextjs()
    except KeyboardInterrupt:
        signal_handler(None, None)