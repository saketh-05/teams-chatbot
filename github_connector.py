# github_connector.py
from connector_interface import ConnectorInterface
from typing import List, Dict, Any
import requests
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GitHubConnector")

class GitHubConnector(ConnectorInterface):
    """Connector for GitHub repositories"""
    
    def __init__(self, token=None, token_env="GITHUB_ACCESS_TOKEN"):
        """Initialize GitHub connector with token or from environment"""
        self.token = token or os.environ.get(token_env)
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
    
    def authenticate(self) -> bool:
        """Verify authentication with GitHub API"""
        if not self.token:
            logger.error("GitHub token not provided")
            return False
            
        try:
            response = requests.get(f"{self.base_url}/user", headers=self.headers)
            if response.status_code == 200:
                user_data = response.json()
                logger.info(f"Authenticated as GitHub user: {user_data.get('login')}")
                return True
            else:
                logger.error(f"GitHub authentication failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"GitHub authentication error: {str(e)}")
            return False
    
    def fetch_data(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch data from GitHub repositories
        
        Parameters:
        - repos (List[str]): List of repositories in format "owner/repo"
        - include_issues (bool): Include issues in the data
        - include_prs (bool): Include pull requests in the data
        - include_readme (bool): Include README files
        - max_items (int): Maximum number of items to fetch per type
        """
        repos = kwargs.get("repos", [])
        include_issues = kwargs.get("include_issues", True)
        include_prs = kwargs.get("include_prs", True)
        include_readme = kwargs.get("include_readme", True)
        max_items = kwargs.get("max_items", 100)
        
        if not repos:
            logger.warning("No repositories specified")
            return []
        
        all_data = []
        
        for repo in repos:
            try:
                # Get repository info
                repo_response = requests.get(f"{self.base_url}/repos/{repo}", headers=self.headers)
                if repo_response.status_code != 200:
                    logger.warning(f"Failed to fetch repo {repo}: {repo_response.status_code}")
                    continue
                
                repo_data = repo_response.json()
                all_data.append({
                    "type": "repository",
                    "id": repo_data["id"],
                    "name": repo_data["full_name"],
                    "description": repo_data.get("description", ""),
                    "url": repo_data["html_url"],
                    "created_at": repo_data["created_at"],
                    "updated_at": repo_data["updated_at"],
                    "content": f"Repository: {repo_data['full_name']}\nDescription: {repo_data.get('description', '')}"
                })
                
                # Get README if requested
                if include_readme:
                    try:
                        readme_response = requests.get(f"{self.base_url}/repos/{repo}/readme", headers=self.headers)
                        if readme_response.status_code == 200:
                            readme_data = readme_response.json()
                            # Get content (it's base64 encoded)
                            import base64
                            content = base64.b64decode(readme_data["content"]).decode("utf-8")
                            all_data.append({
                                "type": "readme",
                                "id": f"{repo}-readme",
                                "name": f"README - {repo}",
                                "url": readme_data["html_url"],
                                "created_at": readme_data["created_at"],
                                "updated_at": readme_data["updated_at"],
                                "content": content
                            })
                    except Exception as e:
                        logger.warning(f"Error fetching README for {repo}: {str(e)}")
                
                # Get issues if requested
                if include_issues:
                    try:
                        issues_response = requests.get(
                            f"{self.base_url}/repos/{repo}/issues",
                            params={"state": "all", "per_page": max_items},
                            headers=self.headers
                        )
                        if issues_response.status_code == 200:
                            issues = issues_response.json()
                            for issue in issues:
                                # Skip pull requests (they're also returned by the issues endpoint)
                                if "pull_request" in issue and not include_prs:
                                    continue
                                    
                                issue_type = "pull_request" if "pull_request" in issue else "issue"
                                all_data.append({
                                    "type": issue_type,
                                    "id": issue["id"],
                                    "name": f"#{issue['number']} - {issue['title']}",
                                    "url": issue["html_url"],
                                    "created_at": issue["created_at"],
                                    "updated_at": issue["updated_at"],
                                    "content": f"Title: {issue['title']}\nState: {issue['state']}\nBody: {issue.get('body', '')}"
                                })
                    except Exception as e:
                        logger.warning(f"Error fetching issues for {repo}: {str(e)}")
                
            except Exception as e:
                logger.error(f"Error processing repository {repo}: {str(e)}")
        
        return all_data
    
    def process_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and normalize GitHub data for embedding"""
        processed_data = []
        
        for item in data:
            # Convert dates to consistent format
            created_at = self._parse_date(item.get("created_at", ""))
            updated_at = self._parse_date(item.get("updated_at", ""))
            
            # Create standardized document
            document = {
                "id": str(item.get("id", "")),
                "source": "github",
                "source_type": item.get("type", "unknown"),
                "title": item.get("name", ""),
                "url": item.get("url", ""),
                "content": item.get("content", ""),
                "created_at": created_at,
                "updated_at": updated_at,
                "metadata": {
                    "type": item.get("type", ""),
                    "repository": item.get("name", "").split("/")[0] if "/" in item.get("name", "") else ""
                }
            }
            
            processed_data.append(document)
        
        return processed_data
    
    def _parse_date(self, date_str):
        """Parse GitHub API date string to standard format"""
        if not date_str:
            return ""
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return date_str