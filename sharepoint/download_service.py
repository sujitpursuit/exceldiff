"""
Download Service Module

Handles downloading file versions from SharePoint to local storage.
"""

import os
import requests
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

from .config import sharepoint_config
from .sharepoint_service import SharePointService

logger = logging.getLogger(__name__)


class DownloadService:
    """Service for downloading SharePoint file versions to local storage."""
    
    def __init__(self, sharepoint_service: Optional[SharePointService] = None, 
                 config: Optional[Any] = None):
        """
        Initialize download service.
        
        Args:
            sharepoint_service: SharePoint service instance
            config: Configuration object
        """
        self.config = config or sharepoint_config
        self.sharepoint_service = sharepoint_service or SharePointService(self.config)
        self.setup_storage_directory()
    
    def setup_storage_directory(self):
        """Create local storage directory structure if it doesn't exist."""
        storage_path = Path(self.config.LOCAL_STORAGE_PATH)
        storage_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Storage directory ready: {storage_path.absolute()}")
    
    def get_local_path(self, file_name: str, sequence_number: int, 
                      version_id: str) -> Tuple[Path, str]:
        """
        Generate local file path for a version.
        
        Args:
            file_name: Original file name from database
            sequence_number: Version sequence number
            version_id: SharePoint version ID
            
        Returns:
            Tuple of (full_path, relative_path_for_db)
        """
        # Get file-specific storage directory
        file_storage_dir = self.config.get_storage_path(file_name)
        file_storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Format filename
        filename = self.config.format_filename(
            file_name=file_name,
            sequence_number=sequence_number,
            version_id=version_id,
            timestamp=timestamp
        )
        
        # Full path
        full_path = file_storage_dir / filename
        
        # Relative path for database (from project root)
        relative_path = str(Path(self.config.LOCAL_STORAGE_PATH) / file_storage_dir.name / filename)
        
        return full_path, relative_path
    
    def check_local_file(self, file_path: str) -> bool:
        """
        Check if a file exists locally.
        
        Args:
            file_path: Path to check (can be relative or absolute)
            
        Returns:
            True if file exists and is readable
        """
        try:
            path = Path(file_path)
            if not path.is_absolute():
                # Try to resolve relative path
                path = Path.cwd() / path
            
            return path.exists() and path.is_file() and os.access(path, os.R_OK)
        except Exception as e:
            logger.debug(f"Error checking file {file_path}: {e}")
            return False
    
    def download_version(self, drive_id: str, item_id: str, version_id: str,
                        file_name: str, sequence_number: int,
                        force_download: bool = False) -> Dict[str, Any]:
        """
        Download a specific version from SharePoint.
        
        Args:
            drive_id: SharePoint drive ID
            item_id: SharePoint item ID
            version_id: SharePoint version ID
            file_name: Original file name
            sequence_number: Version sequence number
            force_download: Force re-download even if file exists
            
        Returns:
            Dictionary with download status and file information
        """
        try:
            # Generate local path
            full_path, relative_path = self.get_local_path(
                file_name=file_name,
                sequence_number=sequence_number,
                version_id=version_id
            )
            
            # Check if file already exists
            if not force_download and full_path.exists():
                file_size = full_path.stat().st_size
                logger.info(f"File already exists locally: {full_path}")
                return {
                    "status": "success",
                    "local_path": relative_path,
                    "full_path": str(full_path),
                    "file_size": file_size,
                    "from_cache": True,
                    "message": "File loaded from local cache"
                }
            
            # Get download URL from SharePoint
            logger.info(f"Getting download URL for version {version_id}")
            download_url = self.sharepoint_service.get_version_download_url(
                drive_id=drive_id,
                item_id=item_id,
                version_id=version_id
            )
            
            if not download_url:
                raise ValueError(f"No download URL available for version {version_id}")
            
            # Download the file
            logger.info(f"Downloading version {sequence_number} to: {full_path}")
            
            headers = {
                'Authorization': f'Bearer {self.sharepoint_service._get_access_token()}',
                'User-Agent': 'ExcelDiff-SharePoint-Download/1.0'
            }
            
            response = requests.get(
                download_url, 
                headers=headers, 
                stream=True,
                timeout=60  # 60 seconds timeout for download
            )
            response.raise_for_status()
            
            # Check file size
            content_length = response.headers.get('content-length')
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                if size_mb > self.config.MAX_FILE_SIZE_MB:
                    raise ValueError(
                        f"File size ({size_mb:.1f}MB) exceeds limit "
                        f"({self.config.MAX_FILE_SIZE_MB}MB)"
                    )
                logger.info(f"Downloading file: {size_mb:.1f}MB")
            
            # Save file
            bytes_downloaded = 0
            with open(full_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        bytes_downloaded += len(chunk)
            
            # Verify download
            if not full_path.exists():
                raise IOError(f"Failed to save file to {full_path}")
            
            actual_size = full_path.stat().st_size
            logger.info(f"Successfully downloaded {actual_size} bytes to {full_path}")
            
            return {
                "status": "success",
                "local_path": relative_path,
                "full_path": str(full_path),
                "file_size": actual_size,
                "from_cache": False,
                "downloaded_at": datetime.now().isoformat(),
                "message": f"Downloaded {actual_size} bytes from SharePoint"
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error downloading version {version_id}: {e}")
            return {
                "status": "error",
                "error": f"Network error: {str(e)}",
                "version_id": version_id
            }
        except Exception as e:
            logger.error(f"Error downloading version {version_id}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "version_id": version_id
            }
    
    def cleanup_old_versions(self, file_name: str, keep_count: int = 5) -> int:
        """
        Clean up old versions of a file, keeping the most recent ones.
        
        Args:
            file_name: File name to clean up versions for
            keep_count: Number of recent versions to keep
            
        Returns:
            Number of files deleted
        """
        if not self.config.KEEP_DOWNLOADED_FILES:
            logger.info("File cleanup is disabled (KEEP_DOWNLOADED_FILES=true)")
            return 0
        
        try:
            file_storage_dir = self.config.get_storage_path(file_name)
            if not file_storage_dir.exists():
                return 0
            
            # Get all files in directory, sorted by modification time
            files = sorted(
                file_storage_dir.glob("*.xlsx"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            # Delete older files
            deleted_count = 0
            for file_path in files[keep_count:]:
                try:
                    file_path.unlink()
                    deleted_count += 1
                    logger.info(f"Deleted old version: {file_path}")
                except Exception as e:
                    logger.warning(f"Could not delete {file_path}: {e}")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return 0
    
    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get information about local storage usage.
        
        Returns:
            Dictionary with storage statistics
        """
        try:
            storage_path = Path(self.config.LOCAL_STORAGE_PATH)
            
            if not storage_path.exists():
                return {
                    "exists": False,
                    "total_size": 0,
                    "file_count": 0,
                    "directory_count": 0
                }
            
            total_size = 0
            file_count = 0
            directory_count = 0
            
            for item in storage_path.rglob("*"):
                if item.is_file():
                    total_size += item.stat().st_size
                    file_count += 1
                elif item.is_dir():
                    directory_count += 1
            
            return {
                "exists": True,
                "path": str(storage_path.absolute()),
                "total_size": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "file_count": file_count,
                "directory_count": directory_count
            }
            
        except Exception as e:
            logger.error(f"Error getting storage info: {e}")
            return {
                "exists": False,
                "error": str(e)
            }