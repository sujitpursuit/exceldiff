"""
Test SharePoint Connection and Services

This script tests the SharePoint integration components.
"""

import json
import logging
from datetime import datetime
from sharepoint import SharePointService, DownloadService, SharePointConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_configuration():
    """Test SharePoint configuration."""
    print("\n" + "="*60)
    print("SHAREPOINT CONFIGURATION TEST")
    print("="*60)
    
    config = SharePointConfig()
    print(config)
    
    is_valid, errors = config.validate()
    if is_valid:
        print("[OK] Configuration is valid")
    else:
        print("[ERROR] Configuration validation failed:")
        for error in errors:
            print(f"  - {error}")
    
    return is_valid


def test_sharepoint_connection():
    """Test SharePoint connection."""
    print("\n" + "="*60)
    print("SHAREPOINT CONNECTION TEST")
    print("="*60)
    
    try:
        service = SharePointService()
        result = service.test_connection()
        
        print(f"Connection Status: {result.get('connected', False)}")
        print(f"Details: {json.dumps(result, indent=2)}")
        
        return result.get('connected', False)
        
    except Exception as e:
        print(f"[ERROR] Connection test failed: {e}")
        return False


def test_parse_sharepoint_url():
    """Test parsing a SharePoint URL."""
    print("\n" + "="*60)
    print("SHAREPOINT URL PARSING TEST")
    print("="*60)
    
    # Test URL from tracked_files
    test_url = "https://pursuitsoftwarebiz-my.sharepoint.com/:x:/g/personal/sujit_s_pursuitsoftware_biz/EQ-MT6NYQZxBuFUGvrpU5VABE4G5Gbmsvvci9J45TLCywQ?e=FlEJry"
    
    try:
        service = SharePointService()
        result = service.parse_sharepoint_url(test_url)
        
        print(f"URL: {test_url[:80]}...")
        print(f"Parsed Result:")
        print(f"  Drive ID: {result.get('drive_id', 'N/A')[:50]}...")
        print(f"  Item ID: {result.get('item_id', 'N/A')}")
        print(f"  File Name: {result.get('file_name', 'N/A')}")
        
        return result.get('drive_id') != 'placeholder_drive_id'
        
    except Exception as e:
        print(f"[ERROR] URL parsing failed: {e}")
        return False


def test_get_file_metadata():
    """Test getting file metadata."""
    print("\n" + "="*60)
    print("FILE METADATA TEST")
    print("="*60)
    
    # Use values from tracked_files table
    drive_id = "b!1_mYx0m0B0OWXPuxQlSp4mDijOxSE6pHqTS5ZF-ezVHGTTc3jX5USo1gOfeb4hno"
    item_id = "01BUFMFVAPRRH2GWCBTRA3QVIGX25FJZKQ"
    
    try:
        service = SharePointService()
        metadata = service.get_file_metadata(drive_id, item_id)
        
        print(f"File Metadata:")
        print(f"  Name: {metadata.get('name', 'N/A')}")
        print(f"  Size: {metadata.get('size', 0)} bytes")
        print(f"  Modified: {metadata.get('lastModifiedDateTime', 'N/A')}")
        print(f"  Web URL: {metadata.get('webUrl', 'N/A')[:80]}...")
        
        return metadata.get('id') is not None
        
    except Exception as e:
        print(f"[ERROR] Metadata retrieval failed: {e}")
        print("This might be due to Graph API permissions. Check Azure AD app permissions.")
        return False


def test_download_service():
    """Test download service storage setup."""
    print("\n" + "="*60)
    print("DOWNLOAD SERVICE TEST")
    print("="*60)
    
    try:
        download_service = DownloadService()
        
        # Test storage info
        storage_info = download_service.get_storage_info()
        print(f"Storage Information:")
        print(f"  Path: {storage_info.get('path', 'N/A')}")
        print(f"  Exists: {storage_info.get('exists', False)}")
        print(f"  Files: {storage_info.get('file_count', 0)}")
        print(f"  Total Size: {storage_info.get('total_size_mb', 0)} MB")
        
        # Test path generation
        test_file_name = "STTM workingversion.xlsx"
        test_seq = 1
        test_version = "1.0"
        
        full_path, relative_path = download_service.get_local_path(
            file_name=test_file_name,
            sequence_number=test_seq,
            version_id=test_version
        )
        
        print(f"\nPath Generation Test:")
        print(f"  Input: {test_file_name}")
        print(f"  Full Path: {full_path}")
        print(f"  Relative Path: {relative_path}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Download service test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("\nSharePoint Integration Test Suite")
    print("="*60)
    print(f"Started at: {datetime.now()}")
    
    results = {
        "Configuration": test_configuration(),
        "Connection": test_sharepoint_connection(),
        "URL Parsing": test_parse_sharepoint_url(),
        "File Metadata": test_get_file_metadata(),
        "Download Service": test_download_service()
    }
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "[OK]" if passed else "[FAILED]"
        print(f"{status} {test_name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\nSUCCESS: All tests passed!")
        print("\nPhase 1 implementation is complete. You can now proceed to Phase 2.")
    else:
        print("\nWARNING: Some tests failed.")
        print("\nTroubleshooting:")
        print("1. Check environment variables in .env file")
        print("2. Verify Graph API permissions in Azure AD")
        print("3. Ensure the SharePoint URL and IDs are correct")
        print("4. Check network connectivity to Microsoft services")
    
    return all_passed


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