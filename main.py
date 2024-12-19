import yaml
import os
import subprocess
import configparser
from sqlalchemy.exc import IntegrityError
from simple_term_menu import TerminalMenu
from models import Host, session

def main_menu():
    """Main menu of the application."""
    #Options presented upon application start
    options = ["[i] Import Hosts", "[c] Connect to Host", "[e] Exit"]
    terminal_menu = TerminalMenu(options)
    menu_entry_index = terminal_menu.show()
    #Conditional statements to determine the next steps
    if menu_entry_index == 0:
        import_hosts_menu()
    elif menu_entry_index == 1:
        connect_host_menu()
    elif menu_entry_index == 2:
        exit()

def import_hosts_menu():
    """Menu to import hosts from Ansible inventory or manually add a host."""
    #Options presented upon selecting "Import Hosts"
    options = ["[y] Import from Ansible YAML", "[i] Import from Ansible INI", "[m] Manually add Host", "[b] Back to Main Menu"]
    terminal_menu = TerminalMenu(options)
    menu_entry_index = terminal_menu.show()
    #Conditional statements to determine the next steps
    #If "Import from Ansible YAML" is selected, the import_from_yaml function is called
    if menu_entry_index == 0:
        import_from_yaml()
    #If "Import from Ansible INI" is selected, the import_from_ini function is called
    elif menu_entry_index == 1:
        # TODO import_from_ini()
        import_from_ini()
    elif menu_entry_index == 2:
        manually_add_host()
    elif menu_entry_index == 3:
        main_menu()

def import_from_yaml():
    """Function to import hosts from an Ansible YAML inventory file."""
    #Name of file to open
    yaml_file = input("What is the name of your inventory file? ")
    try:
        with open(yaml_file, 'r') as file:
            data = yaml.safe_load(file)
            children = data.get('all', {}).get('children', {})
            for group, group_data in children.items():
                vars = group_data.get('vars', {})
                hosts = group_data.get('hosts', {})
                for hostname, host_data in hosts.items():
                    new_host = Host(
                        hostname=hostname,
                        ip_address=host_data.get('ansible_host', ''),
                        network_os=vars.get('ansible_network_os', ''),
                        connection=vars.get('ansible_connection', ''),
                        username=vars.get('ansible_user', ''),
                        password=vars.get('ansible_password', '')
                    )
                    session.add(new_host)
            #Save chanages to hosts.db
            session.commit()
            print("Hosts added to the database.")
    except IntegrityError:
        #Used to prevent having the same host added to the database
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

def import_from_ini():
    """Function to import hosts from an Ansible INI inventory file."""
    ini_file = input("What is the name of your inventory file? ")
    config = configparser.ConfigParser()
    try:
        config.read(ini_file)
        for section in config.sections():
            if section.endswith(":vars"):
                continue  # Skip the vars section
            vars_section = section + ":vars"
            vars = config[vars_section] if vars_section in config else {}
            for item in config.items(section):
                hostname = item[0].split()[0]
                host_info = item[1].split()
                ip_address = host_info[0].split('=')[1] if '=' in host_info[0] else host_info[0]
                new_host = Host(
                    hostname=hostname,
                    ip_address=ip_address,
                    network_os=vars.get('ansible_network_os', ''),
                    connection=vars.get('ansible_connection', ''),
                    username=vars.get('ansible_user', ''),
                    password=vars.get('ansible_password', '')
                )
                session.add(new_host)
        session.commit()
        print("Hosts added to the database.")
    except IntegrityError:
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
    terminal_menu = TerminalMenu(options)
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

def clear_screen():
    """Function to clear the screen. Used this when other TUI was used. Not needed for simple_term_menu."""
    os.system('clear' if os.name == 'posix' else 'cls')

if __name__ == "__main__":
    main_menu()