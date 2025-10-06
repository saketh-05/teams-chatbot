# query_brain.py (Corrected for persistence)

import os
from dotenv import load_dotenv
import google.generativeai as genai
import chromadb

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Connect to the PERSISTENT ChromaDB client
CHROMA_DB_PATH = "./chroma_db"
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

teams_collection = chroma_client.get_or_create_collection("teams_chat_knowledge")
jira_collection = chroma_client.get_or_create_collection("jira_tickets_knowledge")

# The maximum number of relevant documents to fetch from *each* source
N_RESULTS = 3

question = input("Ask your company brain (Teams/Jira): ")

# Embed the question
query_embedding = genai.embed_content(
    model="models/text-embedding-004",
    content=question
)["embedding"]

# --- 1. Query Teams with Hybrid Search ---
teams_results = teams_collection.query(
    query_embeddings=[query_embedding],
    query_texts=[question],
    n_results=N_RESULTS,
    include=['documents', 'metadatas']
)

# --- 2. Query Jira with Hybrid Search ---
jira_results = jira_collection.query(
    query_embeddings=[query_embedding],
    query_texts=[question],
    n_results=N_RESULTS,
    include=['documents', 'metadatas']
)

# --- 3. Compile Context and Sources ---
full_context = []
sources = []

# Compile Teams Context
for doc, meta in zip(teams_results["documents"][0], teams_results["metadatas"][0]):
    full_context.append(f"Source: Teams Channel #{meta['channel']}, Sender: {meta['sender']}\nContent: {doc}")
    sources.append(f"Teams: Channel #{meta['channel']} (Sender: {meta['sender']})")

# Compile Jira Context
for doc, meta in zip(jira_results["documents"][0], jira_results["metadatas"][0]):
    full_context.append(f"Source: Jira Ticket {meta['key']} ({meta['status']})\nContent: {doc}")
    sources.append(f"Jira: {meta['key']} ({meta['summary'].split('.')[0]})")

context_string = "\n\n---\n\n".join(full_context)

# Ask Gemini for the final answer
prompt = f"""
You are an AI knowledge platform (Memory Box) that answers technical questions based only on the provided context, which comes from company chat and ticket systems.
Synthesize a clear, single answer. DO NOT mention the confidence score.
Always summarize the sources used at the end of your answer.

CONTEXT (Teams & Jira):
{context_string}

Question: {question}
"""

response = genai.GenerativeModel("gemini-2.5-flash").generate_content(prompt)
print("\n🧠 Memory Box says:\n")
print(response.text)
print("\n---")
print("🔍 Found Context Sources:")
for source in list(set(sources)):
    print(f"- {source}")