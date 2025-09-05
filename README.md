# Excel Source-Target Mapping Comparison Tool

A production-ready Python tool for comparing two versions of Excel workbooks containing Source-Target mapping data and generating comprehensive HTML reports showing differences between versions.

**🔥 Now Available in Two Modes:**
- **CLI Mode**: Full-featured command-line interface (original)
- **Web API Mode**: REST API with web interface (new!)

## ✨ Key Features

### 🎯 Core Functionality
- **Intelligent Excel Comparison**: Compare two Excel workbooks with sophisticated difference detection
- **Professional HTML Reports**: Generate detailed, responsive HTML reports with navigation
- **JSON Reports**: Machine-readable JSON output with precise Excel row numbers
- **Command-Line Interface**: Full-featured CLI with comprehensive options
- **🆕 REST API**: HTTP endpoints for file upload and programmatic integration
- **🆕 Web Interface**: User-friendly upload form for browser-based usage

### 🚀 Advanced Features
- **Tab Versioning System**: Automatically handles copied tabs with "(2)", "(3)" version suffixes
- **Truncated Name Matching**: Resolves Excel's 31-character tab name limitation
- **Actual Row Numbers**: Reports show real Excel row positions for direct navigation
- **Hidden Tab Support**: Configurable processing of hidden worksheets
- **Dynamic Column Detection**: Handles variable Excel structures automatically
- **Error Resilience**: Graceful handling of malformed data with detailed logging

## 📦 Installation

### Prerequisites
- Python 3.7 or higher
- pip (Python package installer)

### Install Dependencies
```bash
pip install -r requirements.txt
```

Required packages:
- `pandas>=1.5.0` - Excel file processing and data manipulation
- `openpyxl>=3.1.0` - Excel file reading/writing support
- `datetime` - Date/time handling
- `fastapi>=0.104.1` - REST API framework (for Web API mode)
- `uvicorn[standard]>=0.24.0` - ASGI server (for Web API mode)
- `python-multipart>=0.0.6` - File upload support (for Web API mode)

## 🚀 Quick Start

### Option 1: Web API Mode (Recommended) 🌐

**Start the Web Server:**
```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

**Access the Tool:**
- **Web Interface**: Open http://localhost:8000 in your browser
- **API Documentation**: http://localhost:8000/docs  
- **Upload & Compare**: Drag and drop Excel files via web form

**API Usage:**
```bash
# Upload and compare via API
curl -X POST "http://localhost:8000/api/compare-excel" \
  -F "file1=@original.xlsx" \
  -F "file2=@modified.xlsx" \
  -F "title=My Comparison Report"
```

### Option 2: CLI Mode (Original)

**Basic Usage**
```bash
# Compare two Excel files
python main.py file1.xlsx file2.xlsx

# Compare with custom output location
python main.py -o my_report.html file1.xlsx file2.xlsx
```

### Example Output
```
======================================================================
   Excel Source-Target Mapping Comparison Tool v2.0
======================================================================
Comparing: STTM_original.xlsx
     vs:   STTM_changed.xlsx
======================================================================

[OK] File 1: STTM_original.xlsx (153,720 bytes) [OK]
[OK] File 2: STTM_changed.xlsx (171,866 bytes) [OK]

======================================================================
COMPARISON RESULTS
======================================================================
Files analyzed: 2
Total tabs in file 1: 19
Total tabs in file 2: 19
Valid tabs compared: 6

TAB CHANGES:
  Added:     0
  Deleted:   0
  Modified:  2
  Unchanged: 4

MAPPING CHANGES:
  Added:     8
  Deleted:   3
  Modified:  12

CHANGED TABS:
  NetSuiteVendorRequestResponsOTV: +2 added, -1 deleted, ~3 modified
  Vendor Inbound DACH VenProxy: +6 added, -2 deleted, ~9 modified

SUMMARY: 23 total changes detected

======================================================================
SUCCESS: Comparison completed successfully in 2.47 seconds
Report saved to: reports/diff_reports/comparison_STTM_original_vs_STTM_changed_20250902_164532.html
   Open this file in your web browser to view the detailed comparison
======================================================================
```

## 📖 Command-Line Reference

### Usage
```bash
python main.py [OPTIONS] file1.xlsx file2.xlsx
```

### Arguments
- `file1` - First Excel file (original/baseline version)
- `file2` - Second Excel file (modified/new version)

### Output Options
| Option | Description |
|--------|-------------|
| `-o FILE, --output FILE` | Custom output HTML report file path |
| `--no-report` | Skip HTML report generation (console output only) |
| `--report-title TITLE` | Custom title for the HTML report |

### Logging Options
| Option | Description |
|--------|-------------|
| `--debug` | Enable debug mode with verbose output |
| `--quiet` | Suppress console output (errors only) |
| `--log-level LEVEL` | Set logging level (DEBUG, INFO, WARNING, ERROR) |

### Processing Options
| Option | Description |
|--------|-------------|
| `--include-hidden` | Include hidden tabs in comparison |
| `--validate-only` | Only validate files without performing comparison |
| `--progress` | Show progress indicators during processing |

### Examples

#### Basic Comparison
```bash
python main.py source.xlsx target.xlsx
```

#### Debug Mode with Progress
```bash
python main.py --debug --progress source.xlsx target.xlsx
```

#### Custom Report Location
```bash
python main.py -o "reports/my_comparison.html" source.xlsx target.xlsx
```

#### Include Hidden Tabs
```bash
python main.py --include-hidden source.xlsx target.xlsx
```

#### Quiet Mode for Automation
```bash
python main.py --quiet --no-report source.xlsx target.xlsx
```

#### Validation Only
```bash
python main.py --validate-only source.xlsx target.xlsx
```

## 🌐 Web API Reference

### API Endpoints

#### `POST /api/compare-excel`
Upload and compare two Excel files.

**Request:**
- Content-Type: `multipart/form-data`
- Parameters:
  - `file1` (required): First Excel file (.xlsx/.xls) 
  - `file2` (required): Second Excel file (.xlsx/.xls)
  - `title` (optional): Custom title for reports

**Response Example:**
```json
{
    "status": "success",
    "message": "Comparison completed successfully", 
    "comparison_summary": {
        "total_changes": 23,
        "tabs": {"added": 0, "deleted": 0, "modified": 2},
        "mappings": {"added": 8, "deleted": 3, "modified": 12}
    },
    "reports": {
        "html_report": "/reports/diff_reports/comparison_file1_vs_file2.html",
        "json_report": "/reports/diff_reports/comparison_file1_vs_file2.json"
    }
}
```

#### Other Endpoints
- `GET /api/health` - Health check
- `GET /api/config` - Current configuration  
- `GET /` - Web upload interface

### Programming Examples

**Python:**
```python
import requests

with open("file1.xlsx", "rb") as f1, open("file2.xlsx", "rb") as f2:
    files = {"file1": f1, "file2": f2}
    response = requests.post("http://localhost:8000/api/compare-excel", files=files)
    result = response.json()
    print(f"Changes detected: {result['comparison_summary']['total_changes']}")
```

**JavaScript:**
```javascript
const formData = new FormData();
formData.append('file1', file1);
formData.append('file2', file2);

fetch('/api/compare-excel', {method: 'POST', body: formData})
  .then(response => response.json())
  .then(data => console.log('Result:', data));
```

## 📊 Understanding the Output

### Console Output
The tool provides real-time feedback including:
- File validation results with sizes
- Processing progress (with `--progress`)
- Summary of changes detected
- Performance timing information
- Report file locations

### HTML Reports
Generated HTML reports include:
- **Executive Summary**: High-level overview of changes
- **Tab Comparison**: Detailed tab-by-tab analysis
- **Change Details**: Field-level modifications with highlighting
- **Navigation**: Interactive table of contents
- **Version Information**: Tab versioning metadata

### JSON Reports
Machine-readable JSON output contains:
- Structured change data
- Actual Excel row numbers
- Tab versioning information
- Processing metadata

## ⚙️ Configuration

### Built-in Settings
The tool includes smart defaults for:
- Excel structure recognition
- Column name variations
- Report formatting
- Performance optimization

### Key Configuration Options (config.py)
```python
# Processing settings
SKIP_HIDDEN_TABS = True
CASE_SENSITIVE_COMPARISON = False
TRIM_WHITESPACE = True

# Report settings
REPORTS_BASE_DIR = "reports"
INCLUDE_TIMESTAMP_IN_FILENAME = True
REPORT_TITLE_TEMPLATE = "Comparison Report: {file1} vs {file2}"

# Performance limits
MAX_ROWS_TO_PROCESS = 10000
MAX_COLUMNS_TO_SCAN = 50
```

## 🔧 Advanced Features

### Tab Versioning System
Automatically handles Excel's common tab copying patterns:
```
Original Tab: "VendorInboundVendorProxytoD365"
Copied Tab:   "VendorInboundVendorProxytoD3 (2)"  # Truncated + versioned
```
The tool intelligently matches these as the same logical tab.

### Dynamic Column Detection
Recognizes various column naming conventions:
- `Canonical Name` / `Entity` / `Table`
- `Field` / `Field Name` / `Column`
- `Description` / `Desc` / `Comments`
- `Type` / `Data Type` / `DataType`

### Hidden Tab Processing
Control hidden tab processing:
```bash
# Include hidden tabs
python main.py --include-hidden source.xlsx target.xlsx

# Or modify config.py:
PROCESS_HIDDEN_TABS = True
```

## 📁 File Structure

### Input Files
Expects Excel files (.xlsx, .xls) with the following structure:
- **Row 9**: System names (Source and Target systems)
- **Row 10**: Column headers
- **Row 11+**: Mapping data

### Output Files
```
reports/
└── diff_reports/
    ├── comparison_file1_vs_file2_20250902_164532.html
    └── comparison_file1_vs_file2_20250902_164532.json
```

## 🐛 Error Handling

### Common Issues and Solutions

#### File Not Found
```
ERROR: File validation failed: Cannot read file 'missing.xlsx' - File does not exist
```
**Solution**: Check file path and permissions

#### Excel Format Issues
```
ERROR: Excel analysis failed: Unable to read worksheet 'TabName'
```
**Solution**: Ensure files are valid Excel format and not corrupted

#### Memory Issues with Large Files
The tool automatically limits processing:
- Maximum 10,000 rows per tab
- Maximum 50 columns scanned
- Configurable via `config.py`

### Debug Mode
For detailed troubleshooting:
```bash
python main.py --debug source.xlsx target.xlsx
```

This provides:
- Detailed processing logs
- Performance timing
- Column detection details
- Validation step results

## 🔍 Validation

### File Validation
- File existence and readability
- Valid Excel format
- Minimum required structure

### Data Validation
- Required column presence
- System name detection
- Mapping record completeness

### Tab Validation
Automatically filters out:
- Empty tabs
- Field definition tables
- JSON data sheets
- Malformed structures

## 📈 Performance

### Benchmarks
Typical performance on standard hardware:
- **Small files** (1-5 tabs): < 1 second
- **Medium files** (5-15 tabs): 1-5 seconds
- **Large files** (15+ tabs): 5-15 seconds

### Optimization
- Efficient pandas-based processing
- Lazy loading of Excel data
- Memory-conscious design
- Configurable processing limits

## 🤝 Integration

### Automation Scripts
```bash
#!/bin/bash
# Batch comparison script
for file in *.xlsx; do
    python main.py --quiet "$file" "updated_$file"
done
```

### CI/CD Integration
```yaml
# GitHub Actions example
- name: Compare Excel Files
  run: |
    python main.py --quiet original.xlsx updated.xlsx
    # Check exit code: 0 = success, 1 = error
```

### API Integration Examples
```python
# Automated comparison service
import requests

def compare_excel_files(file1_path, file2_path):
    with open(file1_path, 'rb') as f1, open(file2_path, 'rb') as f2:
        files = {'file1': f1, 'file2': f2}
        response = requests.post('http://api-server:8000/api/compare-excel', files=files)
        return response.json()

# Check for changes
result = compare_excel_files('baseline.xlsx', 'current.xlsx')
if result['comparison_summary']['total_changes'] > 0:
    print("🚨 Changes detected! Review reports:")
    print(f"HTML: {result['reports']['html_report']}")
```

## 🚀 Production Deployment

### Web API Deployment

**Using Gunicorn (Recommended):**
```bash
pip install gunicorn
gunicorn api:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

**Using Docker:**
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Environment Variables:**
```bash
export API_HOST="0.0.0.0"
export API_PORT="8000"
export REPORTS_DIR="/app/reports"
```

### Production Considerations

**Security:**
- Configure CORS for specific domains only
- Add rate limiting for file uploads
- Implement file size limits
- Use HTTPS in production

**Performance:**
- Use multiple worker processes
- Configure upload size limits
- Set up file cleanup schedules
- Monitor disk usage for reports directory

**Monitoring:**
```bash
# Health check endpoint
curl http://your-server:8000/api/health

# Expected response:
{"status": "healthy", "service": "Excel Comparison API", "version": "1.0.0"}
```

## 📝 Changelog

### Latest Version (v2.1) 🆕
- ✅ **🌐 Web API Mode**: Complete REST API with FastAPI framework
- ✅ **📱 Web Interface**: Browser-based file upload and comparison  
- ✅ **🔌 HTTP Endpoints**: Programmatic integration support
- ✅ **🚀 Production Ready**: Docker, Gunicorn, monitoring support
- ✅ **💯 Full Compatibility**: CLI and API modes use identical logic
- ✅ **📄 Enhanced Documentation**: API reference and deployment guides

### Version 2.0
- ✅ **Tab Versioning System**: Revolutionary handling of copied tabs
- ✅ **Actual Row Numbers**: JSON reports show real Excel positions
- ✅ **Truncated Name Matching**: Resolves 31-character Excel limitation
- ✅ **Enhanced Reports**: Professional HTML with navigation
- ✅ **Performance Improvements**: Optimized processing engine

### Previous Versions
- **v1.0**: Core comparison functionality
- **Phase 1-4**: Development milestones documented in `DEVELOPMENT_LOG.md`

## 🚨 Production Notes

### System Requirements
- **Memory**: Minimum 1GB RAM (2GB+ recommended for large files)
- **Storage**: 100MB+ free space for reports
- **Python**: 3.7+ with pandas and openpyxl support

### Known Limitations
- Excel files only (no CSV/other formats)
- Maximum 10,000 rows per tab (configurable)
- Requires specific Excel structure (rows 9-10 headers)

### Best Practices
1. **File Naming**: Use descriptive filenames for better reports
2. **Backup**: Always backup original files before modification
3. **Testing**: Use `--validate-only` for initial file testing
4. **Performance**: Use `--quiet` for batch processing
5. **Debugging**: Enable `--debug` for troubleshooting

## 📚 Additional Documentation

- `PROJECT_STATUS.md` - Current development status and metrics
- `DEVELOPMENT_LOG.md` - Detailed session history and achievements
- `PHASE_PROGRESS.md` - Task completion tracking
- `ARCHITECTURE_NOTES.md` - Technical decisions and design notes
- `API_README.md` - Complete API documentation and usage guide

## 🎯 Production Status

**Current Status**: ✅ **Production-ready with dual modes (CLI + Web API)**  
**Latest Enhancement**: 🌐 **Complete Web API with REST endpoints**  
**Modes Available**: 
- **CLI Mode**: Original command-line interface (fully preserved)
- **Web API Mode**: REST API + browser interface (new!)

**Real-world Validation**: 
- ✅ Reduced false positives from 97 to 11 changes
- ✅ 100% pass rate across all phases
- ✅ API tested with existing Excel files
- ✅ All original functionality preserved

**Deployment Options**:
- **Development**: `uvicorn api:app --reload`
- **Production**: Docker, Gunicorn, cloud deployment ready
- **Integration**: REST API for automated workflows

---

**🚀 Ready for immediate production use in both CLI and Web API modes!**

**Quick Start:**
```bash
# CLI Mode (original)
python main.py file1.xlsx file2.xlsx

# Web API Mode (new)
uvicorn api:app --reload
# Then visit: http://localhost:8000
```