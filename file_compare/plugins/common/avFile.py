from pathlib import Path
from subprocess import run
from json import loads, dumps
from .hasher import Hasher
from .ffstream import FFStream, to_metric


class AVFile:
    """Analyzer for video/audio file"""

    __SKIP_HASH = False
    """Skip running time-consuming hash algorithm. (For debuggine since these are time-consuming)"""

    __TYPE_PREF = ("video", "audio", "data")
    """Order of preference for codec types"""
    
    __cmd = [
        'ffprobe',
        '-v', 'quiet',
        '-print_format', 'json',
        '$FILE', # Replace with filename
        '-show_format',
        '-show_streams'
    ]
    """Command to get media info"""

    def __init__(self, filepath: str | Path, precision: int = 64, with_hash = True) -> None:
        self.path = Path(filepath)
        raw = self.fetch_data(self.path)
        self.data = raw.get("format", {})
        self.streams = [FFStream(s) for s in raw.get("streams", {})]
        self.hash = None
        self.media = self._get_media()

        if with_hash and not self.__SKIP_HASH:
            self.hash = Hasher.from_file(filepath, precision, self.media)
    
    @property
    def container(self):
        return self.data.get("format_long_name")

    @property
    def duration(self):
        return float(self.data.get("duration",0))
    
    @property
    def bitrate(self):
        if self.data.get("bit_rate"):
            return int(self.data["bit_rate"])
        return sum(s.bitrate for s in self.streams)
    
    @property
    def stream(self):
        """Main stream of file"""
        for stream in self.streams:
            if stream.media == self.media:
                return stream
        return None
    
    def __str__(self) -> str:
        # 12s (12Kpbs)
        string = f"{self.path.name} <{self.container}>: {round(self.duration,2)}s ({to_metric(self.bitrate, 'bps')})"
        string += f"\n  - Hash: {self.hash}"
        for stream in sorted(self.streams):
            string += f"\n  - {stream}"
        return string
    
    def __repr__(self) -> str:
        data = {
            "format": self.data,
            "duration": self.duration,
            "streams": [s.data for s in self.streams],
        }
        if self.hash is not None:
            data["hash"] = str(self.hash)
        return dumps(data, indent=2)
    
    def _get_media(self):
        """Get media type of file"""
        types = {}
        for stream in self.streams:
            if stream.attached_pic:
                continue
            types[stream.media] = types.get(stream.media,0) + 1

        for pref in self.__TYPE_PREF:
            if types.get(pref):
                return pref
        return next(iter(types), None)
    
    @staticmethod
    def to_json(streams: list[FFStream], indent: int | str = None):
        """Get JSON string from streams list"""
        return dumps([s.json() for s in sorted(streams)], indent=indent)
    
    @staticmethod
    def to_streams(json: str):
        """Get streams list from JSON string"""
        return [FFStream.from_json(s) for s in loads(json)]

    @classmethod
    def fetch_data(cls, filepath: str | Path) -> dict:
        """Runs FFProbe command and returns resulting dictionary, or raise TypeError if no data"""
        cmd = [(str(filepath) if c == '$FILE' else c) for c in cls.__cmd]
        res = run(cmd, capture_output=True)
        if not res.stdout:
            raise TypeError(f"ERROR, Not readable by FFProbe: {filepath}")
        return loads(res.stdout)
