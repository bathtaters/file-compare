from .videoFile import VideoPlugin
from .hasher import Hasher
from ..base.compPlugin import ComparisonPlugin, EnumGet

class VideoStats(EnumGet):
    VID_TYPE = "Container"
    VID_BITRATE = "Bitrate"
    VID_DUR = "Duration"
    VID_HASH = "Video Hash"
    VID_STREAMS = "Streams"


class VideoPlugin(ComparisonPlugin):
    """Hash and comparison functions for fileCompare tool"""

    STATS = VideoStats

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

    threshold = 100
    """A percentage of how close the hashes should match (100 = identical)"""

    precision = 64
    """The size of the hash (This is hard-locked by the hashing library)"""

    def current_stats(self):
        """For each Stat, get its value from the file."""
        video = VideoPlugin(self.path)
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
            return VideoPlugin.to_json(value)
        return value

    @classmethod
    def comparison_funcs(cls, threshold = None, **_):
        """Comparison functions for each Stat. { Stat: (hash1, hash2) -> bool} }
        Optional to override default hash equality function (==)."""

        if threshold is None:
            threshold = cls.threshold
        
        return {
            VideoStats.VID_HASH: lambda a,b,t=threshold: a.matches(b, t),
            VideoStats.VID_STREAMS: lambda a,b: a == b,
        }

    def to_str(self, stat: VideoStats, value):
        """Convert value of stat to a string for display/CSV.
        Optional to override default to_str function (str())."""
        if stat == VideoStats.VID_STREAMS:
            return VideoPlugin.to_json(value)
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
            return VideoPlugin.to_streams(value)
        return str(value)

