from typing import Self
from json import dumps
from re import compile, IGNORECASE
from file_compare.base.compUtils import RichCompare, to_metric, from_metric, sortlist, sortnum

class FFStream(RichCompare):
    """Single stream within a media file"""

    _TYPE_ORDER = ("video","audio","data")
    """Order of codec_types from most to least important."""

    _CODEC_ORDER: dict[str, tuple[str]] = {
        "video": (
            "prores", "h264",
        ),
        "audio": (
            "wav", "aac",
        ),
        "data": tuple()
    }
    """Dict of ordered lists of codec names, indexed by codec type."""
    
    def __init__(self, stream_data: dict) -> None:
        self.data = stream_data
    
    @property
    def media(self):
        return self.data.get("codec_type")
    
    @property
    def codec(self):
        return self.data.get("codec_name")
    
    @property
    def bitrate(self):
        return int(self.data.get("bit_rate",0))
    
    @property
    def duration(self):
        return float(self.data.get("duration",0))
    
    @property
    def width(self):
        return int(self.data.get("width",0))
    
    @property
    def height(self):
        return int(self.data.get("height",0))
    
    @property
    def resolution(self):
        return self.width * self.height
    
    @property
    def fields(self):
        return self.data.get("field_order")
    
    @property
    def fps(self):
        fps = self.data.get("r_frame_rate", "0/0/0").split("/")
        if len(fps) == 1: return float(fps[0])
        if len(fps) != 2 or not int(fps[1]): return None
        return float(fps[0]) / (float(fps[1]))
    
    @property
    def attached_pic(self):
        return self.data.get("disposition",{}).get("attached_pic", False)
    
    def json(self):
        """Stream data as simple dict"""
        if self.media == "video":
            return {
                "media": self.media,
                "codec": self.codec,
                "bitrate": self.bitrate,
                "duration": self.duration,
                "width": self.width,
                "height": self.height,
                "fields": self.fields,
                "fps": self.fps,
            }
        return {
            "media": self.media,
            "codec": self.codec,
            "bitrate": self.bitrate,
            "duration": self.duration,
        }
    
    @classmethod
    def from_json(cls, json: dict[str]):
        """Create stream from JSON string"""
        data: dict[str] = {}
        
        data["codec_type"] = json["media"].lower()
        if "codec" in json:
            data["codec_name"] = json["codec"]
        if "bitrate" in json:
            data["bit_rate"] = int(json["bitrate"])
        if "duration" in json:
            data["duration"] = float(json["duration"])
        if "width" in json:
            data["width"] = int(json["width"])
        if "height" in json:
            data["height"] = int(json["height"])
        if "fields" in json:
            data["field_order"] = json["fields"]
        if "fps" in json:
            fraction = cls.__fps_to_str(json["fps"])
            if fraction:
                data["r_frame_rate"] = fraction
        return cls(data)
    
    _FIELD_DICT = { "p": "progressive", "i": "interlaced" }
    __RX_BASE = compile(r"^(\w+)\s*<([^>]+)>:\s*([0-9\.]+)\s*s\s*\(([\d\.]+\s*\w?)bps\)(.*)$", IGNORECASE)
    __RX_VID = compile(r"^\s*@\s*([0-9\.]+)fps,?\s*(\d+)\s*x\s*(\d+)([A-Za-z]?)$", IGNORECASE)

    @classmethod
    def from_str(cls, string: str):
        """Create FFStream from a string"""
        data = {}

        match = cls.__RX_BASE.match(string)
        if not match:
            raise ValueError("Invalid string format. unable to create Stream", string)
        data["media"] = match.group(1)
        data["codec"] = match.group(2)
        data["duration"] = match.group(3)
        data["bitrate"] = from_metric(match.group(4).upper())
        vid_data = match.group(5)

        match = cls.__RX_VID.match(vid_data)
        if not match:
            return cls.from_json(data) # Not video
        data["fps"] = match.group(1)
        data["width"] = match.group(2)
        data["height"] = match.group(3)
        data["fields"] = cls._FIELD_DICT.get(match.group(4))
        return cls.from_json(data)

    def __str__(self) -> str:
        base =  f"{self.media.capitalize()} <{self.codec}>: {round(self.duration,2)}s ({to_metric(self.bitrate, 'bps')})"
        if self.media.lower() == 'video':
            return f"{base} @ {round(self.fps or 0,3)}fps, {self.width}x{self.height}{(self.fields or '')[:1]}"
        return base
    
    def __repr__(self) -> str:
        return dumps(self.data, indent=2)
    
    def _cmp(self, other: Self):
        """Compare a stream to this stream, required for RichCompare method generator."""
        if self.media != other.media:
            return sortlist(self.media, other.media, self._TYPE_ORDER, "stream")
        elif self.codec != other.codec:
            return sortlist(self.codec, other.codec, self._CODEC_ORDER.get(self.media,[]), "codec")
        elif self.duration != other.duration:
            return sortnum(self.duration, other.duration)
        elif self.bitrate != other.bitrate:
            return sortnum(self.bitrate, other.bitrate)
        elif self.resolution != other.resolution:
            return sortnum(self.resolution, other.resolution)
        elif self.fields != other.fields:
            return sortnum(self.fields, other.fields, True)
        elif self.fps != other.fps:
            return sortnum(self.fps, other.fps, True)
        return 0
    
    @staticmethod
    def __fps_to_str(fps: str | int | float):
        """Convert float FPS to fraction (ie. 24000/1001 for 23.976)"""
        if not fps:
            return None
        
        fps = float(fps)
        if fps.is_integer():
            return str(fps)
        
        num = round(fps)
        for n, d in ((1001,1000),(2000,1993)):
            if round(fps * n / d, 3) == num:
                return str(f"{round(num * d)}/{n}")
        return None
