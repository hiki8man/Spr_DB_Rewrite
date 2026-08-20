import struct
import zlib
from dataclasses import dataclass
from enum import Enum, IntFlag
from io import BytesIO
from pathlib import Path
from typing import IO

import ReadCstring


def is_path(path: str|Path) -> bool:
    if isinstance(path, str):
        path = Path(path)

    if isinstance(path, Path):
        return path.is_file()

    raise TypeError("path must be a string or Path")

class FarcMagic(Enum):
    uncompress = b"FArc"
    compress   = b"FArC"
    aes        = b"FARC" # 暂不打算支持

class FarcFlags(IntFlag):
    # aes用，暂不打算支持
    none = 0 # 0000
    reserved = 1 << 0 # 0001
    compressed = 1 << 1 # 0010
    encrypted  = 1 << 2 # 0100

@dataclass
class FarcEntry:
    file_name: str
    start_offset: int
    compressed_size: int = 0
    original_size: int = 0
    
    @property
    def is_compressed(self) -> bool:
        return False

    @classmethod
    def read_entry(cls, stream: IO[bytes], offset: int = 0) -> tuple["FarcEntry", int]:
        name:str = ReadCstring.ReadStrFromFile(stream, offset)

        offset += len(name.encode("utf-8")) + 1
        stream.seek(offset)
        args:tuple[int, int] = struct.unpack(">II", stream.read(8))

        offset += 8

        return cls(name, args[0], 0, args[1]), offset

@dataclass
class CompressFarcEntry(FarcEntry):
    @property
    def is_compressed(self) -> bool:
        return True

    @classmethod
    def read_entry(cls, stream: IO[bytes], offset: int = 0) -> tuple["CompressFarcEntry", int]:
        name:str = ReadCstring.ReadStrFromFile(stream, offset)

        offset += len(name.encode("utf-8")) + 1
        stream.seek(offset)
        args:tuple[int, int, int] = struct.unpack(">III", stream.read(12))

        offset += 12

        return cls(name, *args), offset


@dataclass
class FarcArchive:
    magic: FarcMagic
    entries: list[FarcEntry]
    stream_data: IO[bytes]|Path
    alignment: int = 16

    @classmethod
    def read_from_file(cls, path: Path|str) -> "FarcArchive":
        if is_path(path) == False: 
            raise FileNotFoundError("文件不存在")
        
        path = Path(path)

        with path.open("rb") as file:
            archive = cls.read_from_stream(file)
        
        archive.stream_data = path
        return archive

    @classmethod
    def read_from_byte(cls, raw_data: bytes) -> "FarcArchive":
        if not isinstance(raw_data, bytes):
            raise TypeError("byte_data必须是bytes类型")
    
        stream = BytesIO(raw_data)
        return cls.read_from_stream(stream)

    @classmethod
    def read_from_stream(cls, stream: IO[bytes]) -> "FarcArchive":
        magic = struct.unpack(">4s", stream.read(4))[0]
        try:
            magic = FarcMagic(magic)
        except ValueError: 
            raise NotImplementedError("暂不支持此压缩格式")
        
        entry_size, alignment = struct.unpack(">II", stream.read(8))
        
        magic, entries = cls.__parse(stream, entry_size, magic)

        stream.seek(0)
        return cls(magic, entries, stream, alignment)

    @staticmethod
    def __parse(stream: IO[bytes], entry_size:int, magic:FarcMagic) -> tuple[FarcMagic, list[FarcEntry]]:
        full_size = entry_size + 8
        entries: list[FarcEntry] = []
        offset:int = 12

        while offset < full_size:
            head_end = full_size - offset
            if ReadCstring.isPadding(stream.read(head_end)):
                break
            
            stream.seek(offset)

            match magic:
                case FarcMagic.compress:
                    entry, offset = CompressFarcEntry.read_entry(stream, offset)
                case FarcMagic.uncompress:
                    entry, offset = FarcEntry.read_entry(stream, offset)
                case _:
                    raise ValueError(f"Invalid magic {magic}")

            entries.append(entry)

        return magic, entries

    def read_entry_data(self, entry: FarcEntry) -> IO[bytes]:
        if entry.is_compressed:
            size: int = entry.compressed_size  
        else:
            size: int = entry.original_size

        if isinstance(self.stream_data, Path):
            with self.stream_data.open("rb") as file:
                file.seek(entry.start_offset)
                data: bytes = file.read(size)
        else:
            self.stream_data.seek(entry.start_offset)
            data: bytes = self.stream_data.read(size)

        if entry.is_compressed:
            data = zlib.decompress(
                data,
                wbits=16 + zlib.MAX_WBITS,
                bufsize=entry.original_size,
            )
    
        return BytesIO(data)
if __name__ == "__main__":
    data = FarcArchive.read_from_file("spr_gam_cmn.farc")
