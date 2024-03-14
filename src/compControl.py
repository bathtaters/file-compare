from json import dumps
from pathlib import Path
from .base.compFile import File, FileStat, FileGroup
from .base.compCsv import CSVParser, CsvStat
from .base.compAlgos import FileComparer, FileAutoKeeper
from .base.compSanit import check_data, clean_data
from .base.compIO import delete_files, move_files, recover_files
from .base.compUtils import get_idx, printerr


class ComparisonController:
    """
    Find similar files, delete duplicates and import/export CSVs.
    
    To extend comparison stats:
    1) Add a new stat key to FileStat Enum `compFile.py`
    2) Add to File class props: current_stats, hash, from_str, [to_str, comparison_funcs] `compFile.py`
    3) (Optional) Add to FileAutoKeeper.algorithms to customize AutoKeep behavior `compAlgos.py`
    """

    def __init__(
        self,
        roots: list[str | Path],
        exts: list[str] = None,
        ignore: list[str] = [],
        *,
        group_by: list[FileStat | str] = None,
        size_var: int = 0,
        time_var: float = 0,
        min_name: int = 3,
        headers: list[CsvStat | FileStat] = None,
        verbose = False,
    ) -> None:
        """Create new ImageScanner tool
        - roots are a list of dirs that will be scanned for files (In order of location preference for auto-keeping)
        - exts in a list of file extensions to scan, in order of preference (most > least)
        - ignore in a list of filenames to skip scanning (i.e. .DS_Store)
        - group_by is a list of FileStats to create FileGroups of
        - time/size_vars are the +/- variance allowed in seconds/bytes for matching files
        - min_name is the minimum size of a name that will use the special name matcher function
        - headers is the header for the CSV file
        - verbose will print each duplicate that is found
        """
        self.roots = [Path(r) for r in roots]
        self.verbose = verbose
        self.group_by: list[FileStat] = (
            list(FileStat) if group_by is None else
            [FileStat.get(g) for g in group_by]
        )

        self.comparer = FileComparer(
            exts,
            ignore,
            time_var=time_var,
            size_var=size_var,
            min_name=min_name,
            verbose=verbose
        )
        self.keeper = FileAutoKeeper(
            exts,
            roots,
            size_var,
            time_var,
            verbose,
        )

        if verbose:
            printerr(f"Setup ComparisonController with options: {dumps(self.__dict__, default=str, indent=2)}")

        self._data: list[FileGroup] = []
        self._csv = CSVParser(headers)


    def scan(self, dirs: list[str | Path] = None):
        """Recursively scan all dirs and store similar files"""
        self._data = self.comparer.run(self.__roots(dirs), self.group_by)
        return self._data
    
    
    def load_csv(self, csv_path: str | Path):
        """Load file data from CSV"""
        self._data = self._csv.read(csv_path)
        return self._data
    
    
    def save_csv(self, csv_path: str | Path):
        """Save file data to CSV"""
        self._csv.write(csv_path, self._data)
        

    def view_all(self, only_deleted = False):
        """Open images in system viewer, one by one"""
        files: FileGroup
        grp = -1
        while True:
            grp, files = get_idx(f"Open group {grp+1} or skip to", self._data, grp + 1)
            if grp is None:
                break
            files.view(only_deleted)

    
    def auto_keep(self):
        """Use auto-keep alogrithm to mark files. Will not delete any already marked files."""
        printerr("Auto-keeping files...")
        self.clean(silent=True)

        for files in self._data:
            if files.stat in self.group_by:
                self.keeper.run(files)

    
    def reset_keep(self, value = False):
        """Sets value of keep on all files to same value"""
        printerr(f"{'Enabling' if value else 'Removing'} all keep flags...")
        for files in self._data:
            for file in files:
                file.keep = value

    
    def delete(self):
        """Delete all files not marked to keep. Returns list of deleted files."""
        deleted, failed = delete_files(self.integrity(), self.verbose)
        if deleted is None:
            return None

        del_cnt, _ = self.clean(clean_solo=True)[0]

        print (f"Deleted {len(deleted)} files ({del_cnt} rows), unable to delete {len(failed)}.")
        return deleted
    

    def move(self, dirs: list[Path | str] = None):
        """Move all files not marked to keep to dir on same volume.
        If no dirs provided, use self.roots.
        Returns list of moved files (With original paths)."""
        moved, failed = move_files(
            self.integrity(),
            self.__roots(dirs),
            self.verbose
        )
        if moved is None:
            return None

        print (f"Moved {len(moved)} files, unable to move {len(failed)}.")
        return moved


    def recover(self, dirs: list[Path | str] = None):
        """Recover all files from dir back into folders specified in data.
        If no dirs provided, use self.roots.
        Returns list of moved files."""
        recovered, failed = recover_files(
            self.integrity(skip_clean=True),
            self.__roots(dirs),
            self.verbose
        )
        if recovered is None:
            return None

        print (f"Recovered {len(recovered)} files, unable to recover {len(failed)}.")
        return recovered
    
    
    def integrity(self, clean_solo = False, skip_clean = False):
        """Integrity check of data
        - Confirms each group has at least one file to keep
        - Removes files that no longer exist if skip_clean = False
        - Returns list of files marked for deletion"""
        
        printerr("Checking data integrity...")
        if not skip_clean:
            self.clean(silent=True, clean_solo=clean_solo)
        to_delete = check_data(self._data)
        return to_delete
    
    
    def clean(self, *, clean_solo = False, clean_kept = False, silent = False):
        """Checks each file, removing deleted ones.
        - If clean_solo is True, will remove groups with one member.
        - If clean_kept is True, will remove all groups whoose entire group is marked to keep.
        - If silent is True, hides start output.
        - Returns a count of (deleted files, removed groups)"""

        if not silent:
            printerr("Cleaning up file data...")
        
        result = clean_data(self._data, clean_solo, clean_kept, self.verbose)
        return result
    
    
    def delete_str(self, cmd = "rm"):
        """Build a list of files to delete as a space-seperated/escaped string."""
        to_delete = self.integrity()
        return f"{cmd} {' '.join(path.quoted for path in to_delete)}"

    
    def __str__(self):
        string = ""
        for i, files in enumerate(self._data):
            string += f"\n{i}\n"
            for file in files:
                string += f"  {file}\n"
        return string
    

    def __roots(self, roots: list[str | Path] = None):
        """Set & return value of roots using new value or exisiting if none provided."""
        if roots is not None:
            File.roots = [Path(r) for r in roots]
        elif self.roots:
            File.roots = self.roots.copy()
        return File.roots