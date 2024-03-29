from .videoFile import VideoFile
from .ffstream import FFStream
from .hasher import Hasher
from ..base.compPlugin import ComparisonPlugin, EnumGet
from ..base.compFilePlugin import FileAlgos

class VideoStats(EnumGet):
    VID_TYPE = "Container"
    VID_BITRATE = "Bitrate"
    VID_DUR = "Duration"
    VID_HASH = "Video Hash"
    VID_STREAMS = "Streams"


class VideoAlgos(FileAlgos):

    def __init__(self, vid_containers: list[str] = None, bitrate_var=0, duration_var=0, **settings):
        super().__init__(**settings)
        
        self.max_dur = self.min_max_algo(lambda f: f.stats.get(VideoStats.VID_DUR), False, duration_var)
        self.max_streams = self.min_max_algo(lambda f: len(f.stats.get(VideoStats.VID_STREAMS)), False)
        self.max_bitrate = self.min_max_algo(lambda f: f.stats.get(VideoStats.VID_BITRATE), False, bitrate_var)
        self.pref_type = self.array_index_algo(vid_containers, lambda f, v: f.hash(VideoStats.VID_TYPE) == v)

        self.algorithms[None] = [self.max_dur, self.max_streams, self.max_bitrate] + self.algorithms[None] + [self.pref_type]



class VideoPlugin(ComparisonPlugin):
    """Hash and comparison functions for fileCompare tool"""

    STATS = VideoStats

    ALGO_BUILDER = VideoAlgos

    GROUP_BY = [VideoStats.VID_DUR, VideoStats.VID_HASH, VideoStats.VID_STREAMS]

    EXTS = (
        '.flv', '.swf',
        '.mov', '.qt',
        '.ogg', '.webm',
        '.mp4', '.m4p', '.m4v',
        '.avi', '.mpg',
        '.mp2', '.mpeg', '.mpe', '.mpv',
        '.wmv',
    )
    """Ordered list of video extensions to use"""


    def current_stats(self):
        """For each Stat, get its value from the file."""
        video = VideoFile(self.path)
        return {
            VideoStats.VID_TYPE: video.container,
            VideoStats.VID_BITRATE: video.bitrate,
            VideoStats.VID_DUR: video.duration,
            VideoStats.VID_HASH: video.hash,
            VideoStats.VID_STREAMS: video.streams,
        }
    
    def hash(self, stat: VideoStats, value):
        """Return a hash corresponding to the provided Stat on the File"""
        
        if stat == VideoStats.VID_TYPE:
            return value.lower()
        if stat == VideoStats.VID_STREAMS:
            return VideoFile.to_json(value)
        return value

    @classmethod
    def comparison_funcs(cls):
        """Comparison functions for each Stat. { Stat: (hash1, hash2) -> bool} }
        Optional to override default hash equality function (==)."""

        threshold = cls.settings.get("threshold", 100) # 100 = exact match
        return {
            VideoStats.VID_HASH: lambda a,b,t=threshold: a.matches(b, t),
        }

    def to_str(self, stat: VideoStats, value):
        """Convert value of stat to a string for display/CSV.
        Optional to override default to_str function (str())."""
        if stat == VideoStats.VID_STREAMS:
            return " | ".join(str(s) for s in sorted(value))
        return str(value)
    
    def from_str(self, stat: VideoStats, value: str):
        """Convert result of to_str back into stat value"""
        if stat == VideoStats.VID_BITRATE:
            return int(value)
        if stat == VideoStats.VID_DUR:
            return float(value)
        if stat == VideoStats.VID_HASH:
            return Hasher.from_hex(value)
        if stat == VideoStats.VID_STREAMS:
            return [FFStream.from_str(s) for s in value.split(" | ")]
        return str(value)

