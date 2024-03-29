from PIL import Image
from pillow_heif import register_heif_opener
from .hasher import Hasher
from ..base.compPlugin import ComparisonPlugin, EnumGet
from ..base.compFilePlugin import FileAlgos

register_heif_opener()  # Allow scanning HEIF/HEIC files

class ImageStats(EnumGet):
    IMG_TYPE = "Encoding"
    IMG_PXL = "Pixel Format"
    IMG_SIZE = "Dimensions"
    IMG_HASH = "Image Hash"
    IMG_FRAMES = "Framecount"


class ImageAlgos(FileAlgos):

    def __init__(self, img_codecs: list[str] = None, dimension_var=0, **settings):
        super().__init__(**settings)
        
        self.max_frames = self.min_max_algo(lambda f: f.stats.get(ImageStats.IMG_FRAMES), False)
        self.max_size = self.min_max_algo(lambda f: f.hash(ImageStats.IMG_SIZE), False, dimension_var)
        self.pref_codec = self.array_index_algo(img_codecs, lambda f, v: f.hash(ImageStats.IMG_TYPE) == v)

        self.algorithms[None] = [self.max_frames] + self.algorithms[None] + [self.max_size, self.pref_codec]


class ImagePlugin(ComparisonPlugin):
    """Hash and comparison functions for fileCompare tool"""

    STATS = ImageStats

    ALGO_BUILDER = ImageAlgos

    GROUP_BY = [ImageStats.IMG_HASH]

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
        data: dict[ImageStats] = {}
        precision = self.settings.get("precision", self._DEF_PRECISION)
        with Image.open(self.path) as img:
            data[ImageStats.IMG_TYPE] = img.format
            data[ImageStats.IMG_PXL] = img.mode
            data[ImageStats.IMG_SIZE] = img.size
            data[ImageStats.IMG_HASH] = Hasher.from_file(img, hash_size=precision)
            data[ImageStats.IMG_FRAMES] = getattr(img, "n_frames", 1)
        return data
    
    def hash(self, stat: ImageStats, value):
        """Return a hash corresponding to the provided Stat on the File"""
        
        if stat == ImageStats.IMG_SIZE:
            return value[0] * value[1]
        if stat == ImageStats.IMG_TYPE:
            return value.lower()
        return value

    @classmethod
    def comparison_funcs(cls):
        """Comparison functions for each Stat. { Stat: (hash1, hash2) -> bool} }
        Optional to override default hash equality function (==)."""

        threshold = cls.settings.get("threshold", 100) # 100 = exact match
        return {
            ImageStats.IMG_HASH: lambda a,b,t=threshold: a.matches(b, t),
        }

    def to_str(self, stat: ImageStats, value):
        """Convert value of stat to a string for display/CSV.
        Optional to override default to_str function (str())."""
        if stat == ImageStats.IMG_SIZE:
            return "x".join(str(d) for d in value)
        return str(value)
    
    def from_str(self, stat: ImageStats, value: str):
        """Convert result of to_str back into stat value"""
        if stat == ImageStats.IMG_SIZE:
            return tuple(int(d) for d in value.split("x"))
        if stat == ImageStats.IMG_HASH:
            return Hasher.from_hex(value)
        if stat == ImageStats.IMG_FRAMES:
            return int(value)
        return str(value)

