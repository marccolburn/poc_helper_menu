import yaml
import os
import subprocess
import configparser
from sqlalchemy.exc import IntegrityError
from simple_term_menu import TerminalMenu
from models import Host, session, Link
from tabulate import tabulate


def main_menu():
    """Main menu of the application."""
    #Options presented upon application start
    options = ["[i] Import Hosts", "[l] Import Links", "[c] Connect to Host", "[a] View and Run Ansible Playbooks", "[e] Exit"]
    terminal_menu = TerminalMenu(options, menu_cursor_style=('fg_red', 'bold'), menu_highlight_style=('bg_green', 'bold'), title="Main Menu")
    menu_entry_index = terminal_menu.show()
    #Conditional statements to determine the next steps
    if menu_entry_index == 0:
        import_hosts_menu()
    elif menu_entry_index == 1:
        import_links_menu()
    elif menu_entry_index == 2:
        connect_host_menu()
    elif menu_entry_index == 3:
        preview_and_run_playbook_menu()
    elif menu_entry_index == 4:
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
    yaml_file = input("What is the path of your Containerlab topology file? ")
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
    #Name of file to open
    yaml_file = input("What is the path to your inventory file? ")
    try:
        with open(yaml_file, 'r') as file:
            data = yaml.safe_load(file)
            children = data.get('all', {}).get('children', {})
            hosts_added = []
            for group, group_data in children.items():
                vars = group_data.get('vars', {})
                hosts = group_data.get('hosts', {})
                for hostname, host_data in hosts.items():
                    image_type = group
                    network_os = "junos" if "junos" in image_type else vars.get('ansible_network_os', '')
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
    except IntegrityError:
        # Used to prevent having the same host added to the database
        session.rollback()
        print("Duplicate host found. Rolling back changes.")
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
        print(f"Host {hostname} added to the database.")
    except IntegrityError:
        #Used to prevent having the same host added to the database
        session.rollback()
        print(f"Host {hostname} already exists in the database.")
    main_menu()

def import_inv_from_ini():
    """Function to import hosts from an Ansible INI inventory file."""
    ini_file = input("What is the path of your inventory file? ")
    hosts_added = []
    try:
        config = ConfigParser()
        config.read(ini_file)
        for section in config.sections():
            for hostname, ip_address in config.items(section):
                network_os = "junos" if "junos" in section else section
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
    except IntegrityError:
        # Used to prevent having the same host added to the database
        session.rollback()
        print("Duplicate host found. Rolling back changes.")
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

def connect_to_host(hostname):
    """Function to connect to a host via SSH."""
    #Query info about host from the database
    host = session.query(Host).filter_by(hostname=hostname).first()
    if host:
        print(f"Connecting to {hostname} via SSH...")
        try:
            #Clearing the terminal and then connecting via SSH to host
            #clear_screen()
            ssh_command = f"ssh -o StrictHostKeyChecking=no {host.username}@{host.ip_address}"
            subprocess.run(ssh_command, shell=True)
        except Exception as e:
            print(f"Failed to connect: {e}")
    else:
        print(f"Host {hostname} not found in the database.")
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

if __name__ == "__main__":
    main_menu()
