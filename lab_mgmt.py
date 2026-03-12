"""
Lab Management Module

This module contains all functions related to lab management including:
- Lab creation, selection, and validation
- Lab CRUD operations (view, rename, delete)
- Lab settings management
- Lab operations menu
"""

import re
from simple_term_menu import TerminalMenu
from tabulate import tabulate
from models import Host, Link, Lab, session
import main


# Global variable to track selected lab
selected_lab = None


def validate_lab_name(lab_name):
    """Validate lab name contains only alphanumeric, underscore, and hyphen characters."""
    if not re.match("^[a-zA-Z0-9_-]+$", lab_name):
        return False
    return True


def get_or_create_lab(prompt_text="Enter lab name"):
    """Get existing lab or create new lab."""
    labs = session.query(Lab).all()
    
    if labs:
        options = [f"[{i}] {lab.lab_name}" for i, lab in enumerate(labs, start=1)]
        options.append("[n] Create New Lab")
        options.append("[b] Back")
        
        terminal_menu = TerminalMenu(
            options,
            menu_cursor_style=("fg_red", "bold"),
            menu_highlight_style=("bg_green", "bold"),
            title=prompt_text,
        )
        menu_entry_index = terminal_menu.show()
        
        if menu_entry_index == len(options) - 1:  # Back
            return None
        elif menu_entry_index == len(options) - 2:  # Create New Lab
            return create_new_lab()
        else:
            return labs[menu_entry_index].lab_name
    else:
        print("No labs exist. Creating your first lab.")
        return create_new_lab()


def create_new_lab():
    """Create a new lab."""
    while True:
        lab_name = input("Enter new lab name (only letters, numbers, _ and - allowed): ").strip()
        if not lab_name:
            print("Lab name cannot be empty.")
            continue
        if not validate_lab_name(lab_name):
            print("Invalid lab name. Only letters, numbers, underscores, and hyphens are allowed.")
            continue
        
        # Check if lab already exists
        existing_lab = session.query(Lab).filter_by(lab_name=lab_name).first()
        if existing_lab:
            print(f"Lab '{lab_name}' already exists.")
            continue
        
        # Select lab type
        lab_type_options = [
            "[1] Hardware Lab",
            "[2] Containerlab",
        ]
        terminal_menu = TerminalMenu(
            lab_type_options,
            menu_cursor_style=("fg_red", "bold"),
            menu_highlight_style=("bg_green", "bold"),
            title="Select Lab Type",
        )
        lab_type_index = terminal_menu.show()
        lab_type = "hardware" if lab_type_index == 0 else "containerlab"
        
        description = input("Enter lab description (optional): ").strip()
        
        # For containerlab, ask for remote host and topology path
        remote_host = None
        remote_username = None
        topology_path = None
        if lab_type == "containerlab":
            remote_host = (
                input("Enter remote containerlab host (SSH hostname/IP, \
                      leave empty for local): ").strip()
            )
            remote_host = remote_host if remote_host else None
            if remote_host:
                remote_username = (
                    input("Enter SSH username for remote host \
                        (leave empty to use current user): ").strip()
                )
                remote_username = remote_username if remote_username else None
            
            topology_path = (
                input("Enter path to containerlab topology directory \
                    (optional, for config backup): ").strip()
            )
            topology_path = topology_path if topology_path else None
        
        new_lab = Lab(
            lab_name=lab_name, 
            description=description or None, 
            lab_type=lab_type,
            remote_containerlab_host=remote_host,
            remote_containerlab_username=remote_username,
            topology_path=topology_path
        )
        session.add(new_lab)
        session.commit()
        print(f"Lab '{lab_name}' ({lab_type}) created successfully.")
        return lab_name

def view_all_labs():
    """Display all labs with their host and link counts."""
    labs = session.query(Lab).all()
    if not labs:
        print("No labs found.")
    else:
        lab_data = []
        for lab in labs:
            host_count = session.query(Host).filter_by(lab_name=lab.lab_name).count()
            link_count = session.query(Link).filter_by(lab_name=lab.lab_name).count()
            if lab.lab_type == "containerlab":
                if lab.remote_containerlab_host:
                    username_part = (
                        f"{lab.remote_containerlab_username}@" if lab.remote_containerlab_username else ""
                    )
                    remote_host = f"{username_part}{lab.remote_containerlab_host}"
                else:
                    remote_host = "Local"
            else:
                remote_host = "N/A"
            
            lab_data.append([
                lab.lab_name,
                lab.description or "No description",
                lab.lab_type,
                remote_host,
                host_count,
                link_count
            ])
        
        print(tabulate(
            lab_data,
            headers=["Lab Name", "Description", "Type", "Remote Host", "Hosts", "Links"],
            tablefmt="grid"
        ))
    
    input("Press Enter to continue...")
    main.manage_labs_menu()


def rename_lab():
    """Rename an existing lab."""
    labs = session.query(Lab).all()
    if not labs:
        print("No labs available to rename.")
        main.manage_labs_menu()
        return
    
    options = [f"[{i}] {lab.lab_name}" for i, lab in enumerate(labs, start=1)]
    options.append("[b] Back to Manage Labs")
    
    terminal_menu = TerminalMenu(
        options,
        menu_cursor_style=("fg_red", "bold"),
        menu_highlight_style=("bg_green", "bold"),
        title="Select Lab to Rename",
    )
    menu_entry_index = terminal_menu.show()
    
    if menu_entry_index == len(options) - 1:
        main.manage_labs_menu()
        return
    
    selected_lab_obj = labs[menu_entry_index]
    old_name = selected_lab_obj.lab_name
    
    while True:
        new_name = input(f"Enter new name for lab '{old_name}': ").strip()
        if not new_name:
            print("Lab name cannot be empty.")
            continue
        if not validate_lab_name(new_name):
            print("Invalid lab name. Only letters, numbers, underscores, and hyphens are allowed.")
            continue
        if new_name == old_name:
            print("New name is the same as the old name.")
            main.manage_labs_menu()
            return
            
        # Check if new name already exists
        existing_lab = session.query(Lab).filter_by(lab_name=new_name).first()
        if existing_lab:
            print(f"Lab '{new_name}' already exists.")
            continue
        
        # Update lab name and all related records
        selected_lab_obj.lab_name = new_name
        session.query(Host).filter_by(lab_name=old_name).update({Host.lab_name: new_name})
        session.query(Link).filter_by(lab_name=old_name).update({Link.lab_name: new_name})
        session.commit()
        print(f"Lab renamed from '{old_name}' to '{new_name}' successfully.")
        break
    
    main.manage_labs_menu()


def delete_lab():
    """Delete a lab and all associated data."""
    labs = session.query(Lab).all()
    if not labs:
        print("No labs available to delete.")
        main.manage_labs_menu()
        return
    
    options = [f"[{i}] {lab.lab_name}" for i, lab in enumerate(labs, start=1)]
    options.append("[b] Back to Manage Labs")
    
    terminal_menu = TerminalMenu(
        options,
        menu_cursor_style=("fg_red", "bold"),
        menu_highlight_style=("bg_green", "bold"),
        title="Select Lab to Delete",
    )
    menu_entry_index = terminal_menu.show()
    
    if menu_entry_index == len(options) - 1:
        main.manage_labs_menu()
        return
    
    selected_lab_obj = labs[menu_entry_index]
    lab_name = selected_lab_obj.lab_name
    
    # Show what will be deleted
    host_count = session.query(Host).filter_by(lab_name=lab_name).count()
    link_count = session.query(Link).filter_by(lab_name=lab_name).count()
    
    print(f"\nWarning: This will delete lab '{lab_name}' and all associated data:")
    print(f"  - {host_count} hosts")
    print(f"  - {link_count} links")
    
    confirm = input("\nAre you sure you want to delete this lab? (yes/no): ").strip().lower()
    if confirm == "yes":
        # Delete all associated data
        session.query(Host).filter_by(lab_name=lab_name).delete()
        session.query(Link).filter_by(lab_name=lab_name).delete()
        session.delete(selected_lab_obj)
        session.commit()
        print(f"Lab '{lab_name}' and all associated data deleted successfully.")
    else:
        print("Deletion cancelled.")
    
    main.manage_labs_menu()


def manage_lab_settings():
    """Manage settings for an existing lab."""
    labs = session.query(Lab).all()
    if not labs:
        print("No labs available to manage.")
        main.manage_labs_menu()
        return
    
    options = [f"[{i}] {lab.lab_name} ({lab.lab_type})" for i, lab in enumerate(labs, start=1)]
    options.append("[b] Back to Manage Labs")
    
    terminal_menu = TerminalMenu(
        options,
        menu_cursor_style=("fg_red", "bold"),
        menu_highlight_style=("bg_green", "bold"),
        title="Select Lab to Manage Settings",
    )
    menu_entry_index = terminal_menu.show()
    
    if menu_entry_index == len(options) - 1:
        main.manage_labs_menu()
        return
    
    selected_lab_obj = labs[menu_entry_index]
    
    # Settings menu
    settings_options = [
        "[t] Change Lab Type",
        "[d] Change Description",
    ]
    
    # Add containerlab-specific options
    if selected_lab_obj.lab_type == "containerlab":
        settings_options.insert(2, "[r] Set Remote Containerlab Host")
        settings_options.insert(3, "[p] Set Topology Path")
    
    settings_options.append("[b] Back to Manage Labs")
    
    terminal_menu = TerminalMenu(
        settings_options,
        menu_cursor_style=("fg_red", "bold"),
        menu_highlight_style=("bg_green", "bold"),
        title=f"Manage Settings for Lab: {selected_lab_obj.lab_name}",
    )
    settings_index = terminal_menu.show()
    
    if settings_index == 0:  
        current_type = selected_lab_obj.lab_type
        new_type = "containerlab" if current_type == "hardware" else "hardware"
        confirm = input(f"Change lab type from '{current_type}' to '{new_type}'? (y/n): ").strip().lower()
        if confirm == "y":
            selected_lab_obj.lab_type = new_type
            # Clear remote host if changing to hardware
            if new_type == "hardware":
                selected_lab_obj.remote_containerlab_host = None
                selected_lab_obj.remote_containerlab_username = None
            session.commit()
            print(f"Lab type changed to '{new_type}' successfully.")
        else:
            print("Lab type change cancelled.")
    elif settings_index == 1:
        current_desc = selected_lab_obj.description or "No description"
        print(f"Current description: {current_desc}")
        new_desc = input("Enter new description (press Enter to keep current): ").strip()
        if new_desc:
            selected_lab_obj.description = new_desc
            session.commit()
            print("Description updated successfully.")
        else:
            print("Description unchanged.")
    elif (selected_lab_obj.lab_type == "containerlab" and settings_index == 2): 
        current_host = selected_lab_obj.remote_containerlab_host or "Not set"
        current_username = selected_lab_obj.remote_containerlab_username or "Not set"
        print(f"Current remote containerlab host: {current_host}")
        print(f"Current remote username: {current_username}")
        
        new_host = input("Enter remote host (SSH hostname/IP, leave empty for local): ").strip()
        new_username = None
        
        if new_host:
            new_username = (
                input("Enter SSH username for remote host (leave empty to use current user): ").strip()
            )
            new_username = new_username if new_username else None
        
        selected_lab_obj.remote_containerlab_host = new_host if new_host else None
        selected_lab_obj.remote_containerlab_username = new_username
        session.commit()
        
        if new_host:
            username_desc = new_username if new_username else "current user"
            print(f"Remote containerlab host set to: {new_host} (username: {username_desc})")
        else:
            print("Remote containerlab host set to: local execution")
    elif (selected_lab_obj.lab_type == "containerlab" and settings_index == 3):
        current_path = selected_lab_obj.topology_path or "Not set"
        print(f"Current topology path: {current_path}")
        
        new_path = input("Enter path to containerlab topology directory (leave empty to clear): ").strip()
        selected_lab_obj.topology_path = new_path if new_path else None
        session.commit()
        
        if new_path:
            print(f"Topology path set to: {new_path}")
        else:
            print("Topology path cleared.")
    
    manage_lab_settings()


def edit_lab_hosts():
    """Select a lab and host to edit host information."""
    labs = session.query(Lab).all()
    if not labs:
        print("No labs available.")
        main.manage_labs_menu()
        return

    options = [f"[{i}] {lab.lab_name} ({lab.lab_type})" for i, lab in enumerate(labs, start=1)]
    options.append("[b] Back to Manage Labs")

    terminal_menu = TerminalMenu(
        options,
        menu_cursor_style=("fg_red", "bold"),
        menu_highlight_style=("bg_green", "bold"),
        title="Select Lab to Edit Hosts",
    )
    menu_entry_index = terminal_menu.show()

    if menu_entry_index == len(options) - 1:
        main.manage_labs_menu()
        return

    selected_lab_obj = labs[menu_entry_index]
    edit_host_select(selected_lab_obj.lab_name)


def edit_host_select(lab_name):
    """Select a host from a lab to edit."""
    hosts = session.query(Host).filter_by(lab_name=lab_name).all()
    if not hosts:
        print(f"No hosts found in lab '{lab_name}'.")
        input("Press Enter to continue...")
        edit_lab_hosts()
        return

    options = [
        f"[{i}] {host.hostname} ({host.ip_address})"
        for i, host in enumerate(hosts, start=1)
    ]
    options.append("[b] Back")

    terminal_menu = TerminalMenu(
        options,
        menu_cursor_style=("fg_red", "bold"),
        menu_highlight_style=("bg_green", "bold"),
        title=f"Select Host to Edit - Lab: {lab_name}",
    )
    menu_entry_index = terminal_menu.show()

    if menu_entry_index == len(options) - 1:
        edit_lab_hosts()
        return

    edit_host_fields(hosts[menu_entry_index], lab_name)


def edit_host_fields(host, lab_name):
    """Edit individual fields of a host."""
    REQUIRED_FIELDS = {"hostname", "ip_address", "network_os", "username", "password", "image_type"}

    field_map = [
        ("hostname",    "Hostname"),
        ("ip_address",  "IP Address"),
        ("network_os",  "Network OS"),
        ("username",    "Username"),
        ("password",    "Password"),
        ("image_type",  "Image Type"),
        ("console",     "Console"),
    ]

    while True:
        options = [
            f"[{i+1}] {label:<12} {getattr(host, attr) or 'Not set'}"
            for i, (attr, label) in enumerate(field_map)
        ]
        options.append("[b] Back to Host Selection")

        terminal_menu = TerminalMenu(
            options,
            menu_cursor_style=("fg_red", "bold"),
            menu_highlight_style=("bg_green", "bold"),
            title=f"Edit Host: {host.hostname} - Lab: {lab_name}",
        )
        menu_entry_index = terminal_menu.show()

        if menu_entry_index == len(options) - 1:
            edit_host_select(lab_name)
            return

        attr, label = field_map[menu_entry_index]
        current_val = getattr(host, attr) or "Not set"
        print(f"Current {label}: {current_val}")
        new_val = input(f"Enter new {label} (press Enter to keep current): ").strip()

        if not new_val:
            print(f"{label} unchanged.")
            continue

        if not new_val and attr in REQUIRED_FIELDS:
            print(f"{label} is required and cannot be empty.")
            continue

        setattr(host, attr, new_val if new_val else None)
        session.commit()
        print(f"{label} updated successfully.")


def edit_lab_links():
    """Select a lab and link to edit link endpoint information."""
    labs = session.query(Lab).all()
    if not labs:
        print("No labs available.")
        main.manage_labs_menu()
        return

    options = [f"[{i}] {lab.lab_name} ({lab.lab_type})" for i, lab in enumerate(labs, start=1)]
    options.append("[b] Back to Manage Labs")

    terminal_menu = TerminalMenu(
        options,
        menu_cursor_style=("fg_red", "bold"),
        menu_highlight_style=("bg_green", "bold"),
        title="Select Lab to Edit Links",
    )
    menu_entry_index = terminal_menu.show()

    if menu_entry_index == len(options) - 1:
        main.manage_labs_menu()
        return

    selected_lab_obj = labs[menu_entry_index]
    edit_link_select(selected_lab_obj.lab_name)


def edit_link_select(lab_name):
    """Select a link from a lab to edit."""
    links = session.query(Link).filter_by(lab_name=lab_name).all()
    if not links:
        print(f"No links found in lab '{lab_name}'.")
        input("Press Enter to continue...")
        edit_lab_links()
        return

    options = [
        f"[{i}] {link.source_host}:{link.source_interface} -> "
        f"{link.destination_host}:{link.destination_interface}"
        for i, link in enumerate(links, start=1)
    ]
    options.append("[b] Back")

    terminal_menu = TerminalMenu(
        options,
        menu_cursor_style=("fg_red", "bold"),
        menu_highlight_style=("bg_green", "bold"),
        title=f"Select Link to Edit - Lab: {lab_name}",
    )
    menu_entry_index = terminal_menu.show()

    if menu_entry_index == len(options) - 1:
        edit_lab_links()
        return

    edit_link_fields(links[menu_entry_index], lab_name)


def edit_link_fields(link, lab_name):
    """Edit source and destination fields of a link."""
    field_map = [
        ("source_host",            "Source Host"),
        ("source_interface",       "Source Interface"),
        ("destination_host",       "Destination Host"),
        ("destination_interface",  "Destination Interface"),
    ]

    while True:
        options = [
            f"[{i+1}] {label:<24} {getattr(link, attr)}"
            for i, (attr, label) in enumerate(field_map)
        ]
        options.append("[b] Back to Link Selection")

        terminal_menu = TerminalMenu(
            options,
            menu_cursor_style=("fg_red", "bold"),
            menu_highlight_style=("bg_green", "bold"),
            title=(
                f"Edit Link: {link.source_host}:{link.source_interface} -> "
                f"{link.destination_host}:{link.destination_interface} - Lab: {lab_name}"
            ),
        )
        menu_entry_index = terminal_menu.show()

        if menu_entry_index == len(options) - 1:
            edit_link_select(lab_name)
            return

        attr, label = field_map[menu_entry_index]
        print(f"Current {label}: {getattr(link, attr)}")
        new_val = input(f"Enter new {label} (press Enter to keep current): ").strip()

        if not new_val:
            print(f"{label} unchanged.")
            continue

        setattr(link, attr, new_val)
        session.commit()
        print(f"{label} updated successfully.")


def get_selected_lab():
    """Get the currently selected lab."""
    return selected_lab


def set_selected_lab(lab_name):
    """Set the currently selected lab."""
    global selected_lab
    selected_lab = lab_name
