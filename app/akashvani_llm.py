# app/akashvani_llm.py
import asyncio
import datetime
from typing import List, Dict
import requests
import json
import os
from dotenv import load_dotenv

# Import the prompt template
from app.prompts import AKASHVANI_PROMPT_TEMPLATE

# Load environment variables from .env file
# This must be called early to load variables into os.environ
load_dotenv()

# --- Configuration (Loaded from .env with defaults and type casting) ---
AKASHVANI_USERNAME = os.getenv("AKASHVANI_USERNAME", "Akashvani")

OLLAMA_MODEL = os.getenv("LLM_MODEL", "llama3")
LLM_HOST = os.getenv("LLM_HOST", "localhost")
LLM_PORT = os.getenv("LLM_PORT", "11434")

# Convert to appropriate types
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.5"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "150"))
LLM_CONTEXT_HISTORY_SIZE = int(os.getenv("LLM_CONTEXT_HISTORY_SIZE", "10"))

OLLAMA_API_URL = f"http://{LLM_HOST}:{LLM_PORT}/api/generate"

async def call_llm_for_akashvani(chat_history: List[Dict], user_question: str) -> str:
    """
    Interacts with an Ollama LLM to generate a response for Akashvani.

    Args:
        chat_history (List[Dict]): A list of past chat messages, each a dict with
                                   'username', 'text', 'timestamp'.
        user_question (str): The specific question directed at Akashvani.

    Returns:
        str: The generated response from the LLM.
    """
    #print(f"Akashvani received question: '{user_question}'")
    #print(f"Chat history for context: {chat_history}")
    #print(f"Using Ollama API URL: {OLLAMA_API_URL} with model: {OLLAMA_MODEL}")
    #print(f"LLM Params: Temp={LLM_TEMPERATURE}, MaxTokens={LLM_MAX_TOKENS}, ContextSize={LLM_CONTEXT_HISTORY_SIZE}")

    # Construct conversation history for the LLM
    # Filter out Akashvani's own messages from the history to prevent loops or self-reference.
    # Use LLM_CONTEXT_HISTORY_SIZE to limit context.
    context_messages = [
        f"{msg['username']}: {msg['text']}"
        for msg in chat_history[-LLM_CONTEXT_HISTORY_SIZE:] # Use configurable context size
        if msg.get('username') != AKASHVANI_USERNAME
    ]
    formatted_context = "\n".join(context_messages)
    if not formatted_context:
        formatted_context = "[No recent chat history]"


    # Use the imported prompt template and format it with current context and question
    prompt = AKASHVANI_PROMPT_TEMPLATE.format(
        context=formatted_context,
        user_question=user_question
    )

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": LLM_TEMPERATURE, # Use configurable temperature
            "num_predict": LLM_MAX_TOKENS, # Use configurable max tokens
        }
    }

    try:
        response = await asyncio.to_thread(
            requests.post, OLLAMA_API_URL, json=payload, timeout=60
        )
        response.raise_for_status()

        response_data = response.json()
        #print(f"Ollama Raw Response: {response_data}")

        if "response" in response_data:
            llm_response_text = response_data["response"].strip()
            # Clean up potential leading phrases from LLM
            if llm_response_text.lower().startswith(f"{AKASHVANI_USERNAME.lower()}:"):
                llm_response_text = llm_response_text[len(AKASHVANI_USERNAME) + 1:].strip()
            if llm_response_text.lower().startswith("your concise answer:"):
                llm_response_text = llm_response_text[len("your concise answer:"):].strip()
            return llm_response_text
        else:
            return f"Akashvani: I received an unexpected response from the LLM."

    except requests.exceptions.RequestException as e:
        print(f"Error calling Ollama API: {e}")
        return f"Akashvani: I apologize, but I'm having trouble connecting to my knowledge base (Ollama). Please ensure Ollama is running and the model '{OLLAMA_MODEL}' is pulled. Error: {e}"
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return f"Akashvani: An internal error occurred while processing your request: {e}"
