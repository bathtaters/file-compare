from typing import Hashable, Callable
from datetime import datetime
from .compPlugin import ComparisonPlugin
from .compAlgos import KeepAlgorithms
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

    min_name: Callable[[list],list]
    """Get list of all files containing the shortest filename"""
    max_size: Callable[[list],list]
    """Get list of all files containing the largest filesize"""
    oldest_ctime: Callable[[list],list]
    """Get list of all files containing the earliest created date"""
    newest_mtime: Callable[[list],list]
    """Get list of all files containing the most recent modified date"""
    pref_exts: Callable[[list],list]
    """Get a list of files containing the most preferred extensions"""
    pref_loc: Callable[[list],list]
    """Get a list of files containing the most preferred location"""
    

    def __init__(self, exts: list[str] = None, roots: list[str] = None, size_var=0, time_var=0, **_):
        
        self.min_name = self.min_max_algo(lambda f: len(f.path.stem), True)
        self.max_size = self.min_max_algo(lambda f: f.hash(FileStat.SIZE), False, size_var)
        self.oldest_ctime = self.min_max_algo(lambda f: f.hash(FileStat.CTIME), True, time_var)
        self.newest_mtime = self.min_max_algo(lambda f: f.hash(FileStat.MTIME), False, time_var)
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
            FileStat.CTIME: datetime.fromtimestamp(self.path.stat().st_ctime),
            FileStat.MTIME: datetime.fromtimestamp(self.path.stat().st_mtime),
        }
    
    def hash(self, stat: FileStat, value) -> Hashable | None:
        """Returns a hash corresponding to the provided stat"""
        if stat == FileStat.NAME:
            return value.lower()
        elif stat == FileStat.CTIME:
            return round(value.timestamp())
        elif stat == FileStat.MTIME:
            return round(value.timestamp())
        return value

    @classmethod
    def comparison_funcs(cls) -> dict[FileStat, Callable[[Hashable, Hashable], bool]]:
        """Comparison functions for FileStats, to override default hash equality function (==)"""
        return {
            FileStat.NAME: length_matcher(cls.settings.get("min_name", 3)),
            FileStat.SIZE: range_matcher(cls.settings.get("size_var", 0)),
            FileStat.CTIME: range_matcher(cls.settings.get("time_var", 0)),
            FileStat.MTIME: range_matcher(cls.settings.get("time_var", 0)),
        }

    def to_str(self, stat: FileStat, value) -> str | None:
        """Convert value of stat to a string for display/CSV"""
        if stat == FileStat.SIZE:
            return to_metric(value, "B")
        elif stat == FileStat.CTIME:
            return value.strftime(self._DATE_FMT)
        elif stat == FileStat.MTIME:
            return value.strftime(self._DATE_FMT)
        return str(value)
    
    def from_str(self, stat: FileStat, value: str):
        """Convert result of to_str back into stat type"""
        if stat == FileStat.SIZE:
            return from_metric(value)
        elif stat == FileStat.CTIME:
            return self.__to_dt(value)
        elif stat == FileStat.MTIME:
            return self.__to_dt(value)
        return value
    
    
    _DATE_FMT = "%m-%d-%Y %H:%M"
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

