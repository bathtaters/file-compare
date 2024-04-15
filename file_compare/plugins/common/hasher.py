from typing import Self, TypeAlias, Literal
from pathlib import Path
from videohash import VideoHash
from imagehash import ImageHash, hex_to_hash, average_hash, NDArray
from PIL import Image
from numpy import count_nonzero


HashFormat: TypeAlias = Literal["image"] | Literal["video"] | Literal["audio"]


class Hasher(ImageHash):
    """Calculate perceptual hash of media file"""

    VALID_FORMATS: tuple[HashFormat] = ("image", "video", "audio")

    hash: NDArray
    """Raw hash array"""

    @classmethod
    def from_file(cls, filepath: str | Path | Image.Image, format: HashFormat = "image", hash_size=64):
        """
        Hash the given file, if is_video if False will be treated an image.
        Also accepts an instance of Image if you already have one open.
        If is_video is True, hash_size will be forced to be 64.
        """
        try:
            if isinstance(filepath, Image.Image):
                return cls(average_hash(filepath, hash_size).hash)
            elif format not in cls.VALID_FORMATS:
                raise ValueError(f"Invalid hash format '{format}'. Expected: {', '.join(HASH_FMTS)}")
            elif format == "video":
                vhash = VideoHash(Path(filepath).as_posix()).hash_hex[2:]
                return cls(hex_to_hash(vhash).hash)
            elif format == "audio":
                raise NotImplementedError() # TODO: Implement
            with Image.open(filepath) as img:
                return cls(average_hash(img, hash_size).hash)
            
        except ValueError as e:
            path = filepath
            if hasattr(path, "filename"):
                path = path.filename
            if type(path) is Path:
                path = path.as_posix()
            print('    WARNING: Skipping hash check for',path,'-',e)
            return None
    
    @classmethod
    def from_hex(cls, hash_hex: str | ImageHash):
        """Create a hash instance from another instance's string"""
        if not hash_hex:
            return None
        return cls(hex_to_hash(str(hash_hex)).hash)
        
    def matches(self: Self, other: Self | None, threshold=100):
        """
        Test if this hashes match another hash
        - threshold is how close of a match they are in percentage (100% = exact)
        """
        if other is None:
            return False
        if len(self) != len(other):
            raise ValueError("Perceptual hash array size mismatch.", len(self), len(other))
        
        limit = max(int((1 - threshold / 100) * len(self)), 0)
        return count_nonzero(self.hash != other.hash) <= limit

