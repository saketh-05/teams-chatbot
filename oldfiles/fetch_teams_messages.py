import requests
from dotenv import load_dotenv

load_dotenv()
ACCESS_TOKEN = "EwBoBMl6BAAUBKgm8k1UswUNwklmy2v7U/S+1fEAARPn0aR3oq1uFfqM+v5PdLfqRd04+2e0yp7TPu4jPq00MMawroeGM0ekyhYVXejlgPybpj+YEygWeQ4CVKHjVh4c3LLKUIwE51GsDRHGmqfg7uay99uX23VcMugVQ5NgK5Bdcufl56Z2KqcCYBsua3NJw/3rtI7rt003JuYuRkXMzh06qZJF3fhAn+caGFrpAqow6xfq2P9dj6wqpkYIPkksPsQA1AGe9GTUW7b/YqRTkSl2xvAfBelgqLFu3BBYszEdISATST5cGl0xJCjhWFQ3DWpaEbMESFRchZknoRhU6CxO2go+2e1YXuQuIxFX0oEjHLEmtdMcVoB32EDgmm8QZgAAEAgsWQVxvs53qFBg0I56DRgwAyHNwWec/Z2QICwIQz7Ow/gcCmEku87eEYA/a6ns9R+rNct9ooQLM1oEemFWOmEs2hw94CcuGmiXXoDuCNn14uSx4URLW+zPxSqDo3GQLWPTQwqZpLIVE6KzxneOMmMqJ6FdOoBZuAxd2XWM+fs6v3qwHiSdjfKeph35geZyp8hXs/1NbOPN0p4K15LsYT0ogjKAVEVx9P5mWY9aNQHT+Tp3KYIE0+zmwSHcC4qoNz/Td8WWs5kWUszh8B0sY9jF8HgYsgOFccshhnXK82llLD+KfspPFQM64ZowQkK8h5AMkQ9DpgSM2Kd8oSlw4EW6k7tfcJA+2D8qlcVHDJX1BeScGysjDzT6hvqnTjjOEQuPbX2Jp3iDauMm0GyJorebmBBIiIoFDz1qFB7tddQi5oYnJImXMDR/M9oFqrvb6bTdXmpZifk2ksa80v0BbWtztK8m3bHqjCX1KG4uXLsBHljANnx+wMo8YdRb5G0holLG71pMOMPvU0piaVA/RO2Pa4IPDzo+VumbGrGbGsY/a59n7MB+6wP4VtUOXRlDcEo1YSzecT+2Yqg2qiZ8u9Ff4YK7DPT4NJx11y1od7hewq/jMjwJA0NexghTVZ5S9Hzm6wzvWSyVZ0KlMp3dRV6q9bIbwmzbYEByHB/hnaeGBXQ3VwetdE89/hRei1H1eZOIiiCKG1egsQmJc/V4MFhJLobh2RHVvqr+OfznSmJ4zVQUCs9slMeiwfqxoGLOLMwxFuggpIH96ZKlLd5Q740pHHbOB6/RtSuf8HKy+3Pwxzwt1HS2IzIKGPJpaspDwWWyb9xz6YJF9LUIDWBfYS9WBTdxufRste3ZhhHSSRVqVY33MEZB12YeFiNc3A9afCqO50MXbOWDzooROtzLOsd1ZddYHMxyEUdS9OBlL8pmov6gp77mh8HKz7pwc3B6x/3ZDXEtXM+a/D1F3//ZISlmnqX6uj6ueJ2um4mg1dE5lWbz16lPqM4gPjn62uTMgAK0oNjmfCsm3JigdzuWZNoAmXcWbYvuNHZKN2h+IcxDDpbZm0GzjW0lduXaq0ChQbLLdSegC9HjtnJpp9ffJCL8j3gD"

# Example: get messages from a specific Team channel
# TEAM_ID = "<your_team_id>"
# CHANNEL_ID = "<your_channel_id>"

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}"
}

# url = f"https://graph.microsoft.com/v1.0/teams/{TEAM_ID}/channels/{CHANNEL_ID}/messages"

# url = "https://graph.microsoft.com/v1.0/users/{user_id}/chats"

url = "https://graph.microsoft.com/v1.0/me/chats"


# def fetch_messages():
#     response = requests.get(url, headers=headers)
#     # response.raise_for_status()
#     # data = response.json()
    
#     print(f"Response Data: {response.json()}")  # Debugging line to inspect the response structure
#     # messages = []
#     # for item in data.get("value", []):
#     #     text = item.get("body", {}).get("content", "")
#     #     messages.append({
#     #         "id": item["id"],
#     #         "from": item.get("from", {}).get("user", {}).get("displayName", "Unknown"),
#     #         "text": text
#     #     })
    
#     # print(f"Fetched {len(messages)} messages")
#     # return messages

def fetch_messages():
    response = requests.get(url, headers=headers)
    data = response.json()
    print(data)

if __name__ == "__main__":
    msgs = fetch_messages()
    # import json
    # with open("teams_messages.json", "w", encoding="utf-8") as f:
    #     json.dump(msgs, f, indent=2, ensure_ascii=False)
    # print("✅ Saved to teams_messages.json")
