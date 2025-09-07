# Excel Comparison API Documentation

## Overview

This FastAPI application converts the Excel Source-Target Mapping Comparison CLI tool into a REST API while preserving ALL existing functionality. The API provides HTTP endpoints for file upload and comparison, maintaining perfect compatibility with the original CLI logic.

## 🚀 Quick Start

### 1. Set Environment Variables
```bash
# Required: Azure SQL Database connection string
export DATABASE_URL="Driver={ODBC Driver 17 for SQL Server};Server=your-server.database.windows.net;Database=your-db;Uid=your-user;Pwd=your-password"

# Required for Azure Storage integration
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=your-account;AccountKey=your-key;EndpointSuffix=core.windows.net"
export AZURE_STORAGE_CONTAINER_NAME="excel-files"
export STORAGE_TYPE="azure"

# Required for Azure Reports Upload
export AZURE_REPORTS_CONTAINER_NAME="diff-reports"
export UPLOAD_REPORTS_TO_AZURE="true"
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Start the API Server
```bash
# Development mode (with auto-reload)
uvicorn api:app --host 0.0.0.0 --port 8000 --reload

# Production mode
uvicorn api:app --host 0.0.0.0 --port 8000

# Or simply run
python api.py
```

### 4. Access the Application
- **Frontend Interface**: http://localhost:8000 (Alpine.js UI for version comparison)
- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **Alternative Docs**: http://localhost:8000/redoc (ReDoc)

## 🆕 New Features

### Azure Blob Storage Integration
- **Excel File Storage**: Supports downloading Excel files directly from Azure Blob Storage
- **Automatic Detection**: Recognizes Azure blob URLs and handles them transparently
- **Temporary File Management**: Downloads Azure files to temp storage for processing, with automatic cleanup

### Azure Reports Upload
- **Mandatory Upload**: All generated reports are automatically uploaded to Azure Blob Storage
- **SAS URL Generation**: Creates secure, time-limited (7-day) access URLs for reports
- **No Public Access Required**: Works with private storage accounts using SAS tokens
- **Dynamic Folder Structure**: Uses database `file_name` field for consistent folder naming

### Enhanced Report Access
- **Dual Access Points**: Both local server URLs and Azure SAS URLs provided in API response
- **Shareable Links**: Azure URLs can be shared with external teams
- **Secure Access**: SAS tokens provide read-only, time-limited access

### File Name Based Organization
- **Database Integration**: Uses `tracked_files.file_name` field for Azure folder naming
- **Consistent Structure**: All versions of a file share the same Azure folder
- **Fallback Support**: Automatically parses filename patterns if `file_name` not provided

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
        "json_report": "/reports/diff_reports/comparison_file1_vs_file2_20250903_142433.json",
        "azure_html_url": "https://stexceldifffiles.blob.core.windows.net/diff-reports/STTM_Master_Mapping/comparison_file1_vs_file2_20250903_142433.html?se=2025-09-14T02%3A15%3A59Z&sp=r&sv=2025-07-05&sr=b&sig=xxx",
        "azure_json_url": "https://stexceldifffiles.blob.core.windows.net/diff-reports/STTM_Master_Mapping/comparison_file1_vs_file2_20250903_142433.json?se=2025-09-14T02%3A15%3A59Z&sp=r&sv=2025-07-05&sr=b&sig=yyy",
        "azure_html_blob": "STTM_Master_Mapping/comparison_file1_vs_file2_20250903_142433.html",
        "azure_json_blob": "STTM_Master_Mapping/comparison_file1_vs_file2_20250903_142433.json"
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

### Version Management Endpoints

#### `GET /api/files/versions`
Get all versions of a file from the database.

**Parameters:**
- `identifier` (required): SharePoint URL or friendly name to search for
- `search_type` (required): Either "url" or "name"

**Example Request:**
```
GET /api/files/versions?identifier=STTM&search_type=name
GET /api/files/versions?identifier=https://sharepoint.com/file.xlsx&search_type=url
```

**Response:**
```json
{
    "file_info": {
        "file_id": 123,
        "sharepoint_url": "https://sharepoint.com/sites/...",
        "file_name": "STTM_Mapping.xlsx",
        "friendly_name": "STTM",
        "total_versions": 15
    },
    "versions": [
        {
            "version_id": 456,
            "sequence_number": 15,
            "sharepoint_version_id": "15.0",
            "modified_datetime": "2025-09-03T10:30:00",
            "file_size_bytes": 182358,
            "discovered_at": "2025-09-03T11:00:00",
            "diff_taken": true,
            "diff_taken_at": "2025-09-03T11:05:00",
            "downloaded": true,
            "download_filename": "downloads/2025/09/STTM_v15.xlsx",
            "downloaded_at": "2025-09-03T11:01:00",
            "download_error": null,
            "is_latest": true,
            "is_available": true
        }
    ],
    "summary": {
        "total_versions": 15,
        "available_versions": 12,
        "latest_version": {...}
    }
}
```

#### `POST /api/compare-versions`
Compare two Excel files using their file paths (supports both local paths and Azure blob URLs).

**Request:**
- Content-Type: `application/x-www-form-urlencoded` or `multipart/form-data`
- Parameters:
  - `file1_path` (required): Path to first Excel file (local path or Azure blob URL)
  - `file2_path` (required): Path to second Excel file (local path or Azure blob URL)
  - `title` (optional): Custom title for the comparison report
  - `file_name` (optional): Database file_name for Azure folder naming (e.g., "STTM_Master_Mapping.xlsx")

**Example Request (Local Files):**
```bash
curl -X POST "http://localhost:8000/api/compare-versions" \
  -F "file1_path=downloads/2025/09/STTM_v14.xlsx" \
  -F "file2_path=downloads/2025/09/STTM_v15.xlsx" \
  -F "title=Version 14 vs Version 15" \
  -F "file_name=STTM_Master_Mapping.xlsx"
```

**Example Request (Azure URLs):**
```bash
curl -X POST "http://localhost:8000/api/compare-versions" \
  -F "file1_path=https://stexceldifffiles.blob.core.windows.net/excel-files/STTM_v14.xlsx" \
  -F "file2_path=https://stexceldifffiles.blob.core.windows.net/excel-files/STTM_v15.xlsx" \
  -F "title=Azure Files Comparison" \
  -F "file_name=STTM_Master_Mapping.xlsx"
```

**Response:** Enhanced structure with both local and Azure report URLs

#### `GET /api/download-file`
Download an Excel file from the server.

**Parameters:**
- `path` (required): File path from the download_filename field

**Example Request:**
```
GET /api/download-file?path=downloads/2025/09/STTM_v15.xlsx
```

**Response:** Binary file download (Excel file)

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
Frontend interface for version selection and comparison (Alpine.js application).

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

### JavaScript Example - File Upload
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

### JavaScript Example - Version Comparison
```javascript
// First, get file versions
fetch('/api/files/versions?identifier=STTM&search_type=name')
.then(response => response.json())
.then(data => {
    // Select two versions from data.versions
    const version1 = data.versions[0];
    const version2 = data.versions[1];
    
    // Compare the versions using their file paths
    const formData = new FormData();
    formData.append('file1_path', version1.download_filename);
    formData.append('file2_path', version2.download_filename);
    formData.append('title', `Version ${version1.sequence_number} vs ${version2.sequence_number}`);
    
    return fetch('/api/compare-versions', {
        method: 'POST',
        body: formData
    });
})
.then(response => response.json())
.then(result => {
    console.log('Comparison completed:', result);
    window.open(result.reports.html_report, '_blank');
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
├── api.py                 # FastAPI application with database integration
├── main.py               # Original CLI tool (preserved)
├── comparator.py         # Core comparison logic (unchanged)
├── report_generator.py   # HTML report generation (unchanged)
├── json_report_generator.py # JSON report generation (unchanged)
├── config.py             # Configuration (unchanged)
├── uploads/              # Temporary file storage
├── reports/              # Generated reports
│   └── diff_reports/     # API-generated comparison reports
├── static/               # Static files for web interface
├── templates/            # Frontend templates
│   └── index.html        # Alpine.js frontend application
├── FRONTEND_README.md    # Frontend documentation
└── API_README.md         # This file
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
# Required
export DATABASE_URL="Driver={ODBC Driver 17 for SQL Server};Server=...;Database=...;Uid=...;Pwd=..."

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
✅ Alpine.js frontend for version comparison  
✅ Database integration for version management  
✅ File path-based comparison  
✅ Automatic cleanup  
✅ CORS support  

### Frontend Features
✅ Search files by name or SharePoint URL  
✅ View all versions with metadata  
✅ Select and compare any two versions  
✅ Real-time error handling and feedback  
✅ Direct access to HTML/JSON reports  
✅ Responsive design with Tailwind CSS  

The API is a **perfect wrapper** around the existing CLI tool - no functionality is lost or modified. The frontend provides an intuitive interface for version selection and comparison.