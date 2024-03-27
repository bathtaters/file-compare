# File Scanner
v1.1.0 – by bathtaters

```
Usage: python main.py [-m:mode] [-option:value] [csv path] paths...

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

Options for scan & auto modes:
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

If no CSV provided, uses './results.csv'
```
