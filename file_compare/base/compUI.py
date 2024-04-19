from re import compile
from pathlib import Path
from .compUtils import printerr


class Arg:
    """Represents a command line argument"""

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

class ArgError(ValueError):
    pass

MODES = (
    'scan',
    'keep',
    'reset',
    'move',
    'recover',
    'clean',
    'view',
    'delete',
    'rmstr'
)

OPT_MAP = {
    "m": Arg("mode"),
    "g": Arg("group_by", is_list=True),
    "x": Arg("exts", is_list=True),
    "i": Arg("ignore", is_list=True),
    "r": Arg("rm_paths", is_list=True),
    "t": Arg("threshold", int),
    "p": Arg("precision", int),
    "vs": Arg("size_var", int),
    "vt": Arg("time_var", float),
    "vb": Arg("bitrate_var", int),
    "vd": Arg("duration_var", int),
    "vs": Arg("dimension_var", int),
    "fc": Arg("clean_filter", int),
    "fv": Arg("view_filter", int),
    "v": Arg("verbose", bool),
    "h": Arg("help", bool),
}

def get_ui(args: list[str], help_text: str, default_csv: str):
    """Get UI from argument list, returning (action, options, csv path)"""

    opts, csv = {"mode": None, "roots": []}, Path(default_csv)

    try:
        for arg in args[1:]:
            option = OPT_MAP.get(Arg.key(arg))
            if option:
                opts[option.name] = option.get(arg)

            elif Path(arg).suffix.lower() == '.csv':
                csv = Path(arg)

            elif Path(arg).is_dir():
                opts["roots"].append(Path(arg))

            else:
                raise ArgError(f"Unknown option '{arg}'")
        
        if "help" in opts:
            opts.pop("help")
            raise ArgError()
        elif not opts["mode"]:
            raise ArgError()
        elif opts["mode"] not in MODES:
            raise ArgError(f"Invalid mode '-m:{opts['mode']}'")
        elif not opts["roots"] and opts["mode"] in ("scan", "move", "recover"):
            raise ArgError(f"Mode -m:{opts['mode']} requires non-CSV path argument(s)")
        elif opts.get("rm_paths") and any(path not in opts["roots"] for path in opts["rm_paths"]):
            raise ArgError(f"Remove path(s) -r{','.join(opts['rm_paths'])} must be a root path: {','.join(opts['root'])}")
        elif opts.get("precision") and (opts["precision"] & (opts["precision"]-1) != 0):
            raise ArgError(f"Precision -p:{opts['precision']} must be a power of 2")
        elif "threshold" in opts and (opts["threshold"] <= 0 or opts["threshold"] > 100):
            raise ArgError(f"Threshold -t:{opts['threshold']} must be a percentage > 0")

    except ArgError as e:
        opts["mode"] = "" # Forces sys.exit
        print(
            help_text.strip()
                .replace("$MAIN", args[0] or "main.py")
                .replace("$CSV_PATH", default_csv)
        )
        if str(e): printerr('\nERROR: ' + str(e))
    return (opts.pop("mode"), opts, csv)