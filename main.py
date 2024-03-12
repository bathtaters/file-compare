"""
-----------------
Duplicate Scanner
-----------------
by bathtaters
"""
usage = """

File Scanner by bathtaters

Usage: $MAIN [-mode] [-option:value] [csv path] paths...

Modes:
 (-s)   (Default) Scan each path for photos, save results to CSV
  -k    Update CSV, auto-flagging which files to keep
  -d    Delete all unflagged files in CSV and update CSV
  -m    Move all unflagged files in CSV to first path
  -r    Recover all unflagged files in CSV from first path
  -x    Remove all keep flags from CSV
  -c    Cleans up CSV, removing deleted photos or groups tha are all flagged to keep
  -p    (Experimental) View all photos in CSV, one group at a time
  -rm   Get delete command as string (Prints to stdout)

Scan (-s) & Update (-k) Options:
  -g:?  Set the file stats to group by, ? is an unspaced, comma-seperated list of values:
        • name      Match on same start of filename
        • size      Match on file size (within variance range)
        • ctime     Match on file creation time
        • mtime     Match on file modified time
  -sv:# Variance range (in bytes) of file size to allowed within group
  -tv:# Variance range (in ms) of created/modified times to allowed within group
  -e:?  Set the extensions to scan, ? is an unspaced, comma-seperated list (ex. jpg,jpeg,mp4)
  -i:?  Filenames to ignore/skip, ? is an unspaced, comma-seperated list (ex. .DS_Store,Thumbs.db)
  -v    If present, prints every match found (NOTE: All feedback is printed to stderr)

If no CSV provided, uses '$CSV_PATH'
"""

### --- BASE OPTIONS --- ###

# Default CSV file
DEFAULT_CSV = "./results.csv"

# Default options
options = {
    # Default file extensions (In order of preference), None will search all
    "exts": None,
    # Default fields to create groups with
    "group_by": ('name','size','ctime','mtime'),
    # Default variance (+/-) for size stat within groups
    "size_var": 0,
    # Default variance (+/-) for create/modify times stat within groups
    "time_var": 0,
    # Ignore these files
    "ignore": ('.DS_Store','Thumbs.db'),
    # If True, prints each duplicate found to stderr
    "verbose": False,
}



### --- CLI RUNNER --- ###

import sys
from src.base.compUtils import get_ui
from src.compControl import ComparisonController

def main():
    action, opts, csv = get_ui(sys.argv, usage, DEFAULT_CSV)

    options.update(opts)
    scanner = ComparisonController(**options)

    if action == "SCAN":
        scanner.scan()
        scanner.save_csv(csv)

    elif action == "KEEP":
        scanner.load_csv(csv)
        scanner.auto_keep()
        scanner.save_csv(csv)

    elif action == "DELETE":
        scanner.load_csv(csv)
        scanner.delete()
        scanner.save_csv(csv)

    elif action == "DELSTR":
        scanner.load_csv(csv)
        print(scanner.delete_str())
    
    elif action == "MOVE":
        scanner.load_csv(csv)
        scanner.move()
    
    elif action == "RECOV":
        scanner.load_csv(csv)
        scanner.recover()
    
    elif action == "VIEW":
        scanner.load_csv(csv)
        scanner.view_all()

    elif action == "CLEAN":
        scanner.load_csv(csv)
        scanner.clean(clean_solo=True, clean_kept=True)
        scanner.save_csv(csv)
    
    elif action == "RESET":
        scanner.load_csv(csv)
        scanner.reset_keep(False)
        scanner.save_csv(csv)

    else:
        sys.exit(1)


if __name__ == "__main__":
    main()