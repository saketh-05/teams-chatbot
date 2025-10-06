# MEMORY BOX SETUP GUIDE

This document provides step-by-step instructions for setting up API keys and credentials for all connectors used in the Memory Box system.

## 1. SLACK API SETUP

1. Go to https://api.slack.com/apps
2. Click "Create New App" → "From scratch"
3. Name your app (e.g., "Memory Box") and select your workspace
4. Under "OAuth & Permissions", add these scopes:
   - channels:history
   - channels:read
   - chat:write
   - groups:history
   - groups:read
   - users:read
5. Install the app to your workspace
6. Copy the "Bot User OAuth Token" that starts with "xoxb-"
7. Add to your environment:
   ```
   SLACK_BOT_TOKEN=xoxb-your-token-here
   ```
   
   You can either:
   - Create a .env file in the project root with this line
   - Set it as an environment variable in your system
   - Add it directly to config.json in the slack section

## 2. GOOGLE DRIVE API SETUP

1. Go to https://console.cloud.google.com/
2. Create a new project
3. Enable the Google Drive API:
   - Go to "APIs & Services" → "Library"
   - Search for "Google Drive API"
   - Click "Enable"
4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth client ID"
   - Application type: Desktop app
   - Name: Memory Box
5. Download the credentials JSON file
6. Save it as "credentials.json" in your project root directory
7. First run will prompt you to authorize in browser:
   - When you run the application, it will open a browser window
   - Sign in with your Google account
   - Grant permissions to access your Drive
   - A token.json file will be created automatically

## 3. GITHUB API SETUP

1. Go to https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Give it a name (e.g., "Memory Box")
4. Select scopes:
   - repo (for private repos)
   - read:user
5. Copy the generated token
6. Add to your environment:
   ```
   GITHUB_ACCESS_TOKEN=ghp_your_token_here
   ```
7. Edit config.json to add your repositories:
   ```json
   "github": {
     "enabled": true,
     "token_env": "GITHUB_ACCESS_TOKEN",
     "repositories": ["username/repo1", "username/repo2"]
   }
   ```

## TESTING YOUR CONNECTIONS

To test all connections at once:
```
python process_and_embed.py
```

To test individual connections:

1. For GitHub:
```python
from github_connector import GitHubConnector
connector = GitHubConnector()
print(f"Authentication successful: {connector.authenticate()}")
```

2. For Google Drive:
```python
from drive_connector import GoogleDriveConnector
connector = GoogleDriveConnector()
print(f"Authentication successful: {connector.authenticate()}")
```

3. For Slack:
```python
from slack_connector import SlackConnector
connector = SlackConnector()
print(f"Authentication successful: {connector.authenticate()}")
```

## TROUBLESHOOTING

1. Slack API Issues:
   - Ensure your bot has been invited to the channels you want to access
   - Check that all required scopes are granted
   - Verify the token is correct and not expired

2. Google Drive API Issues:
   - If authentication fails, delete token.json and try again
   - Ensure you've enabled the Google Drive API in your project
   - Check that credentials.json is in the correct location

3. GitHub API Issues:
   - Ensure your token has the correct permissions
   - Check that the repositories listed in config.json are accessible with your token
   - Verify the token is not expired

## CONFIGURATION FILE STRUCTURE

The config.json file should have this structure:
```json
{
  "connectors": {
    "google_drive": {
      "enabled": true,
      "credentials_file": "credentials.json",
      "token_file": "token.json",
      "scopes": ["https://www.googleapis.com/auth/drive.readonly"]
    },
    "slack": {
      "enabled": true,
      "bot_token_env": "SLACK_BOT_TOKEN"
    },
    "github": {
      "enabled": true,
      "token_env": "GITHUB_ACCESS_TOKEN",
      "repositories": ["username/repo1", "username/repo2"]
    }
  }
}
```

For any questions or issues, please refer to the documentation for each API:
- Slack API: https://api.slack.com/docs
- Google Drive API: https://developers.google.com/drive/api/guides/about-sdk
- GitHub API: https://docs.github.com/en/rest