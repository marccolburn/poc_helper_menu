import yaml
import os
import subprocess
from sqlalchemy.exc import IntegrityError
from simple_term_menu import TerminalMenu
from models import Host, session

def main_menu():
    """Main menu of the application."""
    #Options presented upon application start
    options = ["Import Hosts", "Connect to Host", "Exit"]
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
    options = ["Import from Ansible YAML", "Import from Ansible INI", "Manually add Host", "Back to Main Menu"]
    terminal_menu = TerminalMenu(options)
    menu_entry_index = terminal_menu.show()
    #Conditional statements to determine the next steps
    #If "Import from Ansible YAML" is selected, the import_from_yaml function is called
    if menu_entry_index == 0:
        import_from_yaml()
    #If "Import from Ansible INI" is selected, the import_from_ini function is called
    elif menu_entry_index == 1:
        # TODO import_from_ini()
        print("Not implemented yet.")
    elif menu_entry_index == 2:
        # TODO manually_add_host()
        print("Not implemented yet.")
    elif menu_entry_index == 3:
        main_menu()

def import_from_yaml():
    """Function to import hosts from an Ansible YAML inventory file."""
    #Name of file to open
    yaml_file = "inventory"
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

def connect_host_menu():
    """Menu to connect to a host."""
    #Query all hosts from the database
    hosts = session.query(Host).all()
    #Create an option in the menu for all hosts and a back option
    options = [host.hostname for host in hosts] + ["Back to Main Menu"]
    terminal_menu = TerminalMenu(options)
    menu_entry_index = terminal_menu.show()
    #Logic to initiate connect to host or go back to main menu with a dynamic amount of options
    if menu_entry_index == len(options) - 1:
        main_menu()
    else:
        connect_to_host(options[menu_entry_index])

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