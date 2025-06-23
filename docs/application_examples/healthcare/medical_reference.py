"""
Example: Medical Reference System with Offline-First Resilience
Application Category: Healthcare Applications
"""

import os
import json
import time
from typing import Dict, List, Optional, Any
from enum import Enum

# Import MCP Zero components
from mcp_zero.reference.core import ReferenceCore
from mcp_zero.search.local_search import LocalMedicalSearch
from mcp_zero.search.enhanced_search import EnhancedMedicalSearch
from mcp_zero.sync.data_sync import DataSynchronizer


class SystemMode(Enum):
    """Operating modes for the medical reference system."""
    OFFLINE = "offline"
    ONLINE = "online"


class MedicalReferenceSystem:
    """
    Medical Reference System with offline-first resilience pattern.
    Provides medical information even in disconnected environments.
    Critical for field hospitals and remote locations.
    """
    
    def __init__(
        self,
        local_data_path: str,
        api_key: Optional[str] = None,
        api_endpoint: Optional[str] = None
    ):
        # Start in offline mode by default (offline-first principle)
        self.mode = SystemMode.OFFLINE
        self.last_sync_time = None
        
        # Initialize core reference system
        self.reference_core = ReferenceCore(local_data_path=local_data_path)
        
        # Initialize search engines - both local and enhanced
        self.local_search = LocalMedicalSearch(data_path=local_data_path)
        self.enhanced_search = EnhancedMedicalSearch(
            api_key=api_key,
            api_endpoint=api_endpoint
        )
        
        # Initialize data synchronizer
        self.sync = DataSynchronizer(
            local_path=local_data_path,
            remote_endpoint=api_endpoint,
            api_key=api_key
        )
        
        # Try to connect once if API key is provided
        if api_key:
            self._try_connect_once()
    
    def _try_connect_once(self) -> None:
        """
        Try to connect to the medical reference service exactly once.
        If successful, switch to online mode and sync data.
        If not, remain in offline mode permanently.
        """
        try:
            # Attempt connection with short timeout
            connected = self.enhanced_search.test_connection(timeout_seconds=3)
            
            if connected:
                self.mode = SystemMode.ONLINE
                print("Connected to medical reference service")
                
                # Sync data once on connection
                self._sync_data()
            else:
                print("Medical reference service unavailable, using local data only")
        except Exception as e:
            print(f"Connection error: {str(e)}. Using local data only.")
            # No retry - remain in offline mode permanently
    
    def _sync_data(self) -> None:
        """Synchronize local medical data with remote service."""
        try:
            sync_result = self.sync.synchronize()
            self.last_sync_time = time.time()
            print(f"Synchronized {sync_result['added']} new and {sync_result['updated']} updated references")
        except Exception as e:
            print(f"Data synchronization error: {str(e)}. Continuing with existing local data.")
    
    def search_condition(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        Search for medical conditions with offline resilience.
        Uses enhanced search if online, otherwise uses local search.
        """
        if self.mode == SystemMode.ONLINE:
            try:
                # Try enhanced search
                results = self.enhanced_search.search_conditions(query, max_results)
                return results
            except Exception as e:
                # Permanently fall back to offline mode on failure
                self.mode = SystemMode.OFFLINE
                print(f"Enhanced search failed: {str(e)}. Falling back to local search permanently.")
                # Continue with local search
        
        # Use local search (either as default or after fallback)
        return self.local_search.search_conditions(query, max_results)
    
    def get_treatment_protocol(self, condition_id: str) -> Dict:
        """
        Get treatment protocol with offline resilience.
        Uses latest protocols if online, otherwise uses local cached protocols.
        """
        if self.mode == SystemMode.ONLINE:
            try:
                # Try to get latest protocol
                protocol = self.enhanced_search.get_treatment_protocol(condition_id)
                return protocol
            except Exception as e:
                # Permanently fall back to offline mode on failure
                self.mode = SystemMode.OFFLINE
                print(f"Protocol retrieval failed: {str(e)}. Using local protocols permanently.")
                # Continue with local protocol
        
        # Use local protocol (either as default or after fallback)
        return self.local_search.get_treatment_protocol(condition_id)
    
    def get_drug_interactions(self, medications: List[str]) -> List[Dict]:
        """
        Check for drug interactions with offline resilience.
        Uses comprehensive database if online, otherwise uses local database.
        """
        if self.mode == SystemMode.ONLINE:
            try:
                # Try enhanced drug interaction check
                interactions = self.enhanced_search.check_drug_interactions(medications)
                return interactions
            except Exception as e:
                # Permanently fall back to offline mode on failure
                self.mode = SystemMode.OFFLINE
                print(f"Drug interaction check failed: {str(e)}. Using local database permanently.")
                # Continue with local check
        
        # Use local drug interaction database
        return self.local_search.check_drug_interactions(medications)
    
    def get_system_status(self) -> Dict:
        """Get the current system status."""
        return {
            "mode": self.mode.value,
            "last_sync_time": self.last_sync_time,
            "local_database_version": self.local_search.get_database_version(),
            "local_conditions_count": self.local_search.get_conditions_count(),
            "local_medications_count": self.local_search.get_medications_count()
        }


# Example usage
if __name__ == "__main__":
    # Create medical reference system with offline-first resilience
    med_ref = MedicalReferenceSystem(
        local_data_path="./medical_data",
        api_key=os.environ.get("MED_API_KEY"),
        api_endpoint=os.environ.get("MED_API_ENDPOINT")
    )
    
    # Search always works - comprehensive if online, basic if offline
    condition_results = med_ref.search_condition("acute respiratory infection")
    print(f"Found {len(condition_results)} conditions in {med_ref.mode.value} mode")
    
    if condition_results:
        # Get treatment protocol - works regardless of connectivity
        condition_id = condition_results[0]["id"]
        protocol = med_ref.get_treatment_protocol(condition_id)
        print(f"Treatment protocol: {protocol['name']}")
    
    # Check drug interactions - always works
    interactions = med_ref.get_drug_interactions(["aspirin", "warfarin"])
    print(f"Found {len(interactions)} potential drug interactions")
    
    # System status
    status = med_ref.get_system_status()
    print(f"System status: {status}")
