# test.py
import pytest
import json
import asyncio
import datetime
from typing import List, Dict

# Import TestClient from fastapi.testclient for WebSocket testing
from fastapi.testclient import TestClient

# Assuming the main FastAPI app instance is named 'app' in 'app.main'
from app.main import app as fastapi_app
# Import the ConnectionManager to clear its message history for test isolation
from app.main import manager as connection_manager
from app.akashvani_llm import AKASHVANI_USERNAME

# Constants for formatting output
CHAT_WIDTH = 80
LEFT_ALIGN_PADDING = 2
RIGHT_ALIGN_PADDING = 2
USERNAME_WIDTH = 12 # Adjust as needed for longest username


# Helper function to create chat history entries
def create_message(username: str, text: str, timestamp: str = None) -> dict:
    if timestamp is None:
        timestamp = datetime.datetime.now().isoformat()
    return {"username": username, "text": text, "timestamp": timestamp}

def print_chat_message(username: str, text: str, is_akashvani: bool = False):
    """Prints a message formatted like a chat window."""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    formatted_username = f"[{username[:USERNAME_WIDTH].ljust(USERNAME_WIDTH)}]"
    message_line = f"{text}"

    if is_akashvani:
        # Right align for Akashvani
        prefix_space = " " * (CHAT_WIDTH - len(formatted_username) - len(message_line) - len(timestamp) - RIGHT_ALIGN_PADDING)
        print(f"{prefix_space}{formatted_username} {message_line} ({timestamp})")
    else:
        # Left align for other users
        print(f"{formatted_username} {message_line} ({timestamp})")


# Fixture for the FastAPI TestClient
@pytest.fixture(scope="module")
def client():
    """
    Provides a FastAPI TestClient for testing the application.
    This client handles both HTTP and WebSocket connections.
    """
    with TestClient(fastapi_app) as client_instance:
        yield client_instance

# Fixture to clear chat history before each test function
@pytest.fixture(autouse=True)
def clear_chat_history():
    """
    Clears the ConnectionManager's message history before each test runs
    to ensure test isolation.
    """
    connection_manager.messages = [] # Reset the in-memory history
    yield
    # No cleanup needed here as messages are reset at the start of next test

@pytest.mark.asyncio
async def test_websocket_connection(client: TestClient):
    """
    Tests basic WebSocket connection and disconnection.
    A successful entry into the 'with' block implies acceptance.
    """
    print("\n" + "="*CHAT_WIDTH)
    print(f"--- Test Case: Basic WebSocket Connection ---".center(CHAT_WIDTH))
    print("="*CHAT_WIDTH)
    try:
        with client.websocket_connect("/ws") as websocket:
            # Removed websocket.url as it's not available on WebSocketTestSession
            print(f"  [System Message] Client connected to WebSocket.")
            # If no exception is raised here, the connection was accepted.
        print("  [System Message] Client disconnected from WebSocket.")
        print("Test Result: PASSED\n")
    except Exception as e:
        print(f"Test Result: FAILED - {e}\n")
        pytest.fail(f"Test failed: {e}")


@pytest.mark.asyncio
async def test_user_message_broadcast(client: TestClient):
    """
    Tests if a user's message is broadcast to all connected clients.
    """
    print("\n" + "="*CHAT_WIDTH)
    print(f"--- Test Case: User Message Broadcast ---".center(CHAT_WIDTH))
    print("="*CHAT_WIDTH)
    user1_username = "UserOne"
    user2_username = "UserTwo"
    test_message = "Hello, chat! Can you hear me?"

    try:
        with client.websocket_connect("/ws") as ws1, \
             client.websocket_connect("/ws") as ws2:

            print(f"  [System Message] {user1_username} and {user2_username} connected.")

            # User1 sends a message
            message_to_send = create_message(user1_username, test_message)
            print_chat_message(user1_username, message_to_send['text'])
            ws1.send_text(json.dumps(message_to_send))

            # Both clients should receive the message
            received_message_ws1 = json.loads(ws1.receive_text())
            received_message_ws2 = json.loads(ws2.receive_text())

            print_chat_message(received_message_ws1["username"], received_message_ws1["text"])
            # In a real multi-client test, this would be from a separate connection.
            # Here, it's just proving ws2 received it.
            print_chat_message(received_message_ws2["username"], received_message_ws2["text"])

            assert received_message_ws1["username"] == user1_username, f"Expected username '{user1_username}', got '{received_message_ws1['username']}'"
            assert received_message_ws1["text"] == test_message, f"Expected text '{test_message}', got '{received_message_ws1['text']}'"
            assert received_message_ws2["username"] == user1_username, f"Expected username '{user1_username}', got '{received_message_ws2['username']}'"
            assert received_message_ws2["text"] == test_message, f"Expected text '{test_message}', got '{received_message_ws2['text']}'"
        print("Test Result: PASSED\n")
    except Exception as e:
        print(f"Test Result: FAILED - {e}\n")
        pytest.fail(f"Test failed: {e}")


@pytest.mark.asyncio
async def test_akashvani_explicit_question(client: TestClient):
    """
    Tests an explicit question to Akashvani and verifies its response.
    This test *requires* a running Ollama instance with the configured model.
    """
    print("\n" + "="*CHAT_WIDTH)
    print(f"--- Test Case: Akashvani Explicit Question ---".center(CHAT_WIDTH))
    print("="*CHAT_WIDTH)
    user_username = "Tester"
    question_to_akashvani = "@av what is the capital of France?"
    expected_keywords = ["paris", "france"] # Keywords to check in Akashvani's response

    try:
        with client.websocket_connect("/ws") as ws:
            print(f"  [System Message] {user_username} connected.")

            # Send a message to seed chat history (optional but good for context for some models)
            initial_message = create_message(user_username, "Hello chat, testing Akashvani.")
            print_chat_message(user_username, initial_message['text'])
            ws.send_text(json.dumps(initial_message))
            await asyncio.sleep(0.1) # Small sleep to allow server to process and broadcast
            json.loads(ws.receive_text()) # Consume the initial message echo

            # Send the question to Akashvani
            akashvani_query_message = create_message(user_username, question_to_akashvani)
            print_chat_message(user_username, akashvani_query_message['text'])
            ws.send_text(json.dumps(akashvani_query_message))

            # Expect user's own query to be echoed back (this happens first in broadcast)
            received_query = json.loads(ws.receive_text())
            # We don't print this echo as it's just a confirmation of send for the client itself.

            # Expect Akashvani's response (this comes after LLM processing)
            akashvani_response = json.loads(ws.receive_text())
            print_chat_message(akashvani_response["username"], akashvani_response["text"], is_akashvani=True)
            
            assert akashvani_response["username"] == AKASHVANI_USERNAME, \
                f"Expected Akashvani's username '{AKASHVANI_USERNAME}', got '{akashvani_response['username']}'"
            assert akashvani_response["text"] is not None, \
                "Akashvani's response text should not be None"
            assert len(akashvani_response["text"]) > 0, \
                "Akashvani's response text should not be empty"
            
            found_keyword = any(keyword in akashvani_response["text"].lower() for keyword in expected_keywords)
            assert found_keyword, \
                f"Akashvani's response '{akashvani_response['text']}' did not contain expected keywords {expected_keywords}"
        print("Test Result: PASSED\n")
    except Exception as e:
        print(f"Test Result: FAILED - {e}\n")
        pytest.fail(f"Test failed: {e}")


@pytest.mark.asyncio
async def test_akashvani_contextual_question(client: TestClient):
    """
    Tests Akashvani's ability to respond to a contextual question.
    This test *requires* a running Ollama instance with the configured model.
    """
    print("\n" + "="*CHAT_WIDTH)
    print(f"--- Test Case: Akashvani Contextual Question ---".center(CHAT_WIDTH))
    print("="*CHAT_WIDTH)
    user_username = "TesterContext"
    expected_keywords = ["london", "raining", "weather", "true", "yes"]

    try:
        with client.websocket_connect("/ws") as ws:
            print(f"  [System Message] {user_username} connected.")

            # Simulate a short conversation to build context for Akashvani
            msg_alice = create_message("Alice", "I heard it's raining in London today.")
            print_chat_message("Alice", msg_alice['text'])
            ws.send_text(json.dumps(msg_alice))
            await asyncio.sleep(0.1)
            json.loads(ws.receive_text()) # Consume Alice's message echo

            msg_bob = create_message("Bob", "Is that true? I thought it was sunny.")
            print_chat_message("Bob", msg_bob['text'])
            ws.send_text(json.dumps(msg_bob))
            await asyncio.sleep(0.1)
            json.loads(ws.receive_text()) # Consume Bob's message echo

            # Now ask Akashvani about the previous statement
            akashvani_query_message = create_message(user_username, "@av is it raining in London?")
            print_chat_message(user_username, akashvani_query_message['text'])
            ws.send_text(json.dumps(akashvani_query_message))

            # Consume TesterContext's message echo
            json.loads(ws.receive_text())

            # Expect Akashvani's response
            akashvani_response = json.loads(ws.receive_text())
            print_chat_message(akashvani_response["username"], akashvani_response["text"], is_akashvani=True)
            
            assert akashvani_response["username"] == AKASHVANI_USERNAME, \
                f"Expected Akashvani's username '{AKASHVANI_USERNAME}', got '{akashvani_response['username']}'"
            assert akashvani_response["text"] is not None, \
                "Akashvani's response text should not be None"
            assert len(akashvani_response["text"]) > 0, \
                "Akashvani's response text should not be empty"
            
            found_keyword = any(keyword in akashvani_response["text"].lower() for keyword in expected_keywords)
            assert found_keyword, \
                f"Akashvani's response '{akashvani_response['text']}' did not contain expected keywords {expected_keywords}"
        print("Test Result: PASSED\n")
    except Exception as e:
        print(f"Test Result: FAILED - {e}\n")
        pytest.fail(f"Test failed: {e}")


@pytest.mark.asyncio
async def test_akashvani_summarize_request(client: TestClient):
    """
    Tests Akashvani's ability to summarize the chat history.
    This test *requires* a running Ollama instance with the configured model.
    """
    print("\n" + "="*CHAT_WIDTH)
    print(f"--- Test Case: Akashvani Summarize Request ---".center(CHAT_WIDTH))
    print("="*CHAT_WIDTH)
    user_username = "Summarizer"
    expected_keywords = ["meeting", "agenda", "budget", "milestones", "discuss"]

    try:
        with client.websocket_connect("/ws") as ws:
            print(f"  [System Message] {user_username} connected.")

            # Simulate a conversation with multiple messages
            msg_usera_1 = create_message("UserA", "Let's plan our next team meeting agenda.")
            print_chat_message("UserA", msg_usera_1['text'])
            ws.send_text(json.dumps(msg_usera_1))
            await asyncio.sleep(0.1)
            json.loads(ws.receive_text()) # Consume echo

            msg_userb_1 = create_message("UserB", "I think we should discuss Q3 budget and new hires.")
            print_chat_message("UserB", msg_userb_1['text'])
            ws.send_text(json.dumps(msg_userb_1))
            await asyncio.sleep(0.1)
            json.loads(ws.receive_text()) # Consume echo

            msg_usera_2 = create_message("UserA", "Good idea. Also, review the project milestones.")
            print_chat_message("UserA", msg_usera_2['text'])
            ws.send_text(json.dumps(msg_usera_2))
            await asyncio.sleep(0.1)
            json.loads(ws.receive_text()) # Consume echo

            # Request summary from Akashvani
            akashvani_query_message = create_message(user_username, "@av summarize our chat.")
            print_chat_message(user_username, akashvani_query_message['text'])
            ws.send_text(json.dumps(akashvani_query_message))

            # Consume Summarizer's message echo
            json.loads(ws.receive_text())

            # Expect Akashvani's response
            akashvani_response = json.loads(ws.receive_text())
            print_chat_message(akashvani_response["username"], akashvani_response["text"], is_akashvani=True)
            
            assert akashvani_response["username"] == AKASHVANI_USERNAME, \
                f"Expected Akashvani's username '{AKASHVANI_USERNAME}', got '{akashvani_response['username']}'"
            assert akashvani_response["text"] is not None, \
                "Akashvani's response text should not be None"
            assert len(akashvani_response["text"]) > 0, \
                "Akashvani's response text should not be empty"
            
            found_keyword = any(keyword in akashvani_response["text"].lower() for keyword in expected_keywords)
            assert found_keyword, \
                f"Akashvani's response '{akashvani_response['text']}' did not contain expected keywords {expected_keywords}"
        print("Test Result: PASSED\n")
    except Exception as e:
        print(f"Test Result: FAILED - {e}\n")
        pytest.fail(f"Test failed: {e}")
