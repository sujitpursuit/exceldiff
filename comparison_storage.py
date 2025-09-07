"""
Comparison Storage Manager

A reusable class for managing version comparison results storage.
This class can be used across different APIs and applications.
"""

import pyodbc
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

@dataclass
class ComparisonResult:
    """Data class for comparison result information."""
    file1_version_id: int
    file2_version_id: int
    comparison_title: Optional[str] = None
    comparison_status: str = 'completed'
    html_report_url: Optional[str] = None
    json_report_url: Optional[str] = None
    local_html_path: Optional[str] = None
    local_json_path: Optional[str] = None
    total_changes: int = 0
    added_mappings: int = 0
    modified_mappings: int = 0
    deleted_mappings: int = 0
    tabs_compared: int = 0
    comparison_duration_seconds: Optional[float] = None
    user_notes: Optional[str] = None


class ComparisonStorageManager:
    """
    Manages storage and retrieval of version comparison results.
    
    This class provides a reusable interface for storing comparison results
    in the database and can be used across different APIs and applications.
    """
    
    def __init__(self, connection_string: str, logger: Optional[logging.Logger] = None):
        """
        Initialize the ComparisonStorageManager.
        
        Args:
            connection_string: Database connection string
            logger: Optional logger instance
        """
        self.connection_string = connection_string
        self.logger = logger or logging.getLogger(__name__)
    
    def get_connection(self) -> pyodbc.Connection:
        """Get database connection."""
        try:
            return pyodbc.connect(self.connection_string)
        except Exception as e:
            self.logger.error(f"Database connection failed: {e}")
            raise
    
    def store_comparison_result(self, result: ComparisonResult) -> int:
        """
        Store a comparison result in the database.
        
        Args:
            result: ComparisonResult object with comparison data
            
        Returns:
            int: The ID of the stored comparison record
            
        Raises:
            Exception: If storage fails
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            insert_sql = """
            INSERT INTO version_comparisons (
                file1_version_id, file2_version_id, comparison_title, comparison_status,
                html_report_url, json_report_url, local_html_path, local_json_path,
                total_changes, added_mappings, modified_mappings, deleted_mappings, tabs_compared,
                comparison_duration_seconds, user_notes, comparison_taken_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE())
            """
            
            cursor.execute(insert_sql, (
                result.file1_version_id,
                result.file2_version_id,
                result.comparison_title,
                result.comparison_status,
                result.html_report_url,
                result.json_report_url,
                result.local_html_path,
                result.local_json_path,
                result.total_changes,
                result.added_mappings,
                result.modified_mappings,
                result.deleted_mappings,
                result.tabs_compared,
                result.comparison_duration_seconds,
                result.user_notes
            ))
            
            # Get the ID of the inserted record
            cursor.execute("SELECT @@IDENTITY")
            comparison_id = cursor.fetchone()[0]
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Stored comparison result with ID {comparison_id}: versions {result.file1_version_id} vs {result.file2_version_id}")
            return int(comparison_id)
            
        except Exception as e:
            self.logger.error(f"Failed to store comparison result: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            raise
    
    def get_comparison_by_id(self, comparison_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a comparison result by its ID.
        
        Args:
            comparison_id: The comparison ID
            
        Returns:
            Dict with comparison data or None if not found
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = """
            SELECT 
                id, file1_version_id, file2_version_id, comparison_title, comparison_status,
                html_report_url, json_report_url, local_html_path, local_json_path,
                total_changes, added_mappings, modified_mappings, deleted_mappings, tabs_compared,
                comparison_duration_seconds, comparison_taken_at, created_at, user_notes, is_archived
            FROM version_comparisons 
            WHERE id = ?
            """
            
            cursor.execute(query, (comparison_id,))
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            return {
                "id": row.id,
                "file1_version_id": row.file1_version_id,
                "file2_version_id": row.file2_version_id,
                "comparison_title": row.comparison_title,
                "comparison_status": row.comparison_status,
                "html_report_url": row.html_report_url,
                "json_report_url": row.json_report_url,
                "local_html_path": row.local_html_path,
                "local_json_path": row.local_json_path,
                "total_changes": row.total_changes,
                "added_mappings": row.added_mappings,
                "modified_mappings": row.modified_mappings,
                "deleted_mappings": row.deleted_mappings,
                "tabs_compared": row.tabs_compared,
                "comparison_duration_seconds": float(row.comparison_duration_seconds) if row.comparison_duration_seconds else None,
                "comparison_taken_at": row.comparison_taken_at.isoformat() if row.comparison_taken_at else None,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "user_notes": row.user_notes,
                "is_archived": bool(row.is_archived)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get comparison {comparison_id}: {e}")
            if 'conn' in locals():
                conn.close()
            raise
    
    def get_comparisons_for_versions(self, version1_id: int, version2_id: int) -> List[Dict[str, Any]]:
        """
        Get all comparisons between two specific versions.
        
        Args:
            version1_id: First version ID
            version2_id: Second version ID
            
        Returns:
            List of comparison records
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = """
            SELECT 
                id, file1_version_id, file2_version_id, comparison_title, comparison_status,
                html_report_url, json_report_url, total_changes, comparison_taken_at
            FROM version_comparisons 
            WHERE (file1_version_id = ? AND file2_version_id = ?) 
               OR (file1_version_id = ? AND file2_version_id = ?)
            ORDER BY comparison_taken_at DESC
            """
            
            cursor.execute(query, (version1_id, version2_id, version2_id, version1_id))
            rows = cursor.fetchall()
            conn.close()
            
            return [{
                "id": row.id,
                "file1_version_id": row.file1_version_id,
                "file2_version_id": row.file2_version_id,
                "comparison_title": row.comparison_title,
                "comparison_status": row.comparison_status,
                "html_report_url": row.html_report_url,
                "json_report_url": row.json_report_url,
                "total_changes": row.total_changes,
                "comparison_taken_at": row.comparison_taken_at.isoformat() if row.comparison_taken_at else None
            } for row in rows]
            
        except Exception as e:
            self.logger.error(f"Failed to get comparisons for versions {version1_id}, {version2_id}: {e}")
            if 'conn' in locals():
                conn.close()
            raise
    
    def get_version_comparison_history(self, version_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get comparison history for a specific version.
        
        Args:
            version_id: Version ID to get history for
            limit: Maximum number of results to return
            
        Returns:
            List of comparison records involving this version
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = """
            SELECT TOP (?)
                id, file1_version_id, file2_version_id, comparison_title, comparison_status,
                html_report_url, json_report_url, total_changes, comparison_taken_at
            FROM version_comparisons 
            WHERE file1_version_id = ? OR file2_version_id = ?
            ORDER BY comparison_taken_at DESC
            """
            
            cursor.execute(query, (limit, version_id, version_id))
            rows = cursor.fetchall()
            conn.close()
            
            return [{
                "id": row.id,
                "file1_version_id": row.file1_version_id,
                "file2_version_id": row.file2_version_id,
                "comparison_title": row.comparison_title,
                "comparison_status": row.comparison_status,
                "html_report_url": row.html_report_url,
                "json_report_url": row.json_report_url,
                "total_changes": row.total_changes,
                "comparison_taken_at": row.comparison_taken_at.isoformat() if row.comparison_taken_at else None,
                "other_version_id": row.file2_version_id if row.file1_version_id == version_id else row.file1_version_id
            } for row in rows]
            
        except Exception as e:
            self.logger.error(f"Failed to get comparison history for version {version_id}: {e}")
            if 'conn' in locals():
                conn.close()
            raise
    
    def update_comparison_status(self, comparison_id: int, status: str, notes: Optional[str] = None) -> bool:
        """
        Update the status of a comparison.
        
        Args:
            comparison_id: Comparison ID to update
            status: New status ('completed', 'processing', 'failed', 'archived')
            notes: Optional notes to add
            
        Returns:
            bool: True if update was successful
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if notes:
                query = """
                UPDATE version_comparisons 
                SET comparison_status = ?, user_notes = ? 
                WHERE id = ?
                """
                cursor.execute(query, (status, notes, comparison_id))
            else:
                query = """
                UPDATE version_comparisons 
                SET comparison_status = ? 
                WHERE id = ?
                """
                cursor.execute(query, (status, comparison_id))
            
            rows_affected = cursor.rowcount
            conn.commit()
            conn.close()
            
            if rows_affected > 0:
                self.logger.info(f"Updated comparison {comparison_id} status to {status}")
                return True
            else:
                self.logger.warning(f"No comparison found with ID {comparison_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to update comparison {comparison_id} status: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return False
    
    def archive_old_comparisons(self, days_old: int = 90) -> int:
        """
        Archive comparisons older than specified days.
        
        Args:
            days_old: Number of days old to consider for archiving
            
        Returns:
            int: Number of comparisons archived
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = """
            UPDATE version_comparisons 
            SET is_archived = 1 
            WHERE is_archived = 0 
              AND comparison_taken_at < DATEADD(day, ?, GETDATE())
            """
            
            cursor.execute(query, (-days_old,))
            rows_affected = cursor.rowcount
            conn.commit()
            conn.close()
            
            self.logger.info(f"Archived {rows_affected} comparisons older than {days_old} days")
            return rows_affected
            
        except Exception as e:
            self.logger.error(f"Failed to archive old comparisons: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            raise
    
    def get_comparison_statistics(self) -> Dict[str, Any]:
        """
        Get overall statistics about stored comparisons.
        
        Returns:
            Dict with statistics about comparisons
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            stats_query = """
            SELECT 
                COUNT(*) as total_comparisons,
                COUNT(CASE WHEN comparison_status = 'completed' THEN 1 END) as completed_comparisons,
                COUNT(CASE WHEN comparison_status = 'failed' THEN 1 END) as failed_comparisons,
                COUNT(CASE WHEN is_archived = 1 THEN 1 END) as archived_comparisons,
                AVG(CAST(comparison_duration_seconds as FLOAT)) as avg_duration_seconds,
                AVG(CAST(total_changes as FLOAT)) as avg_changes_per_comparison,
                MAX(comparison_taken_at) as latest_comparison,
                MIN(comparison_taken_at) as earliest_comparison
            FROM version_comparisons
            """
            
            cursor.execute(stats_query)
            row = cursor.fetchone()
            conn.close()
            
            return {
                "total_comparisons": row.total_comparisons or 0,
                "completed_comparisons": row.completed_comparisons or 0,
                "failed_comparisons": row.failed_comparisons or 0,
                "archived_comparisons": row.archived_comparisons or 0,
                "avg_duration_seconds": round(row.avg_duration_seconds, 3) if row.avg_duration_seconds else 0,
                "avg_changes_per_comparison": round(row.avg_changes_per_comparison, 1) if row.avg_changes_per_comparison else 0,
                "latest_comparison": row.latest_comparison.isoformat() if row.latest_comparison else None,
                "earliest_comparison": row.earliest_comparison.isoformat() if row.earliest_comparison else None
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get comparison statistics: {e}")
            if 'conn' in locals():
                conn.close()
            raise