"""Device connection and configuration backup functions for the POC Helper Menu tool."""

import getpass
import os
import subprocess
import tempfile
import threading
import time
import sys
import select
from datetime import datetime
from pathlib import Path
from netmiko._telnetlib import telnetlib
from napalm import get_network_driver
from models import Host, Link, Lab, session
import warnings
# This is to suppress the deprecation warning from pkg_resources being used by NAPALM
# until NAPALM fixes it in their codebase.
warnings.filterwarnings("ignore", message="pkg_resources is deprecated")


# NAPALM driver mapping for configuration backup
NETWORK_OS_TO_NAPALM_DRIVER = {
    'eos': 'eos',
    'ios': 'ios',
    'nxos': 'nxos',
    'iosxr': 'iosxr',
    'junos': 'junos',
}


def connect_to_host(hostname, command=None):
    """Function to connect to a host via SSH or docker exec for containerlab Linux containers."""
    import lab_mgmt
    
    # Query info about host from the database
    host = None
    selected_lab = lab_mgmt.get_selected_lab()
    if selected_lab:
        host = session.query(Host).filter_by(hostname=hostname, lab_name=selected_lab).first()
    else:
        host = session.query(Host).filter_by(hostname=hostname).first()
    
    if host:
        # Get lab info to determine connection method
        lab = session.query(Lab).filter_by(lab_name=host.lab_name).first()
        
        # Use docker exec for Linux containers in containerlab
        if (lab and lab.lab_type == "containerlab" and 
            host.image_type == "linux"):
            connect_to_containerlab_host(host, lab, command)
        else:
            # Use SSH for hardware labs or non-Linux containers
            print(f"Connecting to {hostname} via SSH...")
            try:
                username = (
                    host.username
                    if host.username
                    else input(f"Enter username for {hostname}: ").strip()
                )
                password = (
                    host.password
                    if host.password
                    else getpass.getpass(
                        prompt=f"Enter password for {username}@{host.ip_address}: "
                    )
                )
                ssh_command = (
                    f"sshpass -p '{password}' ssh "
                    f"-o StrictHostKeyChecking=no "
                    f"-o UserKnownHostsFile=/dev/null "
                    f"{username}@{host.ip_address}"
                )
                if command:
                    ssh_command += f" '{command}'"
                subprocess.run(ssh_command, shell=True, check=True)
            except Exception as e:
                print(f"Failed to connect: {e}")
    else:
        print(f"Host {hostname} not found in the database.")
        username = input(f"Enter username for {hostname}: ").strip()
        password = getpass.getpass(
            prompt=f"Enter password for {username}@{hostname}: "
        )
        ip_address = input(f"Enter IP address for {hostname}: ").strip()
        ssh_command = (
            f"sshpass -p '{password}' "
            f"ssh -o StrictHostKeyChecking=no "
            f"-o UserKnownHostsFile=/dev/null {username}@{ip_address}"
        )
        if command:
            ssh_command += f" '{command}'"
        try:
            subprocess.run(ssh_command, shell=True, check=False)
        except Exception as e:
            print(f"Failed to connect: {e}")


def connect_to_containerlab_host(host, lab, command=None):
    """Connect to a containerlab Linux container using docker exec."""
    container_name = host.hostname
    
    if command:
        # Execute a specific command
        docker_command = f"docker exec {container_name} {command}"
    else:
        # Interactive shell
        docker_command = f"docker exec -it {container_name} /bin/bash"
    
    if lab.remote_containerlab_host:
        # Remote execution
        username_part = f"{lab.remote_containerlab_username}@" if lab.remote_containerlab_username else ""
        remote_host = f"{username_part}{lab.remote_containerlab_host}"
        
        print(f"Connecting to container {container_name} on remote host {remote_host}...")
        
        if command:
            # For non-interactive commands, use our remote execution helper
            success = execute_remote_command(
                lab.remote_containerlab_host,
                lab.remote_containerlab_username,
                docker_command,
                f"container command on {container_name}"
            )
            if not success:
                print(f"Failed to execute command on remote container {container_name}")
        else:
            # For interactive shell, need to use SSH with -t flag
            remote_command = f"ssh -t {remote_host} '{docker_command}'"
            
            # Try SSH key authentication first
            try:
                result = subprocess.run(remote_command, shell=True, check=False)
                if result.returncode != 0:
                    # SSH key failed, try with password
                    print("SSH key authentication failed, trying password authentication...")
                    password = getpass.getpass(f"Enter password for {remote_host}: ")
                    remote_command_with_pass = f"sshpass -p '{password}' \
                        ssh -t -o StrictHostKeyChecking=no {remote_host} '{docker_command}'"
                    subprocess.run(remote_command_with_pass, shell=True, check=False)
            except Exception as e:
                print(f"Failed to connect to remote container: {e}")
    else:
        # Local execution
        print(f"Connecting to container {container_name} locally...")
        try:
            subprocess.run(docker_command, shell=True, check=False)
        except Exception as e:
            print(f"Failed to connect to container: {e}")


def connect_to_console(host):
    """
    Connect to a hardware device console using telnet via netmiko.
    
    has custom exit handling because ctrl + ] doesn't work in some terminals.
    """
    
    if not host.console:
        print(f"No console address configured for host {host.hostname}")
        input("Press Enter to continue...")
        return
    
    # Parse console address - it might be host:port
    console_parts = host.console.split(':')
    if len(console_parts) == 2:
        console_host = console_parts[0]
        console_port = int(console_parts[1])
    else:
        console_host = host.console
        console_port = 23  # Default telnet port
    
    print(f"Connecting to console {console_host}:{console_port} for {host.hostname}...")
    
    try:
        tn = telnetlib.Telnet()
        tn.open(console_host, console_port, timeout=10)
        print(f"Connected to {console_host}:{console_port}")
        print("=" * 50)
        print("TELNET CONSOLE SESSION")
        print("Multiple ways to exit:")
        print("1. Type 'QUIT' on a new line")
        print("2. Press Ctrl+C to interrupt")
        print("3. Use Ctrl+] then type 'quit' at telnet prompt")
        print("=" * 50)
        
        # Custom interactive session with better exit handling
        
        # Flag to control the session
        session_active = True
        
        def read_from_telnet():
            """Read data from telnet connection and display it."""
            while session_active:
                try:
                    # Use a short timeout for non-blocking reads
                    data = tn.read_very_eager()
                    if data:
                        sys.stdout.write(data.decode('utf-8', errors='ignore'))
                        sys.stdout.flush()
                    else:
                        time.sleep(0.01)  # Small delay to prevent high CPU usage
                except Exception:
                    break
        
        # Start the read thread
        read_thread = threading.Thread(target=read_from_telnet, daemon=True)
        read_thread.start()
        
        try:
            while session_active:
                # Check if there's input available
                if sys.stdin in select.select([sys.stdin], [], [], 0.1)[0]:
                    user_input = sys.stdin.readline()
                    
                    # Check for exit commands
                    if user_input.strip().upper() == 'QUIT':
                        print("\nExiting telnet session...")
                        session_active = False
                        break
                    
                    # Send input to telnet connection
                    tn.write(user_input.encode('utf-8'))
                
        except KeyboardInterrupt:
            print("\nTelnet session interrupted by user (Ctrl+C)")
            session_active = False
        except Exception as e:
            print(f"\nTelnet session error: {e}")
            session_active = False
        
        # Clean up
        session_active = False
        time.sleep(0.1)  # Give read thread time to exit
        
    except Exception as e:
        print(f"Failed to connect to {console_host}:{console_port}: {e}")
        input("Press Enter to continue...")
    finally:
        try:
            tn.close()
        except:
            pass
        print("\nTelnet session closed.")


def execute_remote_command(remote_host, remote_username, command, description="command"):
    """
    Execute a command on a remote host with SSH key or password authentication.
    
    """
    username_part = f"{remote_username}@" if remote_username else ""
    remote_target = f"{username_part}{remote_host}"
    
    # Try SSH key authentication first
    remote_command = (
        f"ssh -o PasswordAuthentication=no -o ConnectTimeout=10 {remote_target} '{command}'"
    )
    print(f"Executing {description} remotely on {remote_target}: {command}")
    
    try:
        result = (
            subprocess.run(remote_command, shell=True, check=False, capture_output=True, text=True)
        )
        if result.returncode == 0:
            print(f"Remote {description} executed successfully.")
            return True
        else:
            # SSH key failed, try with password authentication
            print("SSH key authentication failed, trying password authentication...")
            password = getpass.getpass(f"Enter password for {remote_target}: ")
            remote_command_with_pass = (
                f"sshpass -p '{password}' ssh -o StrictHostKeyChecking=no {remote_target} '{command}'"
            )
            result = subprocess.run(remote_command_with_pass, shell=True, check=False)
            if result.returncode == 0:
                print(f"Remote {description} executed successfully.")
                return True
            else:
                print(f"Failed to execute remote {description} with password authentication.")
                return False
    except Exception as e:
        print(f"Failed to execute remote {description}: {e}")
        return False


def backup_host_config(host, backup_dir=None):
    """Function to backup the configuration of a host using NAPALM."""
    print(f"Backing up configuration of {host.hostname}...")
    
    # Default backup directory
    if not backup_dir:
        backup_dir = f"{host.lab_name}_config_backup"
    
    # Ensure backup directory exists
    try:
        os.makedirs(backup_dir, exist_ok=True)
    except Exception as e:
        print(f"Failed to create backup directory {backup_dir}: {e}")
        return False
    
    # Get NAPALM driver
    napalm_driver_name = NETWORK_OS_TO_NAPALM_DRIVER.get(host.network_os)
    if not napalm_driver_name:
        print(f"No NAPALM driver found for network OS '{host.network_os}'. Skipping {host.hostname}.")
        return False
    
    try:
        # Get NAPALM driver class
        driver = get_network_driver(napalm_driver_name)
        
        # Create device connection
        device = driver(
            hostname=host.ip_address,
            username=host.username,
            password=host.password,
            optional_args={'port': 22}  # Default SSH port
        )
        
        # Connect to device
        print(f"Connecting to {host.hostname} ({host.ip_address})...")
        device.open()
        
        # Get configuration
        config_dict = device.get_config()
        running_config = config_dict.get("running", "")
        
        if not running_config:
            print(f"No running configuration retrieved for {host.hostname}")
            device.close()
            return False
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"{host.hostname}_{timestamp}.txt"
        filepath = os.path.join(backup_dir, filename)
        
        # Save configuration
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(running_config)
        
        print(f"Configuration backed up to {filepath}")
        device.close()
        return True
        
    except Exception as e:
        print(f"Failed to backup configuration for {host.hostname}: {e}")
        try:
            device.close()
        except:
            pass
        return False


def backup_all_hosts():
    """Backup configurations for all hosts in the selected lab."""
    import lab_mgmt
    
    selected_lab = lab_mgmt.get_selected_lab()
    hosts = session.query(Host).filter_by(lab_name=selected_lab).all()
    
    if not hosts:
        print(f"No hosts found in lab '{selected_lab}'.")
        return False
    
    print(f"Starting backup for all hosts in lab '{selected_lab}'...")
    successful_backups = 0
    failed_backups = 0
    
    for host in hosts:
        if backup_host_config(host):
            successful_backups += 1
        else:
            failed_backups += 1
    
    print(f"\nBackup completed. Successful: {successful_backups}, Failed: {failed_backups}")
    return True


def backup_to_containerlab_directory():
    """Backup configurations to containerlab topology directory structure."""
    import lab_mgmt
    
    selected_lab = lab_mgmt.get_selected_lab()
    lab = session.query(Lab).filter_by(lab_name=selected_lab).first()
    if not lab or not lab.topology_path:
        print("Containerlab topology path not configured for this lab.")
        return False
    
    # Check if topology path exists and find containerlab directory
    if lab.remote_containerlab_host:
        # For remote labs, the topology path is on the remote machine
        topology_path_str = lab.topology_path
        username_part = (
            f"{lab.remote_containerlab_username}@" if lab.remote_containerlab_username else ""
        )
        # Check if the remote path exists
        check_command = (
            f"ssh {username_part}{lab.remote_containerlab_host} 'test -d \"{topology_path_str}\"'"
        )
        result = subprocess.run(check_command, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Topology path does not exist on remote host: {topology_path_str}")
            return
    else:
        # For local labs, expand and resolve the path locally
        topology_path = Path(lab.topology_path).expanduser().resolve()
        if not topology_path.exists():
            print(f"Topology path does not exist: {topology_path}")
            return
    
    # Find containerlab directory (contains "clab" in name)
    if lab.remote_containerlab_host:
        # Remote operation - find directories containing "clab"
        list_command = f"find '{topology_path_str}' -maxdepth 1 -type d -name '*clab*'"
        result = subprocess.run(
            f"ssh {username_part}{lab.remote_containerlab_host} \"{list_command}\"",
            shell=True, capture_output=True, text=True
        )
        
        if result.returncode != 0:
            print("Failed to list directories on remote host.")
            return
        
        clab_dirs_output = result.stdout.strip()
        if not clab_dirs_output:
            print("No containerlab directory (containing 'clab') found in the remote path.")
            return
        
        clab_dirs = clab_dirs_output.split('\n')
        if len(clab_dirs) > 1:
            print("Multiple containerlab directories found. Using the first one.")
        
        clab_dir_path = clab_dirs[0]
        
    else:
        # Local operation - find directories containing "clab"
        clab_dirs = [d for d in topology_path.iterdir() if d.is_dir() and "clab" in d.name]
        if not clab_dirs:
            print("No containerlab directory (containing 'clab') found in the specified path.")
            return
        
        if len(clab_dirs) > 1:
            print("Multiple containerlab directories found. Using the first one.")
        
        clab_dir_path = str(clab_dirs[0])
    
    print(f"Found containerlab directory: {clab_dir_path}")
    print(f"Backing up configurations to containerlab directory: {clab_dir_path}")
    
    hosts = session.query(Host).filter_by(lab_name=selected_lab).all()
    successful_backups = 0
    failed_backups = 0
    
    for host in hosts:
        if lab.remote_containerlab_host:
            # For remote labs, we need to use a different approach
            # Create the node config directory remotely
            node_config_dir = f"{clab_dir_path}/{host.hostname}/config"
            mkdir_command = (
                f"ssh {username_part}{lab.remote_containerlab_host} \
                'mkdir -p \"{node_config_dir}\"'"
            )
            subprocess.run(mkdir_command, shell=True, check=False)
            
            # Backup configuration and upload to remote
            with tempfile.NamedTemporaryFile(mode='w', suffix='.cfg', delete=False) as temp_file:
                if backup_host_config_to_file(host, temp_file.name):
                    # Copy to remote location
                    remote_config_file = f"{node_config_dir}/startup-config.cfg"
                    scp_command = (
                        f"scp '{temp_file.name}' {username_part}{lab.remote_containerlab_host}:\
                        '{remote_config_file}'"
                    )

                    result = subprocess.run(scp_command, shell=True, check=False)
                    if result.returncode == 0:
                        successful_backups += 1
                        print(f"Configuration for {host.hostname} copied to remote location")
                    else:
                        failed_backups += 1
                        print(f"Failed to copy configuration for {host.hostname} to remote location")
                else:
                    failed_backups += 1
                
                # Clean up temp file
                os.unlink(temp_file.name)
        else:
            # Local operation
            node_config_dir = Path(clab_dir_path) / host.hostname / "config"
            node_config_dir.mkdir(parents=True, exist_ok=True)
            
            config_file = node_config_dir / "startup-config.cfg"
            
            if backup_host_config_to_file(host, str(config_file)):
                successful_backups += 1
            else:
                failed_backups += 1
    
    print(f"\nContainerlab backup completed. Successful: {successful_backups}, Failed: {failed_backups}")
    return True


def backup_host_config_to_file(host, filepath):
    """Backup host configuration to a specific file path."""
    print(f"Backing up {host.hostname} to {filepath}...")
    
    # Get NAPALM driver
    napalm_driver_name = NETWORK_OS_TO_NAPALM_DRIVER.get(host.network_os)
    if not napalm_driver_name:
        print(f"No NAPALM driver found for network OS '{host.network_os}'. Skipping {host.hostname}.")
        return False
    
    try:
        # Get NAPALM driver class
        driver = get_network_driver(napalm_driver_name)
        
        # Create device connection
        device = driver(
            hostname=host.ip_address,
            username=host.username,
            password=host.password,
            optional_args={'port': 22}
        )
        
        # Connect to device
        device.open()
        
        # Get configuration
        config_dict = device.get_config()
        running_config = config_dict.get("running", "")
        
        if not running_config:
            print(f"No running configuration retrieved for {host.hostname}")
            device.close()
            return False
        
        # Save configuration to specified file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(running_config)
        
        print(f"Configuration backed up to {filepath}")
        device.close()
        return True
        
    except Exception as e:
        print(f"Failed to backup configuration for {host.hostname}: {e}")
        try:
            device.close()
        except:
            pass
        return False
