# process_and_embed.py (Enhanced with connector integration)

import os, json
from dotenv import load_dotenv
import google.generativeai as genai
import chromadb
from connectors.connector_interface import ConnectorInterface
from connectors.drive_connector import DriveConnector
from connectors.slack_connector import SlackConnector
from connectors.github_connector import GitHubConnector

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Constants
EMBEDDING_MODEL = "models/text-embedding-004"
CHROMA_DB_PATH = "./chroma_db"
if not os.path.exists(CHROMA_DB_PATH):
    os.makedirs(CHROMA_DB_PATH)

# Initialize ChromaDB client
chroma_client = chromadb.PersistentClient(
    path=CHROMA_DB_PATH, 
    settings=chromadb.Settings(anonymized_telemetry=False, is_persistent=True) # type: ignore
)

# Initialize embedding function
gemini_ef = chromadb.utils.embedding_functions.GoogleGenerativeAiEmbeddingFunction( # type: ignore
    api_key=os.getenv("GEMINI_API_KEY"), 
    model_name=EMBEDDING_MODEL
)

def process_teams_data(file_path="data/teams_chat_poc_data_extended.json"):
    """Process Teams data from file or API"""
    teams_collection = chroma_client.get_or_create_collection(
        "teams_chat_knowledge",
        embedding_function=gemini_ef
    )
    
    with open(file_path, "r", encoding="utf-8") as f:
        teams_messages = json.load(f)

    print(f"Loading {len(teams_messages)} Teams messages...")

    teams_ids = []
    teams_documents = []
    teams_metadatas = []

    for msg in teams_messages:
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

def process_jira_data(file_path="data/jira_tickets_poc_data_extended.json"):
    """Process Jira data from file or API"""
    jira_collection = chroma_client.get_or_create_collection(
        "jira_tickets_knowledge",
        embedding_function=gemini_ef
    )
    
    with open(file_path, "r", encoding="utf-8") as f:
        jira_tickets = json.load(f)

    print(f"Loading {len(jira_tickets)} Jira tickets...")

    jira_ids = []
    jira_documents = []
    jira_metadatas = []

    for ticket in jira_tickets:
        comments_text = "\n".join([f"Comment by {c['author']}: {c['body']}" for c in ticket.get("comments", [])])
        document = f"Ticket KEY: {ticket['key']}. Summary: {ticket['summary']}. Status: {ticket['status']}. Description: {ticket['description']}\nComments:\n{comments_text}"
        
        jira_ids.append(ticket["key"])
        jira_documents.append(document)
        jira_metadatas.append({
            "source": "Jira",
            "key": ticket["key"],
            "status": ticket["status"],
            "issueType": ticket["issueType"],
            "summary": ticket["summary"]
        })

    jira_collection.add(
        ids=jira_ids,
        documents=jira_documents,
        metadatas=jira_metadatas
    )
    print(f"✅ Stored {len(jira_tickets)} Jira tickets in ChromaDB!")

def process_connector_data(connector: ConnectorInterface, collection_name: str, **kwargs):
    """Process data from any connector implementing the ConnectorInterface"""
    collection = chroma_client.get_or_create_collection(
        collection_name,
        embedding_function=gemini_ef
    )
    
    # Run the connector pipeline to get processed data
    try:
        processed_data = connector.run_pipeline(**kwargs)
        print(f"Fetched {len(processed_data)} items from {connector.__class__.__name__}")
        
        # Prepare data for ChromaDB
        ids = []
        documents = []
        metadatas = []
        
        for item in processed_data:
            # Extract common fields
            item_id = item.get("id", f"{collection_name}_{len(ids)}")
            
            # Create document text based on the data structure
            if "message" in item:
                # For message-based data (Slack, Teams)
                document = f"Sender: {item.get('sender', 'Unknown')} in {item.get('channel', 'Unknown')}. Message: {item['message']}"
            elif "title" in item and "message" in item:
                # For document-based data (Drive)
                document = f"Title: {item['title']}. Owner: {item.get('owner', 'Unknown')}. Content: {item['message']}"
            else:
                # Generic fallback
                document = json.dumps({k: v for k, v in item.items() if k != "id"})
            
            # Add to collections
            ids.append(item_id)
            documents.append(document)
            metadatas.append({k: v for k, v in item.items() if k != "message" and isinstance(v, (str, int, float, bool))})
        
        # Add to ChromaDB
        if ids:
            collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            print(f"✅ Stored {len(ids)} items in ChromaDB collection '{collection_name}'!")
        else:
            print("⚠️ No data to store in ChromaDB.")
            
        return len(ids)
    
    except Exception as e:
        print(f"❌ Error processing data from {connector.__class__.__name__}: {str(e)}")
        return 0

def main():
    """Main function to run the data processing pipeline"""
    # Process Teams data (from file for now)
    process_teams_data()
    
    # Process Jira data (from file for now)
    process_jira_data()
    
    # Process Google Drive data (if credentials available)
    # if os.path.exists("credentials.json"):
    #     try:
    #         drive_connector = DriveConnector()
    #         process_connector_data(
    #             drive_connector, 
    #             "drive_documents_knowledge",
    #             max_results=50,  # Adjust as needed
    #             file_types=['application/vnd.google-apps.document', 'text/plain']
    #         )
    #     except Exception as e:
    #         print(f"❌ Error processing Drive data: {str(e)}")
    # else:
    #     print("⚠️ Google Drive credentials not found. Skipping Drive connector.")
    
    # Process Slack data (if token available)
    if os.getenv("SLACK_BOT_TOKEN"):
        try:
            slack_connector = SlackConnector()
            process_connector_data(
                slack_connector, 
                "slack_messages_knowledge",
                limit=100  # Adjust as needed
            )
        except Exception as e:
            print(f"❌ Error processing Slack data: {str(e)}")
    else:
        print("⚠️ Slack token not found. Skipping Slack connector.")
        
    # Process GitHub data (if token available)
    if os.getenv("GITHUB_ACCESS_TOKEN"):
        try:
            github_connector = GitHubConnector()
            process_connector_data(
                github_connector,
                "github_knowledge",
                repos=["saketh-05/teams-chatbot", "saketh-05/codesen"],
                include_issues=True,
                include_prs=True,
                include_readme=True,
                max_items=50
            )
        except Exception as e:
            print(f"❌ Error processing GitHub data: {str(e)}")
    else:
        print("⚠️ GitHub token not found. Skipping GitHub connector.")
    
    print("\n✅ All data sources processed and embedded successfully!")

if __name__ == "__main__":
    main()