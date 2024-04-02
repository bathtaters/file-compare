from typing import Hashable, Callable
from pathlib import Path
from .compFile import File, FileGroup
from .compLog import CSVLog
from .compUtils import printerr, EnumGet


class FileScanner:
    """
    Find duplicate/similar files

    - exts {list[str]}: Which file extensions to scan (None will scan all)
    - ignore {list[str]}: Which filenames to ignore (i.e. .DS_Store) (Should be all lower case)
    - combine_groups {bool}: If True, combine groups with matching hashes/keys (Default: True)
    - logpath {str}: If provided, save each scanned file to the path provided, and use this path to recover an interrupted san (Default: None)
    - verbose {bool}: If True, print each duplicate that is found
    - comparers {EnumGet: (hash,hash)->bool}: Special comparison dictionary based on StatEnum (Result of File.comparison_funcs)
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
    comparers: dict[EnumGet, Callable[[Hashable, Hashable], bool]]
    """Special comparison dictionary based on StatEnum (Result of File.comparison_funcs)"""
    
    def __init__(
        self,
        exts: list[str] = None,
        ignore: list[str] = [],
        *,
        combine_groups = True,
        logpath: str | Path = None,
        verbose = False,
    ):
        self.exts = exts
        self.ignore = [fn.lower() for fn in ignore]
        self.combine_groups = combine_groups
        self.verbose = verbose
        self._log = CSVLog(logpath)

        self.comparers = {}

    @property
    def exts(self):
        return self.__exts
    
    @exts.setter
    def exts(self, value):
        if not value:
            self.__exts = value
        else:
            self.__exts = [f"{'' if e[0] == '.' else '.'}{e.lower()}" for e in value]

    def run(self, dirs: list[Path | str], groups: list[EnumGet]):
        """Run scan, returning a list of FileGroups, only selectings by provided groups
        (or all in StatEnums if None provided)"""
        
        self.comparers = File.comparison_funcs()

        matches, skipped, scanned = self._log.open(groups)
        if scanned:
            printerr(f"  Recovered {len(scanned)} files from log.")

        printerr(f"Scanning {len(dirs)} directories...")

        for dir in (Path(d) for d in dirs):
            # Pre-checks
            if type(dir) is not Path:
                dir = Path(dir)

            if self.verbose:
                printerr()
            if not dir.exists() or not dir.is_dir():
                printerr(f"  Skipping invalid file path: {dir}")
                continue
            
            # Walk dir
            printerr(f"  Checking {dir}...")
            count = 0
            for path in dir.rglob("*"):
                if self.__LIMIT and count == self.__LIMIT:
                    break

                if scanned and path in scanned:
                    continue

                if not path.is_file() or path.name.lower() in self.ignore:
                    continue
                
                if not self.__is_valid_ext(path, skipped):
                    self.verbose and printerr(f"    File skipped {path}")
                    continue
                
                count += 1
                err = self.__append_hash_dict(matches, path)
                if err:
                    printerr("   ", err)
                
            printerr(f"  Checked {count} files.")
        
        if not self.verbose and skipped:
            printerr(f"Extensions skipped: {', '.join(skipped)}")
        return self.__clean_hash_dict(matches)
    

    def cleanup(self):
        """Delete log file (If one exists)"""
        self._log.remove()
    

    def __is_match(self, stat: EnumGet, a: Hashable, b: Hashable):
        """Returns TRUE if a & b match"""
        if stat in self.comparers:
            return self.comparers[stat](a, b)
        return a == b

    
    def __is_valid_ext(self, path: Path, skipped_exts: set):
        """Check if path has a valid extension, if not append to skipped extensions list."""
        if self.exts is None or path.suffix.lower() in self.exts:
            return True
        if not path:
            return False
        ext = path.suffix.lower()
        if ext not in skipped_exts:
            skipped_exts.add(ext)
            self._log.append_skip(ext)
        return False
            

    def __append_hash_dict(self, hash_dict: dict[EnumGet, dict[Hashable, FileGroup]], path: Path):
        """Append data from file path to hash dictionary. Returns error string or None"""

        file = None
        logdata: list[tuple[EnumGet, str]] = []
        try:
            file = File(path)
            for stat, group in hash_dict.items():
                hash = file.to_hash(stat)
                if hash is None:
                    continue
                
                for key in group:
                    if self.__is_match(stat, key, hash):
                        FileGroup.append_to(group, stat, file, key)
                        logdata.append((stat, file.hash_to_str(stat, key)))
                
                if hash not in group:
                    FileGroup.append_to(group, stat, file, hash)
                    logdata.append((stat, file.to_str(stat)))

        except Exception as e:
            if path.stem in str(e):
                return f"{e.__class__.__name__}: {e}"
            else:
                return f"{e.__class__.__name__}: {file or path} - {e}"
        
        return self._log.append(file, logdata)
    
    def __clean_hash_dict(self, hash_dict: dict[EnumGet, dict[Hashable, FileGroup]]):
        """Trim down matches, removing single items and combining matching hashes"""
        
        result: list[FileGroup] = []
        for stat, group in hash_dict.items():

            combo: dict[Hashable, FileGroup] = {}
            for hash, files in group.items():
                if len(files) < 2:
                    continue  # remove single items
                if not self.combine_groups:
                    combo[hash] = files
                    continue

                found = False
                for key in combo:
                    if self.__is_match(stat, hash, key):
                        combo[key].add_unique(files)
                        found = True  # combine matching hashes
                if not found:
                    combo[hash] = files  # add unmatched hash group

            result.extend(combo.values())
        return result
