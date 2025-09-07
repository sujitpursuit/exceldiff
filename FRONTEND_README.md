# Excel Version Comparison Tool - Frontend Documentation

## Overview

The Excel Version Comparison Tool frontend is a single-page application built with Alpine.js that provides an intuitive interface for comparing different versions of Excel files tracked in SharePoint. The frontend is served directly by the FastAPI backend at the root endpoint.

## Technology Stack

- **Alpine.js v3** - Lightweight reactive framework for interactivity
- **Tailwind CSS** - Utility-first CSS framework for styling
- **HTML5** - Semantic markup structure
- **Vanilla JavaScript** - Core functionality and API integration

## Accessing the Frontend

1. Start the FastAPI server:
   ```bash
   uvicorn api:app --host 0.0.0.0 --port 8000 --reload
   # OR
   python api.py
   ```

2. Open your browser and navigate to:
   ```
   http://localhost:8000
   ```

## Features

### 1. File Search
- Search for files by **friendly name** (e.g., "STTM", "Mapping File")
- Search by **SharePoint URL** (full URL from SharePoint)
- Toggle between name and URL search types
- Auto-search on page load for quick testing (pre-filled with "STTM")

### 2. Version Display
- View all versions of a selected file
- See version metadata:
  - Version number and sequence
  - SharePoint version ID
  - Modified date and time
  - File size
  - Download status (Available/Not Downloaded)
  - Latest version indicator
- Visual indicators for version availability

### 3. Version Selection
- Select exactly 2 versions for comparison
- Checkbox selection with visual feedback
- Disabled state for unavailable versions
- Clear error messages for invalid selections
- Maximum 2 versions enforcement

### 4. Comparison Process
- One-click comparison of selected versions
- Loading states during processing
- Success/error message display
- Auto-clearing messages (3-5 seconds)

### 5. Results Display
- Summary statistics:
  - Total changes count
  - Added mappings count
  - Modified mappings count
- Dual report access:
  - **Local Reports**: Server-hosted files for fast access
    - HTML report (opens in new tab)
    - JSON report (downloadable)
  - **Cloud Reports (Azure)**: Shareable Azure-hosted files with SAS URLs
    - HTML report with cloud icon (opens in new tab)
    - JSON report with cloud icon (downloadable)
    - Secure access via time-limited SAS tokens (7-day expiry)

## User Interface Components

### Search Section
```html
- Text input for search term
- Dropdown for search type (Name/URL)
- Search button with loading state
```

### File Information Panel
```html
- Friendly name display
- Original file name
- Total versions count
- Available versions count
```

### Version List
```html
- Card-based layout for each version
- Checkbox for selection
- Version metadata display
- Visual states (available/unavailable/selected)
```

### Comparison Controls
```html
- Compare button (enabled when 2 versions selected)
- Loading indicator during comparison
- Instructional text
```

### Results Panel
```html
- Statistics cards (Total/Added/Modified)
- Local report buttons (blue/gray)
- Azure report buttons with cloud icons (green/indigo)
- Success/error messages
```

## State Management

The frontend uses Alpine.js data model with the following state:

```javascript
{
    // UI State
    searchTerm: string,        // Search input value
    searchType: string,        // 'name' or 'url'
    loading: boolean,          // Search loading state
    comparing: boolean,        // Comparison loading state
    error: string|null,        // Error message
    successMessage: string|null, // Success message
    
    // Data
    fileInfo: object|null,     // File metadata
    versions: array,           // List of versions
    summary: object|null,      // Version summary
    selectedVersions: array,   // Selected versions (max 2)
    comparisonResult: object|null // Comparison results
}
```

## API Integration

The frontend communicates with the following backend endpoints:

### 1. Get File Versions
```javascript
GET /api/files/versions?identifier={search}&search_type={type}
```
- Fetches all versions of a file
- Returns file info and version list

### 2. Compare Versions
```javascript
POST /api/compare-versions
FormData: {
    file1_path: string,    // Path from version.download_filename or Azure URL
    file2_path: string,    // Path from version.download_filename or Azure URL
    title: string,         // Optional custom title
    file_name: string      // Optional database file_name for Azure folder naming
}
```
- Compares two Excel files by their paths (local or Azure)
- Returns comparison results with both local and Azure report links
- Uses file_name for consistent Azure folder structure when provided

## Error Handling

The frontend implements comprehensive error handling:

1. **Network Errors** - Caught and displayed with descriptive messages
2. **API Errors** - Server error messages displayed to user
3. **Validation Errors** - Client-side validation with helpful messages
4. **State Errors** - Preventing invalid operations (e.g., comparing unavailable versions)

## Visual Feedback

### Color Coding
- **Green** - Available versions, success messages, Azure HTML reports
- **Red** - Errors, unavailable items
- **Blue** - Selected items, primary actions, local HTML reports
- **Gray** - Disabled/unavailable states, local JSON reports
- **Indigo** - Azure JSON reports

### Interactive States
- Hover effects on clickable elements
- Disabled styling for unavailable versions
- Loading spinners during async operations
- Auto-clearing messages with timeouts

## Browser Compatibility

The frontend is compatible with modern browsers that support:
- ES6+ JavaScript features
- CSS Grid and Flexbox
- Async/await syntax
- FormData API

Tested on:
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

## Development Tips

### Debugging
1. Open browser DevTools Console for error messages
2. Check Network tab for API requests/responses
3. Use Alpine DevTools extension for state inspection

### Customization
1. **Styling**: Modify Tailwind classes in HTML
2. **Behavior**: Update Alpine.js methods in script section
3. **Default Values**: Change initial state in `excelComparator()` function

### Testing Different Scenarios
1. **No Results**: Search for non-existent file
2. **Unavailable Versions**: Test with versions that haven't been downloaded
3. **Error States**: Disconnect network to test error handling
4. **Success Flow**: Use "STTM" search to test full flow

## Common Issues and Solutions

### Issue: Versions not showing as available
**Solution**: Ensure files have been downloaded and `download_filename` is populated in database

### Issue: Comparison fails with 404
**Solution**: Verify file paths in `download_filename` are correct and files exist on disk

### Issue: UI not updating
**Solution**: Check browser console for JavaScript errors, ensure Alpine.js is loaded

### Issue: Styles not rendering
**Solution**: Verify Tailwind CSS CDN is accessible, check for network issues

## File Structure

```
templates/
└── index.html          # Single-page Alpine.js application
```

## Security Considerations

1. **Input Validation** - All user inputs are validated before API calls
2. **Path Traversal** - File paths are validated on backend
3. **CORS** - Configured in backend for appropriate origins
4. **Error Messages** - Sensitive information not exposed in errors

## Future Enhancements

Potential improvements for the frontend:

1. **Pagination** - For files with many versions
2. **Filtering** - Filter versions by date range
3. **Bulk Operations** - Compare multiple version pairs
4. **Progress Bar** - For long-running comparisons
5. **Download Management** - UI to trigger file downloads from SharePoint
6. **Comparison History** - View previous comparisons
7. **Export Options** - Additional report formats
8. **Dark Mode** - Theme toggle for user preference

## Support

For issues or questions:
1. Check browser console for errors
2. Verify API is running and accessible
3. Check network connectivity
4. Review this documentation
5. Check API_README.md for backend issues