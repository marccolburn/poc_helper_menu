import yaml
import os
import subprocess
import configparser
from sqlalchemy.exc import IntegrityError
from simple_term_menu import TerminalMenu
from models import Host, session, Link
from tabulate import tabulate
from configparser import ConfigParser
import getpass


def main_menu():
    """Main menu of the application."""
    options = ["[i] Import Hosts", "[l] Import Links", "[c] Connect to Host", "[a] View and Run Ansible Playbooks", "[m] Interface Management", "[e] Exit"]
    terminal_menu = TerminalMenu(options, menu_cursor_style=('fg_red', 'bold'), menu_highlight_style=('bg_green', 'bold'), title="Main Menu")
    menu_entry_index = terminal_menu.show()
    if menu_entry_index == 0:
        import_hosts_menu()
    elif menu_entry_index == 1:
        import_links_menu()
    elif menu_entry_index == 2:
        connect_host_menu()
    elif menu_entry_index == 3:
        preview_and_run_playbook_menu()
    elif menu_entry_index == 4:
        interface_management_menu()
    elif menu_entry_index == 5:
        exit()

def import_hosts_menu():
    """Menu to import hosts from Ansible inventory or manually add a host."""
    #Options presented upon selecting "Import Hosts"
    options = ["[y] Import from Ansible YAML", "[i] Import from Ansible INI", "[m] Manually add Host", "[b] Back to Main Menu"]
    terminal_menu = TerminalMenu(options, menu_cursor_style=('fg_red', 'bold'), menu_highlight_style=('bg_green', 'bold'), title="Import Hosts")
    menu_entry_index = terminal_menu.show()
    #Conditional statements to determine the next steps
    #If "Import from Ansible YAML" is selected, the import_inv_from_yaml function is called
    if menu_entry_index == 0:
        import_inv_from_yaml()
    #If "Import from Ansible INI" is selected, the import_inv_from_ini function is called
    elif menu_entry_index == 1:
        # TODO import_inv_from_ini()
        import_inv_from_ini()
    elif menu_entry_index == 2:
        manually_add_host()
    elif menu_entry_index == 3:
        main_menu()


def import_links_menu():
    """Menu to import connections from containerlab topology style YAML."""
    options = ["[c] Import from Containerlab Topology YAML", "[b] Back to Main Menu"]
    terminal_menu = TerminalMenu(options, menu_cursor_style=('fg_red', 'bold'), menu_highlight_style=('bg_green', 'bold'), title="Import Links")
    menu_entry_index = terminal_menu.show()
    if menu_entry_index == 0:
        import_links_from_containerlab()
    elif menu_entry_index == 1:
        main_menu()

def import_links_from_containerlab():
    """Function to import links from a Containerlab topology YAML file."""
    default_yaml_file = find_topology_yml()
    if default_yaml_file:
        print(f"Default topology file found: {default_yaml_file}")
        use_default = input(f"Do you want to use the default topology file? (y/n): ").strip().lower()
        if use_default == 'y':
            yaml_file = default_yaml_file
        else:
            yaml_file = input("What is the path of your Containerlab topology file? ")
    else:
        yaml_file = input("What is the path of your Containerlab topology file? ")

    if not yaml_file:
        print("No topology file provided.")
        return

    try:
        with open(yaml_file, 'r') as file:
            data = yaml.safe_load(file)
            links = data.get('topology', {}).get('links', [])
            links_added = []
            for link in links:
                endpoints = link.get('endpoints', [])
                if len(endpoints) == 2:
                    source = endpoints[0].split(':')
                    destination = endpoints[1].split(':')
                    if len(source) == 2 and len(destination) == 2:
                        source_host, source_interface = source
                        destination_host, destination_interface = destination
                        new_link = Link(
                            source_host=source_host,
                            source_interface=source_interface,
                            destination_host=destination_host,
                            destination_interface=destination_interface
                        )
                        session.add(new_link)
                        links_added.append(new_link)
            session.commit()
            print(tabulate([[link.source_host, link.source_interface, link.destination_host, link.destination_interface] for link in links_added], headers=["Source Host", "Source Interface", "Destination Host", "Destination Interface"]))
    except FileNotFoundError:
        print(f"File {yaml_file} not found.")
    except yaml.YAMLError as exc:
        print(f"Error parsing YAML file: {exc}")
    main_menu()


def import_inv_from_yaml():
    """Function to import hosts from an Ansible YAML inventory file."""
    default_yaml_file = find_ansible_inventory_yml()
    if default_yaml_file:
        print(f"Default inventory file found: {default_yaml_file}")
        use_default = input(f"Do you want to use the default inventory file? (y/n): ").strip().lower()
        if use_default == 'y':
            yaml_file = default_yaml_file
        else:
            yaml_file = input("What is the path to your inventory file? ")
    else:
        yaml_file = input("What is the path to your inventory file? ")

    if not yaml_file:
        print("No inventory file provided.")
        return

    try:
        with open(yaml_file, 'r') as file:
            data = yaml.safe_load(file)
            children = data.get('all', {}).get('children', {})
            hosts_added = []
            for group, group_data in children.items():
                if group == 'bridge':
                    continue
                vars = group_data.get('vars', {})
                hosts = group_data.get('hosts', {})
                for hostname, host_data in hosts.items():
                    image_type = group
                    network_os = "junos" if "junos" in image_type else 'linux' if 'linux' in image_type else vars.get('ansible_network_os', '')
                    new_host = Host(
                        hostname=hostname,
                        ip_address=host_data.get('ansible_host', ''),
                        network_os=network_os,
                        connection=vars.get('ansible_connection', ''),
                        username=vars.get('ansible_user', ''),
                        password=vars.get('ansible_password', ''),
                        image_type=image_type
                    )
                    session.add(new_host)
                    hosts_added.append(new_host)
            # Save changes to hosts.db
            session.commit()
            print(tabulate([[host.hostname, host.ip_address, host.network_os, host.connection, host.username, host.password, host.image_type] for host in hosts_added], headers=["Hostname", "IP Address", "Network OS", "Connection", "Username", "Password", "Image Type"]))
    except IntegrityError as e:
        # Used to prevent having the same host added to the database
        session.rollback()
        print(f"IntegrityError: {e}")
        print(f"Host {hostname} already exists in the database.")
    except Exception as e:
        print(f"Failed to import from YAML: {e}")
    main_menu()

def manually_add_host():
    """Function to manually add a host."""
    #User input to add a host
    hostname = input("Enter hostname: ")
    ip_address = input("Enter IP address: ")
    network_os = input("Enter network OS: ")
    connection = input("Enter connection type: ")
    username = input("Enter username: ")
    password = input("Enter password: ")
    #Add host to the database
    try:
        new_host = Host(
            hostname=hostname,
            ip_address=ip_address,
            network_os=network_os,
            connection=connection,
            username=username,
            password=password
            )
        session.add(new_host)
        session.commit()
        print(tabulate([[host.hostname, host.ip_address, host.network_os, host.connection, host.username, host.password, host.image_type] for host in hosts_added], headers=["Hostname", "IP Address", "Network OS", "Connection", "Username", "Password", "Image Type"]))
    except IntegrityError as e:
        # Used to prevent having the same host added to the database
        session.rollback()
        print(f"IntegrityError: {e}")
        print(f"Host {hostname} already exists in the database.")
    main_menu()

def import_inv_from_ini():
    """Function to import hosts from an Ansible INI inventory file."""
    default_ini_file = find_ansible_inventory_ini()
    if default_ini_file:
        print(f"Default inventory file found: {default_ini_file}")
        use_default = input(f"Do you want to use the default inventory file? (y/n): ").strip().lower()
        if use_default == 'y':
            ini_file = default_ini_file
        else:
            ini_file = input("What is the path of your inventory file? ")
    else:
        ini_file = input("What is the path of your inventory file? ")

    if not ini_file:
        print("No inventory file provided.")
        return

    hosts_added = []
    try:
        config = ConfigParser()
        config.read(ini_file)
        for section in config.sections():
            for hostname, ip_address in config.items(section):
                network_os = "junos" if "junos" in section else 'linux' if 'linux' in section else section
                new_host = Host(
                    hostname=hostname,
                    ip_address=ip_address,
                    network_os=network_os,
                    connection=config.get(section, 'ansible_connection', fallback=''),
                    username=config.get(section, 'ansible_user', fallback=''),
                    password=config.get(section, 'ansible_password', fallback=''),
                    image_type=section
                )
                session.add(new_host)
                hosts_added.append(new_host)
        # Save changes to hosts.db
        session.commit()
        print(tabulate([[host.hostname, host.ip_address, host.network_os, host.connection, host.username, host.password, host.image_type] for host in hosts_added], headers=["Hostname", "IP Address", "Network OS", "Connection", "Username", "Password", "Image Type"]))
    except IntegrityError as e:
        # Used to prevent having the same host added to the database
        session.rollback()
        print(f"IntegrityError: {e}")
        print(f"Host {hostname} already exists in the database.")
    except Exception as e:
        print(f"Failed to import from INI: {e}")
    main_menu()

def connect_host_menu():
    """Menu to connect to a host."""
    #Query all hosts from the database
    hosts = session.query(Host).all()
    #Create an option in the menu for all hosts and a back option
    options = [f"[{i}] {host.hostname}" for i, host in enumerate(hosts, start=1)] + ["[b] Back to Main Menu"]
    terminal_menu = TerminalMenu(options, menu_cursor_style=('fg_red', 'bold'), menu_highlight_style=('bg_green', 'bold'), title="Connect to Host")
    menu_entry_index = terminal_menu.show()
    #Logic to initiate connect to host or go back to main menu with a dynamic amount of options
    if menu_entry_index == len(options) - 1:
        main_menu()
    else:
        connect_to_host(hosts[menu_entry_index].hostname)

def list_files(directory="."):
    return (file for file in os.listdir(directory) if os.path.isfile(os.path.join(directory, file)))

def preview_and_run_playbook_menu():
    """Menu to preview files and run ansible-playbook."""
    files = []
    for f in os.listdir('.'):
        if os.path.isfile(f):
            files.append(f)
    options = []
    for i, file in enumerate(files, start=1):
        options.append(f"[{i}] {file}")
    options.append("[b] Back to Main Menu")
    
    def preview_command(file):
        """Function to preview the contents of a file."""
        try:
            with open(file, 'r') as f:
                return f.read()
        except Exception:
            return ""  # Return an empty string if the file can't be read

    terminal_menu = TerminalMenu(options, menu_cursor_style=('fg_red', 'bold'), menu_highlight_style=('bg_green', 'bold'), preview_command=preview_command)
    menu_entry_index = terminal_menu.show()
    if menu_entry_index == len(options) - 1:
        main_menu()
    else:
        selected_file = files[menu_entry_index]
        run_ansible_playbook(selected_file)

def run_ansible_playbook(file):
    """Function to run ansible-playbook with the selected file and arguments."""
    args = input("Enter any additional arguments for ansible-playbook: ")
    command = f"ansible-playbook {file} {args}"
    try:
        subprocess.run(command, shell=True)
    except Exception as e:
        print(f"Failed to run ansible-playbook: {e}")
    main_menu()

def list_files(directory="."):
    return (file for file in os.listdir(directory) if os.path.isfile(os.path.join(directory, file)))

def preview_and_run_playbook_menu():
    """Menu to preview files and run ansible-playbook."""
    files = []
    for f in os.listdir('.'):
        if os.path.isfile(f):
            files.append(f)
    options = []
    for i, file in enumerate(files, start=1):
        options.append(f"[{i}] {file}")
    options.append("[b] Back to Main Menu")
    
    def preview_command(file):
        """Function to preview the contents of a file."""
        try:
            with open(file, 'r') as f:
                return f.read()
        except Exception:
            return ""  # Return an empty string if the file can't be read

    terminal_menu = TerminalMenu(options, menu_cursor_style=('fg_red', 'bold'), menu_highlight_style=('bg_green', 'bold'), preview_command=preview_command)
    menu_entry_index = terminal_menu.show()
    if menu_entry_index == len(options) - 1:
        main_menu()
    else:
        selected_file = files[menu_entry_index]
        run_ansible_playbook(selected_file)

def run_ansible_playbook(file):
    """Function to run ansible-playbook with the selected file and arguments."""
    args = input("Enter any additional arguments for ansible-playbook: ")
    command = f"ansible-playbook {file} {args}"
    try:
        subprocess.run(command, shell=True)
    except Exception as e:
        print(f"Failed to run ansible-playbook: {e}")
    main_menu()

def clear_screen():
    """Function to clear the screen. Used this when other TUI was used. Not needed for simple_term_menu."""
    os.system('clear' if os.name == 'posix' else 'cls')

def find_ansible_inventory_yml():
    """Function to find ansible-inventory.yml in the current directory or clab folder in the parent directory."""
    current_dir = os.getcwd()
    ansible_inventory_yml = os.path.join(current_dir, 'ansible-inventory.yml')
    
    if os.path.isfile(ansible_inventory_yml):
        return ansible_inventory_yml
    
    parent_dir = os.path.dirname(current_dir)
    for item in os.listdir(parent_dir):
        if item.startswith('clab') and os.path.isdir(os.path.join(parent_dir, item)):
            clab_dir = os.path.join(parent_dir, item)
            ansible_inventory_yml = os.path.join(clab_dir, 'ansible-inventory.yml')
            if os.path.isfile(ansible_inventory_yml):
                return ansible_inventory_yml
    
    return None

def find_ansible_inventory_ini():
    """Function to find ansible-inventory.ini in the current directory or parent directory."""
    current_dir = os.getcwd()
    ansible_inventory_ini = os.path.join(current_dir, 'ansible-inventory.ini')
    
    if os.path.isfile(ansible_inventory_ini):
        return ansible_inventory_ini
    
    parent_dir = os.path.dirname(current_dir)
    ansible_inventory_ini = os.path.join(parent_dir, 'ansible-inventory.ini')
    
    if os.path.isfile(ansible_inventory_ini):
        return ansible_inventory_ini
    
    return None

def find_topology_yml():
    """Function to find topology.yml in the current directory or parent directory."""
    current_dir = os.getcwd()
    topology_yml = os.path.join(current_dir, 'topology.yml')
    
    if os.path.isfile(topology_yml):
        return topology_yml
    
    parent_dir = os.path.dirname(current_dir)
    topology_yml = os.path.join(parent_dir, 'topology.yml')
    
    if os.path.isfile(topology_yml):
        return topology_yml
    
    return None

def interface_management_menu():
    """Menu for interface management."""
    options = ["[e] Enable or Disable Interfaces", "[i] Impair Interfaces", "[b] Back to Main Menu"]
    terminal_menu = TerminalMenu(options, menu_cursor_style=('fg_red', 'bold'), menu_highlight_style=('bg_green', 'bold'), title="Interface Management")
    menu_entry_index = terminal_menu.show()
    if menu_entry_index == 0:
        enable_disable_interfaces_menu()
    elif menu_entry_index == 1:
        impair_interfaces_menu()
    elif menu_entry_index == 2:
        main_menu()

def enable_disable_interfaces_menu():
    """Menu to enable or disable network interfaces."""
    links = session.query(Link).all()
    options = [f"{link.source_host}:{link.source_interface} -> {link.destination_host}:{link.destination_interface} (State: {link.state})" for link in links]
    options.append("[b] Back to Interface Management")
    terminal_menu = TerminalMenu(options, menu_cursor_style=('fg_red', 'bold'), menu_highlight_style=('bg_green', 'bold'), title="Enable or Disable Interfaces")
    menu_entry_index = terminal_menu.show()
    if menu_entry_index == len(options) - 1:
        interface_management_menu()
    else:
        selected_link = links[menu_entry_index]
        enable_disable_interfaces(selected_link)
        enable_disable_interfaces_menu()  # Return to the enable/disable interfaces menu after execution

def impair_interfaces_menu():
    """Menu to impair network interfaces."""
    links = session.query(Link).all()
    options = []
    for link in links:
        impairments = []
        if link.jitter != 0:
            impairments.append(f"Jitter: {link.jitter}ms")
        if link.latency != 0:
            impairments.append(f"Latency: {link.latency}ms")
        if link.loss != 0:
            impairments.append(f"Loss: {link.loss}%")
        if link.rate != 0:
            impairments.append(f"Rate: {link.rate}kbit/s")
        if link.corruption != 0:
            impairments.append(f"Corruption: {link.corruption}%")
        impairments_str = ", ".join(impairments) if impairments else "No impairments"
        options.append(f"{link.source_host}:{link.source_interface} -> {link.destination_host}:{link.destination_interface} ({impairments_str})")
    options.append("[b] Back to Interface Management")
    terminal_menu = TerminalMenu(options, menu_cursor_style=('fg_red', 'bold'), menu_highlight_style=('bg_green', 'bold'), title="Impair Interfaces")
    menu_entry_index = terminal_menu.show()
    if menu_entry_index == len(options) - 1:
        interface_management_menu()
    else:
        selected_link = links[menu_entry_index]
        manage_impairment(selected_link)
        impair_interfaces_menu()  # Return to the impair interfaces menu after execution

def manage_impairment(link):
    """Function to manage impairments on a network interface."""
    impairments = {
        "jitter": link.jitter,
        "latency": link.latency,
        "loss": link.loss,
        "rate": link.rate,
        "corruption": link.corruption
    }
    non_zero_impairments = {k: v for k, v in impairments.items() if v != 0}
    if non_zero_impairments:
        print(f"Current impairments on {link.source_host}:{link.source_interface} -> {link.destination_host}:{link.destination_interface}:")
        for k, v in non_zero_impairments.items():
            print(f"{k.capitalize()}: {v}")
        remove = input("Do you want to remove the impairments? (y/n): ").strip().lower()
        if remove == 'y':
            link.jitter = 0
            link.latency = 0
            link.loss = 0
            link.rate = 0
            link.corruption = 0
            session.add(link)
            session.commit()
            print("Impairments removed.")
            apply_impairments(link)
            return

    options = ["[d] Delay and Jitter", "[l] Latency", "[o] Loss", "[r] Rate", "[c] Corruption", "[b] Back to Impair Interfaces"]
    terminal_menu = TerminalMenu(options, menu_cursor_style=('fg_red', 'bold'), menu_highlight_style=('bg_green', 'bold'), title="Set Impairments")
    menu_entry_index = terminal_menu.show()
    if menu_entry_index == len(options) - 1:
        impair_interfaces_menu()
    else:
        if menu_entry_index == 0:
            link.latency = int(input("Enter delay value (ms): ").strip())
            link.jitter = int(input("Enter jitter value (ms): ").strip())
        elif menu_entry_index == 1:
            link.latency = int(input("Enter latency value (ms): ").strip())
        elif menu_entry_index == 2:
            link.loss = int(input("Enter loss value (%): ").strip())
        elif menu_entry_index == 3:
            link.rate = int(input("Enter rate value (kbit/s): ").strip())
        elif menu_entry_index == 4:
            link.corruption = int(input("Enter corruption value (%): ").strip())
        session.add(link)
        session.commit()
        print("Impairment set.")
        apply_impairments(link)  # Apply the impairments after setting them
        manage_impairment(link)  # Return to the manage impairment menu after setting an impairment

def apply_impairments(link):
    """Function to apply impairments to a network interface using containerlab tools netem set."""
    host = session.query(Host).filter(Host.hostname.contains(link.source_host)).first()
    if not host:
        print(f"Host {link.source_host} not found in the database.")
        return

    command = f"sudo containerlab tools netem set -n {host.hostname} -i {link.source_interface}"
    if link.latency > 0:
        command += f" --delay {link.latency}ms"
    if link.jitter > 0:
        command += f" --jitter {link.jitter}ms"
    if link.loss > 0:
        command += f" --loss {link.loss}"
    if link.rate > 0:
        command += f" --rate {link.rate}"
    if link.corruption > 0:
        command += f" --corruption {link.corruption}"

    print(f"Applying impairments with command: {command}")
    try:
        subprocess.run(command, shell=True)
        print("Impairments applied successfully.")
    except Exception as e:
        print(f"Failed to apply impairments: {e}")

def connect_to_host(hostname, command=None, return_to_main_menu=True):
    """Function to connect to a host via SSH and optionally run a command."""
    # Query info about host from the database
    host = session.query(Host).filter_by(hostname=hostname).first()
    if host:
        print(f"Connecting to {hostname} via SSH...")
        try:
            username = host.username if host.username else input(f"Enter username for {hostname}: ").strip()
            password = host.password if host.password else getpass.getpass(prompt=f"Enter password for {username}@{host.ip_address}: ")
            ssh_command = f"sshpass -p '{password}' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {username}@{host.ip_address}"
            if command:
                ssh_command += f" '{command}'"
            subprocess.run(ssh_command, shell=True)
        except Exception as e:
            print(f"Failed to connect: {e}")
    else:
        print(f"Host {hostname} not found in the database.")
        username = input(f"Enter username for {hostname}: ").strip()
        password = getpass.getpass(prompt=f"Enter password for {username}@{hostname}: ")
        ip_address = input(f"Enter IP address for {hostname}: ").strip()
        ssh_command = f"sshpass -p '{password}' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {username}@{ip_address}"
        if command:
            ssh_command += f" '{command}'"
        try:
            subprocess.run(ssh_command, shell=True)
        except Exception as e:
            print(f"Failed to connect: {e}")
    
    if return_to_main_menu:
        main_menu()



def enable_disable_interfaces(link):
    """Function to enable or disable both the source and destination network interfaces.
    
    This is being done because the abstraction of running a VM inside of a container prevents the interface state from being detected.
    
    If you want to manage the interfaces of a physical device, or another system that does not have this limitation
    
    you can use the following code:

    ```
    def enable_disable_interfaces(link):
        #Function to enable or disable a network interface.
        host = session.query(Host).filter(Host.hostname.contains(link.source_host)).first()
        if not host:
            print(f"Host {link.source_host} not found in the database.")
            enable_disable_interfaces_menu()
            return

        print(f"Managing interface {link.source_interface} on {link.source_host}...")
        action = "disable" if link.state == "enabled" else "enable"

        if host.network_os == "linux":
            command = f"ip link set {link.source_interface} {'up' if action == 'enable' else 'down'}"
        elif host.network_os == "junos":
            command = f"configure; set interfaces {link.source_interface} {action}; commit and-quit"
        else:
            print(f"Unsupported network OS: {host.network_os}")
            enable_disable_interfaces_menu()
            return

        print(f"Command to be executed: {command}")

        try:
            connect_to_host(host.hostname, command, return_to_main_menu=False)
            link.state = "disabled" if link.state == "enabled" else "enabled"
            session.add(link)  # Mark the link object as dirty
            session.commit()
            # Verify the update by querying the database
            updated_link = session.query(Link).filter_by(id=link.id).first()
            print(f"Verified link state in database: {updated_link.state}")
            print(f"Interface {link.source_interface} on {link.source_host} has been {link.state}.")
        except Exception as e:
            print(f"Failed to manage interface: {e}")
            session.rollback()  # Rollback in case of an error

        enable_disable_interfaces_menu()
    ```
    """
    source_host = session.query(Host).filter(Host.hostname.contains(link.source_host)).first()
    destination_host = session.query(Host).filter(Host.hostname.contains(link.destination_host)).first()
    
    if not source_host and not destination_host:
        print(f"Both source host {link.source_host} and destination host {link.destination_host} not found in the database.")
        enable_disable_interfaces_menu()
        return

    if not source_host:
        print(f"Source host {link.source_host} not found in the database. Only managing destination interface.")
    elif not destination_host:
        print(f"Destination host {link.destination_host} not found in the database. Only managing source interface.")
    else:
        print(f"Managing interface {link.source_interface} on {link.source_host} and {link.destination_interface} on {link.destination_host}...")

    action = "disable" if link.state == "enabled" else "enable"
    
    source_command = None
    destination_command = None

    if source_host:
        if source_host.network_os == "linux":
            source_command = f"ip link set {link.source_interface} {'up' if action == 'enable' else 'down'}"
        elif source_host.network_os == "junos":
            source_command = f"configure; set interfaces {link.source_interface} {action}; commit and-quit"
        else:
            print(f"Unsupported network OS: {source_host.network_os}")

    if destination_host:
        if destination_host.network_os == "linux":
            destination_command = f"ip link set {link.destination_interface} {'up' if action == 'enable' else 'down'}"
        elif destination_host.network_os == "junos":
            destination_command = f"configure; set interfaces {link.destination_interface} {action}; commit and-quit"
        else:
            print(f"Unsupported network OS: {destination_host.network_os}")

    if source_command:
        print(f"Source command to be executed: {source_command}")
    if destination_command:
        print(f"Destination command to be executed: {destination_command}")

    try:
        if source_command:
            connect_to_host(source_host.hostname, source_command, return_to_main_menu=False)
        if destination_command:
            connect_to_host(destination_host.hostname, destination_command, return_to_main_menu=False)
        link.state = "disabled" if link.state == "enabled" else "enabled"
        session.add(link)  # Mark the link object as dirty
        session.commit()
        # Verify the update by querying the database
        updated_link = session.query(Link).filter_by(id=link.id).first()
        print(f"Verified link state in database: {updated_link.state}")
        print(f"Interfaces {link.source_interface} on {link.source_host} and {link.destination_interface} on {link.destination_host} have been {link.state}.")
    except Exception as e:
        print(f"Failed to manage interfaces: {e}")
        session.rollback()  # Rollback in case of an error

    enable_disable_interfaces_menu()

if __name__ == "__main__":
    main_menu()
