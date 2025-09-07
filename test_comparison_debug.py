"""
Debug SharePoint comparison functionality
"""

import time
from api import db_manager, api_wrapper
from sharepoint import DownloadService

def test_comparison_debug():
    """Debug the SharePoint comparison functionality step by step."""
    
    print("SharePoint Comparison Debug Test")
    print("=" * 50)
    
    try:
        # Get real data
        result = db_manager.get_file_versions(
            'https://pursuitsoftwarebiz-my.sharepoint.com/:x:/g/personal/sujit_s_pursuitsoftware_biz/EQ-MT6NYQZxBuFUGvrpU5VABE4G5Gbmsvvci9J45TLCywQ?e=FlEJry', 
            'url'
        )
        
        if len(result['versions']) < 2:
            print("Need at least 2 versions for comparison test")
            return False
        
        version1 = result['versions'][0]
        version2 = result['versions'][1]
        
        print(f"Testing comparison between:")
        print(f"  Version 1: seq={version1['sequence_number']}, id={version1['version_id']}, downloaded={version1['downloaded']}")
        print(f"  Version 2: seq={version2['sequence_number']}, id={version2['version_id']}, downloaded={version2['downloaded']}")
        
        # Step 1: Check if both versions can be accessed
        print("\\n1. Checking version access...")
        try:
            info1 = db_manager.get_sharepoint_info(version1['version_id'])
            info2 = db_manager.get_sharepoint_info(version2['version_id'])
            print("   [OK] Both versions accessible from database")
        except Exception as e:
            print(f"   [FAILED] Error accessing version info: {e}")
            return False
        
        # Step 2: Test individual download capability
        print("\\n2. Testing individual downloads...")
        download_service = DownloadService()
        
        # Test version 1 download
        start_time = time.time()
        try:
            file1_path = api_wrapper._ensure_version_downloaded(version1['version_id'], info1, download_service)
            download1_time = time.time() - start_time
            print(f"   [OK] Version 1 download: {download1_time:.2f}s, path: {file1_path}")
        except Exception as e:
            print(f"   [FAILED] Version 1 download failed: {e}")
            return False
        
        # Test version 2 download
        start_time = time.time()
        try:
            file2_path = api_wrapper._ensure_version_downloaded(version2['version_id'], info2, download_service)
            download2_time = time.time() - start_time
            print(f"   [OK] Version 2 download: {download2_time:.2f}s, path: {file2_path}")
        except Exception as e:
            print(f"   [FAILED] Version 2 download failed: {e}")
            return False
        
        # Step 3: Test file comparison directly
        print("\\n3. Testing file comparison...")
        start_time = time.time()
        try:
            # Test the direct comparison method
            comparison_result = api_wrapper.compare_file_versions_by_path(
                file1_path=file1_path,
                file2_path=file2_path,
                custom_title=f"Debug Test: v{version1['sequence_number']} vs v{version2['sequence_number']}",
                db_file_name=info1["file_name"]
            )
            comparison_time = time.time() - start_time
            print(f"   [OK] File comparison completed: {comparison_time:.2f}s")
            
            if comparison_result.get('status') == 'success':
                summary = comparison_result.get('comparison_summary', {})
                print(f"   Total changes: {summary.get('total_changes', 'unknown')}")
                print(f"   Tabs compared: {comparison_result.get('processing_info', {}).get('total_tabs_compared', 'unknown')}")
            else:
                print(f"   Comparison status: {comparison_result.get('status', 'unknown')}")
                
        except Exception as e:
            print(f"   [FAILED] File comparison failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Step 4: Test the full SharePoint comparison method
        print("\\n4. Testing full SharePoint comparison method...")
        start_time = time.time()
        try:
            full_result = api_wrapper.compare_versions_with_sharepoint(
                version1_id=version1['version_id'],
                version2_id=version2['version_id'],
                custom_title=f"Full Test: v{version1['sequence_number']} vs v{version2['sequence_number']}"
            )
            full_comparison_time = time.time() - start_time
            print(f"   [OK] Full SharePoint comparison completed: {full_comparison_time:.2f}s")
            
            if full_result.get('status') == 'success':
                summary = full_result.get('comparison_summary', {})
                print(f"   Total changes: {summary.get('total_changes', 'unknown')}")
                reports = full_result.get('reports', {})
                print(f"   HTML report: {reports.get('html_url', 'N/A')}")
                print(f"   JSON report: {reports.get('json_url', 'N/A')}")
            else:
                print(f"   Full comparison status: {full_result.get('status', 'unknown')}")
                
        except Exception as e:
            print(f"   [FAILED] Full SharePoint comparison failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print("\\n" + "=" * 50)
        print("[SUCCESS] All comparison tests completed successfully!")
        print(f"Performance summary:")
        print(f"  Download 1: {download1_time:.2f}s")
        print(f"  Download 2: {download2_time:.2f}s") 
        print(f"  File comparison: {comparison_time:.2f}s")
        print(f"  Full comparison: {full_comparison_time:.2f}s")
        
        total_time = download1_time + download2_time + comparison_time
        print(f"  Total estimated time: {total_time:.2f}s")
        
        if total_time > 60:
            print("\\n[WARNING] Total time exceeds 60s - API timeout likely")
            print("   Consider increasing timeout or optimizing downloads")
        else:
            print("\\n[OK] Performance is within reasonable limits")
        
        return True
        
    except Exception as e:
        print(f"Debug test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import sys
    success = test_comparison_debug()
    sys.exit(0 if success else 1)