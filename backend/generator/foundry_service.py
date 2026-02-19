import os
import time
from dotenv import load_dotenv

from azure.ai.projects import AIProjectClient
from azure.identity import ClientSecretCredential

load_dotenv()

ENDPOINT = os.getenv("FOUNDRY_ENDPOINT")
AGENT_ID = os.getenv("FOUNDRY_AGENT_ID")
PROJECT_NAME = os.getenv("FOUNDRY_PROJECT_NAME")

TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")


def _validate_env():
    required = {
        "FOUNDRY_ENDPOINT": ENDPOINT,
        "FOUNDRY_AGENT_ID": AGENT_ID,
        "FOUNDRY_PROJECT_NAME": PROJECT_NAME,
        "AZURE_TENANT_ID": TENANT_ID,
        "AZURE_CLIENT_ID": CLIENT_ID,
        "AZURE_CLIENT_SECRET": CLIENT_SECRET,
    }

    missing = [k for k, v in required.items() if not v]
    if missing:
        raise Exception(f"Missing environment variables: {', '.join(missing)}")


def generate_brd_tap(prompt: str) -> dict:
    """
    Calls Azure AI Foundry Agent and returns BRD + TAP.
    """

    _validate_env()

    credential = ClientSecretCredential(
        tenant_id=TENANT_ID,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
    )

    project_client = AIProjectClient(
        endpoint=ENDPOINT,
        credential=credential,
        project_name=PROJECT_NAME,
    )

    # 1️⃣ Create thread
    thread = project_client.agents.threads.create()

    # 2️⃣ Send user message
    project_client.agents.messages.create(
        thread_id=thread.id,
        role="user",
        content=prompt,
    )

    # 3️⃣ Run the agent
    run = project_client.agents.runs.create(
        thread_id=thread.id,
        agent_id=AGENT_ID,
    )

    # 4️⃣ Poll until finished
    while run.status in ("queued", "in_progress"):
        time.sleep(2)
        run = project_client.agents.runs.get(
            thread_id=thread.id,
            run_id=run.id,
        )

    if run.status != "completed":
        raise Exception(f"Agent run failed: {run.status}")

    # 5️⃣ Fetch messages (ItemPaged → list)
    messages = list(project_client.agents.messages.list(thread_id=thread.id))

    # 6️⃣ Get latest assistant response safely
    full_text = None

    for msg in reversed(messages):
        if msg.role == "assistant" and msg.content:
            # Azure Agents message structure
            for item in msg.content:
                if hasattr(item, "text") and item.text:
                    full_text = item.text.value
                    break
        if full_text:
            break

    if not full_text:
        raise Exception("No assistant response found.")

    brd, tap = split_documents(full_text)

    return {"brd": brd, "tap": tap}


def split_documents(text: str):
    brd_marker = "=== BRD ==="
    tap_marker = "=== TAP ==="

    if brd_marker in text and tap_marker in text:
        brd = text.split(brd_marker)[1].split(tap_marker)[0].strip()
        tap = text.split(tap_marker)[1].strip()
    else:
        brd = text
        tap = "TAP section not clearly generated."

    return brd, tap
