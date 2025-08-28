"""
Comparator Module

This module contains the core comparison logic for analyzing differences
between two Excel workbooks containing Source-Target mapping data.
"""

import logging
from typing import Dict, List, Set, Tuple, Optional, Any
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
import config

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


def resolve_tab_versions(tabs1: Dict[str, TabAnalysis], tabs2: Dict[str, TabAnalysis]) -> Dict[str, Dict[str, Any]]:
    """
    Resolve tab versions to identify active tabs for comparison.
    
    Handles cases where tabs have version suffixes like " (2)", " (3)" etc.
    The highest numbered version (or base if no numbered versions) is considered active.
    
    Args:
        tabs1: Dictionary of tab analyses from first workbook  
        tabs2: Dictionary of tab analyses from second workbook
        
    Returns:
        Dictionary mapping logical_name to {
            'logical_name': str,
            'tab1': TabAnalysis or None,
            'tab2': TabAnalysis or None,
            'physical_name_v1': str or None,
            'physical_name_v2': str or None,
            'version_v1': int,
            'version_v2': int
        }
    """
    import re
    
    def extract_base_name_and_version(tab_name: str) -> tuple[str, int, bool]:
        """Extract base name, version, and truncation flag from tab name.
        
        Returns:
            tuple[str, int, bool]: (base_name, version, is_truncated)
            
        Examples:
            'TabName (2)' -> ('TabName', 2, False)
            'VendorInboundVendorProxytoD (2)' -> ('VendorInboundVendorProxytoD', 2, True) # if 31 chars
        """
        # Pattern to match " (number)" at the end of the string
        pattern = r'^(.+?)\s*\((\d+)\)$'
        match = re.match(pattern, tab_name.strip())
        
        if match:
            base_name = match.group(1).strip()
            version = int(match.group(2))
            
            # Check if this might be a truncated name
            is_truncated = (
                config.ENABLE_TRUNCATED_TAB_MATCHING and 
                len(tab_name.strip()) == config.EXCEL_TAB_NAME_MAX_LENGTH
            )
            
            return base_name, version, is_truncated
        else:
            # No version suffix, this is the base version (version 0)
            return tab_name.strip(), 0, False
    
    def find_truncated_match(truncated_base: str, tab_dict: Dict[str, TabAnalysis]) -> Optional[str]:
        """Find the original tab name that matches a truncated base name.
        
        Args:
            truncated_base: The truncated base name (e.g., "VendorInboundVendorProxytoD")
            tab_dict: Dictionary of tab names to analyze
            
        Returns:
            The full original tab name if found, None otherwise
        """
        candidates = []
        
        for physical_name in tab_dict.keys():
            # Check if this tab starts with the truncated base and is longer
            if (physical_name.startswith(truncated_base) and 
                len(physical_name) > len(truncated_base)):
                
                # Additional validation: ensure it's not a coincidental match
                # The original should be exactly the truncated part + additional characters
                remainder = physical_name[len(truncated_base):]
                if remainder.isalnum() or remainder.replace('_', '').replace('-', '').isalnum():
                    candidates.append(physical_name)
        
        # If we have exactly one candidate, it's likely the original
        if len(candidates) == 1:
            logger.debug(f"Found truncated match: '{truncated_base}' -> '{candidates[0]}'")
            return candidates[0]
        elif len(candidates) > 1:
            # Multiple candidates - choose the shortest one (most likely original)
            best_match = min(candidates, key=len)
            logger.warning(f"Multiple truncated matches for '{truncated_base}': {candidates}. Using: '{best_match}'")
            return best_match
        
        return None
    
    def get_active_tab(tab_dict: Dict[str, TabAnalysis], base_name: str) -> tuple[TabAnalysis, str, int]:
        """Get the active (highest version) tab for a base name"""
        candidates = []
        
        for physical_name, analysis in tab_dict.items():
            extracted_base, version, is_truncated = extract_base_name_and_version(physical_name)
            
            # Handle exact matches
            if extracted_base == base_name:
                candidates.append((analysis, physical_name, version))
            # Handle truncated matches using the mapping
            elif is_truncated and config.ENABLE_TRUNCATED_TAB_MATCHING:
                if truncated_to_original.get(extracted_base) == base_name:
                    candidates.append((analysis, physical_name, version))
        
        if not candidates:
            return None, None, 0
        
        # Return the tab with the highest version number
        return max(candidates, key=lambda x: x[2])
    
    # Combine all tab names from both workbooks for cross-file matching
    all_tabs_combined = {}
    all_tabs_combined.update(tabs1)
    all_tabs_combined.update(tabs2)
    
    # Get all unique base names from both workbooks
    all_base_names = set()
    truncated_bases = set()
    
    for tab_name in tabs1.keys():
        base_name, _, is_truncated = extract_base_name_and_version(tab_name)
        all_base_names.add(base_name)
        if is_truncated:
            truncated_bases.add(base_name)
    
    for tab_name in tabs2.keys():
        base_name, _, is_truncated = extract_base_name_and_version(tab_name)
        all_base_names.add(base_name)
        if is_truncated:
            truncated_bases.add(base_name)
    
    # For each truncated base, try to find the original across both files
    # If found, remove the truncated base and use only the original
    truncated_to_original = {}
    for truncated_base in truncated_bases.copy():
        if config.ENABLE_TRUNCATED_TAB_MATCHING:
            original_match = find_truncated_match(truncated_base, all_tabs_combined)
            if original_match:
                truncated_to_original[truncated_base] = original_match
                all_base_names.add(original_match)
                all_base_names.discard(truncated_base)  # Remove truncated base from logical names
                logger.debug(f"Cross-file truncated match found: '{truncated_base}' -> '{original_match}'")
    
    # Resolve active tabs for each base name
    resolved_tabs = {}
    
    for base_name in all_base_names:
        tab1, physical1, version1 = get_active_tab(tabs1, base_name)
        tab2, physical2, version2 = get_active_tab(tabs2, base_name)
        
        resolved_tabs[base_name] = {
            'logical_name': base_name,
            'tab1': tab1,
            'tab2': tab2,
            'physical_name_v1': physical1,
            'physical_name_v2': physical2,
            'version_v1': version1,
            'version_v2': version2
        }
    
    logger.info(f"Resolved {len(resolved_tabs)} logical tabs from {len(tabs1)} + {len(tabs2)} physical tabs")
    
    # Debug: Log all resolved tab mappings
    for logical_name, resolution in resolved_tabs.items():
        logger.debug(f"  Logical tab '{logical_name}': v1='{resolution['physical_name_v1']}' v2='{resolution['physical_name_v2']}'")
    
    return resolved_tabs


def compare_all_tabs(tabs1: Dict[str, TabAnalysis], tabs2: Dict[str, TabAnalysis]) -> Dict[str, TabComparison]:
    """
    Compare all tabs between two workbook analyses with version resolution.
    
    Args:
        tabs1: Dictionary of tab analyses from first workbook
        tabs2: Dictionary of tab analyses from second workbook
        
    Returns:
        Dictionary mapping logical tab names to TabComparison objects
    """
    tab_comparisons = {}
    
    # Resolve tab versions to get active tabs
    resolved_tabs = resolve_tab_versions(tabs1, tabs2)
    
    for logical_name, resolution in resolved_tabs.items():
        tab_comparison = compare_single_tab(
            resolution['tab1'],
            resolution['tab2'], 
            logical_name,
            resolution
        )
        tab_comparisons[logical_name] = tab_comparison
    
    return tab_comparisons


def compare_single_tab(tab1: Optional[TabAnalysis], tab2: Optional[TabAnalysis], 
                      tab_name: str, resolution: Optional[Dict[str, Any]] = None) -> TabComparison:
    """
    Compare a single tab between two workbook versions.
    
    Args:
        tab1: Tab analysis from first workbook (None if tab doesn't exist)
        tab2: Tab analysis from second workbook (None if tab doesn't exist)
        tab_name: Name of the tab being compared (logical name)
        resolution: Version resolution info containing physical names and versions
        
    Returns:
        TabComparison object with all differences
    """
    comparison = TabComparison()
    comparison.tab_name = tab_name
    
    # Set version tracking metadata if resolution info provided
    if resolution:
        comparison.logical_name = resolution['logical_name']
        comparison.physical_name_v1 = resolution['physical_name_v1']
        comparison.physical_name_v2 = resolution['physical_name_v2']
        comparison.version_v1 = resolution['version_v1']
        comparison.version_v2 = resolution['version_v2']
    else:
        # Legacy mode - use tab_name as both logical and physical
        comparison.logical_name = tab_name
        comparison.physical_name_v1 = tab_name if tab1 else None
        comparison.physical_name_v2 = tab_name if tab2 else None
        comparison.version_v1 = 0
        comparison.version_v2 = 0
    
    # Extract system information from metadata (prioritize tab2, fallback to tab1)
    if tab2 is not None:
        comparison.source_system = tab2.metadata.source_system
        comparison.target_system = tab2.metadata.target_system
    elif tab1 is not None:
        comparison.source_system = tab1.metadata.source_system
        comparison.target_system = tab1.metadata.target_system
    
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
    
    logger.debug(f"Basic mapping comparison: +{len(added_mappings)} -{len(deleted_mappings)} ~{len(modified_mappings)}")
    
    # Perform basic comparison first
    basic_result = {
        "added": added_mappings,
        "deleted": deleted_mappings,
        "modified": modified_mappings
    }
    
    # Enhance with advanced partial mapping detection
    enhanced_result = enhance_mapping_comparison(mappings1, mappings2, basic_result)
    
    logger.debug(f"Enhanced mapping comparison: +{len(enhanced_result['added'])} -{len(enhanced_result['deleted'])} ~{len(enhanced_result['modified'])}")
    
    return enhanced_result


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


def enhance_mapping_comparison(mappings1: List[MappingRecord], mappings2: List[MappingRecord], 
                              basic_result: Dict[str, List]) -> Dict[str, List]:
    """
    Enhance basic comparison with advanced matching for partial mappings.
    
    Looks for scenarios like:
    - Source-only mappings that became complete
    - Complete mappings that became target-only
    - Field movements between source and target sides
    
    Args:
        mappings1: Mappings from first version
        mappings2: Mappings from second version
        basic_result: Result from basic comparison
        
    Returns:
        Enhanced comparison result with better change classification
    """
    DELIMITER = "||@@||"
    
    # Extract unmatched mappings for fuzzy matching
    unmatched_added = basic_result["added"].copy()
    unmatched_deleted = basic_result["deleted"].copy()
    enhanced_added = []
    enhanced_deleted = []
    enhanced_modified = basic_result["modified"].copy()
    
    # Create lookup dictionaries for fuzzy matching
    deleted_by_fields = {}
    for mapping in unmatched_deleted:
        # Create field-based keys for fuzzy matching
        source_key = f"{mapping.source_canonical}|{mapping.source_field}" if mapping.source_canonical and mapping.source_field else None
        target_key = f"{mapping.target_canonical}|{mapping.target_field}" if mapping.target_canonical and mapping.target_field else None
        
        if source_key:
            deleted_by_fields[f"SOURCE:{source_key}"] = mapping
        if target_key:
            deleted_by_fields[f"TARGET:{target_key}"] = mapping
    
    # Check added mappings for potential matches with deleted ones
    remaining_added = []
    for mapping in unmatched_added:
        matched = False
        
        # Try to find a corresponding deleted mapping
        source_key = f"{mapping.source_canonical}|{mapping.source_field}" if mapping.source_canonical and mapping.source_field else None
        target_key = f"{mapping.target_canonical}|{mapping.target_field}" if mapping.target_canonical and mapping.target_field else None
        
        # Look for completion scenarios (source-only became complete, etc.)
        potential_matches = []
        if source_key and f"SOURCE:{source_key}" in deleted_by_fields:
            potential_matches.append(("SOURCE_COMPLETED", deleted_by_fields[f"SOURCE:{source_key}"]))
        if target_key and f"TARGET:{target_key}" in deleted_by_fields:
            potential_matches.append(("TARGET_COMPLETED", deleted_by_fields[f"TARGET:{target_key}"]))
        
        if potential_matches:
            # Found a potential completion/transformation scenario
            match_type, deleted_mapping = potential_matches[0]
            
            # Create a modified mapping change instead of separate add/delete
            change = MappingChange(mapping=mapping, change_type="completed_mapping")
            change.add_field_change("completion_type", match_type, "COMPLETED")
            change.add_field_change("original_mapping", str(deleted_mapping.unique_id), str(mapping.unique_id))
            
            enhanced_modified.append(change)
            unmatched_deleted.remove(deleted_mapping)
            matched = True
        
        if not matched:
            remaining_added.append(mapping)
    
    # Classify remaining unmatched mappings with enhanced types
    for mapping in remaining_added:
        # Classify by completeness
        if mapping.unique_id.startswith("SOURCE_ONLY"):
            enhanced_added.append(mapping)  # Keep as regular added for now
        elif mapping.unique_id.startswith("TARGET_ONLY"):
            enhanced_added.append(mapping)  # Keep as regular added for now
        else:
            enhanced_added.append(mapping)
    
    # Remaining deleted mappings
    for mapping in unmatched_deleted:
        enhanced_deleted.append(mapping)
    
    return {
        "added": enhanced_added,
        "deleted": enhanced_deleted,
        "modified": enhanced_modified
    }


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