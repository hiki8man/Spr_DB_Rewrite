from dataclasses import dataclass, field
from typing import IO, Self
from ReadCstring import ReadStrFromFile
from pathlib import Path
from Farc import FarcArchive, FarcEntry
from collections.abc import Generator
import struct


@dataclass
class SprNameList:
    Texture: list[str] = field(default_factory=list)
    Sprite: list[str] = field(default_factory=list)

@dataclass
class SprDbConut:
    Sprite: int = 0
    SpriteSet: int = 0

    def update_sprite(self, spr_name_list: SprNameList) -> None:
        self.Sprite += len(spr_name_list.Sprite) + len(spr_name_list.Texture)
        self.SpriteSet += 1

    @property
    def sprite_size(self) -> int:
        count: int = self.Sprite * 0x0C
        count += -count % 0x20
        return count

    @property
    def sprite_set_size(self) -> int:
        count: int = self.SpriteSet * 0x10
        count += -count % 0x20
        return count

    def get_head_data(self) -> bytes:
        return struct.pack(
            "<4I",
            self.SpriteSet,
            0x20,
            self.Sprite,
            0x20 + self.sprite_set_size
        )
def get_spr_name_list(file: IO[bytes]) -> SprNameList:
    file.seek(0x08)
    tex_conut: int = int.from_bytes(file.read(4), "little")
    spr_count: int = int.from_bytes(file.read(4), "little")
    file.seek(0x14)
    tex_offset: int = int.from_bytes(file.read(4), "little")
    spr_offset: int = int.from_bytes(file.read(4), "little")

    spr_name_list: SprNameList = SprNameList()

    for i in range(tex_conut): 
        file.seek(tex_offset + i * 4)
        tex_ptr = int.from_bytes(file.read(4), "little")
        spr_name_list.Texture.append(ReadStrFromFile(file, tex_ptr))

    for i in range(spr_count): 
        file.seek(spr_offset + i * 4)
        spr_ptr = int.from_bytes(file.read(4), "little")
        spr_name_list.Sprite.append(ReadStrFromFile(file, spr_ptr))

    return spr_name_list

def get_entry(_path: Path) -> Generator[tuple[str, IO[bytes]], None, None]:
    for farc_path in _path.glob("*.farc"): 
        farc = FarcArchive.read_from_file(farc_path)
        for entry in farc.entries:
            yield entry.file_name, farc.read_entry_data(entry)

def create_spr_db(_path: Path, output_db: Path) -> None:

    spr_entry_dict: dict[str, SprNameList] = {}
    spr_db_count: SprDbConut = SprDbConut()

    for file_name, entry_data in get_entry(_path):
        spr_name_list = get_spr_name_list(entry_data)
        spr_entry_dict[file_name] = spr_name_list
        spr_db_count.update_sprite(spr_name_list)

    with output_db.open("w+b") as db_file:
        # 写头部
        db_file.write(spr_db_count.get_head_data())
        db_file.write(struct.pack("<4I", 0, 0, 0, 0))
        sprite_offset: int = db_file.tell()

        # 预留sprite空白数据区
        db_file.write(b"\x00" * spr_db_count.sprite_size)
        sprite_set_offset: int = db_file.tell()

        # 预留sprite_set空白数据区
        db_file.write(b"\x00" * spr_db_count.sprite_set_size)
        string_offset: int = db_file.tell()

        # 正式写数据
        for file_name, spr_name_list in spr_entry_dict.items():
            
            ...