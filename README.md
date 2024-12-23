# POC Helper Menu

This is a Python-based terminal application for managing and connecting to hosts. It allows you to import hosts from Ansible inventory files or manually add them, and then connect to these hosts via SSH.

## Features

- Import hosts from Ansible YAML inventory files.
- Connect to hosts via SSH.
- Simple terminal menu interface.
- Enable or disable network interfaces.
- Impair network interfaces with delay, jitter, packet loss, rate limiting, and packet corruption.

## Requirements

- Python 3.x
- `PyYAML` for parsing YAML files.
- `SQLAlchemy` for database operations.
- `simple-term-menu` for the terminal menu interface.
- `tabulate` for tabulating data to be printed.

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/marccolburn/poc_helper_menu.git
    cd poc_helper_menu
    ```

2. Install the required Python packages:
    ```sh
    pip install -r requirements.txt
    ```

## Usage

1. Run the main application:
    ```sh
    python main.py
    ```

2. Import hosts:
    - Import YAML:
        - The application will search for a default YAML file (`ansible-inventory.yml`) in the current directory and `../clab*/` directory.
        - If the default file is found, you will be prompted to use it. If not, you can specify the path to your YAML file.
    - Import INI:
        - The application will search for a default INI file (`ansible-inventory.ini`) in the current directory and parent directory.
        - If the default file is found, you will be prompted to use it. If not, you can specify the path to your INI file.
    - Manual import:
        - You can manually enter host information through the terminal menu.

3. Import links:
    - The application will search for a default containerlab topology file (`topology.yml`) in the current directory and parent directory.
    - If the default file is found, you will be prompted to use it. If not, you can specify the path to your topology YAML file.
    - If not using containerlab, you can still import your topology if described in containerlab yaml format

4. Enable/disable interfaces:
    - Navigate to "Interface Management" -> "Enable or Disable Interfaces".
    - Select an interface to enable or disable it.

5. Link impairment:
    - This will only work for containerlab at this time
    - Navigate to "Interface Management" -> "Impair Interfaces".
    - Select a link to view and manage its impairments.
    - If the link has no impairments, you can set delay, jitter, packet loss, rate limiting, and packet corruption.
    - If the link has impairments, you can choose to remove them or update the values.

## File Structure

- `main.py`: The main application file containing the terminal menu and functions for importing and connecting to hosts.
- `models.py`: The database schema definition using SQLAlchemy.

## Database Schema

The application uses SQLite for storing host information. The schema is defined in `models.py` and includes the following fields:

### Hosts Table
- `id`: Integer, primary key.
- `hostname`: String, unique, not nullable.
- `ip_address`: String, not nullable.
- `network_os`: String, not nullable.
- `connection`: String, not nullable.
- `username`: String, not nullable.
- `password`: String, not nullable.

### Links Table

- `id`: Integer, primary key.
- `source_host`: String, not nullable.
- `source_interface`: String, not nullable.
- `destination_host`: String, not nullable.
- `destination_interface`: String, not nullable.
- `jitter`: Float, default 0, not nullable.
- `latency`: Float, default 0, not nullable.
- `loss`: Float, default 0, not nullable.
- `rate`: Float, default 0, not nullable.
- `corruption`: Float, default 0, not nullable.
- `state`: String, default 'enabled', not nullable.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.