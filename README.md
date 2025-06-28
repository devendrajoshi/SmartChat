# Akashvani: Your Dynamic Chat Companion

## 🚀 Project Overview

**Akashvani** (Sanskrit for "voice from the sky") is an innovative Proof-of-Concept (PoC) project exploring new paradigms for AI integration in modern messaging applications. It addresses a common challenge: how to have an intelligent AI assistant seamlessly participate in group chats without being intrusive, while also understanding the rich, evolving context of human conversations.

This project is currently focused on **Phase 1: The "On-Demand" AI Participant**. Here, Akashvani acts as an "invisible participant," a silent presence that only offers its insights when explicitly invoked by users. Phase 2 will explore a "Proactive" mode, where the AI intelligently contributes when needed, while still adhering to strict ethical guidelines.

For a deeper dive into the core concept, design philosophy, and the real-world problem Akashvani aims to solve, check out my accompanying blog post:
[**The Invisible Participant: Your Dynamic Chat Companion - A Smarter AI Solution for Your Messaging Apps**](https://www.linkedin.com/pulse/invisible-participant-your-dynamic-chat-companion-devendra-joshi-2jboc)
*(**Remember to replace `YOUR_BLOG_POST_LINK_HERE` with the actual URL to your blog post!**)*

## ✨ Key Features (Phase 1)

* **On-Demand AI Interaction:** Users explicitly call Akashvani using `@Akashvani` or a configurable shorthand (default `@av`).

* **Contextual Understanding:** Utilizes a two-step LLM process to first summarize chat history relevant to a user's question, then uses that summary to generate a precise, factual answer.

* **External Knowledge Lookup:** Capable of answering general knowledge questions from its LLM's training data.

* **Ethical Design Principles:** Built with an emphasis on respecting human conversational flow, reducing information overload, and promoting positive person-to-person trust by avoiding unsolicited judgment or blame.

* **Showcase Examples:** Dedicated static web pages to quickly demonstrate core capabilities without live LLM inference.

* **LLM-Assisted Testing:** Integrates an innovative LLM-based evaluation system for non-deterministic AI responses, providing dynamic `PASS`/`FAIL` judgments and reasons.

## 🛠️ Prerequisites

Before you begin, ensure you have the following installed:

* **Python 3.12+**

* **pip** (Python package installer)

* **Ollama:** A local Ollama server running with your chosen LLM model pulled (e.g., `llama2`).
    * Download Ollama: <https://ollama.com/>
    * Pull a model (e.g., `ollama pull llama2`)

## 📦 Setup & Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git](https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git)
    cd YOUR_REPO_NAME # Replace with your actual repo name
    ```
    *(**Note**: Replace `YOUR_USERNAME` and `YOUR_REPO_NAME` with your actual GitHub details!)*

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv .venv
    ```

3.  **Activate the virtual environment:**
    * **macOS/Linux:**
        ```bash
        source .venv/bin/activate
        ```
    * **Windows (Command Prompt):**
        ```bash
        .venv\Scripts\activate.bat
        ```
    * **Windows (PowerShell):**
        ```bash
        .venv\Scripts\Activate.ps1
        ```

4.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(The `requirements.txt` file should contain: `fastapi`, `uvicorn`, `requests`, `python-dotenv`, `pytest`, `requests_mock`, `httpx`, `pytest-asyncio`)*

5.  **Configure environment variables:**
    Create a `.env` file in the project's root directory with the following variables. Adjust values as per your Ollama setup and preferences:
    ```dotenv
    # --- LLM Configuration for Akashvani ---
    LLM_MODEL=llama2
    LLM_HOST=localhost
    LLM_PORT=11434
    LLM_TEMPERATURE=0.5
    LLM_MAX_TOKENS=150
    LLM_CONTEXT_HISTORY_SIZE=10

    # --- Akashvani AI Persona & Behavior Configuration ---
    AKASHVANI_USERNAME=Akashvani
    AKASHVANI_SHORTHAND=@av

    # --- LLM Judge Configuration (for testing) ---
    LLM_JUDGE_MODEL=llama2 # Can be a smaller, faster model if preferred
    LLM_JUDGE_TEMPERATURE=0.2

    # --- LLM Summarizer Configuration (for context processing) ---
    LLM_SUMMARIZER_MODEL=llama2 # Can be a smaller, faster model if preferred
    LLM_SUMMARIZER_TEMPERATURE=0.1
    LLM_SUMMARIZER_MAX_TOKENS=200
    ```

## 🚀 Running the Application

1.  **Ensure your Ollama server is running** and the models specified in `.env` (`LLM_MODEL`, `LLM_JUDGE_MODEL`, `LLM_SUMMARIZER_MODEL`) are pulled.

2.  **Activate your virtual environment** (if not already active).

3.  **Start the FastAPI server:**
    ```bash
    uvicorn app.main:app --reload
    ```
4.  **Access the application in your browser:**

    * **Live Chat (Interactive):** `http://127.0.0.1:8000`
        (Allows you to set your username and chat. Akashvani will respond to explicit queries like `@Akashvani` or `@av`.)

    * **Static Example 1 (Contextual Conclusion):** `http://127.0.0.1:8000/example_1`
        (Demonstrates Akashvani summarizing chat history for a question.)

    * **Static Example 2 (External Knowledge Lookup):** `http://127.0.0.1:8000/example_2`
        (Demonstrates Akashvani answering a general knowledge question.)

    * **Static Example 3 (Chat Summarization):** `http://127.0.0.1:8000/example_3`
        (Demonstrates Akashvani summarizing a multi-topic chat.)

## 🧪 Running Tests

This project includes robust integration tests that utilize an LLM (Akashvani itself, or a specified judge model) to evaluate responses.

1.  **Ensure your Ollama server is running** and the models are pulled (as tests will make live LLM calls).

2.  **Activate your virtual environment.**

3.  **Run the tests:**
    ```bash
    pytest test.py -s -v
    ```
    The `-s` flag allows `print` statements (like the detailed chat logs and judge results) to be displayed, and `-v` provides verbose output.

## 📁 Project Structure
