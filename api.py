"""
Excel Source-Target Mapping Comparison Tool - REST API

FastAPI wrapper around the existing CLI tool, providing HTTP endpoints
for file upload and comparison while preserving all existing logic.

Usage: uvicorn api:app --host 0.0.0.0 --port 8000 --reload
"""

import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import traceback
import pyodbc
from dotenv import load_dotenv

from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Request, Query
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

# Import Azure storage service
from azure_storage_service import get_azure_storage_service, is_azure_path, AzureStorageError

# Import SharePoint services
from sharepoint import SharePointService, DownloadService

# Load environment variables
load_dotenv()

# Import existing modules (preserve all logic)
from comparator import compare_workbooks
from report_generator import generate_html_report
from json_report_generator import generate_json_report
from utils import validate_file_path
from exceptions import (
    ExcelComparisonError, FileValidationError, ComparisonError,
    ReportGenerationError, create_user_friendly_message
)
from logger import get_logger, PerformanceTimer, log_exception, log_user_action
import config

# Initialize FastAPI app
app = FastAPI(
    title="Excel Comparison API",
    description="REST API for comparing Excel Source-Target mapping files",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup logger
logger = get_logger("api")

# Database configuration from environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

# Create directories for file storage and reports
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

REPORTS_DIR = Path(config.REPORTS_BASE_DIR)
REPORTS_DIR.mkdir(exist_ok=True)

DIFF_REPORTS_DIR = REPORTS_DIR / config.DIFF_REPORTS_DIR
DIFF_REPORTS_DIR.mkdir(exist_ok=True)

# Setup templates and static files
from pathlib import Path
template_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(template_dir))

# Mount static files for serving reports
app.mount("/reports", StaticFiles(directory=str(REPORTS_DIR)), name="reports")
app.mount("/static", StaticFiles(directory="static"), name="static")


class DatabaseManager:
    """Database manager for Azure SQL Server operations."""
    
    def __init__(self):
        self.connection_string = DATABASE_URL
        self.logger = get_logger("database")
    
    def get_connection(self):
        """Get database connection."""
        try:
            return pyodbc.connect(self.connection_string)
        except Exception as e:
            self.logger.error(f"Database connection failed: {e}")
            raise HTTPException(status_code=500, detail="Database connection failed")
    
    def get_file_versions(self, file_identifier: str, search_type: str = "url") -> Dict[str, Any]:
        """
        Get all versions of a file by SharePoint URL or friendly name.
        
        Args:
            file_identifier: SharePoint URL or friendly name
            search_type: "url" for sharepoint_url, "name" for friendly_name
        
        Returns:
            Dictionary with file info and versions
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if search_type == "url":
                # Search by SharePoint URL
                query = """
                SELECT 
                    tf.id as file_id,
                    tf.sharepoint_url,
                    tf.file_name,
                    tf.friendly_name,
                    fv.id as version_id,
                    fv.sequence_number,
                    fv.sharepoint_version_id,
                    fv.modified_datetime,
                    fv.file_size_bytes,
                    fv.discovered_at,
                    fv.diff_taken,
                    fv.diff_taken_at,
                    fv.downloaded,
                    fv.download_filename,
                    fv.downloaded_at,
                    fv.download_error
                FROM tracked_files tf
                JOIN file_versions fv ON tf.id = fv.file_id
                WHERE tf.sharepoint_url = ? AND tf.is_active = 1
                ORDER BY fv.sequence_number DESC
                """
                cursor.execute(query, (file_identifier,))
                
            elif search_type == "name":
                # Search by friendly name (case-insensitive, partial match)
                query = """
                SELECT 
                    tf.id as file_id,
                    tf.sharepoint_url,
                    tf.file_name,
                    tf.friendly_name,
                    fv.id as version_id,
                    fv.sequence_number,
                    fv.sharepoint_version_id,
                    fv.modified_datetime,
                    fv.file_size_bytes,
                    fv.discovered_at,
                    fv.diff_taken,
                    fv.diff_taken_at,
                    fv.downloaded,
                    fv.download_filename,
                    fv.downloaded_at,
                    fv.download_error
                FROM tracked_files tf
                JOIN file_versions fv ON tf.id = fv.file_id
                WHERE (tf.friendly_name LIKE ? OR tf.file_name LIKE ?) AND tf.is_active = 1
                ORDER BY fv.sequence_number DESC
                """
                search_pattern = f"%{file_identifier}%"
                cursor.execute(query, (search_pattern, search_pattern))
            
            else:
                raise HTTPException(status_code=400, detail="search_type must be 'url' or 'name'")
            
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                raise HTTPException(status_code=404, detail=f"No file found with {search_type}: {file_identifier}")
            
            # Extract file info from first row
            first_row = rows[0]
            file_info = {
                "file_id": first_row.file_id,
                "sharepoint_url": first_row.sharepoint_url,
                "file_name": first_row.file_name,
                "friendly_name": first_row.friendly_name,
                "total_versions": len(rows)
            }
            
            # Extract version information
            versions = []
            for row in rows:
                version = {
                    "version_id": row.version_id,
                    "sequence_number": row.sequence_number,
                    "sharepoint_version_id": row.sharepoint_version_id,
                    "modified_datetime": row.modified_datetime.isoformat() if row.modified_datetime else None,
                    "file_size_bytes": row.file_size_bytes,
                    "discovered_at": row.discovered_at.isoformat() if row.discovered_at else None,
                    "diff_taken": bool(row.diff_taken) if row.diff_taken is not None else False,
                    "diff_taken_at": row.diff_taken_at.isoformat() if row.diff_taken_at else None,
                    "downloaded": bool(row.downloaded) if row.downloaded is not None else False,
                    "download_filename": row.download_filename,
                    "downloaded_at": row.downloaded_at.isoformat() if row.downloaded_at else None,
                    "download_error": row.download_error,
                    "is_latest": row.sequence_number == rows[0].sequence_number,
                    "is_available": bool(row.downloaded) and row.download_filename is not None
                }
                versions.append(version)
            
            return {
                "file_info": file_info,
                "versions": versions
            }
            
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            self.logger.error(f"Failed to get file versions: {e}")
            raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
    
    def get_version_download_path(self, version_id: int) -> str:
        """Get download filename for a specific version."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = """
            SELECT download_filename, downloaded
            FROM file_versions 
            WHERE id = ?
            """
            cursor.execute(query, (version_id,))
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                raise HTTPException(status_code=404, detail=f"Version {version_id} not found")
            
            if not row.downloaded or not row.download_filename:
                raise HTTPException(status_code=404, detail=f"Version {version_id} not downloaded or file not available")
            
            return row.download_filename
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Failed to get version download path: {e}")
            raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
    
    def get_sharepoint_info(self, version_id: int) -> Dict[str, Any]:
        """Get SharePoint information for a specific version."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = """
            SELECT 
                tf.sharepoint_url,
                tf.file_name,
                tf.drive_id,
                tf.item_id,
                fv.sharepoint_version_id,
                fv.sequence_number,
                fv.downloaded,
                fv.download_filename
            FROM file_versions fv
            JOIN tracked_files tf ON fv.file_id = tf.id
            WHERE fv.id = ? AND tf.is_active = 1
            """
            cursor.execute(query, (version_id,))
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                raise HTTPException(status_code=404, detail=f"Version {version_id} not found")
            
            return {
                "sharepoint_url": row.sharepoint_url,
                "file_name": row.file_name,
                "drive_id": row.drive_id,
                "item_id": row.item_id,
                "sharepoint_version_id": row.sharepoint_version_id,
                "sequence_number": row.sequence_number,
                "downloaded": bool(row.downloaded) if row.downloaded is not None else False,
                "download_filename": row.download_filename
            }
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Failed to get SharePoint info: {e}")
            raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
    
    def update_download_status(self, version_id: int, download_result: Dict[str, Any]) -> bool:
        """Update download status in the database after SharePoint download."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if download_result.get("status") == "success":
                query = """
                UPDATE file_versions 
                SET downloaded = 1, 
                    download_filename = ?, 
                    downloaded_at = GETDATE(),
                    download_error = NULL
                WHERE id = ?
                """
                cursor.execute(query, (download_result["local_path"], version_id))
            else:
                query = """
                UPDATE file_versions 
                SET downloaded = 0, 
                    download_filename = NULL,
                    download_error = ?
                WHERE id = ?
                """
                cursor.execute(query, (download_result.get("error", "Unknown error"), version_id))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Updated download status for version {version_id}: {download_result.get('status')}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update download status: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return False


class ExcelComparisonAPI:
    """API wrapper class preserving all existing functionality."""
    
    def __init__(self):
        self.logger = get_logger("api_wrapper")
    
    def save_uploaded_file(self, upload_file: UploadFile, prefix: str = "") -> str:
        """Save uploaded file to temp location and return path."""
        try:
            # Generate unique filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            original_name = upload_file.filename or "unknown.xlsx"
            safe_filename = f"{prefix}{timestamp}_{original_name}"
            
            file_path = UPLOAD_DIR / safe_filename
            
            # Save the file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(upload_file.file, buffer)
            
            self.logger.info(f"Uploaded file saved: {file_path}")
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"Failed to save uploaded file: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    def validate_excel_file(self, file_path: str) -> bool:
        """Validate uploaded Excel file using existing validation logic."""
        try:
            is_valid, error = validate_file_path(file_path)
            if not is_valid:
                raise FileValidationError(file_path, error)
            return True
        except Exception as e:
            self.logger.error(f"File validation failed: {e}")
            return False
    
    def perform_comparison(self, file1_path: str, file2_path: str, custom_title: Optional[str] = None, 
                          original_file1_path: Optional[str] = None, original_file2_path: Optional[str] = None,
                          db_file_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform comparison using existing logic and return structured response.
        This preserves ALL existing functionality without modification.
        """
        try:
            self.logger.info(f"Starting API comparison: {file1_path} vs {file2_path}")
            
            # Use existing comparison logic (zero modification)
            with PerformanceTimer(self.logger, "API Excel comparison", f"{file1_path} vs {file2_path}"):
                comparison_result = compare_workbooks(file1_path, file2_path)
            
            if comparison_result.has_errors:
                self.logger.warning(f"Comparison completed with errors: {comparison_result.errors}")
            
            # Generate report files using existing logic
            # Pass original paths for Azure folder naming, fallback to actual paths
            paths_for_naming = (original_file1_path or file1_path, original_file2_path or file2_path)
            report_paths = self.generate_reports(comparison_result, file1_path, file2_path, custom_title, 
                                                original_paths=paths_for_naming, db_file_name=db_file_name)
            
            # Prepare API response
            response_data = {
                "status": "success",
                "message": "Comparison completed successfully",
                "comparison_summary": self.extract_summary(comparison_result),
                "reports": report_paths,
                "files_info": {
                    "file1": {
                        "name": Path(file1_path).name,
                        "size": Path(file1_path).stat().st_size
                    },
                    "file2": {
                        "name": Path(file2_path).name, 
                        "size": Path(file2_path).stat().st_size
                    }
                },
                "processing_info": {
                    "timestamp": datetime.now().isoformat(),
                    "total_tabs_compared": len(comparison_result.tab_comparisons),
                    "has_errors": comparison_result.has_errors,
                    "errors": comparison_result.errors if comparison_result.has_errors else []
                }
            }
            
            return response_data
            
        except Exception as e:
            self.logger.error(f"API comparison failed: {e}")
            log_exception(self.logger, "API comparison", e)
            raise HTTPException(
                status_code=500, 
                detail=f"Comparison failed: {create_user_friendly_message(e) if isinstance(e, ExcelComparisonError) else str(e)}"
            )
    
    def generate_reports(self, result, file1_path: str, file2_path: str, custom_title: Optional[str] = None, 
                        original_paths: Optional[Tuple[str, str]] = None, db_file_name: Optional[str] = None) -> Dict[str, str]:
        """Generate HTML and JSON reports using existing logic and optionally upload to Azure."""
        try:
            # Generate filenames using simplified logic to avoid Windows path length issues
            timestamp = datetime.now().strftime(config.REPORT_TIMESTAMP_FORMAT)
            
            # Extract original filenames from the uploaded file paths
            # For API uploads, use the original filename from the path
            file1_original = Path(file1_path).name
            file2_original = Path(file2_path).name
            
            # Try to extract original names by removing the upload prefix if present
            import re
            if file1_original.startswith('file1_'):
                # Extract original name after timestamp
                match = re.search(r'file1_\d{8}_\d{6}_\d+_(.+)', file1_original)
                if match:
                    file1_clean = match.group(1)
                else:
                    file1_clean = file1_original
            else:
                file1_clean = file1_original
                
            if file2_original.startswith('file2_'):
                # Extract original name after timestamp  
                match = re.search(r'file2_\d{8}_\d{6}_\d+_(.+)', file2_original)
                if match:
                    file2_clean = match.group(1)
                else:
                    file2_clean = file2_original
            else:
                file2_clean = file2_original
            
            # Create shorter, sanitized filenames
            file1_short = re.sub(r'[^a-zA-Z0-9_]', '_', Path(file1_clean).stem)[:20]  # Limit to 20 chars
            file2_short = re.sub(r'[^a-zA-Z0-9_]', '_', Path(file2_clean).stem)[:20]  # Limit to 20 chars
            
            self.logger.info(f"Short filenames: '{file1_short}' vs '{file2_short}'")
            
            # Use a simpler filename template to avoid Windows path length limits
            base_filename = f"comparison_{file1_short}_vs_{file2_short}_{timestamp}"
            self.logger.info(f"Base filename: '{base_filename}'")
            
            html_filename = base_filename + '.html'
            json_filename = base_filename + '.json'
            
            html_path = DIFF_REPORTS_DIR / html_filename
            json_path = DIFF_REPORTS_DIR / json_filename
            
            # Generate title using existing config
            if custom_title:
                report_title = custom_title
            else:
                report_title = config.REPORT_TITLE_TEMPLATE.format(
                    file1=Path(file1_path).name,
                    file2=Path(file2_path).name
                )
            
            # Generate HTML report using existing function
            with PerformanceTimer(self.logger, "API HTML report generation", str(html_path)):
                self.logger.info(f"Attempting to generate HTML report: {html_path}")
                html_success = generate_html_report(result, str(html_path), report_title)
                self.logger.info(f"HTML report generation result: {html_success}")
            
            # Generate JSON report using existing function
            with PerformanceTimer(self.logger, "API JSON report generation", str(json_path)):
                self.logger.info(f"Attempting to generate JSON report: {json_path}")
                json_success = generate_json_report(result, str(json_path), report_title)
                self.logger.info(f"JSON report generation result: {json_success}")
            
            if not html_success or not json_success:
                self.logger.error(f"Report generation failed - HTML: {html_success}, JSON: {json_success}")
                raise ReportGenerationError("Report generation failed", "One or both reports failed to generate")
            
            self.logger.info(f"Reports generated successfully: HTML={html_path}, JSON={json_path}")
            
            # Prepare response with local paths (existing functionality)
            response = {
                "html_report": f"/reports/{config.DIFF_REPORTS_DIR}/{html_path.name}",
                "json_report": f"/reports/{config.DIFF_REPORTS_DIR}/{json_path.name}",
                "html_path": str(html_path),
                "json_path": str(json_path)
            }
            
            # Upload reports to Azure (mandatory for API compatibility)
            try:
                azure_service = get_azure_storage_service()
                
                # Extract base filename for Azure folder structure
                # Use db_file_name if provided (preferred), otherwise fall back to parsing
                base_name = None
                
                if db_file_name:
                    # Use the file_name from database directly - no parsing needed
                    # Remove extension if present
                    base_name = Path(db_file_name).stem if db_file_name else None
                    self.logger.info(f"Using database file_name for Azure folder: {base_name}")
                elif original_paths:
                    # Fall back to original parsing logic if db_file_name not provided
                    original_file1_path, original_file2_path = original_paths
                    if original_file1_path:
                        # For Azure URLs, extract the blob name which has the original filename
                        original_name = Path(original_file1_path).name if not original_file1_path.startswith('http') else original_file1_path.split('/')[-1]
                        # URL decode in case the filename has spaces
                        from urllib.parse import unquote
                        original_name = unquote(original_name)
                        self.logger.info(f"Extracted original filename from file1: {original_name}")
                        base_name = azure_service.extract_base_filename(original_name)
                    elif original_file2_path:
                        original_name = Path(original_file2_path).name if not original_file2_path.startswith('http') else original_file2_path.split('/')[-1]
                        from urllib.parse import unquote
                        original_name = unquote(original_name)
                        self.logger.info(f"Extracted original filename from file2: {original_name}")
                        base_name = azure_service.extract_base_filename(original_name)
                
                if not base_name:
                    base_name = "Comparison Reports"
                
                self.logger.info(f"Using Azure folder base name: {base_name}")
                
                # Upload HTML report to Azure - MANDATORY
                azure_html_url = azure_service.upload_report_to_azure(
                    str(html_path), 
                    base_name, 
                    html_filename
                )
                
                # Upload JSON report to Azure - MANDATORY
                azure_json_url = azure_service.upload_report_to_azure(
                    str(json_path), 
                    base_name, 
                    json_filename
                )
                
                # Add Azure URLs to response (always present)
                response["azure_html_url"] = azure_html_url
                response["azure_json_url"] = azure_json_url
                response["azure_html_blob"] = f"{base_name}/{html_filename}"
                response["azure_json_blob"] = f"{base_name}/{json_filename}"
                
                self.logger.info(f"HTML report uploaded to Azure: {azure_html_url}")
                self.logger.info(f"JSON report uploaded to Azure: {azure_json_url}")
                
            except AzureStorageError as e:
                self.logger.error(f"Azure storage error during report upload: {e}")
                raise ReportGenerationError(
                    "Azure report upload failed", 
                    f"Reports could not be uploaded to Azure blob storage: {str(e)}"
                )
            except Exception as e:
                self.logger.error(f"Unexpected error during Azure upload: {e}")
                raise ReportGenerationError(
                    "Azure report upload failed", 
                    f"Unexpected error uploading reports to Azure: {str(e)}"
                )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Report generation failed: {e}")
            log_exception(self.logger, "API report generation", e)
            raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")
    
    def extract_summary(self, result) -> Dict[str, Any]:
        """Extract comparison summary for API response."""
        try:
            if not hasattr(result, 'summary') or not result.summary:
                return {"message": "No summary available"}
            
            summary = result.summary
            
            # Calculate total changes
            total_changes = (
                summary.tabs_added + summary.tabs_deleted + summary.tabs_modified +
                summary.total_mappings_added + summary.total_mappings_deleted + summary.total_mappings_modified
            )
            
            # Get changed tabs details
            changed_tabs = []
            if hasattr(result, 'tab_comparisons'):
                for tab_name, comparison in result.tab_comparisons.items():
                    if comparison.has_changes:
                        changes = comparison.change_summary
                        changed_tabs.append({
                            "name": tab_name,
                            "added": changes.get('added', 0),
                            "deleted": changes.get('deleted', 0),
                            "modified": changes.get('modified', 0)
                        })
            
            return {
                "total_changes": total_changes,
                "tabs": {
                    "total_v1": summary.total_tabs_v1,
                    "total_v2": summary.total_tabs_v2,
                    "added": summary.tabs_added,
                    "deleted": summary.tabs_deleted,
                    "modified": summary.tabs_modified,
                    "unchanged": summary.tabs_unchanged
                },
                "mappings": {
                    "total_v1": summary.total_mappings_v1,
                    "total_v2": summary.total_mappings_v2,
                    "added": summary.total_mappings_added,
                    "deleted": summary.total_mappings_deleted,
                    "modified": summary.total_mappings_modified
                },
                "changed_tabs": changed_tabs
            }
            
        except Exception as e:
            self.logger.warning(f"Failed to extract summary: {e}")
            return {"error": "Failed to extract summary", "message": str(e)}
    
    def cleanup_uploaded_files(self, *file_paths):
        """Clean up uploaded temporary files."""
        for file_path in file_paths:
            try:
                if file_path and Path(file_path).exists():
                    Path(file_path).unlink()
                    self.logger.info(f"Cleaned up uploaded file: {file_path}")
            except Exception as e:
                self.logger.warning(f"Failed to cleanup file {file_path}: {e}")
    
    def compare_file_versions_by_path(self, file1_path: str, file2_path: str, custom_title: Optional[str] = None, 
                                      db_file_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Compare two Excel files using their file paths directly.
        This method supports both local file paths and Azure blob paths.
        
        Args:
            file1_path: Path to the first Excel file (local path or Azure blob path)
            file2_path: Path to the second Excel file (local path or Azure blob path)
            custom_title: Optional custom title for the comparison report
            
        Returns:
            Dictionary with comparison results matching the structure of compare_excel endpoint
            
        Raises:
            HTTPException: If files don't exist or comparison fails
        """
        temp_file1 = None
        temp_file2 = None
        
        try:
            self.logger.info(f"Starting version comparison by path: {file1_path} vs {file2_path}")
            
            # Step 1: Determine if files are local or Azure blobs
            file1_is_azure = is_azure_path(file1_path)
            file2_is_azure = is_azure_path(file2_path)
            
            self.logger.info(f"File 1 is Azure blob: {file1_is_azure}")
            self.logger.info(f"File 2 is Azure blob: {file2_is_azure}")
            
            # Step 2: Get local file paths (download from Azure if needed)
            if file1_is_azure:
                try:
                    azure_service = get_azure_storage_service()
                    temp_file1 = azure_service.download_blob_to_temp(file1_path)
                    actual_file1_path = temp_file1
                    self.logger.info(f"Downloaded file 1 from Azure to: {temp_file1}")
                except AzureStorageError as e:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Failed to download first file from Azure: {str(e)}"
                    )
            else:
                # Local file - validate path
                path1 = Path(file1_path)
                if not path1.is_absolute():
                    path1 = Path.cwd() / path1
                
                if not path1.exists():
                    self.logger.error(f"Local file 1 not found: {path1}")
                    raise HTTPException(
                        status_code=404,
                        detail=f"First file not found: {file1_path}"
                    )
                
                if not path1.is_file():
                    raise HTTPException(
                        status_code=400,
                        detail=f"First path is not a file: {file1_path}"
                    )
                
                actual_file1_path = str(path1)
            
            if file2_is_azure:
                try:
                    azure_service = get_azure_storage_service()
                    temp_file2 = azure_service.download_blob_to_temp(file2_path)
                    actual_file2_path = temp_file2
                    self.logger.info(f"Downloaded file 2 from Azure to: {temp_file2}")
                except AzureStorageError as e:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Failed to download second file from Azure: {str(e)}"
                    )
            else:
                # Local file - validate path
                path2 = Path(file2_path)
                if not path2.is_absolute():
                    path2 = Path.cwd() / path2
                
                if not path2.exists():
                    self.logger.error(f"Local file 2 not found: {path2}")
                    raise HTTPException(
                        status_code=404,
                        detail=f"Second file not found: {file2_path}"
                    )
                
                if not path2.is_file():
                    raise HTTPException(
                        status_code=400,
                        detail=f"Second path is not a file: {file2_path}"
                    )
                
                actual_file2_path = str(path2)
            
            # Step 3: Validate file extensions
            allowed_extensions = ['.xlsx', '.xls']
            
            file1_ext = Path(actual_file1_path).suffix.lower()
            file2_ext = Path(actual_file2_path).suffix.lower()
            
            if file1_ext not in allowed_extensions:
                raise HTTPException(
                    status_code=400,
                    detail=f"First file is not an Excel file: {file1_ext}"
                )
            
            if file2_ext not in allowed_extensions:
                raise HTTPException(
                    status_code=400,
                    detail=f"Second file is not an Excel file: {file2_ext}"
                )
            
            # Step 4: Validate Excel files using existing validation
            if not self.validate_excel_file(actual_file1_path):
                raise HTTPException(
                    status_code=400,
                    detail=f"First file is not a valid Excel file"
                )
            
            if not self.validate_excel_file(actual_file2_path):
                raise HTTPException(
                    status_code=400,
                    detail=f"Second file is not a valid Excel file"
                )
            
            # Step 5: Perform comparison using existing logic
            # This reuses the exact same comparison logic as compare_excel endpoint
            result = self.perform_comparison(actual_file1_path, actual_file2_path, custom_title, 
                                           original_file1_path=file1_path, original_file2_path=file2_path,
                                           db_file_name=db_file_name)
            
            # Log successful comparison
            self.logger.info(
                f"Version comparison completed successfully. "
                f"Total changes: {result['comparison_summary']['total_changes']}"
            )
            
            return result
            
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
            
        except AzureStorageError as e:
            # Handle Azure-specific errors
            self.logger.error(f"Azure storage error in compare_file_versions_by_path: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Azure storage error: {str(e)}"
            )
            
        except Exception as e:
            # Log unexpected errors with full traceback for debugging
            self.logger.error(f"Unexpected error in compare_file_versions_by_path: {e}")
            self.logger.error(traceback.format_exc())
            
            # Create user-friendly error message
            error_detail = str(e)
            if isinstance(e, ExcelComparisonError):
                error_detail = create_user_friendly_message(e)
            
            raise HTTPException(
                status_code=500,
                detail=f"Failed to compare files: {error_detail}"
            )
            
        finally:
            # Clean up temporary Azure files
            if temp_file1:
                try:
                    from azure_storage_service import AzureStorageService
                    AzureStorageService.cleanup_temp_file(temp_file1)
                except Exception as e:
                    self.logger.warning(f"Failed to cleanup temp file 1: {e}")
                    
            if temp_file2:
                try:
                    from azure_storage_service import AzureStorageService
                    AzureStorageService.cleanup_temp_file(temp_file2)
                except Exception as e:
                    self.logger.warning(f"Failed to cleanup temp file 2: {e}")
    
    def compare_versions_with_sharepoint(self, version1_id: int, version2_id: int, 
                                        custom_title: Optional[str] = None) -> Dict[str, Any]:
        """
        Compare two file versions with automatic SharePoint download if needed.
        
        This method checks if versions are available locally, downloads from SharePoint
        if needed, then performs the comparison.
        
        Args:
            version1_id: Database ID of the first version
            version2_id: Database ID of the second version
            custom_title: Optional custom title for the comparison report
            
        Returns:
            Dictionary with comparison results
            
        Raises:
            HTTPException: If versions don't exist or comparison fails
        """
        try:
            self.logger.info(f"Starting SharePoint-aware version comparison: {version1_id} vs {version2_id}")
            
            # Get version information from database
            version1_info = db_manager.get_sharepoint_info(version1_id)
            version2_info = db_manager.get_sharepoint_info(version2_id)
            
            # Ensure older version is file1, newer version is file2
            if version1_info["sequence_number"] > version2_info["sequence_number"]:
                # Swap if version1 is newer than version2
                version1_id, version2_id = version2_id, version1_id
                version1_info, version2_info = version2_info, version1_info
                self.logger.info(f"Swapped versions for correct order: older={version1_id} vs newer={version2_id}")
            
            # Initialize download service
            download_service = DownloadService()
            
            # Check/download version 1 (older)
            file1_path = self._ensure_version_downloaded(version1_id, version1_info, download_service)
            # Check/download version 2 (newer)
            file2_path = self._ensure_version_downloaded(version2_id, version2_info, download_service)
            
            # Use the existing comparison logic with older file as file1, newer file as file2
            return self.compare_file_versions_by_path(
                file1_path=file1_path,
                file2_path=file2_path,
                custom_title=custom_title,
                db_file_name=version1_info["file_name"]
            )
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"SharePoint version comparison failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to compare SharePoint versions: {str(e)}"
            )
    
    def _ensure_version_downloaded(self, version_id: int, version_info: Dict[str, Any], 
                                  download_service) -> str:
        """
        Ensure a version is downloaded locally, downloading if necessary.
        
        Returns the local file path for the version.
        """
        # Check if already downloaded and file exists locally
        if version_info["downloaded"] and version_info["download_filename"]:
            if download_service.check_local_file(version_info["download_filename"]):
                self.logger.info(f"Version {version_id} already available locally: {version_info['download_filename']}")
                return version_info["download_filename"]
            else:
                self.logger.warning(f"Version {version_id} marked as downloaded but file missing: {version_info['download_filename']}")
        
        # Need to download from SharePoint
        self.logger.info(f"Downloading version {version_id} from SharePoint")
        
        download_result = download_service.download_version(
            drive_id=version_info["drive_id"],
            item_id=version_info["item_id"],
            version_id=version_info["sharepoint_version_id"],
            file_name=version_info["file_name"],
            sequence_number=version_info["sequence_number"],
            force_download=False
        )
        
        if download_result.get("status") != "success":
            raise HTTPException(
                status_code=500,
                detail=f"Failed to download version {version_id}: {download_result.get('error', 'Unknown error')}"
            )
        
        # Update database
        db_manager.update_download_status(version_id, download_result)
        
        return download_result["local_path"]


# Initialize API wrapper and database manager
api_wrapper = ExcelComparisonAPI()
db_manager = DatabaseManager()


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root endpoint - serves the Alpine.js frontend application."""
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        # Fallback: serve template directly
        from pathlib import Path
        template_path = Path("templates/index.html")
        if template_path.exists():
            return HTMLResponse(content=template_path.read_text(encoding='utf-8'))
        else:
            return HTMLResponse(content="<h1>Template not found</h1><p>Please check templates/index.html</p>")


@app.post("/api/compare-excel")
async def compare_excel_files(
    file1: UploadFile = File(..., description="First Excel file (original/baseline)"),
    file2: UploadFile = File(..., description="Second Excel file (modified/new)"),
    title: Optional[str] = Form(None, description="Custom title for the report")
):
    """
    Compare two Excel files and return comparison results with generated reports.
    
    This endpoint uses the existing CLI logic without modification to ensure
    perfect compatibility and preserve all advanced features.
    """
    file1_path = None
    file2_path = None
    
    try:
        # Log API usage
        log_user_action(logger, "API comparison requested", 
                       f"Files: {file1.filename} vs {file2.filename}")
        
        # Validate file types
        for file, name in [(file1, "file1"), (file2, "file2")]:
            if not file.filename or not any(file.filename.lower().endswith(ext) for ext in ['.xlsx', '.xls']):
                raise HTTPException(
                    status_code=400, 
                    detail=f"{name} must be an Excel file (.xlsx or .xls)"
                )
        
        # Save uploaded files
        file1_path = api_wrapper.save_uploaded_file(file1, "file1_")
        file2_path = api_wrapper.save_uploaded_file(file2, "file2_")
        
        # Validate files using existing validation logic
        if not api_wrapper.validate_excel_file(file1_path):
            raise HTTPException(status_code=400, detail="Invalid first Excel file")
        
        if not api_wrapper.validate_excel_file(file2_path):
            raise HTTPException(status_code=400, detail="Invalid second Excel file")
        
        # Perform comparison using existing logic
        result = api_wrapper.perform_comparison(file1_path, file2_path, title)
        
        # Log successful completion
        log_user_action(logger, "API comparison completed", 
                       f"Files: {file1.filename} vs {file2.filename}, Changes: {result['comparison_summary']['total_changes']}")
        
        return JSONResponse(content=result)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Unexpected API error: {e}")
        log_exception(logger, "API endpoint", e)
        
        error_detail = str(e)
        if isinstance(e, ExcelComparisonError):
            error_detail = create_user_friendly_message(e)
        
        raise HTTPException(status_code=500, detail=f"Internal server error: {error_detail}")
        
    finally:
        # Cleanup uploaded files
        api_wrapper.cleanup_uploaded_files(file1_path, file2_path)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Excel Comparison API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/config")
async def get_config():
    """Get current API configuration."""
    return {
        "supported_extensions": config.SUPPORTED_EXTENSIONS,
        "max_rows_to_process": config.MAX_ROWS_TO_PROCESS,
        "max_columns_to_scan": config.MAX_COLUMNS_TO_SCAN,
        "reports_base_dir": config.REPORTS_BASE_DIR,
        "include_hidden_tabs": not config.SKIP_HIDDEN_TABS
    }


@app.get("/api/download-file") 
async def download_file(path: str = Query(..., description="File path to download")):
    """
    Download a file from the server by its path.
    Used by the frontend to fetch Excel files for comparison.
    
    Args:
        path: The file path from the download_filename field in database
    
    Returns:
        FileResponse with the requested Excel file
    """
    try:
        log_user_action(logger, "File download requested", f"Path: {path}")
        
        # Security: Ensure the path is within allowed directories and doesn't contain path traversal
        safe_path = os.path.normpath(path)
        if '..' in safe_path or safe_path.startswith('/') or ':' in safe_path[1:]:
            raise HTTPException(status_code=400, detail="Invalid file path")
        
        # Convert to absolute path
        file_path = Path(safe_path)
        
        # If path is relative, make it relative to the working directory
        if not file_path.is_absolute():
            file_path = Path.cwd() / file_path
        
        # Check if file exists
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            raise HTTPException(status_code=404, detail=f"File not found: {path}")
        
        # Check if it's actually a file (not a directory)
        if not file_path.is_file():
            logger.warning(f"Path is not a file: {file_path}")
            raise HTTPException(status_code=400, detail=f"Path is not a file: {path}")
        
        # Security: Only allow Excel files
        allowed_extensions = ['.xlsx', '.xls']
        if file_path.suffix.lower() not in allowed_extensions:
            logger.warning(f"File type not allowed: {file_path.suffix}")
            raise HTTPException(status_code=400, detail="Only Excel files are allowed")
        
        logger.info(f"Serving file: {file_path}")
        log_user_action(logger, "File download served", f"File: {file_path}, Size: {file_path.stat().st_size}")
        
        # Return the file
        return FileResponse(
            path=str(file_path),
            filename=file_path.name,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in download_file: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/files/versions")
async def get_file_versions(
    identifier: str = Query(..., description="SharePoint URL or friendly name"),
    search_type: str = Query("name", description="Search type: 'url' or 'name'")
):
    """
    Get all versions of a file by SharePoint URL or friendly name.
    
    Args:
        identifier: SharePoint URL or friendly name to search for
        search_type: "url" to search by sharepoint_url, "name" to search by friendly_name or file_name
    
    Returns:
        JSON response with file info and available versions
    
    Example URLs:
        /api/files/versions?identifier=STTM&search_type=name
        /api/files/versions?identifier=https://...sharepoint-url...&search_type=url
    """
    try:
        log_user_action(logger, "Get file versions requested", f"Identifier: {identifier}, Type: {search_type}")
        
        result = db_manager.get_file_versions(identifier, search_type)
        
        # Add availability summary
        available_versions = [v for v in result["versions"] if v["is_available"]]
        result["summary"] = {
            "total_versions": len(result["versions"]),
            "available_versions": len(available_versions),
            "latest_version": result["versions"][0] if result["versions"] else None
        }
        
        log_user_action(logger, "Get file versions completed", 
                       f"Found {result['summary']['total_versions']} versions, {result['summary']['available_versions']} available")
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_file_versions: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/compare-versions")
async def compare_file_versions(
    file1_path: str = Form(..., description="Path to first Excel file (from download_filename)"),
    file2_path: str = Form(..., description="Path to second Excel file (from download_filename)"),
    title: Optional[str] = Form(None, description="Custom title for the report"),
    file_name: Optional[str] = Form(None, description="Database file_name for Azure folder naming")
):
    """
    Compare two Excel files using their file paths.
    
    This endpoint is designed to work with files that are already downloaded
    from SharePoint and stored locally. The frontend passes the download_filename
    paths from the version data.
    
    Args:
        file1_path: Path to the first Excel file (typically from version's download_filename)
        file2_path: Path to the second Excel file (typically from version's download_filename)
        title: Optional custom title for the comparison report
    
    Returns:
        JSON response with comparison results and report links, matching the
        structure of the /api/compare-excel endpoint
        
    Example Request:
        POST /api/compare-versions
        Form Data:
            file1_path: "downloads/2024/01/mapping_v1.xlsx"
            file2_path: "downloads/2024/01/mapping_v2.xlsx"
            title: "Version 1.0 vs Version 2.0"
    """
    try:
        # Log the comparison request for debugging and audit
        log_user_action(
            logger, 
            "Version comparison requested", 
            f"Files: {file1_path} vs {file2_path}"
        )
        
        # Validate that paths are provided (not empty strings)
        if not file1_path or not file1_path.strip():
            raise HTTPException(
                status_code=400,
                detail="file1_path is required and cannot be empty"
            )
        
        if not file2_path or not file2_path.strip():
            raise HTTPException(
                status_code=400,
                detail="file2_path is required and cannot be empty"
            )
        
        # Use the new method that handles path-based comparison
        result = api_wrapper.compare_file_versions_by_path(
            file1_path=file1_path.strip(),
            file2_path=file2_path.strip(),
            custom_title=title,
            db_file_name=file_name
        )
        
        # Log successful completion with summary
        log_user_action(
            logger,
            "Version comparison completed",
            f"Files: {file1_path} vs {file2_path}, "
            f"Changes: {result['comparison_summary']['total_changes']}"
        )
        
        return JSONResponse(content=result)
        
    except HTTPException:
        # Re-raise HTTP exceptions (these have proper status codes and messages)
        raise
        
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Unexpected error in compare_file_versions endpoint: {e}")
        logger.error(traceback.format_exc())
        
        # Create user-friendly error message
        error_detail = str(e)
        if isinstance(e, ExcelComparisonError):
            error_detail = create_user_friendly_message(e)
        
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {error_detail}"
        )


@app.post("/api/download-sharepoint-version")
async def download_sharepoint_version(
    version_id: int = Form(..., description="Database ID of the version to download"),
    force_download: bool = Form(False, description="Force re-download even if file exists locally")
):
    """
    Download a specific version from SharePoint to local storage.
    
    This endpoint downloads a file version from SharePoint using Microsoft Graph API
    and stores it in persistent local storage. If the file already exists locally
    and force_download is False, it returns the cached file information.
    
    Args:
        version_id: Database ID of the file version to download
        force_download: If True, re-download even if file exists locally
    
    Returns:
        JSON response with download status and file information
        
    Example Request:
        POST /api/download-sharepoint-version
        Form Data:
            version_id: 123
            force_download: false
    """
    try:
        log_user_action(logger, "SharePoint version download requested", f"Version ID: {version_id}")
        
        # Get SharePoint information for this version
        sharepoint_info = db_manager.get_sharepoint_info(version_id)
        
        # Initialize SharePoint services
        download_service = DownloadService()
        
        # Download the version
        download_result = download_service.download_version(
            drive_id=sharepoint_info["drive_id"],
            item_id=sharepoint_info["item_id"],
            version_id=sharepoint_info["sharepoint_version_id"],
            file_name=sharepoint_info["file_name"],
            sequence_number=sharepoint_info["sequence_number"],
            force_download=force_download
        )
        
        # Update database with download status
        db_update_success = db_manager.update_download_status(version_id, download_result)
        
        if not db_update_success:
            logger.warning(f"Failed to update download status in database for version {version_id}")
        
        # Prepare response
        response_data = {
            "version_id": version_id,
            "download_status": download_result.get("status"),
            "file_info": {
                "file_name": sharepoint_info["file_name"],
                "sequence_number": sharepoint_info["sequence_number"],
                "sharepoint_version_id": sharepoint_info["sharepoint_version_id"]
            },
            "local_storage": {
                "local_path": download_result.get("local_path"),
                "full_path": download_result.get("full_path"),
                "file_size": download_result.get("file_size"),
                "from_cache": download_result.get("from_cache", False)
            }
        }
        
        if download_result.get("status") == "success":
            response_data["message"] = download_result.get("message", "Download completed successfully")
            log_user_action(
                logger, 
                "SharePoint version download completed", 
                f"Version {version_id}: {download_result.get('file_size', 0)} bytes"
            )
        else:
            response_data["error"] = download_result.get("error", "Unknown download error")
            response_data["message"] = "Download failed"
            
        return JSONResponse(content=response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in download_sharepoint_version: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/api/get-version-status")
async def get_version_status(
    version_id: int = Query(..., description="Database ID of the version to check")
):
    """
    Get the download status and local availability of a SharePoint version.
    
    This endpoint checks if a version is downloaded locally and provides
    information about its status without triggering a download.
    
    Args:
        version_id: Database ID of the file version to check
    
    Returns:
        JSON response with version status information
        
    Example Request:
        GET /api/get-version-status?version_id=123
    """
    try:
        # Get SharePoint information for this version
        sharepoint_info = db_manager.get_sharepoint_info(version_id)
        
        # Initialize download service to check local file
        download_service = DownloadService()
        
        # Check if file exists locally
        local_file_exists = False
        file_size = None
        full_path = None
        
        if sharepoint_info["downloaded"] and sharepoint_info["download_filename"]:
            local_file_exists = download_service.check_local_file(sharepoint_info["download_filename"])
            if local_file_exists:
                try:
                    from pathlib import Path
                    file_path = Path(sharepoint_info["download_filename"])
                    if not file_path.is_absolute():
                        file_path = Path.cwd() / file_path
                    
                    if file_path.exists():
                        file_size = file_path.stat().st_size
                        full_path = str(file_path.absolute())
                except Exception as e:
                    logger.warning(f"Could not get file stats for {sharepoint_info['download_filename']}: {e}")
        
        response_data = {
            "version_id": version_id,
            "file_info": {
                "file_name": sharepoint_info["file_name"],
                "sequence_number": sharepoint_info["sequence_number"],
                "sharepoint_version_id": sharepoint_info["sharepoint_version_id"]
            },
            "download_status": {
                "downloaded": sharepoint_info["downloaded"],
                "local_file_exists": local_file_exists,
                "download_filename": sharepoint_info["download_filename"],
                "file_size": file_size,
                "full_path": full_path,
                "needs_download": not (sharepoint_info["downloaded"] and local_file_exists)
            }
        }
        
        return JSONResponse(content=response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_version_status: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/api/compare-sharepoint-versions")
async def compare_sharepoint_versions(
    version1_id: int = Form(..., description="Database ID of the first version to compare"),
    version2_id: int = Form(..., description="Database ID of the second version to compare"),
    title: Optional[str] = Form(None, description="Custom title for the report")
):
    """
    Compare two SharePoint file versions with automatic download.
    
    This endpoint compares two file versions by their database IDs, automatically
    downloading from SharePoint if the files are not available locally.
    
    Args:
        version1_id: Database ID of the first file version
        version2_id: Database ID of the second file version
        title: Optional custom title for the comparison report
    
    Returns:
        JSON response with comparison results and report links
        
    Example Request:
        POST /api/compare-sharepoint-versions
        Form Data:
            version1_id: 123
            version2_id: 124
            title: "Version 1.0 vs Version 2.0"
    """
    try:
        log_user_action(
            logger, 
            "SharePoint version comparison requested", 
            f"Versions: {version1_id} vs {version2_id}"
        )
        
        # Use the new SharePoint-aware comparison method
        result = api_wrapper.compare_versions_with_sharepoint(
            version1_id=version1_id,
            version2_id=version2_id,
            custom_title=title
        )
        
        # Log successful completion with summary
        log_user_action(
            logger,
            "SharePoint version comparison completed",
            f"Versions: {version1_id} vs {version2_id}, "
            f"Changes: {result['comparison_summary']['total_changes']}"
        )
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in compare_sharepoint_versions: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


if __name__ == "__main__":
    # For development only - use environment variables or defaults
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run("api:app", host=host, port=port, reload=True)