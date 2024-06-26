from typing import Self, Hashable, Callable, Iterable
from types import MappingProxyType
import subprocess
from pathlib import Path
from .compFilePlugin import FilePlugin
from .compPlugin import ComparisonPlugin
from .compUtils import EnumGet, get_parent, printerr


class File:
    """Representation of a file"""

    plugins: list[type[ComparisonPlugin]] = [FilePlugin]
    """List of plugins to use for all Files"""
    
    roots: list[Path] = []
    """List of root paths, to remove for 'short' path formatting"""

    _comparers: dict[EnumGet, Callable[[Hashable, Hashable], bool]] = None
    """Cached comparison functions."""

    @property
    def path(self):
        """Path of this file (read-only)"""
        return self.__path
    
    @property
    def stats(self) -> MappingProxyType[EnumGet]:
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
        return f'"{self.path.as_posix()}"'

    keep: bool
    """True/False to retain file while cleaning files"""

    def __init__(
        self,
        path: str | Path | Self,
        stats: dict[EnumGet] = {},
        keep = False,
    ):
        if type(path) is self.__class__:
            self.__dict__.update(path.__dict__)
        else:
            self.__path = Path(path).expanduser().resolve()

        self.extensions: list[ComparisonPlugin] = []
        for plugin in self.plugins:
            try:
                self.extensions.append(plugin(self.path))
            except ComparisonPlugin.InvalidFile:
                pass
        
        self.keep = bool(keep)
        self.__stats = {}
        self.update_stats(stats)
    
    def uses_plugin(self, plugin: type[ComparisonPlugin]):
        """Indicates if the provided Plugin class is used in this file's extensions."""
        return any(type(ext) is plugin for ext in self.extensions)

    def update_stats(self, stats: dict[EnumGet, str] = None):
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
    
    def match_count(self, other: Self, max_matches: int = None):
        """Count the number of matching stats between two files."""
        if self is other:
            return max_matches or len(self.stats)
        
        matches = 0
        for stat in self.stats:
            if max_matches is not None and matches >= max_matches:
                return matches
            
            other_hash = other.to_hash(stat)
            if other_hash is None:
                continue
            try:
                matches += self.compare(stat, self.to_hash(stat), other_hash)
            except Exception as e:
                printerr(f"Error comparing {self.short} to {other.short} on {stat}: {e}")
            
        return matches
    
    def current_stats(self):
        """Combined stats of all plugins"""
        stats: dict[EnumGet] = {}
        for extension in self.extensions:
            stats.update(extension.current_stats())
        return stats
    
    def to_hash(self, stat: EnumGet) -> Hashable | None:
        """Get hash from the cooresponding plugin"""
        for extension in self.extensions:
            if type(stat) is extension.STATS:
                return extension.to_hash(stat, self.stats[stat])
        return None

    def to_str(self, stat: EnumGet) -> str | None:
        """Get string value from the cooresponding plugin"""
        for extension in self.extensions:
            if type(stat) is extension.STATS:
                return extension.to_str(stat, self.stats[stat])
        return None
    
    def from_str(self, stat: EnumGet, value: str):
        """Convert string to value using the cooresponding plugin"""
        for extension in self.extensions:
            if type(stat) is extension.STATS:
                return extension.from_str(stat, value)
        return value
    
    @classmethod
    def compare(cls, stat: EnumGet, a: Hashable, b: Hashable) -> bool:
        """Compare two stat values, returning True if they are a match."""
        if cls._comparers is None:
            cls.refresh_comparison_funcs()

        if stat in cls._comparers:
            if callable(cls._comparers[stat]):
                return cls._comparers[stat](a, b)
            return cls._comparers[stat]
        return a == b
    
    @classmethod
    def hash_to_str(cls, stat: EnumGet, hash: Hashable):
        """Convert the given hash to a string"""
        for plugin in cls.plugins:
            if type(stat) is plugin.STATS:
                return plugin.to_str(stat, plugin.from_hash(stat, hash))
        raise TypeError(f"Stat {stat} has no cooresponding plugin!")
    
    @classmethod
    def str_to_hash(cls, stat: EnumGet, string: str):
        """Convert the given hash to a string"""
        for plugin in cls.plugins:
            if type(stat) is plugin.STATS:
                return plugin.to_hash(stat, plugin.from_str(stat, string))
        raise TypeError(f"Stat {stat} has no cooresponding plugin!")
    
    @classmethod
    def refresh_comparison_funcs(cls):
        """Combined comparison functions of all plugins"""
        cls._comparers = {}
        for plugin in cls.plugins:
            cls._comparers.update(plugin.comparison_funcs())
    
    def __eq__(self, other: Self):
        return self.path.__eq__(other.path)
    
    def __hash__(self) -> int:
        return self.path.__hash__()
    
    def __str__(self) -> str:
        return (
            f"{'*' if self.keep else '-'} {self.short} | " +
            " | ".join(str(self.to_str(stat)) for stat in self.stats)
        )
    
    def __repr__(self) -> str:
        return f"{'*' if self.keep else 'X'}{self.path}"


class FileGroup(list[File]):
    """Creates a List object w/ additional 'stat' field"""
    def __init__(self, stat: EnumGet, itr: Iterable = None):
        if not isinstance(stat, EnumGet):
            raise TypeError("FileGroup requires stat to be an Enum type.", type(stat), stat)
        self.stat = stat
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
    
    def get_plugins(self):
        """Get a list of plugin classes used by this group"""
        return [
            p for p in File.plugins
            if all(file.uses_plugin(p) for file in self)
        ]
    
    def __str__(self) -> str:
        files = "\n  ".join(str(file) for file in self)
        return f'{self.stat.name}:\n  {files}'
    
    @classmethod
    def append_to(Cls, dictionary: dict[Hashable,Self], stat: EnumGet, value: File, key: Hashable):
        """Append value to exisiting dict, otherwise start new list"""
        if key not in dictionary:
            dictionary[key] = Cls(stat)
        if dictionary[key].stat != stat:
            raise TypeError(f"FileGroup type mistmatch: {dictionary[key].stat.name}. {stat.name}")
        dictionary[key].append(value)
