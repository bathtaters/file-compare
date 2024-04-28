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

    _FFMPEG_PATH = "ffmpeg"
    _FFMPEG_LOG = "fatal"

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
    

    def __hash__(self):
        """
        Override if self.hash is not hashable
        """
        return hash(self.hash)
    
    
    def __eq__(self, other: Self):
        """
        Equality test For plugin unit tests,
        can be overridden if there is a better way to calculate exact equality.
        """
        return str(self) == str(other)
    

    def __str__(self) -> str:
        raise NotImplementedError("str")
    

    @staticmethod
    def from_str(string: str):
        """Convert string into the assumed hasher"""
        if not string:
            return None
        if "|" in string:
            return VideoHasher.from_str(string)
        return AudioHasher.from_str(string)
    
    
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
    """Number of frames per video to compare"""
    
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
    

    def __hash__(self):
        return sum( hash(h) for h in self.hash )
    

    @classmethod
    def from_str(cls, string: str) -> Self:
        if not string:
            return None
        return cls([hex_to_hash(h) for h in string.split("|")])
    

    @classmethod
    def from_file(cls, file: str | Path, precision: int, duration: float):
        file, temp = Path(file), Path(gettempdir())
        precision = max(2, precision >> 3) # Match to Image precision

        if cls._create_imgs(file, temp.joinpath(f"{file.stem}_%02d.tif"), duration):
            printerr(f"    Failed to generate video hash: {file}")
            return None
        
        hashes = []
        for tmpfile in sorted(temp.glob(f"{file.stem}_*.tif")):
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

    hash: bytes

    _SEG_DURATION = 1.0
    """Number of seconds each segment should be"""
    _FP_CODEC = "pcm_s16le"
    """Codec to use for fingerprinting (s16le used by audioread.ffdec.FFMpeg)"""
    
    def matches(self, other: Self, threshold: float | int = None) -> bool:
        if type(self) is not type(other):
            return False
        count = compare_fingerprints((0, self.hash), (0, other.hash))
        # Using 275 to allow use of same threshold for image hashing
        return count * 275 >= threshold
    

    def __str__(self) -> str:
        return self.hash.decode()
    

    def __hash__(self):
        return hash(self.hash)


    @classmethod
    def from_str(cls, string: str) -> Self:
        if not string:
            return None
        return cls(string.encode())
    

    @classmethod
    def from_file(cls, file: str | Path, precision: int, duration: float):
        """
        Create a new hash object from a file
        - precision is how many segments of the file to make (precision / 2 = number of clips of _SEG_DURATION)
        - these are divided equally across the entire file using duration
        """
        file, tmpfile = Path(file), Path(gettempdir(), f"{file.stem}.wav")
        precision = max(precision >> 1, 4) # Match to Image precision

        if cls._segment_audio(file, tmpfile, duration, precision):
            printerr(f"    Failed to generate audio hash: {file}")
            return None
        
        fp = fingerprint_file(tmpfile, precision * cls._SEG_DURATION)[1]
        tmpfile.unlink()
        return cls(fp)


    @classmethod
    def _segment_audio(cls, input: str, output: str, duration: float, count: int):
        """Split a longer audio file into 'count' equally-spaced segments
        that are _SEG_DURATION long."""

        dis = duration / count
        segs = "+".join(
            f"between(t,{seg * dis},{seg * dis + cls._SEG_DURATION})"
            for seg in range(count)
        )

        cmd = [
            cls._FFMPEG_PATH,
            "-i", str(input),
            "-af", f"aselect='{segs}',asetpts=N/SR/TB",
            "-c", cls._FP_CODEC,
            str(output),
            "-v", cls._FFMPEG_LOG,
        ]
        return run(cmd).returncode