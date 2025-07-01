import os
import subprocess
from simple_term_menu import TerminalMenu
from models import Host, Link, Lab, session
import imports
import device_actions
import lab_mgmt
import warnings
import interface_actions
# This is to suppress the deprecation warning from pkg_resources being used by NAPALM
# until NAPALM fixes it in their codebase.
warnings.filterwarnings("ignore", message="pkg_resources is deprecated")


def paginated_menu(items, page_size=9, title="Select Item", format_func=None):
    """
    Create a paginated menu for large lists of items.
    
    Args:
        items: List of items to display
        page_size: Number of items per page
        title: Menu title
        format_func: Function to format each item for display
    
    Returns:
        Selected item or None if cancelled
    """
    if not items:
        return None
    
    if len(items) <= page_size:
        # No pagination needed
        if format_func:
            options = [format_func(i, item) for i, item in enumerate(items)]
        else:
            options = [f"[{i+1}] {item}" for i, item in enumerate(items)]
        options.append("[b] Back")
        
        terminal_menu = TerminalMenu(
            options,
            menu_cursor_style=("fg_red", "bold"),
            menu_highlight_style=("bg_green", "bold"),
            title=title,
        )
        choice = terminal_menu.show()
        if choice is None or choice == len(options) - 1:
            return None
        return items[choice]
    
    # Pagination needed
    total_pages = (len(items) + page_size - 1) // page_size
    current_page = 0
    
    while True:
        start_idx = current_page * page_size
        end_idx = min(start_idx + page_size, len(items))
        page_items = items[start_idx:end_idx]
        
        # Create options for current page
        if format_func:
            options = [format_func(start_idx + i, item) for i, item in enumerate(page_items)]
        else:
            options = [f"[{start_idx + i + 1}] {item}" for i, item in enumerate(page_items)]
        
        # Add navigation options
        nav_options = []
        if current_page > 0:
            nav_options.append("[p] Previous Page")
        if current_page < total_pages - 1:
            nav_options.append("[n] Next Page")
        nav_options.append("[b] Back")
        
        all_options = options + nav_options
        
        page_title = f"{title} - Page {current_page + 1}/{total_pages} ({len(items)} total)"
        terminal_menu = TerminalMenu(
            all_options,
            menu_cursor_style=("fg_red", "bold"),
            menu_highlight_style=("bg_green", "bold"),
            title=page_title,
        )
        
        choice = terminal_menu.show()
        if choice is None:
            return None
        
        # Handle item selection
        if choice < len(options):
            return page_items[choice]
        
        # Handle navigation
        nav_choice = choice - len(options)
        if current_page > 0 and nav_options[nav_choice] == "[p] Previous Page":
            current_page -= 1
        elif current_page < total_pages - 1 and nav_options[nav_choice] == "[n] Next Page":
            current_page += 1
        elif nav_options[nav_choice] == "[b] Back":
            return None




def main_menu():
    """Main menu of the application."""
    options = [
        "[s] Select Lab",
        "[c] Create Lab", 
        "[m] Manage Labs",
        "[e] Exit",
    ]
    terminal_menu = TerminalMenu(
        options,
        menu_cursor_style=("fg_red", "bold"),
        menu_highlight_style=("bg_green", "bold"),
        title="Main Menu",
    )
    menu_entry_index = terminal_menu.show()
    if menu_entry_index == 0:
        select_lab_menu()
    elif menu_entry_index == 1:
        create_lab_menu()
    elif menu_entry_index == 2:
        manage_labs_menu()
    elif menu_entry_index == 3:
        exit()


def create_lab_menu():
    """Menu to create a new lab and set up imports."""
    # Create the lab first
    lab_name = lab_mgmt.create_new_lab()
    if not lab_name:
        main_menu()
        return
    
    # Get the lab info to determine the type
    lab = session.query(Lab).filter_by(lab_name=lab_name).first()
    if not lab:
        print("Error: Lab creation failed.")
        main_menu()
        return
    
    # Set the lab as selected
    lab_mgmt.set_selected_lab(lab_name)
    
    if lab.lab_type == "containerlab":
        # For containerlab, go straight to containerlab import
        print(f"Containerlab '{lab_name}' created. Now importing from containerlab topology...")
        imports.import_from_containerlab_topology(lab_name)
        # After import, go to lab operations
        lab_operations_menu()
    else:
        # For hardware labs, show import menu
        hardware_import_menu(lab_name)


def hardware_import_menu(lab_name):
    """Import menu for hardware labs."""
    options = [
        "[h] Import Hosts",
        "[l] Import Links",
        "[e] Exit to Main Menu",
    ]
    terminal_menu = TerminalMenu(
        options,
        menu_cursor_style=("fg_red", "bold"),
        menu_highlight_style=("bg_green", "bold"),
        title=f"Hardware Lab Setup - {lab_name}",
    )
    menu_entry_index = terminal_menu.show()
    if menu_entry_index == 0:
        file_based_import_hosts_menu(lab_name)
    elif menu_entry_index == 1:
        import_links_menu(lab_name)
    elif menu_entry_index == 2:
        main_menu()


def file_based_import_hosts_menu(lab_name):
    """File-based import menu for hosts - auto-detects file type."""
    print("Select a file to import hosts from:")
    
    # Get list of potential import files
    import_files = []
    for f in os.listdir("."):
        if os.path.isfile(f) and (f.endswith(('.yml', '.yaml', '.ini'))):
            import_files.append(f)
    
    if not import_files:
        print("No suitable import files found (looking for .yml, .yaml, .ini files)")
        input("Press Enter to continue...")
        hardware_import_menu(lab_name)
        return
    
    options = [f"[{i}] {file}" for i, file in enumerate(import_files, start=1)]
    options.append("[b] Back to Hardware Lab Setup")
    
    terminal_menu = TerminalMenu(
        options,
        menu_cursor_style=("fg_red", "bold"),
        menu_highlight_style=("bg_green", "bold"),
        title=f"Select Import File - {lab_name}",
    )
    menu_entry_index = terminal_menu.show()
    
    if menu_entry_index == len(options) - 1:  # Back
        hardware_import_menu(lab_name)
        return
    
    selected_file = import_files[menu_entry_index]
    
    # Auto-detect file type and call appropriate import function
    if selected_file.endswith(('.yml', '.yaml')):
        imports.import_inv_from_yaml(lab_name, selected_file)
    elif selected_file.endswith('.ini'):
        imports.import_inv_from_ini(lab_name, selected_file)
    else:
        print(f"Unsupported file type: {selected_file}")
        input("Press Enter to continue...")
    
    # Return to hardware import menu
    hardware_import_menu(lab_name)


def import_links_menu(lab_name):
    """Menu to import connections from containerlab topology style YAML."""
    print("Select a containerlab topology file to import links from:")
    
    # Get list of potential topology files
    topology_files = []
    for f in os.listdir("."):
        if os.path.isfile(f) and f.endswith(('.yml', '.yaml')):
            topology_files.append(f)
    
    if not topology_files:
        print("No YAML files found for link import")
        input("Press Enter to continue...")
        hardware_import_menu(lab_name)
        return
    
    options = [f"[{i}] {file}" for i, file in enumerate(topology_files, start=1)]
    options.append("[b] Back to Hardware Lab Setup")
    
    terminal_menu = TerminalMenu(
        options,
        menu_cursor_style=("fg_red", "bold"),
        menu_highlight_style=("bg_green", "bold"),
        title=f"Select Topology File for Links - {lab_name}",
    )
    menu_entry_index = terminal_menu.show()
    
    if menu_entry_index == len(options) - 1:  # Back
        hardware_import_menu(lab_name)
        return
    
    selected_file = topology_files[menu_entry_index]
    imports.import_links_from_containerlab(lab_name, selected_file)
    
    # Return to hardware import menu
    hardware_import_menu(lab_name)


def connect_host_menu():
    """Menu to connect to a host."""
    current_lab = lab_mgmt.get_selected_lab()
    if not current_lab:
        print("No lab selected. Please select a lab first.")
        lab_operations_menu()
        return
        
    # Query hosts from the selected lab
    hosts = session.query(Host).filter_by(lab_name=current_lab).all()
    if not hosts:
        print(f"No hosts found in lab '{current_lab}'.")
        lab_operations_menu()
        return
    
    # Get lab info to determine connection methods
    lab = session.query(Lab).filter_by(lab_name=current_lab).first()
    
    # First, show connection method selection
    connection_options = ["[s] SSH Connection", "[c] Console (Telnet)", "[b] Back to Lab Operations"]
    
    conn_menu = TerminalMenu(
        connection_options,
        menu_cursor_style=("fg_red", "bold"),
        menu_highlight_style=("bg_green", "bold"),
        title=f"Select Connection Method - Lab: {current_lab}",
    )
    conn_choice = conn_menu.show()
    
    if conn_choice == 2:  # Back to Lab Operations
        lab_operations_menu()
        return
    elif conn_choice == 0:  # SSH Connection
        show_ssh_hosts_menu(hosts, lab)
    elif conn_choice == 1:  # Console (Telnet)
        show_console_hosts_menu(hosts, lab)


def show_ssh_hosts_menu(hosts, lab):
    """Show menu for SSH connections to hosts."""
    current_lab = lab_mgmt.get_selected_lab()
    
    # Show all hosts for SSH/docker exec connections
    ssh_hosts = hosts 
    
    if not ssh_hosts:
        print("No hosts available for connection in this lab.")
        input("Press Enter to continue...")
        connect_host_menu()
        return
    
    # Use paginated menu for host selection
    def format_host(idx, host):
        return f"[{idx + 1}] {host.hostname}"
    
    selected_host = paginated_menu(
        ssh_hosts,
        page_size=9,
        title=f"SSH/Docker Connection - Lab: {current_lab}",
        format_func=format_host
    )
    
    if selected_host is None:
        connect_host_menu()
        return
    else:
        device_actions.connect_to_host(selected_host.hostname)
        # Return to lab operations menu after connection
        current_lab = lab_mgmt.get_selected_lab()
        if current_lab:
            lab_operations_menu()
        else:
            main_menu()


def show_console_hosts_menu(hosts, lab):
    """Show menu for console (telnet) connections to hosts."""
    current_lab = lab_mgmt.get_selected_lab()
    
    # Filter hosts that have console configured
    console_hosts = [host for host in hosts if host.console and host.console.strip()]
    
    if not console_hosts:
        print("No hosts with console configuration available in this lab.")
        input("Press Enter to continue...")
        connect_host_menu()
        return
    
    # Use paginated menu for host selection
    def format_host(idx, host):
        return f"[{idx + 1}] {host.hostname}"
    
    selected_host = paginated_menu(
        console_hosts,
        page_size=9,
        title=f"Console (Telnet) Connection - Lab: {current_lab}",
        format_func=format_host
    )
    
    if selected_host is None:
        connect_host_menu()
        return
    else:
        device_actions.connect_to_console(selected_host)
        connect_host_menu() 

def preview_and_run_playbook_menu():
    """Menu to preview files and run ansible-playbook."""
    current_lab = lab_mgmt.get_selected_lab()
    if not current_lab:
        print("No lab selected. Please select a lab first.")
        lab_operations_menu()
        return
        
    # Filter for Ansible playbook files (.yml and .yaml)
    playbook_files = []
    for f in os.listdir("."):
        if os.path.isfile(f) and f.endswith(('.yml', '.yaml')):
            playbook_files.append(f)
    
    if not playbook_files:
        print("No Ansible playbook files found (looking for .yml and .yaml files)")
        input("Press Enter to continue...")
        lab_operations_menu()
        return
    
    options = []
    for i, file in enumerate(playbook_files, start=1):
        options.append(f"[{i}] {file}")
    options.append("[b] Back to Lab Operations")

    def preview_command(file):
        """Function to preview the contents of a file."""
        try:
            with open(file, "r") as f:
                return f.read()
        except Exception:
            return ""

    terminal_menu = TerminalMenu(
        options,
        menu_cursor_style=("fg_red", "bold"),
        menu_highlight_style=("bg_green", "bold"),
        preview_command=preview_command,
        title=f"View and Run Ansible Playbooks - Lab: {current_lab}",
    )
    menu_entry_index = terminal_menu.show()
    if menu_entry_index == len(options) - 1:
        lab_operations_menu()
    else:
        selected_file = playbook_files[menu_entry_index]
        run_ansible_playbook(selected_file)


def run_ansible_playbook(file):
    """Function to run ansible-playbook with the selected file and arguments."""
    current_lab = lab_mgmt.get_selected_lab()
    args = input("Enter any additional arguments for ansible-playbook: ")
    command = f"ansible-playbook {file} {args}"
    try:
        subprocess.run(command, shell=True, check=False)
    except Exception as e:
        print(f"Failed to run ansible-playbook: {e}")
    
    if current_lab: 
        lab_operations_menu()
    else:
        main_menu()


def config_backup_menu():
    """Menu for configuration backup."""
    current_lab = lab_mgmt.get_selected_lab()
    if not current_lab:
        print("No lab selected. Please select a lab first.")
        lab_operations_menu()
        return
    
    # Get lab info
    lab = session.query(Lab).filter_by(lab_name=current_lab).first()
    
    options = [
        "[i] Backup Individual Host",
        "[a] Backup All Hosts",
    ]
    
    # Add containerlab-specific backup option if topology path is set
    if lab and lab.lab_type == "containerlab" and lab.topology_path:
        options.append("[c] Backup to Containerlab Directory")
    
    options.append("[b] Back to Lab Operations")
    
    terminal_menu = TerminalMenu(
        options,
        menu_cursor_style=("fg_red", "bold"),
        menu_highlight_style=("bg_green", "bold"),
        title=f"Configuration Backup - Lab: {current_lab}",
    )
    menu_entry_index = terminal_menu.show()
    if menu_entry_index == 0:
        single_host_backup_menu()
    elif menu_entry_index == 1:
        device_actions.backup_all_hosts()
        lab_operations_menu()
    elif (lab and lab.lab_type == "containerlab" and lab.topology_path and 
          menu_entry_index == len(options) - 2):
        device_actions.backup_to_containerlab_directory()
        lab_operations_menu()
    elif menu_entry_index == len(options) - 1:
        lab_operations_menu()


def single_host_backup_menu():
    """Menu to backup the configuration of a single host."""
    current_lab = lab_mgmt.get_selected_lab()
    if not current_lab:
        print("No lab selected. Please select a lab first.")
        config_backup_menu()
        return
        
    # Query hosts from the selected lab
    hosts = session.query(Host).filter_by(lab_name=current_lab).all()
    if not hosts:
        print(f"No hosts found in lab '{current_lab}'.")
        config_backup_menu()
        return
    
    # Use paginated menu for host selection
    def format_host(idx, host):
        return f"[{idx + 1}] {host.hostname}"
    
    selected_host = paginated_menu(
        hosts,
        page_size=9,
        title=f"Backup Individual Host - Lab: {current_lab}",
        format_func=format_host
    )
    
    if selected_host is None:
        config_backup_menu()
        return
    else:
        device_actions.backup_host_config(selected_host)
        # Return to the single host backup menu after execution
        single_host_backup_menu()

def interface_management_menu():
    """Menu for interface management."""
    
    selected_lab = lab_mgmt.get_selected_lab()
    if not selected_lab:
        print("No lab selected. Please select a lab first.")
        lab_operations_menu()
        return
    
    # Get lab type to determine available options
    lab = session.query(Lab).filter_by(lab_name=selected_lab).first()
    lab_type = lab.lab_type if lab else "containerlab"
        
    options = [
        "[e] Enable or Disable Interfaces",
    ]
    
    # Only show impairment option for containerlab
    if lab_type == "containerlab":
        options.append("[i] Impair Interfaces")
    
    options.append("[b] Back to Lab Operations")
    
    terminal_menu = TerminalMenu(
        options,
        menu_cursor_style=("fg_red", "bold"),
        menu_highlight_style=("bg_green", "bold"),
        title=f"Interface Management - Lab: {selected_lab} ({lab_type})",
    )
    menu_entry_index = terminal_menu.show()
    if menu_entry_index == 0:
        enable_disable_interfaces_menu()
    elif lab_type == "containerlab" and menu_entry_index == 1:
        impair_interfaces_menu()
    elif menu_entry_index == len(options) - 1:
        lab_operations_menu()


def enable_disable_interfaces_menu():
    """Menu to enable or disable network interfaces."""
     
    selected_lab = lab_mgmt.get_selected_lab()
    if not selected_lab:
        print("No lab selected. Please select a lab first.")
        interface_management_menu()
        return
        
    links = session.query(Link).filter_by(lab_name=selected_lab).all()
    if not links:
        print(f"No links found in lab '{selected_lab}'.")
        interface_management_menu()
        return
    
    # Use paginated menu for link selection
    def format_link(idx, link):
        return (f"[{idx + 1}] {link.source_host}:{link.source_interface} -> "
                f"{link.destination_host}:{link.destination_interface} "
                f"(State: {link.state})")
    
    selected_link = paginated_menu(
        links,
        page_size=9,
        title=f"Enable or Disable Interfaces - Lab: {selected_lab}",
        format_func=format_link
    )
    
    if selected_link is None:
        interface_management_menu()
        return
    else:
        interface_actions.enable_disable_interfaces(selected_link)
        enable_disable_interfaces_menu()


def impair_interfaces_menu():
    """Menu to impair network interfaces."""
    
    selected_lab = lab_mgmt.get_selected_lab()
    if not selected_lab:
        print("No lab selected. Please select a lab first.")
        interface_management_menu()
        return
        
    links = session.query(Link).filter_by(lab_name=selected_lab).all()
    if not links:
        print(f"No links found in lab '{selected_lab}'.")
        interface_management_menu()
        return
    
    # Use paginated menu for link selection
    def format_link(idx, link):
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
        impairments_str = (", ".join(impairments) if impairments else "No impairments")
        
        return (f"[{idx + 1}] {link.source_host}:{link.source_interface} -> "
                f"{link.destination_host}:{link.destination_interface} "
                f"({impairments_str})")
    
    selected_link = paginated_menu(
        links,
        page_size=9,
        title=f"Impair Interfaces - Lab: {selected_lab}",
        format_func=format_link
    )
    
    if selected_link is None:
        interface_management_menu()
        return
    else:
        interface_actions.manage_impairment(selected_link)
        impair_interfaces_menu()


def select_lab_menu():
    """Menu to select a lab for operations."""
    
    labs = session.query(Lab).all()
    
    if not labs:
        print("No labs available. Please import hosts first to create a lab.")
        main_menu()
        return
    
    # Use paginated menu for lab selection
    def format_lab(idx, lab):
        return f"[{idx + 1}] {lab.lab_name} ({lab.lab_type})"
    
    selected_lab_obj = paginated_menu(
        labs,
        page_size=9,
        title="Select Lab",
        format_func=format_lab
    )
    
    if selected_lab_obj is None:
        main_menu()
        return
    else:
        selected_lab_name = selected_lab_obj.lab_name
        lab_mgmt.set_selected_lab(selected_lab_name)
        lab_operations_menu()


def lab_operations_menu():
    """Sub-menu for lab-specific operations."""
    
    selected_lab = lab_mgmt.get_selected_lab()
    if not selected_lab:
        select_lab_menu()
        return
    
    # Get lab info to show type in title
    lab = session.query(Lab).filter_by(lab_name=selected_lab).first()
    lab_type = lab.lab_type if lab else "unknown"
        
    options = [
        "[c] Connect to Host",
        "[a] View and Run Ansible Playbooks", 
        "[m] Interface Management",
        "[b] Backup Device Configurations",
        "[x] Back to Lab Selection",
        "[e] Exit to Main Menu",
    ]
    terminal_menu = TerminalMenu(
        options,
        menu_cursor_style=("fg_red", "bold"),
        menu_highlight_style=("bg_green", "bold"),
        title=f"Lab Operations - {selected_lab} ({lab_type})",
    )
    menu_entry_index = terminal_menu.show()
    
    
    if menu_entry_index == 0:
        connect_host_menu()
    elif menu_entry_index == 1:
        preview_and_run_playbook_menu()
    elif menu_entry_index == 2:
        interface_management_menu()
    elif menu_entry_index == 3:
        config_backup_menu()
    elif menu_entry_index == 4:
        lab_mgmt.set_selected_lab(None)
        select_lab_menu()
    elif menu_entry_index == 5:
        lab_mgmt.set_selected_lab(None)
        main_menu()


def manage_labs_menu():
    """Menu for managing labs."""
    
    options = [
        "[v] View All Labs",
        "[r] Rename Lab",
        "[d] Delete Lab",
        "[s] Manage Lab Settings",
        "[b] Back to Main Menu",
    ]
    terminal_menu = TerminalMenu(
        options,
        menu_cursor_style=("fg_red", "bold"),
        menu_highlight_style=("bg_green", "bold"),
        title="Manage Labs",
    )
    menu_entry_index = terminal_menu.show()
    
    if menu_entry_index == 0:
        lab_mgmt.view_all_labs()
    elif menu_entry_index == 1:
        lab_mgmt.rename_lab()
    elif menu_entry_index == 2:
        lab_mgmt.delete_lab()
    elif menu_entry_index == 3:
        lab_mgmt.manage_lab_settings()
    elif menu_entry_index == 4:
        main_menu()


if __name__ == "__main__":
    main_menu()










