from typing import TypeVar, Generic, Hashable, Callable, Any
from pathlib import Path
from .compAlgos import KeepAlgorithms
from .compUtils import EnumGet

Stat = TypeVar("Stat", bound=EnumGet)

class ComparisonPlugin(Generic[Stat]):
    """
    Comparison Plugin: Implement custom comparisons.

    Required overrides (All classmethods unless noted):
    - Props: STATS
    - Methods: current_stats (instance), to_hash, from_hash, from_str

    Optional overrides (All classmethods):
    - Props: EXTS, GROUP_BY, ALGO_BUILDER
    - Methods: __init__, comparison_funcs, to_str

    For more info on creating custom algorithms, see compAlgos.KeepAlgorithms
    """

    EXTS: tuple[str] = None
    """List of valid extensions for this plugin or None to match all.
    Extensions should be lower case, must include '.'"""

    STATS: type[Stat] = EnumGet
    """Extension of EnumGet containing the Stats supported by this plugin"""

    GROUP_BY: list[Stat] | None = None
    """Recommended stats to use for file-grouping (Default: None => all STATS)"""

    ALGO_BUILDER: type[KeepAlgorithms] = KeepAlgorithms
    """Class that will build algorithms to use for Keep mode"""

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
    
    @classmethod
    def to_hash(cls, stat: Stat, value: Any) -> Hashable | None:
        """Return a hash corresponding to the provided Stat on the File"""
        raise NotImplementedError("hash")
    
    @classmethod
    def from_hash(cls, stat: Stat, hash: Hashable) -> Any:
        """Inverse of hash function"""
        raise NotImplementedError("from_hash")

    @classmethod
    def comparison_funcs(cls) -> dict[Stat, Callable[[Hashable, Hashable], bool]]:
        """Comparison functions for each Stat.
        Optional to override default hash equality function (==)."""
        return {}

    @classmethod
    def to_str(cls, stat: Stat, value: Any) -> str | None:
        """Convert value of stat to a string for display/CSV.
        Optional to override default to_str function (str())."""
        return None if value is None else str(value)
    
    @classmethod
    def from_str(cls, stat: Stat, value: str) -> Any:
        """Convert result of to_str back into stat value"""
        raise NotImplementedError("from_str")
    

    class InvalidFile(TypeError):
        """File is not a match for this plugin"""
        pass