from typing import Self, Hashable, Callable, Iterable
from types import MappingProxyType
import subprocess
from datetime import datetime
from pathlib import Path
from .compUtils import EnumGet, get_parent, to_metric, from_metric, range_matcher, length_matcher


class FileStat(EnumGet):
    """File statistics used for comparison.
    - Value is used as CSV header unless otherwise provided in CsvHdr Enum"""

    NAME = "Name"
    """Filename without extension"""
    SIZE = "Size"
    """File size in bytes"""
    CTIME = "Created"
    """File creation date/time"""
    MTIME = "Modified"
    """Last modification date/time"""

    


class File:
    """Representation of a file"""
    
    def current_stats(self):
        """Fetch stats dict from filesystem"""
        return {
            FileStat.NAME: self.path.stem,
            FileStat.SIZE: self.path.stat().st_size if self.path.exists() else 0,
            FileStat.CTIME: datetime.fromtimestamp(self.path.stat().st_ctime),
            FileStat.MTIME: datetime.fromtimestamp(self.path.stat().st_mtime),
        }
    
    def hash(self, stat: FileStat) -> Hashable | None:
        """Returns a hash corresponding to the provided stat on the File"""
        if stat == FileStat.NAME:
            return self.path.stem.lower()
        elif stat == FileStat.SIZE:
            return self.stats[stat]
        elif stat == FileStat.CTIME:
            return round(self.stats[stat].timestamp())
        elif stat == FileStat.MTIME:
            return round(self.stats[stat].timestamp())
        return None

    @staticmethod
    def comparison_funcs(min_name=3, size_var=0, time_var=0) -> dict[FileStat, Callable[[Hashable, Hashable], bool]]:
        """Comparison functions for FileStats, to override default hash equality function (==)"""
        return {
            FileStat.NAME: length_matcher(min_name),
            FileStat.SIZE: range_matcher(size_var),
            FileStat.CTIME: range_matcher(time_var),
            FileStat.MTIME: range_matcher(time_var),
        }

    def to_str(self, stat: FileStat) -> str | None:
        """Convert value of stat to a string for display/CSV"""
        if stat == FileStat.NAME:
            return self.path.stem
        elif stat == FileStat.SIZE:
            return to_metric(self.stats[stat], "B")
        elif stat == FileStat.CTIME:
            return self.stats[stat].strftime(self._DATE_FMT)
        elif stat == FileStat.MTIME:
            return self.stats[stat].strftime(self._DATE_FMT)
        return str(self.stats[stat])
    
    def from_str(self, stat: FileStat, value: str):
        """Convert result of to_str back into stat type"""
        if stat == FileStat.NAME:
            return value
        elif stat == FileStat.SIZE:
            return from_metric(value)
        elif stat == FileStat.CTIME:
            return self.__to_dt(value)
        elif stat == FileStat.MTIME:
            return self.__to_dt(value)
        return None

    # # #

    _DATE_FMT = "%m-%d-%Y %H:%M"
    """Default datetime format for reading/writing to CSV"""
    
    roots: list[Path] = []
    """List of root paths, to remove for 'short' path formatting"""

    @property
    def path(self):
        """Path of this file (read-only)"""
        return self.__path
    
    @property
    def stats(self):
        """Stats of this file (update w/ update_stats())"""
        return self.__stats
    
    @property
    def exists(self):
        """True/False if file exists"""
        return self.__exists
    
    @property
    def short(self):
        """Shortened filepath (with root dir removed)"""
        parent = get_parent(self.path, self.roots)
        return self.path.relative_to(parent) if parent else self.path
    
    @property
    def quoted(self):
        """Full filepath, quoted for command line"""
        return f'"{self.path.resolve().as_posix()}"'

    keep: bool
    """True/False to retain file while cleaning files"""

    def __init__(
        self,
        path: str | Path | Self,
        stats: dict[FileStat] = {},
        keep = False,
    ):
        if type(path) is self.__class__:
            self.__dict__.update(path.__dict__)
        else:
            self.__path = Path(path).resolve()
        
        self.keep = bool(keep)
        self.__stats = {}
        self.update_stats(stats)
        self.update_stats()

    def update_stats(self, stats: dict[FileStat, str] = None):
        """Update file stats from CSV if dict provided, otherwise fetch from OS."""
        result = dict(self.__stats)
        if stats:
            for key, val in stats.items():
                result[key] = self.from_str(key, val)
        else:
            self.__exists = self.path.exists()
            if not self.exists:
                return False
            result.update(self.current_stats())
        self.__stats = MappingProxyType(result)
        return True
    
    def open(self, *args, **kws):
        """Open file for IO"""
        return open(self.path, *args, **kws)
    
    def view(self):
        """Open file in system viewer"""
        return subprocess.call(['open', self.path.as_posix()])
    
    def __eq__(self, other: Self):
        return self.path.__eq__(other.path)
    
    def __hash__(self) -> int:
        return self.path.__hash__()
    
    def __str__(self) -> str:
        return (
            f"{'*' if self.keep else '-'} {self.short} | " +
            " | ".join(self.to_str(stat) for stat in FileStat)
        )
    
    def __repr__(self) -> str:
        return f"{'*' if self.keep else 'X'}{self.path}"
    
    @classmethod
    def __to_dt(cls, val):
        """Convert input to datetime object"""
        if val is None or val == "":
            return datetime.max
        if type(val) is str:
            try:
                val = float(val)
            except ValueError:
                try:
                    return datetime.strptime(val, cls._DATE_FMT)
                except:
                    pass
        if type(val) in (int, float):
            return datetime.fromtimestamp(val)
        return datetime.max


class FileGroup(list[File]):
    """Creates a List object w/ additional 'stat' field"""
    def __init__(self, stat: FileStat, itr: Iterable = None):
        self.stat = FileStat(stat)
        super().__init__(self) if itr is None else super().__init__(self, itr)

    def only(self, keep: bool):
        """Get only files with keep flag set to given value"""
        return [p for p in self if p.keep == keep]

    def view(self, only_deleted = False):
        """Open files in system viewer. keep_only only views Files with keep flag."""
        paths = self.only(False) if only_deleted else self
        return subprocess.call(['open'] + [p.path.as_posix() for p in paths])
    
    def add_unique(self, values: Iterable[File] | Self):
        """Iterate through values, appending unique ones."""
        self.extend(val for val in values if val not in self)
    
    def __str__(self) -> str:
        files = "\n  ".join(str(file) for file in self)
        return f'{self.stat.name}:\n  {files}'
    
    @classmethod
    def append_to(Cls, dictionary: dict[Hashable,Self], stat: FileStat, key: Hashable, value: File):
        """Append value to exisiting dict, otherwise start new list"""
        if key not in dictionary:
            dictionary[key] = Cls(stat)
        if dictionary[key].stat != stat:
            raise TypeError(f"FileGroup type mistmatch: {dictionary[key].stat.name}. {stat.name}")
        dictionary[key].append(value)
