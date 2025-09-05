# Excel Comparison API Documentation

## Overview

This FastAPI application converts the Excel Source-Target Mapping Comparison CLI tool into a REST API while preserving ALL existing functionality. The API provides HTTP endpoints for file upload and comparison, maintaining perfect compatibility with the original CLI logic.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the API Server
```bash
# Development mode (with auto-reload)
uvicorn api:app --host 0.0.0.0 --port 8000 --reload

# Production mode
uvicorn api:app --host 0.0.0.0 --port 8000
```

### 3. Access the API
- **Web Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

## 📡 API Endpoints

### Main Comparison Endpoint

#### `POST /api/compare-excel`

Compare two Excel files and generate reports.

**Request:**
- Content-Type: `multipart/form-data`
- Parameters:
  - `file1` (required): First Excel file (.xlsx/.xls)
  - `file2` (required): Second Excel file (.xlsx/.xls) 
  - `title` (optional): Custom title for reports

**Response:**
```json
{
    "status": "success",
    "message": "Comparison completed successfully",
    "comparison_summary": {
        "total_changes": 23,
        "tabs": {
            "total_v1": 19,
            "total_v2": 19,
            "added": 0,
            "deleted": 0,
            "modified": 2,
            "unchanged": 4
        },
        "mappings": {
            "total_v1": 1245,
            "total_v2": 1256,
            "added": 8,
            "deleted": 3,
            "modified": 12
        },
        "changed_tabs": [
            {
                "name": "NetSuiteVendorRequestResponsOTV",
                "added": 2,
                "deleted": 1,
                "modified": 3
            }
        ]
    },
    "reports": {
        "html_report": "/reports/diff_reports/comparison_file1_vs_file2_20250903_142433.html",
        "json_report": "/reports/diff_reports/comparison_file1_vs_file2_20250903_142433.json"
    },
    "files_info": {
        "file1": {"name": "STTM_original.xlsx", "size": 153720},
        "file2": {"name": "STTM_changed.xlsx", "size": 171866}
    },
    "processing_info": {
        "timestamp": "2025-09-03T14:24:33.123456",
        "total_tabs_compared": 6,
        "has_errors": false,
        "errors": []
    }
}
```

### Utility Endpoints

#### `GET /api/health`
Health check endpoint.

**Response:**
```json
{
    "status": "healthy", 
    "service": "Excel Comparison API",
    "version": "1.0.0",
    "timestamp": "2025-09-03T14:24:33.123456"
}
```

#### `GET /api/config`
Get current API configuration.

**Response:**
```json
{
    "supported_extensions": [".xlsx", ".xls"],
    "max_rows_to_process": 10000,
    "max_columns_to_scan": 50,
    "reports_base_dir": "reports",
    "include_hidden_tabs": false
}
```

#### `GET /`
Web interface for file upload and testing.

## 🔄 Usage Examples

### cURL Example
```bash
curl -X POST "http://localhost:8000/api/compare-excel" \
  -F "file1=@STTM_original.xlsx" \
  -F "file2=@STTM_changed.xlsx" \
  -F "title=My Custom Comparison Report"
```

### Python Example
```python
import requests

url = "http://localhost:8000/api/compare-excel"

with open("file1.xlsx", "rb") as f1, open("file2.xlsx", "rb") as f2:
    files = {
        "file1": ("file1.xlsx", f1, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        "file2": ("file2.xlsx", f2, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    }
    data = {"title": "API Comparison Test"}
    
    response = requests.post(url, files=files, data=data)
    result = response.json()
    
    print(f"Total changes: {result['comparison_summary']['total_changes']}")
    print(f"HTML Report: {result['reports']['html_report']}")
```

### JavaScript Example
```javascript
const formData = new FormData();
formData.append('file1', file1); // File object from input
formData.append('file2', file2); // File object from input
formData.append('title', 'My Report');

fetch('/api/compare-excel', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(data => {
    console.log('Comparison result:', data);
    // Access reports via data.reports.html_report and data.reports.json_report
});
```

## 📁 File Handling

### Supported Formats
- Excel 2007+ (.xlsx) - Recommended
- Excel 97-2003 (.xls) - Legacy support

### File Processing
1. **Upload**: Files uploaded via multipart/form-data
2. **Temporary Storage**: Saved to `uploads/` directory with unique timestamps
3. **Validation**: Same validation as CLI tool using existing logic
4. **Processing**: Uses identical comparison logic as CLI version
5. **Cleanup**: Temporary files automatically deleted after processing

### Report Generation
- **HTML Reports**: Generated in `reports/diff_reports/` directory
- **JSON Reports**: Generated alongside HTML with same filename
- **Access**: Reports accessible via HTTP at `/reports/` endpoint
- **Naming**: Uses same timestamp-based naming as CLI tool

## 🛡️ Error Handling

The API preserves all existing error handling from the CLI tool:

### Client Errors (4xx)
- **400 Bad Request**: Invalid file format, validation errors
- **413 Request Entity Too Large**: Files too large (if configured)

### Server Errors (5xx)
- **500 Internal Server Error**: Processing failures, report generation errors

### Error Response Format
```json
{
    "detail": "User-friendly error message explaining what went wrong"
}
```

## ⚙️ Configuration

All existing configuration from `config.py` is preserved:

### Key Settings
- `MAX_ROWS_TO_PROCESS = 10000`: Limit for large files
- `MAX_COLUMNS_TO_SCAN = 50`: Column scanning limit
- `SKIP_HIDDEN_TABS = True`: Hidden tab processing
- `CASE_SENSITIVE_COMPARISON = False`: Comparison sensitivity

### Directory Structure
```
project/
├── api.py                 # FastAPI application
├── main.py               # Original CLI tool (preserved)
├── comparator.py         # Core comparison logic (unchanged)
├── report_generator.py   # HTML report generation (unchanged)
├── json_report_generator.py # JSON report generation (unchanged)
├── config.py             # Configuration (unchanged)
├── uploads/              # Temporary file storage
├── reports/              # Generated reports
│   └── diff_reports/     # API-generated comparison reports
├── static/               # Static files for web interface
└── templates/            # Jinja2 templates
```

## 🔧 Development

### Running in Development
```bash
# Auto-reload on code changes
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

### Testing
The API can be tested using the existing Excel test files:
- Use any two Excel files with Source-Target mapping structure
- Test via web interface at http://localhost:8000
- Or use cURL/Postman with `/api/compare-excel` endpoint

### Logging
- API requests logged using existing logging framework
- Same log files and levels as CLI tool
- Performance timers preserved for API operations

## 🚀 Production Deployment

### Using Gunicorn
```bash
pip install gunicorn
gunicorn api:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Using Docker
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables
```bash
# Optional environment configuration
export API_HOST="0.0.0.0"
export API_PORT="8000"
export REPORTS_DIR="/app/reports"
```

## 🔒 Security Considerations

### File Upload Security
- File type validation (only .xlsx/.xls allowed)
- Temporary file cleanup after processing
- No persistent storage of user files

### CORS Configuration
- Currently allows all origins (`allow_origins=["*"]`)
- Configure for production: `allow_origins=["https://yourdomain.com"]`

### Rate Limiting
Consider adding rate limiting for production:
```bash
pip install slowapi
```

## ✅ Compatibility

### Preserved Features
✅ All CLI functionality intact  
✅ Identical comparison logic  
✅ Same report generation  
✅ All advanced features (tab versioning, truncated names, etc.)  
✅ Same error handling  
✅ Same configuration options  

### New API Features
✅ HTTP REST endpoints  
✅ File upload via multipart/form-data  
✅ JSON response format  
✅ Web interface for testing  
✅ Automatic cleanup  
✅ CORS support  

The API is a **perfect wrapper** around the existing CLI tool - no functionality is lost or modified.