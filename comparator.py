"""
Comparator Module

This module contains the core comparison logic for analyzing differences
between two Excel workbooks containing Source-Target mapping data.
"""

import logging
from typing import Dict, List, Set, Tuple, Optional
from datetime import datetime

from data_models import (
    TabAnalysis, MappingRecord, ComparisonResult, TabComparison, 
    ComparisonSummary, MappingChange
)
from excel_analyzer import analyze_workbook
from exceptions import (
    ComparisonError, IncompatibleFilesError, ExcelAnalysisError,
    FileValidationError, ProcessingError
)
from logger import get_logger, PerformanceTimer, log_exception

logger = get_logger(__name__)


def compare_workbooks(file1_path: str, file2_path: str) -> ComparisonResult:
    """
    Compare two Excel workbooks and generate a comprehensive comparison result.
    
    Args:
        file1_path: Path to the first (baseline/old) Excel workbook
        file2_path: Path to the second (new/updated) Excel workbook
        
    Returns:
        ComparisonResult object containing all differences and summary
    """
    comparison_result = ComparisonResult()
    comparison_result.file1_path = file1_path
    comparison_result.file2_path = file2_path
    
    try:
        logger.info(f"Starting workbook comparison: '{file1_path}' vs '{file2_path}'")
        
        # Analyze both workbooks with performance timing
        with PerformanceTimer(logger, "first workbook analysis", file1_path):
            logger.info("Analyzing first workbook...")
            workbook1_analysis = analyze_workbook(file1_path)
        
        with PerformanceTimer(logger, "second workbook analysis", file2_path):
            logger.info("Analyzing second workbook...")
            workbook2_analysis = analyze_workbook(file2_path)
        
        # Check for analysis errors
        if "ERROR" in workbook1_analysis:
            comparison_result.add_error(f"Failed to analyze first workbook: {workbook1_analysis['ERROR'].errors}")
            return comparison_result
            
        if "ERROR" in workbook2_analysis:
            comparison_result.add_error(f"Failed to analyze second workbook: {workbook2_analysis['ERROR'].errors}")
            return comparison_result
        
        # Filter out tabs with errors (skipped tabs)
        valid_tabs1 = {name: analysis for name, analysis in workbook1_analysis.items() 
                      if not analysis.errors}
        valid_tabs2 = {name: analysis for name, analysis in workbook2_analysis.items() 
                      if not analysis.errors}
        
        logger.info(f"Valid tabs: File1={len(valid_tabs1)}, File2={len(valid_tabs2)}")
        
        # Compare tabs
        comparison_result.tab_comparisons = compare_all_tabs(valid_tabs1, valid_tabs2)
        
        # Generate summary
        comparison_result.summary = generate_comparison_summary(
            valid_tabs1, valid_tabs2, comparison_result.tab_comparisons
        )
        
        logger.info(f"Comparison complete: {len(comparison_result.tab_comparisons)} tabs compared")
        
    except FileNotFoundError as e:
        error_msg = f"File not found during comparison: {e}"
        logger.error(error_msg)
        comparison_result.add_error(error_msg)
        raise FileValidationError(str(e), "File not found during comparison")
    
    except PermissionError as e:
        error_msg = f"Permission denied accessing file: {e}"
        logger.error(error_msg)
        comparison_result.add_error(error_msg)
        raise FileValidationError(str(e), "Permission denied")
    
    except Exception as e:
        error_msg = f"Failed to compare workbooks: {e}"
        logger.error(error_msg)
        log_exception(logger, "workbook comparison", e)
        comparison_result.add_error(error_msg)
        raise ComparisonError(str(e), file1_path, file2_path)
    
    return comparison_result


def compare_all_tabs(tabs1: Dict[str, TabAnalysis], tabs2: Dict[str, TabAnalysis]) -> Dict[str, TabComparison]:
    """
    Compare all tabs between two workbook analyses.
    
    Args:
        tabs1: Dictionary of tab analyses from first workbook
        tabs2: Dictionary of tab analyses from second workbook
        
    Returns:
        Dictionary mapping tab names to TabComparison objects
    """
    tab_comparisons = {}
    
    # Get all unique tab names from both workbooks
    all_tab_names = set(tabs1.keys()) | set(tabs2.keys())
    
    for tab_name in all_tab_names:
        tab_comparison = compare_single_tab(
            tabs1.get(tab_name), 
            tabs2.get(tab_name), 
            tab_name
        )
        tab_comparisons[tab_name] = tab_comparison
    
    return tab_comparisons


def compare_single_tab(tab1: Optional[TabAnalysis], tab2: Optional[TabAnalysis], 
                      tab_name: str) -> TabComparison:
    """
    Compare a single tab between two workbook versions.
    
    Args:
        tab1: Tab analysis from first workbook (None if tab doesn't exist)
        tab2: Tab analysis from second workbook (None if tab doesn't exist)
        tab_name: Name of the tab being compared
        
    Returns:
        TabComparison object with all differences
    """
    comparison = TabComparison()
    comparison.tab_name = tab_name
    
    # Determine tab status
    if tab1 is None and tab2 is not None:
        # Tab was added
        comparison.status = "added"
        comparison.added_mappings = tab2.mappings.copy()
        logger.debug(f"Tab '{tab_name}' was added with {len(tab2.mappings)} mappings")
        
    elif tab1 is not None and tab2 is None:
        # Tab was deleted
        comparison.status = "deleted" 
        comparison.deleted_mappings = tab1.mappings.copy()
        logger.debug(f"Tab '{tab_name}' was deleted with {len(tab1.mappings)} mappings")
        
    elif tab1 is not None and tab2 is not None:
        # Tab exists in both - compare mappings
        mapping_changes = compare_tab_mappings(tab1.mappings, tab2.mappings)
        
        comparison.added_mappings = mapping_changes["added"]
        comparison.deleted_mappings = mapping_changes["deleted"]
        comparison.modified_mappings = mapping_changes["modified"]
        
        # Check for metadata changes
        comparison.metadata_changes = compare_tab_metadata(tab1.metadata, tab2.metadata)
        
        # Determine overall status
        if comparison.has_changes:
            comparison.status = "modified"
        else:
            comparison.status = "unchanged"
            
        logger.debug(f"Tab '{tab_name}' comparison: {comparison.change_summary}")
    
    else:
        # This shouldn't happen, but handle it gracefully
        comparison.status = "unchanged"
        logger.warning(f"Tab '{tab_name}' comparison: both tabs are None")
    
    return comparison


def compare_tab_mappings(mappings1: List[MappingRecord], mappings2: List[MappingRecord]) -> Dict[str, List]:
    """
    Compare mappings between two tab versions.
    
    Args:
        mappings1: List of mappings from first tab version
        mappings2: List of mappings from second tab version
        
    Returns:
        Dictionary with 'added', 'deleted', and 'modified' mapping lists
    """
    # Create dictionaries keyed by unique_id for efficient lookup
    mappings1_dict = {mapping.unique_id: mapping for mapping in mappings1}
    mappings2_dict = {mapping.unique_id: mapping for mapping in mappings2}
    
    # Get unique IDs from both versions
    ids1 = set(mappings1_dict.keys())
    ids2 = set(mappings2_dict.keys())
    
    # Find added, deleted, and potentially modified mappings
    added_ids = ids2 - ids1
    deleted_ids = ids1 - ids2
    common_ids = ids1 & ids2
    
    # Build result lists
    added_mappings = [mappings2_dict[mapping_id] for mapping_id in added_ids]
    deleted_mappings = [mappings1_dict[mapping_id] for mapping_id in deleted_ids]
    modified_mappings = []
    
    # Check common mappings for modifications
    for mapping_id in common_ids:
        mapping1 = mappings1_dict[mapping_id]
        mapping2 = mappings2_dict[mapping_id]
        
        changes = compare_mapping_fields(mapping1, mapping2)
        logger.debug(f"Comparing mapping {mapping_id}: {len(changes.field_changes)} field changes")
        if changes.field_changes:  # Only add if there are actual changes
            modified_mappings.append(changes)
    
    logger.debug(f"Mapping comparison: +{len(added_mappings)} -{len(deleted_mappings)} ~{len(modified_mappings)}")
    
    return {
        "added": added_mappings,
        "deleted": deleted_mappings,
        "modified": modified_mappings
    }


def compare_mapping_fields(mapping1: MappingRecord, mapping2: MappingRecord) -> MappingChange:
    """
    Compare individual fields between two mapping records.
    
    Args:
        mapping1: Original mapping record
        mapping2: Updated mapping record
        
    Returns:
        MappingChange object with field-level differences
    """
    change = MappingChange(mapping=mapping2, change_type="modified")
    
    # Compare core fields
    core_fields = [
        'source_canonical', 'source_field', 'target_canonical', 'target_field'
    ]
    
    for field in core_fields:
        value1 = getattr(mapping1, field, "")
        value2 = getattr(mapping2, field, "")
        if value1 != value2:
            change.add_field_change(field, value1, value2)
    
    # Compare all other fields from all_fields dictionary
    all_fields1 = mapping1.all_fields or {}
    all_fields2 = mapping2.all_fields or {}
    
    # Get all unique field names from both mappings
    all_field_names = set(all_fields1.keys()) | set(all_fields2.keys())
    
    for field_name in all_field_names:
        value1 = all_fields1.get(field_name, None)
        value2 = all_fields2.get(field_name, None)
        
        # Normalize empty values for comparison
        def normalize_value(val):
            if val is None:
                return ""
            val_str = str(val).strip()
            return val_str
        
        value1_norm = normalize_value(value1)
        value2_norm = normalize_value(value2)
        
        if value1_norm != value2_norm:
            change.add_field_change(field_name, value1, value2)
            logger.debug(f"Field change detected: {field_name} '{value1}' -> '{value2}'")
    
    return change


def compare_tab_metadata(metadata1, metadata2) -> Dict[str, Dict[str, str]]:
    """
    Compare metadata between two tab versions.
    
    Args:
        metadata1: TabMetadata from first version
        metadata2: TabMetadata from second version
        
    Returns:
        Dictionary of metadata changes
    """
    changes = {}
    
    # Compare key metadata fields
    metadata_fields = ['source_system', 'target_system']
    
    for field in metadata_fields:
        value1 = getattr(metadata1, field, "")
        value2 = getattr(metadata2, field, "")
        if value1 != value2:
            changes[field] = {'old': value1, 'new': value2}
    
    return changes


def generate_comparison_summary(tabs1: Dict[str, TabAnalysis], tabs2: Dict[str, TabAnalysis], 
                               tab_comparisons: Dict[str, TabComparison]) -> ComparisonSummary:
    """
    Generate summary statistics for the comparison.
    
    Args:
        tabs1: Tab analyses from first workbook
        tabs2: Tab analyses from second workbook
        tab_comparisons: Results of tab comparisons
        
    Returns:
        ComparisonSummary object with statistics
    """
    summary = ComparisonSummary()
    
    # Basic counts
    summary.total_tabs_v1 = len(tabs1)
    summary.total_tabs_v2 = len(tabs2)
    
    # Tab change counts
    for comparison in tab_comparisons.values():
        if comparison.status == "added":
            summary.tabs_added += 1
        elif comparison.status == "deleted":
            summary.tabs_deleted += 1
        elif comparison.status == "modified":
            summary.tabs_modified += 1
        elif comparison.status == "unchanged":
            summary.tabs_unchanged += 1
    
    # Mapping counts
    summary.total_mappings_v1 = sum(len(tab.mappings) for tab in tabs1.values())
    summary.total_mappings_v2 = sum(len(tab.mappings) for tab in tabs2.values())
    
    # Mapping change counts
    for comparison in tab_comparisons.values():
        summary.total_mappings_added += len(comparison.added_mappings)
        summary.total_mappings_deleted += len(comparison.deleted_mappings)
        summary.total_mappings_modified += len(comparison.modified_mappings)
    
    # Set timestamp
    summary.comparison_timestamp = datetime.now().isoformat()
    
    logger.info(f"Summary generated: {summary.tabs_added} added, {summary.tabs_deleted} deleted, "
               f"{summary.tabs_modified} modified tabs")
    
    return summary


def create_test_comparison(original_file: str, modified_file: str, output_summary: bool = True) -> ComparisonResult:
    """
    Convenience function for testing - compare two files and optionally print summary.
    
    Args:
        original_file: Path to original Excel file
        modified_file: Path to modified Excel file
        output_summary: Whether to print comparison summary
        
    Returns:
        ComparisonResult object
    """
    result = compare_workbooks(original_file, modified_file)
    
    if output_summary and not result.has_errors:
        print(f"\n" + "="*60)
        print(f"COMPARISON SUMMARY: {original_file} -> {modified_file}")
        print("="*60)
        
        summary = result.summary
        print(f"Tabs: {summary.total_tabs_v1} -> {summary.total_tabs_v2}")
        print(f"  Added: {summary.tabs_added}")
        print(f"  Deleted: {summary.tabs_deleted}")  
        print(f"  Modified: {summary.tabs_modified}")
        print(f"  Unchanged: {summary.tabs_unchanged}")
        
        print(f"\nMappings: {summary.total_mappings_v1} -> {summary.total_mappings_v2}")
        print(f"  Added: {summary.total_mappings_added}")
        print(f"  Deleted: {summary.total_mappings_deleted}")
        print(f"  Modified: {summary.total_mappings_modified}")
        
        print(f"\nChanged tabs:")
        for tab_name, comparison in result.tab_comparisons.items():
            if comparison.has_changes:
                changes = comparison.change_summary
                print(f"  {tab_name}: +{changes['added']} -{changes['deleted']} ~{changes['modified']}")
    
    elif result.has_errors:
        print(f"COMPARISON ERRORS:")
        for error in result.errors:
            print(f"  - {error}")
    
    return result