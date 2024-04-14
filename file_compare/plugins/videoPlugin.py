from .videoFile import VideoFile
from .ffstream import FFStream
from .hasher import Hasher
from file_compare.base.compPlugin import ComparisonPlugin, EnumGet
from file_compare.base.compFilePlugin import FileAlgos

class VideoStat(EnumGet):
    VID_TYPE = "Container"
    VID_BITRATE = "Bitrate"
    VID_DUR = "Duration"
    VID_HASH = "Video Hash"
    VID_STREAMS = "Streams"


class VideoAlgos(FileAlgos):

    def __init__(self, vid_containers: list[str] = None, bitrate_var=0, duration_var=0, **settings):
        super().__init__(**settings)
        
        self.max_dur = self.min_max_algo(lambda f: f.stats.get(VideoStat.VID_DUR), False, duration_var)
        self.max_streams = self.min_max_algo(lambda f: len(f.stats.get(VideoStat.VID_STREAMS)), False)
        self.max_bitrate = self.min_max_algo(lambda f: f.stats.get(VideoStat.VID_BITRATE), False, bitrate_var)
        self.pref_type = self.array_index_algo(vid_containers, lambda f, v: f.to_hash(VideoStat.VID_TYPE) == v)

        self.algorithms[None] = [self.max_dur, self.max_streams, self.max_bitrate] + self.algorithms[None] + [self.pref_type]



class VideoPlugin(ComparisonPlugin):
    """Hash and comparison functions for fileCompare tool"""

    STATS = VideoStat

    ALGO_BUILDER = VideoAlgos

    GROUP_BY = [VideoStat.VID_DUR, VideoStat.VID_HASH, VideoStat.VID_STREAMS]

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
            VideoStat.VID_TYPE: video.container,
            VideoStat.VID_BITRATE: video.bitrate,
            VideoStat.VID_DUR: video.duration,
            VideoStat.VID_HASH: video.hash,
            VideoStat.VID_STREAMS: video.streams,
        }
    
    @classmethod
    def to_hash(cls, stat: VideoStat, value):
        """Return a hash corresponding to the provided Stat on the File"""
        
        if stat == VideoStat.VID_TYPE:
            return value.lower()
        if stat == VideoStat.VID_STREAMS:
            value = cls.from_str(stat, cls.to_str(stat, value))
            return VideoFile.to_json(value)
        return value
    
    @classmethod
    def from_hash(cls, stat: VideoStat, hash):
        """Returns a stat value based on the given hash"""
        if stat == VideoStat.VID_STREAMS:
            return VideoFile.to_streams(hash)
        return hash

    @classmethod
    def comparison_funcs(cls):
        """Comparison functions for each Stat. { Stat: (hash1, hash2) -> bool} }
        Optional to override default hash equality function (==)."""

        threshold = cls.settings.get("threshold", 100) # 100 = exact match
        return {
            VideoStat.VID_HASH: lambda a,b,t=threshold: bool(a) and a.matches(b, t),
        }

    @classmethod
    def to_str(cls, stat: VideoStat, value):
        """Convert value of stat to a string for display/CSV.
        Optional to override default to_str function (str())."""
        if stat == VideoStat.VID_STREAMS:
            return " | ".join(str(s) for s in sorted(value))
        return super().to_str(stat, value)
    
    @classmethod
    def from_str(cls, stat: VideoStat, value: str):
        """Convert result of to_str back into stat value"""
        if stat == VideoStat.VID_BITRATE:
            return int(value)
        if stat == VideoStat.VID_DUR:
            return float(value)
        if stat == VideoStat.VID_HASH:
            return Hasher.from_hex(value)
        if stat == VideoStat.VID_STREAMS:
            return [FFStream.from_str(s) for s in value.split(" | ")]
        return value
