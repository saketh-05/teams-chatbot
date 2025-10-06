import requests, os
from dotenv import load_dotenv

load_dotenv()
GRAPH_TOKEN = os.getenv("GRAPH_TOKEN")

TEAM_ID = "<your_team_id>"
CHANNEL_ID = "<your_channel_id>"

headers = {
    "Authorization": f"Bearer {GRAPH_TOKEN}",
    "Content-Type": "application/json"
}

message = input("Message to send on Teams: ")

url = f"https://graph.microsoft.com/v1.0/teams/{TEAM_ID}/channels/{CHANNEL_ID}/messages"
payload = {"body": {"content": message}}

res = requests.post(url, headers=headers, json=payload)
if res.status_code == 201:
    print("✅ Message sent successfully!")
else:
    print("❌ Failed:", res.text)
