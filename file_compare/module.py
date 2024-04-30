from json import dumps
from pathlib import Path
from .base.compFile import File, FileGroup
from .base.compCsv import CSVParser
from .base.compScan import FileScanner
from .base.compKeep import FileAutoKeeper
from .base.compSanit import check_data, clean_data
from .base.compIO import delete_files, move_files, recover_files
from .base.compUtils import get_idx, printerr, EnumGet
from .base.compPlugin import ComparisonPlugin
from .base.compFilePlugin import FilePlugin


class ComparisonController:
    """
    Find similar files, delete duplicates and import/export CSVs.
    
    To extend comparison stats:
    1) Create plugin classes off of ComparisonPlugin (See compPlugin.py for more info)
    2) Add to plugins property on creation, or use register_plugin() method.
    3) Add Stats to group_by & headers (or leave them unset) to ensure they're used.
    4) Add plugin_settings on creation or via register_plugin() method.
    """

    def __init__(
        self,
        roots: list[str | Path],
        exts: list[str] = None,
        ignore: list[str] = [],
        *,
        group_by: list[EnumGet | str] = None,
        headers: list[EnumGet] = None,
        logpath: str | Path = None,
        clean_filter: int = None,
        view_filter: int = 0,
        verbose = False,
        plugins: list[ComparisonPlugin] = [],
        **plugin_settings,
    ) -> None:
        """
        Create new FileComparison tool
        - roots are a list of dirs that will be scanned for files (In order of location preference for auto-keeping)
        - exts in a list of file extensions to scan, in order of preference (most > least)
        - ignore in a list of filenames to skip scanning (i.e. .DS_Store)
        - group_by is a list of StatEnums to create FileGroups of
        - headers is the header for the CSV file
        - logpath will create a log file at the given path that can be used to recover interrupted scans
        - clean_filter is the minimum number of stats two files must share to remain in a group while cleaning.
        - view_filter is the minimum number of files a group must have to appear in the view list.
        - verbose will print each duplicate that is found
        - plugins should include any ComparisonPlugins you wish to use (FilePlugin is always included)
        - plugin_settings allows additional keyword args to be passed through to ComparisonPlugins
            - Default Settings:
                - time_var {float}: The +/- variance allowed in seconds for matching files times.
                - size_var {int}: The +/- variance allowed in bytes for matching file sizes.
                - min_name {int}: The shortest filename length that will use the alternative matcher.
                - rm_paths: {str[]}: List of base paths, ONLY files under these paths will be marked for removal,
                    bypassing other rules.
            - Plus settings to be passed to custom plugins
        """
        self.roots = [Path(r).expanduser().resolve() for r in roots]
        self.verbose = verbose
        self.group_by = group_by
        self.view_filter = view_filter
        self.clean_filter = clean_filter
        self.plugin_settings = plugin_settings
        File.plugins = [FilePlugin] + plugins

        for plugin in File.plugins:
            plugin.settings = plugin_settings
        
        if headers is None:
            headers = []
            for plugin in File.plugins:
                headers.extend(p for p in plugin.STATS if p not in plugin._HIDDEN)

        self.comparer = FileScanner(exts, ignore, logpath=logpath, verbose=verbose)
        self.keeper = FileAutoKeeper(verbose, exts=exts, roots=roots, **plugin_settings)

        if verbose:
            printerr(f"Setup ComparisonController with options: {dumps(self.__dict__, default=str, indent=2)}")

        self._data: list[FileGroup] = []
        self._csv = CSVParser(headers)


    def scan(self, dirs: list[str | Path] = None):
        """Recursively scan all dirs and store similar files"""
        self._data = self.comparer.run(self.__roots(dirs), self._group_by())
        return self._data
    
    
    def load_csv(self, csv_path: str | Path):
        """Load file data from CSV"""
        self._data = self._csv.read(csv_path, [p.STATS for p in File.plugins])
        return self._data
    
    
    def save_csv(self, csv_path: str | Path):
        """Save file data to CSV"""
        if self._csv.write(csv_path, self._data, [p.STATS for p in File.plugins]):
            self.comparer.cleanup()
        

    def view_all(self, only_deleted = False):
        """Open files in system viewer, one by one"""
        files: FileGroup
        printerr("Viewing groups " + (
            f"(With at least {self.view_filter} matches)..."
            if self.view_filter else "..."
        ))
        filtered = [(i,g) for i,g in enumerate(self._data) if len(g) >= self.view_filter]
        idx = -1
        while True:
            idx, grp, files = get_idx(f"Open group {idx+1} or skip to", filtered, idx + 1)
            if idx is None:
                break
            print(f"  Viewing group {idx}", f"(#{grp})" if grp != idx else "")
            files.view(only_deleted)

    
    def auto_keep(self):
        """Use auto-keep alogrithm to mark files. Will not delete any already marked files."""
        printerr("Auto-keeping files...")
        self.clean(silent=True)

        self.keeper.init()
        for files in self._data:
            if files.stat in self._group_by():
                self.keeper.run(files)

    
    def reset_keep(self, value = False):
        """Sets value of keep on all files to same value"""
        printerr(f"{'Enabling' if value else 'Removing'} all keep flags...")
        for files in self._data:
            for file in files:
                file.keep = value

    
    def delete(self):
        """Delete all files not marked to keep. Returns list of deleted files."""
        deleted, failed = delete_files(self.integrity(), self.verbose)
        if deleted is None:
            return None

        del_cnt, _ = self.clean(clean_solo=True)[0]

        print (f"Deleted {len(deleted)} files ({del_cnt} rows), unable to delete {len(failed)}.")
        return deleted
    

    def move(self, dirs: list[Path | str] = None):
        """Move all files not marked to keep to dir on same volume.
        If no dirs provided, use self.roots.
        Returns list of moved files (With original paths)."""
        moved, failed = move_files(
            self.integrity(),
            self.__roots(dirs),
            self.verbose
        )
        if moved is None:
            return None

        print (f"Moved {len(moved)} files, unable to move {len(failed)}.")
        return moved


    def recover(self, dirs: list[Path | str] = None):
        """Recover all files from dir back into folders specified in data.
        If no dirs provided, use self.roots.
        Returns list of moved files."""
        recovered, failed = recover_files(
            self.integrity(skip_clean=True),
            self.__roots(dirs),
            self.verbose
        )
        if recovered is None:
            return None

        print (f"Recovered {len(recovered)} files, unable to recover {len(failed)}.")
        return recovered
    
    
    def integrity(self, clean_solo = False, skip_clean = False):
        """Integrity check of data
        - Confirms each group has at least one file to keep
        - Removes files that no longer exist if skip_clean = False
        - Returns list of files marked for deletion"""
        
        printerr("Checking data integrity...")
        if not skip_clean:
            self.clean(silent=True, clean_solo=clean_solo)
        to_delete = check_data(self._data)
        return to_delete
    
    
    def clean(self, *, clean_solo = False, clean_kept = False, use_filter = False, silent = False):
        """Checks each file, removing deleted ones.
        - If clean_solo is True, will remove groups with one member.
        - If clean_kept is True, will remove all groups whoose entire group is marked to keep.
        - If use_filter is True, will remove files who don't share > clean_filter stats with any other group member.
        - If silent is True, hides start output.
        - Returns a count of (deleted files, removed groups)"""

        if not silent:
            printerr("Cleaning up file groups"+ (
                f" (With at least {self.clean_filter} matching stats)..."
                if self.clean_filter else "..."
            ))
        
        result = clean_data(
            self._data,
            clean_solo,
            clean_kept,
            self.clean_filter if use_filter else 0,
            self.verbose,
        )
        return result
    
    
    def delete_str(self, cmd = "rm"):
        """Build a list of files to delete as a space-seperated/escaped string."""
        to_delete = self.integrity()
        return f"{cmd} {' '.join(path.quoted for path in to_delete)}"


    def register_plugin(self, plugin: type[ComparisonPlugin] = None, header: list[EnumGet] = None, **plugin_settings):
        """Add a new plugin and/or settings to the engine
        - header: Add Stats to CSV header (Default: Add all plugin.STATS)
        - raises TypeError if invalid type or ValueError if plugin is duplicate."""

        if plugin is not None:
            if not issubclass(plugin, ComparisonPlugin):
                raise TypeError("Plugin must descend from ComparisonPlugin", plugin)
            if plugin in File.plugins:
                raise ValueError("Plugin has alredy been registered", plugin)
            
            if header is None:
                header = [stat for stat in plugin.STATS if stat not in plugin._HIDDEN]
            for stat in header:
                if stat not in self._csv.hdr:
                    self._csv.hdr.append(stat)
                    
            plugin.settings = self.plugin_settings
            File.plugins.append(plugin)

        self.plugin_settings.update(plugin_settings)


    def deregister_plugin(self, plugin: type[ComparisonPlugin], header: list[EnumGet] = None):
        """Remove a plugin that was previously registered.
        - header: Remove Stats from CSV header (Default: Remove all plugin.STATS)"""

        if header is None:
            header = [stat for stat in plugin.STATS if stat not in plugin._HIDDEN]
        for stat in header:
            if stat in self._csv.hdr:
                self._csv.hdr.remove(stat)
        
        File.plugins.remove(plugin)


    def __str__(self):
        string = ""
        for i, files in enumerate(self._data):
            string += f"\n{i}\n"
            for file in files:
                string += f"  {file}\n"
        return string
    

    def __roots(self, roots: list[str | Path] = None):
        """Set & return value of roots using new value or exisiting if none provided."""
        if roots is not None:
            File.roots = [Path(r) for r in roots]
        elif self.roots:
            File.roots = self.roots.copy()
        return File.roots
    
    def _group_by(self):
        """Get actual value of GroupBy (As Stat list)"""
        group_by: list[EnumGet] = []

        if self.group_by is None:
            for plugin in File.plugins:
                if plugin.GROUP_BY is None:
                    group_by.extend(plugin.STATS)
                else:
                    group_by.extend(plugin.GROUP_BY)
            return group_by
        
        stat_enums: list[EnumGet] = [p.STATS for p in File.plugins]
        for stat in self.group_by:
            group_by.append(EnumGet.get(stat, stat_enums))
        return group_by