# spr_db.bin 结构（KKdLib classic）

本文只描述 KKdLib 的 **classic** `spr_db.bin`：小端序、无 `SPDB` 容器。现代 `.spi` / `SPDB` 格式不是本文范围。

`spr_db.bin` 是 `spr.bin` 的索引目录。它不包含 TXP 像素、`SprInfo`、SpriteData 或 UV 数据；它只记录名字属于哪个 `spr.bin`，以及该名字在该文件的贴图表或 sprite 表中的下标。

## 文件布局

KKdLib classic 写入顺序如下：

```text
0x00  文件头占位区（0x20 字节）
0x20  Sprite 条目表（每条 0x0C 字节）
      补 00，对齐至 0x20
      Set 表（每条 0x10 字节）
      补 00，对齐至 0x20
      条目名字字符串：逐 Set，先 texture、后 sprite
      补 00，对齐至 0x04
      Set 字符串：逐 Set，先 name、再 file_name
      补 00，对齐至 0x04
文件尾 由外层写入流程补 00，对齐至 0x10
```

表的物理顺序是 **Sprite 条目表在前，Set 表在后**。

## 文件头

KKdLib 先写入 8 个 `0x90669066` 作为 `0x20` 字节占位，再在写完其他数据后回填前 16 字节。

| 偏移 | 类型 | KKdLib 字段名 | 含义 |
|---:|---|---|---|
| `0x00` | `u32` | `sprite_sets_count` | Set 数量 |
| `0x04` | `u32` | `sprite_sets_offset` | Set 表起始偏移 |
| `0x08` | `u32` | `sprites_count` | Sprite 条目总数（texture 和 sprite 都计入） |
| `0x0C` | `u32` | `sprites_offset` | Sprite 条目表起始偏移 |
| `0x10`–`0x1F` | 16 字节 | 未回填 | 保持初始占位值 |

所有 `offset` 都是相对于文件开头的绝对偏移。

## Set 表

Set 表从 `sprite_sets_offset` 开始。一个 Set 对应一个 `spr.bin`，每项 `0x10`（16）字节：

```text
+0x00  u32  id
+0x04  u32  name_offset
+0x08  u32  file_name_offset
+0x0C  u32  index
```

| 字段 | 含义 |
|---|---|
| `id` | Set 的预先计算好的 ID；KKdLib 直接写入 `i.id` |
| `name_offset` | Set 名称字符串的绝对偏移 |
| `file_name_offset` | `spr.bin` 文件名字符串的绝对偏移 |
| `index` | Set 编号；条目 `info` 中引用的就是该值 |

例如：

```text
index     = 0
name      = "face"
file_name = "face.bin"
```

`file_name` 是 `.bin`，不是承载它的 `.farc` 文件名。

## Sprite 条目表

Sprite 条目表从 `sprites_offset` 开始，每项 `0x0C`（12）字节：

```text
+0x00  u32  id
+0x04  u32  name_offset
+0x08  u32  info
```

| 字段 | 含义 |
|---|---|
| `id` | 条目的预先计算好的 ID；KKdLib 直接写入 `j.id` |
| `name_offset` | 条目名称字符串的绝对偏移 |
| `info` | `index`、Set 编号和 texture 标记的组合值 |

KKdLib 写入时按每个 Set 的顺序写条目，并且固定为：

```text
当前 Set 的全部 texture 条目
当前 Set 的全部 sprite 条目
下一个 Set
```

条目表自身的行号没有格式含义；真正引用 `spr.bin` 内部名字表位置的是 `info` 的低 16 位 `index`。

## info

`info` 是一个 `u32`：

```text
┌──────────────────── 高 16 位 ────────────────────┬──── 低 16 位 ────┐
│ bit 0–11：Set index；bit 12：texture 标记         │ spr.bin 表内 index │
└──────────────────────────────────────────────────┴──────────────────┘
```

KKdLib 的读取方式：

```text
index     = info 的低 16 位
set_index = info 高 16 位的低 12 位
texture   = info 高 16 位的第 12 位是否为 1
```

不使用位运算时，可理解为：

```python
# 写入前应保证 set_index 在 0～4095，index 在 0～65535
high = set_index + (4096 if texture else 0)
info = high * 65536 + index
```

| 条目类型 | `high` | `info` |
|---|---|---|
| sprite | `set_index` | `set_index * 65536 + index` |
| texture | `set_index + 4096` | `(set_index + 4096) * 65536 + index` |

其中 `4096`（`0x1000`）仅表示“该条目是 texture”。它不改变 Set 编号。

## 字符串区与去重

字符串区只保存文本；它不保存 `id`、`index`、`info` 或表的数量。

字符串均为以 `\0` 结尾的字符串。KKdLib 在整个文件范围内对相同字符串去重：同样的文本只写一次，多个 `name_offset` 可以指向同一个位置。

### 每个 Set 需要准备哪些字符串

一个 Set 对应一个 `spr.bin`。它需要两类 Set 字符串，以及该文件中每个 texture / sprite 各一条条目字符串：

| 字符串 | 被哪个字段引用 | 示例 |
|---|---|---|
| Set 名称 `name` | Set 表的 `name_offset` | `SPR_SEL_PV001` |
| 文件名 `file_name` | Set 表的 `file_name_offset` | `spr_sel_pv001.bin` |
| texture 名称 | texture 条目表的 `name_offset` | `SPRTEX_SEL_PV001_TEX_A` |
| sprite 名称 | sprite 条目表的 `name_offset` | `SPR_SEL_PV001_ICON` |

`name` 是数据库中识别 Set 的逻辑名称；`file_name` 是 FARC 内实际存在的 `.bin` 文件名。二者不是同一个值：

```text
name      = "SPR_SEL_PV001"
file_name = "spr_sel_pv001.bin"
```

KKdLib 不规定上述文本如何命名，只把调用者提供的字符串写入文件。若需兼容旧生成器，可由 `.bin` 文件名和 spr.bin 的原始名字按旧工具规则生成这些文本。

### “逐 Set，先 name、再 file_name”是什么意思

假设有两个 Set：

```text
Set 0:
  name      = "SPR_SEL_PV001"
  file_name = "spr_sel_pv001.bin"

Set 1:
  name      = "SPR_SEL_PV002"
  file_name = "spr_sel_pv002.bin"
```

字符串区的 Set 字符串部分按以下顺序写入：

```text
SPR_SEL_PV001\0
spr_sel_pv001.bin\0
SPR_SEL_PV002\0
spr_sel_pv002.bin\0
```

也就是每次处理一个 Set，连续写入它的 `name` 和 `file_name`，再处理下一个 Set。

### offset 如何得到

不需要预估字符串区大小。写每个字符串前，当前文件位置就是它的 offset：

```python
offset = file.tell()
file.write(text.encode("utf-8"))
file.write(b"\x00")
```

例如文件位置 `0x180` 写入了 `SPR_SEL_PV001\0`，则该 Set 表的 `name_offset` 应写入 `0x180`。

写入顺序严格为：

1. 遍历每个 Set，写入其 texture 名称；
2. 同一 Set 再写入其 sprite 名称；
3. 字符串区对齐至 `0x04`；
4. 再遍历每个 Set，写入 `name`，然后写入 `file_name`；
5. 再对齐至 `0x04`。

## 生成所需的 spr.bin 数据

对每个 `spr.bin`：

1. 分配一个 Set `index`；
2. 读取 texture 名字指针表，表下标就是 texture 条目的 `index`；
3. 读取 sprite 名字指针表，表下标就是 sprite 条目的 `index`；
4. 先添加 texture 条目，再添加 sprite 条目；
5. 将 Set 名称、文件名和所有条目名称写入字符串区。

生成数据库时不需要解析 TXP、`SprInfo`、SpriteData 或 UV 数据。
