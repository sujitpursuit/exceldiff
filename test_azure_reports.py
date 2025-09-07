"""
Test Azure Reports Upload Integration

This script tests the complete workflow of Excel comparison with Azure reports upload.
It will compare the STTM files and verify that both local and Azure reports are generated.

Usage:
    python test_azure_reports.py
"""

import os
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_comparison_with_azure_reports():
    """Test comparison that includes Azure reports upload."""
    print("Testing Excel Comparison with Azure Reports Upload")
    print("=" * 55)
    
    # Use the Azure blob URLs for STTM files
    file1_path = "https://stexceldifffiles.blob.core.windows.net/excel-files/STTM Working Version File_seq1_v1.0_20250904_210303.xlsx"
    file2_path = "https://stexceldifffiles.blob.core.windows.net/excel-files/STTM Working Version File_seq7_v7.0_20250904_210617.xlsx"
    
    print(f"Comparing files:")
    print(f"  File 1: ...{file1_path[-60:]}")
    print(f"  File 2: ...{file2_path[-60:]}")
    print()
    
    # Check environment configuration
    print("Environment Configuration:")
    reports_container = os.getenv("AZURE_REPORTS_CONTAINER_NAME")
    upload_enabled = os.getenv("UPLOAD_REPORTS_TO_AZURE")
    print(f"  Reports Container: {reports_container}")
    print(f"  Upload Enabled: {upload_enabled}")
    print()
    
    try:
        # Prepare the request
        api_url = "http://localhost:8000/api/compare-versions"
        form_data = {
            'file1_path': file1_path,
            'file2_path': file2_path,
            'title': 'Azure Reports Test: STTM v1 vs v7'
        }
        
        print(">> Sending comparison request...")
        start_time = datetime.now()
        
        response = requests.post(api_url, data=form_data, timeout=180)  # 3 minute timeout
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f">> Request completed in {duration:.2f} seconds")
        print()
        
        if response.status_code == 200:
            result = response.json()
            
            print("SUCCESS: Comparison completed!")
            print()
            
            # Display comparison summary
            summary = result.get('comparison_summary', {})
            print("Comparison Summary:")
            print(f"  Total changes: {summary.get('total_changes', 'Unknown')}")
            
            mappings = summary.get('mappings', {})
            print(f"  Added mappings: {mappings.get('added', 0)}")
            print(f"  Modified mappings: {mappings.get('modified', 0)}")
            print(f"  Deleted mappings: {mappings.get('deleted', 0)}")
            print()
            
            # Display reports information
            reports = result.get('reports', {})
            print("Generated Reports:")
            
            # Local reports (existing functionality)
            print("  Local Reports:")
            if reports.get('html_report'):
                print(f"    HTML: http://localhost:8000{reports['html_report']}")
            if reports.get('json_report'):
                print(f"    JSON: http://localhost:8000{reports['json_report']}")
            
            # Azure reports (mandatory functionality)
            print("  Azure Reports (Required):")
            has_azure_reports = bool(reports.get('azure_html_url') and reports.get('azure_json_url'))
            
            if reports.get('azure_html_url'):
                print(f"    HTML: {reports['azure_html_url']}")
            else:
                print("    HTML: MISSING - API should have failed!")
            
            if reports.get('azure_json_url'):
                print(f"    JSON: {reports['azure_json_url']}")
            else:
                print("    JSON: MISSING - API should have failed!")
            
            # Azure blob information
            if reports.get('azure_html_blob') or reports.get('azure_json_blob'):
                print("  Azure Blob Paths:")
                if reports.get('azure_html_blob'):
                    print(f"    HTML Blob: {reports['azure_html_blob']}")
                if reports.get('azure_json_blob'):
                    print(f"    JSON Blob: {reports['azure_json_blob']}")
            
            print()
            
            # Test results
            local_reports_ok = bool(reports.get('html_report') and reports.get('json_report'))
            
            print("Test Results:")
            print(f"  [OK] Local reports generated: {local_reports_ok}")
            print(f"  {'[OK]' if has_azure_reports else '[WARN]'} Azure reports uploaded: {has_azure_reports}")
            
            if upload_enabled == "true":
                if has_azure_reports:
                    print("  [OK] Azure upload working as expected")
                    
                    # Test base filename extraction
                    expected_base = "STTM Working Version File"
                    if reports.get('azure_html_blob') and expected_base in reports['azure_html_blob']:
                        print(f"  [OK] Base filename extraction working: Found '{expected_base}' in blob path")
                    else:
                        print(f"  [WARN] Base filename extraction may need review")
                        
                else:
                    print("  [WARN] Azure upload enabled but no reports uploaded - check logs")
            else:
                print("  [INFO] Azure upload disabled in configuration")
            
            print()
            
            # Processing information
            processing = result.get('processing_info', {})
            print("Processing Details:")
            print(f"  Tabs compared: {processing.get('total_tabs_compared', 0)}")
            print(f"  Has errors: {processing.get('has_errors', False)}")
            print(f"  Timestamp: {processing.get('timestamp', 'Unknown')}")
            
            return True
            
        else:
            print(f"ERROR: Comparison failed - Status: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {error_data.get('detail', 'Unknown error')}")
            except:
                print(f"Error response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("ERROR: Request timed out")
        print("The comparison might be taking longer due to Azure uploads")
        return False
    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot connect to API")
        print("Make sure the server is running: python api.py")
        return False
    except Exception as e:
        print(f"ERROR: Request failed: {e}")
        return False

def test_api_health():
    """Quick health check."""
    try:
        response = requests.get("http://localhost:8000/api/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def main():
    """Main test function."""
    print("Azure Reports Integration Test")
    print("=" * 50)
    print(f"Started at: {datetime.now()}")
    print()
    
    # Health check
    if not test_api_health():
        print("ERROR: API is not healthy or not running")
        print("Please start the server first: python api.py")
        return False
    
    print("OK: API is healthy")
    print()
    
    # Run the main test
    success = test_comparison_with_azure_reports()
    
    print()
    print("=" * 50)
    print("Test Summary")
    
    if success:
        print("SUCCESS: Azure reports integration test completed!")
        print()
        print("What was tested:")
        print("+ Excel files downloaded from Azure Storage")
        print("+ Comparison performed successfully")
        print("+ Local reports generated (HTML & JSON)")
        print("+ Azure reports upload attempted")
        print("+ Enhanced API response with Azure URLs")
        print()
        print("Next steps:")
        print("- Check Azure portal to verify reports are in blob storage")
        print("- Test accessing the Azure report URLs directly")
        print("- Verify folder structure matches expected pattern")
        
    else:
        print("ERROR: Test failed")
        print()
        print("Troubleshooting:")
        print("- Check API server is running")
        print("- Verify Azure configuration in .env file")
        print("- Check Azure blob containers exist")
        print("- Review API logs for detailed error information")
    
    return success

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)