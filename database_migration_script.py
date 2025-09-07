"""
One-time Database Migration Script

This script migrates the following tables from a source database to a destination database:
- tracked_files
- file_versions
- alembic_version
- monitoring_log

Usage:
1. Edit the SOURCE_DB_CONNECTION_STRING and DEST_DB_CONNECTION_STRING variables below
2. Run the script: python database_migration_script.py
3. Check the migration log for any issues

IMPORTANT: 
- This script will CREATE tables in the destination database if they don't exist
- It will INSERT data, handling ID conflicts by updating existing records
- Always backup your destination database before running this script
"""

import pyodbc
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import sys
import os

# =============================================================================
# CONFIGURE YOUR CONNECTION STRINGS HERE
# =============================================================================

# Source database connection string (where data comes FROM)
SOURCE_DB_CONNECTION_STRING = "DRIVER={ODBC Driver 18 for SQL Server};SERVER=tcp:chatbotserver456.database.windows.net,1433;DATABASE=pocdb;UID=sqlserver;PWD=chatbot@123;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
# Example: "DRIVER={ODBC Driver 18 for SQL Server};SERVER=tcp:server1.database.windows.net,1433;DATABASE=sourcedb;UID=user;PWD=password;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"

# Destination database connection string (where data goes TO)
DEST_DB_CONNECTION_STRING = "DRIVER={ODBC Driver 18 for SQL Server};SERVER=tcp:chatbotserver456.database.windows.net,1433;DATABASE=sttmversion_db;UID=sqlserver;PWD=chatbot@123;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
# Example: "DRIVER={ODBC Driver 18 for SQL Server};SERVER=tcp:server2.database.windows.net,1433;DATABASE=destdb;UID=user;PWD=password;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"

# =============================================================================
# MIGRATION CONFIGURATION
# =============================================================================

# Set to True to actually perform the migration, False for dry-run
EXECUTE_MIGRATION = True

# Set to True to drop and recreate tables (DANGEROUS - will lose existing data)
DROP_EXISTING_TABLES = False

# Enable detailed logging
VERBOSE_LOGGING = True

# =============================================================================
# LOGGING SETUP
# =============================================================================

logging.basicConfig(
    level=logging.INFO if VERBOSE_LOGGING else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger('DatabaseMigration')

# =============================================================================
# MIGRATION CLASS
# =============================================================================

class DatabaseMigrator:
    """Handles migration between two SQL Server databases."""
    
    def __init__(self, source_conn_str: str, dest_conn_str: str):
        self.source_conn_str = source_conn_str
        self.dest_conn_str = dest_conn_str
        
        # Table definitions matching the SharePoint integration schema
        self.table_schemas = {
            'tracked_files': {
                'create_sql': '''
                    CREATE TABLE tracked_files (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        sharepoint_url NVARCHAR(2048) NOT NULL,
                        file_name NVARCHAR(255) NOT NULL,
                        friendly_name NVARCHAR(500) NULL,
                        drive_id NVARCHAR(255) NULL,
                        item_id NVARCHAR(255) NULL,
                        created_at DATETIME2 DEFAULT GETDATE(),
                        last_checked_at DATETIME2 NULL,
                        is_active BIT DEFAULT 1
                    )
                ''',
                'columns': ['id', 'sharepoint_url', 'file_name', 'friendly_name', 'drive_id', 'item_id', 'created_at', 'last_checked_at', 'is_active']
            },
            'file_versions': {
                'create_sql': '''
                    CREATE TABLE file_versions (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        file_id INT NOT NULL,
                        sequence_number INT NOT NULL,
                        sharepoint_version_id NVARCHAR(100) NOT NULL,
                        modified_datetime DATETIME2 NULL,
                        file_size_bytes BIGINT NULL,
                        discovered_at DATETIME2 DEFAULT GETDATE(),
                        diff_taken BIT DEFAULT 0,
                        diff_taken_at DATETIME2 NULL,
                        downloaded BIT DEFAULT 0,
                        download_filename NVARCHAR(1024) NULL,
                        downloaded_at DATETIME2 NULL,
                        download_error NTEXT NULL,
                        FOREIGN KEY (file_id) REFERENCES tracked_files(id)
                    )
                ''',
                'columns': ['id', 'file_id', 'sequence_number', 'sharepoint_version_id', 'modified_datetime', 'file_size_bytes', 'discovered_at', 'diff_taken', 'diff_taken_at', 'downloaded', 'download_filename', 'downloaded_at', 'download_error']
            },
            'alembic_version': {
                'create_sql': '''
                    CREATE TABLE alembic_version (
                        version_num VARCHAR(32) NOT NULL PRIMARY KEY
                    )
                ''',
                'columns': ['version_num']
            },
            'monitoring_log': {
                'create_sql': '''
                    CREATE TABLE monitoring_log (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        file_id INT NOT NULL,
                        check_timestamp DATETIME2 DEFAULT GETDATE(),
                        versions_found INT DEFAULT 0,
                        status NVARCHAR(50) NOT NULL,
                        error_message NTEXT NULL,
                        FOREIGN KEY (file_id) REFERENCES tracked_files(id)
                    )
                ''',
                'columns': ['id', 'file_id', 'check_timestamp', 'versions_found', 'status', 'error_message']
            }
        }
    
    def test_connections(self) -> bool:
        """Test both database connections."""
        logger.info("Testing database connections...")
        
        try:
            # Test source connection
            source_conn = pyodbc.connect(self.source_conn_str)
            source_cursor = source_conn.cursor()
            source_cursor.execute("SELECT 1")
            source_cursor.fetchone()
            source_conn.close()
            logger.info("✓ Source database connection successful")
            
            # Test destination connection
            dest_conn = pyodbc.connect(self.dest_conn_str)
            dest_cursor = dest_conn.cursor()
            dest_cursor.execute("SELECT 1")
            dest_cursor.fetchone()
            dest_conn.close()
            logger.info("✓ Destination database connection successful")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Connection test failed: {e}")
            return False
    
    def ensure_tables_exist(self) -> bool:
        """Create tables in destination database if they don't exist."""
        logger.info("Ensuring destination tables exist...")
        
        try:
            dest_conn = pyodbc.connect(self.dest_conn_str)
            dest_cursor = dest_conn.cursor()
            
            # Check and create tables in dependency order
            table_order = ['tracked_files', 'file_versions', 'monitoring_log', 'alembic_version']
            
            for table_name in table_order:
                # Check if table exists
                dest_cursor.execute("""
                    SELECT COUNT(*) 
                    FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_NAME = ?
                """, table_name)
                
                table_exists = dest_cursor.fetchone()[0] > 0
                
                if DROP_EXISTING_TABLES and table_exists:
                    # Drop table if requested
                    if table_name in ['file_versions', 'monitoring_log']:
                        logger.info(f"Dropping table {table_name}")
                        dest_cursor.execute(f"DROP TABLE {table_name}")
                        table_exists = False
                    elif table_name == 'tracked_files':
                        # Drop dependent tables first
                        logger.info("Dropping dependent tables before tracked_files")
                        try:
                            dest_cursor.execute("DROP TABLE file_versions")
                        except:
                            pass
                        try:
                            dest_cursor.execute("DROP TABLE monitoring_log")
                        except:
                            pass
                        dest_cursor.execute("DROP TABLE tracked_files")
                        table_exists = False
                
                if not table_exists:
                    logger.info(f"Creating table {table_name}")
                    dest_cursor.execute(self.table_schemas[table_name]['create_sql'])
                else:
                    logger.info(f"Table {table_name} already exists")
            
            dest_conn.commit()
            dest_conn.close()
            
            logger.info("✓ All destination tables are ready")
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to ensure tables exist: {e}")
            if 'dest_conn' in locals():
                dest_conn.rollback()
                dest_conn.close()
            return False
    
    def get_table_data(self, table_name: str) -> List[Dict[str, Any]]:
        """Extract data from source table."""
        logger.info(f"Extracting data from source table: {table_name}")
        
        try:
            source_conn = pyodbc.connect(self.source_conn_str)
            source_cursor = source_conn.cursor()
            
            columns = self.table_schemas[table_name]['columns']
            column_list = ', '.join(columns)
            
            source_cursor.execute(f"SELECT {column_list} FROM {table_name}")
            
            rows = []
            for row in source_cursor.fetchall():
                row_dict = {}
                for i, column in enumerate(columns):
                    value = row[i]
                    # Handle datetime and boolean conversions
                    if isinstance(value, str) and column.endswith('_at'):
                        try:
                            # Try to parse datetime string
                            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                        except:
                            pass
                    elif isinstance(value, str) and column in ['is_active', 'diff_taken', 'downloaded']:
                        # Convert string boolean to actual boolean
                        value = value.lower() in ['true', '1', 'yes']
                    elif isinstance(value, str) and column in ['id', 'file_id', 'sequence_number', 'file_size_bytes', 'versions_found']:
                        # Convert string numbers to int/bigint
                        try:
                            value = int(value)
                        except:
                            pass
                    
                    row_dict[column] = value
                rows.append(row_dict)
            
            source_conn.close()
            
            logger.info(f"✓ Extracted {len(rows)} rows from {table_name}")
            return rows
            
        except Exception as e:
            logger.error(f"✗ Failed to extract data from {table_name}: {e}")
            if 'source_conn' in locals():
                source_conn.close()
            return []
    
    def insert_table_data(self, table_name: str, data: List[Dict[str, Any]]) -> bool:
        """Insert data into destination table."""
        if not data:
            logger.info(f"No data to insert for table {table_name}")
            return True
        
        logger.info(f"Inserting {len(data)} rows into destination table: {table_name}")
        
        try:
            dest_conn = pyodbc.connect(self.dest_conn_str)
            dest_cursor = dest_conn.cursor()
            
            # Handle IDENTITY columns
            has_identity = table_name != 'alembic_version'  # alembic_version doesn't have IDENTITY
            
            if has_identity:
                dest_cursor.execute(f"SET IDENTITY_INSERT {table_name} ON")
            
            columns = self.table_schemas[table_name]['columns']
            placeholders = ', '.join(['?' for _ in columns])
            column_list = ', '.join(columns)
            
            insert_sql = f"INSERT INTO {table_name} ({column_list}) VALUES ({placeholders})"
            
            inserted_count = 0
            updated_count = 0
            error_count = 0
            
            for row in data:
                try:
                    # Prepare values in column order
                    values = []
                    for column in columns:
                        value = row.get(column)
                        
                        # Handle None values and type conversions
                        if value is None:
                            values.append(None)
                        elif column in ['is_active', 'diff_taken', 'downloaded'] and isinstance(value, str):
                            values.append(1 if value.lower() in ['true', '1', 'yes'] else 0)
                        elif column in ['is_active', 'diff_taken', 'downloaded'] and isinstance(value, bool):
                            values.append(1 if value else 0)
                        else:
                            values.append(value)
                    
                    # Try insert first
                    dest_cursor.execute(insert_sql, values)
                    inserted_count += 1
                    
                except pyodbc.IntegrityError as e:
                    if "PRIMARY KEY constraint" in str(e) or "UNIQUE constraint" in str(e):
                        # Record already exists, try to update it
                        try:
                            if table_name == 'alembic_version':
                                # For alembic_version, just update the version_num
                                update_sql = "UPDATE alembic_version SET version_num = ? WHERE version_num = ?"
                                dest_cursor.execute(update_sql, values[0], values[0])
                            else:
                                # For other tables, update all columns except ID
                                update_columns = [col for col in columns if col != 'id']
                                update_placeholders = ', '.join([f"{col} = ?" for col in update_columns])
                                update_values = [row.get(col) for col in update_columns]
                                
                                update_sql = f"UPDATE {table_name} SET {update_placeholders} WHERE id = ?"
                                dest_cursor.execute(update_sql, update_values + [row['id']])
                            
                            updated_count += 1
                        except Exception as update_error:
                            logger.warning(f"Failed to update row in {table_name}: {update_error}")
                            error_count += 1
                    else:
                        logger.warning(f"Insert error for row in {table_name}: {e}")
                        error_count += 1
                
                except Exception as e:
                    logger.warning(f"Unexpected error inserting row in {table_name}: {e}")
                    error_count += 1
            
            if has_identity:
                dest_cursor.execute(f"SET IDENTITY_INSERT {table_name} OFF")
            
            dest_conn.commit()
            dest_conn.close()
            
            logger.info(f"✓ {table_name}: {inserted_count} inserted, {updated_count} updated, {error_count} errors")
            
            return error_count == 0
            
        except Exception as e:
            logger.error(f"✗ Failed to insert data into {table_name}: {e}")
            if 'dest_conn' in locals():
                dest_conn.rollback()
                dest_conn.close()
            return False
    
    def migrate_table(self, table_name: str) -> bool:
        """Migrate a single table from source to destination."""
        logger.info(f"Migrating table: {table_name}")
        
        # Extract data from source
        data = self.get_table_data(table_name)
        if not data and table_name != 'alembic_version':
            logger.warning(f"No data found in source table {table_name}")
        
        # Insert data into destination
        if EXECUTE_MIGRATION:
            return self.insert_table_data(table_name, data)
        else:
            logger.info(f"DRY-RUN: Would insert {len(data)} rows into {table_name}")
            return True
    
    def run_migration(self) -> bool:
        """Run the complete migration process."""
        logger.info("=" * 60)
        logger.info("STARTING DATABASE MIGRATION")
        logger.info("=" * 60)
        
        if not SOURCE_DB_CONNECTION_STRING or not DEST_DB_CONNECTION_STRING:
            logger.error("✗ Please configure SOURCE_DB_CONNECTION_STRING and DEST_DB_CONNECTION_STRING")
            return False
        
        if not EXECUTE_MIGRATION:
            logger.warning("DRY-RUN MODE: No actual changes will be made")
        
        # Test connections
        if not self.test_connections():
            return False
        
        # Ensure destination tables exist
        if not self.ensure_tables_exist():
            return False
        
        # Migrate tables in dependency order
        migration_order = ['tracked_files', 'file_versions', 'monitoring_log', 'alembic_version']
        
        all_successful = True
        for table_name in migration_order:
            success = self.migrate_table(table_name)
            all_successful = all_successful and success
            
            if not success:
                logger.error(f"✗ Migration failed for table {table_name}")
            else:
                logger.info(f"✓ Migration completed for table {table_name}")
        
        logger.info("=" * 60)
        if all_successful:
            logger.info("✓ DATABASE MIGRATION COMPLETED SUCCESSFULLY!")
        else:
            logger.error("✗ DATABASE MIGRATION COMPLETED WITH ERRORS!")
        logger.info("=" * 60)
        
        return all_successful

# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main execution function."""
    
    print("Database Migration Script")
    print("=" * 60)
    
    # Validate configuration
    if not SOURCE_DB_CONNECTION_STRING:
        print("ERROR: SOURCE_DB_CONNECTION_STRING is not configured!")
        print("Please edit the script and set your source database connection string.")
        return False
    
    if not DEST_DB_CONNECTION_STRING:
        print("ERROR: DEST_DB_CONNECTION_STRING is not configured!")
        print("Please edit the script and set your destination database connection string.")
        return False
    
    # Confirm migration
    if EXECUTE_MIGRATION:
        print("WARNING: This will modify your destination database!")
        if DROP_EXISTING_TABLES:
            print("DANGER: DROP_EXISTING_TABLES is enabled - existing data will be lost!")
        
        confirm = input("Are you sure you want to proceed? (yes/no): ").lower().strip()
        if confirm != 'yes':
            print("Migration cancelled by user.")
            return False
    
    # Run migration
    migrator = DatabaseMigrator(SOURCE_DB_CONNECTION_STRING, DEST_DB_CONNECTION_STRING)
    return migrator.run_migration()

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\\n\\nMigration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)