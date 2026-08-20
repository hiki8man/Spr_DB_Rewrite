from enum import Enum


class CompressionMagic(Enum):
    gzip = b"\x1f\x8b"
    lzma = b'\x1f\xfb' # 有点复杂，暂不打算支持