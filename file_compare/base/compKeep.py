from .compFile import File, FileGroup
from .compAlgos import KeepAlgorithms, Algorithm
from .compPlugin import ComparisonPlugin
from .compUtils import EnumGet, printerr


class FileAutoKeeper:
    """Automatically mark files to keep/delete.
    - Runs each algorithm under each File.Plugin, in order, until a single file is left to keep
    - NOTE: exts/locations should be ordered from [most > least preferred]
    """

    not_rm_path: Algorithm | None
    algorithms: dict[type[ComparisonPlugin] | EnumGet, list[Algorithm]]
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
        self.algorithms = {}
        
        for plugin in File.plugins:
            algos = plugin.ALGO_BUILDER(**self.settings).algorithms
            if None in algos:
                self.algorithms[plugin] = algos.pop(None)
            self.algorithms.update(algos)

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
    

    def get_algos(self, files: FileGroup):
        """Get the most specific algorithm list that works for the given `FileGroup`.
        If a default is needed and none found, walk up the plugin list until one is found.
        (This should always at least find FileAlgos[None] if nothing better.)"""

        if files.stat in self.algorithms:
            return self.algorithms[files.stat]  # Exact match
        
        for plugin in reversed(files.get_plugins()):
            if plugin in self.algorithms:
                return self.algorithms[plugin]  # Most specific default
            
        raise ValueError(f"No valid algorithm found for <{files.stat}> {files}.")
    

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
        for func in self.get_algos(files):
            if len(matches) < 2:
                break
            matches = func(matches)     # Whittle down matches
            if not matches:
                printerr("  WARNING! No matches kept from set.", [p.short for p in files])

        if matches:
            matches[0].keep = True      # Keep the first file in the list
