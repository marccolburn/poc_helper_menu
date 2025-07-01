"""
Import functions for POC Helper Menu.
Handles importing hosts and links from various sources including:
- Ansible YAML inventory files
- Ansible INI inventory files  
- Containerlab topology files
- Manual host entry
"""

import os
import yaml
from configparser import ConfigParser
from simple_term_menu import TerminalMenu
from sqlalchemy.exc import IntegrityError
from tabulate import tabulate
from models import Host, Link, Lab, session


# Mapping of containerlab kinds to Ansible network_os values
CONTAINERLAB_KIND_TO_NETWORK_OS = {
    # Arista
    'arista_ceos': 'eos',
    'arista_veos': 'eos',
    'ceos': 'eos',
    'veos': 'eos',
    
    # Cisco IOS/IOS-XE
    'cisco_c8000v': 'ios',
    'cisco_cat9kv': 'ios', 
    'cisco_csr1000v': 'ios',
    'cisco_c9300v': 'ios',
    'c8000v': 'ios',
    'cat9kv': 'ios',
    'csr1000v': 'ios',
    'c9300v': 'ios',
    
    # Cisco NX-OS
    'cisco_n9kv': 'nxos',
    'cisco_nexus9000v': 'nxos',
    'n9kv': 'nxos',
    'nexus9000v': 'nxos',
    
    # Cisco IOS-XR
    'cisco_xrd': 'iosxr',
    'cisco_xrv9k': 'iosxr',
    'cisco_iosxrv': 'iosxr',
    'xrd': 'iosxr',
    'xrv9k': 'iosxr',
    'iosxrv': 'iosxr',
    
    # Juniper
    'juniper_vjunosevolved': 'junos',
    'juniper_vjunosswitch': 'junos',
    'juniper_vmx': 'junos',
    'juniper_vsrx': 'junos',
    'juniper_vqfx': 'junos',
    'juniper_vrr': 'junos',
    'vjunosevolved': 'junos',
    'vjunosswitch': 'junos',
    'vmx': 'junos',
    'vsrx': 'junos',
    'vqfx': 'junos',
    'vrr': 'junos',
    
    # Nokia
    'nokia_sros': 'sros',
    'sros': 'sros',
    
    # Generic Linux
    'linux': 'linux',
    'ubuntu': 'linux',
    'centos': 'linux',
    'alpine': 'linux',
    
    # Fortinet
    'fortinet_fortigate': 'fortios',
    'fortigate': 'fortios',
    
    # Palo Alto
    'paloalto_panos': 'panos',
    'panos': 'panos',
    
    # Mikrotik
    'mikrotik_routeros': 'routeros',
    'routeros': 'routeros',
}


def file_selector(title="Select File", file_extensions=None):
    """
    Unified file selector that filters for .yml/.yaml/.ini files in the current directory,
    with an option to browse to another directory.
    """
    if not file_extensions:
        file_extensions = ['.yml', '.yaml', '.ini']
    
    try:
        current_dir = os.getcwd()
        files_found = []
        
        # Search current directory for matching files
        try:
            for item in os.listdir(current_dir):
                item_path = os.path.join(current_dir, item)
                if os.path.isfile(item_path):
                    _, ext = os.path.splitext(item.lower())
                    if ext in [e.lower() for e in file_extensions]:
                        files_found.append((item, item_path))
        except PermissionError:
            pass
        
        # Create menu options
        options = [file_info[0] for file_info in files_found]
        options.append("Browse other directory")
        options.append("Cancel")
        
        # Show current working directory and file types in title
        ext_info = f" ({', '.join(file_extensions)})"
        full_title = f"{title}{ext_info} - Current: {current_dir}"
        
        terminal_menu = TerminalMenu(
            options,
            menu_cursor_style=("fg_red", "bold"),
            menu_highlight_style=("bg_green", "bold"),
            title=full_title,
        )
        
        choice_index = terminal_menu.show()
        
        if choice_index is None or choice_index == len(options) - 1:  # Cancel
            return None
        elif choice_index == len(options) - 2:  # Browse other directory
            custom_dir = input("Enter directory path: ").strip()
            if not custom_dir:
                return file_selector(title, file_extensions)
            
            custom_dir = os.path.abspath(os.path.expanduser(custom_dir))
            if not os.path.isdir(custom_dir):
                print(f"Directory not found: {custom_dir}")
                input("Press Enter to continue...")
                return file_selector(title, file_extensions)
            
            # Change to the custom directory and recursively call file_selector
            original_dir = os.getcwd()
            try:
                os.chdir(custom_dir)
                return file_selector(title, file_extensions)
            finally:
                os.chdir(original_dir)
        else: 
            return files_found[choice_index][1]
            
    except KeyboardInterrupt:
        return None
    except Exception as e:
        print(f"Error in file selector: {e}")
        input("Press Enter to continue...")
        return None


def import_links_from_containerlab(lab_name, filename=None):
    """Function to import links from a Containerlab topology YAML file."""
    if filename:
        yaml_file = filename
    else:
        yaml_file = file_selector("Select Containerlab Topology File")
        if not yaml_file:
            print("No topology file selected.")
            return

    try:
        with open(yaml_file, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
            links = data.get("topology", {}).get("links", [])
            links_added = []
            for link in links:
                endpoints = link.get("endpoints", [])
                if len(endpoints) == 2:
                    source = endpoints[0].split(":")
                    destination = endpoints[1].split(":")
                    if len(source) == 2 and len(destination) == 2:
                        source_host, source_interface = source
                        destination_host, destination_interface = destination
                        new_link = Link(
                            source_host=source_host,
                            source_interface=source_interface,
                            destination_host=destination_host,
                            destination_interface=destination_interface,
                            lab_name=lab_name,
                        )
                        session.add(new_link)
                        links_added.append(new_link)
            session.commit()
            print(
                tabulate(
                    [
                        [
                            link.source_host,
                            link.source_interface,
                            link.destination_host,
                            link.destination_interface,
                            link.lab_name,
                        ]
                        for link in links_added
                    ],
                    headers=[
                        "Source Host",
                        "Source Interface",
                        "Destination Host",
                        "Destination Interface",
                        "Lab",
                    ],
                )
            )
    except FileNotFoundError:
        print(f"File {yaml_file} not found.")
    except yaml.YAMLError as exc:
        print(f"Error parsing YAML file: {exc}")


def import_from_containerlab_topology(lab_name):
    """Function to import both hosts and links from a Containerlab topology YAML file."""
    
    # Get lab info to check for remote configuration
    lab = session.query(Lab).filter_by(lab_name=lab_name).first()
    
    # Check if remote path is configured
    has_remote = (lab and lab.remote_containerlab_host and 
                 lab.remote_containerlab_username and lab.topology_path)
    
    yaml_file = None
    
    if has_remote:
        # Show options for local vs remote
        options = [
            "[l] Select local topology file",
            "[r] Scan remote path for topology files", 
            "[c] Cancel"
        ]
        
        terminal_menu = TerminalMenu(
            options,
            menu_cursor_style=("fg_red", "bold"),
            menu_highlight_style=("bg_green", "bold"),
            title=f"Containerlab Import Options - Lab: {lab_name}",
        )
        choice = terminal_menu.show()
        
        if choice == 0:  # Local file
            yaml_file = file_selector("Select Local Containerlab Topology File")
        elif choice == 1:  # Remote scan
            yaml_file = scan_remote_topology_files(lab)
        else:  # Cancel
            print("Import cancelled.")
            return
    else:
        # No remote config, use local file selector
        yaml_file = file_selector("Select Containerlab Topology File")
    
    if not yaml_file:
        print("No topology file selected.")
        return

    try:
        with open(yaml_file, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
            topology = data.get("topology", {})
            nodes = topology.get("nodes", {})
            links = topology.get("links", [])
            
            # Capture the containerlab topology name and update the lab
            containerlab_name = data.get("name")
            if containerlab_name:
                lab = session.query(Lab).filter_by(lab_name=lab_name).first()
                if lab:
                    lab.containerlab_name = containerlab_name
                    session.add(lab)
                    print(f"Captured containerlab topology name: {containerlab_name}")
            
            hosts_added = []
            links_added = []
            
            # Import hosts/nodes (skip bridge nodes)
            for hostname, node_data in nodes.items():
                kind = node_data.get("kind", "")
                
                # Skip bridge nodes
                if kind == "bridge":
                    continue
                
                # Use kind for image_type, mgmt-ipv4 for address
                mgmt_ipv4 = node_data.get("mgmt-ipv4", "")
                
                # Map containerlab kind to network_os using the dictionary
                network_os = CONTAINERLAB_KIND_TO_NETWORK_OS.get(kind, "")
            
                
                new_host = Host(
                    hostname=hostname,
                    ip_address=mgmt_ipv4,
                    network_os=network_os,
                    username="admin",     # Default containerlab username
                    password="admin@123", # Default containerlab password
                    image_type=kind,      # Use kind for image_type
                    lab_name=lab_name,
                    console="", 
                )
                session.add(new_host)
                hosts_added.append(new_host)
            
            # Import links (reuse logic from import_links_from_containerlab)
            for link in links:
                endpoints = link.get("endpoints", [])
                if len(endpoints) == 2:
                    source = endpoints[0].split(":")
                    destination = endpoints[1].split(":")
                    if len(source) == 2 and len(destination) == 2:
                        source_host, source_interface = source
                        destination_host, destination_interface = destination
                        new_link = Link(
                            source_host=source_host,
                            source_interface=source_interface,
                            destination_host=destination_host,
                            destination_interface=destination_interface,
                            lab_name=lab_name,
                        )
                        session.add(new_link)
                        links_added.append(new_link)
            
            # Commit all changes
            session.commit()
            
            if containerlab_name:
                print(f"Containerlab topology '{containerlab_name}' imported successfully.")
            # Display results
            if hosts_added:
                print("\nHosts imported:")
                print(
                    tabulate(
                        [
                            [
                                host.hostname,
                                host.ip_address,
                                host.network_os,
                                host.username,
                                host.password,
                                host.image_type,
                                host.lab_name,
                                host.console,
                            ]
                            for host in hosts_added
                        ],
                        headers=[
                            "Hostname",
                            "IP Address",
                            "Network OS",
                            "Username",
                            "Password",
                            "Image Type",
                            "Lab",
                            "Console",
                        ],
                    )
                )
            
            if links_added:
                print("\nLinks imported:")
                print(
                    tabulate(
                        [
                            [
                                link.source_host,
                                link.source_interface,
                                link.destination_host,
                                link.destination_interface,
                                link.lab_name,
                            ]
                            for link in links_added
                        ],
                        headers=[
                            "Source Host",
                            "Source Interface",
                            "Destination Host",
                            "Destination Interface",
                            "Lab",
                        ],
                    )
                )
                
            print(f"\nImport completed: {len(hosts_added)} hosts, {len(links_added)} links")
            
    except FileNotFoundError:
        print(f"File {yaml_file} not found.")
    except yaml.YAMLError as exc:
        print(f"Error parsing YAML file: {exc}")
    except Exception as e:
        print(f"Error importing containerlab topology: {e}")
        session.rollback()


def import_inv_from_yaml(lab_name, filename=None):
    """Function to import hosts from an Ansible YAML inventory file."""
    if filename:
        yaml_file = filename
    else:
        yaml_file = file_selector("Select YAML Inventory File")
        if not yaml_file:
            print("No inventory file selected.")
            return

    def process_group(group_name, group_data, parent_vars=None):
        """Recursively process groups to find hosts."""
        hosts_found = []
        
        # Merge parent vars with current group vars
        current_vars = parent_vars.copy() if parent_vars else {}
        group_vars = group_data.get("vars", {})
        current_vars.update(group_vars)
        
        # Process direct hosts in this group
        hosts = group_data.get("hosts", {})
        for hostname, host_data in hosts.items():
            # Use ansible_network_os if available, otherwise use group name as network_os
            network_os = current_vars.get("ansible_network_os", group_name)
            
            console = host_data.get("console", "")
            if console and not (":" in console or "." in console):
                # If Console is a hostname without domain, prompt for domain
                domain = input(f"Enter domain for console '{console}' (or press Enter to use as-is): ").strip()
                if domain:
                    console = f"{console}.{domain}"
            
            new_host = Host(
                hostname=hostname,
                ip_address=host_data.get("ansible_host", ""),
                network_os=network_os,
                username=current_vars.get("ansible_user", ""),
                password=current_vars.get("ansible_password", ""),
                image_type="",  # Leave blank for hardware labs - network_os should be explicit in vars
                lab_name=lab_name,
                console=console,
            )
            hosts_found.append(new_host)
        
        # Process children groups recursively
        children = group_data.get("children", {})
        for child_name, child_data in children.items():
            child_hosts = process_group(child_name, child_data, current_vars)
            hosts_found.extend(child_hosts)
        
        return hosts_found

    try:
        with open(yaml_file, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
            children = data.get("all", {}).get("children", {})
            hosts_added = []
            
            for group, group_data in children.items():
                if group == "bridge":
                    continue
                
                group_hosts = process_group(group, group_data)
                hosts_added.extend(group_hosts)
            
            # Add all hosts to database
            for host in hosts_added:
                session.add(host)
            
            # Save changes to hosts.db
            session.commit()
            print(
                tabulate(
                    [
                        [
                            host.hostname,
                            host.ip_address,
                            host.network_os,
                            host.username,
                            host.password,
                            host.image_type,
                            host.lab_name,
                            host.console,
                        ]
                        for host in hosts_added
                    ],
                    headers=[
                        "Hostname",
                        "IP Address",
                        "Network OS",
                        "Username",
                        "Password",
                        "Image Type",
                        "Lab",
                        "Console",
                    ],
                )
            )
    except IntegrityError as e:
        # Used to prevent having the same host added to the database
        session.rollback()
        print(f"IntegrityError: {e}")
        print("One or more hosts already exist in the database.")
    except Exception as e:
        print(f"Failed to import from YAML: {e}")


def manually_add_host(lab_name):
    """Function to manually add a host."""
    # User input to add a host
    hostname = input("Enter hostname: ")
    ip_address = input("Enter IP address: ")
    network_os = input("Enter network OS: ")
    username = input("Enter username: ")
    password = input("Enter password: ")
    image_type = input("Enter image type: ")
    console = input("Enter console address (optional): ").strip()
    
    # Handle console domain concatenation
    if console and not (":" in console or "." in console):
        # Console is a hostname without domain, prompt for domain
        domain = input(f"Enter domain for console '{console}' (or press Enter to use as-is): ").strip()
        if domain:
            console = f"{console}.{domain}"
    
    # Add host to the database
    try:
        new_host = Host(
            hostname=hostname,
            ip_address=ip_address,
            network_os=network_os,
            username=username,
            password=password,
            image_type=image_type,
            lab_name=lab_name,
            console=console or None,
        )
        session.add(new_host)
        session.commit()
        print(
            tabulate(
                [
                    [
                        new_host.hostname,
                        new_host.ip_address,
                        new_host.network_os,
                        new_host.username,
                        new_host.password,
                        new_host.image_type,
                        new_host.lab_name,
                        new_host.console,
                    ]
                ],
                headers=[
                    "Hostname",
                    "IP Address",
                    "Network OS",
                    "Username",
                    "Password",
                    "Image Type",
                    "Lab",
                    "Console",
                ],
            )
        )
    except IntegrityError as e:
        # Used to prevent having the same host added to the database
        session.rollback()
        print(f"IntegrityError: {e}")
        print(f"Host {hostname} already exists in the database.")


def import_inv_from_ini(lab_name, filename=None):
    """Function to import hosts from an Ansible INI inventory file."""
    if filename:
        ini_file = filename
    else:
        ini_file = file_selector("Select INI Inventory File")
        if not ini_file:
            print("No inventory file selected.")
            return

    hosts_added = []
    try:
        config = ConfigParser()
        config.read(ini_file)
        for section in config.sections():
            for hostname, ip_address in config.items(section):
                # Use ansible_network_os if available, otherwise use section name as network_os
                network_os = config.get(section, "ansible_network_os", fallback=section)
                
                console = config.get(section, "console", fallback="")
                if console and not (":" in console or "." in console):
                    # Console is a hostname without domain, prompt for domain
                    domain = (
                    input(f"Enter domain for console '{console}' (or press Enter to use as-is): ").strip()
                    )
                    if domain:
                        console = f"{console}.{domain}"
                
                new_host = Host(
                    hostname=hostname,
                    ip_address=ip_address,
                    network_os=network_os,
                    username=config.get(section, "ansible_user", fallback=""),
                    password=config.get(
                        section, "ansible_password", fallback=""
                    ),
                    image_type="",  # Leave blank for hardware labs - network_os should be explicit
                    lab_name=lab_name,
                    console=console or None,
                )
                session.add(new_host)
                hosts_added.append(new_host)
        # Save changes to hosts.db
        session.commit()
        print(
            tabulate(
                [
                    [
                        host.hostname,
                        host.ip_address,
                        host.network_os,
                        host.username,
                        host.password,
                        host.image_type,
                        host.lab_name,
                        host.console,
                    ]
                    for host in hosts_added
                ],
                headers=[
                    "Hostname",
                    "IP Address",
                    "Network OS",
                    "Username",
                    "Password",
                    "Image Type",
                    "Lab",
                    "Console",
                ],
            )
        )
    except IntegrityError as e:
        # Used to prevent having the same host added to the database
        session.rollback()
        print(f"IntegrityError: {e}")
        print(f"Host {hostname} already exists in the database.")
    except Exception as e:
        print(f"Failed to import from INI: {e}")


def scan_remote_topology_files(lab):
    """Scan remote path for containerlab topology YAML files and let user select one."""
    import subprocess
    import tempfile
    
    remote_host = lab.remote_containerlab_host
    remote_user = lab.remote_containerlab_username  
    remote_path = lab.topology_path
    
    if not all([remote_host, remote_user, remote_path]):
        print("Remote configuration incomplete. Missing host, username, or path.")
        return None
    
    try:
        # Use SSH to list YAML files in the remote directory (top level only)
        # Use find with -maxdepth 1 to avoid shell wildcard issues
        ssh_command = (
        f"ssh {remote_user}@{remote_host} \
        'find {remote_path} -maxdepth 1 \
        -type f \\( -name \"*.yml\" -o -name \"*.yaml\" \\) 2>/dev/null'"
        )
        result = subprocess.run(ssh_command, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Failed to scan remote path: {result.stderr}")
            return None
        
        remote_files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
        
        if not remote_files:
            print(f"No YAML files found in remote path: {remote_path}")
            return None
        
        # Let user select a file
        options = []
        for i, file_path in enumerate(remote_files):
            filename = os.path.basename(file_path)
            options.append(f"[{i+1}] {filename} ({file_path})")
        options.append("[c] Cancel")
        
        terminal_menu = TerminalMenu(
            options,
            menu_cursor_style=("fg_red", "bold"),
            menu_highlight_style=("bg_green", "bold"),
            title=f"Remote Topology Files - {remote_user}@{remote_host}:{remote_path}",
        )
        choice = terminal_menu.show()
        
        if choice is None or choice == len(options) - 1:  # Cancel
            return None
        
        selected_remote_file = remote_files[choice]
        
        # Download the selected file to a temporary location
        temp_dir = tempfile.mkdtemp()
        local_filename = os.path.basename(selected_remote_file)
        local_path = os.path.join(temp_dir, local_filename)
        
        scp_command = f"scp {remote_user}@{remote_host}:{selected_remote_file} {local_path}"
        scp_result = subprocess.run(scp_command, shell=True, capture_output=True, text=True)
        
        if scp_result.returncode != 0:
            print(f"Failed to download remote file: {scp_result.stderr}")
            return None
        
        print(f"Downloaded {selected_remote_file} to {local_path}")
        return local_path
        
    except Exception as e:
        print(f"Error scanning remote topology files: {e}")
        return None
