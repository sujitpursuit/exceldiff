"""
SharePoint Service Module

Handles Microsoft Graph API operations for SharePoint integration.
"""

import requests
import base64
import time
import logging
from typing import Dict, Any, Optional, List
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .config import sharepoint_config

logger = logging.getLogger(__name__)


class SharePointService:
    """Service for interacting with SharePoint via Microsoft Graph API."""
    
    def __init__(self, config: Optional[Any] = None):
        """
        Initialize SharePoint service.
        
        Args:
            config: Optional configuration object (defaults to sharepoint_config)
        """
        self.config = config or sharepoint_config
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[float] = None
        
        # Validate configuration
        is_valid, errors = self.config.validate()
        if not is_valid:
            logger.warning(f"SharePoint configuration validation warnings: {errors}")
    
    def _get_access_token(self) -> str:
        """
        Get access token using client credentials flow.
        
        Returns:
            Access token string
            
        Raises:
            Exception: If token acquisition fails
        """
        # Check if token is still valid
        if self.access_token and self.token_expires_at and time.time() < self.token_expires_at:
            return self.access_token
        
        try:
            token_url = self.config.get_token_url()
            
            data = {
                'grant_type': 'client_credentials',
                'client_id': self.config.MICROSOFT_CLIENT_ID,
                'client_secret': self.config.MICROSOFT_CLIENT_SECRET,
                'scope': self.config.GRAPH_API_SCOPE
            }
            
            response = requests.post(token_url, data=data, timeout=self.config.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            expires_in = token_data.get('expires_in', 3600)
            # Set expiry time with 60-second buffer
            self.token_expires_at = time.time() + expires_in - 60
            
            logger.info("Successfully acquired SharePoint access token")
            return self.access_token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get access token: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting access token: {str(e)}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((requests.exceptions.RequestException, requests.exceptions.Timeout))
    )
    def _make_graph_request(self, url: str, method: str = "GET", 
                           params: Dict = None, headers: Dict = None) -> Dict[str, Any]:
        """
        Make a Microsoft Graph API request with retry logic.
        
        Args:
            url: API endpoint URL
            method: HTTP method
            params: Query parameters
            headers: Additional headers
            
        Returns:
            JSON response data
            
        Raises:
            requests.exceptions.RequestException: On API errors
        """
        if not headers:
            headers = {}
        
        headers.update({
            "Authorization": f"Bearer {self._get_access_token()}",
            "Content-Type": "application/json"
        })
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                timeout=self.config.REQUEST_TIMEOUT
            )
            
            # Handle 401 - token might be expired
            if response.status_code == 401:
                logger.info("Token expired, refreshing...")
                self.access_token = None
                headers["Authorization"] = f"Bearer {self._get_access_token()}"
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    timeout=self.config.REQUEST_TIMEOUT
                )
            
            response.raise_for_status()
            return response.json() if response.text else {}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Graph API request failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise
    
    def parse_sharepoint_url(self, sharepoint_url: str) -> Dict[str, str]:
        """
        Parse SharePoint URL to extract drive_id and item_id using Graph API.
        
        Args:
            sharepoint_url: SharePoint sharing URL
            
        Returns:
            Dictionary with drive_id, item_id, and file_name
        """
        try:
            # Encode sharing URL for Graph API shares endpoint
            sharing_url_bytes = sharepoint_url.encode('utf-8')
            sharing_url_b64 = base64.urlsafe_b64encode(sharing_url_bytes).decode('utf-8')
            # Remove padding as required by Graph API
            sharing_url_b64 = sharing_url_b64.rstrip('=')
            
            api_url = f"{self.config.GRAPH_API_BASE_URL}/shares/u!{sharing_url_b64}/driveItem"
            
            response = self._make_graph_request(api_url)
            
            return {
                "drive_id": response['parentReference']['driveId'],
                "item_id": response['id'],
                "file_name": response.get('name', 'unknown_file.xlsx')
            }
            
        except Exception as e:
            logger.warning(f"Could not parse SharePoint URL: {str(e)}")
            # Return placeholder values for backward compatibility
            return {
                "drive_id": "placeholder_drive_id",
                "item_id": "placeholder_item_id", 
                "file_name": sharepoint_url.split('/')[-1] if '/' in sharepoint_url else "unknown_file.xlsx"
            }
    
    def get_file_metadata(self, drive_id: str, item_id: str) -> Dict[str, Any]:
        """
        Get basic file metadata from SharePoint.
        
        Args:
            drive_id: Drive identifier
            item_id: Item identifier
            
        Returns:
            File metadata dictionary
        """
        url = f"{self.config.GRAPH_API_BASE_URL}/drives/{drive_id}/items/{item_id}"
        
        try:
            response = self._make_graph_request(url)
            return {
                "id": response.get("id"),
                "name": response.get("name"),
                "size": response.get("size"),
                "lastModifiedDateTime": response.get("lastModifiedDateTime"),
                "webUrl": response.get("webUrl"),
                "driveId": response.get("parentReference", {}).get("driveId", drive_id)
            }
        except Exception as e:
            logger.error(f"Error getting file metadata: {str(e)}")
            raise
    
    def get_file_versions(self, drive_id: str, item_id: str) -> List[Dict[str, Any]]:
        """
        Get all versions of a file from SharePoint.
        
        Args:
            drive_id: Drive identifier
            item_id: Item identifier
            
        Returns:
            List of version dictionaries
        """
        try:
            versions_url = f"{self.config.GRAPH_API_BASE_URL}/drives/{drive_id}/items/{item_id}/versions"
            
            response = self._make_graph_request(versions_url)
            versions = response.get('value', [])
            
            # Get detailed metadata for each version
            detailed_versions = []
            for version in versions:
                version_id = version['id']
                version_detail_url = f"{self.config.GRAPH_API_BASE_URL}/drives/{drive_id}/items/{item_id}/versions/{version_id}"
                
                try:
                    detailed_version = self._make_graph_request(version_detail_url)
                    detailed_versions.append(detailed_version)
                except Exception as e:
                    logger.warning(f"Could not get details for version {version_id}: {e}")
                    detailed_versions.append(version)  # Fallback to basic data
            
            logger.info(f"Found {len(detailed_versions)} versions for item {item_id[:10]}...")
            return detailed_versions
            
        except Exception as e:
            logger.error(f"Error getting file versions: {str(e)}")
            raise
    
    def get_version_download_url(self, drive_id: str, item_id: str, version_id: str) -> Optional[str]:
        """
        Get download URL for a specific file version.
        
        Args:
            drive_id: Drive identifier
            item_id: Item identifier
            version_id: Version identifier
            
        Returns:
            Download URL or None if not available
        """
        try:
            version_url = f"{self.config.GRAPH_API_BASE_URL}/drives/{drive_id}/items/{item_id}/versions/{version_id}"
            
            response = self._make_graph_request(version_url)
            download_url = response.get('@microsoft.graph.downloadUrl')
            
            if not download_url:
                logger.warning(f"No download URL found for version {version_id}")
                return None
            
            return download_url
            
        except Exception as e:
            logger.error(f"Error getting download URL for version {version_id}: {str(e)}")
            raise
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test SharePoint connection using Application permissions.
        
        Returns:
            Connection status dictionary
        """
        try:
            # Try to get access token first
            token = self._get_access_token()
            
            # Test with sites endpoint (works with Sites.Read.All permission)
            url = f"{self.config.GRAPH_API_BASE_URL}/sites/root"
            response = self._make_graph_request(url)
            
            return {
                "connected": True,
                "site_name": response.get("displayName", "SharePoint Site"),
                "site_id": response.get("id"),
                "tenant_id": self.config.MICROSOFT_TENANT_ID,
                "auth_method": "client_credentials",
                "permissions": "Application permissions (Sites.Read.All, Files.Read.All)"
            }
            
        except Exception as e:
            logger.error(f"SharePoint connection test failed: {str(e)}")
            
            # Check if we can at least get a token
            try:
                token = self._get_access_token()
                return {
                    "connected": True,
                    "message": "Token acquired successfully, but limited site access",
                    "tenant_id": self.config.MICROSOFT_TENANT_ID,
                    "auth_method": "client_credentials",
                    "note": "Check Graph API permissions in Azure AD"
                }
            except Exception as token_error:
                return {
                    "connected": False,
                    "error": str(e),
                    "token_error": str(token_error),
                    "tenant_id": self.config.MICROSOFT_TENANT_ID,
                    "message": "Failed to authenticate with SharePoint"
                }