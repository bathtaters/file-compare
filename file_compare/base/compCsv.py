from typing import Hashable
import csv
from pathlib import Path
from .compFile import File, FileGroup
from .compUtils import EnumGet, is_yes, printerr, find_nested


class CsvStat(EnumGet):
    """Special stats for CSV file.
    Value is CSV column name."""
    
    GROUP = "Group"
    BY = "Type"
    KEEP = "Keep"
    PATH = "Path"


class CSVParser:
    """Simplify reading/writing of CSVs"""

    def __init__(self, header: list[EnumGet] = None) -> None:
        self.hdr = header
    

    def read(self, filepath: str | Path, plugins: list[type[EnumGet]]):
        """Import CSV as list of filepath arrays"""

        data: dict[int,FileGroup] = {}

        printerr(f'Loading CSV from {filepath}...')
        self._fix_hdr(plugins)

        with open(filepath, "r") as f:
            csvfile = csv.reader(f)

            self._set_hdr(next(csvfile), plugins)
            for row in csvfile:
                if not row:
                    continue

                key = self._read_cell(CsvStat.GROUP, row)
                if key not in data:
                
                path = Path(self._read_cell(CsvStat.PATH,row))
                try:
                    exisiting = find_nested(data.values(), lambda f: f.path == path)
                    data[key].append(exisiting)
                except ValueError:
                    data[key].append(self._file_from_row(row))
        return [data[idx] for idx in sorted(data)]
    

    def write(self, filepath: str | Path, data: list[FileGroup], plugins: list[type[EnumGet]]):
        """Store data in CSV"""
        
        if Path(filepath).exists():
            if not is_yes("CSV exists. Overwrite"):
                return False

        printerr(f'Saving CSV to {filepath}...')
        self._fix_hdr(plugins)

        with open(filepath, "w") as f:
            csvfile = csv.writer(f)
            csvfile.writerow(cell.value for cell in self.hdr)
            for group, files in enumerate(data):
                for file in files:
                    csvfile.writerow(self._write_cell(col, group, files.stat, file) for col in self.hdr)
        return True
    
    def _file_from_row(self, row: list[str]):
        """Convert CSV row into File object"""
        return File(
            path=Path(self._read_cell(CsvStat.PATH,row)),
            keep=bool(self._read_cell(CsvStat.KEEP,row)),
            stats=dict(
                (col, self._read_cell(col, row))
                for col in self.hdr
                if type(col) is not CsvStat
            ),
        )

    def read_log(self, filepath: str | Path, plugins: list[type[EnumGet]], hash_dict: dict[EnumGet, dict[Hashable, FileGroup]] = {}):
        """Import CSV as list of filepath arrays, optionally starting with the given hash_dict"""

        scanned: set[Path] = set()
        skipped: set[str] = set()
        self._fix_hdr(plugins)

        with open(filepath, "r") as f:
            csvfile = csv.reader(f)

            self._set_hdr(next(csvfile), plugins)
            file: File | None = None
            for row in csvfile:
                if not row:
                    continue

                key = self._read_cell(CsvStat.GROUP, row)
                if key == "FILE":
                    file = self._file_from_row(row)
                    scanned.add(file.path)
                
                elif key == "SKIP":
                    skipped.add(self._read_cell(CsvStat.BY, row))
                    file = None

                elif key != "KEY":
                    printerr("Skipping invalid row key:", key)
                    continue

                elif file is None:
                    printerr("Found unmatched hash while parsing log", row)

                else:
                    stat = EnumGet.get(self._read_cell(CsvStat.BY, row), plugins)
                    hash = file.str_to_hash(stat, self._read_cell(stat, row))
                    if stat not in hash_dict:
                        hash_dict[stat] = {}
                    FileGroup.append_to(hash_dict[stat], stat, file, hash)
                
        return (hash_dict, skipped, scanned)
    

    def start_log(self, filepath: str | Path, plugins: list[type[EnumGet]]):
        """Start a new log CSV"""

        self._fix_hdr(plugins)
        with open(filepath, "w") as f:
            csvfile = csv.writer(f)
            csvfile.writerow(cell.value for cell in self.hdr)


    def add_log(self, filepath: str | Path, file: File = None, hashes: list[tuple[EnumGet, str]] = [], *, skip: str = None):
        """Add a row to the log, may be a file, hash group row OR skipped ext."""

        with open(filepath, "a") as f:
            csvfile = csv.writer(f)
            if file is not None:
                csvfile.writerow(self._write_cell(col, "FILE", file=file) for col in self.hdr)
            for stat, hashstr in hashes:
                csvfile.writerow(
                    (hashstr if col is stat else self._write_cell(col, "KEY", stat))
                    for col in self.hdr
                )
            if skip is not None:
                csvfile.writerow(self._write_cell(col, "SKIP", skip) for col in self.hdr)

    

    def _fix_hdr(self, plugins: list[type[EnumGet]]):
        """Set hdr to all values if None"""
        if self.hdr is None:
            self.hdr = list(CsvStat)
            for plugin in plugins:
                self.hdr.extend(plugin)


    def _set_hdr(self, csv_hdr: list[str], plugins: list[type[EnumGet]]):
        """Update self.hdr from CSV header"""
        new_hdr: list[EnumGet] = []

        for col in csv_hdr:
            try:
                new_hdr.append(EnumGet.get(col, plugins))
                continue
            except ValueError:
                pass
            if len(new_hdr) >= len(self.hdr):
                break
            new_hdr.append(self.hdr[len(new_hdr)])

        self.hdr = new_hdr
    

    def _read_cell(self, col: CsvStat, row: list, default = None):
        """dict.get() method for CSV cell"""
        try:
            idx = self.hdr.index(col)
        except ValueError:
            return default
        if idx >= len(row):
            return default
        return row[idx] or None
    

    @staticmethod
    def _write_cell(col: EnumGet, grp_id: int | str, by_val: EnumGet | str = "", file: File = None):
        """Get value of col for given File/group"""
        if col == CsvStat.GROUP:
            return grp_id
        elif col == CsvStat.BY:
            return str(by_val.name if hasattr(by_val, "name") else by_val)
        elif file is None:
            return ""
        elif col == CsvStat.PATH:
            return str(file.path)
        elif col == CsvStat.KEEP:
            return "x" if file.keep else ""
        return file.to_str(col)
