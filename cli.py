#!/usr/bin/env python3
"""
CLI for Cold Storage Drive Manager
"""

import click
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.database import SessionLocal
from app import crud
from app.schemas import DriveCreate, DriveUpdate, FileSearch
from app.scanner import DriveScanner


def get_db():
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise


def format_bytes(bytes_value):
    if not bytes_value or bytes_value == 0:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(bytes_value) < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


def parse_size(size_str):
    """Parse size string like '10G', '5K', '2T' to bytes"""
    if not size_str:
        return None
    
    size_str = str(size_str).strip().upper()
    
    # If it's already a number, return it
    if size_str.isdigit():
        return int(size_str)
    
    # Extract number and unit
    import re
    match = re.match(r'^([\d.]+)\s*([KMGT]?)B?$', size_str)
    if not match:
        raise click.BadParameter(f"Invalid size format: {size_str}. Use format like 10G, 5K, 2T, or bytes")
    
    number = float(match.group(1))
    unit = match.group(2)
    
    multipliers = {
        '': 1,
        'K': 1024,
        'M': 1024 ** 2,
        'G': 1024 ** 3,
        'T': 1024 ** 4,
    }
    
    return int(number * multipliers.get(unit, 1))


@click.group()
def cli():
    """Cold Storage Drive Manager CLI"""
    pass


@cli.group()
def drive():
    """Manage drives"""
    pass


@drive.command("add")
@click.argument("label", required=False)
@click.option("--serial", "serial_number", help="Drive serial number")
@click.option("--path", "scan_path", help="Path to scan when connected")
@click.option("--depth", "max_depth", default=-1, type=int, help="Max scan depth (-1 for unlimited)")
@click.option("--note", "note", help="Note/description for the drive")
@click.pass_context
def drive_add(ctx, label, serial_number, scan_path, max_depth, note):
    """Add a new drive to the catalog"""
    if label is None:
        click.echo(ctx.get_help())
        ctx.exit(1)
    
    db = next(iter([get_db()]))
    try:
        if crud.get_drive_by_label(db, label):
            click.echo(f"Error: Drive with label '{label}' already exists", err=True)
            sys.exit(1)

        drive = DriveCreate(
            label=label,
            serial_number=serial_number,
            scan_path=scan_path,
            max_depth=max_depth,
            note=note,
        )
        db_drive = crud.create_drive(db, drive)
        
        # Get disk capacity if path is provided and exists
        if scan_path:
            import subprocess
            scan_path_obj = Path(scan_path)
            if scan_path_obj.exists():
                try:
                    result = subprocess.run(
                        ['df', '-B1', str(scan_path)],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')
                        if len(lines) >= 2:
                            values = lines[1].split()
                            if len(values) >= 4:
                                total_capacity = int(values[1])
                                available_space = int(values[3])
                                crud.update_drive_capacity(db, db_drive.id, total_capacity, available_space)
                                click.echo(f"Drive capacity: {format_bytes(total_capacity)} (available: {format_bytes(available_space)})")
                except Exception:
                    pass
        
        click.echo(f"Drive added successfully: {db_drive.label} (ID: {db_drive.id})")
    finally:
        db.close()


@drive.command("list")
@click.option("--offline", is_flag=True, help="Show only un-scanned drives")
def drive_list(offline):
    """List all registered drives"""
    db = next(iter([get_db()]))
    try:
        drives = crud.list_drives(db, offline=offline)
        if not drives:
            click.echo("No drives registered" if not offline else "All drives have been scanned")
            return

        click.echo(f"{'ID':<5} {'Label':<15} {'Serial':<15} {'Files':>8} {'Size':>12} {'Scan Path':<25} {'Note'}")
        click.echo("-" * 100)
        for d in drives:
            note = d.note[:15] + "..." if d.note and len(d.note) > 18 else (d.note or '-')
            scan_path = d.scan_path[:22] + "..." if d.scan_path and len(d.scan_path) > 25 else (d.scan_path or '-')
            click.echo(f"{d.id:<5} {d.label:<15} {d.serial_number or '-':<15} {d.total_files:>8,} {format_bytes(d.total_size):>12} {scan_path:<25} {note}")
    finally:
        db.close()


@drive.command("meta")
@click.argument("path", required=False)
@click.pass_context
def drive_meta(ctx, path):
    """Detect and display disk metadata for a given path
    
    This helps identify drive information (serial number, size, filesystem)
    needed when adding a new drive to the catalog.
    """
    if path is None:
        click.echo(ctx.get_help())
        ctx.exit(1)
    
    import subprocess
    import os
    from pathlib import Path
    
    target_path = Path(path).resolve()
    
    if not target_path.exists():
        click.echo(f"Error: Path '{path}' does not exist", err=True)
        sys.exit(1)
    
    click.echo(f"Analyzing drive at: {target_path}\n")
    
    # Get filesystem information using df
    device = None
    try:
        result = subprocess.run(
            ['df', '-T', str(target_path)], 
            capture_output=True, 
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                # Parse df output
                header = lines[0].split()
                values = lines[1].split()
                click.echo("=== Filesystem Information ===")
                click.echo(f"Device:       {values[0]}")
                click.echo(f"Filesystem:   {values[1]}")
                click.echo(f"Size:         {values[2]}")
                click.echo(f"Used:         {values[3]}")
                click.echo(f"Available:    {values[4]}")
                click.echo(f"Use%:         {values[5]}")
                click.echo(f"Mount Point:  {values[6]}")
                click.echo()
                
                # Try to find the physical disk device
                device = values[0]
    except Exception as e:
        click.echo(f"Warning: Could not get filesystem info: {e}", err=True)
    
    # Try to get serial number using lsblk
    click.echo("=== Disk Information ===")
    try:
        if device:
            # Get the base device name (remove partition numbers)
            base_device = device
            if device.startswith('/dev/'):
                # Remove partition numbers (e.g., /dev/sda1 -> /dev/sda)
                import re
                base_device = re.sub(r'(\d+)$', '', device)
            
            # Try to get serial number
            result = subprocess.run(
                ['lsblk', '-dno', 'NAME,SERIAL,SIZE,MODEL', base_device],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split()
                if len(parts) >= 2:
                    click.echo(f"Base Device:  {base_device}")
                    if len(parts) >= 4:
                        # Model might have spaces, try to reconstruct
                        model_start = 3 if len(parts) > 3 else 2
                        model = ' '.join(parts[model_start:])
                        click.echo(f"Model:        {model}")
                    click.echo(f"Serial:       {parts[1]}")
                    if len(parts) >= 3:
                        click.echo(f"Size:         {parts[2]}")
            else:
                # Fallback: try smartctl if available
                try:
                    result = subprocess.run(
                        ['smartctl', '-i', base_device],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if 'Serial Number' in line:
                                click.echo(f"Serial:       {line.split(':')[1].strip()}")
                            elif 'Device Model' in line or 'Model Number' in line:
                                click.echo(f"Model:        {line.split(':')[1].strip()}")
                            elif 'User Capacity' in line:
                                click.echo(f"Capacity:     {line.split('[')[1].split(']')[0]}")
                except FileNotFoundError:
                    pass
    except Exception as e:
        click.echo(f"Warning: Could not get disk info: {e}", err=True)
    
    # Get UUID if available
    try:
        result = subprocess.run(
            ['blkid', '-s', 'UUID', str(device) if device else str(target_path)],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            uuid = result.stdout.strip().split('UUID=')[1].strip('"')
            click.echo(f"UUID:         {uuid}")
    except Exception:
        pass
    
    click.echo("\n=== Suggested Command ===")
    # Try to get serial for suggested command
    suggested_serial = "<serial_number>"
    try:
        if device:
            result = subprocess.run(
                ['lsblk', '-dno', 'SERIAL', device],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                suggested_serial = result.stdout.strip()
    except:
        pass
    
    click.echo(f"./cli.sh drive add <label> --serial {suggested_serial} --path {target_path}")


@drive.command("scan")
@click.argument("label", required=False)
@click.option("--note", "note", help="Update note for the drive")
@click.pass_context
def drive_scan(ctx, label, note):
    """Scan a drive and update the catalog"""
    if label is None:
        click.echo(ctx.get_help())
        ctx.exit(1)
    
    db = next(iter([get_db()]))
    try:
        drive = crud.get_drive_by_label(db, label)
        if not drive:
            click.echo(f"Error: Drive '{label}' not found", err=True)
            sys.exit(1)

        if not drive.scan_path:
            click.echo(f"Error: Drive '{label}' has no scan path configured", err=True)
            sys.exit(1)

        scan_path = Path(drive.scan_path)
        if not scan_path.exists():
            click.echo(f"Error: Path '{drive.scan_path}' does not exist. Is the drive connected?", err=True)
            sys.exit(1)

        click.echo(f"Scanning drive '{label}' at {drive.scan_path}...")

        # Get existing files before clearing
        existing_files = {}
        from app.schemas import FileSearch
        search = FileSearch(drive_label=label, limit=1000000)
        old_files, _ = crud.search_files(db, search)
        for f in old_files:
            existing_files[f.full_path] = f
        
        click.echo(f"Found {len(existing_files)} existing file entries in database")

        # Clear existing files for this drive
        deleted_count = crud.clear_drive_files(db, drive.id)
        click.echo(f"Cleared {deleted_count} existing file entries")

        # Scan the drive
        scanner = DriveScanner(str(scan_path), drive.max_depth)
        files = []
        total_size = 0

        for file_data in scanner.scan():
            file_data["drive_id"] = drive.id
            files.append(file_data)
            total_size += file_data.get("size", 0)

            if len(files) % 1000 == 0:
                click.echo(f"  Scanned {len(files)} files...")

        # Find removed files (in old but not in new)
        current_paths = {f['full_path'] for f in files}
        removed_files = [f for path, f in existing_files.items() if path not in current_paths]
        
        if removed_files:
            click.echo(f"\n[REMOVED] {len(removed_files)} files/folders no longer exist on drive:")
            for f in removed_files[:10]:  # Show first 10
                click.echo(f"  - {f.full_path}")
            if len(removed_files) > 10:
                click.echo(f"  ... and {len(removed_files) - 10} more")
            click.echo()

        # Bulk insert files
        if files:
            crud.bulk_create_files(db, files)
            db.commit()

        # Update drive stats
        crud.update_drive_stats(db, drive.id, len(files), total_size, datetime.now(timezone.utc))

        # Create gzipped scan file on the drive
        scan_file_path = scan_path / "disk_scan.txt.gz"
        try:
            import gzip
            with gzip.open(scan_file_path, 'wt', encoding='utf-8') as f:
                # Write header comments with scan information
                f.write(f"# Disk Scan Report\n")
                f.write(f"# ================================\n")
                f.write(f"# Drive Label: {drive.label}\n")
                f.write(f"# Serial Number: {drive.serial_number or 'N/A'}\n")
                f.write(f"# Scan Path: {drive.scan_path}\n")
                f.write(f"# Max Depth: {'Unlimited' if drive.max_depth == -1 else drive.max_depth}\n")
                f.write(f"# Scan Date: {datetime.now(timezone.utc).isoformat()}\n")
                f.write(f"# Total Files: {len(files)}\n")
                f.write(f"# Total Size: {total_size} bytes\n")
                f.write(f"# ================================\n\n")
                
                # Write table header
                f.write(f"{'Filename':<60} {'Size':>15} {'Modified':<20} {'Extension':<10} {'Path'}\n")
                f.write(f"{'-'*60} {'-'*15} {'-'*20} {'-'*10} {'-'*50}\n")
                
                # Write file entries
                for file_info in files:
                    filename = file_info['filename'][:57] + "..." if len(file_info['filename']) > 60 else file_info['filename']
                    size_str = f"{file_info['size']:,}"
                    mtime_str = file_info['created_at'].strftime('%Y-%m-%d %H:%M:%S') if file_info['created_at'] else 'N/A'
                    ext = file_info.get('extension', '')[:8]
                    rel_path = file_info.get('relative_path', '') or '/'
                    rel_path = rel_path[:47] + "..." if len(rel_path) > 50 else rel_path
                    
                    f.write(f"{filename:<60} {size_str:>15} {mtime_str:<20} {ext:<10} {rel_path}\n")
            click.echo(f"Scan report saved to: {scan_file_path}")
        except Exception as e:
            click.echo(f"Warning: Could not save scan file to drive: {e}", err=True)

        click.echo(f"Scan complete: {len(files)} files, {format_bytes(total_size)}")
        
        # Update note if provided
        if note is not None:
            if note == '-':
                crud.update_drive_note(db, drive.id, None)
                click.echo(f"Note cleared for drive '{label}'")
            else:
                crud.update_drive_note(db, drive.id, note)
                click.echo(f"Note updated for drive '{label}'")
    finally:
        db.close()


@drive.command("remove")
@click.argument("label", required=False)
@click.confirmation_option(prompt="Are you sure? This will remove all file entries for this drive.")
@click.pass_context
def drive_remove(ctx, label):
    """Remove a drive from the catalog"""
    if label is None:
        click.echo(ctx.get_help())
        ctx.exit(1)
    
    db = next(iter([get_db()]))
    try:
        drive = crud.get_drive_by_label(db, label)
        if not drive:
            click.echo(f"Error: Drive '{label}' not found", err=True)
            sys.exit(1)

        crud.delete_drive(db, drive.id)
        click.echo(f"Drive '{label}' removed successfully")
    finally:
        db.close()


@drive.command("note")
@click.argument("label", required=False)
@click.argument("note_text", required=False)
@click.option("--append", "-a", is_flag=True, help="Append to existing note instead of overwriting")
@click.pass_context
def drive_note(ctx, label, note_text, append):
    """View or set note for a drive
    
    If note_text is provided, it will be set.
    If no note_text, the current note will be displayed.
    Use '-' to clear the note.
    Use --append (-a) to append to existing note.
    """
    if label is None:
        click.echo(ctx.get_help())
        ctx.exit(1)
    
    db = next(iter([get_db()]))
    try:
        drive = crud.get_drive_by_label(db, label)
        if not drive:
            click.echo(f"Error: Drive '{label}' not found", err=True)
            sys.exit(1)
        
        if note_text is None:
            # View note
            if drive.note:
                click.echo(f"Note for '{label}':")
                click.echo(drive.note)
            else:
                click.echo(f"No note set for drive '{label}'")
        else:
            # Set note
            if note_text == '-':
                new_note = None
                click.echo(f"Note cleared for drive '{label}'")
            elif append and drive.note:
                # Append with timestamp
                from datetime import datetime, timezone
                timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                new_note = f"{drive.note}\n[{timestamp}] {note_text}"
                click.echo(f"Note appended to drive '{label}'")
            else:
                new_note = note_text
                click.echo(f"Note updated for drive '{label}'")
            
            crud.update_drive_note(db, drive.id, new_note)
    finally:
        db.close()


@cli.command("search")
@click.argument("query", required=False)
@click.option("--drive", "drive_label", help="Filter by drive label")
@click.option("--ext", "extension", help="Filter by file extension")
@click.option("--min-size", callback=lambda ctx, param, value: parse_size(value), help="Minimum file size (e.g., 10G, 5K, 2T, or bytes)")
@click.option("--max-size", callback=lambda ctx, param, value: parse_size(value), help="Maximum file size (e.g., 10G, 5K, 2T, or bytes)")
@click.option("--from-date", help="From date (ISO format)")
@click.option("--to-date", help="To date (ISO format)")
@click.option("--limit", default=100, help="Maximum results")
@click.option("--export", "export_file", help="Export results to CSV file")
@click.pass_context
def search(ctx, query, drive_label, extension, min_size, max_size, from_date, to_date, limit, export_file):
    """Search files by pattern with optional filters"""
    # If no search criteria provided, show help
    if not any([query, drive_label, extension, min_size, max_size, from_date, to_date]):
        click.echo(ctx.get_help())
        return
    
    db = next(iter([get_db()]))
    try:
        search_params = FileSearch(
            query=query,
            drive_label=drive_label,
            extension=extension,
            min_size=min_size,
            max_size=max_size,
            from_date=datetime.fromisoformat(from_date) if from_date else None,
            to_date=datetime.fromisoformat(to_date) if to_date else None,
            limit=limit,
            offset=0,
        )

        files, total = crud.search_files(db, search_params)

        if not files:
            click.echo("No files found matching your criteria")
            return

        click.echo(f"Found {total} files (showing {len(files)}):")
        click.echo()

        if export_file:
            with open(export_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["filename", "relative_path", "drive_label", "size", "created_at", "created_time", "extension"])
                for file in files:
                    drive = crud.get_drive(db, file.drive_id)
                    writer.writerow([
                        file.filename,
                        file.relative_path or "",
                        drive.label if drive else "",
                        file.size,
                        file.created_at.isoformat() if file.created_at else "",
                        file.created_time.isoformat() if file.created_time else "",
                        file.extension or "",
                    ])
            click.echo(f"Results exported to: {export_file}")
        else:
            click.echo(f"{'ID':<8} {'Filename':<45} {'Drive':<15} {'Size':<12} {'Extension':<10} {'Full Path'}")
            click.echo("-" * 130)
            for f in files:
                drive = crud.get_drive(db, f.drive_id)
                filename = f.filename[:42] + "..." if len(f.filename) > 45 else f.filename
                full_path = f.full_path[:50] + "..." if len(f.full_path) > 53 else f.full_path
                click.echo(f"{f.id:<8} {filename:<45} {drive.label if drive else '?':<15} {format_bytes(f.size):<12} {f.extension or '-':<10} {full_path}")
    finally:
        db.close()


@cli.command("file")
@click.argument("file_id", type=int, required=False)
@click.pass_context
def file_info(ctx, file_id):
    """Show details for a specific file"""
    if file_id is None:
        click.echo(ctx.get_help())
        ctx.exit(1)
    
    db = next(iter([get_db()]))
    try:
        file = crud.get_file_by_id(db, file_id)
        if not file:
            click.echo(f"Error: File ID {file_id} not found", err=True)
            sys.exit(1)

        drive = crud.get_drive(db, file.drive_id)

        click.echo(f"File ID: {file.id}")
        click.echo(f"Filename: {file.filename}")
        click.echo(f"Drive: {drive.label if drive else 'Unknown'} (ID: {file.drive_id})")
        click.echo(f"Relative Path: {file.relative_path or '/'}")
        click.echo(f"Full Path: {file.full_path}")
        click.echo(f"Size: {format_bytes(file.size)}")
        click.echo(f"Extension: {file.extension or 'None'}")
        click.echo(f"Modified: {file.created_at}")
        click.echo(f"Created: {file.created_time}")
    finally:
        db.close()


@cli.command("stats")
def stats():
    """Show catalog statistics"""
    db = next(iter([get_db()]))
    try:
        stats = crud.get_stats(db)
        extensions = crud.get_all_extensions(db)

        click.echo("Catalog Statistics:")
        click.echo(f"  Total Drives: {stats['total_drives']}")
        click.echo(f"  Total Files: {stats['total_files']:,}")
        click.echo(f"  Total Size: {format_bytes(stats['total_size'])}")
        click.echo()

        if extensions:
            click.echo(f"File Types: {', '.join(sorted(extensions))}")
    finally:
        db.close()


@cli.command("df")
def disk_free():
    """Show disk space usage (like df command)"""
    db = next(iter([get_db()]))
    try:
        drives = crud.list_drives(db)
        if not drives:
            click.echo("No drives registered")
            return

        click.echo(f"{'Drive':<15} {'Total':>12} {'Used':>12} {'Available':>12} {'Use%':>6} {'Files':>8} {'Note'}")
        click.echo("-" * 100)
        
        total_capacity = 0
        total_used = 0
        total_files = 0
        
        for drive in drives:
            # Use stored capacity if available, otherwise show "N/A"
            if drive.total_capacity:
                total = drive.total_capacity
                used = drive.total_size  # Catalog size is the used space
                avail = drive.available_space if drive.available_space else (total - used)
                use_percent = f"{(used/total)*100:.0f}%" if total > 0 else "0%"
                
                total_str = format_bytes(total)
                used_str = format_bytes(used)
                avail_str = format_bytes(avail)
            else:
                total_str = used_str = avail_str = "N/A"
                use_percent = "N/A"
            
            # Truncate note if too long
            note = drive.note[:20] + "..." if drive.note and len(drive.note) > 23 else (drive.note or '-')
            
            click.echo(f"{drive.label:<15} {total_str:>12} {used_str:>12} {avail_str:>12} {use_percent:>6} {drive.total_files:>8,} {note}")
            
            if drive.total_capacity:
                total_capacity += drive.total_capacity
            total_used += drive.total_size
            total_files += drive.total_files
        
        click.echo("-" * 100)
        click.echo(f"{'TOTAL':<15} {format_bytes(total_capacity):>12} {format_bytes(total_used):>12} {'':>12} {'':>6} {total_files:>8,}")
    finally:
        db.close()


@cli.command("du")
@click.argument("drive_label", required=False)
@click.option("-s", "summary", is_flag=True, help="Display only a total for each argument")
@click.option("-h", "human_readable", is_flag=True, help="Print sizes in human readable format")
@click.pass_context
def disk_usage(ctx, drive_label, summary, human_readable):
    """Show disk usage for a specific drive (like du command)
    
    DRIVE_LABEL is the label of the drive to check (e.g., '28T-02')
    """
    if drive_label is None:
        click.echo(ctx.get_help())
        ctx.exit(1)
    
    db = next(iter([get_db()]))
    try:
        drive = crud.get_drive_by_label(db, drive_label)
        if not drive:
            click.echo(f"Error: Drive '{drive_label}' not found", err=True)
            sys.exit(1)

        # Get catalog size
        catalog_size = drive.total_size
        catalog_files = drive.total_files
        
        # Use stored capacity from database
        if drive.total_capacity:
            total = drive.total_capacity
            avail = drive.available_space if drive.available_space else (total - catalog_size)
            used = catalog_size
            
            # Format sizes
            if human_readable:
                size_str = format_bytes(catalog_size)
                total_str = format_bytes(total)
                avail_str = format_bytes(avail)
                used_str = format_bytes(used)
            else:
                size_str = f"{catalog_size:,} bytes"
                total_str = f"{total:,} bytes"
                avail_str = f"{avail:,} bytes"
                used_str = f"{used:,} bytes"
            
            use_percent = f"{(used/total)*100:.1f}%" if total > 0 else "0%"
            
            click.echo(f"Drive:        {drive_label}")
            click.echo(f"Total Size:   {total_str}")
            click.echo(f"Used:         {used_str} ({use_percent})")
            click.echo(f"Available:    {avail_str}")
            click.echo(f"Catalog Size: {size_str}")
            click.echo(f"Files:        {catalog_files:,}")
            if drive.note:
                click.echo(f"Note:         {drive.note}")
        else:
            # No capacity stored, just show catalog info
            if human_readable:
                size_str = format_bytes(catalog_size)
            else:
                size_str = f"{catalog_size:,} bytes"
            
            click.echo(f"Drive:        {drive_label}")
            click.echo(f"Catalog Size: {size_str}")
            click.echo(f"Files:        {catalog_files:,}")
            if drive.note:
                click.echo(f"Note:         {drive.note}")
            click.echo("Info: Drive capacity not stored. Run 'drive scan' or 'drive add' to update.")
        
        if not summary:
            click.echo(f"Last scanned: {drive.last_scanned or 'Never'}")
            if drive.serial_number:
                click.echo(f"Serial:       {drive.serial_number}")
            if drive.note:
                click.echo(f"Note:         {drive.note}")
    finally:
        db.close()


@cli.command("ls")
@click.argument("target")
@click.option("-l", "long_format", is_flag=True, help="Use long listing format")
@click.option("-a", "show_all", is_flag=True, help="Do not ignore entries starting with .")
@click.option("-h", "human_readable", is_flag=True, help="Print sizes in human readable format")
def list_contents(target, long_format, show_all, human_readable):
    """List contents of a disk, path, or file (like ls -l)
    
    TARGET can be:
    - A drive label (e.g., '28T-02')
    - A path within a drive (e.g., '28T-02:/folder/subfolder')
    - A file ID (number)
    """
    db = next(iter([get_db()]))
    try:
        # Check if target is a file ID
        if target.isdigit():
            file_id = int(target)
            file = crud.get_file_by_id(db, file_id)
            if not file:
                click.echo(f"Error: File ID {file_id} not found", err=True)
                sys.exit(1)
            
            # Display single file info
            drive = crud.get_drive(db, file.drive_id)
            click.echo(f"File: {file.filename}")
            click.echo(f"Drive: {drive.label if drive else 'Unknown'}")
            click.echo(f"Path: {file.full_path}")
            click.echo(f"Size: {format_bytes(file.size) if human_readable else f'{file.size} bytes'}")
            click.echo(f"Extension: {file.extension or 'None'}")
            click.echo(f"Modified: {file.created_at}")
            click.echo(f"Created: {file.created_time}")
            return
        
        # Parse target (drive:path or just drive)
        if ":" in target:
            parts = target.split(":", 1)
            drive_label = parts[0]
            subpath = parts[1] if len(parts) > 1 else ""
            # Normalize path (remove leading/trailing slashes)
            subpath = subpath.strip("/")
        else:
            drive_label = target
            subpath = ""
        
        # Get the drive
        drive = crud.get_drive_by_label(db, drive_label)
        if not drive:
            click.echo(f"Error: Drive '{drive_label}' not found", err=True)
            sys.exit(1)
        
        # Get all files for this drive
        from app.schemas import FileSearch
        search = FileSearch(drive_label=drive_label, limit=10000)
        files, total = crud.search_files(db, search)
        
        if not files:
            click.echo(f"No files found in drive '{drive_label}'")
            return
        
        # Filter by subpath if specified
        if subpath:
            files = [f for f in files if f.relative_path and f.relative_path.startswith(subpath)]
            if not files:
                click.echo(f"No files found in path '{target}'")
                return
        
        # Group files by directory
        from collections import defaultdict
        dirs = defaultdict(list)
        root_files = []
        
        for f in files:
            if not f.relative_path:
                root_files.append(f)
            else:
                rel_parts = f.relative_path.split("/")
                if subpath:
                    # Remove the subpath prefix
                    subpath_parts = subpath.split("/")
                    if rel_parts[:len(subpath_parts)] == subpath_parts:
                        remaining = rel_parts[len(subpath_parts):]
                        if remaining:
                            dirs[remaining[0]].append(f)
                        else:
                            root_files.append(f)
                else:
                    dirs[rel_parts[0]].append(f)
        
        # Display results
        if long_format:
            click.echo(f"{'Permissions':<12} {'Size':>12} {'Date':<20} {'Name'}")
            click.echo("-" * 80)
            
            # Show directories first
            for dirname in sorted(dirs.keys()):
                if not show_all and dirname.startswith("."):
                    continue
                size = sum(f.size for f in dirs[dirname])
                size_str = format_bytes(size) if human_readable else f"{size}"
                click.echo(f"{'drwxr-xr-x':<12} {size_str:>12} {'':<20} {dirname}/")
            
            # Show files
            for f in sorted(root_files, key=lambda x: x.filename):
                if not show_all and f.filename.startswith("."):
                    continue
                size_str = format_bytes(f.size) if human_readable else f"{f.size}"
                date_str = f.created_at.strftime("%b %d %H:%M") if f.created_at else "-"
                click.echo(f"{'-rw-r--r--':<12} {size_str:>12} {date_str:<20} {f.filename}")
        else:
            # Simple listing
            output = []
            for dirname in sorted(dirs.keys()):
                if not show_all and dirname.startswith("."):
                    continue
                output.append(f"{dirname}/")
            for f in sorted(root_files, key=lambda x: x.filename):
                if not show_all and f.filename.startswith("."):
                    continue
                output.append(f.filename)
            
            if output:
                # Print in columns
                cols = 4
                for i in range(0, len(output), cols):
                    row = output[i:i+cols]
                    click.echo("  ".join(f"{name:<25}" for name in row))
        
        click.echo(f"\nTotal: {len(dirs)} directories, {len(root_files)} files")
        
    finally:
        db.close()


if __name__ == "__main__":
    cli()
