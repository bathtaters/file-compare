from PIL import Image
from pillow_heif import register_heif_opener
from .common.hasher import ImageHasher
from file_compare.base.compPlugin import ComparisonPlugin, EnumGet
from file_compare.base.compFilePlugin import FileAlgos

register_heif_opener()  # Allow scanning HEIF/HEIC files

class ImageStat(EnumGet):
    IMG_TYPE = "Encoding"
    IMG_SIZE = "Dimensions"
    IMG_HASH = "Image Hash"
    IMG_FRAMES = "Framecount"


class ImageAlgos(FileAlgos):

    def __init__(self, img_codecs: list[str] = None, dimension_var=0, **settings):
        super().__init__(**settings)
        
        self.max_frames = self.min_max_algo(lambda f: f.stats.get(ImageStat.IMG_FRAMES), False)
        self.max_size = self.min_max_algo(lambda f: f.to_hash(ImageStat.IMG_SIZE), False, dimension_var)
        self.pref_codec = self.array_index_algo(img_codecs, lambda f, v: f.to_hash(ImageStat.IMG_TYPE) == v)

        self.algorithms[None] = [self.max_frames] + self.algorithms[None] + [self.max_size, self.pref_codec]


class ImagePlugin(ComparisonPlugin):
    """Hash and comparison functions for fileCompare tool"""

    STATS = ImageStat

    ALGO_BUILDER = ImageAlgos

    GROUP_BY = [ImageStat.IMG_HASH]

    EXTS = (
        '.heic', '.heif', '.tif', '.tiff', '.png',
        '.jpg', '.jpeg', '.jpe', '.jif', '.jfif', '.jfi',
        '.jp2', '.j2k', '.jpf', '.jpx', '.jpm', '.mj2',
        '.gif', '.webp', '.bmp', '.dib',
    )
    """Ordered list of image extensions to use"""

    _DEF_PRECISION = 8
    """Default hash size (_DEF_PRECIISON ^ 2 = actual size of hash)"""

    def current_stats(self):
        """For each Stat, get its value from the file."""
        data: dict[ImageStat] = {}
        precision = self.settings.get("precision", self._DEF_PRECISION)
        with Image.open(self.path) as img:
            data[ImageStat.IMG_TYPE] = img.format
            data[ImageStat.IMG_SIZE] = img.size
            data[ImageStat.IMG_HASH] = ImageHasher.from_file(img, precision)
            data[ImageStat.IMG_FRAMES] = getattr(img, "n_frames", 1)
        return data
    
    @classmethod
    def to_hash(cls, stat: ImageStat, value):
        """Return a hash corresponding to the provided Stat on the File""" 
        if stat == ImageStat.IMG_SIZE:
            return value[0] * value[1]
        if stat == ImageStat.IMG_TYPE:
            return value.lower()
        return value

    @classmethod
    def from_hash(cls, stat: ImageStat, hash):
        """Returns a stat value based on the given hash"""
        if stat == ImageStat.IMG_SIZE:
            return (hash, 1)
        return hash
    
    @classmethod
    def comparison_funcs(cls):
        """Comparison functions for each Stat. { Stat: (hash1, hash2) -> bool} }
        Optional to override default hash equality function (==).
        Also can add a static value to specific stats by adding Stat: <value>."""
        threshold = cls.settings.get("threshold", 100) # 100 = exact match
        return {
            ImageStat.IMG_HASH: lambda a,b,t=threshold: bool(a) and a.matches(b, t),
            ImageStat.IMG_FRAMES: lambda a,b: a == b and bool(a) and a > 1,
            ImageStat.IMG_TYPE: False,
            ImageStat.IMG_SIZE: False,
        }

    @classmethod
    def to_str(cls, stat: ImageStat, value):
        """Convert value of stat to a string for display/CSV.
        Optional to override default to_str function (str())."""
        if stat == ImageStat.IMG_SIZE:
            return "x".join(str(d) for d in value)
        return super().to_str(stat, value)
    
    @classmethod
    def from_str(cls, stat: ImageStat, value: str):
        """Convert result of to_str back into stat value"""
        if stat == ImageStat.IMG_SIZE:
            return tuple(int(d) for d in value.split("x"))
        if stat == ImageStat.IMG_HASH:
            return ImageHasher.from_str(value)
        if stat == ImageStat.IMG_FRAMES:
            return int(value)
        return value

