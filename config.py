"""
Configuration constants for Excel Source-Target Mapping Comparison Tool

This module contains all configuration constants, default values, and 
mapping definitions used throughout the application.
"""

# Excel Structure Constants
METADATA_END_ROW = 8
SYSTEM_NAMES_ROW = 9
HEADERS_ROW = 10
DATA_START_ROW = 11

SOURCE_SYSTEM_COLUMN = 1  # Column A
DEFAULT_TARGET_SYSTEM_COLUMN = 14  # Column N

# Column Name Variations
# These are the various ways column names might appear in different Excel files
COLUMN_NAME_MAPPINGS = {
    'canonical_name': ['canonical name', 'entity', 'table', 'entity field'],
    'field': ['field', 'field name', 'column', 'column name'],
    'description': ['description', 'desc', 'comments', 'comment'],
    'type': ['type', 'data type', 'datatype'],
    'length_min': ['length(min)', 'length min', 'min length', 'minimum length'],
    'length_max': ['length(max)', 'length max', 'max length', 'maximum length', 'length'],
    'format': ['format', 'data format'],
    'enum_values': ['enum values', 'enumeration', 'enum', 'values', 'possible values'],
    'mandatory': ['mandatory', 'required', 'optional'],
    'notes': ['notes', 'note', 'remarks', 'remark'],
    'business_transformation': ['business transformation', 'transformation', 'mapping rule', 'rule'],
    'sample_data': ['sample data', 'sample', 'sample data value', 'example'],
    'primary_key': ['primary key', 'pk', 'key']
}

# Standard column order for comparison purposes
STANDARD_COLUMN_ORDER = [
    'canonical_name',
    'field', 
    'description',
    'type',
    'length_min',
    'length_max',
    'format',
    'enum_values',
    'mandatory',
    'notes',
    'business_transformation',
    'sample_data',
    'primary_key'
]

# HTML Report Configuration
HTML_REPORT_CONFIG = {
    'title': 'Source-Target Mapping Comparison Report',
    'max_cell_display_length': 100,  # Truncate long cell values in display
    'show_empty_sections': False,    # Hide sections with no changes
    'include_timestamp': True,
    'responsive_design': True,
    'printable_styles': True
}

# Colors for HTML report (CSS classes)
REPORT_COLORS = {
    'added': '#d4edda',      # Light green
    'deleted': '#f8d7da',    # Light red  
    'modified': '#fff3cd',   # Light yellow
    'unchanged': '#f8f9fa',  # Light gray
    'header': '#e9ecef',     # Medium gray
    'border': '#dee2e6'      # Border gray
}

# Error handling constants
MAX_ERRORS_PER_TAB = 10
CONTINUE_ON_ERROR = True

# Performance settings
MAX_ROWS_TO_PROCESS = 10000  # Prevent memory issues with very large files
MAX_COLUMNS_TO_SCAN = 50     # Limit column scanning range

# Validation rules
MIN_MAPPING_FIELDS = 2  # Minimum fields required for a valid mapping
REQUIRED_FIELDS = ['canonical_name', 'field']  # At least one of these must be present

# File handling
SUPPORTED_EXTENSIONS = ['.xlsx', '.xls']
DEFAULT_OUTPUT_FILENAME = 'comparison_report.html'

# Logging configuration
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = 'INFO'

# Comparison settings
CASE_SENSITIVE_COMPARISON = False  # Whether field comparisons are case sensitive
TRIM_WHITESPACE = True             # Whether to trim whitespace from values
IGNORE_EMPTY_CELLS = True          # Whether empty cells should be ignored in comparisons

# Tab processing settings
SKIP_HIDDEN_TABS = True            # Whether to skip hidden worksheets
PROCESS_HIDDEN_TABS = False        # Set to True to process hidden tabs (overrides SKIP_HIDDEN_TABS)

# Tab name versioning settings
EXCEL_TAB_NAME_MAX_LENGTH = 31     # Maximum length for Excel tab names (as per Excel documentation)
ENABLE_TRUNCATED_TAB_MATCHING = True  # Whether to enable fuzzy matching for truncated tab names

# System name detection rules
SYSTEM_NAME_MAX_SEARCH_COLUMNS = 20  # How many columns to search for target system name
SYSTEM_NAME_MIN_LENGTH = 2           # Minimum length for a valid system name

# Column detection rules  
MIN_COLUMN_HEADER_LENGTH = 2         # Minimum length for a valid column header
MAX_EMPTY_COLUMNS_BETWEEN_SECTIONS = 3  # Max empty columns between source and target sections

# =============================================================================
# REPORT GENERATION CONFIGURATION
# =============================================================================

# Report directory configuration
REPORTS_BASE_DIR = "reports"           # Base directory for all reports
DIFF_REPORTS_DIR = "diff_reports"      # Subdirectory for comparison reports (configurable)
TEST_REPORTS_DIR = "test_reports"      # Subdirectory for test reports
SAMPLE_REPORTS_DIR = "sample_reports"  # Subdirectory for sample/demo reports

# Report file naming
REPORT_FILENAME_TEMPLATE = "comparison_{file1}_vs_{file2}_{timestamp}.html"
REPORT_TITLE_TEMPLATE = "Comparison Report: {file1} vs {file2}"
REPORT_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"  # Format for timestamps in filenames

# Report generation options
AUTO_CREATE_REPORT_DIRS = True         # Automatically create report directories if they don't exist
INCLUDE_TIMESTAMP_IN_FILENAME = True   # Whether to include timestamp in report filenames
OVERWRITE_EXISTING_REPORTS = False     # Whether to overwrite reports with same name

# Report content configuration
INCLUDE_TECHNICAL_DETAILS = False      # Whether to include technical details section (already removed)
INCLUDE_PERFORMANCE_METRICS = True     # Whether to include performance timing in reports
INCLUDE_FILE_METADATA = True           # Whether to include file size, dates, etc. in reports