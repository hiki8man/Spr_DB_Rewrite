基本上是旧的sprdb生成的重写版，让AI帮我整理了下MikuMikuLibrary和kkdlib的逻辑确保不会再出现不兼容工具的问题

需要注意的是，sprdb生成没有完全照搬kkdlib的规范

kkdlib的规范是：
- 写入Set条目
- - 写入Texture
- - 写入Sprite
- 0x04对齐
- 写入SpriteSet
- 0x04对齐

这个库的逻辑则是：
- 写入Set
- - 写入Texture
- - 写入Sprite
- - 写入SpriteSet
- 0x10对齐

考虑到字符串数据区不会影响解析，因此没有按照规范填写
