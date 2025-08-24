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
        """Generate a unique identifier for this mapping."""
        source_part = f"{self.source_canonical}|{self.source_field}".strip("|")
        target_part = f"{self.target_canonical}|{self.target_field}".strip("|")
        return f"{source_part}->{target_part}"
    
    def is_valid(self) -> bool:
        """Check if the mapping has minimum required data."""
        return bool(
            (self.source_canonical or self.source_field) and
            (self.target_canonical or self.target_field)
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
    change_type: str  # 'added', 'deleted', 'modified'
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