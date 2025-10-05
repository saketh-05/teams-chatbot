import requests, os
from dotenv import load_dotenv

load_dotenv()
GRAPH_TOKEN = os.getenv("GRAPH_TOKEN")

# Example: get messages from a specific Team channel
TEAM_ID = "<your_team_id>"
CHANNEL_ID = "<your_channel_id>"

headers = {
    "Authorization": f"Bearer {GRAPH_TOKEN}",
    "Content-Type": "application/json"
}

url = f"https://graph.microsoft.com/v1.0/teams/{TEAM_ID}/channels/{CHANNEL_ID}/messages"

def fetch_messages():
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    
    messages = []
    for item in data.get("value", []):
        text = item.get("body", {}).get("content", "")
        messages.append({
            "id": item["id"],
            "from": item.get("from", {}).get("user", {}).get("displayName", "Unknown"),
            "text": text
        })
    
    print(f"Fetched {len(messages)} messages")
    return messages

if __name__ == "__main__":
    msgs = fetch_messages()
    import json
    with open("teams_messages.json", "w", encoding="utf-8") as f:
        json.dump(msgs, f, indent=2, ensure_ascii=False)
    print("✅ Saved to teams_messages.json")
