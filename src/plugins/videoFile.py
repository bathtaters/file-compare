from pathlib import Path
from subprocess import run
from json import loads, dumps
from .ffstream import FFStream, to_metric
from .hasher import Hasher


class VideoFile:
    """Analyzer for video file"""

    __SKIP_HASH = False
    """Skip running time-consuming hash algorithm. (For debuggine since these are time-consuming)"""
    
    __cmd = [
        'ffprobe',
        '-v', 'quiet',
        '-print_format', 'json',
        '$FILE', # Replace with filename
        '-show_format',
        '-show_streams'
    ]
    """Command to get media info"""

    def __init__(self, filepath: str | Path) -> None:
        self.path = Path(filepath)
        raw = self.fetch_data(self.path)
        self.data = raw.get("format", {})
        self.streams = [FFStream(s) for s in raw.get("streams", {})]
        self.hash = None
        if not self.__SKIP_HASH:
            self.hash = Hasher.from_file(filepath, is_video=True)
    
    @property
    def container(self):
        return self.data.get("format_long_name")

    @property
    def duration(self):
        return float(self.data.get("duration",0))
    
    @property
    def bitrate(self):
        if self.data.get("bitrate") is not None:
            return int(self.data["bitrate"])
        return sum(s.bitrate for s in self.streams)
    
    @property
    def stream(self):
        """Main video stream"""
        for stream in self.streams:
            if stream.media == "video":
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
