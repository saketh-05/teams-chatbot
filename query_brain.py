import os
from dotenv import load_dotenv
import google.generativeai as genai
import chromadb

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection("teams_messages")

question = input("Ask your company brain: ")

# Embed the question
query_embedding = genai.embed_content(
    model="models/text-embedding-004",
    content=question
)["embedding"]

# Query nearest documents
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=5
)

context = "\n\n".join(results["documents"][0]) # type: ignore

# Ask Gemini for answer
prompt = f"""
You are an AI assistant with access to company conversations from Microsoft Teams.

Answer the question based only on the following context:
{context}

Question: {question}
"""

response = genai.GenerativeModel("gemini-1.5-flash").generate_content(prompt)
print("\n🧠 Company Brain says:\n", response.text)
