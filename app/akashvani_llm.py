# app/akashvani_llm.py
import asyncio
import datetime
from typing import List, Dict
import requests
import json
import os
from dotenv import load_dotenv

# Import the prompt templates
from app.prompts import AKASHVANI_PROMPT_TEMPLATE, EVALUATION_PROMPT_TEMPLATE, SUMMARIZATION_PROMPT_TEMPLATE

# Load environment variables from .env file
load_dotenv()

# --- Configuration (Loaded from .env with defaults and type casting) ---
AKASHVANI_USERNAME = os.getenv("AKASHVANI_USERNAME", "Akashvani")

OLLAMA_MODEL = os.getenv("LLM_MODEL", "llama3")
LLM_HOST = os.getenv("LLM_HOST", "localhost")
LLM_PORT = os.getenv("LLM_PORT", "11434")

LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.5"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "150"))
LLM_CONTEXT_HISTORY_SIZE = int(os.getenv("LLM_CONTEXT_HISTORY_SIZE", "10"))

# Configuration for the LLM Judge
LLM_JUDGE_MODEL = os.getenv("LLM_JUDGE_MODEL", OLLAMA_MODEL) # Use main model by default for judging
LLM_JUDGE_TEMPERATURE = float(os.getenv("LLM_JUDGE_TEMPERATURE", "0.2")) # Lower temp for more strict judging

# Configuration for the LLM Summarizer (defaults to main model settings)
LLM_SUMMARIZER_MODEL = os.getenv("LLM_SUMMARIZER_MODEL", OLLAMA_MODEL)
LLM_SUMMARIZER_TEMPERATURE = float(os.getenv("LLM_SUMMARIZER_TEMPERATURE", "0.1")) # Lower temp for more factual summary
LLM_SUMMARIZER_MAX_TOKENS = int(os.getenv("LLM_SUMMARIZER_MAX_TOKENS", "200")) # Allow more tokens for summary

OLLAMA_API_URL = f"http://{LLM_HOST}:{LLM_PORT}/api/generate"

async def summarize_chat_history(full_chat_history: List[Dict], user_question: str) -> str:
    """
    Summarizes the full chat history based on the user's explicit question
    using an LLM.

    Args:
        full_chat_history (List[Dict]): The complete list of chat messages.
        user_question (str): The specific question asked by the user.

    Returns:
        str: A concise summary of relevant history, or a "no relevant history" message.
    """
    #print(f"\n--- LLM Summarizer Call ---")
    #print(f"  User Question for Summarization: '{user_question}'")
    #print(f"  Full Chat History for Summarization: {full_chat_history}")

    # Format the full chat history for the summarizer prompt
    formatted_full_history = "\n".join([
        f"{msg['username']}: {msg['text']}"
        for msg in full_chat_history
        if msg.get('username') != AKASHVANI_USERNAME # Exclude Akashvani's own messages
    ])
    if not formatted_full_history:
        formatted_full_history = "[No chat history available for summarization]"

    summarizer_prompt = SUMMARIZATION_PROMPT_TEMPLATE.format(
        full_chat_history=formatted_full_history,
        user_question=user_question
    )

    payload = {
        "model": LLM_SUMMARIZER_MODEL,
        "prompt": summarizer_prompt,
        "stream": False,
        "options": {
            "temperature": LLM_SUMMARIZER_TEMPERATURE,
            "num_predict": LLM_SUMMARIZER_MAX_TOKENS,
        }
    }

    try:
        response = await asyncio.to_thread(
            requests.post, OLLAMA_API_URL, json=payload, timeout=45 # Moderate timeout
        )
        response.raise_for_status()
        response_data = response.json()
        summary_text = response_data.get("response", "").strip()
        #print(f"  Summarizer Raw Output: {summary_text}")
        return summary_text
    except requests.exceptions.RequestException as e:
        print(f"Error calling Ollama Summarizer API: {e}")
        return "[Error: Could not generate summary. Check Ollama connection.]"
    except Exception as e:
        print(f"An unexpected error occurred during summarization: {e}")
        return "[Error: Unexpected summarization issue.]"


async def call_llm_for_akashvani(chat_history: List[Dict], user_question: str) -> str:
    """
    Interacts with an Ollama LLM to generate a response for Akashvani.
    Now includes a summarization step before final answer generation.

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

    # Step 1: Summarize the chat history in view of the user's question
    # Pass the full chat history to the summarizer
    summarized_context = await summarize_chat_history(chat_history, user_question)

    # Use LLM_CONTEXT_HISTORY_SIZE just for logging or if you prefer a hard limit on summarizer input
    # For summarizer, we usually pass as much as possible within token limits.

    # Step 2: Generate the final answer using the summarized context
    prompt = AKASHVANI_PROMPT_TEMPLATE.format(
        context=summarized_context, # Use the summarized context here
        user_question=user_question
    )

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": LLM_TEMPERATURE,
            "num_predict": LLM_MAX_TOKENS,
        }
    }

    try:
        response = await asyncio.to_thread(
            requests.post, OLLAMA_API_URL, json=payload, timeout=60
        )
        response.raise_for_status()

        response_data = response.json()
        #print(f"Ollama Raw Response (Final Answer): {response_data}")

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


async def evaluate_akashvani_response(expected_behavior: str, actual_response: str) -> Dict:
    """
    Evaluates an Akashvani response using an LLM judge.

    Args:
        expected_behavior (str): A description of what the response should achieve.
        actual_response (str): The actual response generated by Akashvani.

    Returns:
        Dict: A dictionary with 'status' (PASS/FAIL) and 'reason' (if FAIL).
    """
    print(f"\n--- LLM Judge Evaluation ---")
    print(f"  Expected Behavior: {expected_behavior}")
    print(f"  Actual Response: '{actual_response}'")

    prompt = EVALUATION_PROMPT_TEMPLATE.format(
        expected_behavior=expected_behavior,
        actual_response=actual_response
    )

    payload = {
        "model": LLM_JUDGE_MODEL, # Use judge model configuration
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": LLM_JUDGE_TEMPERATURE, # Lower temp for strictness
            "num_predict": 50, # Keep judge response concise
        }
    }

    try:
        response = await asyncio.to_thread(
            requests.post, OLLAMA_API_URL, json=payload, timeout=30 # Shorter timeout for judge
        )
        response.raise_for_status()
        response_data = response.json()
        judge_output = response_data.get("response", "").strip()
        print(f"  Judge Raw Output: {judge_output}")

        # Parse the judge's response
        lines = judge_output.split('\n', 1)
        status = lines[0].strip().upper()
        reason = lines[1].strip() if len(lines) > 1 else ""

        if status == "PASS":
            return {"status": "PASS", "reason": ""}
        else:
            # Ensure reason is provided if FAIL
            if not reason:
                reason = "No specific reason provided by judge, but status was FAIL."
            return {"status": "FAIL", "reason": reason}

    except requests.exceptions.RequestException as e:
        print(f"Error calling Ollama LLM Judge API: {e}")
        return {"status": "ERROR", "reason": f"Judge connection error: {e}"}
    except Exception as e:
        print(f"An unexpected error occurred during judging: {e}")
        return {"status": "ERROR", "reason": f"Judge internal error: {e}"}

