# slack_connector.py
import os
import json
import logging
from typing import List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
from slack_sdk import WebClient # type: ignore
from slack_sdk.errors import SlackApiError # type: ignore
from .connector_interface import ConnectorInterface

# Configure logging
logger = logging.getLogger("SlackConnector")

class SlackConnector(ConnectorInterface):
    """Slack connector to fetch messages from channels and conversations"""
    
    def __init__(self, token: str = None): # type: ignore
        """Initialize the Slack connector with token"""
        self.token = token or os.getenv("SLACK_BOT_TOKEN")
        self.client = None
        self.authenticated = False
    
    def authenticate(self) -> bool:
        """Authenticate with Slack API
        
        Returns:
            bool: True if authentication was successful, False otherwise
            
        Raises:
            ValueError: If Slack token is not provided
            Exception: For other authentication errors
        """
        try:
            if not self.token:
                logger.error("Slack token is required. Set SLACK_BOT_TOKEN in .env or pass token to constructor.")
                raise ValueError("Slack token is required. Set SLACK_BOT_TOKEN in .env or pass token to constructor.")
            
            self.client = WebClient(token=self.token)
            # Test the connection by getting basic info
            response = self.client.auth_test()
            logger.info(f"Connected to Slack as {response['user']} in workspace {response['team']}")
            self.authenticated = True
            return True
        except SlackApiError as e:
            logger.error(f"Authentication failed: {str(e)}")
            self.authenticated = False
            return False
        except Exception as e:
            logger.error(f"Unexpected error during Slack authentication: {e}")
            self.authenticated = False
            return False
    
    def fetch_data(self, channels: List[str] = None,  # type: ignore
                  days_history: int = 7, 
                  limit: int = 100, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch messages from Slack channels
        
        Args:
            channels: List of channel IDs or names to fetch from (if None, fetches from all accessible channels)
            days_history: Number of days of history to fetch
            limit: Maximum number of messages per channel
            
        Returns:
            List of message dictionaries
        """
        if not self.client:
            raise Exception("Not authenticated. Call authenticate() first.")
        
        all_messages = []
        
        # If no channels specified, get all accessible channels
        if not channels:
            try:
                response = self.client.conversations_list(types="public_channel,private_channel")
                channels = [channel["id"] for channel in response["channels"]]
            except Exception as e:
                print(f"Error listing channels: {str(e)}")
                return []
        
        # For each channel, get messages
        for channel_id in channels:
            try:
                # Get channel info for better context
                channel_info = self.client.conversations_info(channel=channel_id)
                channel_name = channel_info["channel"]["name"]
                
                # Get messages from the channel
                response = self.client.conversations_history(
                    channel=channel_id,
                    limit=limit
                )
                
                # Process each message
                for msg in response["messages"]:
                    # Skip bot messages and system messages if they don't have text
                    if "subtype" in msg and msg["subtype"] in ["bot_message", "channel_join"] and not msg.get("text"):
                        continue
                    
                    # Get user info for the message
                    user_id = msg.get("user")
                    user_name = "Unknown"
                    if user_id:
                        try:
                            user_info = self.client.users_info(user=user_id)
                            user_name = user_info["user"]["real_name"]
                        except:
                            pass
                    
                    # Create a message object
                    message = {
                        "id": msg.get("ts", ""),
                        "channel_id": channel_id,
                        "channel": channel_name,
                        "sender": user_name,
                        "timestamp": msg.get("ts", ""),
                        "message": msg.get("text", ""),
                        "thread_ts": msg.get("thread_ts", ""),
                        "reactions": msg.get("reactions", [])
                    }
                    
                    all_messages.append(message)
                    
                    # If this message has replies, get them too
                    if "thread_ts" in msg and msg["thread_ts"] == msg["ts"]:
                        try:
                            replies = self.client.conversations_replies(
                                channel=channel_id,
                                ts=msg["ts"],
                                limit=20  # Limit replies to avoid excessive API calls
                            )
                            
                            # Skip the first message as it's the parent we already processed
                            for reply in replies["messages"][1:]:
                                # Get user info for the reply
                                reply_user_id = reply.get("user")
                                reply_user_name = "Unknown"
                                if reply_user_id:
                                    try:
                                        reply_user_info = self.client.users_info(user=reply_user_id)
                                        reply_user_name = reply_user_info["user"]["real_name"]
                                    except:
                                        pass
                                
                                reply_message = {
                                    "id": reply.get("ts", ""),
                                    "channel_id": channel_id,
                                    "channel": channel_name,
                                    "sender": reply_user_name,
                                    "timestamp": reply.get("ts", ""),
                                    "message": reply.get("text", ""),
                                    "thread_ts": reply.get("thread_ts", ""),
                                    "parent_msg_id": msg["ts"],
                                    "reactions": reply.get("reactions", [])
                                }
                                
                                all_messages.append(reply_message)
                        except Exception as e:
                            print(f"Error fetching thread replies: {str(e)}")
            
            except Exception as e:
                print(f"Error fetching messages from channel {channel_id}: {str(e)}")
        
        return all_messages
    
    def process_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process and normalize the Slack data for embedding
        
        Args:
            data: Raw data from fetch_data()
            
        Returns:
            Processed data ready for embedding
        """
        processed_data = []
        
        for item in data:
            # Generate a unique ID for each message
            msg_id = f"slack_{item['id'].replace('.', '_')}"
            
            # Format the timestamp
            timestamp = item.get("timestamp", "")
            if timestamp:
                # Convert Slack timestamp (epoch seconds) to ISO format
                try:
                    ts_float = float(timestamp)
                    dt = datetime.fromtimestamp(ts_float)
                    timestamp = dt.isoformat()
                except:
                    pass
            
            # Create a document that matches our expected format
            document = {
                "id": msg_id,
                "sender": item.get("sender", "Unknown"),
                "timestamp": timestamp,
                "channel": item.get("channel", "Unknown"),
                "message": item.get("message", "")
            }
            
            # Add thread information if available
            if "thread_ts" in item and item["thread_ts"] != item.get("id"):
                document["thread_id"] = f"slack_{item['thread_ts'].replace('.', '_')}"
            
            processed_data.append(document)
        
        return processed_data


# Example usage
if __name__ == "__main__":
    load_dotenv()
    
    # Initialize and authenticate
    slack_connector = SlackConnector()
    if slack_connector.authenticate():
        # Fetch messages from specific channels or all accessible channels
        messages = slack_connector.fetch_data(
            limit=50  # Adjust as needed
        )
        
        # Process the data
        processed_messages = slack_connector.process_data(messages)
        
        # Save to a JSON file
        with open('slack_messages.json', 'w', encoding='utf-8') as f:
            json.dump(processed_messages, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Fetched and processed {len(processed_messages)} messages from Slack")
    else:
        print("❌ Authentication failed")