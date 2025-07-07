# POC Helper Menu

A  Python-based terminal application for managing and connecting to network
devices across multiple lab environments. Supports both hardware labs and containerlab
environments with remote execution, interface management, and network impairments.

## Key Features

### Multi-Lab Support

- **Lab Organization**: Organize hosts and links by distinct lab environments
- **Lab Types**: Support for both hardware labs and containerlab environments
- **Lab Isolation**: Complete separation of hosts, links, and operations between labs
- **Lab Management**: Create, rename, delete, and configure lab settings

### Import & Discovery

- Import hosts from Ansible YAML or INI inventory files
- Import network topology and links from Containerlab YAML files
- **Remote Topology Scanning**: Automatically discover and import topology files from
remote containerlab hosts
- Manual host and link entry

### Connection Methods

- **SSH Connections**: Direct SSH to network devices and servers
- **Docker Exec**: Native containerlab container access (local and remote)
- **Console/Telnet**: Hardware device console access via telnet
- **Remote Execution**: Supports remote containerlab hosts

### Network Management

- **Interface Control**: Enable/disable network interfaces across lab topologies
- **Network Impairments**: Add latency, jitter, packet loss, rate limiting, and corruption
(containerlab)
- **Configuration Backup**: Automated device configuration backup with NAPALM integration
- **Ansible Integration**: Run Ansible playbooks directly from the interface

## Requirements

### Python Version

- **Python < 3.13** (Required due to telnetlib dependency in NAPALM)
  - NAPALM currently requires telnetlib, which was deprecated in Python 3.13
  - This requirement will be removed once NAPALM is updated

### Python Packages

- `PyYAML` - YAML file parsing
- `SQLAlchemy` - Database operations and ORM
- `simple-term-menu` - Terminal menu interface
- `tabulate` - Data table formatting
- `napalm` - Network device automation and configuration backup
- `netmiko` - For telnet connections to network devices

### System Utilities

- `sshpass` - SSH password authentication utility
- `ssh` and `scp` - Remote file operations and command execution

## Installation

1. **Clone the repository:**

    ```sh
    git clone https://github.com/marccolburn/poc_helper_menu.git
    cd poc_helper_menu
    ```

2. Create virtual environment

    ```sh
    python3.12 venv venv/
    source venv/bin/activate
    ```

3. **Install Python dependencies:**

    ```sh
    pip install -r requirements.txt
    ```

4. **Install sshpass:**

    ```sh
    # On Ubuntu/Debian
    sudo apt-get install sshpass
    
    # On RHEL/CentOS/Fedora
    sudo yum install sshpass  # or dnf install sshpass
    
    # On macOS
    brew install sshpass
    ```

## Architecture

### Core Modules

- **`main.py`** - Main application entry point and menu system
- **`models.py`** - SQLAlchemy database models and schema
- **`imports.py`** - Import functions for hosts and links
- **`lab_mgmt.py`** - Lab management operations (CRUD, settings)
- **`device_actions.py`** - Device connection and configuration backup functions
- **`interface_actions.py`** - Network interface management and impairment functions

### Database Schema

The application uses SQLite with three main tables:

#### Labs Table

- `lab_name` - Unique lab identifier
- `description` - Optional lab description
- `lab_type` - Either 'hardware' or 'containerlab'
- `remote_containerlab_host` - SSH hostname/IP for remote containerlab
- `remote_containerlab_username` - SSH username for remote access
- `topology_path` - Path to containerlab topology directory

#### Hosts Table

- `hostname` - Device hostname
- `ip_address` - Management IP address
- `network_os` - Network OS type (ios, eos, nxos, etc.)
- `username/password` - Authentication credentials
- `image_type` - Container image or device type
- `console` - Console/telnet address for hardware devices
- `lab_name` - Foreign key to parent lab

#### Links Table

- `source_host/destination_host` - Connected device hostnames
- `source_interface/destination_interface` - Connected interface names
- `state` - Interface state (enabled/disabled)
- `jitter/latency/loss/rate/corruption` - Network impairment values
- `lab_name` - Foreign key to parent lab

## Lab Management

### Lab Types

#### Hardware Labs

- Physical network devices
- Console/telnet access support
- Ansible inventory import
- Manual host configuration
- SSH-based connections

#### Containerlab Labs

- Container-based network simulation
- Docker exec access
- Topology YAML import
- Network impairment capabilities
- Local and remote execution support

### Lab Operations

- **Create Labs** - Set up new lab environments with type selection
- **Select Lab** - Choose active lab for operations
- **Manage Labs** - View, rename, delete, and configure lab settings

### Lab Configuration

#### Remote Containerlab Support

When creating a containerlab lab, you can configure:

- **Remote Host** - SSH hostname or IP of the containerlab server
- **SSH Username** - Username for remote authentication
- **Topology Path** - Directory path containing topology files

Remote capabilities include:

- Automatic topology file discovery and import
- Remote docker exec for container access
- Remote network impairment management
- Remote configuration backup

## Usage

### Getting Started

1. **Run the application:**

    ```sh
    python main.py
    ```

2. **Create or select a lab:**
   - Choose "Create Lab" to set up a new environment
   - Select lab type (hardware or containerlab)
   - Configure remote settings if using containerlab

3. **Import hosts and topology:**
   - For hardware labs: Import from Ansible YAML/INI files
   - For containerlab: Import from topology YAML files
   - Support for both local and remote file sources

### Main Menu Options

- **Select Lab** - Choose active lab environment
- **Create Lab** - Set up new lab with guided configuration
- **Manage Labs** - Lab administration and settings
- **Exit** - Close the application

### Lab Operations Menu

Once a lab is selected, you can:

- **Connect to Host** - SSH or docker exec to devices
- **View and Run Ansible Playbooks** - Execute automation scripts
- **Interface Management** - Control interfaces and containerlab impairments
- **Backup Device Configurations** - Save device configs via NAPALM

### Connection Types

#### SSH Connections

- Direct SSH access to network devices and servers

#### Docker Exec (Containerlab)

- Linux container access for containerlab environments
- Supports both local and remote containerlab hosts

#### Console/Telnet Access

- Hardware device console access via telnet
- Implemented using Netmiko's telnetlib library(because of 3.13 telnetlib deprecation)
- Supports hostname:port and plain hostname formats

### Network Interface Management

#### Interface Control

- Enable/disable network interfaces across lab topologies
- Support for both hardware and containerlab environments

#### Network Impairments (Containerlab Only)

- **Latency** - Add network delay in milliseconds
- **Jitter** - Add variable delay for realistic simulation
- **Packet Loss** - Simulate packet drops as percentage
- **Rate Limiting** - Bandwidth throttling in kbit/s
- **Packet Corruption** - Simulate data corruption

### Configuration Management

#### Device Configuration Backup

- Config backup using NAPALM
- Support for multiple network OS types
- Local and remote containerlab directory backup
- Individual or bulk device operations

#### Ansible Integration

- Direct playbook execution from the interface
- File preview and selection capabilities
- Argument passing and execution feedback

## Advanced Features

### Remote Topology Discovery

- Automatic scanning of remote containerlab hosts
- Topology file discovery and selection

## Troubleshooting

### Python Version Issues

If you encounter telnetlib-related errors, ensure you're using Python < 3.13:

```sh
python --version  # Should be < 3.13
```

### SSH Key Authentication

For remote containerlab access, ensure SSH key authentication is configured:

```sh
ssh-copy-id username@remote-host
```

### Missing Dependencies Warning or SSH fails

Install sshpass:

```sh
# Ubuntu/Debian
sudo apt-get update && sudo apt-get install sshpass

# RHEL/CentOS/Fedora  
sudo dnf install sshpass

# macOS
brew install sshpass
```

## SSH Key Setup for Seamless Remote Access

For the best user experience, it's recommended to set up SSH key authentication and
passwordless sudo for containerlab commands. Thiseliminates password prompts for a
smoother demo experience.

### 1. Generate SSH Key Pair

On your local machine (where POC Helper Menu runs):

```sh
# Generate a new SSH key pair (use your email address)
ssh-keygen -t ed25519 -C "your.email@company.com"

# When prompted for file location, press Enter for default (~/.ssh/id_ed25519)
# When prompted for passphrase, press Enter for no passphrase (recommended for demos)
```

**Alternative for systems that don't support ed25519:**

```sh
ssh-keygen -t rsa -b 4096 -C "your.email@company.com"
```

### 2. Copy SSH Key to Remote Containerlab Host

```sh
# Copy your public key to the remote containerlab server
ssh-copy-id username@remote-containerlab-host
```

**Manual method (if ssh-copy-id is not available):**

```sh
# Display your public key
cat ~/.ssh/id_ed25519.pub

# On the remote host, add the key to authorized_keys
mkdir -p ~/.ssh
echo "your-public-key-content" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
```

### 3. Test SSH Key Authentication

```sh
# Test passwordless SSH connection
ssh username@remote-containerlab-host

# You should connect without being prompted for a password
```

### 4. Configure Passwordless Sudo for Containerlab

On the **remote containerlab host**, configure sudo to allow passwordless execution of
containerlab commands:

```sh
# Edit the sudoers file (always use visudo for safety)
sudo visudo

# Add this line at the end of the file:

# Allow only containerlab commands without password (more secure)
username ALL=(ALL) NOPASSWD: /usr/bin/containerlab, /usr/local/bin/containerlab
```

**Replace `username` with your actual username on the remote host.**

### 5. Test Complete Setup

Test that both SSH keys and passwordless sudo work together:

```sh
# Test remote containerlab command execution
ssh username@remote-host "sudo containerlab version"

# This should execute without any password prompts
```

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
