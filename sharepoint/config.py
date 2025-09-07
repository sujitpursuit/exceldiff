"""
SharePoint Configuration Module

Manages configuration settings for SharePoint integration.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class SharePointConfig:
    """Configuration settings for SharePoint integration."""
    
    def __init__(self):
        """Initialize SharePoint configuration from environment variables."""
        
        # Microsoft Graph API Credentials
        self.MICROSOFT_CLIENT_ID = os.getenv('MICROSOFT_CLIENT_ID')
        self.MICROSOFT_CLIENT_SECRET = os.getenv('MICROSOFT_CLIENT_SECRET')
        self.MICROSOFT_TENANT_ID = os.getenv('MICROSOFT_TENANT_ID')
        
        # SharePoint Settings
        self.SHAREPOINT_SITE_URL = os.getenv('SHAREPOINT_SITE_URL', 'https://pursuitsoftwarebiz-my.sharepoint.com')
        self.GRAPH_API_SCOPE = os.getenv('GRAPH_API_SCOPE', 'https://graph.microsoft.com/.default')
        
        # Local Storage Configuration
        self.LOCAL_STORAGE_PATH = os.getenv('LOCAL_STORAGE_PATH', './downloads/excel_versions')
        self.KEEP_DOWNLOADED_FILES = os.getenv('KEEP_DOWNLOADED_FILES', 'true').lower() == 'true'
        self.MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', '100'))
        
        # API Settings
        self.GRAPH_API_BASE_URL = 'https://graph.microsoft.com/v1.0'
        self.TOKEN_URL_TEMPLATE = 'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token'
        
        # Retry Configuration
        self.MAX_RETRY_ATTEMPTS = int(os.getenv('MAX_RETRY_ATTEMPTS', '3'))
        self.RETRY_DELAY_SECONDS = int(os.getenv('RETRY_DELAY_SECONDS', '5'))
        
        # Request Timeout
        self.REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))
        
    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate required configuration settings.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        if not self.MICROSOFT_CLIENT_ID:
            errors.append("MICROSOFT_CLIENT_ID is not configured")
        
        if not self.MICROSOFT_CLIENT_SECRET:
            errors.append("MICROSOFT_CLIENT_SECRET is not configured")
        
        if not self.MICROSOFT_TENANT_ID:
            errors.append("MICROSOFT_TENANT_ID is not configured")
        
        # Check if local storage path exists or can be created
        storage_path = Path(self.LOCAL_STORAGE_PATH)
        try:
            storage_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create local storage path: {e}")
        
        return len(errors) == 0, errors
    
    def get_token_url(self) -> str:
        """Get the OAuth2 token URL for the configured tenant."""
        return self.TOKEN_URL_TEMPLATE.format(tenant_id=self.MICROSOFT_TENANT_ID)
    
    def get_storage_path(self, file_name: str = None) -> Path:
        """
        Get the storage path for a specific file or the base storage path.
        
        Args:
            file_name: Optional filename to get specific storage path
            
        Returns:
            Path object for storage location
        """
        base_path = Path(self.LOCAL_STORAGE_PATH)
        
        if file_name:
            # Remove extension and clean filename
            clean_name = Path(file_name).stem.replace(' ', '_').replace('.', '_')
            return base_path / clean_name
        
        return base_path
    
    def format_filename(self, file_name: str, sequence_number: int, 
                       version_id: str, timestamp: str) -> str:
        """
        Format a filename according to the naming convention.
        
        Args:
            file_name: Original file name from database
            sequence_number: Version sequence number
            version_id: SharePoint version ID
            timestamp: Timestamp in YYYYMMDD_HHMMSS format
            
        Returns:
            Formatted filename
        """
        # Extract base name and clean it
        base_name = Path(file_name).stem.replace(' ', '_')
        
        # Clean version ID (replace dots with underscores)
        clean_version = version_id.replace('.', '_')
        
        # Build filename
        filename = f"{base_name}_seq{sequence_number}_v{clean_version}_{timestamp}.xlsx"
        
        return filename
    
    def __str__(self) -> str:
        """String representation of configuration."""
        return (
            f"SharePointConfig(\n"
            f"  Tenant ID: {self.MICROSOFT_TENANT_ID}\n"
            f"  Client ID: {self.MICROSOFT_CLIENT_ID[:10]}...\n"
            f"  Storage Path: {self.LOCAL_STORAGE_PATH}\n"
            f"  Keep Files: {self.KEEP_DOWNLOADED_FILES}\n"
            f"  Max File Size: {self.MAX_FILE_SIZE_MB}MB\n"
            f")"
        )


# Create a singleton instance
sharepoint_config = SharePointConfig()