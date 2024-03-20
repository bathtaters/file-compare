from typing import TypeVar, Generic, Hashable, Callable, Any
from pathlib import Path
from .compUtils import EnumGet

Stat = TypeVar("Stat", bound=EnumGet)

class ComparisonPlugin(Generic[Stat]):
    """
    Comparison Plugin: Implement custom comparisons.

    Required overrides:
    - Props: STATS
    - Methods: current_stats, hash, from_str

    Optional overrides:
    - Props: EXTS, GROUP_BY
    - Methods: __init__, comparison_funcs, to_str

    NOTE: To use custom AutoKeep algorithms,
    open compAlgos.py and edit FileAutoKeeper directly.
    1) Import StatEnum to compAlgos.py.
    2) Add algorithm method to FileAutoKeeper class.
    3) Add method to FileAutoKeeper.default_order and/or new entry in FileAutoKeeper.algorithms.
    """

    EXTS: tuple[str] = None
    """List of valid extensions for this plugin or None to match all.
    Extensions should be lower case, must include '.'"""

    STATS: type[Stat] = EnumGet
    """Extension of EnumGet containing the Stats supported by this plugin"""

    GROUP_BY: list[Stat] | None = None
    """Recommended stats to use for file-grouping (Default: None => all STATS)"""

    settings: dict[str] = {}
    """plugin_settings passed in from ComparisonController"""

    path: Path
    """Underlying file to run comparison on."""

    def __init__(self, path: Path) -> None:
        """
        Create a new instance of this plugin.
        - `path: Path` path to a file.
        - Raises: `self.InvalidFile` if the file extension doesn't match.
        - Raise this Error yourself for additional file validation.
        """

        if self.EXTS is not None and path.suffix.lower() not in self.EXTS:
            raise self.InvalidFile("Invalid extension.", path.suffix)
        self.path = path

    
    def current_stats(self) -> dict[Stat]:
        """For each Stat, get its value from the file."""
        raise NotImplementedError("current_stats")
    
    def hash(self, stat: Stat, value: Any) -> Hashable | None:
        """Return a hash corresponding to the provided Stat on the File"""
        raise NotImplementedError("hash")

    @classmethod
    def comparison_funcs(_) -> dict[Stat, Callable[[Hashable, Hashable], bool]]:
        """Comparison functions for each Stat.
        Optional to override default hash equality function (==)."""
        return {}

    def to_str(self, stat: Stat, value: Any) -> str | None:
        """Convert value of stat to a string for display/CSV.
        Optional to override default to_str function (str())."""
        return str(value)
    
    def from_str(self, stat: Stat, value: str) -> Any:
        """Convert result of to_str back into stat value"""
        raise NotImplementedError("from_str")
    

    class InvalidFile(TypeError):
        """File is not a match for this plugin"""
        pass