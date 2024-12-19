# POC Helper Menu

This is a Python-based terminal application for managing and connecting to hosts. It allows you to import hosts from Ansible inventory files or manually add them, and then connect to these hosts via SSH.

## Features

- Import hosts from Ansible YAML inventory files.
- Connect to hosts via SSH.
- Simple terminal menu interface.

## Requirements

- Python 3.x
- `PyYAML` for parsing YAML files.
- `SQLAlchemy` for database operations.
- `simple-term-menu` for the terminal menu interface.

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

2. Follow the on-screen menu to import hosts or connect to a host.

## File Structure

- `main.py`: The main application file containing the terminal menu and functions for importing and connecting to hosts.
- `models.py`: The database schema definition using SQLAlchemy.

## Database Schema

The application uses SQLite for storing host information. The schema is defined in `models.py` and includes the following fields:

- `id`: Integer, primary key.
- `hostname`: String, unique, not nullable.
- `ip_address`: String, not nullable.
- `network_os`: String, not nullable.
- `connection`: String, not nullable.
- `username`: String, not nullable.
- `password`: String, not nullable.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.