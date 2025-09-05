"""
Database Test Module - Inspect table data and test connection
"""

import os
import pyodbc
from dotenv import load_dotenv
from datetime import datetime
import traceback

# Load environment variables
load_dotenv()

class DatabaseTester:
    def __init__(self):
        self.connection_string = os.getenv("DATABASE_URL")
        if not self.connection_string:
            raise ValueError("DATABASE_URL environment variable is required")
    
    def test_connection(self):
        """Test basic database connection"""
        print("=" * 60)
        print("TESTING DATABASE CONNECTION")
        print("=" * 60)
        
        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()
            
            # Test basic query
            cursor.execute("SELECT @@VERSION")
            version = cursor.fetchone()[0]
            print(f"[SUCCESS] Connection successful!")
            print(f"[INFO] Server version: {version[:100]}...")
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"[ERROR] Connection failed: {e}")
            return False
    
    def inspect_tracked_files(self):
        """Inspect tracked_files table data"""
        print("\n" + "=" * 60)
        print("📋 TRACKED_FILES TABLE DATA")
        print("=" * 60)
        
        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()
            
            # Get table structure
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'tracked_files'
                ORDER BY ORDINAL_POSITION
            """)
            
            print("\n📝 Table Structure:")
            print("-" * 40)
            for row in cursor.fetchall():
                nullable = "NULL" if row.IS_NULLABLE == "YES" else "NOT NULL"
                max_len = f"({row.CHARACTER_MAXIMUM_LENGTH})" if row.CHARACTER_MAXIMUM_LENGTH else ""
                print(f"  {row.COLUMN_NAME}: {row.DATA_TYPE}{max_len} {nullable}")
            
            # Get record count
            cursor.execute("SELECT COUNT(*) FROM tracked_files")
            total_count = cursor.fetchone()[0]
            print(f"\n📊 Total records: {total_count}")
            
            if total_count == 0:
                print("⚠️  No records found in tracked_files table")
                conn.close()
                return
            
            # Get active records count
            cursor.execute("SELECT COUNT(*) FROM tracked_files WHERE is_active = 1")
            active_count = cursor.fetchone()[0]
            print(f"📊 Active records: {active_count}")
            
            # Show first 5 records
            cursor.execute("""
                SELECT TOP 5 
                    id, 
                    sharepoint_url, 
                    file_name, 
                    friendly_name, 
                    is_active,
                    created_at
                FROM tracked_files 
                ORDER BY id
            """)
            
            print(f"\n📋 First 5 records:")
            print("-" * 40)
            for row in cursor.fetchall():
                print(f"ID: {row.id}")
                print(f"  SharePoint URL: {row.sharepoint_url[:50]}..." if row.sharepoint_url and len(row.sharepoint_url) > 50 else f"  SharePoint URL: {row.sharepoint_url}")
                print(f"  File Name: {row.file_name}")
                print(f"  Friendly Name: {row.friendly_name}")
                print(f"  Active: {row.is_active}")
                print(f"  Created: {row.created_at}")
                print()
            
            # Show unique friendly names for testing
            cursor.execute("""
                SELECT DISTINCT friendly_name 
                FROM tracked_files 
                WHERE friendly_name IS NOT NULL AND is_active = 1
                ORDER BY friendly_name
            """)
            
            friendly_names = [row.friendly_name for row in cursor.fetchall()]
            print(f"🏷️  Available friendly names for testing:")
            print("-" * 40)
            if friendly_names:
                for name in friendly_names:
                    print(f"  - '{name}'")
            else:
                print("  ⚠️  No friendly names found")
            
            conn.close()
            return friendly_names
            
        except Exception as e:
            print(f"❌ Error inspecting tracked_files: {e}")
            traceback.print_exc()
            return []
    
    def inspect_file_versions(self, file_id=None):
        """Inspect file_versions table data"""
        print("\n" + "=" * 60)
        print("📋 FILE_VERSIONS TABLE DATA")
        print("=" * 60)
        
        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()
            
            # Get table structure
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'file_versions'
                ORDER BY ORDINAL_POSITION
            """)
            
            print("\n📝 Table Structure:")
            print("-" * 40)
            for row in cursor.fetchall():
                nullable = "NULL" if row.IS_NULLABLE == "YES" else "NOT NULL"
                max_len = f"({row.CHARACTER_MAXIMUM_LENGTH})" if row.CHARACTER_MAXIMUM_LENGTH else ""
                print(f"  {row.COLUMN_NAME}: {row.DATA_TYPE}{max_len} {nullable}")
            
            # Get record count
            cursor.execute("SELECT COUNT(*) FROM file_versions")
            total_count = cursor.fetchone()[0]
            print(f"\n📊 Total versions: {total_count}")
            
            if total_count == 0:
                print("⚠️  No records found in file_versions table")
                conn.close()
                return
            
            # Get downloaded versions count
            cursor.execute("SELECT COUNT(*) FROM file_versions WHERE downloaded = 1")
            downloaded_count = cursor.fetchone()[0]
            print(f"📊 Downloaded versions: {downloaded_count}")
            
            # Show first 5 records with file info
            query = """
                SELECT TOP 5 
                    fv.id,
                    fv.file_id,
                    tf.friendly_name,
                    tf.file_name,
                    fv.sequence_number,
                    fv.last_modified_datetime,
                    fv.downloaded,
                    fv.download_filename,
                    fv.file_size_bytes
                FROM file_versions fv
                JOIN tracked_files tf ON fv.file_id = tf.id
                ORDER BY fv.file_id, fv.sequence_number DESC
            """
            
            cursor.execute(query)
            
            print(f"\n📋 First 5 versions with file info:")
            print("-" * 40)
            for row in cursor.fetchall():
                print(f"Version ID: {row.id}")
                print(f"  File ID: {row.file_id}")
                print(f"  Friendly Name: {row.friendly_name}")
                print(f"  File Name: {row.file_name}")
                print(f"  Sequence: {row.sequence_number}")
                print(f"  Modified: {row.last_modified_datetime}")
                print(f"  Downloaded: {row.downloaded}")
                print(f"  Download Path: {row.download_filename}")
                print(f"  Size: {row.file_size_bytes} bytes")
                print()
            
            # Show files with multiple versions
            cursor.execute("""
                SELECT 
                    tf.friendly_name,
                    tf.file_name,
                    COUNT(fv.id) as version_count,
                    SUM(CASE WHEN fv.downloaded = 1 THEN 1 ELSE 0 END) as downloaded_count
                FROM tracked_files tf
                JOIN file_versions fv ON tf.id = fv.file_id
                WHERE tf.is_active = 1
                GROUP BY tf.id, tf.friendly_name, tf.file_name
                ORDER BY version_count DESC
            """)
            
            print(f"📊 Files with version counts:")
            print("-" * 40)
            for row in cursor.fetchall():
                print(f"  {row.friendly_name or row.file_name}: {row.version_count} versions ({row.downloaded_count} downloaded)")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ Error inspecting file_versions: {e}")
            traceback.print_exc()
    
    def test_join_query(self, identifier=""):
        """Test the actual join query used in the API"""
        print("\n" + "=" * 60)
        print(f"🔍 TESTING JOIN QUERY (identifier: '{identifier}')")
        print("=" * 60)
        
        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()
            
            # Test the actual query used in API
            query = """
            SELECT 
                tf.id as file_id,
                tf.sharepoint_url,
                tf.file_name,
                tf.friendly_name,
                fv.id as version_id,
                fv.sequence_number,
                fv.sharepoint_version_id,
                fv.last_modified_datetime,
                fv.file_size_bytes,
                fv.downloaded,
                fv.download_filename
            FROM tracked_files tf
            JOIN file_versions fv ON tf.id = fv.file_id
            WHERE (tf.friendly_name LIKE ? OR tf.file_name LIKE ?) AND tf.is_active = 1
            ORDER BY fv.sequence_number DESC
            """
            
            search_pattern = f"%{identifier}%"
            cursor.execute(query, (search_pattern, search_pattern))
            
            results = cursor.fetchall()
            print(f"📊 Found {len(results)} matching records")
            
            if results:
                print("\n📋 Matching records:")
                print("-" * 40)
                for row in results:
                    print(f"File ID: {row.file_id}")
                    print(f"  Friendly Name: {row.friendly_name}")
                    print(f"  File Name: {row.file_name}")
                    print(f"  Version ID: {row.version_id}")
                    print(f"  Sequence: {row.sequence_number}")
                    print(f"  Downloaded: {row.downloaded}")
                    print()
            else:
                print("⚠️  No matching records found")
                print(f"   Search pattern was: '%{identifier}%'")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ Error testing join query: {e}")
            traceback.print_exc()
    
    def run_full_inspection(self):
        """Run complete database inspection"""
        print("🚀 STARTING FULL DATABASE INSPECTION")
        print("=" * 60)
        
        # Test connection
        if not self.test_connection():
            return
        
        # Inspect tables
        friendly_names = self.inspect_tracked_files()
        self.inspect_file_versions()
        
        # Test with actual data
        if friendly_names:
            test_name = friendly_names[0]
            self.test_join_query(test_name)
        else:
            # Test with empty search (should return all records)
            self.test_join_query("")
        
        print("\n✅ Database inspection completed!")
        print("📝 Use the friendly names above to test the API endpoints")


if __name__ == "__main__":
    try:
        tester = DatabaseTester()
        tester.run_full_inspection()
        
        print("\n" + "=" * 60)
        print("🧪 SUGGESTED API TESTS")
        print("=" * 60)
        print("1. Health check: GET http://localhost:8000/api/health")
        print("2. Test with found friendly names above:")
        print("   GET http://localhost:8000/api/files/versions?identifier=FRIENDLY_NAME&search_type=name")
        print("3. Test broad search:")
        print("   GET http://localhost:8000/api/files/versions?identifier=&search_type=name")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        traceback.print_exc()