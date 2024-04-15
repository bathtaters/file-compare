from .common.avFile import AVFile
from .common.hasher import Hasher
from .common.ffstream import FFStream
from file_compare.base.compPlugin import ComparisonPlugin, EnumGet
from file_compare.base.compFilePlugin import FileAlgos

class AVStat(EnumGet):
    AV_MEDIA = "Media Type"
    AV_CONTAINER = "Container"
    AV_BITRATE = "Bitrate"
    AV_DUR = "Duration"
    AV_HASH = "Media Hash"
    AV_STREAMS = "Streams"


class AVAlgos(FileAlgos):

    def __init__(self, vid_containers: list[str] = None, bitrate_var=0, duration_var=0, **settings):
        super().__init__(**settings)
        
        self.max_dur = self.min_max_algo(lambda f: f.stats.get(AVStat.AV_DUR), False, duration_var)
        self.max_streams = self.min_max_algo(lambda f: len(f.stats.get(AVStat.AV_STREAMS)), False)
        self.max_bitrate = self.min_max_algo(lambda f: f.stats.get(AVStat.AV_BITRATE), False, bitrate_var)
        self.pref_container = self.array_index_algo(vid_containers, lambda f, v: f.to_hash(AVStat.AV_CONTAINER) == v)

        self.algorithms[None] = [self.max_dur, self.max_streams, self.max_bitrate] + self.algorithms[None] + [self.pref_container]



class AVPlugin(ComparisonPlugin):
    """Hash and comparison functions for fileCompare tool"""

    STATS = AVStat

    ALGO_BUILDER = AVAlgos

    GROUP_BY = [AVStat.AV_DUR, AVStat.AV_HASH, AVStat.AV_STREAMS]

    EXTS = (
        '.flv', '.swf',
        '.mov', '.qt',
        '.ogg', '.webm',
        '.mp4', '.m4p', '.m4v',
        '.avi', '.mpg',
        '.mp2', '.mpeg', '.mpe', '.mpv',
        '.wmv',
    )
    """Ordered list of av extensions to use"""

    def current_stats(self):
        """For each Stat, get its value from the file."""
        file = AVFile(self.path)
        return {
            AVStat.AV_MEDIA: file.media,
            AVStat.AV_CONTAINER: file.container,
            AVStat.AV_BITRATE: file.bitrate,
            AVStat.AV_DUR: file.duration,
            AVStat.AV_HASH: file.hash,
            AVStat.AV_STREAMS: file.streams,
        }
    
    @classmethod
    def to_hash(cls, stat: AVStat, value):
        """Return a hash corresponding to the provided Stat on the File"""
        
        if stat in (AVStat.AV_MEDIA, AVStat.AV_CONTAINER):
            return value.lower()
        if stat == AVStat.AV_STREAMS:
            value = cls.from_str(stat, cls.to_str(stat, value))
            return AVFile.to_json(value)
        return value
    
    @classmethod
    def from_hash(cls, stat: AVStat, hash):
        """Returns a stat value based on the given hash"""
        if stat == AVStat.AV_STREAMS:
            return AVFile.to_streams(hash)
        return hash

    @classmethod
    def comparison_funcs(cls):
        """Comparison functions for each Stat. { Stat: (hash1, hash2) -> bool} }
        Optional to override default hash equality function (==)."""

        threshold = cls.settings.get("threshold", 100) # 100 = exact match
        return {
            AVStat.AV_HASH: lambda a,b,t=threshold: bool(a) and a.matches(b, t),
        }

    @classmethod
    def to_str(cls, stat: AVStat, value):
        """Convert value of stat to a string for display/CSV.
        Optional to override default to_str function (str())."""
        if stat == AVStat.AV_STREAMS:
            return " | ".join(str(s) for s in sorted(value))
        return super().to_str(stat, value)
    
    @classmethod
    def from_str(cls, stat: AVStat, value: str):
        """Convert result of to_str back into stat value"""
        if stat == AVStat.AV_BITRATE:
            return int(value)
        if stat == AVStat.AV_DUR:
            return float(value)
        if stat == AVStat.AV_HASH:
            return Hasher.from_str(value)
        if stat == AVStat.AV_STREAMS:
            return [FFStream.from_str(s) for s in value.split(" | ")]
        return value

