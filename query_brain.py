# query_brain.py (Enhanced with multi-source integration)

import os
from dotenv import load_dotenv
import google.generativeai as genai
import chromadb

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Connect to the PERSISTENT ChromaDB client
CHROMA_DB_PATH = "./chroma_db"
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

# Default number of results to fetch from each source
DEFAULT_N_RESULTS = 3

def get_available_collections():
    """Get all available knowledge collections"""
    return chroma_client.list_collections()

def query_collection(collection_name, query_text, query_embedding, n_results=DEFAULT_N_RESULTS):
    """Query a specific collection with hybrid search"""
    try:
        collection = chroma_client.get_collection(collection_name)
        results = collection.query(
            query_embeddings=[query_embedding],
            query_texts=[query_text],
            n_results=n_results,
            include=['documents', 'metadatas'] # type: ignore
        )
        return results
    except Exception as e:
        print(f"Error querying collection {collection_name}: {str(e)}")
        return {"documents": [[]], "metadatas": [[]]}

def format_context(results, collection_name):
    """Format context and sources from query results"""
    context = []
    sources = []
    
    if not results["documents"][0]:
        return [], []
    
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        if collection_name == "teams_chat_knowledge":
            context.append(f"Source: Teams Channel #{meta.get('channel', 'Unknown')}, Sender: {meta.get('sender', 'Unknown')}\nContent: {doc}")
            sources.append(f"Teams: Channel #{meta.get('channel', 'Unknown')} (Sender: {meta.get('sender', 'Unknown')})")
        
        elif collection_name == "jira_tickets_knowledge":
            context.append(f"Source: Jira Ticket {meta.get('key', 'Unknown')} ({meta.get('status', 'Unknown')})\nContent: {doc}")
            sources.append(f"Jira: {meta.get('key', 'Unknown')} ({meta.get('summary', '').split('.')[0] if meta.get('summary') else 'Unknown'})")
        
        elif collection_name == "slack_messages_knowledge":
            context.append(f"Source: Slack Channel #{meta.get('channel', 'Unknown')}, Sender: {meta.get('sender', 'Unknown')}\nContent: {doc}")
            sources.append(f"Slack: Channel #{meta.get('channel', 'Unknown')} (Sender: {meta.get('sender', 'Unknown')})")
        
        elif collection_name == "drive_documents_knowledge":
            context.append(f"Source: Google Drive Document '{meta.get('title', 'Unknown')}', Owner: {meta.get('owner', 'Unknown')}\nContent: {doc}")
            sources.append(f"Drive: {meta.get('title', 'Unknown')} (Owner: {meta.get('owner', 'Unknown')})")
        
        elif collection_name == "github_knowledge":
            if 'type' in meta and meta['type'] in ['issue', 'pull_request']:
                context.append(f"Source: GitHub {meta['type'].replace('_', ' ').title()} '{meta.get('title', 'Unknown')}'\nContent: {doc}")
                sources.append(f"GitHub: {meta['type'].replace('_', ' ').title()} #{meta.get('title', 'Unknown').split(' - ')[0] if meta.get('title') else 'Unknown'}")
            else:
                context.append(f"Source: GitHub Repository Item\nContent: {doc}")
                sources.append(f"GitHub: {meta}")
        else:
            # Generic handling for any other collection
            source_type = collection_name.replace("_knowledge", "").title()
            context.append(f"Source: {source_type}\nContent: {doc}")
            sources.append(f"{source_type}: {meta.get('id', 'Unknown')}")
    
    return context, sources

def main():
    """Main function to query the brain"""

    i = 0
    while i < 5:
        # Get the question from command line or input
        question = input("Ask your company brain from any of the following sources (Teams/Jira/Slack/Drive/GitHub): ")
        sources_input = input("Specify sources to query (space-separated, e.g., Teams Jira) or leave blank for all: ")
        n_results_input = input(f"Number of results per source (default {DEFAULT_N_RESULTS}): ")

        if not n_results_input.isdigit():
            print("Invalid input for number of results. Using default value.")
            n_results_input = str(DEFAULT_N_RESULTS)
        
        n_results = int(n_results_input) if n_results_input else DEFAULT_N_RESULTS
        sources = sources_input.split() if sources_input else []
        sources = [s.lower() for s in sources]
        valid_sources = ["teams", "jira", "slack", "drive", "github"]
        for s in sources:
            if s not in valid_sources:
                print(f"Warning: '{s}' is not a recognized source. Valid options are: {'  '.join(valid_sources)}.")

        # Embed the question
        query_embedding = genai.embed_content(
            model="models/text-embedding-004",
            content=question
        )["embedding"]
        
        # Get available collections
        available_collections = [c.name for c in get_available_collections()]
        print(f"Available knowledge sources: {', '.join(available_collections)}")
        
        # Filter collections if sources are specified
        if sources:
            source_map = {
                "teams": "teams_chat_knowledge",
                "jira": "jira_tickets_knowledge",
                "slack": "slack_messages_knowledge",
                "drive": "drive_documents_knowledge",
                "github": "github_knowledge"
            }
            collections_to_query = [source_map.get(s, s) for s in sources if source_map.get(s, s) in available_collections]
        else:
            collections_to_query = available_collections
        
        # Query each collection
        all_context = []
        all_sources = []
        
        for collection_name in collections_to_query:
            print(f"Querying {collection_name}...")
            results = query_collection(collection_name, question, query_embedding, n_results)
            context, sources = format_context(results, collection_name)
            all_context.extend(context)
            all_sources.extend(sources)
            
        if not all_context:
            print("No relevant information found in any knowledge source.")
            return
        
        # Compile all context
        context_string = "\n\n---\n\n".join(all_context)
        
        # Ask Gemini for the final answer
        prompt = f"""
            You are an AI knowledge platform (Memory Box) that answers technical questions based only on the provided context, which comes from company knowledge sources.
            Synthesize a clear, single answer. DO NOT mention the confidence score.
            Always summarize the sources used at the end of your answer.

            CONTEXT (Knowledge Sources):
            {context_string}

            Question: {question}
        """

        response = genai.GenerativeModel("gemini-2.5-flash").generate_content(prompt)
        print("\n🧠 Memory Box says:\n")
        print(response.text)
        print("\n---")
        print("🔍 Found Context Sources:")
        for source in list(set(all_sources)):
            print(f"- {source}")
            
        i += 1
        
if __name__ == "__main__":
    main()