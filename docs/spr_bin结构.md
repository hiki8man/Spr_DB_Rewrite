# spr.bin 结构（KKdLib classic）

本文描述 KKdLib 的 **classic** `spr.bin`：小端序、无 `SPRC` 外层容器。MM+ 等现代格式可能需要先处理外层 `SPRC`，不适用本文。

`spr.bin` 保存一个 Sprite Set：

- texture 名字表；
- sprite 名字表；
- sprite 的 UV、尺寸和位置数据；
- 内嵌 TXP 贴图数据。

生成 `spr_db.bin` 时，通常只需要读取两个名字表；不需要读取 `SprInfo`、`SpriteData` 或 TXP 像素。

## 文件整体布局

KKdLib classic 的写入顺序如下：

```text
0x00  头部（0x20 / 32 字节）
      sprite 名字指针表（S × 4 字节）
      补 00，对齐至 0x20
      SprInfo 表（S × 40 字节）
      补 00，对齐至 0x20
      texture 名字指针表（T × 4 字节）
      补 00，对齐至 0x20
      SpriteData 表（S × 8 字节）
      补 00，对齐至 0x20
      sprite 名字字符串
      补 00，对齐至 0x04
      texture 名字字符串
      补 00，对齐至 0x04
texofs 内嵌 TXP 数据
```

其中：

```text
T = texture 数量
S = sprite 数量
```

> 名字表本身是 `u32` 指针表，不是连续字符串表。

## 头部

头部固定 32 字节：

| 偏移 | 类型 | KKdLib 字段名 | 含义 |
|---:|---|---|---|
| `0x00` | `u32` | `flag` | Sprite Set 标记 |
| `0x04` | `u32` | `texofs` | 内嵌 TXP 数据起始偏移 |
| `0x08` | `u32` | `num_of_texture` | texture 数量 `T` |
| `0x0C` | `u32` | `num_of_sprite` | sprite 数量 `S` |
| `0x10` | `u32` | `sprinfo_offset` | SprInfo 表起始偏移 |
| `0x14` | `u32` | `texname_offset` | texture 名字指针表起始偏移 |
| `0x18` | `u32` | `sprname_offset` | sprite 名字指针表起始偏移 |
| `0x1C` | `u32` | `sprdata_offset` | SpriteData 表起始偏移 |

所有偏移均是相对于 `spr.bin` 文件开头的绝对偏移。

## texture 与 sprite 名字表

这两张表的结构相同：每项是一个 `u32`，其值是对应字符串的绝对偏移。

```text
名字指针表

+0x00  u32  第 0 个名字字符串的偏移
+0x04  u32  第 1 个名字字符串的偏移
+0x08  u32  第 2 个名字字符串的偏移
...
```

正确的读取方式：

```python
file.seek(table_offset + index * 4)
name_offset = int.from_bytes(file.read(4), "little")
name = ReadStrFromFile(file, name_offset)
```

不能这样读：

```python
# 错误：名字表不是连续字符串
file.seek(table_offset)
name = ReadStrFromFile(file)
```

### 对生成 spr_db.bin 的意义

`spr_db` 条目的 `index` 就是该名字在对应指针表中的下标：

```text
texture 指针表第 0 项 → texture 条目的 index = 0
texture 指针表第 1 项 → texture 条目的 index = 1

sprite 指针表第 0 项  → sprite 条目的 index = 0
sprite 指针表第 1 项  → sprite 条目的 index = 1
```

texture 与 sprite 使用独立的名字表，因此二者都可以有 `index = 0`。

## SprInfo 表

SprInfo 表从 `sprinfo_offset` 开始，每个 sprite 一项，固定 40 字节：

```text
+0x00  u32    texid
+0x04  i32    rotate
+0x08  float  su
+0x0C  float  sv
+0x10  float  eu
+0x14  float  ev
+0x18  float  px
+0x1C  float  py
+0x20  float  width
+0x24  float  height
```

| 字段 | 含义 |
|---|---|
| `texid` | 此 sprite 使用的 texture 下标 |
| `rotate` | 旋转标记 |
| `su`, `sv`, `eu`, `ev` | UV 矩形范围 |
| `px`, `py` | sprite 位置 |
| `width`, `height` | sprite 尺寸 |

生成 `spr_db.bin` 时不需要读取此表。

## SpriteData 表

SpriteData 表从 `sprdata_offset` 开始，每个 sprite 一项，固定 8 字节：

```text
+0x00  u32  attr
+0x04  u32  resolution_mode
```

生成 `spr_db.bin` 时不需要读取此表。

## TXP 数据

`texofs` 指向内嵌 TXP 数据的开头。TXP 保存实际贴图像素和格式信息。

生成 `spr_db.bin` 时不需要解析 TXP；只需读取头部的两个数量和两个名字指针表：

```text
0x08  texture 数量
0x0C  sprite 数量
0x14  texture 名字表偏移
0x18  sprite 名字表偏移
```

## 生成 spr_db 时的最小读取流程

```python
file.seek(0x08)
texture_count = int.from_bytes(file.read(4), "little")
sprite_count = int.from_bytes(file.read(4), "little")

file.seek(0x14)
texture_table_offset = int.from_bytes(file.read(4), "little")
sprite_table_offset = int.from_bytes(file.read(4), "little")

for index in range(texture_count):
    file.seek(texture_table_offset + index * 4)
    name_offset = int.from_bytes(file.read(4), "little")
    texture_name = ReadStrFromFile(file, name_offset)

for index in range(sprite_count):
    file.seek(sprite_table_offset + index * 4)
    name_offset = int.from_bytes(file.read(4), "little")
    sprite_name = ReadStrFromFile(file, name_offset)
```

`index` 必须保留循环中的原始下标；不要因为字符串重复、排序或命名加工而重新编号。
