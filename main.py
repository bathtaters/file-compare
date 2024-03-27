"""
-----------------
Duplicate Scanner
-----------------
by bathtaters
"""
usage = """

File Scanner by bathtaters

Usage: python $MAIN [-m:mode] [-option:value] [csv path] paths...

Modes:
  -m:scan     Scan each path for files, save results to CSV.
  -m:keep     Update CSV, auto-flagging which files to keep.
  -m:reset    Clear all 'keep' flags in CSV.
  -m:move     Move all unflagged files in CSV to first non-CSV path.
  -m:recover  Return all unflagged files in CSV from first non-CSV path to original location.
  -m:clean    Cleans up CSV: remove paths that don't exist and groups that are all flagged as 'keep.'
  -m:view     Open files in CSV with default app, one group at a time (Requires command line interaction).
  -m:delete   Delete all unflagged files permanently and update CSV.
  -m:rmstr    Get delete command as string (Prints to stdout).

Options for scan & keep modes:
  -g:?  Set the file details to group by, ? is an unspaced, comma-seperated list of values:
        • name      Match on same start of filename
        • size      Match on file size (within variance range)
        • ctime     Match on file creation time
        • mtime     Match on file modified time
  -x:?  Set the extensions to scan, ? is an unspaced, comma-seperated list (ex. jpg,jpeg,mp4).
  -i:?  Filenames to ignore/skip, ? is an unspaced, comma-seperated list (ex. .DS_Store,Thumbs.db).
  -vs:# Variance range (in bytes) of file size to allowed within group.
  -vt:# Variance range (in ms) of created/modified times to allowed within group.
  -v    If present, prints every match found (NOTE: All feedback is printed to stderr).
  -h    Shows you this help text.

If no CSV provided, uses '$CSV_PATH'
"""

### --- BASE OPTIONS --- ###

# Import Plugins
from src.plugins.imagePlugin import ImagePlugin
from src.plugins.videoPlugin import VideoPlugin

# Default CSV file
DEFAULT_CSV = "./results.csv"

# Default options
options = {
    # Default file extensions (In order of preference), None will search all
    "exts": None,
    # Default fields to create groups with (None will use defaults from plugins)
    "group_by": None, # ('name','size','ctime','mtime','img_hash','vid_hash','vid_streams','vid_dur'),
    # Default variance (+/- bytes) for size stat within groups
    "size_var": 0,
    # Default variance (+/- ms) for create/modify times stat within groups
    "time_var": 0,
    # Default shortest filename length that will use the alternative matcher.
    "min_name": 3,
    # Ignore these files
    "ignore": ('.DS_Store','Thumbs.db'),
    # If True, prints each duplicate found to stderr
    "verbose": False,
    # Set to a list of paths, will force AutoKeeper to only remove files under these paths
    "rm_paths": None,

    ### PLUGINS ###
    # List ComparisonPlugins to use here (In order of least specific to most)
    "plugins": [ImagePlugin, VideoPlugin],
    # Threshold for perceptual hash comparisons
    "threshold": 100,
    # Size for perceptual hash comparisons
    "precision": 16,
    # Video containers in order of preference, None will ignore
    "vid_containers": None,
    # Default video bitrate variance (+/- bytes) for bitrate stat within groups
    "bitrate_var": 100,
    # Default video length variance (+/- seconds) for duration stat within groups
    "duration_var": 1,
    # Image condecs in order of preference, None will ignore
    "img_codecs": None,
    # Default picture dimension variance (+/- pixels) for w*h stat within groups
    "dimension_var": 100,
}



### --- CLI RUNNER --- ###

import sys
from src.base.compUI import get_ui
from src.compControl import ComparisonController

def main():
    mode, opts, csv = get_ui(sys.argv, usage, DEFAULT_CSV)

    options.update(opts)
    scanner = ComparisonController(**options)

    if mode == "scan":
        scanner.scan()
        scanner.save_csv(csv)

    elif mode == "keep":
        scanner.load_csv(csv)
        scanner.auto_keep()
        scanner.save_csv(csv)
    
    elif mode == "reset":
        scanner.load_csv(csv)
        scanner.reset_keep(False)
        scanner.save_csv(csv)
    
    elif mode == "move":
        scanner.load_csv(csv)
        scanner.move()
    
    elif mode == "recover":
        scanner.load_csv(csv)
        scanner.recover()

    elif mode == "clean":
        scanner.load_csv(csv)
        scanner.clean(clean_solo=True, clean_kept=True)
        scanner.save_csv(csv)
    
    elif mode == "view":
        scanner.load_csv(csv)
        scanner.view_all()

    elif mode == "delete":
        scanner.load_csv(csv)
        scanner.delete()
        scanner.save_csv(csv)

    elif mode == "rmstr":
        scanner.load_csv(csv)
        print(scanner.delete_str())

    else:
        sys.exit(1)


if __name__ == "__main__":
    main()