# Multi-Lab Support Implementation Summary

## Overview
The POC Helper Menu application has been updated to support multiple lab environments, allowing users to organize hosts and links by lab and work with them independently.

## Key Changes Made

### 1. Database Schema Updates (`models.py`)
- **Added Lab table**: New table to store lab information
  - `id`: Primary key
  - `lab_name`: Unique lab identifier
  - `description`: Optional lab description
- **Updated Host table**: Added `lab_name` foreign key field
- **Updated Link table**: Added `lab_name` foreign key field
- **Added relationships**: SQLAlchemy relationships between Lab, Host, and Link tables
- **Removed unique constraint**: Hostnames can now be duplicated across different labs

### 2. Main Menu Restructure (`main.py`)
- **Updated main menu**: 
  - Import Hosts
  - Import Links
  - Select Lab
  - Manage Labs
  - Exit
- **New lab selection workflow**: Users select labs before performing operations
- **Lab operations submenu**: Contains host connections, playbooks, interface management, and backups

### 3. Import Functions Enhanced
- **Host import functions** now require lab selection:
  - `import_inv_from_yaml(lab_name)`
  - `import_inv_from_ini(lab_name)`
  - `manually_add_host(lab_name)`
- **Link import functions** now require existing lab selection:
  - `import_links_from_containerlab(lab_name)`
- **Lab creation/selection**: Users can create new labs or select existing ones during import

### 4. New Lab Management Features
- **`get_or_create_lab()`**: Utility function for lab selection and creation
- **`create_new_lab()`**: Creates new labs with validation
- **`select_lab_menu()`**: Lab selection interface
- **`lab_operations_menu()`**: Lab-specific operations menu
- **`manage_labs_menu()`**: Lab management interface
- **`view_all_labs()`**: Display all labs with statistics
- **`rename_lab()`**: Rename existing labs
- **`delete_lab()`**: Delete labs and all associated data
- **`validate_lab_name()`**: Validates lab naming rules

### 5. Operations Updated for Lab Context
- **Host connections**: Filter by selected lab
- **Interface management**: Work only with links from selected lab
- **Configuration backups**: Work only with hosts from selected lab
- **Ansible playbooks**: Run in context of selected lab

### 6. Global State Management
- **`selected_lab`**: Global variable to track currently selected lab
- **Context-aware navigation**: Functions return to appropriate menus based on lab selection state

### 7. Enhanced Database Queries
- All database queries now filter by lab_name where appropriate
- Host and Link queries include lab context
- Improved error handling for lab-specific operations

### 8. Migration Support
- **`migrate_to_labs.py`**: Migration script for existing databases
- Creates default lab for existing data
- Updates database schema safely
- Preserves existing hosts and links

## Lab Naming Rules
- Only alphanumeric characters, underscores (_), and hyphens (-) allowed
- No spaces or special characters
- Must be unique across the system
- Cannot be empty

## User Workflow Changes

### Import Workflow
1. Select "Import Hosts" from main menu
2. Choose existing lab or create new lab
3. Select import method (YAML, INI, or manual)
4. Import hosts with lab association

### Link Import Workflow
1. Select "Import Links" from main menu
2. Choose from existing labs (requires hosts to exist first)
3. Import links with lab association

### Operations Workflow
1. Select "Select Lab" from main menu
2. Choose lab to work with
3. Access lab-specific operations:
   - Connect to hosts
   - Run Ansible playbooks
   - Interface management
   - Configuration backups

### Lab Management Workflow
1. Select "Manage Labs" from main menu
2. View, rename, or delete labs
3. See lab statistics (host/link counts)

## Backward Compatibility
- Migration script provided for existing installations
- Existing data moved to "default" lab
- All existing functionality preserved within lab context

## Files Modified
1. `models.py` - Database schema updates
2. `main.py` - Complete restructure with lab support
3. `README.md` - Updated documentation
4. `migrate_to_labs.py` - New migration script
5. `CHANGES.md` - This summary document

## Testing Recommendations
1. Run migration script on copy of existing database
2. Test import workflows with various file types
3. Verify lab isolation (operations only affect selected lab)
4. Test lab management functions (create, rename, delete)
5. Ensure all existing functionality works within lab context
