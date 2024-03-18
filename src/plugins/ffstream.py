from typing import Self
from json import dumps
from ..base.compUtils import RichCompare, to_metric, sortlist, sortnum

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
    def type(self):
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
        if len(fps) == 2: return float(fps[0]) / float(fps[1])
        return None
    
    def json(self):
        """Stream data as simple dict"""
        if self.type == "video":
            return {
                "type": self.type,
                "codec": self.codec,
                "bitrate": self.bitrate,
                "duration": self.duration,
                "width": self.width,
                "height": self.height,
                "fields": self.fields,
                "fps": self.fps,
            }
        return {
            "type": self.type,
            "codec": self.codec,
            "bitrate": self.bitrate,
            "duration": self.duration,
        }
    
    @classmethod
    def from_json(cls, json: dict[str]):
        """Create stream from JSON string"""
        data: dict[str] = {}
        
        data["codec_type"] = json["type"]
        if "codec" in json:
            data["codec_name"] = json["codec"]
        if "bitrate" in json:
            data["bit_rate"] = json["bitrate"]
        if "duration" in json:
            data["duration"] = json["duration"]
        if "width" in json:
            data["width"] = json["width"]
        if "height" in json:
            data["height"] = json["height"]
        if "fields" in json:
            data["field_order"] = json["fields"]
        if "fps" in json:
            fraction = cls.__fps_to_str(json["fps"])
            if fraction:
                data["r_frame_rate"] = fraction
        return cls(data)
    
    def __str__(self) -> str:
        base =  f"{self.type.capitalize()} <{self.codec}>: {round(self.duration,2)}s ({to_metric(self.bitrate, 'bps')})"
        if self.type.lower() == 'video':
            return f"{base} @ {round(self.fps,2)}fps, {self.width}x{self.height}{self.fields[:1]}"
        return base
    
    def __repr__(self) -> str:
        return dumps(self.data, indent=2)
    
    def _cmp(self, other: Self):
        """Compare a stream to this stream, required for RichCompare method generator."""
        if self.type != other.type:
            return sortlist(self.type, other.type, self._TYPE_ORDER, "stream")
        elif self.codec != other.codec:
            return sortlist(self.codec, other.codec, self._CODEC_ORDER.get(self.type,[]), "codec")
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
        for div in (1001,):
            if round(fps * div / 1000, 3) == num:
                return str(f"{num * 1000}/{div}")
        return None
    