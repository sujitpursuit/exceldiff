"""
JSON Report Generator Module

This module generates comprehensive JSON reports from Excel comparison results.
It creates structured JSON output that mirrors the HTML report data for API consumption,
data processing, and integration with other systems.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import os

from data_models import ComparisonResult, TabComparison, MappingChange

logger = logging.getLogger(__name__)


class JSONReportGenerator:
    """
    Generates comprehensive JSON reports from Excel comparison results.
    """
    
    def __init__(self):
        pass
        
    def generate_report(self, comparison_result: ComparisonResult, 
                       output_path: str, 
                       report_title: Optional[str] = None,
                       file1_modified_time: Optional[str] = None,
                       file2_modified_time: Optional[str] = None) -> bool:
        """
        Generate a complete JSON report from comparison results.
        
        Args:
            comparison_result: The comparison results to report on
            output_path: Path where the JSON report will be saved
            report_title: Optional custom title for the report
            file1_modified_time: Optional modified time for original file (ISO format)
            file2_modified_time: Optional modified time for modified file (ISO format)
            
        Returns:
            True if report generated successfully, False otherwise
        """
        try:
            logger.info(f"Generating JSON report: {output_path}")
            
            # Ensure output directory exists
            output_dir = Path(output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate the complete JSON content
            json_data = self._build_json_report(
                comparison_result, 
                report_title,
                file1_modified_time,
                file2_modified_time
            )
            
            # Write to file with proper formatting
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False, default=str)
                
            logger.info(f"JSON report generated successfully: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate JSON report: {e}")
            return False
    
    def _build_json_report(self, result: ComparisonResult, 
                          title: Optional[str] = None,
                          file1_modified_time: Optional[str] = None,
                          file2_modified_time: Optional[str] = None) -> Dict[str, Any]:
        """
        Build the complete JSON report structure.
        
        Args:
            result: Comparison results
            title: Optional custom title
            file1_modified_time: Optional modified time for original file
            file2_modified_time: Optional modified time for modified file
            
        Returns:
            Complete JSON data structure
        """
        # Extract file names for display
        file1_name = Path(result.file1_path).name if result.file1_path else "File 1"
        file2_name = Path(result.file2_path).name if result.file2_path else "File 2"
        
        # Generate timestamp
        timestamp = datetime.now().strftime("%B %d, %Y - %I:%M %p")
        
        # Use custom title or generate default
        if not title:
            title = "Excel Source-Target Mapping Comparison Report"
        
        # Get file modified times
        file1_last_modified = self._get_file_modified_time(
            result.file1_path, file1_modified_time
        )
        file2_last_modified = self._get_file_modified_time(
            result.file2_path, file2_modified_time
        )
        
        # Build JSON structure
        json_data = {
            "report_metadata": self._build_report_metadata(title, timestamp),
            "file_information": self._build_file_information(
                result, file1_name, file2_name, 
                file1_last_modified, file2_last_modified
            ),
            "executive_summary": self._build_executive_summary(result),
            "technical_details": self._build_technical_details(),
            "detailed_changes": self._build_detailed_changes(result)
        }
        
        return json_data
    
    def _get_file_modified_time(self, file_path: str, provided_time: Optional[str] = None) -> str:
        """
        Get file modified time from provided parameter or file system.
        
        Args:
            file_path: Path to the file
            provided_time: Optional provided modified time
            
        Returns:
            ISO formatted datetime string
        """
        if provided_time:
            return provided_time
            
        if file_path and os.path.exists(file_path):
            try:
                mtime = os.path.getmtime(file_path)
                return datetime.fromtimestamp(mtime).isoformat() + 'Z'
            except Exception as e:
                logger.warning(f"Could not get modified time for {file_path}: {e}")
                
        return datetime.now().isoformat() + 'Z'
    
    def _build_report_metadata(self, title: str, timestamp: str) -> Dict[str, Any]:
        """Build report metadata section."""
        return {
            "title": title,
            "subtitle": "Detailed analysis of changes between workbook versions",
            "generated_by": "Excel Comparison Tool v2.0",
            "generation_timestamp": timestamp,
            "processing_time": "< 1 second"
        }
    
    def _build_file_information(self, result: ComparisonResult, 
                              file1_name: str, file2_name: str,
                              file1_modified: str, file2_modified: str) -> Dict[str, Any]:
        """Build file information section."""
        return {
            "original_file": {
                "name": file1_name,
                "path": result.file1_path or "",
                "last_modified": file1_modified
            },
            "modified_file": {
                "name": file2_name,
                "path": result.file2_path or "",
                "last_modified": file2_modified
            }
        }
    
    def _build_executive_summary(self, result: ComparisonResult) -> Dict[str, Any]:
        """Build executive summary section."""
        summary = result.summary
        
        # Calculate total changes
        total_changes = (summary.tabs_added + summary.tabs_deleted + 
                        summary.tabs_modified + summary.total_mappings_added +
                        summary.total_mappings_deleted + summary.total_mappings_modified)
        
        return {
            "statistics": {
                "total_changes": total_changes,
                "tabs": {
                    "original_count": summary.total_tabs_v1,
                    "modified_count": summary.total_tabs_v2,
                    "added": summary.tabs_added,
                    "deleted": summary.tabs_deleted,
                    "modified": summary.tabs_modified,
                    "unchanged": summary.tabs_unchanged
                },
                "mappings": {
                    "original_count": summary.total_mappings_v1,
                    "modified_count": summary.total_mappings_v2,
                    "added": summary.total_mappings_added,
                    "deleted": summary.total_mappings_deleted,
                    "modified": summary.total_mappings_modified
                }
            }
        }
    
    def _build_technical_details(self) -> Dict[str, Any]:
        """Build technical details section."""
        return {
            "comparison_method": "Content-based unique ID matching",
            "position_independence": "Enabled - handles row reordering",
            "hidden_tabs": "Skipped by default configuration"
        }
    
    def _build_detailed_changes(self, result: ComparisonResult) -> Dict[str, Any]:
        """Build detailed changes section."""
        detailed_changes = {
            "changed_tabs": [],
            "unchanged_tabs": []
        }
        
        # Process changed tabs
        changed_tabs = [(name, comp) for name, comp in result.tab_comparisons.items() 
                       if comp.has_changes]
        
        for tab_name, tab_comparison in changed_tabs:
            detailed_changes["changed_tabs"].append(
                self._build_tab_change_data(tab_name, tab_comparison)
            )
        
        # Process unchanged tabs
        unchanged_tabs = [name for name, comp in result.tab_comparisons.items() 
                         if not comp.has_changes]
        
        for tab_name in unchanged_tabs:
            detailed_changes["unchanged_tabs"].append({
                "tab_name": tab_name,
                "status": "unchanged"
            })
        
        return detailed_changes
    
    def _build_tab_change_data(self, tab_name: str, tab_comparison: TabComparison) -> Dict[str, Any]:
        """Build data for a single changed tab."""
        # Get change badge info
        badge_info = self._get_change_badge_info(tab_comparison)
        
        tab_data = {
            "tab_name": tab_name,
            "change_type": self._determine_change_type(tab_comparison),
            "change_badge": badge_info,
            "change_summary": {
                "added": tab_comparison.change_summary['added'],
                "deleted": tab_comparison.change_summary['deleted'],
                "modified": tab_comparison.change_summary['modified'],
                "description": self._get_change_summary_text(tab_comparison)
            },
            "mappings": {
                "added_mappings": self._build_added_mappings_data(tab_comparison.added_mappings),
                "deleted_mappings": self._build_deleted_mappings_data(tab_comparison.deleted_mappings),
                "modified_mappings": self._build_modified_mappings_data(tab_comparison.modified_mappings)
            }
        }
        
        return tab_data
    
    def _determine_change_type(self, tab_comparison: TabComparison) -> str:
        """Determine the change type for a tab."""
        changes = tab_comparison.change_summary
        added = changes['added']
        deleted = changes['deleted'] 
        modified = changes['modified']
        
        if added > 0 and deleted == 0 and modified == 0:
            return "additions_only"
        elif added == 0 and deleted > 0 and modified == 0:
            return "deletions_only"
        elif added == 0 and deleted == 0 and modified > 0:
            return "modifications_only"
        else:
            return "mixed"
    
    def _get_change_badge_info(self, tab_comparison: TabComparison) -> Dict[str, str]:
        """Get badge information for a tab comparison."""
        changes = tab_comparison.change_summary
        added = changes['added']
        deleted = changes['deleted'] 
        modified = changes['modified']
        
        # Determine badge style based on change types
        if added > 0 and deleted == 0 and modified == 0:
            return {'class': 'badge-added', 'text': f'+{added} Added'}
        elif added == 0 and deleted > 0 and modified == 0:
            return {'class': 'badge-deleted', 'text': f'-{deleted} Deleted'}
        elif added == 0 and deleted == 0 and modified > 0:
            return {'class': 'badge-modified', 'text': f'~{modified} Modified'}
        else:
            # Mixed changes
            parts = []
            if added > 0:
                parts.append(f'+{added}')
            if modified > 0:
                parts.append(f'~{modified}')
            if deleted > 0:
                parts.append(f'-{deleted}')
            
            return {
                'class': 'badge-mixed', 
                'text': f"{' '.join(parts)} Mixed"
            }
    
    def _get_change_summary_text(self, tab_comparison: TabComparison) -> str:
        """Generate human-readable change summary text."""
        changes = tab_comparison.change_summary
        added = changes['added']
        deleted = changes['deleted']
        modified = changes['modified']
        
        parts = []
        if added > 0:
            parts.append(f"{added} mapping{'s' if added != 1 else ''} added")
        if deleted > 0:
            parts.append(f"{deleted} mapping{'s' if deleted != 1 else ''} deleted") 
        if modified > 0:
            parts.append(f"{modified} mapping{'s' if modified != 1 else ''} modified")
        
        if len(parts) == 1:
            return parts[0].capitalize()
        elif len(parts) == 2:
            return f"{parts[0].capitalize()} and {parts[1]}"
        else:
            return f"{', '.join(parts[:-1]).capitalize()}, and {parts[-1]}"
    
    def _build_added_mappings_data(self, added_mappings: List) -> List[Dict[str, Any]]:
        """Build data for added mappings."""
        if not added_mappings:
            return []
        
        mappings_data = []
        for i, mapping in enumerate(added_mappings):
            # Separate key fields from other fields
            key_fields, other_fields = self._separate_key_and_other_fields(mapping)
            
            mapping_data = {
                "status": "Added",
                "row_number": i + 1,  # This could be enhanced with actual row tracking
                "mapping_fields": key_fields,
                "other_fields": other_fields
            }
            mappings_data.append(mapping_data)
        
        return mappings_data
    
    def _build_deleted_mappings_data(self, deleted_mappings: List) -> List[Dict[str, Any]]:
        """Build data for deleted mappings."""
        if not deleted_mappings:
            return []
        
        mappings_data = []
        for i, mapping in enumerate(deleted_mappings):
            # Separate key fields from other fields
            key_fields, other_fields = self._separate_key_and_other_fields(mapping)
            
            mapping_data = {
                "status": "Deleted",
                "original_row_number": i + 1,  # This could be enhanced with actual row tracking
                "mapping_fields": key_fields,
                "other_fields": other_fields
            }
            mappings_data.append(mapping_data)
        
        return mappings_data
    
    def _build_modified_mappings_data(self, modified_mappings: List[MappingChange]) -> List[Dict[str, Any]]:
        """Build data for modified mappings."""
        if not modified_mappings:
            return []
        
        mappings_data = []
        for i, mapping_change in enumerate(modified_mappings):
            mapping = mapping_change.mapping
            
            # Get key mapping fields (Source/Target System and Field)
            key_fields, _ = self._separate_key_and_other_fields(mapping)
            
            # Process field changes (skip internal technical fields)
            field_changes = {}
            for field_name, change_info in mapping_change.field_changes.items():
                # Skip internal technical fields
                if field_name == 'original_mapping':
                    continue
                    
                field_changes[field_name] = {
                    "old_value": change_info.get('old', ''),
                    "new_value": change_info.get('new', '')
                }
            
            mapping_data = {
                "status": "Modified",
                "row_number": i + 1,  # This could be enhanced with actual row tracking
                "mapping_fields": key_fields,
                "field_changes": field_changes
            }
            mappings_data.append(mapping_data)
        
        return mappings_data
    
    def _extract_mapping_fields(self, mapping) -> Dict[str, Any]:
        """Extract all fields from a mapping object into a dictionary with original column names."""
        fields = {}
        
        # Extract all additional fields from all_fields first (this contains the complete data)
        if hasattr(mapping, 'all_fields') and mapping.all_fields:
            for key, value in mapping.all_fields.items():
                # Convert internal field names to display names
                display_key = self._convert_field_name_to_display(key)
                if value is not None and str(value).strip():
                    fields[display_key] = value
        
        # Always add basic fields as fallback if they're not already present or are empty
        if hasattr(mapping, 'source_canonical') and mapping.source_canonical:
            if not any(k in fields for k in ["Source System", "Source Canonical Name"]):
                fields["Source System"] = mapping.source_canonical
        if hasattr(mapping, 'source_field') and mapping.source_field:
            if "Source Field" not in fields:
                fields["Source Field"] = mapping.source_field
        if hasattr(mapping, 'target_canonical') and mapping.target_canonical:
            if not any(k in fields for k in ["Target System", "Target Canonical Name", "Target Entity"]):
                fields["Target System"] = mapping.target_canonical
        if hasattr(mapping, 'target_field') and mapping.target_field:
            if "Target Field" not in fields:
                fields["Target Field"] = mapping.target_field
        
        return fields
    
    def _convert_field_name_to_display(self, field_name: str) -> str:
        """Convert internal field names to display-friendly names."""
        # This preserves the original column names from Excel
        # You can add specific mappings here if needed
        return field_name.replace('_', ' ').title()
    
    def _separate_key_and_other_fields(self, mapping) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Separate key mapping fields from other fields."""
        key_fields = {}
        other_fields = {}
        
        # Get all fields
        all_fields = self._extract_mapping_fields(mapping)
        
        # Define key field names that we want to separate (expanded to include all variations)
        key_field_names = {
            'Source System', 'Source Field', 'Target System', 'Target Field',
            'Source Canonical Name', 'Target Entity', 'Target Canonical Name',
            'Source Entity', 'Target Entity Name', 'Source System Name', 'Target System Name'
        }
        
        # Separate fields
        for field_name, field_value in all_fields.items():
            if field_name in key_field_names:
                key_fields[field_name] = field_value
            else:
                other_fields[field_name] = field_value
        
        # Enhanced fallback: ensure we have complete key mapping information
        # Add missing Source System/Canonical Name/Entity
        if hasattr(mapping, 'source_canonical') and mapping.source_canonical:
            has_source_system = any(k in key_fields for k in ['Source Canonical Name', 'Source System', 'Source Entity'])
            if not has_source_system:
                key_fields["Source System"] = mapping.source_canonical
        
        # Add missing Source Field
        if hasattr(mapping, 'source_field') and mapping.source_field:
            if 'Source Field' not in key_fields:
                key_fields["Source Field"] = mapping.source_field
        
        # Add missing Target System/Canonical Name/Entity
        if hasattr(mapping, 'target_canonical') and mapping.target_canonical:
            has_target_system = any(k in key_fields for k in ['Target Canonical Name', 'Target System', 'Target Entity', 'Target Entity Name'])
            if not has_target_system:
                key_fields["Target System"] = mapping.target_canonical
        
        # Add missing Target Field  
        if hasattr(mapping, 'target_field') and mapping.target_field:
            if 'Target Field' not in key_fields:
                key_fields["Target Field"] = mapping.target_field
        
        return key_fields, other_fields


# Convenience function for easy JSON report generation
def generate_json_report(comparison_result: ComparisonResult, 
                        output_path: str,
                        title: Optional[str] = None,
                        file1_modified_time: Optional[str] = None,
                        file2_modified_time: Optional[str] = None) -> bool:
    """
    Convenience function to generate a JSON report.
    
    Args:
        comparison_result: The comparison results to report on
        output_path: Path where the JSON report will be saved
        title: Optional custom title for the report
        file1_modified_time: Optional modified time for original file (ISO format)
        file2_modified_time: Optional modified time for modified file (ISO format)
        
    Returns:
        True if report generated successfully, False otherwise
    """
    generator = JSONReportGenerator()
    return generator.generate_report(
        comparison_result, 
        output_path, 
        title,
        file1_modified_time,
        file2_modified_time
    )