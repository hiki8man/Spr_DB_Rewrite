import logging
from typing import IO

logger = logging.getLogger("ReadCstring")

class PaddingDataError(Exception):
    def __init__(self, message) -> None:
        self.message = message

    def __str__(self) -> str:
        return self.message

def isPadding(data: bytes) -> bool:
    return len(set(data)) == 1

def isCorrupted(data: bytes) -> bool:
    return data.find(b"\x00") == -1
    
def CheckData(data: bytes) -> None:
    logger.debug("检测数据完整性")

    if isCorrupted(data):
        logger.debug("数据字符串不完整")
        raise ValueError("字符串数据不完整")
    
    logger.debug("数据完整性检测完成")

def ReadCstring(data: bytes) -> bytes:
    logger.debug("读取Cstring")

    CheckData(data)
    return data.split(b"\x00",1)[0]

def ReadCstringDict(data: bytes, encode:str ,startoffset: int = 0) -> dict[int,str]:
    CstringDict = {}
    data = data[startoffset:]
    offset = 0
    lenght = len(data)
    while offset < lenght:

        if isPadding(data[offset:]):
            logger.debug("读取到填充数据，不再读取后续内容")
            break

        bytestring = ReadCstring(data[offset:])
        logger.debug(f"读取到的值 {bytestring}")

        address = startoffset + offset
        logger.debug(f"{address}地址对应的字符串{bytestring}")
        CstringDict[address] = bytestring.decode(encode)
        offset += len(bytestring) + 1

    return CstringDict

def ReadDictFromFile(file: IO[bytes], offset:int = 0, encode:str = "UTF-8"):
    file.seek(offset)
    CstringDict = ReadCstringDict(file.read(), encode)
    if offset != 0:
        return {key + offset: value for key, value in CstringDict.items()}
    else:
        return CstringDict

def ReadStrFromFile(file: IO[bytes], offset:int = 0, encode:str = "UTF-8") -> str:

    file.seek(offset)
    string = b""
    while True:
        string_char = file.read(1)
        if not string_char or string_char == b"\x00":
            break # 读取到末尾没有数据
        else:
            string += string_char

    return string.decode(encode)
        