import math
from sys import stderr
from pathlib import Path
from re import compile, IGNORECASE
from enum import Enum
from typing import Any, Self, Callable, Iterable, Hashable


def printerr(*args, **kwargs):
    """Print to stderr"""
    print(*args, **kwargs, file=stderr)


def is_yes(prompt: str):
    """Prompt and return True if user entered y"""
    print(f"{prompt} (y/n)?", end=" ")
    res = input()
    return res.strip().lower()[0] == 'y'


def get_parent(child: Path, parents: list[Path]):
    """Get parent directory for child path
    (If multiple match, select the longest one)."""
    parent, size = None, 0
    for curr in parents:
        if len(curr.parts) < size:
            continue
        if child.is_relative_to(curr):
            parent = curr
            size = len(curr.parts)
    return parent


def get_sibling(base: Path, siblings: list[Path]):
    """Get directory on same drive as base path
    (If multiple match, select the first one).
    Raises ValueError on failure"""
    for sibling in siblings:
        drive = get_drive(sibling)
        if drive and base.is_relative_to(drive):
            return sibling
    raise ValueError(f"No provided paths are on the same drive as base path '{base}'")


def get_drive(child: Path):
    """Get drive of Path object (For Windows or Mac)"""
    child = child.resolve()
    try:
        drive = child.parts.index("Volumes")
        return Path(*child.parts[:drive + 2])
    except ValueError:
        return Path(*child.parts[:2])


def find_nested(array: Iterable, test: Callable[[Any], bool]):
    """Find and return value from within an array (Can be nested w/in another array)"""
    for value in array:
        if hasattr(value, "__iter__"):
            try:
                return find_nested(value, test)
            except ValueError:
                pass
        elif test(value):
            return value
    raise ValueError("Test not passed by any value in array.")


def get_idx(prompt: str, array: list, default: int = 0):
    """Get array index from user, using 'default' if non-numeric
    or None if index is out of range or input is 'q'."""
    idx = input(f"{prompt} [0-{len(array) - 1}]: ")
    if idx.isdigit():
        idx = int(idx)
    elif idx and idx[0].lower() == 'q':
        return (None, None)
    else:
        idx = default
    if idx not in range(len(array)):
        return (None, None)
    return (idx, array[idx])


_METRIC_PREFIX = ("", "K", "M", "G", "T", "P", "E", "Z", "Y")
_DIVISOR = 1000 # 1024
def to_metric(num: int | float, suffix = "", deicmals = 2):
    """Convert an number into suffixed representation (i.e. 1000 = 1 K)"""
    if num == 0:
        return f"0 {suffix}"
    i = int(math.floor(math.log(num, _DIVISOR)))
    p = math.pow(_DIVISOR, i)
    s = round(num / p, deicmals)
    return f"{s} {_METRIC_PREFIX[i]}{suffix}"

_METRIC_RE = compile(r"^((?:\d+\,)*\d*\.?\d+)\s?("+"|".join(_METRIC_PREFIX)+")", IGNORECASE)
def from_metric(num_str: str):
    """Convert a suffixed numeric string back into a number"""
    try:
        num, prefix = _METRIC_RE.match(num_str).groups()
        num = float(num.replace(",",""))
        idx = _METRIC_PREFIX.index(prefix.upper())
    except (NameError, ValueError):
        raise ValueError(f"Expecting form of '0.0 K', not '{num_str}'.")
    return num * math.pow(_DIVISOR, idx)

def length_matcher(min_len):
    """Matcher function: Do a standard == if length is less than min_len,
    otherwise trim strings to same length before computing ==."""

    def matcher_func(a: Hashable, b: Hashable) -> bool:
        least = min(len(a), len(b))
        most = max(len(a), len(b))
        if least < min_len or most - least >= least:
            return a == b
        return a[:least] == b[:least]
        
    return matcher_func

def range_matcher(variance) -> Callable[[Hashable, Hashable], bool]:
    """Matcher function: Test that numbers are within +/- variance of each other."""
    if not variance:
        return lambda a, b: a == b
    return lambda a, b : b >= a - variance and b <= a + variance


class EnumGet(Enum):
    """Extend Enum class with getter method,
    expects uppercase member names and capitalized values"""

    @classmethod
    def get(cls, val: Self | str) -> Self | None:
        """Get matching val (Check uppercase names/capitalized values)
        raises a ValueError if not found."""
        if type(val) is cls:
            return val
        try:
            return cls[val.upper()]
        except KeyError:
            pass
        return cls(val.capitalize())


### --- GET UI --- ###

class Option:
    REGEX = compile(r"^-(\w+)(?::(.+))?$")
    DELIM = ","

    @staticmethod
    def strlower(value):
        """Adapt to lowercase string"""
        return str(value).lower()

    def __init__(self, name: str = None, adapt: type = strlower, is_list = False):
        self.name = name
        self.adapt = adapt
        self.is_list = is_list
    
    def get(self, ui: str):
        """Parse UI for value"""
        match = self.REGEX.match(ui)
        if not match: return None
        if match[2] is None: # For 'flags'
            return True if self.adapt is bool else None
        if self.is_list: 
            return [self.adapt(val) for val in (match[2] or '').split(self.DELIM)]
        return self.adapt(match[2])

    @classmethod
    def key(cls, ui: str):
        """Get key from UI or None if not an option"""
        match = cls.REGEX.match(ui)
        return match[1] if match else None


ACTION_MAP = {
    "-s": "SCAN",
    "-k": "KEEP",
    "-d": "DELETE",
    "-rm": "DELSTR",
    "-m": "MOVE",
    "-r": "RECOV",
    "-x": "RESET",
    "-c": "CLEAN",
    "-p": "VIEW",
}

OPT_MAP = {
    "e": Option("exts", is_list=True),
    "i": Option("ignore", is_list=True),
    "g": Option("group_by", is_list=True),
    "sv": Option("size_var", int),
    "tv": Option("time_var", float),
    "v": Option("verbose", bool),
}

def get_ui(args: list[str], help_text: str, default_csv: str):
    """Get UI from argument list, returning (action, options, csv path)"""

    action, opts, csv = "", {"roots": []}, Path(default_csv)

    try:
        for arg in args[1:]:
            lowarg = arg.lower()
            if lowarg in ACTION_MAP:
                action = ACTION_MAP[lowarg]
                continue
            
            option = OPT_MAP.get(Option.key(arg))
            if option:
                opts[option.name] = option.get(arg)

            elif Path(arg).suffix.lower() == '.csv':
                csv = Path(arg)

            elif Path(arg).is_dir():
                opts["roots"].append(Path(arg))
                if not action:
                    action = "SCAN"
            else:
                raise AssertionError(f"ERROR: Unknown option '{arg}'")
        
        if not action:
            raise AssertionError("")
        elif not opts["roots"] and action in ("SCAN", "MOVE", "RECOV"):
            raise AssertionError(f"ERROR: -{action[0]} ({action.capitalize()}) requires non-CSV path argument(s)")

    except AssertionError as e:
        action = ""
        if str(e): printerr(e,'\n')
        print(
            help_text.strip()
                .replace("$MAIN", args[0] or "main.py")
                .replace("$CSV_PATH", default_csv)
        )
    return (action, opts, csv)