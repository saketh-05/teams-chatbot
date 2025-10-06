# drive_connector.py
import os
import json
import logging
from typing import List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow # type: ignore
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from .connector_interface import ConnectorInterface

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
    
    def fetch_data(self, folder_name: str = None, max_results: int = 100, # type: ignore
                file_types: List[str] = None, **kwargs) -> List[Dict[str, Any]]: # type: ignore
        """
        Fetch documents from Google Drive

        Args:
            folder_name: Name of the folder to fetch files from
            max_results: Maximum number of results to return
            file_types: List of MIME types to filter by (e.g. ['application/pdf'])

        Returns:
            List of document dictionaries with metadata
        """
        if not self.service:
            raise Exception("Not authenticated. Call authenticate() first.")

        # --- Step 1: Find folder ID if folder_name is given ---
        folder_query = ""
        if folder_name:
            try:
                folder_result = self.service.files().list(
                    q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'",
                    spaces='drive',
                    fields='files(id, name)',
                ).execute()

                if not folder_result['files']:
                    raise Exception(f"❌ Folder '{folder_name}' not found in your Drive.")

                folder_id = folder_result['files'][0]['id']
                folder_query = f"'{folder_id}' in parents"
            except Exception as e:
                logger.error(f"Error locating folder '{folder_name}': {str(e)}")
                raise

        # --- Step 2: Build MIME type filter ---
        mime_query = ""
        if file_types:
            mime_conditions = [f"mimeType='{m}'" for m in file_types]
            mime_query = "(" + " or ".join(mime_conditions) + ")"

        # --- Step 3: Combine all conditions ---
        query_parts = [q for q in [folder_query, mime_query, "mimeType != 'application/vnd.google-apps.folder'"] if q]
        query_string = " and ".join(query_parts)

        # --- Step 4: Execute Drive API request ---
        results = []
        page_token = None

        while True:
            response = self.service.files().list(
                q=query_string,
                spaces='drive',
                fields='nextPageToken, files(id, name, mimeType, description, createdTime, modifiedTime, owners)',
                pageToken=page_token,
                pageSize=min(max_results, 100)
            ).execute()

            results.extend(response.get('files', []))
            page_token = response.get('nextPageToken')

            if not page_token or len(results) >= max_results:
                break

        # --- Step 5: Extract or export content for each file ---
        for item in results:
            try:
                if item['mimeType'] == 'application/vnd.google-apps.document':
                    content = self.service.files().export(
                        fileId=item['id'], mimeType='text/plain').execute().decode('utf-8')
                elif item['mimeType'].startswith('text/'):
                    content = self.service.files().get_media(fileId=item['id']).execute().decode('utf-8')
                elif item['mimeType'] == 'application/pdf':
                    content = "[PDF content not extracted in this version]"
                else:
                    content = f"[Unsupported type: {item['mimeType']}]"

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