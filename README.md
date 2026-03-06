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
./cli.sh drive list
```

## Quick Start

### 1. Detect Drive Information

Before adding a drive, detect its metadata:

```bash
./cli.sh drive meta /mnt/your-drive
```

### 2. Add a Drive

```bash
./cli.sh drive add 28T-02 --serial ABC123 --path /mnt/ext_2 --note "Backup drive for raw data"
```

### 3. Scan the Drive

```bash
./cli.sh drive scan 28T-02
```

This will:
- Scan all files on the drive
- Store metadata in the database
- Create a `disk_scan.txt.gz` report on the drive itself

### 4. Search Files

```bash
# Search by pattern
./cli.sh search "*.pdf"

# Search with filters
./cli.sh search "*" --drive 28T-02 --min-size 1G

# Export results
./cli.sh search "*.jpg" --export photos.csv
```

### 5. Check Disk Usage

```bash
# Show all drives
./cli.sh df

# Show specific drive details
./cli.sh du 28T-02
```

## CLI Commands

### Drive Management

```bash
# Detect drive metadata
./cli.sh drive meta /path/to/drive

# Add a new drive
./cli.sh drive add <label> --serial <serial> --path <path> --note <note>

# List all drives
./cli.sh drive list

# Scan a drive
./cli.sh drive scan <label> [--note <note>]

# View or set drive note
./cli.sh drive note <label> [note_text] [--append, -a]

# Remove a drive
./cli.sh drive remove <label>
```

### File Operations

```bash
# Search files
./cli.sh search <pattern> [--drive <label>] [--ext <ext>] [--min-size <size>] [--max-size <size>]

# List files (like ls)
./cli.sh ls <target> [-l] [-a] [-h]

# Get file details
./cli.sh file <file_id>

# Show catalog statistics
./cli.sh stats
```

### Disk Usage

```bash
# Show all drives (like df)
./cli.sh df

# Show specific drive (like du)
./cli.sh du <drive_label> [-h]
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
./cli.sh drive list
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
./cli.sh search "*" --min-size 10G --max-size 100G
./cli.sh search "*.mov" --min-size 500M
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
│   ├── api/           # FastAPI endpoints
│   ├── templates/     # HTML templates
│   ├── main.py        # FastAPI application
│   ├── models.py      # SQLAlchemy models
│   ├── schemas.py     # Pydantic schemas
│   ├── crud.py        # Database operations
│   ├── scanner.py     # Drive scanning logic
│   └── database.py    # Database connection
├── data/              # SQLite database (gitignored)
├── cli.py             # CLI entry point
├── config.py          # Configuration settings
├── pixi.toml          # Pixi configuration
├── run.sh             # Start web server
├── cli.sh             # CLI wrapper
├── migrate_db.py      # Database migration script
└── README.md          # This file
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues or questions, please contact: kaiyu062@gmail.com
