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
# Import Akashvani's LLM components and the evaluation function
from app.akashvani_llm import AKASHVANI_USERNAME, evaluate_akashvani_response

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
        # Ensure that the length calculation accounts for potential multi-line responses from LLM
        # For simplicity in this display, we'll align the first line right.
        first_line = message_line.split('\n')[0]
        prefix_space = " " * (CHAT_WIDTH - len(formatted_username) - len(first_line) - len(timestamp) - RIGHT_ALIGN_PADDING)
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
    Tests an explicit question to Akashvani and verifies its response using LLM evaluation.
    This test *requires* a running Ollama instance with the configured model.
    """
    print("\n" + "="*CHAT_WIDTH)
    print(f"--- Test Case: Akashvani Explicit Question ---".center(CHAT_WIDTH))
    print("="*CHAT_WIDTH)
    user_username = "Tester"
    question_to_akashvani = "@av what is the capital of France?"
    
    expected_behavior = (
        f"Akashvani should respond with the correct capital of France. "
        f"The response should be concise and directly answer the question."
    )

    try:
        with client.websocket_connect("/ws") as ws:
            print(f"  [System Message] {user_username} connected.")

            initial_message = create_message(user_username, "Hello chat, testing Akashvani.")
            print_chat_message(user_username, initial_message['text'])
            ws.send_text(json.dumps(initial_message))
            await asyncio.sleep(0.1)
            json.loads(ws.receive_text()) # Consume echo

            akashvani_query_message = create_message(user_username, question_to_akashvani)
            print_chat_message(user_username, akashvani_query_message['text'])
            ws.send_text(json.dumps(akashvani_query_message))

            json.loads(ws.receive_text()) # Consume echo of user's query

            akashvani_response = json.loads(ws.receive_text())
            print_chat_message(akashvani_response["username"], akashvani_response["text"], is_akashvani=True)
            
            # Use LLM Judge for assertion
            evaluation_result = await evaluate_akashvani_response(expected_behavior, akashvani_response["text"])
            
            print(f"  [LLM Judge Result] Status: {evaluation_result['status']}")
            if evaluation_result['status'] == "FAIL":
                print(f"  [LLM Judge Reason] Reason: {evaluation_result['reason']}")

            assert evaluation_result['status'] == "PASS", \
                f"LLM Judge failed the response. Reason: {evaluation_result['reason']}"

        print("Test Result: PASSED\n")
    except Exception as e:
        print(f"Test Result: FAILED - {e}\n")
        pytest.fail(f"Test failed: {e}")


@pytest.mark.asyncio
async def test_akashvani_contextual_question(client: TestClient):
    """
    Tests Akashvani's ability to respond to a contextual question using LLM evaluation.
    This test *requires* a running Ollama instance with the configured model.
    """
    print("\n" + "="*CHAT_WIDTH)
    print(f"--- Test Case: Akashvani Contextual Question ---".center(CHAT_WIDTH))
    print("="*CHAT_WIDTH)
    user_username = "TesterContext"

    expected_behavior = (
        f"Akashvani should verify whether it is currently raining in London based on its knowledge. "
        f"It should not just repeat what was said in the chat, but provide a factual answer. "
        f"The response should be concise."
    )

    try:
        with client.websocket_connect("/ws") as ws:
            print(f"  [System Message] {user_username} connected.")

            msg_alice = create_message("Alice", "I heard it's raining in London today.")
            print_chat_message("Alice", msg_alice['text'])
            ws.send_text(json.dumps(msg_alice))
            await asyncio.sleep(0.1)
            json.loads(ws.receive_text()) # Consume echo

            msg_bob = create_message("Bob", "Is that true? I thought it was sunny.")
            print_chat_message("Bob", msg_bob['text'])
            ws.send_text(json.dumps(msg_bob))
            await asyncio.sleep(0.1)
            json.loads(ws.receive_text()) # Consume echo

            akashvani_query_message = create_message(user_username, "@av is it raining in London?")
            print_chat_message(user_username, akashvani_query_message['text'])
            ws.send_text(json.dumps(akashvani_query_message))

            json.loads(ws.receive_text()) # Consume echo of user's query

            akashvani_response = json.loads(ws.receive_text())
            print_chat_message(akashvani_response["username"], akashvani_response["text"], is_akashvani=True)
            
            # Use LLM Judge for assertion
            evaluation_result = await evaluate_akashvani_response(expected_behavior, akashvani_response["text"])
            
            print(f"  [LLM Judge Result] Status: {evaluation_result['status']}")
            if evaluation_result['status'] == "FAIL":
                print(f"  [LLM Judge Reason] Reason: {evaluation_result['reason']}")

            assert evaluation_result['status'] == "PASS", \
                f"LLM Judge failed the response. Reason: {evaluation_result['reason']}"

        print("Test Result: PASSED\n")
    except Exception as e:
        print(f"Test Result: FAILED - {e}\n")
        pytest.fail(f"Test failed: {e}")


@pytest.mark.asyncio
async def test_akashvani_summarize_request(client: TestClient):
    """
    Tests Akashvani's ability to summarize the chat history using LLM evaluation.
    This test *requires* a running Ollama instance with the configured model.
    """
    print("\n" + "="*CHAT_WIDTH)
    print(f"--- Test Case: Akashvani Summarize Request ---".center(CHAT_WIDTH))
    print("="*CHAT_WIDTH)
    user_username = "Summarizer"

    expected_behavior = (
        f"Akashvani should provide a brief and accurate summary of the preceding chat messages. "
        f"The summary should capture the main topics discussed (e.g., meeting agenda, budget, hires, milestones)."
    )

    try:
        with client.websocket_connect("/ws") as ws:
            print(f"  [System Message] {user_username} connected.")

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

            json.loads(ws.receive_text()) # Consume echo of user's query

            akashvani_response = json.loads(ws.receive_text())
            print_chat_message(akashvani_response["username"], akashvani_response["text"], is_akashvani=True)
            
            # Use LLM Judge for assertion
            evaluation_result = await evaluate_akashvani_response(expected_behavior, akashvani_response["text"])
            
            print(f"  [LLM Judge Result] Status: {evaluation_result['status']}")
            if evaluation_result['status'] == "FAIL":
                print(f"  [LLM Judge Reason] Reason: {evaluation_result['reason']}")

            assert evaluation_result['status'] == "PASS", \
                f"LLM Judge failed the response. Reason: {evaluation_result['reason']}"

        print("Test Result: PASSED\n")
    except Exception as e:
        print(f"Test Result: FAILED - {e}\n")
        pytest.fail(f"Test failed: {e}")


@pytest.mark.asyncio
async def test_akashvani_complex_contextual_question(client: TestClient):
    """
    Tests Akashvani's ability to extract relevant information from a complex, multi-topic chat history
    and answer a specific question using LLM evaluation.
    Requires a running Ollama instance.
    """
    print("\n" + "="*CHAT_WIDTH)
    print(f"--- Test Case: Akashvani Complex Contextual Question ---".center(CHAT_WIDTH))
    print("="*CHAT_WIDTH)
    user_username = "ComplexQueryUser"
    expected_behavior = (
        f"Akashvani should identify the specific date of the marketing meeting from the chat history "
        f"and state it concisely. It should ignore irrelevant topics like lunch plans."
    )

    try:
        with client.websocket_connect("/ws") as ws:
            print(f"  [System Message] {user_username} connected.")

            messages = [
                create_message("Dev", "Hey team, just finished the Q2 report. It's looking good."),
                create_message("Marketing", "Great! When's our next marketing sync meeting? Need to discuss the new campaign launch."),
                create_message("Ops", "I'm free next Tuesday, but not Wednesday."),
                create_message("Admin", "Marketing meeting is confirmed for July 15th at 10 AM. Room 301."),
                create_message("Dev", "Sounds good. Anyone up for lunch at the new cafe?"),
                create_message("Marketing", "Can't make lunch, busy prepping for July 15th!"),
                create_message("Ops", "Lunch sounds great, but after our meeting on the 15th."),
            ]

            for msg in messages:
                print_chat_message(msg['username'], msg['text'])
                ws.send_text(json.dumps(msg))
                await asyncio.sleep(0.1)
                json.loads(ws.receive_text()) # Consume echo

            akashvani_query_message = create_message(user_username, "@av when is the next marketing meeting?")
            print_chat_message(user_username, akashvani_query_message['text'])
            ws.send_text(json.dumps(akashvani_query_message))

            json.loads(ws.receive_text()) # Consume echo of user's query

            akashvani_response = json.loads(ws.receive_text())
            print_chat_message(akashvani_response["username"], akashvani_response["text"], is_akashvani=True)
            
            evaluation_result = await evaluate_akashvani_response(expected_behavior, akashvani_response["text"])
            
            print(f"  [LLM Judge Result] Status: {evaluation_result['status']}")
            if evaluation_result['status'] == "FAIL":
                print(f"  [LLM Judge Reason] Reason: {evaluation_result['reason']}")

            assert evaluation_result['status'] == "PASS", \
                f"LLM Judge failed the response. Reason: {evaluation_result['reason']}"
        print("Test Result: PASSED\n")
    except Exception as e:
        print(f"Test Result: FAILED - {e}\n")
        pytest.fail(f"Test failed: {e}")


@pytest.mark.asyncio
async def test_akashvani_no_relevant_context(client: TestClient):
    """
    Tests Akashvani's response when the chat history contains no relevant information
    to the user's question, using LLM evaluation.
    Requires a running Ollama instance.
    """
    print("\n" + "="*CHAT_WIDTH)
    print(f"--- Test Case: Akashvani No Relevant Context ---".center(CHAT_WIDTH))
    print("="*CHAT_WIDTH)
    user_username = "NoContextUser"
    expected_behavior = (
        f"Akashvani should provide the correct chemical formula for water from its general knowledge. "
        f"It should respond concisely with the factual answer (H2O) and not attempt to summarize chat history. "
        f"It should not mention that the chat history is irrelevant." # Removed the requirement for disclaimer
    )

    try:
        with client.websocket_connect("/ws") as ws:
            print(f"  [System Message] {user_username} connected.")

            messages = [
                create_message("UserX", "What's everyone having for dinner tonight?"),
                create_message("UserY", "I'm thinking pizza. How about you?"),
                create_message("UserX", "Sounds good! I might cook pasta."),
            ]

            for msg in messages:
                print_chat_message(msg['username'], msg['text'])
                ws.send_text(json.dumps(msg))
                await asyncio.sleep(0.1)
                json.loads(ws.receive_text()) # Consume echo

            akashvani_query_message = create_message(user_username, "@av what is the chemical formula for water?")
            print_chat_message(user_username, akashvani_query_message['text'])
            ws.send_text(json.dumps(akashvani_query_message))

            json.loads(ws.receive_text()) # Consume echo of user's query

            akashvani_response = json.loads(ws.receive_text())
            print_chat_message(akashvani_response["username"], akashvani_response["text"], is_akashvani=True)
            
            evaluation_result = await evaluate_akashvani_response(expected_behavior, akashvani_response["text"])
            
            print(f"  [LLM Judge Result] Status: {evaluation_result['status']}")
            if evaluation_result['status'] == "FAIL":
                print(f"  [LLM Judge Reason] Reason: {evaluation_result['reason']}")

            assert evaluation_result['status'] == "PASS", \
                f"LLM Judge failed the response. Reason: {evaluation_result['reason']}"
        print("Test Result: PASSED\n")
    except Exception as e:
        print(f"Test Result: FAILED - {e}\n")
        pytest.fail(f"Test failed: {e}")
