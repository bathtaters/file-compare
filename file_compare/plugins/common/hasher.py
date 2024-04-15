from typing import Self, TypeAlias, Literal
from pathlib import Path
from videohash import VideoHash
from imagehash import ImageHash, hex_to_hash, average_hash
from acoustid import fingerprint_file, compare_fingerprints
from PIL import Image
from numpy import count_nonzero


HashFormat: TypeAlias = Literal["image"] | Literal["video"] | Literal["audio"]
VALID_FORMATS: tuple[HashFormat] = ("image", "video", "audio")


class Hasher:
    """
    Abstract Hasher class. Must implement:
    - self.matches(other: Hasher | None, threshold %)
    - str(self) = string
    - Hasher.from_file(file, precision?)
    - Hasher.from_str(string)

    Use Hasher(hash) to set self.hash.
    """

    def __init__(self, hash) -> None:
        """
        Create a new hash object
        """
        self.hash = hash

    
    def matches(self, other: Self, threshold: float | int = None) -> bool:
        """
        Test if this hashes match another hash
        - threshold is how close of a match they are in percentage (100% = exact)
        """
        raise NotImplementedError("matches")
    
    
    def __str__(self) -> str:
        raise NotImplementedError("str")
    

    @staticmethod
    def from_str(string: str):
        """Convert string into the assumed hasher"""
        if not string:
            return None
        if ":" in string:
            return AudioHasher.from_str(string)
        return VideoHasher.from_str(string)
    
    
    @staticmethod
    def from_file(file: str | Path | Image.Image, precision=64, format: HashFormat = "image"):
        """Hash the given file."""
        try:
            if isinstance(file, Image.Image) or format == "image":
                hasher = ImageHasher
            elif format == "video":
                hasher = VideoHasher
            elif format == "audio":
                hasher = AudioHasher
            else:
                raise ValueError(f"Invalid hash format '{format}'. Expected: {', '.join(VALID_FORMATS)}")
            
            return hasher.from_file(file, precision)
            
        except ValueError as e:
            if hasattr(file, "filename"):
                file = file.filename
            if type(file) is Path:
                file = file.as_posix()
            print(f'    WARNING: Skipping hash check for {file} - {e}')
            return None
        


class ImageHasher(Hasher):
    """Calculate perceptual hash of image file"""

    hash: ImageHash
    
    def matches(self, other: Self, threshold: float | int = None) -> bool:
        if other is None or type(self) is not type(other):
            return False
        if len(self.hash) != len(other.hash):
            raise ValueError("Perceptual hash array size mismatch.", len(self.hash), len(other.hash))
        
        limit = max(int((1 - threshold / 100) * len(self.hash)), 0)
        return count_nonzero(self.hash.hash != other.hash.hash) <= limit
    

    def __str__(self) -> str:
        return self.hash.__str__()
    

    @classmethod
    def from_str(cls, string: str) -> Self:
        if not string:
            return None
        return cls(hex_to_hash(str(string)))
    

    @classmethod
    def from_file(cls, file: str | Path | Image.Image, precision: int = 64) -> None:
        """
        Create a new hash object from a file
        - precision is how large of a hash to use (power of 2)
        """
        if isinstance(file, Image.Image):
            cls(average_hash(file, precision))
        else:
            with Image.open(file) as img:
                cls(average_hash(img, precision))
        


class VideoHasher(ImageHasher):
    """Calculate perceptual hash of video file"""
    
    @classmethod
    def from_file(cls, file: str | Path | Image.Image, precision: int = 64) -> None:
        vhash = VideoHash(Path(file).as_posix()).hash_hex[2:]
        return cls(hex_to_hash(vhash))
    


class AudioHasher(Hasher):
    """Calculate acoustic fingerprint of file"""

    hash: tuple[float, bytes]
    
    def matches(self, other: Self, threshold: float | int = None) -> bool:
        if other is None or type(self) is not type(other):
            return False
        return compare_fingerprints(self.hash, other.hash) >= threshold / 100.0
    

    def __str__(self) -> str:
        return f"{round(self.hash[0], 2)}:" + self.hash[1].decode()
    

    @classmethod
    def from_str(cls, string: str) -> Self:
        if not string:
            return None
        dur, fp = string.split(":")
        return cls((float(dur), fp.encode()))
    

    @classmethod
    def from_file(cls, file: str | Path, precision: int = 64) -> None:
        """
        Create a new hash object from a file
        - precision is how much of the file to use (x 4 sec)
        """
        return cls(fingerprint_file(file, precision * 4))

