from typing import Hashable, Callable
from pathlib import Path
from .compFile import File, FileGroup, FileStat
from .compUtils import printerr


class FileComparer:
    """
    Find duplicate/similar files

    - exts {list[str]}: Which file extensions to scan (None will scan all)
    - ignore {list[str]}: Which filenames to ignore (i.e. .DS_Store) (Should be all lower case)
    - time_var {float}: The +/- variance allowed in seconds for the default matcher function for file times
    - size_var {int}: The +/- variance allowed in bytes for the default matcher function for file sizes
    - min_name {int}: The minimum size of a name that will use the special name matcher function
    - combine_groups {bool}: If True, combine groups with matching hashes/keys (Default: True)
    - verbose {bool}: If True, print each duplicate that is found
    """

    __LIMIT = None
    """FOR DEBUGGING: Stop scanning after this many (Falsy = scan all)"""
    
    exts: list[str] | None
    """Which file extensions to scan (None will scan all)"""
    ignore: list[str] | None
    """Which filenames to ignore (i.e. .DS_Store) (Should be all lower case)"""
    combine_groups: bool
    """If True, combine groups with matching hashes/keys (Default: True)"""
    verbose: bool
    """If True, print each duplicate that is found"""
    comparers: dict[FileStat, Callable[[Hashable, Hashable], bool]]
    """Special comparison dictionary based on FileStat (Result of File.comparison_funcs)"""
    
    def __init__(
        self,
        exts: list[str] = None,
        ignore: list[str] = [],
        *,
        time_var = 0,
        size_var = 0,
        min_name = 3,
        combine_groups = True,
        verbose = False,
    ):
        self.exts = exts
        self.ignore = [fn.lower() for fn in ignore]
        self.combine_groups = combine_groups
        self.verbose = verbose

        self.comparers = File.comparison_funcs(min_name, size_var, time_var)

    @property
    def exts(self):
        return self.__exts
    
    @exts.setter
    def exts(self, value):
        if not value:
            self.__exts = value
        else:
            self.__exts = [f"{'' if e[0] == '.' else '.'}{e.lower()}" for e in value]

    def run(self, dirs: list[Path | str], groups: list[FileStat] = None):
        """Run scan, returning a list of FileGroups, only selectings by provided groups
        (or all in FileStat if None provided)"""
        
        if groups is None:
            groups = list(FileStat)
            
        matches: dict[FileStat, dict[Hashable, FileGroup]] = dict((g, {}) for g in groups)
        skipped: set[str] = set()

        printerr(f"Scanning {len(dirs)} directories...")

        for dir in (Path(d) for d in dirs):
            # Pre-checks
            if type(dir) is not Path:
                dir = Path(dir)

            if self.verbose:
                printerr()
            if not dir.exists() or not dir.is_dir():
                printerr(f"  Invalid file path {dir} skipping")
                continue
            
            # Walk dir
            printerr(f"  Checking {dir}...")
            count = 0
            for file in dir.rglob("*"):
                if self.__LIMIT and count == self.__LIMIT:
                    break

                if not file.is_file() or file.name.lower() in self.ignore:
                    continue
                
                # Test extensions
                if self.exts is not None and file.suffix.lower() not in self.exts:
                    if file.suffix:
                        skipped.add(file.suffix.lower())
                    if self.verbose:
                        printerr(f"    File skipped {file}")
                    continue
                
                count += 1
                try:
                    # Build group hash dicts
                    file = File(file)
                    for stat, group in matches.items():
                        hash = file.hash(stat)
                        if hash is None:
                            continue
                        
                        for key in group:
                            if self.__is_match(stat, key, hash):
                                FileGroup.append_to(group, stat, key, file)
                        
                        if hash not in group:
                            FileGroup.append_to(group, stat, hash, file)

                except Exception as e:
                    if file.path.stem in str(e):
                        printerr(f"   ",e.__class__.__name__,e)
                    else:
                        printerr(f"   ",e.__class__.__name__,file, e)
                
            printerr(f"  Checked {count} files.")
        
        # Trim down matches, removing single items and combining matching hashes
        result: list[FileGroup] = []
        for stat, group in matches.items():
            combo: dict[Hashable, FileGroup] = {}
            for hash, files in group.items():
                if len(files) < 2:
                    continue
                if not self.combine_groups:
                    combo[hash] = files
                    continue
                found = False
                for key in combo:
                    if self.__is_match(stat, hash, key):
                        combo[key].add_unique(files)
                        found = True
                if not found:
                    combo[hash] = files
            result.extend(combo.values())

        if not self.verbose and skipped:
            printerr(f"Extensions skipped: {', '.join(skipped)}")
        return result
    

    def __is_match(self, stat: FileStat, a: Hashable, b: Hashable):
        """Returns TRUE if a & b match"""
        if stat in self.comparers:
            return self.comparers[stat](a, b)
        return a == b



class FileAutoKeeper:
    """Automatically mark files to keep/delete.
    - Runs each algorithm under the FileGroup.stat, in order, until a single file is left to keep
    - NOTE: exts/locations should be ordered from [most > least preferred]
    """

    __RM_DESCENDS: Path = None
    """Set to a Base Path string to remove ONLY files under this path
    NOTE: This will override all other settings, but will ignore files outside of size_var"""

    def __init__(
        self,
        exts: list[str] = None,
        locations: list[Path | str] = None,
        size_var: int = 0,
        time_var: float = 0,
        verbose = False,
    ):
        self.exts = exts
        self.size_var = size_var
        self.time_var = time_var
        self.locations = locations
        self.verbose = verbose

    @property
    def exts(self):
        return self.__exts
    
    @exts.setter
    def exts(self, value):
        if not value:
            self.__exts = value
        else:
            self.__exts = [f"{'' if e[0] == '.' else '.'}{e.lower()}" for e in value]
    
    def run(self, files: FileGroup):
        """Keeps the prevailing files from each group.
        Also keeps files not matched at all (i.e. not the same file)"""

        if self.__RM_DESCENDS:          # Override, keeping only non RM_DESCENDS
            for file in self.not_rm_path(files):
                file.keep = True
            return
        if self.has_keep(files):        # Skip if already marked
            return
        
        matches = list(files)
        for func in self.algorithms.get(files.stat, self.default_order):
            if len(matches) < 2:
                break
            matches = func(self, matches)     # Whittle down matches
            if not matches:
                printerr("  WARNING! No matches kept from set.", [p.short for p in files])

        if matches:
            matches[0].keep = True      # Keep the first file in the list

    
    ### --- ALGORITHMS --- ###
    """
    Algorithm function should be type:
        (list[File] <ReadOnly>) -> list[File]
        Returning a new list of files from the group who satisfy the algorithm.
        This can be a instance method, allowing acces to self.<vars>
    """
    
    def has_keep(self, files: list[File]):
        """True if any file has 'keep' set to True"""
        return any(file.keep for file in files)
    
    def not_rm_path(self, files: list[File]):
        """Get list of all files not containing RM_DESCENDS"""
        return [file for file in files if not file.path.is_relative_to(self.__RM_DESCENDS)]

    def min_name(self, files: list[File]):
        """Get list of all files containing the shortest filename"""
        result: list[File] = []
        size = -1
        for file in files:
            curr = len(file.path.stem)
            if size == -1 or curr < size:
                result, size = [file], curr
            elif curr == size:
                result.append(file)
        return result

    def max_size(self, files: list[File]):
        """Get list of all files containing the largest filesize"""
        result: list[File] = []
        size: range = None
        for file in files:
            curr = file.hash(FileStat.SIZE)
            if size is None or curr > size.stop:
                result = [file]
                size = range(curr - self.size_var, curr + self.size_var)
            elif (curr in size if self.size_var else curr == size.start):
                result.append(file)
        return result

    def oldest_date(self, files: list[File]):
        """Get list of all files containing the earliest created date"""
        result: list[File] = []
        date: range = None
        for file in files:
            curr = file.hash(FileStat.CTIME)
            if date is None or curr < date.start:
                result = [file]
                date = range(curr - self.time_var, curr + self.time_var)
            elif (curr in date if self.size_var else curr == date.start):
                result.append(file)
        return result
    
    def newest_date(self, files: list[File]):
        """Get list of all files containing the latest modified date"""
        result: list[File] = []
        date: range = None
        for file in files:
            curr = file.hash(FileStat.MTIME)
            if date is None or curr > date.stop:
                result = [file]
                date = range(curr - self.time_var, curr + self.time_var)
            elif (curr in date if self.size_var else curr == date.start):
                result.append(file)
        return result

    def pref_ext(self, files: list[File]):
        """Get a list of files containing the most preferred extensions"""

        if not self.exts:
            return files

        def ext_idx(file: File):
            try:
                return len(self.exts) - self.exts.index(file.path.suffix.lower())
            except ValueError:
                return -1
        
        result, idx = files[:1], ext_idx(files[0])
        for file in files[1:]:
            curr = ext_idx(file)
            if curr > idx:
                result, idx = [file], curr
            elif curr == idx:
                result.append(file)
        return result

    def pref_loc(self, files: list[File]):
        """Get a list of files containing the most preferred location"""

        if not self.locations:
            return files

        def loc_idx(file: File):
            for i, loc in enumerate(self.locations):
                if file.path.is_relative_to(loc):
                    return len(self.locations) - i
            return -1
        
        result, idx = files[:1], loc_idx(files[0])
        for file in files[1:]:
            curr = loc_idx(file)
            if curr > idx:
                result, idx = [file], curr
            elif curr == idx:
                result.append(file)
        return result
    
    default_order = [max_size, pref_ext, pref_loc, min_name, newest_date, oldest_date]
    """Default algorithm order: max_size > pref_ext > pref_loc > min_name > newest_date > oldest_date"""

    algorithms = {
        FileStat.SIZE: [newest_date, pref_ext, pref_loc, min_name],
    }
    """For each FileGroup with given FileStat, a list of algorithms to run in order.
    Otherwise run in default_order."""