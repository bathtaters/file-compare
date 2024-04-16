from typing import Self, TypeAlias, Literal
from pathlib import Path
from subprocess import run
from tempfile import gettempdir
from imagehash import ImageHash, hex_to_hash, average_hash
from acoustid import fingerprint_file, compare_fingerprints
from PIL import Image
from numpy import count_nonzero
from file_compare.base.compUtils import printerr


HashFormat: TypeAlias = Literal["image"] | Literal["video"] | Literal["audio"]
VALID_FORMATS: tuple[HashFormat] = ("image", "video", "audio")


class Hasher:
    """
    Abstract Hasher class. Must implement:
    - self.matches(other: Hasher | None, threshold %)
    - str(self) = string
    - Hasher.from_file(file, precision?, duration?)
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
    def from_file(file: str | Path | Image.Image, precision=64, format: HashFormat = "image", duration = 0.0):
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
            
            return hasher.from_file(file, precision, duration)
            
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
        if type(self) is not type(other):
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
    def from_file(cls, file: str | Path | Image.Image, precision: int, *_):
        """
        Create a new hash object from a file
        - precision is how large of a hash to use (power of 2)
        """
        if isinstance(file, Image.Image):
            return cls(average_hash(file, precision))
        else:
            with Image.open(file) as img:
                return cls(average_hash(img, precision))
        


class VideoHasher(Hasher):
    """Calculate perceptual hash of video file"""

    _VHASH_FCOUNT = 10
    _FFMPEG_PATH = "ffmpeg"
    _FFMPEG_LOG = "fatal"
    
    hash: list[ImageHash]
    

    def matches(self, other: Self, threshold: float | int = None) -> bool:
        if type(self) is not type(other):
            return False
        
        frame_count = min(len(self.hash), len(other.hash), self._VHASH_FCOUNT)
        if frame_count < 1:
            return False

        hash_size = min(len(self.hash[0]), len(other.hash[0]))
        if hash_size < 2:
            return False

        limit = max(int((1 - threshold / 100) * hash_size), 0) * frame_count

        count = 0
        for i in range(frame_count):
            count += count_nonzero(self.hash[i].hash != other.hash[i].hash)
        return count <= limit
    

    def __str__(self) -> str:
        return "|".join(str(h) for h in self.hash)
    

    @classmethod
    def from_str(cls, string: str) -> Self:
        if not string:
            return None
        return cls([hex_to_hash(h) for h in string.split("|")])
    

    @classmethod
    def from_file(cls, file: str | Path, precision: int, duration: float):
        file = Path(file)
        temp = Path(gettempdir())
        precision = max(2, precision >> 3)

        if cls._create_imgs(file, temp.joinpath(f"{file.stem}_%02d.png"), duration):
            printerr(f"    Failed to generate video hash: {file}")
            return None
        
        hashes = []
        for tmpfile in sorted(temp.glob(f"{file.stem}_*.png")):
            with Image.open(tmpfile) as img:
                hashes.append(average_hash(img))
            tmpfile.unlink()
        return cls(hashes)


    @classmethod
    def _create_imgs(cls, input: str, output: str, duration: float):
        cmd = [
            cls._FFMPEG_PATH,
            "-i", str(input),
            "-vf", f"fps={cls._VHASH_FCOUNT}/{duration}",
            str(output),
            "-v", cls._FFMPEG_LOG,
        ]
        return run(cmd).returncode
    


class AudioHasher(Hasher):
    """Calculate acoustic fingerprint of file"""

    hash: tuple[float, bytes]
    
    def matches(self, other: Self, threshold: float | int = None) -> bool:
        if type(self) is not type(other):
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
    def from_file(cls, file: str | Path, precision: int, *_) -> None:
        """
        Create a new hash object from a file
        - precision is how much of the file to use (x 4 sec)
        """
        return cls(fingerprint_file(file, precision * 4))

