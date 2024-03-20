from typing import Self
from pathlib import Path
from videohash import VideoHash
from imagehash import ImageHash, hex_to_hash, average_hash
from PIL import Image
from numpy import count_nonzero


class Hasher(ImageHash):
    """Calculate perceptual hash of media file"""

    @classmethod
    def from_file(cls, filepath: str | Path, is_video=False, hash_size=64):
        """
        Hash the given file, if is_video if False will be treated an image.
        If is_video is True, hash_size will be forced to be 64.
        """
        if is_video:
            vhash = VideoHash(Path(filepath).as_posix()).hash_hex[2:]
            return cls(hex_to_hash(vhash).hash)
        with Image.open(filepath) as img:
            return cls(average_hash(img, hash_size).hash)
    
    @classmethod
    def from_hex(cls, hash_hex: str | ImageHash):
        """Create a hash instance from another instance's string"""
        return cls(hex_to_hash(str(hash_hex)).hash)
        
    def matches(self: Self, other: Self, threshold=100):
        """
        Test if this hashes match another hash
        - threshold is how close of a match they are in percentage (100% = exact)
        """
        if len(self) != len(other):
            raise ValueError("Perceptual hash array size mismatch.", len(self), len(other))
        
        limit = max(int((1 - threshold / 100) * len(self)), 0)
        return count_nonzero(self.hash != other.hash) <= limit

