"""
Utility Functions

This module contains helper functions for data processing, file handling,
and other utilities used throughout the Excel comparison tool.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Set
from pathlib import Path
import shutil
from datetime import datetime

from data_models import ComparisonResult, TabComparison, MappingRecord
from exceptions import FileValidationError, ProcessingError
from logger import get_logger, log_exception

logger = get_logger(__name__)


def validate_file_path(file_path: str) -> tuple[bool, str]:
    """
    Validate that a file path exists and is a valid Excel file.
    
    Args:
        file_path: Path to the file to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        path = Path(file_path)
        
        if not path.exists():
            return False, f"File does not exist: {file_path}"
        
        if not path.is_file():
            return False, f"Path is not a file: {file_path}"
        
        if path.suffix.lower() not in ['.xlsx', '.xls']:
            return False, f"File is not an Excel file (.xlsx/.xls): {file_path}"
        
        if path.stat().st_size == 0:
            return False, f"File is empty: {file_path}"
        
        return True, ""
        
    except Exception as e:
        return False, f"Error validating file path: {e}"


def create_output_directory(output_path: str) -> tuple[bool, str]:
    """
    Create output directory if it doesn't exist.
    
    Args:
        output_path: Path where output files will be created
        
    Returns:
        Tuple of (success, error_message)
    """
    try:
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        return True, ""
    except Exception as e:
        return False, f"Failed to create output directory: {e}"


def generate_output_filename(file1_path: str, file2_path: str, extension: str = ".html") -> str:
    """
    Generate a descriptive output filename based on input files.
    
    Args:
        file1_path: Path to first file
        file2_path: Path to second file
        extension: File extension for output file
        
    Returns:
        Generated filename
    """
    file1_name = Path(file1_path).stem
    file2_name = Path(file2_path).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    return f"comparison_{file1_name}_vs_{file2_name}_{timestamp}{extension}"


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing/replacing invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for filesystem
    """
    # Characters not allowed in filenames
    invalid_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
    
    sanitized = filename
    for char in invalid_chars:
        sanitized = sanitized.replace(char, '_')
    
    # Replace multiple underscores with single underscore
    while '__' in sanitized:
        sanitized = sanitized.replace('__', '_')
    
    # Remove leading/trailing underscores and spaces
    sanitized = sanitized.strip('_ ')
    
    return sanitized


def get_file_info(file_path: str) -> Dict[str, Any]:
    """
    Get detailed information about a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dictionary with file information
    """
    try:
        path = Path(file_path)
        stat = path.stat()
        
        return {
            'path': str(path.absolute()),
            'name': path.name,
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            'extension': path.suffix.lower(),
            'exists': True
        }
    except Exception as e:
        return {
            'path': file_path,
            'error': str(e),
            'exists': False
        }


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string (e.g., "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.1f} {units[unit_index]}"


def get_comparison_statistics(comparison_result: ComparisonResult) -> Dict[str, Any]:
    """
    Extract detailed statistics from a comparison result.
    
    Args:
        comparison_result: ComparisonResult object
        
    Returns:
        Dictionary with detailed statistics
    """
    stats = {
        'summary': {
            'total_tabs_compared': len(comparison_result.tab_comparisons),
            'tabs_with_changes': len(comparison_result.changed_tabs),
            'total_changes': 0
        },
        'tab_changes': {},
        'mapping_changes': {
            'added': 0,
            'deleted': 0,
            'modified': 0
        },
        'change_distribution': {}
    }
    
    # Analyze each tab comparison
    for tab_name, tab_comparison in comparison_result.tab_comparisons.items():
        if tab_comparison.has_changes:
            changes = tab_comparison.change_summary
            stats['tab_changes'][tab_name] = changes
            
            # Add to totals
            stats['mapping_changes']['added'] += changes['added']
            stats['mapping_changes']['deleted'] += changes['deleted']
            stats['mapping_changes']['modified'] += changes['modified']
            
            total_tab_changes = sum(changes.values())
            stats['summary']['total_changes'] += total_tab_changes
            
            # Track change distribution
            if total_tab_changes not in stats['change_distribution']:
                stats['change_distribution'][total_tab_changes] = 0
            stats['change_distribution'][total_tab_changes] += 1
    
    return stats


def find_similar_mappings(mapping: MappingRecord, mapping_list: List[MappingRecord], 
                         similarity_threshold: float = 0.8) -> List[tuple[MappingRecord, float]]:
    """
    Find mappings similar to a given mapping based on field content.
    
    Args:
        mapping: The mapping to find similarities for
        mapping_list: List of mappings to search in
        similarity_threshold: Minimum similarity score (0.0 to 1.0)
        
    Returns:
        List of tuples (similar_mapping, similarity_score) sorted by similarity
    """
    similarities = []
    
    for candidate in mapping_list:
        similarity = calculate_mapping_similarity(mapping, candidate)
        if similarity >= similarity_threshold:
            similarities.append((candidate, similarity))
    
    # Sort by similarity score (highest first)
    similarities.sort(key=lambda x: x[1], reverse=True)
    
    return similarities


def calculate_mapping_similarity(mapping1: MappingRecord, mapping2: MappingRecord) -> float:
    """
    Calculate similarity score between two mappings.
    
    Args:
        mapping1: First mapping
        mapping2: Second mapping
        
    Returns:
        Similarity score between 0.0 and 1.0
    """
    # Key fields for similarity calculation
    key_fields = [
        'source_canonical', 'source_field', 'target_canonical', 'target_field'
    ]
    
    matches = 0
    total_fields = len(key_fields)
    
    for field in key_fields:
        value1 = getattr(mapping1, field, "").lower().strip()
        value2 = getattr(mapping2, field, "").lower().strip()
        
        if value1 and value2:
            # Calculate string similarity (simple approach)
            if value1 == value2:
                matches += 1
            elif value1 in value2 or value2 in value1:
                matches += 0.5  # Partial match
        elif not value1 and not value2:
            matches += 1  # Both empty counts as match
    
    return matches / total_fields if total_fields > 0 else 0.0


def group_mappings_by_system(mappings: List[MappingRecord]) -> Dict[str, List[MappingRecord]]:
    """
    Group mappings by their source and target systems.
    
    Args:
        mappings: List of mapping records
        
    Returns:
        Dictionary grouped by system pairs
    """
    groups = {}
    
    for mapping in mappings:
        source = mapping.source_canonical or "Unknown"
        target = mapping.target_canonical or "Unknown"
        key = f"{source} -> {target}"
        
        if key not in groups:
            groups[key] = []
        groups[key].append(mapping)
    
    return groups


def export_mappings_to_csv(mappings: List[MappingRecord], output_path: str) -> bool:
    """
    Export mappings to CSV format for external analysis.
    
    Args:
        mappings: List of mapping records to export
        output_path: Path where CSV file will be created
        
    Returns:
        True if export successful, False otherwise
    """
    try:
        import csv
        
        if not mappings:
            logger.warning("No mappings to export")
            return False
        
        # Determine all possible field names
        all_fields = set(['unique_id', 'source_canonical', 'source_field', 
                         'target_canonical', 'target_field'])
        
        for mapping in mappings:
            if mapping.all_fields:
                all_fields.update(mapping.all_fields.keys())
        
        # Sort field names for consistent column order
        field_names = sorted(all_fields)
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=field_names)
            writer.writeheader()
            
            for mapping in mappings:
                row = {
                    'unique_id': mapping.unique_id,
                    'source_canonical': mapping.source_canonical,
                    'source_field': mapping.source_field,
                    'target_canonical': mapping.target_canonical,
                    'target_field': mapping.target_field
                }
                
                # Add all other fields
                if mapping.all_fields:
                    row.update(mapping.all_fields)
                
                # Ensure all values are strings
                row = {k: str(v) if v is not None else '' for k, v in row.items()}
                
                writer.writerow(row)
        
        logger.info(f"Exported {len(mappings)} mappings to {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to export mappings to CSV: {e}")
        return False


def backup_file(file_path: str, backup_suffix: str = "_backup") -> tuple[bool, str]:
    """
    Create a backup copy of a file.
    
    Args:
        file_path: Path to file to backup
        backup_suffix: Suffix to add to backup filename
        
    Returns:
        Tuple of (success, backup_path_or_error_message)
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return False, f"File does not exist: {file_path}"
        
        # Generate backup filename
        backup_path = path.with_name(f"{path.stem}{backup_suffix}{path.suffix}")
        
        # Handle duplicate backup names
        counter = 1
        while backup_path.exists():
            backup_path = path.with_name(f"{path.stem}{backup_suffix}_{counter}{path.suffix}")
            counter += 1
        
        # Copy file
        shutil.copy2(file_path, backup_path)
        
        logger.info(f"Created backup: {backup_path}")
        return True, str(backup_path)
        
    except Exception as e:
        error_msg = f"Failed to create backup: {e}"
        logger.error(error_msg)
        return False, error_msg


def clean_temp_files(temp_dir: str, max_age_hours: int = 24) -> int:
    """
    Clean up temporary files older than specified age.
    
    Args:
        temp_dir: Directory containing temporary files
        max_age_hours: Maximum age in hours before files are deleted
        
    Returns:
        Number of files deleted
    """
    try:
        temp_path = Path(temp_dir)
        if not temp_path.exists():
            return 0
        
        current_time = datetime.now().timestamp()
        max_age_seconds = max_age_hours * 3600
        deleted_count = 0
        
        for file_path in temp_path.glob("*"):
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    file_path.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted temp file: {file_path}")
        
        logger.info(f"Cleaned {deleted_count} temporary files from {temp_dir}")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Failed to clean temp files: {e}")
        return 0


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """
    Set up logging configuration for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        
    Returns:
        Configured logger instance
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            print(f"Warning: Could not create log file {log_file}: {e}")
    
    return root_logger