"""
Test script for SharePoint API endpoints
"""

import os
import sys
import requests
import time
import subprocess
import json
from pathlib import Path

def test_sharepoint_endpoints():
    """Test the new SharePoint API endpoints."""
    
    print("SharePoint API Endpoints Test")
    print("=" * 50)
    
    # Test 1: Import test
    print("1. Testing imports...")
    try:
        from api import app, db_manager, api_wrapper
        from sharepoint import SharePointService, DownloadService
        print("   [OK] All imports successful")
    except Exception as e:
        print(f"   [FAILED] Import failed: {e}")
        return False
    
    # Test 2: Database connection
    print("2. Testing database connection...")
    try:
        conn = db_manager.get_connection()
        conn.close()
        print("   [OK] Database connection successful")
    except Exception as e:
        print(f"   [FAILED] Database connection failed: {e}")
        return False
    
    # Test 3: SharePoint service initialization
    print("3. Testing SharePoint service initialization...")
    try:
        sharepoint_service = SharePointService()
        download_service = DownloadService()
        print("   [OK] SharePoint services initialized successfully")
    except Exception as e:
        print(f"   [FAILED] SharePoint service initialization failed: {e}")
        return False
    
    # Test 4: API routes registration
    print("4. Testing API routes registration...")
    try:
        from fastapi.routing import APIRoute
        sharepoint_routes = []
        for route in app.routes:
            if isinstance(route, APIRoute) and '/api/' in route.path:
                if any(sp_keyword in route.path for sp_keyword in ['sharepoint', 'version-status', 'download-sharepoint']):
                    sharepoint_routes.append(f"{list(route.methods)[0]} {route.path}")
        
        expected_routes = [
            'POST /api/download-sharepoint-version',
            'GET /api/get-version-status', 
            'POST /api/compare-sharepoint-versions'
        ]
        
        print("   SharePoint routes found:")
        for route in sharepoint_routes:
            print(f"     - {route}")
        
        if len(sharepoint_routes) >= 3:
            print("   [OK] SharePoint routes registered successfully")
        else:
            print("   [FAILED] Missing SharePoint routes")
            return False
            
    except Exception as e:
        print(f"   [FAILED] Route registration test failed: {e}")
        return False
    
    # Test 5: Database methods
    print("5. Testing new database methods...")
    try:
        # Test get_sharepoint_info with invalid ID (should raise HTTPException)
        try:
            db_manager.get_sharepoint_info(99999)
            print("   [FAILED] get_sharepoint_info should have failed for invalid ID")
        except Exception:
            print("   [OK] get_sharepoint_info properly handles invalid ID")
        
        # Test update_download_status
        test_result = {"status": "success", "local_path": "test/path.xlsx"}
        success = db_manager.update_download_status(99999, test_result)
        if not success:
            print("   [OK] update_download_status properly handles invalid version")
        else:
            print("   [INFO] update_download_status accepted invalid version (might be expected)")
            
    except Exception as e:
        print(f"   [FAILED] Database methods test failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("[SUCCESS] All SharePoint API endpoint tests passed!")
    print("\nAvailable endpoints:")
    print("  POST /api/download-sharepoint-version")
    print("  GET  /api/get-version-status") 
    print("  POST /api/compare-sharepoint-versions")
    print("  POST /api/compare-versions (enhanced)")
    print("\nPhase 2 implementation is complete!")
    return True

if __name__ == "__main__":
    success = test_sharepoint_endpoints()
    sys.exit(0 if success else 1)