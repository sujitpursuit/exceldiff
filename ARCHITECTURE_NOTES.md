# Architecture & Technical Decision Log

## 🏗️ System Architecture Overview

### High-Level Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                    Excel Comparison Tool                        │
├─────────────────────────────────────────────────────────────────┤
│  Phase 1: Excel Analysis Engine ✅                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   File 1    │  │   File 2    │  │ Config &    │              │
│  │ (XLSX/XLS)  │  │ (XLSX/XLS)  │  │ Validation  │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│         │                 │                │                    │
│         ▼                 ▼                ▼                    │
│  ┌─────────────────────────────────────────────────────┐        │
│  │         Excel Analyzer Engine                       │        │
│  │  • Tab Validation    • System Name Extraction      │        │
│  │  • Column Detection  • Mapping Data Parsing        │        │
│  │  • Hidden Tab Handle • Error Recovery              │        │
│  └─────────────────────────────────────────────────────┘        │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐        │
│  │            Structured Data Models                   │        │
│  │  • TabAnalysis       • MappingRecord               │        │
│  │  • TabMetadata       • ColumnMapping               │        │
│  └─────────────────────────────────────────────────────┘        │
├─────────────────────────────────────────────────────────────────┤
│  Phase 2: Comparison Engine ⏳ (Next)                           │
│  ┌─────────────────────────────────────────────────────┐        │
│  │              Comparison Logic                       │        │
│  │  • Tab Comparison    • Change Detection            │        │
│  │  • Mapping Diff      • Summary Generation          │        │
│  └─────────────────────────────────────────────────────┘        │
├─────────────────────────────────────────────────────────────────┤
│  Phase 3: Report Generation ⏳                                  │
│  ┌─────────────────────────────────────────────────────┐        │
│  │              HTML Report Engine                     │        │
│  │  • Template System   • CSS Styling                 │        │
│  │  • Change Highlight  • Responsive Design           │        │
│  └─────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🧠 Key Technical Decisions

### 1. Excel Structure Understanding
**Decision:** Standardize on specific Excel structure pattern
**Rationale:** Real-world analysis of STTM.xlsx revealed consistent pattern
**Implementation:**
- Rows 1-8: Header/metadata information
- Row 9: System names (Source in A9, Target in next filled cell)
- Row 10: Column headers defining field types
- Row 11+: Actual mapping data

**Why this matters:** Provides reliable structure for parsing while remaining flexible for variations.

### 2. Position Independence Strategy
**Decision:** Use content-based unique IDs instead of row positions
**Rationale:** Users may add/remove rows, making position-based comparison unreliable
**Implementation:**
```python
unique_id = f"{source_canonical}|{source_field}->{target_canonical}|{target_field}"
```
**Why this matters:** Ensures accurate comparison even when data is rearranged.

### 3. Dynamic Column Detection
**Decision:** Pattern-matching approach for source vs target sections
**Rationale:** Column arrangements vary significantly between Excel files
**Implementation:**
- Analyze row 10 headers for duplicate column types
- First occurrence → Source section
- Second occurrence → Target section
- Fallback to boundary-based detection using target system column

**Why this matters:** Handles real-world Excel variations automatically.

### 4. Multi-Level Validation Pipeline
**Decision:** Implement cascading validation approach
**Rationale:** Need to filter various types of invalid content reliably
**Implementation:**
1. **Structure Validation:** Check rows/columns, header presence
2. **Content Validation:** Verify system names, meaningful headers
3. **Data Validation:** Ensure sufficient mapping data exists
4. **Format Validation:** Detect JSON, field definitions, etc.

**Why this matters:** Ensures only legitimate mapping tabs are processed.

### 5. Hidden Tab Configuration System
**Decision:** Implement runtime-configurable hidden tab processing
**Rationale:** Different use cases need different approaches to hidden data
**Implementation:**
```python
SKIP_HIDDEN_TABS = True            # Default behavior
PROCESS_HIDDEN_TABS = False        # Override flag
```
**Why this matters:** Provides flexibility for different organizational policies.

---

## 📊 Data Flow Architecture

### Excel Processing Flow
```
Excel File → Workbook Load → Tab Iteration → Tab Validation → Analysis → Results
     │              │              │              │             │          │
     │              │              │              │             │          ▼
     │              │              │              │             │    TabAnalysis
     │              │              │              │             │    Objects
     │              │              │              │             ▼
     │              │              │              │       Column Detection
     │              │              │              │       & Mapping Parsing
     │              │              │              ▼
     │              │              │         Valid Structure?
     │              │              │         • Header Check
     │              │              │         • System Names
     │              │              │         • Data Content
     │              │              ▼
     │              │         Hidden Tab?
     │              │         • Check sheet_state
     │              │         • Apply config rules
     │              ▼
     │         Load with openpyxl
     │         • data_only=True
     │         • Error handling
     ▼
   File Exists?
   • Path validation
   • Extension check
```

### Data Structure Hierarchy
```
ComparisonResult
├── file1_path: str
├── file2_path: str  
├── summary: ComparisonSummary
├── tab_comparisons: Dict[str, TabComparison]
└── errors: List[str]

TabComparison
├── tab_name: str
├── status: str ('added'|'deleted'|'modified'|'unchanged')
├── added_mappings: List[MappingRecord]
├── deleted_mappings: List[MappingRecord]
├── modified_mappings: List[MappingChange]
└── metadata_changes: Dict[str, Any]

TabAnalysis
├── metadata: TabMetadata
├── column_mapping: ColumnMapping  
├── mappings: List[MappingRecord]
└── errors: List[str]

MappingRecord
├── source_canonical: str
├── source_field: str
├── target_canonical: str
├── target_field: str
├── unique_id: str
├── all_fields: Dict[str, Any]
└── row_number: Optional[int]
```

---

## 🔧 Implementation Patterns

### 1. Error Handling Strategy
**Pattern:** Graceful degradation with detailed logging
```python
try:
    # Main processing logic
    analysis = analyze_worksheet(worksheet)
except Exception as e:
    # Log error with context
    logger.error(f"Error processing {worksheet.title}: {e}")
    # Create error analysis object
    error_analysis = TabAnalysis()
    error_analysis.add_error(f"Processing failed: {e}")
    return error_analysis
```
**Benefits:** System continues processing other tabs even when one fails.

### 2. Configuration Management
**Pattern:** Centralized config with runtime flexibility
```python
# config.py - Default values
SKIP_HIDDEN_TABS = True

# Runtime override capability
from config import SKIP_HIDDEN_TABS, PROCESS_HIDDEN_TABS
if SKIP_HIDDEN_TABS and not PROCESS_HIDDEN_TABS:
    # Apply skip logic
```
**Benefits:** Easy to modify behavior without code changes.

### 3. Validation Chain Pattern
**Pattern:** Sequential validation with early exit
```python
def is_valid_mapping_tab(worksheet):
    if not _has_sufficient_rows(worksheet):
        return False
    if not _has_valid_headers(worksheet):
        return False  
    if not _has_system_names(worksheet):
        return False
    if not _has_meaningful_data(worksheet):
        return False
    return True
```
**Benefits:** Fast rejection of invalid tabs, clear validation logic.

### 4. Factory Pattern for Data Creation
**Pattern:** Centralized object creation with validation
```python
def create_mapping_record(worksheet, row_num, column_mapping):
    mapping = MappingRecord()
    # Extract and validate data
    mapping.source_canonical = _extract_field(worksheet, row_num, 'source_canonical')
    # Auto-generate unique ID
    mapping.unique_id = mapping.generate_unique_id()
    return mapping if mapping.is_valid() else None
```
**Benefits:** Consistent object creation, automatic validation.

---

## 🎯 Design Principles Applied

### 1. Single Responsibility Principle
- Each module has a clear, focused purpose
- `excel_analyzer.py` - Excel processing only
- `data_models.py` - Data structures only
- `config.py` - Configuration only

### 2. Open/Closed Principle
- Easy to add new column types via `COLUMN_NAME_MAPPINGS`
- New validation rules can be added without changing core logic
- Configuration system allows behavior changes without code modification

### 3. Dependency Inversion
- Core logic depends on interfaces (data models) not implementations
- Configuration drives behavior rather than hard-coded values
- Logging abstraction allows different logging implementations

### 4. Don't Repeat Yourself (DRY)
- Common validation logic centralized
- Reusable utility functions
- Configuration constants eliminate magic numbers

---

## 🚀 Performance Considerations

### 1. Memory Management
**Strategy:** Process worksheets one at a time
**Implementation:** Load workbook, process each sheet, release resources
**Why:** Prevents memory issues with large Excel files

### 2. Early Termination
**Strategy:** Fail fast on invalid tabs
**Implementation:** Multi-level validation with early exit
**Why:** Saves processing time on obviously invalid content

### 3. Efficient Column Detection
**Strategy:** Cache column mappings once detected
**Implementation:** Store column positions in ColumnMapping object
**Why:** Avoids re-parsing headers for each data row

### 4. Lazy Loading Approach
**Strategy:** Only parse data when validation passes
**Implementation:** Validate structure before extracting mappings
**Why:** Avoids wasted processing on tabs that will be skipped

---

## 🔮 Future Architecture Considerations

### Phase 2 Design Decisions Needed
1. **Comparison Algorithm:** How to efficiently match mappings between files
2. **Change Detection Granularity:** Field-level vs record-level change tracking
3. **Memory vs Speed Tradeoff:** Load both files simultaneously or sequentially
4. **Diff Algorithm:** Custom implementation vs existing library

### Phase 3 Design Decisions Needed
1. **Template Engine:** Custom HTML generation vs template library
2. **Styling Approach:** Inline CSS vs separate stylesheet
3. **Interactive Features:** Static HTML vs JavaScript enhancements
4. **Large Report Handling:** Pagination vs full single-page report

### Scalability Considerations
1. **File Size Limits:** How to handle very large Excel files (1000+ tabs)
2. **Comparison Complexity:** Performance with thousands of mappings
3. **Report Size:** Managing large HTML reports efficiently
4. **Memory Usage:** Preventing memory issues with complex comparisons

---

## 📋 Technical Debt & Future Improvements

### Current Technical Debt
1. **Unicode Handling:** Arrow characters replaced with ASCII (→ became ->)
2. **Error Message Granularity:** Could provide more specific validation failure reasons
3. **Configuration Validation:** No validation of config parameter combinations

### Future Improvements
1. **Plugin Architecture:** Allow custom validation rules
2. **Multiple File Format Support:** Support .xls files (currently .xlsx focused)
3. **Parallel Processing:** Multi-threaded worksheet analysis
4. **Caching System:** Cache analysis results for repeated comparisons
5. **Configuration UI:** GUI for setting processing options

---

**Architecture Status: 🏗️ Phase 1 Foundation Complete - Ready for Phase 2 Development**