# config_manager.py
# Handles configuration and credentials for all connectors

import os
import json
from dotenv import load_dotenv
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("memory_box.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ConfigManager")

class ConfigManager:
    """
    Manages configuration and credentials for all connectors in Memory Box
    """
    
    def __init__(self, config_file="config.json"):
        """Initialize the configuration manager"""
        # Load environment variables
        load_dotenv()
        
        self.config_file = config_file
        self.config = self._load_config()
        
        # Initialize default config structure if not exists
        if not self.config:
            self.config = {
                "connectors": {
                    "google_drive": {
                        "enabled": False,
                        "credentials_file": "credentials.json",
                        "token_file": "token.json",
                        "scopes": ["https://www.googleapis.com/auth/drive.readonly"]
                    },
                    "slack": {
                        "enabled": False,
                        "bot_token_env": "SLACK_BOT_TOKEN"
                    },
                    "github": {
                        "enabled": False,
                        "token_env": "GITHUB_ACCESS_TOKEN",
                        "repositories": []
                    },
                    "teams": {
                        "enabled": False,
                        "client_id_env": "TEAMS_CLIENT_ID",
                        "client_secret_env": "TEAMS_CLIENT_SECRET"
                    },
                    "jira": {
                        "enabled": False,
                        "url_env": "JIRA_URL",
                        "username_env": "JIRA_USERNAME",
                        "api_token_env": "JIRA_API_TOKEN"
                    }
                },
                "embedding": {
                    "model": "models/text-embedding-004",
                    "api_key_env": "GEMINI_API_KEY",
                    "chunk_size": 1000,
                    "chunk_overlap": 200
                },
                "database": {
                    "chroma_path": "./chroma_db"
                }
            }
            self._save_config()
    
    def _load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            return {}
    
    def _save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Configuration saved to {self.config_file}")
        except Exception as e:
            logger.error(f"Error saving config: {str(e)}")
    
    def get_connector_config(self, connector_name):
        """Get configuration for a specific connector"""
        try:
            return self.config["connectors"].get(connector_name, {})
        except KeyError:
            logger.error(f"Connector {connector_name} not found in configuration")
            return {}
    
    def get_embedding_config(self):
        """Get embedding configuration"""
        return self.config.get("embedding", {})
    
    def get_database_config(self):
        """Get database configuration"""
        return self.config.get("database", {})
    
    def update_connector_config(self, connector_name, config_updates):
        """Update configuration for a specific connector"""
        try:
            if connector_name not in self.config["connectors"]:
                self.config["connectors"][connector_name] = {}
            
            self.config["connectors"][connector_name].update(config_updates)
            self._save_config()
            logger.info(f"Updated configuration for {connector_name}")
            return True
        except Exception as e:
            logger.error(f"Error updating {connector_name} config: {str(e)}")
            return False
    
    def enable_connector(self, connector_name):
        """Enable a connector"""
        return self.update_connector_config(connector_name, {"enabled": True})
    
    def disable_connector(self, connector_name):
        """Disable a connector"""
        return self.update_connector_config(connector_name, {"enabled": False})
    
    def is_connector_enabled(self, connector_name):
        """Check if a connector is enabled"""
        try:
            return self.config["connectors"].get(connector_name, {}).get("enabled", False)
        except Exception:
            return False
    
    def get_credential(self, env_var_name, default=None):
        """Get a credential from environment variables"""
        value = os.getenv(env_var_name)
        if not value:
            logger.warning(f"Environment variable {env_var_name} not set")
        return value or default
    
    def check_connector_credentials(self, connector_name):
        """Check if all required credentials for a connector are available"""
        try:
            connector_config = self.get_connector_config(connector_name)
            
            if connector_name == "google_drive":
                credentials_file = connector_config.get("credentials_file")
                return os.path.exists(credentials_file) if credentials_file else False
            
            elif connector_name == "slack":
                token_env = connector_config.get("bot_token_env")
                return bool(self.get_credential(token_env)) if token_env else False
            
            elif connector_name == "teams":
                client_id_env = connector_config.get("client_id_env")
                client_secret_env = connector_config.get("client_secret_env")
                return bool(self.get_credential(client_id_env) and self.get_credential(client_secret_env))
            
            elif connector_name == "jira":
                url_env = connector_config.get("url_env")
                username_env = connector_config.get("username_env")
                api_token_env = connector_config.get("api_token_env")
                return bool(self.get_credential(url_env) and 
                           self.get_credential(username_env) and 
                           self.get_credential(api_token_env))
            
            return False
        except Exception as e:
            logger.error(f"Error checking credentials for {connector_name}: {str(e)}")
            return False
    
    def auto_configure_connectors(self):
        """Automatically configure connectors based on available credentials"""
        # Check Google Drive
        if os.path.exists("credentials.json"):
            self.enable_connector("google_drive")
            logger.info("Google Drive connector enabled (credentials.json found)")
        
        # Check Slack
        if os.getenv("SLACK_BOT_TOKEN"):
            self.enable_connector("slack")
            logger.info("Slack connector enabled (SLACK_BOT_TOKEN found)")
        
        # Check Teams
        if os.getenv("TEAMS_CLIENT_ID") and os.getenv("TEAMS_CLIENT_SECRET"):
            self.enable_connector("teams")
            logger.info("Teams connector enabled (credentials found)")
        
        # Check Jira
        if os.getenv("JIRA_URL") and os.getenv("JIRA_USERNAME") and os.getenv("JIRA_API_TOKEN"):
            self.enable_connector("jira")
            logger.info("Jira connector enabled (credentials found)")
        
        return self.get_enabled_connectors()
    
    def get_enabled_connectors(self):
        """Get list of enabled connectors"""
        enabled = []
        for connector in self.config.get("connectors", {}):
            if self.is_connector_enabled(connector):
                enabled.append(connector)
        return enabled

# Singleton instance
config_manager = ConfigManager()

if __name__ == "__main__":
    # If run directly, show current configuration status
    print("Memory Box Configuration Status:")
    print("-" * 40)
    
    # Check embedding API key
    embedding_config = config_manager.get_embedding_config()
    api_key_env = embedding_config.get("api_key_env")
    if api_key_env and config_manager.get_credential(api_key_env):
        print(f"✅ Embedding API Key ({api_key_env}): Available")
    else:
        print(f"❌ Embedding API Key ({api_key_env}): Missing")
    
    # Check connectors
    print("\nConnector Status:")
    for connector in config_manager.config.get("connectors", {}):
        enabled = config_manager.is_connector_enabled(connector)
        has_credentials = config_manager.check_connector_credentials(connector)
        
        status = "✅ Enabled & Configured" if enabled and has_credentials else \
                "⚠️ Enabled but Missing Credentials" if enabled else \
                "❌ Disabled"
        
        print(f"{connector.title()}: {status}")
    
    print("\nRun auto-configure? (y/n)")
    choice = input().lower()
    if choice == 'y':
        enabled = config_manager.auto_configure_connectors()
        print(f"\nEnabled connectors: {', '.join(enabled)}")