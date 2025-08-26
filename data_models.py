"""
Data models for Excel Source-Target Mapping Comparison Tool

This module contains the core data structures used throughout the application
for representing mapping records, tab analysis results, and comparison results.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class MappingRecord:
    """Represents a single source-to-target mapping entry from Excel."""
    
    source_canonical: str = ""
    source_field: str = ""
    target_canonical: str = ""
    target_field: str = ""
    unique_id: str = ""
    all_fields: Dict[str, Any] = field(default_factory=dict)
    row_number: Optional[int] = None
    
    def __post_init__(self):
        """Generate unique ID if not provided."""
        if not self.unique_id:
            self.unique_id = self.generate_unique_id()
    
    def generate_unique_id(self) -> str:
        """Generate a unique identifier for this mapping using tiered approach."""
        # Multi-character delimiter to avoid conflicts with actual data
        DELIMITER = "||@@||"
        
        # Clean up field values (convert None to empty string)
        source_canonical = self.source_canonical or ""
        source_field = self.source_field or ""
        target_canonical = self.target_canonical or ""
        target_field = self.target_field or ""
        
        # Tier 1: Complete mapping (both source and target have canonical + field)
        if all([source_canonical, source_field, target_canonical, target_field]):
            return f"COMPLETE{DELIMITER}{source_canonical}{DELIMITER}{source_field}{DELIMITER}{target_canonical}{DELIMITER}{target_field}"
        
        # Tier 2: Source-only complete (source has both canonical + field, target incomplete)
        elif source_canonical and source_field and not (target_canonical and target_field):
            return f"SOURCE_ONLY{DELIMITER}{source_canonical}{DELIMITER}{source_field}{DELIMITER}BLANK{DELIMITER}BLANK"
        
        # Tier 3: Target-only complete (target has both canonical + field, source incomplete)
        elif target_canonical and target_field and not (source_canonical and source_field):
            return f"TARGET_ONLY{DELIMITER}BLANK{DELIMITER}BLANK{DELIMITER}{target_canonical}{DELIMITER}{target_field}"
        
        # Tier 4: Partial mappings (at least one side has some data)
        else:
            # Use row number as additional identifier for partial mappings to ensure uniqueness
            row_identifier = getattr(self, 'row_number', 0)
            return f"PARTIAL{DELIMITER}{source_canonical}{DELIMITER}{source_field}{DELIMITER}{target_canonical}{DELIMITER}{target_field}{DELIMITER}ROW_{row_identifier}"
    
    def is_valid(self) -> bool:
        """
        Check if the mapping has minimum required data.
        Now supports partial mappings where only one side (Source OR Target) 
        has complete canonical + field information.
        """
        # Complete source side (both canonical and field)
        source_complete = bool(self.source_canonical and self.source_field)
        
        # Complete target side (both canonical and field)
        target_complete = bool(self.target_canonical and self.target_field)
        
        # Valid if at least one side is complete OR both sides have some data
        return bool(
            source_complete or 
            target_complete or 
            ((self.source_canonical or self.source_field) and 
             (self.target_canonical or self.target_field))
        )


@dataclass
class TabMetadata:
    """Metadata extracted from a worksheet tab."""
    
    tab_name: str = ""
    source_system: str = ""
    target_system: str = ""
    source_system_column: int = 1  # Column A by default
    target_system_column: int = 14  # Column N by default
    max_row: int = 0
    max_column: int = 0


@dataclass
class ColumnMapping:
    """Maps column types to their positions in the worksheet."""
    
    source_columns: Dict[str, int] = field(default_factory=dict)
    target_columns: Dict[str, int] = field(default_factory=dict)
    all_headers: Dict[int, str] = field(default_factory=dict)
    
    def get_source_column(self, column_type: str) -> Optional[int]:
        """Get the column number for a source field type."""
        return self.source_columns.get(column_type.lower())
    
    def get_target_column(self, column_type: str) -> Optional[int]:
        """Get the column number for a target field type."""
        return self.target_columns.get(column_type.lower())


@dataclass
class TabAnalysis:
    """Complete analysis result for a single worksheet tab."""
    
    metadata: TabMetadata = field(default_factory=TabMetadata)
    column_mapping: ColumnMapping = field(default_factory=ColumnMapping)
    mappings: List[MappingRecord] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    @property
    def tab_name(self) -> str:
        """Convenience property to get tab name."""
        return self.metadata.tab_name
    
    @property
    def mapping_count(self) -> int:
        """Number of valid mappings in this tab."""
        return len([m for m in self.mappings if m.is_valid()])
    
    def add_error(self, error_message: str):
        """Add an error message to this analysis."""
        self.errors.append(error_message)


@dataclass
class MappingChange:
    """Represents a change to a mapping between versions."""
    
    mapping: MappingRecord
    change_type: str  # 'added', 'deleted', 'modified', 'added_source_only', 'added_target_only', 'completed_mapping', 'split_mapping', 'moved_mapping'
    field_changes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def add_field_change(self, field_name: str, old_value: Any, new_value: Any):
        """Record a change to a specific field."""
        self.field_changes[field_name] = {
            'old': old_value,
            'new': new_value
        }


@dataclass
class TabComparison:
    """Comparison result for a single tab between two versions."""
    
    tab_name: str = ""
    status: str = "unchanged"  # 'added', 'deleted', 'modified', 'unchanged'
    added_mappings: List[MappingRecord] = field(default_factory=list)
    deleted_mappings: List[MappingRecord] = field(default_factory=list)
    modified_mappings: List[MappingChange] = field(default_factory=list)
    metadata_changes: Dict[str, Any] = field(default_factory=dict)
    source_system: Optional[str] = None
    target_system: Optional[str] = None
    
    @property
    def has_changes(self) -> bool:
        """Check if this tab has any changes."""
        return (
            len(self.added_mappings) > 0 or
            len(self.deleted_mappings) > 0 or
            len(self.modified_mappings) > 0 or
            len(self.metadata_changes) > 0
        )
    
    @property
    def change_summary(self) -> Dict[str, int]:
        """Get summary of changes."""
        return {
            'added': len(self.added_mappings),
            'deleted': len(self.deleted_mappings),
            'modified': len(self.modified_mappings)
        }


@dataclass
class ComparisonSummary:
    """High-level summary of the comparison between two workbooks."""
    
    total_tabs_v1: int = 0
    total_tabs_v2: int = 0
    tabs_added: int = 0
    tabs_deleted: int = 0
    tabs_modified: int = 0
    tabs_unchanged: int = 0
    total_mappings_v1: int = 0
    total_mappings_v2: int = 0
    total_mappings_added: int = 0
    total_mappings_deleted: int = 0
    total_mappings_modified: int = 0
    comparison_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ComparisonResult:
    """Complete comparison result between two Excel workbooks."""
    
    file1_path: str = ""
    file2_path: str = ""
    summary: ComparisonSummary = field(default_factory=ComparisonSummary)
    tab_comparisons: Dict[str, TabComparison] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    
    def add_error(self, error_message: str):
        """Add an error message to the comparison result."""
        self.errors.append(error_message)
    
    def get_tabs_by_status(self, status: str) -> List[TabComparison]:
        """Get all tabs with a specific status."""
        return [tc for tc in self.tab_comparisons.values() if tc.status == status]
    
    @property
    def has_errors(self) -> bool:
        """Check if the comparison had any errors."""
        return len(self.errors) > 0
    
    @property
    def changed_tabs(self) -> List[TabComparison]:
        """Get all tabs that have changes."""
        return [tc for tc in self.tab_comparisons.values() if tc.has_changes]