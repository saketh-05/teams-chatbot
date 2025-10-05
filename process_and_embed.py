import os, json
from dotenv import load_dotenv
import google.generativeai as genai
import chromadb

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Initialize ChromaDB
chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection("teams_messages")

# Load Teams messages from JSON
with open("teams_messages.json", "r", encoding="utf-8") as f:
    messages = json.load(f)

# Create embeddings using Gemini
def embed_texts(texts):
    model = "models/text-embedding-004"  # Gemini embedding model
    embeddings = genai.embed_content(model=model, content=texts)["embedding"]
    return embeddings

# Store in ChromaDB
for i, msg in enumerate(messages):
    text = msg["text"].strip()
    if not text:
        continue

    embedding = embed_texts(text)
    collection.add(
        ids=[str(i)],
        embeddings=[embedding],
        documents=[text],
        metadatas=[{"sender": msg.get("from", "Unknown")}]
    )

print(f"✅ Stored {len(messages)} messages in ChromaDB!")
