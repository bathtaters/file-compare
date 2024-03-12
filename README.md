# File Scanner
#### by bathtaters

```
Usage: ./src/main.py [-mode] [-option:value] [csv path] paths...

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

If no CSV provided, uses './results.csv'
```

### TODO:
 - GetUI: Change 'modes' to -m:MODE (Fix -p description too)
 - Init Repo
 - Add Video and Image options