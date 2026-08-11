# FFmpeg Toolkit 使用指南

基于 FFmpeg 的视频处理工具，通过统一 CLI 完成格式转换、分辨率修改、压缩、裁剪、拼接、音频处理、GIF 制作、倍速、旋转/翻转和信息查看。**不直接拼 ffmpeg 命令**——CLI 负责参数校验、编码器选择和覆盖保护。

## 目录

- [环境要求与安装](#环境要求与安装)
- [快速上手](#快速上手)
- [全局选项](#全局选项)
- [命令参考](#命令参考)
  - [info — 信息查看](#1-info--信息查看)
  - [convert — 格式转换](#2-convert--格式转换)
  - [scale — 分辨率修改](#3-scale--分辨率修改)
  - [compress — 压缩/码率控制](#4-compress--压缩码率控制)
  - [trim — 裁剪片段](#5-trim--裁剪片段)
  - [concat — 拼接文件](#6-concat--拼接文件)
  - [audio — 音频操作](#7-audio--音频操作)
  - [gif — GIF 制作](#8-gif--gif-制作)
  - [speed — 倍速](#9-speed--倍速)
  - [rotate — 旋转](#10-rotate--旋转)
  - [flip — 翻转](#11-flip--翻转)
- [完整工作流示例](#完整工作流示例)
- [退出码](#退出码)
- [配置文件](#配置文件)
- [测试](#测试)
- [常见问题](#常见问题)

## 环境要求与安装

- 需要系统已安装 `ffmpeg` 和 `ffprobe`。检测：`which ffmpeg ffprobe`
- 未安装时按平台安装：
  - macOS：`brew install ffmpeg`
  - Linux：`apt install ffmpeg`（Debian/Ubuntu）或 `dnf install ffmpeg`（Fedora）
  - Windows：`winget install ffmpeg`
- 运行方式（在项目根目录）：

  ```bash
  .venv/bin/python skills/ffmpeg-toolkit/cli.py <操作> [选项] <输入...> [输出]
  ```

## 快速上手

```bash
# 查看视频信息
.venv/bin/python skills/ffmpeg-toolkit/cli.py info 视频.mp4

# 转成 MKV
.venv/bin/python skills/ffmpeg-toolkit/cli.py convert 视频.mp4 视频.mkv

# 缩放到 1080p 宽（保持宽高比）
.venv/bin/python skills/ffmpeg-toolkit/cli.py scale 视频.mp4 视频1080.mp4 --width 1920

# 压缩（CRF 28，体积明显减小）
.venv/bin/python skills/ffmpeg-toolkit/cli.py compress 视频.mp4 视频压缩.mp4 --crf 28

# 截取 1:30 开始的 30 秒
.venv/bin/python skills/ffmpeg-toolkit/cli.py trim 视频.mp4 片段.mp4 --start 00:01:30 --duration 00:00:30

# 转 GIF
.venv/bin/python skills/ffmpeg-toolkit/cli.py gif 视频.mp4 动画.gif --width 480 --fps 10
```

## 全局选项

以下选项所有子命令通用，可放在子命令**前或后**：

| 选项 | 说明 |
|------|------|
| `--overwrite` | 覆盖已存在的输出文件（默认拒绝覆盖） |
| `--verbose` | 打印实际执行的 ffmpeg 命令 |

```bash
# 两种写法等价
.venv/bin/python skills/ffmpeg-toolkit/cli.py --overwrite convert in.mp4 out.mp4
.venv/bin/python skills/ffmpeg-toolkit/cli.py convert in.mp4 out.mp4 --overwrite
```

## 命令参考

### 1. info — 信息查看

```bash
cli.py info <输入文件>
```

输出：时长、分辨率、视频编码、音频编码、文件大小。

```bash
$ cli.py info 视频.mp4
时长: 01:23
分辨率: 1920x1080
视频编码: h264
音频编码: aac
文件大小: 245.67 MB
```

### 2. convert — 格式转换

```bash
cli.py convert <输入> <输出> [--video-codec 编码器]
```

| 参数 | 说明 |
|------|------|
| `--video-codec` | 指定视频编码器（如 `libvpx-vp9`、`libx265`）；不指定时按输出容器自动选默认编码器 |

支持输出格式：`.mp4 .mkv .webm .mov .avi .m4v .ts`

```bash
cli.py convert 视频.mp4 视频.mkv
cli.py convert 视频.mp4 视频.webm --video-codec libvpx-vp9
```

### 3. scale — 分辨率修改

```bash
cli.py scale <输入> <输出> --width 宽 [--height 高] [--force]
```

| 参数 | 范围 | 说明 |
|------|------|------|
| `--width` | 16–7680 | 目标宽度（与 `--height` 至少一个） |
| `--height` | 16–4320 | 目标高度（与 `--width` 至少一个） |
| `--force` | — | 强制拉伸到指定宽高（必须同时给宽和高）；不加则保持宽高比 |

支持输出格式：`.mp4 .mkv .webm .mov`

```bash
cli.py scale in.mp4 out.mp4 --width 1920          # 宽 1920，高按比例自动（自动偶数对齐）
cli.py scale in.mp4 out.mp4 --height 720          # 高 720，宽按比例自动
cli.py scale in.mp4 out.mp4 --width 640 --height 480 --force   # 强制拉伸
```

### 4. compress — 压缩/码率控制

```bash
cli.py compress <输入> <输出> [--crf 数值] [--codec h264|h265|vp9]
```

| 参数 | 范围/取值 | 说明 |
|------|-----------|------|
| `--crf` | 0–51（默认 23） | 恒定质量因子：**越大越省体积、画质越低** |
| `--codec` | `h264`（默认）/ `h265` / `vp9` | 编码器 |

支持输出格式：`.mp4 .mkv .webm`

CRF 经验值（H.264）：23 ≈ 原质量；26–28 明显缩小、观感可接受；30+ 画质损失明显，适合存档不重要的内容。

```bash
cli.py compress in.mp4 out.mp4 --crf 28        # 默认 H.264
cli.py compress in.mp4 out.mp4 --crf 26 --codec h265   # H.265 同画质体积更小
```

### 5. trim — 裁剪片段

```bash
cli.py trim <输入> <输出> --start 时间 [--duration 时长 | --end 时间]
```

| 参数 | 说明 |
|------|------|
| `--start` | 起点（默认 0），格式 `HH:MM:SS` 或秒数 |
| `--duration` | 持续时长（与 `--end` 二选一） |
| `--end` | 终点（与 `--duration` 二选一；须大于 `--start`） |

支持输出格式：`.mp4 .mkv .webm .mov`。始终重编码，保证关键帧精确。

```bash
cli.py trim in.mp4 out.mp4 --start 00:01:30 --duration 00:00:30
cli.py trim in.mp4 out.mp4 --start 30 --end 60          # 秒数写法：30s 到 60s
cli.py trim in.mp4 out.mp4 --duration 10                # 开头 10 秒
```

### 6. concat — 拼接文件

```bash
cli.py concat <输出> <输入1> <输入2> [<输入3> ...] [--reencode]
```

注意：**输出文件名在前**。至少 2 个输入。

| 参数 | 说明 |
|------|------|
| `--reencode` | 统一重编码。默认流拷贝（`-c copy`，快且无损），要求各片编码/分辨率一致；不一致或失败时加此参数 |

支持输出格式：`.mp4 .mkv .webm .mov`

```bash
cli.py concat 合集.mp4 片1.mp4 片2.mp4              # 编码一致，流拷贝
cli.py concat 合集.mp4 片1.mp4 片2.mp4 --reencode   # 编码/分辨率不一致时
```

### 7. audio — 音频操作

```bash
cli.py audio <输入> <输出> --extract | --replace 音频文件 | --mute
```

三个模式**互斥**，必须选一个：

| 模式 | 说明 | 输出格式 |
|------|------|----------|
| `--extract` | 提取音轨（视频转音频） | `.mp3 .m4a .aac .wav .flac .ogg` |
| `--replace 音频文件` | 用指定音频替换原音轨 | `.mp4 .mkv .mov .webm` |
| `--mute` | 去除音轨（静音版） | `.mp4 .mkv .mov .webm` |

```bash
cli.py audio 视频.mp4 音频.mp3 --extract
cli.py audio 视频.mp4 换音轨版.mp4 --replace 新音频.wav
cli.py audio 视频.mp4 静音版.mp4 --mute
```

### 8. gif — GIF 制作

```bash
cli.py gif <输入> <输出.gif> [--width 宽] [--fps 帧率] [--start 时间] [--duration 时长]
```

| 参数 | 范围/默认 | 说明 |
|------|-----------|------|
| `--width` | 16–7680（默认 480） | GIF 宽度（高按比例） |
| `--fps` | 1–30（默认 10） | 帧率，越大越流畅、文件越大 |
| `--start` | 任意时间格式 | 起始时间（可选） |
| `--duration` | 任意时间格式 | 持续时长（可选） |

输出格式：仅 `.gif`。内部使用 palette 两遍法保证质量。

```bash
cli.py gif in.mp4 out.gif --width 480 --fps 10
cli.py gif in.mp4 out.gif --width 320 --fps 8 --start 5 --duration 3   # 5s 起的 3 秒片段
```

### 9. speed — 倍速

```bash
cli.py speed <输入> <输出> --factor 倍数
```

| 参数 | 范围 | 说明 |
|------|------|------|
| `--factor` | 0.25–4.0（必填） | >1 加速，<1 慢放 |

支持输出格式：`.mp4 .mkv .webm .mov`。视频与音频自动同步（>2 倍时音频自动拆 atempo 链，如 2.5 倍 = 2.0×1.25）。

```bash
cli.py speed in.mp4 out.mp4 --factor 2      # 2 倍速
cli.py speed in.mp4 out.mp4 --factor 0.5    # 0.5 倍慢放
```

### 10. rotate — 旋转

```bash
cli.py rotate <输入> <输出> --degrees 90|180|270
```

支持输出格式：`.mp4 .mkv .webm .mov`。90° 为顺时针。

```bash
cli.py rotate in.mp4 out.mp4 --degrees 90
```

### 11. flip — 翻转

```bash
cli.py flip <输入> <输出> [--horizontal] [--vertical]
```

至少选一个；两个都选则水平+垂直同时翻转。支持输出格式：`.mp4 .mkv .webm .mov`。

```bash
cli.py flip in.mp4 out.mp4 --horizontal     # 水平镜像
cli.py flip in.mp4 out.mp4 --vertical       # 上下翻转
```

## 完整工作流示例

把一段 1080p 长视频处理成「720p 的 30 秒片段 + GIF 封面」：

```bash
# 1. 先看源信息
cli.py info 原始视频.mp4

# 2. 截取 2:00 起的 30 秒
cli.py trim 原始视频.mp4 片段.mp4 --start 00:02:00 --duration 30

# 3. 缩放到 720p
cli.py scale 片段.mp4 片段720.mp4 --width 1280

# 4. 压缩成小体积存档版
cli.py compress 片段720.mp4 片段720压缩.mp4 --crf 26

# 5. 用前 3 秒做 GIF
cli.py gif 片段720.mp4 封面.gif --width 480 --fps 8 --duration 3
```

## 退出码

| 退出码 | 含义 | 处理建议 |
|--------|------|----------|
| `0` | 成功 | — |
| `1` | ffmpeg/ffprobe 执行失败 | 读 stderr 报错（如编码器不支持、源文件损坏），调整参数重试 |
| `2` | 参数/校验错误 | 读 stderr 提示（文件不存在、扩展名不支持、数值越界、缺必填参数），修正后重试 |

失败时注意检查输出目录是否留下了半成品文件，需要的话手动清理。

## 配置文件

`skills/ffmpeg-toolkit/config.json`（可编辑，改后立即生效）：

```json
{
  "default_crf": 23,
  "gif_default_width": 480,
  "gif_default_fps": 10,
  "overwrite": false
}
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `default_crf` | `23` | `compress` 不指定 `--crf` 时的默认值 |
| `gif_default_width` | `480` | `gif` 不指定 `--width` 时的默认值 |
| `gif_default_fps` | `10` | `gif` 不指定 `--fps` 时的默认值 |
| `overwrite` | `false` | 全局默认是否覆盖输出（命令行 `--overwrite` 优先） |

注意：各命令支持的输出格式白名单与数值范围是代码内硬约束，config.json 无法放宽。

## 测试

```bash
.venv/bin/python -m pytest skills/ffmpeg-toolkit/tests/ -v
```

测试使用 fake ffmpeg/ffprobe 二进制验证命令构建与参数校验逻辑，不依赖真实 ffmpeg，可在未安装 ffmpeg 的机器上运行。

## 常见问题

**Q: 输出文件已存在报错？**
A: 覆盖保护是故意行为。确认要覆盖就加 `--overwrite`。

**Q: 压缩后还是很大？**
A: 加大 `--crf`（如 30）；或换 `--codec h265`（同画质体积约为 H.264 的 60–70%）。

**Q: 拼接出来画面/声音对不上？**
A: 各片编码或分辨率不一致导致。加 `--reencode` 统一重编码。

**Q: 裁剪的时间点不准？**
A: 本工具始终重编码裁剪，精度为帧级。若还嫌不准，可尝试在源文件上先 `info` 确认时长后再定 `--start`/`--end`。

**Q: 想要的参数 CLI 不支持？**
A: 格式白名单与数值范围是刻意限制（防止误操作）。确需绕过时，用 `--verbose` 查看 CLI 实际生成的命令，以此为模板手动执行 ffmpeg。
