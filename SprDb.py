from dataclasses import dataclass, field
from typing import IO, Self
from ReadCstring import ReadStrFromFile
from pathlib import Path
from Farc import FarcArchive, FarcEntry
from collections.abc import Generator
import struct
import MurmurHash
from io import SEEK_END


@dataclass
class SprDbSet:
    file_name: str
    sprite: list[str] = field(default_factory=list)
    texture: list[str] = field(default_factory=list)

    @property
    def set_name(self) -> str:
        return Path(self.file_name).stem.upper()

    @property
    def sprite_suffix(self) -> str:
        return self.set_name

    @property
    def texture_suffix(self) -> str:
        name: str = self.set_name.split("_", maxsplit=1)[1]
        return f"SPRTEX_{name}"


@dataclass
class SprDb:
    _dict: dict[str, SprDbSet] = field(default_factory=dict)

    def updata(self, spr_db_set: SprDbSet) -> Self:
        self._dict[spr_db_set.set_name] = spr_db_set
        return self

    @property
    def sets(self) -> list[SprDbSet]:
        return list(self._dict.values())

    @property
    def sprites_count(self) -> int:
        count: int = 0
        for spr_db_set in self.sets:
            count += len(spr_db_set.sprite) 
            count += len(spr_db_set.texture)
        return count

    @property
    def sets_count(self) -> int:
        return len(self.sets)
    
def get_spr_db_set(file: IO[bytes], file_name: str) -> SprDbSet:
    file.seek(0x08)
    tex_conut: int = int.from_bytes(file.read(4), "little")
    spr_count: int = int.from_bytes(file.read(4), "little")

    file.seek(0x14)
    tex_offset: int = int.from_bytes(file.read(4), "little")
    spr_offset: int = int.from_bytes(file.read(4), "little")

    spr_db_set: SprDbSet = SprDbSet(file_name)

    for i in range(tex_conut): 
        file.seek(tex_offset + i * 4)
        tex_ptr = int.from_bytes(file.read(4), "little")
        spr_db_set.texture.append(ReadStrFromFile(file, tex_ptr))

    for i in range(spr_count): 
        file.seek(spr_offset + i * 4)
        spr_ptr = int.from_bytes(file.read(4), "little")
        spr_db_set.sprite.append(ReadStrFromFile(file, spr_ptr))

    return spr_db_set

def get_entry(_path: Path) -> Generator[tuple[str, IO[bytes]], None, None]:
    for farc_path in _path.glob("*.farc"): 
        farc = FarcArchive.read_from_file(farc_path)
        for entry in farc.entries:
            yield entry.file_name, farc.read_entry_data(entry)

def get_c_string(string: str) -> bytes:
    return string.encode("utf-8") + b"\x00"

def create_spr_db(_path: Path, output_db: Path) -> None:
    spr_db: SprDb = SprDb()

    for file_name, entry_data in get_entry(_path):
        spr_db_set: SprDbSet = get_spr_db_set(entry_data, file_name)
        spr_db.updata(spr_db_set)

    with output_db.open("w+b") as db_file:
        # 头部预留空白
        db_file.write(b"\x00" * 0x20)
        sprite_pts: int = db_file.tell() # 记录地址

        # 预留sprite空白数据区
        sprite_size: int = spr_db.sprites_count * 0x0c
        sprite_size += -sprite_size % 0x20
        db_file.write(b"\x00" * sprite_size)
        sprite_set_pts: int = db_file.tell() # 记录地址

        # 预留sprite_set空白数据区
        spriteset_size: int = (spr_db.sets_count) * 0x10
        spriteset_size += -spriteset_size % 0x20
        db_file.write(b"\x00" * spriteset_size)

        # 回填头部数据
        db_file.seek(0x00)
        db_file.write(struct.pack(
            "<IIII", 
            spr_db.sets_count,
            sprite_set_pts, 
            spr_db.sprites_count, 
            sprite_pts, 
            )
        )


        for set_index in range(len(spr_db.sets)):
            spr_set = spr_db.sets[set_index]

            # 先写sprite_set数据
            db_file.seek(0, SEEK_END)
            name_offset: int = db_file.tell()
            db_file.write(get_c_string(spr_set.set_name))

            file_name_offset = db_file.tell()
            db_file.write(get_c_string(spr_set.file_name))

            db_file.seek(sprite_set_pts)
            set_id: int = MurmurHash.calculate_str(spr_set.set_name)

            db_file.write(struct.pack(
                "<IIII", 
                set_id,
                name_offset, 
                file_name_offset,
                set_index
                )
            )
            sprite_set_pts = db_file.tell()

            # 再写sprite数据
            for spr_index in range(len(spr_set.sprite)):
                sprite = spr_set.sprite[spr_index]

                db_file.seek(0, SEEK_END)
                name_offset: int = db_file.tell()
                name_str = f"{spr_set.sprite_suffix}_{sprite}"
                db_file.write(get_c_string(name_str))

                db_file.seek(sprite_pts)
                spr_id: int = MurmurHash.calculate_str(name_str)

                db_file.write(struct.pack(
                    "<III", 
                    spr_id, 
                    name_offset, 
                    ((set_index | 0x0000) << 16) | spr_index)
                )
                sprite_pts = db_file.tell()

            # 最后写texture数据
            for tex_index in range(len(spr_set.texture)):
                texture = spr_set.texture[tex_index]

                db_file.seek(0, SEEK_END)
                name_offset: int = db_file.tell()

                name_str = f"{spr_set.texture_suffix}_{texture}"
                db_file.write(get_c_string(name_str))

                db_file.seek(sprite_pts)
                tex_id: int = MurmurHash.calculate_str(name_str)

                db_file.write(struct.pack(
                    "<III", 
                    tex_id, 
                    name_offset, 
                    ((set_index | 0x1000) << 16) | tex_index)
                )
                sprite_pts = db_file.tell()

        db_file.seek(0, SEEK_END)
        db_file.write(b"\x00" * (-db_file.tell() % 0x10))