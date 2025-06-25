# app/main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Dict
import json
import os
import datetime
from dotenv import load_dotenv # Import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import Akashvani's LLM logic
# AKASHVANI_USERNAME is now retrieved here as well to ensure consistency
# in prefix checking and message creation.
from app.akashvani_llm import call_llm_for_akashvani

# --- Configuration (Loaded from .env with defaults) ---
AKASHVANI_USERNAME = os.getenv("AKASHVANI_USERNAME", "Akashvani")
AKASHVANI_SHORTHAND = os.getenv("AKASHVANI_SHORTHAND", "@av") # New: Load shorthand from .env

app = FastAPI()

# Get the directory of the current file (main.py)
current_dir = os.path.dirname(os.path.abspath(__file__))
# Construct the path to the static directory, assuming it's sibling to 'app'
static_dir = os.path.join(current_dir, "..", "static")

# Mount a directory for static files (our HTML, CSS, JS)
# Ensure that your HTML file (e.g., index.html) is in a directory named 'static'
# This server expects the `index.html` to already exist.
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# In-memory storage for connected clients and chat messages
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        # Store messages with their full structure (username, text, timestamp)
        self.messages: List[Dict] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        # Ensure the list is managed carefully in a real high-concurrency app
        # For this example, simple append/remove is fine.
        self.active_connections.append(websocket)
        # Send past messages to the newly connected client
        for message in self.messages:
            await websocket.send_text(json.dumps(message))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        # Store the message before broadcasting
        parsed_message = json.loads(message)
        self.messages.append(parsed_message) # Store the full message object
        # Using a copy of the list to avoid "list changed during iteration" errors
        # if a client disconnects during broadcast.
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except RuntimeError as e: # Handle cases where connection might have just closed
                print(f"Error sending to a connection, removing: {e}")
                self.disconnect(connection)

manager = ConnectionManager()

# --- FastAPI Endpoints ---

@app.get("/")
async def get_home():
    """Serves the main HTML page for the chat application."""
    # Assuming your main chat HTML file is named index.html and located in the 'static' directory
    # It is critical that 'static/index.html' exists before running the app.
    return HTMLResponse(content=open(os.path.join(static_dir, "index.html")).read(), status_code=200)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handles WebSocket connections for chat communication, including Akashvani interactions."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Assuming data is a JSON string containing username, text, and timestamp
            incoming_message = json.loads(data)
            message_text = incoming_message.get("text", "").strip()

            # Normalize user-provided shorthand to lower case for comparison
            # Ensure it starts with '@' for prefix matching consistency
            normalized_shorthand_check = AKASHVANI_SHORTHAND.lower()
            if not normalized_shorthand_check.startswith('@'):
                normalized_shorthand_check = f"@{normalized_shorthand_check}"

            # Check if the message is an explicit call to Akashvani
            # Uses the configured AKASHVANI_USERNAME and AKASHVANI_SHORTHAND
            if message_text.lower().startswith(f"@{AKASHVANI_USERNAME.lower()}") or \
               message_text.lower().startswith(normalized_shorthand_check):

                # Determine which prefix was used and remove it
                if message_text.lower().startswith(f"@{AKASHVANI_USERNAME.lower()}"):
                    # +1 for the '@' symbol
                    user_question = message_text[len(AKASHVANI_USERNAME) + 1:].strip()
                elif message_text.lower().startswith(normalized_shorthand_check):
                    # Use the length of the actual shorthand from the env, including the '@' if it has it
                    user_question = message_text[len(AKASHVANI_SHORTHAND):].strip()
                else:
                    # Fallback or error, though previous checks should prevent this
                    user_question = message_text # Keep original message if prefix not clearly matched

                # First, broadcast the user's query to everyone in the chat
                await manager.broadcast(data)

                # Then, generate Akashvani's response
                akashvani_response_text = await call_llm_for_akashvani(manager.messages, user_question)

                akashvani_message = {
                    "username": AKASHVANI_USERNAME, # Use configured username for Akashvani's message
                    "text": akashvani_response_text,
                    "timestamp": datetime.datetime.now().isoformat()
                }
                # Broadcast Akashvani's response
                await manager.broadcast(json.dumps(akashvani_message))

            else:
                # Regular message, just broadcast it
                await manager.broadcast(data)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"Client disconnected: {websocket.client}")
    except RuntimeError as e:
        # Catch potential errors related to WebSocket state (e.g., trying to receive on closed socket)
        print(f"Runtime error during WebSocket communication: {e}")
        manager.disconnect(websocket) # Ensure disconnection on error

# To run this FastAPI app:
# 1. Ensure your project structure is:
#    .
#    ├── app/
#    │   ├── main.py
#    │   └── akashvani_llm.py
#    │   └── prompts.py
#    ├── .env           (with the new AKASHVANI_SHORTHAND variable)
#    ├── requirements.txt
#    └── static/
#        └── index.html
# 2. Make sure you have `uvicorn` installed (`pip install uvicorn fastapi`).
# 3. From your project root directory (the one containing 'app' and 'static' folders),
#    run the FastAPI app using: `uvicorn app.main:app --reload`
# 4. Access your app in the browser at http://127.0.0.1:8000
