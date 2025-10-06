# connector_interface.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class ConnectorInterface(ABC):
    """Base interface for all data source connectors"""
    
    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the data source"""
        pass
    
    @abstractmethod
    def fetch_data(self, **kwargs) -> List[Dict[str, Any]]:
        """Fetch data from the source with optional parameters"""
        pass
    
    @abstractmethod
    def process_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and normalize the data for embedding"""
        pass
    
    def run_pipeline(self, **kwargs) -> List[Dict[str, Any]]:
        """Run the full pipeline: authenticate, fetch, and process"""
        if not self.authenticate():
            raise Exception(f"Authentication failed for {self.__class__.__name__}")
        
        raw_data = self.fetch_data(**kwargs)
        processed_data = self.process_data(raw_data)
        return processed_data