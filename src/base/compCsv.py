import csv
from pathlib import Path
from .compFile import File, FileGroup, FileStat
from .compUtils import EnumGet, is_yes, printerr, find_nested


class CsvStat(EnumGet):
    """Special stats for CSV file, not in FileStat.
    Value is CSV column name."""
    
    GROUP = "Group"
    BY = "Type"
    KEEP = "Keep"
    PATH = "Path"


class CSVParser:
    """Simplify reading/writing of CSVs"""

    _DEFAULT_HDR = list(CsvStat) + list(FileStat)
    """Default Header: CsvStat + FileStat members"""

    def __init__(self, header: list[CsvStat | FileStat] = None) -> None:
        self.hdr = self._DEFAULT_HDR if header is None else header
    

    def read(self, filepath: str | Path):
        """Import CSV as list of filepath arrays"""
        data: dict[int,FileGroup] = {}

        printerr(f'Loading CSV from {filepath}...')
        with open(filepath, "r") as f:
            csvfile = csv.reader(f)

            self._set_hdr(next(csvfile))
            for row in csvfile:
                if not row:
                    continue

                key = self._read_cell(CsvStat.GROUP, row)
                if key not in data:
                    data[key] = FileGroup(FileStat[self._read_cell(CsvStat.BY, row)])
                
                path = Path(self._read_cell(CsvStat.PATH,row))
                try:
                    data[key].append(
                        find_nested(data.values(), lambda f: f.path == path)
                    )
                except ValueError:
                    data[key].append(
                        File(
                            path=path,
                            keep=bool(self._read_cell(CsvStat.KEEP,row)),
                            stats=dict(
                                (col, self._read_cell(col, row))
                                for col in self.hdr
                                if type(col) is FileStat
                            ),
                        )
                    )
        return [data[idx] for idx in sorted(data)]
    

    def write(self, filepath: str | Path, data: list[FileGroup]):
        """Store data in CSV"""
        
        if Path(filepath).exists():
            if not is_yes("CSV exists. Overwrite"):
                return

        printerr(f'Saving CSV to {filepath}...')
        with open(filepath, "w") as f:
            csvfile = csv.writer(f)
            csvfile.writerow(cell.value for cell in self.hdr)
            for group, files in enumerate(data):
                for file in files:
                    csvfile.writerow(self._write_cell(col, file, group, files) for col in self.hdr)
    

    
    def _set_hdr(self, csv_hdr: list[str]):
        """Update self.hdr from CSV header"""
        new_hdr: list[CsvStat | FileStat] = []

        for col in csv_hdr:
            for val in self._DEFAULT_HDR:
                try:
                    new_hdr.append(val.get(col))
                    break
                except ValueError:
                    pass
            else:
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
        
        cell = row[idx]
        if type(cell) is str:
            cell = cell.strip()
            if cell.isdigit():
                cell = int(cell)
        return cell
    

    @staticmethod
    def _write_cell(col: FileStat | CsvStat, file: File, grp_idx: int, group: FileGroup):
        """Get value of col for given File/group"""
        if type(col) is FileStat:
            return file.to_str(col)
        elif col == CsvStat.GROUP:
            return grp_idx
        elif col == CsvStat.BY:
            return group.stat.name
        elif col == CsvStat.PATH:
            return str(file.path)
        elif col == CsvStat.KEEP:
            return "x" if file.keep else ""
        return None

