from typing import Hashable, Callable
from pathlib import Path
from .compFile import File, FileGroup
from .compUtils import printerr, EnumGet


class FileScanner:
    """
    Find duplicate/similar files

    - exts {list[str]}: Which file extensions to scan (None will scan all)
    - ignore {list[str]}: Which filenames to ignore (i.e. .DS_Store) (Should be all lower case)
    - combine_groups {bool}: If True, combine groups with matching hashes/keys (Default: True)
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
        verbose = False,
    ):
        self.exts = exts
        self.ignore = [fn.lower() for fn in ignore]
        self.combine_groups = combine_groups
        self.verbose = verbose

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
            
        matches: dict[EnumGet, dict[Hashable, FileGroup]] = dict((g, {}) for g in groups)
        skipped: set[str] = set()

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
    

    def __is_match(self, stat: EnumGet, a: Hashable, b: Hashable):
        """Returns TRUE if a & b match"""
        if stat in self.comparers:
            return self.comparers[stat](a, b)
        return a == b

    
    def __is_valid_ext(self, path: Path, skipped_exts: set):
        """Check if path has a valid extension, if not append to skipped extensions list."""
        if self.exts is None or path.suffix.lower() in self.exts:
            return True
        if path.suffix:
            skipped_exts.add(path.suffix.lower())
        return False
            

    def __append_hash_dict(self, hash_dict: dict[EnumGet, dict[Hashable, FileGroup]], path: Path):
        """Append data from file path to hash dictionary. Returns error string or None"""

        file = None
        try:
            file = File(path)
            for stat, group in hash_dict.items():
                hash = file.to_hash(stat)
                if hash is None:
                    continue
                
                for key in group:
                    if self.__is_match(stat, key, hash):
                        FileGroup.append_to(group, stat, key, file)
                
                if hash not in group:
                    FileGroup.append_to(group, stat, hash, file)

        except Exception as e:
            if path.stem in str(e):
                return f"{e.__class__.__name__}: {e}"
            else:
                return f"{e.__class__.__name__}: {file or path} - {e}"
        return None
    
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
