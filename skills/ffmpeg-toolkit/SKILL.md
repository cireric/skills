---
name: ffmpeg-toolkit
description: >
  视频处理工具箱——封装 ffmpeg/ffprobe，通过统一 CLI 完成格式转换、分辨率修改、压缩、裁剪/拼接、
  音频提取/替换/静音、GIF 制作、倍速、旋转/翻转和信息查看。
  用户说「把视频转成 mp4」「改分辨率」「压缩视频」「截取片段」「转 GIF」「提取音频」「加速/慢放」
  「旋转视频」「ffmpeg」「视频太大压一下」等需求时使用。
  通过 skills/ffmpeg-toolkit/cli.py 调用，不要直接拼 ffmpeg 命令。
---

# FFmpeg Toolkit 视频处理

你负责用本 skill 的 CLI 完成用户的视频处理需求。**禁止直接拼 ffmpeg/ffprobe 命令**——统一走 `cli.py`，
它负责参数校验、编码器选择、覆盖保护，命令可预期且经过测试。

## 环境要求

- 依赖系统安装 ffmpeg + ffprobe。检测：`which ffmpeg ffprobe`
- 未安装时：macOS 执行 `brew install ffmpeg`；Linux `apt install ffmpeg`；Windows `winget install ffmpeg`
- CLI 路径：`skills/ffmpeg-toolkit/cli.py`（从项目根目录运行）
- 运行方式：`.venv/bin/python skills/ffmpeg-toolkit/cli.py <operation> [options] <input...> [output]`

## 核心流程

1. **确认需求**：用户往往只给一句模糊需求（如「这个视频压一下」）。先问清关键参数：
   - 目标格式/分辨率/大小上限（压到多小）
   - 裁剪的起止时间
   - 倍速的方向和倍数
   - 输出文件名（无明确要求时：`<原名>_<操作>.<扩展名>`，放在输入同目录）
2. **看源文件**：不确定源文件信息（时长/分辨率/编码）时，先跑 `info` 再决定参数，避免瞎猜。
3. **执行操作**：按下表选子命令。全局 flag `--overwrite`（覆盖已存在输出）和 `--verbose`（打印完整命令）
   可放在子命令前或后。
4. **验证输出**：处理完跑 `info <输出文件>` 确认时长/分辨率符合预期；GIF/裁剪等看文件是否生成。

## 操作速查表

### 信息查看
```bash
python skills/ffmpeg-toolkit/cli.py info 视频.mp4
```
输出：时长、分辨率、视频编码、音频编码、文件大小。

### 格式转换
```bash
python skills/ffmpeg-toolkit/cli.py convert 输入.mp4 输出.mkv
python skills/ffmpeg-toolkit/cli.py convert 输入.mp4 输出.webm --video-codec libvpx-vp9
```
支持输出：.mp4 .mkv .webm .mov .avi .m4v .ts。默认由输出容器自动选编码器，`--video-codec` 可覆盖。

### 分辨率修改
```bash
python skills/ffmpeg-toolkit/cli.py scale 输入.mp4 输出.mp4 --width 1920      # 保持宽高比
python skills/ffmpeg-toolkit/cli.py scale 输入.mp4 输出.mp4 --height 720
python skills/ffmpeg-toolkit/cli.py scale 输入.mp4 输出.mp4 --width 640 --height 480 --force  # 强制拉伸
```
`--width`/`--height` 至少一个；默认保持宽高比（另一边自动 `-2` 保证偶数像素）。

### 压缩 / 码率控制
```bash
python skills/ffmpeg-toolkit/cli.py compress 输入.mp4 输出.mp4 --crf 28        # CRF 越大越省体积（0–51，默认 23）
python skills/ffmpeg-toolkit/cli.py compress 输入.mp4 输出.mp4 --codec h265    # h264 | h265 | vp9
```
经验：23 ≈ 原质量，28 明显缩小，32 以上可接受观感损失。

### 裁剪片段
```bash
python skills/ffmpeg-toolkit/cli.py trim 输入.mp4 输出.mp4 --start 00:01:30 --duration 00:00:30
python skills/ffmpeg-toolkit/cli.py trim 输入.mp4 输出.mp4 --start 30 --end 60     # 秒数亦可
```
时间格式：`HH:MM:SS` 或秒。`--duration` 与 `--end` 二选一。始终重编码保证关键帧精确。

### 拼接多个文件
```bash
python skills/ffmpeg-toolkit/cli.py concat 输出.mp4 片1.mp4 片2.mp4            # 输出在前
python skills/ffmpeg-toolkit/cli.py concat 输出.mp4 片1.mp4 片2.mp4 --reencode # 编码不一致时用
```
默认 `-c copy` 流拷贝（要求各片编码/分辨率一致）；不一致时加 `--reencode` 统一重编码。

### 音频操作
```bash
python skills/ffmpeg-toolkit/cli.py audio 视频.mp4 音频.mp3 --extract          # 提取音轨
python skills/ffmpeg-toolkit/cli.py audio 视频.mp4 换音轨.mp4 --replace 新音频.wav
python skills/ffmpeg-toolkit/cli.py audio 视频.mp4 静音.mp4 --mute             # 去音轨
```
三模式互斥。提取支持 .mp3 .m4a .aac .wav .flac .ogg；替换/静音输出 .mp4 .mkv .mov .webm。

### GIF 制作
```bash
python skills/ffmpeg-toolkit/cli.py gif 视频.mp4 动画.gif --width 480 --fps 10 --start 5 --duration 3
```
默认宽 480、10fps（config.json 可改）。内部用 palette 两遍法保证质量。

### 倍速
```bash
python skills/ffmpeg-toolkit/cli.py speed 输入.mp4 输出.mp4 --factor 2     # 2 倍速（0.25–4.0）
python skills/ffmpeg-toolkit/cli.py speed 输入.mp4 输出.mp4 --factor 0.5   # 0.5 倍慢放
```
视频 setpts + 音频 atempo 链自动同步，>2x 时自动拆链（如 2.5 → atempo=2.0,atempo=1.25）。

### 旋转 / 翻转
```bash
python skills/ffmpeg-toolkit/cli.py rotate 输入.mp4 输出.mp4 --degrees 90    # 90 | 180 | 270
python skills/ffmpeg-toolkit/cli.py flip 输入.mp4 输出.mp4 --horizontal      # 水平翻转
python skills/ffmpeg-toolkit/cli.py flip 输入.mp4 输出.mp4 --vertical        # 垂直翻转
```

## 行为约定（务必遵守）

- **覆盖保护**：输出已存在时默认拒绝（错误码 2），需要显式加 `--overwrite` 才覆盖。这是特性不是 bug。
- **退出码**：0 成功；1 ffmpeg/ffprobe 执行失败（stderr 已打印原因）；2 参数/校验错误（stderr 已打印原因）。
- **失败处理**：退出码非 0 时，读 stderr 定位原因（如编码器不支持、源文件损坏），调整参数重试；
  不要绕过 CLI 自己拼命令。若用户明确要 CLI 不支持的参数组合，告知并请求用户确认后直连 ffmpeg。
- **不要编造输出**：ffmpeg 失败时检查是否真的生成了输出文件；部分失败会留下半成品文件，应提示用户。

## 配置

`config.json`（skill 目录下，用户可编辑，运行期不可改）：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `default_crf` | `23` | compress 默认 CRF |
| `gif_default_width` | `480` | gif 默认宽度 |
| `gif_default_fps` | `10` | gif 默认帧率 |
| `overwrite` | `false` | 全局默认是否覆盖（CLI `--overwrite` 可覆盖此设置） |

注意：格式白名单与数值范围是代码内硬约束，config.json 无法放宽。

## 测试

```bash
.venv/bin/python -m pytest skills/ffmpeg-toolkit/tests/ -v
```
测试用 fake ffmpeg/ffprobe 二进制验证命令构建与校验逻辑，不依赖真实 ffmpeg。
