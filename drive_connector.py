# drive_connector.py
import os
import json
import logging
from typing import List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from connector_interface import ConnectorInterface

# Configure logging
logger = logging.getLogger("DriveConnector")

class DriveConnector(ConnectorInterface):
    """Google Drive connector to fetch documents and their content"""
    
    # Define the scopes needed for Google Drive API
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    
    def __init__(self, credentials_file: str = 'credentials.json', token_file: str = 'token.json'):
        """Initialize the Drive connector with credential paths"""
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self.authenticated = False
    
    def authenticate(self) -> bool:
        """Authenticate with Google Drive API
        
        Returns:
            bool: True if authentication was successful, False otherwise
            
        Raises:
            FileNotFoundError: If credentials file doesn't exist
            Exception: For other authentication errors
        """
        try:
            if not os.path.exists(self.credentials_file):
                logger.error(f"Credentials file not found: {self.credentials_file}")
                raise FileNotFoundError(f"Credentials file not found: {self.credentials_file}")
                
            creds = None
            
            # Check if token file exists
            if os.path.exists(self.token_file):
                try:
                    with open(self.token_file, 'r') as token:
                        creds = Credentials.from_authorized_user_info(
                            json.load(token), self.SCOPES)
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Invalid token file, will re-authenticate: {str(e)}")
                    # If token file is invalid, we'll re-authenticate below
            
            # If credentials don't exist or are invalid, get new ones
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    logger.info("Refreshing expired credentials")
                    creds.refresh(Request())
                else:
                    logger.info("Starting new authentication flow")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, self.SCOPES)
                    creds = flow.run_local_server(port=0)
                
                # Save the credentials for future use
                with open(self.token_file, 'w') as token:
                    token.write(creds.to_json())
                    logger.info(f"Saved new credentials to {self.token_file}")
            
            # Build the Drive service
            self.service = build('drive', 'v3', credentials=creds)
            self.authenticated = True
            logger.info("Successfully authenticated with Google Drive")
            return True
            
        except FileNotFoundError as e:
            logger.error(f"Authentication failed - file not found: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            self.authenticated = False
            return False
    
    def fetch_data(self, query: str = None, max_results: int = 100, 
                  file_types: List[str] = None, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch documents from Google Drive
        
        Args:
            query: Search query for Drive files (optional)
            max_results: Maximum number of results to return
            file_types: List of MIME types to filter by (e.g. 'application/pdf')
        
        Returns:
            List of document dictionaries with metadata
        """
        if not self.service:
            raise Exception("Not authenticated. Call authenticate() first.")
        
        # Build the query string
        query_parts = []
        if query:
            query_parts.append(f"fullText contains '{query}'")
        
        if file_types:
            mime_type_conditions = [f"mimeType='{mime_type}'" for mime_type in file_types]
            query_parts.append(f"({' or '.join(mime_type_conditions)})")
        
        # Only include files, not folders
        query_parts.append("mimeType != 'application/vnd.google-apps.folder'")
        
        # Combine all query parts
        query_string = " and ".join(query_parts) if query_parts else ""
        
        # Execute the query
        results = []
        page_token = None
        
        while True:
            response = self.service.files().list(
                q=query_string,
                spaces='drive',
                fields='nextPageToken, files(id, name, mimeType, description, createdTime, modifiedTime, owners)',
                pageToken=page_token,
                pageSize=min(max_results, 100)  # API limit is 100 per page
            ).execute()
            
            results.extend(response.get('files', []))
            
            # Check if we have more pages and if we've reached max_results
            page_token = response.get('nextPageToken')
            if not page_token or len(results) >= max_results:
                break
        
        # Fetch content for each document (where possible)
        for item in results:
            try:
                # For Google Docs, Sheets, etc. we need to export them
                if item['mimeType'].startswith('application/vnd.google-apps'):
                    if item['mimeType'] == 'application/vnd.google-apps.document':
                        content = self.service.files().export(
                            fileId=item['id'], mimeType='text/plain').execute().decode('utf-8')
                    else:
                        content = f"[Content not extracted for {item['mimeType']}]"
                else:
                    # For regular files, download the content if it's text-based
                    if item['mimeType'].startswith('text/') or 'pdf' in item['mimeType']:
                        content = self.service.files().get_media(fileId=item['id']).execute().decode('utf-8')
                    else:
                        content = f"[Binary content for {item['mimeType']}]"
                
                item['content'] = content
            except Exception as e:
                item['content'] = f"[Error extracting content: {str(e)}]"
        
        return results[:max_results]
    
    def process_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process and normalize the Drive data for embedding
        
        Args:
            data: Raw data from fetch_data()
            
        Returns:
            Processed data ready for embedding
        """
        processed_data = []
        
        for i, item in enumerate(data):
            # Generate a unique ID for each document
            doc_id = f"drive_{item['id']}"
            
            # Extract owner information
            owner = item.get('owners', [{}])[0].get('displayName', 'Unknown') if 'owners' in item else 'Unknown'
            
            # Format dates
            created_time = item.get('createdTime', '')
            if created_time:
                created_time = datetime.fromisoformat(created_time.replace('Z', '+00:00')).isoformat()
            
            # Create a document that matches our expected format
            document = {
                "id": doc_id,
                "source": "Google Drive",
                "title": item.get('name', 'Untitled'),
                "owner": owner,
                "created": created_time,
                "type": item.get('mimeType', 'unknown'),
                "message": item.get('content', '')
            }
            
            processed_data.append(document)
        
        return processed_data


# Example usage
if __name__ == "__main__":
    load_dotenv()
    
    # Initialize and authenticate
    drive_connector = DriveConnector()
    if drive_connector.authenticate():
        # Fetch documents (e.g., only Google Docs)
        docs = drive_connector.fetch_data(
            max_results=10,
            file_types=['application/vnd.google-apps.document']
        )
        
        # Process the data
        processed_docs = drive_connector.process_data(docs)
        
        # Save to a JSON file
        with open('drive_docs.json', 'w', encoding='utf-8') as f:
            json.dump(processed_docs, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Fetched and processed {len(processed_docs)} documents from Google Drive")
    else:
        print("❌ Authentication failed")