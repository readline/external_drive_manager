# External Drive Manager

A Python-based catalog system for managing cold storage drives. Track datasets across external hard drives with a searchable SQLite database, web interface, and command-line tools.

## Features

- **Drive Management**: Register external drives with custom labels, serial numbers, and notes
- **File Catalog**: Track filename, size, timestamps, extensions, and full paths
- **Search & Filter**: Case-sensitive search with wildcards (`*`, `?`), filter by drive/extension/size/date
- **Web UI**: Interactive dashboard for browsing and searching files
- **CLI**: Comprehensive command-line interface for automation and scripting
- **CSV Export**: Export search results for offline analysis
- **Drive Capacity Tracking**: Store total drive size and available space in database
- **Scan Reports**: Automatically creates gzipped scan reports on each drive

## Author

**Kai Yu**  
Email: kaiyu062@gmail.com  
Developed with assistance from Kimi 2.5 and OpenCode

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Requirements

- Python 3.10+
- [Pixi](https://pixi.sh/) package manager
- Linux or macOS

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/external_drive_manager.git
cd external_drive_manager

# Install dependencies
pixi install

# Initialize the database (creates data/catalog.db automatically on first run)
./ext_drive_manager drive list
```

## Quick Start

### 1. Detect Drive Information

Before adding a drive, detect its metadata:

```bash
./ext_drive_manager drive meta /mnt/your-drive
```

### 2. Add a Drive

```bash
./ext_drive_manager drive add 28T-02 --serial ABC123 --path /mnt/ext_2 --note "Backup drive for raw data"
```

### 3. Scan the Drive

```bash
./ext_drive_manager drive scan 28T-02
```

This will:
- Scan all files on the drive
- Store metadata in the database
- Create a `disk_scan.txt.gz` report on the drive itself

### 4. Search Files

```bash
# Search by pattern
./ext_drive_manager search "*.pdf"

# Search with filters
./ext_drive_manager search "*" --drive 28T-02 --min-size 1G

# Export results
./ext_drive_manager search "*.jpg" --export photos.csv
```

### 5. Check Disk Usage

```bash
# Show all drives
./ext_drive_manager df

# Show specific drive details
./ext_drive_manager du 28T-02
```

## CLI Commands

### Drive Management

```bash
# Detect drive metadata
./ext_drive_manager drive meta /path/to/drive

# Add a new drive
./ext_drive_manager drive add <label> --serial <serial> --path <path> --note <note>

# List all drives
./ext_drive_manager drive list

# Scan a drive
./ext_drive_manager drive scan <label> [--note <note>]

# View or set drive note
./ext_drive_manager drive note <label> [note_text] [--append, -a]

# Remove a drive
./ext_drive_manager drive remove <label>
```

### File Operations

```bash
# Search files
./ext_drive_manager search <pattern> [--drive <label>] [--ext <ext>] [--min-size <size>] [--max-size <size>]

# List files (like ls)
./ext_drive_manager ls <target> [-l] [-a] [-h]

# Get file details
./ext_drive_manager file <file_id>

# Show catalog statistics
./ext_drive_manager stats
```

### Disk Usage

```bash
# Show all drives (like df)
./ext_drive_manager df

# Show specific drive (like du)
./ext_drive_manager du <drive_label> [-h]
```

## Web Interface

Start the web server:

```bash
./run.sh
```

Access the UI at http://localhost:8000

Features:
- **Dashboard**: Overview of all drives and statistics
- **Browse**: Browse files with filters
- **Search**: Advanced search interface
- **CLI Reference**: Quick reference for all commands

## Database

The application uses SQLite for data storage. The database file (`data/catalog.db`) is automatically created on first run.

**Note**: The database file is excluded from git via `.gitignore`. Each user maintains their own local catalog.

**To initialize the database:**

Simply run any CLI command:
```bash
./ext_drive_manager drive list
```

Or start the web server:
```bash
./run.sh
```

## Size Units

The CLI supports human-readable size formats:
- `K` or `KB` - Kilobytes
- `M` or `MB` - Megabytes  
- `G` or `GB` - Gigabytes
- `T` or `TB` - Terabytes

Examples:
```bash
./ext_drive_manager search "*" --min-size 10G --max-size 100G
./ext_drive_manager search "*.mov" --min-size 500M
```

## Development

This project was developed using:
- **Python 3.12**
- **FastAPI** - Web framework
- **SQLAlchemy** - ORM for database operations
- **Click** - CLI framework
- **Jinja2** - Template engine
- **Pixi** - Package and environment management

## File Structure

```
external_drive_manager/
├── app/
│   ├── api/              # FastAPI endpoints
│   ├── templates/        # HTML templates
│   ├── main.py           # FastAPI application
│   ├── models.py         # SQLAlchemy models
│   ├── schemas.py        # Pydantic schemas
│   ├── crud.py           # Database operations
│   ├── scanner.py        # Drive scanning logic
│   └── database.py       # Database connection
├── data/                 # SQLite database (gitignored)
├── cli.py                # CLI entry point
├── ext_drive_manager     # CLI symlink (main entry point)
├── config.py             # Configuration settings
├── pixi.toml             # Pixi configuration
├── run.sh                # Start web server
├── cli.sh                # CLI wrapper (legacy)
├── migrate_db.py         # Database migration script
└── README.md             # This file
```

**Note:** Use `./ext_drive_manager` as the main CLI entry point. The `cli.sh` wrapper is kept for backwards compatibility.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues or questions, please contact: kaiyu062@gmail.com
