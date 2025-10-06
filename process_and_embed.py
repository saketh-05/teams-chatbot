# process_and_embed.py (with corrected Jira metadata)

import os, json
from dotenv import load_dotenv
import google.generativeai as genai
import chromadb

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

EMBEDDING_MODEL = "models/text-embedding-004"
CHROMA_DB_PATH = "./chroma_db"
if not os.path.exists(CHROMA_DB_PATH):
    os.makedirs(CHROMA_DB_PATH)
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH, settings=chromadb.Settings(anonymized_telemetry=False, is_persistent=True))
gemini_ef = chromadb.utils.embedding_functions.GoogleGenerativeAiEmbeddingFunction(api_key=os.getenv("GEMINI_API_KEY"), model_name=EMBEDDING_MODEL)

# --- 1. Process Teams Messages (no changes needed) ---
TEAM_MESSAGES_FILE = "teams_chat_poc_data_extended.json"
teams_collection = chroma_client.get_or_create_collection(
    "teams_chat_knowledge",
    embedding_function=gemini_ef
)

with open(TEAM_MESSAGES_FILE, "r", encoding="utf-8") as f:
    teams_messages = json.load(f)

print(f"Loading {len(teams_messages)} Teams messages...")

teams_ids = []
teams_documents = []
teams_metadatas = []

for i, msg in enumerate(teams_messages):
    document = f"Sender: {msg.get('sender', 'Unknown')} in Channel: {msg.get('channel', 'General')}. Message: {msg['message']}"
    
    teams_ids.append(msg["id"])
    teams_documents.append(document)
    teams_metadatas.append({
        "source": "Teams",
        "sender": msg.get("sender", "Unknown"),
        "channel": msg.get("channel", "General")
    })

teams_collection.add(
    ids=teams_ids,
    documents=teams_documents,
    metadatas=teams_metadatas
)
print(f"✅ Stored {len(teams_messages)} Teams messages in ChromaDB!")


# --- 2. Process Jira Tickets (metadata updated) ---
JIRA_TICKETS_FILE = "jira_tickets_poc_data_extended.json"
jira_collection = chroma_client.get_or_create_collection(
    "jira_tickets_knowledge",
    embedding_function=gemini_ef
)

with open(JIRA_TICKETS_FILE, "r", encoding="utf-8") as f:
    jira_tickets = json.load(f)

print(f"Loading {len(jira_tickets)} Jira tickets...")

jira_ids = []
jira_documents = []
jira_metadatas = []

for i, ticket in enumerate(jira_tickets):
    comments_text = "\n".join([f"Comment by {c['author']}: {c['body']}" for c in ticket.get("comments", [])])
    document = f"Ticket KEY: {ticket['key']}. Summary: {ticket['summary']}. Status: {ticket['status']}. Description: {ticket['description']}\nComments:\n{comments_text}"
    
    jira_ids.append(ticket["key"])
    jira_documents.append(document)
    jira_metadatas.append({
        "source": "Jira",
        "key": ticket["key"],
        "status": ticket["status"],
        "issueType": ticket["issueType"],
        "summary": ticket["summary"] # <-- ADDED: Now storing the summary
    })

jira_collection.add(
    ids=jira_ids,
    documents=jira_documents,
    metadatas=jira_metadatas
)
print(f"✅ Stored {len(jira_tickets)} Jira tickets in ChromaDB!")