from typing import TypeVar, Generic, Hashable, Callable, Self, Any
from pathlib import Path
from .compAlgos import KeepAlgorithms
from .compUtils import EnumGet

Stat = TypeVar("Stat", bound=EnumGet)

class ComparisonPlugin(Generic[Stat]):
    """
    Comparison Plugin: Implement custom comparisons.

    Required overrides (All are classmethods unless noted):
    - Props: STATS
    - Methods: current_stats (instance), to_hash, from_hash, from_str

    Optional overrides (All are classmethods):
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

    @classmethod
    def validate(plugin, *instances: Self, ignore_warnings = False):
        """
        Tests that this plugin was implemented correctly:
        - Check that all required methods are implemented
        - Tests all to_... and from_... functions of Plugin are reversible
            - Must provide one or more sample instances to properly test this!
        """
        REQUIRED = ("current_stats", "to_hash", "from_hash", "from_str")
        TO_FROM = ("hash", "str") # to_... from_...

        errors: list[str] = []
        warnings: list[str] = []

        if plugin.STATS is EnumGet or not len(plugin.STATS):
            errors.append("STATS unset or has no defined Stats")
        try:
            if not issubclass(plugin.STATS, EnumGet):
                raise TypeError("STATS not subclass of EnumGet")
        except TypeError:
            errors.append("STATS must extend EnumGet")
        
        for func in REQUIRED:
            if getattr(plugin, func) is getattr(ComparisonPlugin, func):
                errors.append(f"{func} must be overridden.")
        
        if errors:
            if not ignore_warnings:
                errors += warnings
            raise AssertionError(
                f"{plugin.__name__} failed validation:" +
                "\n  - " + "\n  - ".join(errors)
            )
        if not ignore_warnings and warnings:
            print(
                f"{plugin.__name__} warnings:",
                "\n  - " + "\n  - ".join(warnings)
            )

        for instance in instances:
            fname = instance.path.stem
            stats = instance.current_stats()
            
            for stat, from1 in stats.items():
                for func in TO_FROM:
                    to1, from2, to2 = "<FAILED>", "<FAILED>", "<FAILED>"
                    try:
                        to_func = getattr(plugin, f"to_{func}")
                        from_func = getattr(plugin, f"from_{func}")

                        to1 = to_func(stat, from1)
                        from2 = from_func(stat, to1)
                        to2 = to_func(stat, from2)
                        if to1 != to2:
                            errors.append(
                                f"{stat.name} failed to/from_{func} function traversal: "
                                + f"{from1} -> {to1} -> {from2} -> {to2} ({fname})"
                            )
                        elif from1 != from2:
                            warnings.append(
                                f"{stat.name} to/from_{func} function traversal mistmatch: "
                                + f"{from1} -> {to1} -> {from2} ({fname})"
                            )

                    except (AttributeError, TypeError, ValueError) as e:
                        errors.append(
                            f"{stat.name} stat failed to/from_{func} function traversal: "
                            + f"{from1} -> {to1} -> {from2} -> {to2} ({fname}) {e}"
                        )
                    except NotImplementedError as e:
                        errors.append(f"{e} must be overridden.")
        
        if errors:
            if not ignore_warnings:
                errors += warnings
            raise AssertionError(
                f"{plugin.__name__} failed validation:" +
                "\n  - " + "\n  - ".join(errors + warnings)
            )
        if not ignore_warnings and warnings:
            print(
                f"{plugin.__name__} warnings:",
                "\n  - " + "\n  - ".join(warnings)
            )

    