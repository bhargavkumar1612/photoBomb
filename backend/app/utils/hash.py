"""
Utility functions for computing file hashes.
"""
import hashlib
from typing import BinaryIO


def compute_sha256(file_obj: BinaryIO) -> str:
    """
    Compute SHA256 hash of a file.
    
    Args:
        file_obj: File-like object opened in binary mode
    
    Returns:
        Hex-encoded SHA256 hash string
    """
    sha256_hash = hashlib.sha256()
    
    # Read in chunks to handle large files
    file_obj.seek(0)
    for byte_block in iter(lambda: file_obj.read(4096), b""):
        sha256_hash.update(byte_block)
    
    file_obj.seek(0)  # Reset file pointer
    return sha256_hash.hexdigest()


def compute_sha256_from_bytes(data: bytes) -> str:
    """
    Compute SHA256 hash of bytes.
    
    Args:
        data: Bytes to hash
    
    Returns:
        Hex-encoded SHA256 hash string
    """
    return hashlib.sha256(data).hexdigest()
