# File Scanner
#### v2.1.3 – by bathtaters

Find and manage duplicate/similar files.

Requires installation of [FFMpeg](https://ffmpeg.org/download.html) and [chromaprint](https://acoustid.org/chromaprint).

---

## Install as Dependency
```bash
pip install git+https://github.com/bathtaters/file-compare.git@main
```

---

## Run via Command Line

Using main.py

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

Options for scan & keep modes:
  -x:$  File extensions to exclusively scan, $ is an unspaced, comma-seperated list (ex. jpg,jpeg,mp4).
  -i:$  Filenames to ignore/skip, $ is an unspaced, comma-seperated list (ex. .DS_Store,Thumbs.db).
  -g:$  Set the file details to group by, $ is an unspaced, comma-seperated list of values:
        • name          Match on same start of filename
        • size          Match on file size (within variance range)
        • img_hash      Match on perceptual hash of still (i.e. visual similarity)
        • av_hash       Match on perceptual hash of video or audio (i.e. visual/audible similarity)
        • av_streams    Match by stream layouts (i.e. video/audio size/duration/codec)
        • av_dur        Match on video/audio duration
         -- (Default groups above this line) --
        • all           Matches every file, placing them all under the same group
        • ctime         Match on file creation time
        • mtime         Match on file modified time
        • img_type      Match on image encoding (ex. JPEG,MPO,HEIF,etc)
        • img_size      Match on image dimensions (WxH)
        • img_frames    Match on framecount (For animated images, otherwise 1)
        • av_media      Match on media type (video or audio)
        • av_container  Match on audio/video container name
        • av_bitrate    Match on total bitrate of media (bits/second)
  -t:#  Match threshold for perceptual hash comparison (As a percentage, with 100 being an exact match).
  -p:#  Size (precision) of perceptual hashes (As a power of 2, higher values take longer but are more precise).
  -vs:# Variance range (# is +/- value in bytes) of file size within group.
  -vt:# Variance range (# is +/- value in ms) of created/modified times within group.
  -vb:# Variance range (# is +/- value in bytes) of video bitrate within group.
  -vd:# Variance range (# is +/- value in seconds) of video duration within group.
  -vs:# Variance range (# is +/- value in pixels) of image size (w x h) within group.
  -r:$  Path (from paths) to exclusively use when removing files (All files not under this path will be marked to keep).

Other options:
  -fc:# For m:clean, remove files with less than this many matching stats.
  -fv:# For m:view, filter out groups with less than this many matches.
  -v    If present, prints every match found (NOTE: All feedback is printed to stderr).
  -h    Shows you this help text.

If no CSV provided, uses './results.csv'
```
