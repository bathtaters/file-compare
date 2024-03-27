from typing import Callable, TYPE_CHECKING, TypeAlias, Any
from .compUtils import EnumGet

if TYPE_CHECKING:
    from .compFile import File
else:
    File = Any

Algorithm: TypeAlias = Callable[[list[File]], list[File]]
"""Algorithm function, accepts a FileGroup or list of Files, returns a new list of Files that satisfy the algorithm."""
AlgorithmDict: TypeAlias = dict[EnumGet | None, list[Algorithm]]
"""Algorithm dictionary, keys are StatEnums or `None`, values are arrays of `Algorithms`."""

class KeepAlgorithms:
    """
    Class containing Algorithm Functions that will take a list of Files
    and return a subset of that list containing any files that satisfy the given algorithm.

    The input list must be treated as read-only,
    and the resulting list will only contain more than one File if they are tied.

    When extending, must override __init__(**settings), which sets self.algorithms.
    
    To extend:
    1) Create a class that is a child of this (Or a descendant of this to use as a starting point)
        - Note that if you use a descendant, be sure to pass through the **kwargs from init() to it's init() method.
    2) Override `__init__(**settings)` method.
        - `settings` are passed from CompController, and include:
            - `exts` - list of prefered extensions
            - `roots` - list of prefered locations
            - All other plugin_settings sent by user
    3) Call `super().__init__(**settings)` first (No need to pass in settings if you are extending KeepAlgorithms directly).
    4) Create any algorithms you want to use and assign them as instance properties.
    5) Set `self.algorithms` dict using rules:
        - Keys are `StatEnums` related to plugin, or `None`
        - `self.algorithms[StatEnum]` = Order of algorithms for Groupings using this Stat
        - `self.algorithms[None]` = Default order of algorithms
        - If no `StatEnum` value is provided, algorithms fall back to `None`
        - If no `None` provided, algorithms fall back to FileAlgos.algorithms[None]
        - Note that if you are extending a descendant, you may just want to add values to self.algorithms.
    """

    algorithms: AlgorithmDict
    """
    For each File list with given EnumGet, a list of algorithms to run in order.
    Will use algorithms[None] as the default order, if a given Enum is not included in this dict.
    """

    def __init__(self, **settings) -> None:
        self.algorithms = {}


    @staticmethod
    def pass_test_algo(test_func: Callable[[File], bool]) -> Algorithm:
        """Generic Algorithm Generator: Get the file(s) that pass the test function"""
        return lambda files, test_func=test_func: [file for file in files if test_func(file)]


    @staticmethod
    def min_max_algo(get_value: Callable[[File], int | float], is_min: bool, variance = 0) -> Algorithm:
        """
        Generic Algorithm Generator: 
        - Get the value(s) that are the least (is_min=True) or most (is_min=False).
        - Variance allows the value to be in a range of +/- value of variance.
        - All floats will be rounded to the nearest int (Recommend multiplying values, if you expect them to be very close).
        """
        min_func: Callable[[int,range], bool] = lambda a, b: a < b.start
        max_func: Callable[[int,range], bool] = lambda a, b: a > b.stop
        comp_func = min_func if is_min else max_func

        def min_max_val(files: list[File], get_value=get_value, comp_func=comp_func, variance=variance):
            result: list[File] = []
            rng: range = None
            for file in files:
                curr = get_value(file)
                if rng is None or comp_func(curr, rng):
                    result = [file]
                    rng = range(round(curr - variance), round(curr + variance))
                elif (round(curr) in rng if variance else round(curr) == rng.start):
                    result.append(file)
            return result
        
        return min_max_val


    @staticmethod
    def array_index_algo(array: list | None, file_matches_value: Callable[[File, Any], bool], is_min=True) -> Algorithm:
        """Generic Algorithm Generator: Get the value(s) matching the front/back-most (is_min=True/False) value in the array."""

        if not array:
            return lambda files: files
        
        array = [(a.lower() if type(a) is str else a) for a in array]
        
        def get_idx(file: File, array=array, file_matches_value=file_matches_value):
            for i, val in enumerate(array):
                if file_matches_value(file, val):
                    return len(array) - i
            return -1
        
        return KeepAlgorithms.min_max_algo(get_idx, is_min)
