from typing import Callable
from .compFile import File, FileGroup
from .compAlgos import KeepAlgorithms, Algorithm
from .compUtils import EnumGet, printerr


class FileAutoKeeper:
    """Automatically mark files to keep/delete.
    - Runs each algorithm under each File.Plugin, in order, until a single file is left to keep
    - NOTE: exts/locations should be ordered from [most > least preferred]
    """

    not_rm_path: Algorithm | None
    algorithms: dict[EnumGet | type[EnumGet], list[Callable[[list[File]], list[File]]]]
    settings: dict[str]
    verbose: bool

    def __init__(
        self,
        verbose = False,
        **settings,
    ):    
        self.verbose = verbose
        self.settings = settings
        self.algorithms = None
        self.not_rm_path = None

    
    def init(self):
        """Initialize Keeper before running (Builds algorithm functions from File.plugins)"""
        self.algorithms = KeepAlgorithms().algorithms
        for plugin in File.plugins:
            algos: KeepAlgorithms = plugin.ALGO_BUILDER(**self.settings)
            if None in algos.algorithms:
                self.algorithms[plugin.STATS] = algos.algorithms.pop(None)
            self.algorithms.update(algos.algorithms)

        self.not_rm_path = None
        if self.settings.get("rm_paths"):
            self.not_rm_path = KeepAlgorithms.pass_test_algo(
                lambda f, locs=self.settings["rm_paths"]: any(
                    f.path.is_relative_to(loc) for loc in locs
                )
            )
    

    def has_keep(self, files: list[File]):
        """True if any file has 'keep' set to True"""
        return any(file.keep for file in files)
    

    def get_algos(self, stat: EnumGet):
        """Get list of algorithms from stat or default list if not found.
        If no default set, walk File.plugins until a default is found or raise a ValueError.
        (This should come up with the FileAlgos default if not set, which should work for any filetype.)"""
        if stat in self.algorithms:
            return self.algorithms[stat]
        if type(stat) in self.algorithms:
            return self.algorithms[type(stat)]
        for plugin in File.plugins:
            if plugin.STATS in self.algorithms:
                return self.algorithms[plugin.STATS]
        raise ValueError(f"No valid algorithm found for {stat}.")
    

    def run(self, files: FileGroup):
        """Keeps the prevailing files from each group.
        Also keeps files not matched at all (i.e. not the same file)
        
        #### IMPORTANT: Must run init() at least once before running this!"""

        if self.not_rm_path:            # Override, keeping only non rm_paths
            for file in self.not_rm_path(files):
                file.keep = True
            return
        if self.has_keep(files):        # Skip if already marked
            return
        
        matches = list(files)
        for func in self.get_algos(files.stat):
            if len(matches) < 2:
                break
            matches = func(matches)     # Whittle down matches
            if not matches:
                printerr("  WARNING! No matches kept from set.", [p.short for p in files])

        if matches:
            matches[0].keep = True      # Keep the first file in the list
