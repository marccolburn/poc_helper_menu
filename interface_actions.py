"""Interface management functions for the POC Helper Menu tool."""

import subprocess
from simple_term_menu import TerminalMenu
from models import Host, Link, Lab, session
import main

def manage_impairment(link):
    """Function to manage impairments on a network interface."""
    impairments = {
        "jitter": link.jitter,
        "latency": link.latency,
        "loss": link.loss,
        "rate": link.rate,
        "corruption": link.corruption,
    }
    non_zero_impairments = {k: v for k, v in impairments.items() if v != 0}
    if non_zero_impairments:
        print(
            (
                f"Current impairments on "
                f"{link.source_host}:{link.source_interface} -> "
                f"{link.destination_host}:{link.destination_interface}:"
            )
        )
        for k, v in non_zero_impairments.items():
            print(f"{k.capitalize()}: {v}")
        remove = (
            input("Do you want to remove the impairments? (y/n): ")
            .strip()
            .lower()
        )
        if remove == "y":
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

    options = [
        "[d] Delay and Jitter",
        "[l] Latency",
        "[o] Loss",
        "[r] Rate",
        "[c] Corruption",
        "[b] Back to Impair Interfaces",
    ]
    terminal_menu = TerminalMenu(
        options,
        menu_cursor_style=("fg_red", "bold"),
        menu_highlight_style=("bg_green", "bold"),
        title="Set Impairments",
    )
    menu_entry_index = terminal_menu.show()
    if menu_entry_index == len(options) - 1:
        main.impair_interfaces_menu()
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
        apply_impairments(link)
        manage_impairment(link)


def apply_impairments(link):
    """
    Function to apply impairments to a network interface using containerlab
        tools netem set. Supports remote execution if lab has remote_containerlab_host set.
    """
    from device_actions import execute_remote_command
    
    lab = session.query(Lab).filter_by(lab_name=link.lab_name).first()
    if not lab:
        print(f"Lab {link.lab_name} not found in database.")
        return
    
    host = (
        session.query(Host)
        .filter(Host.hostname.contains(link.source_host))
        .filter(Host.lab_name == link.lab_name)
        .first()
    )
    if not host:
        print(f"Host {link.source_host} not found in lab {link.lab_name}.")
        return

    # Construct the containerlab container name: clab-{containerlab_name}-{hostname}
    if lab.containerlab_name:
        container_name = f"clab-{lab.containerlab_name}-{host.hostname}"
    else:
        # Fallback to just hostname if containerlab_name is not set
        container_name = host.hostname
        print(f"Warning: No containerlab_name found for lab {link.lab_name}, using hostname only")

    command = (
        f"sudo containerlab tools netem set -n {container_name} "
        f"-i {link.source_interface}"
    )
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

    print(f"Using container name: {container_name}")

    # Execute locally or remotely based on lab configuration
    if lab.remote_containerlab_host:
        # Remote execution using helper function
        success = execute_remote_command(
            lab.remote_containerlab_host,
            lab.remote_containerlab_username,
            command,
            "impairments"
        )
        if not success:
            print("Failed to apply remote impairments.")
    else:
        # Local execution
        print(f"Applying impairments locally: {command}")
        try:
            subprocess.run(command, shell=True, check=False)
            print("Impairments applied successfully.")
        except Exception as e:
            print(f"Failed to apply impairments: {e}")


def enable_disable_interfaces(link):
    """
    Function to enable or disable network interfaces based on lab type.
    - Hardware labs: Disable only the source interface
    - Containerlab labs: Disable both source and destination interfaces
    """
    import lab_mgmt
    import device_actions
    
    selected_lab = lab_mgmt.get_selected_lab()
    
    # Get lab information to determine type
    lab = session.query(Lab).filter_by(lab_name=link.lab_name).first()
    if not lab:
        print(f"Lab {link.lab_name} not found in database.")
        main.enable_disable_interfaces_menu()
        return
    
    action = "disable" if link.state == "enabled" else "enable"
    print(f"Lab type: {lab.lab_type}")
    
    if lab.lab_type == "hardware":
        # Hardware lab - only manage source interface
        source_host = (
            session.query(Host)
            .filter(Host.hostname.contains(link.source_host))
            .filter(Host.lab_name == link.lab_name)
            .first()
        )
        
        if not source_host:
            print(f"Source host {link.source_host} not found in lab {link.lab_name}.")
            main.enable_disable_interfaces_menu()
            return

        print(f"Managing interface {link.source_interface} on {link.source_host}...")

        if source_host.network_os == "linux":
            command = f"ip link set {link.source_interface} {'up' if action == 'enable' else 'down'}"
        elif source_host.network_os == "junos":
            command = f"configure; set interfaces {link.source_interface} {action}; commit and-quit"
        else:
            print(f"Unsupported network OS: {source_host.network_os}")
            return

        print(f"Command to be executed: {command}")

        try:
            device_actions.connect_to_host(source_host.hostname, command)
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

    else:
        # Containerlab - manage both source and destination interfaces
        source_host = (
            session.query(Host)
            .filter(Host.hostname.contains(link.source_host))
            .filter(Host.lab_name == link.lab_name)
            .first()
        )
        destination_host = (
            session.query(Host)
            .filter(Host.hostname.contains(link.destination_host))
            .filter(Host.lab_name == link.lab_name)
            .first()
        )

        if not source_host and not destination_host:
            print(
                (
                    f"Both source host {link.source_host} and "
                    f"destination host {link.destination_host} not found "
                    f"in lab {link.lab_name}."
                )
            )
            return

        if not source_host:
            print(
                f"Source host {link.source_host} not found in lab {link.lab_name}. "
                f"Only managing destination interface."
            )
        elif not destination_host:
            print(
                f"Destination host {link.destination_host} not found in "
                f"lab {link.lab_name}. Only managing source interface."
            )
        else:
            print(
                f"Managing interface {link.source_interface} on {link.source_host} "
                f"and {link.destination_interface} on {link.destination_host}..."
            )

        source_command = None
        destination_command = None

        if source_host:
            if source_host.network_os == "linux":
                source_command = (
                    f"ip link set {link.source_interface} "
                    f"{'up' if action == 'enable' else 'down'}"
                )
            elif source_host.network_os == "junos":
                source_command = (
                    f"configure; set interfaces {link.source_interface} {action}; "
                    f"commit and-quit"
                )
            else:
                print(f"Unsupported network OS: {source_host.network_os}")

        if destination_host:
            if destination_host.network_os == "linux":
                destination_command = (
                    f"ip link set {link.destination_interface} "
                    f"{'up' if action == 'enable' else 'down'}"
                )
            elif destination_host.network_os == "junos":
                destination_command = (
                    f"configure; "
                    f"set interfaces {link.destination_interface} {action}; "
                    f"commit and-quit"
                )
            else:
                print(f"Unsupported network OS: {destination_host.network_os}")

        if source_command:
            print(f"Source command to be executed: {source_command}")
        if destination_command:
            print(f"Destination command to be executed: {destination_command}")

        try:
            if source_command:
                device_actions.connect_to_host(source_host.hostname, source_command)
            if destination_command:
                device_actions.connect_to_host(destination_host.hostname, destination_command)
            link.state = "disabled" if link.state == "enabled" else "enabled"
            session.add(link)  # Mark the link object as dirty
            session.commit()
            # Verify the update by querying the database
            updated_link = session.query(Link).filter_by(id=link.id).first()
            print(f"Verified link state in database: {updated_link.state}")
            
            if lab.lab_type == "containerlab":
                print(
                    (
                        f"Interfaces {link.source_interface} on {link.source_host} and "
                        f"{link.destination_interface} on {link.destination_host} have "
                        f"been {link.state}."
                    )
                )
            else:
                print(f"Interface {link.source_interface} on {link.source_host} has been {link.state}.")
        except Exception as e:
            print(f"Failed to manage interfaces: {e}")
            session.rollback()  # Rollback in case of an error
