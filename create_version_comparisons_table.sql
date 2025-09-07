-- Create version_comparisons table for storing comparison results
-- This table stores the results and metadata of Excel version comparisons

CREATE TABLE version_comparisons (
    -- Primary Key
    id INT IDENTITY(1,1) PRIMARY KEY,
    
    -- Foreign Keys to file_versions table
    file1_version_id INT NOT NULL,
    file2_version_id INT NOT NULL,
    
    -- Comparison Metadata
    comparison_title NVARCHAR(500) NULL,
    comparison_status NVARCHAR(50) NOT NULL DEFAULT 'completed',
    
    -- Results Storage (URLs and Local Paths)
    html_report_url NVARCHAR(2048) NULL,
    json_report_url NVARCHAR(2048) NULL,
    local_html_path NVARCHAR(1024) NULL,
    local_json_path NVARCHAR(1024) NULL,
    
    -- Summary Statistics from Comparison
    total_changes INT DEFAULT 0,
    added_mappings INT DEFAULT 0,
    modified_mappings INT DEFAULT 0,
    deleted_mappings INT DEFAULT 0,
    tabs_compared INT DEFAULT 0,
    
    -- Processing Information
    comparison_duration_seconds DECIMAL(10,3) NULL,
    comparison_taken_at DATETIME2 DEFAULT GETDATE(),
    created_at DATETIME2 DEFAULT GETDATE(),
    
    -- Additional Metadata
    user_notes NTEXT NULL,
    is_archived BIT DEFAULT 0,
    
    -- Foreign Key Constraints
    CONSTRAINT FK_version_comparisons_file1 
        FOREIGN KEY (file1_version_id) REFERENCES file_versions(id),
    CONSTRAINT FK_version_comparisons_file2 
        FOREIGN KEY (file2_version_id) REFERENCES file_versions(id)
);

-- Create Indexes for Performance
CREATE INDEX IX_version_comparisons_file_versions 
    ON version_comparisons (file1_version_id, file2_version_id);
    
CREATE INDEX IX_version_comparisons_datetime 
    ON version_comparisons (comparison_taken_at);
    
CREATE INDEX IX_version_comparisons_status 
    ON version_comparisons (comparison_status);

-- Add a check constraint to ensure file1_version_id != file2_version_id
ALTER TABLE version_comparisons 
ADD CONSTRAINT CK_version_comparisons_different_versions 
CHECK (file1_version_id != file2_version_id);

-- Add sample comment for documentation
EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'Stores results and metadata of Excel version comparisons including Azure blob URLs and summary statistics', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'version_comparisons';

PRINT 'version_comparisons table created successfully with indexes and constraints';