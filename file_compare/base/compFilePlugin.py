from typing import Any, Hashable, Callable
from datetime import datetime, timedelta
from .compPlugin import ComparisonPlugin
from .compAlgos import KeepAlgorithms, Algorithm
from .compUtils import EnumGet, to_metric, from_metric, range_matcher, length_matcher


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


class FileAlgos(KeepAlgorithms):

    min_name: Algorithm
    """Get list of all files containing the shortest filename"""
    max_size: Algorithm
    """Get list of all files containing the largest filesize"""
    oldest_ctime: Algorithm
    """Get list of all files containing the earliest created date"""
    newest_mtime: Algorithm
    """Get list of all files containing the most recent modified date"""
    pref_exts: Algorithm
    """Get a list of files containing the most preferred extensions"""
    pref_loc: Algorithm
    """Get a list of files containing the most preferred location"""
    

    def __init__(self, exts: list[str] = None, roots: list[str] = None, size_var=0, time_var=0, **_):
        super().__init__()
        
        self.min_name = self.min_max_algo(lambda f: len(f.path.stem), True)
        self.max_size = self.min_max_algo(lambda f: f.to_hash(FileStat.SIZE), False, size_var)
        self.oldest_ctime = self.min_max_algo(lambda f: f.to_hash(FileStat.CTIME), True, time_var)
        self.newest_mtime = self.min_max_algo(lambda f: f.to_hash(FileStat.MTIME), False, time_var)
        self.pref_exts = self.array_index_algo(exts, lambda f, v: f.path.suffix.lower() == v)
        self.pref_loc = self.array_index_algo(roots, lambda f, v: f.path.is_relative_to(v))

        self.algorithms = {
            None: [self.max_size, self.pref_exts, self.pref_loc, self.min_name, self.newest_mtime, self.oldest_ctime],
            FileStat.SIZE: [self.newest_mtime, self.pref_exts, self.pref_loc, self.min_name],
        }
        


class FilePlugin(ComparisonPlugin[FileStat]):
    """Default File scanner plugin"""

    STATS = FileStat

    ALGO_BUILDER = FileAlgos

    def current_stats(self):
        """Fetch stats dict from filesystem"""
        return {
            FileStat.NAME: self.path.stem,
            FileStat.SIZE: self.path.stat().st_size if self.path.exists() else 0,
            FileStat.CTIME: self.__round_dt(datetime.fromtimestamp(self.path.stat().st_ctime)),
            FileStat.MTIME: self.__round_dt(datetime.fromtimestamp(self.path.stat().st_mtime)),
        }
    
    @classmethod
    def to_hash(cls, stat: FileStat, value) -> Hashable | None:
        """Returns a hash corresponding to the provided stat"""
        if stat == FileStat.NAME:
            return value.lower()
        elif stat in (FileStat.CTIME, FileStat.MTIME):
            return round(value.timestamp())
        return value
    
    @classmethod
    def from_hash(cls, stat: FileStat, hash: Hashable) -> Any:
        """Returns a stat value based on the given hash"""
        if stat in (FileStat.CTIME, FileStat.MTIME):
            return datetime.fromtimestamp(hash)
        return hash

    @classmethod
    def comparison_funcs(cls) -> dict[FileStat, Callable[[Hashable, Hashable], bool]]:
        """Comparison functions for FileStats, to override default hash equality function (==)"""
        return {
            FileStat.NAME: length_matcher(cls.settings.get("min_name", 3)),
            FileStat.SIZE: range_matcher(cls.settings.get("size_var", 0)),
            FileStat.CTIME: range_matcher(cls.settings.get("time_var", 0)),
            FileStat.MTIME: range_matcher(cls.settings.get("time_var", 0)),
        }

    @classmethod
    def to_str(cls, stat: FileStat, value) -> str | None:
        """Convert value of stat to a string for display/CSV"""
        if stat == FileStat.SIZE:
            return to_metric(value, "B", 16)
        elif stat == FileStat.CTIME:
            return value.strftime(cls._DATE_FMT)
        elif stat == FileStat.MTIME:
            return value.strftime(cls._DATE_FMT)
        return super().to_str(stat, value)
    
    @classmethod
    def from_str(cls, stat: FileStat, value: str):
        """Convert result of to_str back into stat type"""
        if stat == FileStat.SIZE:
            return round(from_metric(value))
        elif stat == FileStat.CTIME:
            return cls.__to_dt(value)
        elif stat == FileStat.MTIME:
            return cls.__to_dt(value)
        return value
    
    
    _DATE_FMT = "%m-%d-%Y %H:%M:%S"
    """Default datetime format for reading/writing to CSV"""
    
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

    @staticmethod
    def __round_dt(val: datetime):
        if val.microsecond >= 500000:
            val += timedelta(seconds=1)
        return val.replace(microsecond=0)
