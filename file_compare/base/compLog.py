
from typing import Hashable
from pathlib import Path
from .compFile import File
from .compCsv import CSVParser
from .compUtils import EnumGet, printerr


class CSVLog:
    """
    Read/write data to/from a CSV log
    """

    logpath: Path
    """Path of logfile to write/read"""
    stats: list[type[EnumGet]]
    """Stat descriptors"""
    _csv: CSVParser
    """Underlying CSV I/O object"""

    def __init__(self, logpath: str | Path = None) -> None:
        self.logpath = Path(logpath) if logpath else None
        self.stats = [plugin.STATS for plugin in File.plugins]
        self._csv = CSVParser()

    def open(self, default_enums: list[EnumGet] = []):
        """Check if log exists, determine if it should be recovered"""
        hash_dict = dict((e, {}) for e in default_enums)

        if self.logpath is not None and self.logpath.exists():
            yn = input("An incomplete scan has been found. Would you like to resume (y/n)? ")
            if yn.strip().lower()[0] == "y":
                printerr(f"Recovering data from {self.logpath}...")
                return self._csv.read_log(self.logpath, self.stats, hash_dict)
        
        if self.logpath is not None:
            self._csv.start_log(self.logpath, self.stats)
        return (hash_dict, set(), None)
    
    def append(self, file: File, logdata: list[tuple[EnumGet, str]]):
        """Save current file data to log"""
        if self.logpath is not None:
            self._csv.add_log(self.logpath, file, logdata)
    
    def append_skip(self, skipped: str):
        """Save a skipped extension to log"""
        if self.logpath is not None:
            self._csv.add_log(self.logpath, skip=skipped)

    def remove(self):
        """Delete log"""
        if self.logpath is not None and self.logpath.exists():
            self.logpath.unlink()