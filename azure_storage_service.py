"""
Azure Storage Service

This module provides a clean abstraction layer for Azure Blob Storage operations
used by the Excel comparison API. It handles file downloads, uploads, and path
management for Excel files stored in Azure containers.

Features:
- Download blobs to temporary files for comparison
- Upload files to Azure storage
- List and manage blobs in containers
- Handle authentication and connection management
- Automatic cleanup of temporary files
- Support for both blob names and full URLs

Usage:
    storage_service = AzureStorageService()
    
    # Download file for comparison
    local_path = await storage_service.download_blob_to_temp("my-file.xlsx")
    
    # Upload a new file
    blob_name = await storage_service.upload_file("local-file.xlsx", "folder/new-name.xlsx")
"""

import os
import tempfile
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
import asyncio
from contextlib import asynccontextmanager

from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient, ContentSettings, BlobSasPermissions, generate_blob_sas
from azure.storage.blob.aio import BlobServiceClient as AsyncBlobServiceClient
from azure.core.exceptions import AzureError, ResourceNotFoundError
from dotenv import load_dotenv

from logger import get_logger
from exceptions import ExcelComparisonError

# Load environment variables
load_dotenv()


class AzureStorageError(ExcelComparisonError):
    """Custom exception for Azure storage operations."""
    pass


class AzureStorageService:
    """
    Service class for Azure Blob Storage operations.
    
    This class provides a clean interface for working with Excel files stored
    in Azure Blob Storage, including downloading for comparison, uploading new
    files, and managing blob metadata.
    """
    
    def __init__(self, connection_string: Optional[str] = None, container_name: Optional[str] = None):
        """
        Initialize Azure Storage Service.
        
        Args:
            connection_string: Azure storage connection string. If None, reads from environment.
            container_name: Container name for Excel files. If None, reads from environment.
        """
        self.logger = get_logger("azure_storage")
        
        # Get configuration from environment or parameters
        self.connection_string = connection_string or os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.container_name = container_name or os.getenv("AZURE_STORAGE_CONTAINER_NAME", "excel-files")
        
        # Reports configuration
        self.reports_container_name = os.getenv("AZURE_REPORTS_CONTAINER_NAME", "diff-reports")
        self.upload_reports_enabled = os.getenv("UPLOAD_REPORTS_TO_AZURE", "false").lower() == "true"
        
        if not self.connection_string:
            raise AzureStorageError(
                "Azure Storage connection string not configured. "
                "Please set AZURE_STORAGE_CONNECTION_STRING environment variable."
            )
        
        # Initialize clients
        try:
            self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
            self.container_client = self.blob_service_client.get_container_client(self.container_name)
            
            # Initialize reports container client
            self.reports_container_client = self.blob_service_client.get_container_client(self.reports_container_name)
            
            # Verify main container connection
            if not self.container_client.exists():
                raise AzureStorageError(f"Container '{self.container_name}' does not exist")
            
            # Verify reports container exists (if upload is enabled)
            if self.upload_reports_enabled and not self.reports_container_client.exists():
                self.logger.warning(f"Reports container '{self.reports_container_name}' does not exist. Reports upload will be disabled.")
                self.upload_reports_enabled = False
                
        except AzureError as e:
            raise AzureStorageError(f"Failed to connect to Azure Storage: {str(e)}")
        
        self.logger.info(f"Azure Storage Service initialized for container: {self.container_name}")
        self.logger.info(f"Reports upload {'enabled' if self.upload_reports_enabled else 'disabled'} for container: {self.reports_container_name}")
    
    def extract_blob_name_from_path(self, file_path: str) -> str:
        """
        Extract blob name from various path formats.
        
        Handles:
        - Full blob URLs: https://account.blob.core.windows.net/container/blob-name
        - Container paths: container-name/blob-name  
        - Simple blob names: blob-name
        
        Args:
            file_path: Path in various formats
            
        Returns:
            Clean blob name for the container
        """
        if not file_path:
            raise AzureStorageError("File path cannot be empty")
        
        # Handle full blob URLs
        if file_path.startswith("https://"):
            # Extract blob name from URL
            # Format: https://account.blob.core.windows.net/container/blob-name
            parts = file_path.split("/")
            if len(parts) >= 5:
                # Skip protocol, domain, container - take the rest as blob name
                blob_name = "/".join(parts[4:])
                self.logger.debug(f"Extracted blob name from URL: {blob_name}")
                return blob_name
            else:
                raise AzureStorageError(f"Invalid blob URL format: {file_path}")
        
        # Handle container/blob format
        if "/" in file_path:
            # Check if first part is container name
            parts = file_path.split("/", 1)
            if parts[0] == self.container_name:
                blob_name = parts[1]
                self.logger.debug(f"Extracted blob name from container path: {blob_name}")
                return blob_name
            else:
                # Assume it's a blob path with folders
                self.logger.debug(f"Using full path as blob name: {file_path}")
                return file_path
        
        # Simple blob name
        self.logger.debug(f"Using simple blob name: {file_path}")
        return file_path
    
    def download_blob_to_temp(self, file_path: str) -> str:
        """
        Download a blob to a temporary file for processing.
        
        Args:
            file_path: Blob name, container path, or full URL
            
        Returns:
            Path to downloaded temporary file
            
        Raises:
            AzureStorageError: If download fails
        """
        try:
            blob_name = self.extract_blob_name_from_path(file_path)
            
            self.logger.info(f"Downloading blob to temp file: {blob_name}")
            
            # Get blob client
            blob_client = self.container_client.get_blob_client(blob_name)
            
            # Check if blob exists
            if not blob_client.exists():
                raise AzureStorageError(f"Blob not found: {blob_name}")
            
            # Get blob properties for validation
            properties = blob_client.get_blob_properties()
            file_size = properties.size
            
            self.logger.info(f"Blob size: {file_size} bytes")
            
            # Create temporary file with appropriate extension
            file_extension = Path(blob_name).suffix or ".xlsx"
            temp_fd, temp_path = tempfile.mkstemp(suffix=file_extension, prefix="azure_excel_")
            
            try:
                # Download blob data
                with os.fdopen(temp_fd, 'wb') as temp_file:
                    download_stream = blob_client.download_blob()
                    download_stream.readinto(temp_file)
                
                # Verify download
                if not Path(temp_path).exists() or Path(temp_path).stat().st_size == 0:
                    raise AzureStorageError(f"Failed to download blob: {blob_name}")
                
                downloaded_size = Path(temp_path).stat().st_size
                self.logger.info(f"Successfully downloaded {blob_name} to {temp_path} ({downloaded_size} bytes)")
                
                return temp_path
                
            except Exception as e:
                # Clean up temp file on error
                try:
                    if Path(temp_path).exists():
                        Path(temp_path).unlink()
                except:
                    pass
                raise
            
        except AzureError as e:
            self.logger.error(f"Azure error downloading blob {file_path}: {e}")
            raise AzureStorageError(f"Failed to download file from Azure: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error downloading blob {file_path}: {e}")
            raise AzureStorageError(f"Unexpected error downloading file: {str(e)}")
    
    def upload_file(self, local_file_path: str, blob_name: str, overwrite: bool = False) -> str:
        """
        Upload a local file to Azure blob storage.
        
        Args:
            local_file_path: Path to local file to upload
            blob_name: Name for the blob in Azure storage
            overwrite: Whether to overwrite existing blob
            
        Returns:
            Full blob URL
            
        Raises:
            AzureStorageError: If upload fails
        """
        try:
            if not Path(local_file_path).exists():
                raise AzureStorageError(f"Local file not found: {local_file_path}")
            
            self.logger.info(f"Uploading {local_file_path} to blob: {blob_name}")
            
            # Get blob client
            blob_client = self.container_client.get_blob_client(blob_name)
            
            # Upload file
            with open(local_file_path, 'rb') as file_data:
                blob_client.upload_blob(
                    file_data, 
                    overwrite=overwrite,
                    content_settings={
                        'content_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    }
                )
            
            blob_url = blob_client.url
            self.logger.info(f"Successfully uploaded to: {blob_url}")
            
            return blob_url
            
        except AzureError as e:
            self.logger.error(f"Azure error uploading file {local_file_path}: {e}")
            raise AzureStorageError(f"Failed to upload file to Azure: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error uploading file {local_file_path}: {e}")
            raise AzureStorageError(f"Unexpected error uploading file: {str(e)}")
    
    def list_blobs(self, prefix: Optional[str] = None) -> List[Dict]:
        """
        List blobs in the container.
        
        Args:
            prefix: Filter blobs by prefix
            
        Returns:
            List of blob information dictionaries
        """
        try:
            blobs = []
            
            for blob in self.container_client.list_blobs(name_starts_with=prefix):
                blob_info = {
                    'name': blob.name,
                    'size': blob.size,
                    'last_modified': blob.last_modified,
                    'content_type': blob.content_settings.content_type if blob.content_settings else None,
                    'url': f"https://{self.blob_service_client.account_name}.blob.core.windows.net/{self.container_name}/{blob.name}"
                }
                blobs.append(blob_info)
            
            self.logger.info(f"Listed {len(blobs)} blobs with prefix: {prefix}")
            return blobs
            
        except AzureError as e:
            self.logger.error(f"Azure error listing blobs: {e}")
            raise AzureStorageError(f"Failed to list blobs: {str(e)}")
    
    def blob_exists(self, file_path: str) -> bool:
        """
        Check if a blob exists in the container.
        
        Args:
            file_path: Blob name, container path, or full URL
            
        Returns:
            True if blob exists, False otherwise
        """
        try:
            blob_name = self.extract_blob_name_from_path(file_path)
            blob_client = self.container_client.get_blob_client(blob_name)
            return blob_client.exists()
            
        except Exception as e:
            self.logger.warning(f"Error checking blob existence {file_path}: {e}")
            return False
    
    def get_blob_properties(self, file_path: str) -> Dict:
        """
        Get properties of a blob.
        
        Args:
            file_path: Blob name, container path, or full URL
            
        Returns:
            Dictionary with blob properties
        """
        try:
            blob_name = self.extract_blob_name_from_path(file_path)
            blob_client = self.container_client.get_blob_client(blob_name)
            
            properties = blob_client.get_blob_properties()
            
            return {
                'name': blob_name,
                'size': properties.size,
                'last_modified': properties.last_modified,
                'content_type': properties.content_settings.content_type if properties.content_settings else None,
                'etag': properties.etag,
                'url': blob_client.url
            }
            
        except AzureError as e:
            self.logger.error(f"Azure error getting blob properties {file_path}: {e}")
            raise AzureStorageError(f"Failed to get blob properties: {str(e)}")
    
    def delete_blob(self, file_path: str) -> bool:
        """
        Delete a blob from the container.
        
        Args:
            file_path: Blob name, container path, or full URL
            
        Returns:
            True if deleted successfully, False if blob didn't exist
        """
        try:
            blob_name = self.extract_blob_name_from_path(file_path)
            blob_client = self.container_client.get_blob_client(blob_name)
            
            blob_client.delete_blob()
            self.logger.info(f"Deleted blob: {blob_name}")
            return True
            
        except ResourceNotFoundError:
            self.logger.info(f"Blob not found for deletion: {file_path}")
            return False
        except AzureError as e:
            self.logger.error(f"Azure error deleting blob {file_path}: {e}")
            raise AzureStorageError(f"Failed to delete blob: {str(e)}")
    
    def extract_base_filename(self, filename: str) -> str:
        """
        Extract base name from Excel filename for folder structure.
        
        Examples:
        'STTM Working Version File_seq1_v1.0_20250904_210303.xlsx' 
        → 'STTM Working Version File'
        
        'MyFile_seq3_v2.1_20250901_120000.xlsx' 
        → 'MyFile'
        
        Args:
            filename: Full filename or path
            
        Returns:
            Base name for folder structure
        """
        try:
            # Get just the filename without path or extension
            name = Path(filename).stem
            
            # Split by '_seq' and take first part (most common pattern)
            if '_seq' in name:
                base_name = name.split('_seq')[0]
                self.logger.debug(f"Extracted base name using '_seq' pattern: {base_name}")
                return base_name
            
            # Fallback: take everything before first underscore with version info
            if '_v' in name:
                base_name = name.split('_v')[0]
                self.logger.debug(f"Extracted base name using '_v' pattern: {base_name}")
                return base_name
                
            # Another fallback: take first 3 words if separated by spaces or underscores
            parts = name.replace('_', ' ').split()
            if len(parts) >= 3:
                base_name = ' '.join(parts[:3])
                self.logger.debug(f"Extracted base name using first 3 words: {base_name}")
                return base_name
            
            # Final fallback: use full stem
            self.logger.debug(f"Using full filename as base: {name}")
            return name
            
        except Exception as e:
            self.logger.warning(f"Error extracting base filename from {filename}: {e}")
            return "Unknown"
    
    def upload_report_to_azure(self, local_file_path: str, base_filename: str, report_filename: str) -> Optional[str]:
        """
        Upload a report file to Azure blob storage with dynamic folder structure.
        
        Args:
            local_file_path: Path to local report file
            base_filename: Base name extracted from Excel files (e.g., 'STTM Working Version File')
            report_filename: Report filename (e.g., 'comparison_v1_vs_v7_20250907.html')
        
        Returns:
            Azure blob URL if successful, None if failed
            
        Raises:
            AzureStorageError: If upload is disabled or fails
        """
        if not self.upload_reports_enabled:
            self.logger.error("Reports upload is disabled but required for API compatibility")
            raise AzureStorageError(
                "Azure reports upload is disabled. Please set UPLOAD_REPORTS_TO_AZURE=true in environment."
            )
            
        try:
            if not Path(local_file_path).exists():
                self.logger.error(f"Local report file not found: {local_file_path}")
                raise AzureStorageError(f"Local report file not found: {local_file_path}")
            
            # Create blob name with folder structure: {base_filename}/{report_filename}
            blob_name = f"{base_filename}/{report_filename}"
            
            self.logger.info(f"Uploading report to Azure: {blob_name}")
            
            # Get blob client for reports container
            blob_client = self.reports_container_client.get_blob_client(blob_name)
            
            # Determine content type based on file extension
            file_ext = Path(local_file_path).suffix.lower()
            content_type = {
                '.html': 'text/html',
                '.json': 'application/json',
                '.txt': 'text/plain'
            }.get(file_ext, 'application/octet-stream')
            
            # Upload file
            with open(local_file_path, 'rb') as file_data:
                blob_client.upload_blob(
                    file_data,
                    overwrite=True,
                    content_settings=ContentSettings(content_type=content_type)
                )
            
            # Generate SAS URL for the blob (valid for 7 days)
            sas_url = self.generate_blob_sas_url(
                container_name=self.reports_container_name,
                blob_name=blob_name,
                expiry_days=7
            )
            
            self.logger.info(f"Successfully uploaded report with SAS URL: {blob_name}")
            
            return sas_url
            
        except AzureError as e:
            self.logger.error(f"Azure error uploading report {local_file_path}: {e}")
            raise AzureStorageError(f"Failed to upload report to Azure: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error uploading report {local_file_path}: {e}")
            raise AzureStorageError(f"Unexpected error uploading report: {str(e)}")
    

    def generate_blob_sas_url(self, container_name: str, blob_name: str, expiry_days: int = 7) -> str:
        """
        Generate a SAS URL for a blob with read permissions.
        
        Args:
            container_name: Name of the container
            blob_name: Name of the blob
            expiry_days: Number of days until the SAS token expires (default: 7)
            
        Returns:
            Full blob URL with SAS token
        """
        try:
            # Get account name and key from connection string
            # Parse connection string to extract account name and key
            conn_str_parts = {}
            for part in self.connection_string.split(';'):
                if '=' in part:
                    key, value = part.split('=', 1)
                    conn_str_parts[key] = value
            
            account_name = conn_str_parts.get('AccountName')
            account_key = conn_str_parts.get('AccountKey')
            
            if not account_name or not account_key:
                raise AzureStorageError("Could not extract account credentials from connection string")
            
            # Generate SAS token
            sas_token = generate_blob_sas(
                account_name=account_name,
                container_name=container_name,
                blob_name=blob_name,
                account_key=account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(days=expiry_days)
            )
            
            # Construct the full URL with SAS token
            blob_url = f"https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}?{sas_token}"
            
            return blob_url
            
        except Exception as e:
            self.logger.error(f"Error generating SAS URL for {blob_name}: {e}")
            raise AzureStorageError(f"Failed to generate SAS URL: {str(e)}")
    
    @staticmethod
    def cleanup_temp_file(temp_path: str):
        """
        Clean up a temporary file.
        
        Args:
            temp_path: Path to temporary file to delete
        """
        try:
            if temp_path and Path(temp_path).exists():
                Path(temp_path).unlink()
                logger = get_logger("azure_storage")
                logger.info(f"Cleaned up temporary file: {temp_path}")
        except Exception as e:
            logger = get_logger("azure_storage")
            logger.warning(f"Failed to cleanup temp file {temp_path}: {e}")
    
    @asynccontextmanager
    async def download_for_comparison(self, file1_path: str, file2_path: str):
        """
        Context manager to download two blobs for comparison and automatically clean up.
        
        Args:
            file1_path: First blob path
            file2_path: Second blob path
            
        Yields:
            Tuple of (temp_file1_path, temp_file2_path)
        """
        temp_file1 = None
        temp_file2 = None
        
        try:
            self.logger.info(f"Downloading files for comparison: {file1_path} vs {file2_path}")
            
            # Download both files
            temp_file1 = self.download_blob_to_temp(file1_path)
            temp_file2 = self.download_blob_to_temp(file2_path)
            
            yield temp_file1, temp_file2
            
        finally:
            # Clean up temporary files
            if temp_file1:
                self.cleanup_temp_file(temp_file1)
            if temp_file2:
                self.cleanup_temp_file(temp_file2)


# Global instance for easy access
_azure_storage_service: Optional[AzureStorageService] = None


def get_azure_storage_service() -> AzureStorageService:
    """
    Get the global Azure Storage Service instance.
    
    Returns:
        AzureStorageService instance
    """
    global _azure_storage_service
    
    if _azure_storage_service is None:
        _azure_storage_service = AzureStorageService()
    
    return _azure_storage_service


def is_azure_path(file_path: str) -> bool:
    """
    Check if a file path is an Azure blob path.
    
    Args:
        file_path: File path to check
        
    Returns:
        True if path appears to be an Azure blob path
    """
    if not file_path:
        return False
    
    # Check for Azure blob URL pattern
    if file_path.startswith("https://") and ".blob.core.windows.net" in file_path:
        return True
    
    # Check for container/blob pattern (less reliable, but we'll assume Azure if it contains forward slashes)
    # This is a heuristic - in practice you might want to be more specific
    return "/" in file_path and not file_path.startswith("/") and not ":" in file_path