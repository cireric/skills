# ADR 0001: FFmpeg Toolkit 设计

Status: Accepted
Date: 2026-08-10

## 背景

用户需要一个可复用的 Skill，对本地视频做格式转换、分辨率修改等常见处理。
FFmpeg 是外部 CLI 工具（本机通过 Homebrew 安装），直接让 agent 拼 ffmpeg 命令
容易出错（编码器不支持、参数顺序、覆盖文件、宽高比失真等）。

## 决策

### 1. Python CLI 封装，而非纯 Markdown 指引

- 用 stdlib `subprocess` 封装 ffmpeg/ffprobe，提供受控子命令入口
- 参数白名单 + 数值范围校验硬编码在代码中（config.json 不承担安全约束）
- 可写 pytest 测试（fake ffmpeg 脚本 + monkeypatch 二进制路径），符合仓库惯例

被取代方案：纯 Markdown 指引（命令正确性全靠 agent 自觉，不可测试）。

### 2. 仅 stdlib，兼容 Python 3.9

仓库约定「仅 stdlib，除 pytest 外无 pip 依赖」。venv 实际为 Python 3.9.6，
代码不得使用 3.10+ 语法（无 `X | None`、无 `match`）。

### 3. 子命令设计

| 子命令 | 功能 | 关键参数 |
|--------|------|----------|
| `info` | ffprobe 元数据 | 无 |
| `convert` | 格式转换 | `--video-codec` |
| `scale` | 分辨率修改 | `--width` / `--height`（保持宽高比，`--force` 拉伸） |
| `compress` | 压缩/码率控制 | `--crf`、`--codec` |
| `trim` | 时间裁剪 | `--start`、`--duration` 或 `--end` |
| `concat` | 多文件拼接 | 默认重编码，`--copy` 流拷贝 |
| `audio` | 提取/替换/静音 | `--extract` / `--replace FILE` / `--mute`（互斥） |
| `gif` | GIF 制作 | `--width`、`--fps`、`--start`、`--duration`（palette 两遍法） |
| `speed` | 倍速 | `--factor` 0.25–4.0（setpts + atempo 链） |
| `rotate` | 旋转 | `--degrees` ∈ {90, 180, 270} |
| `flip` | 翻转 | `--horizontal` / `--vertical` |

### 4. 安全与错误处理

- 默认**不覆盖**已存在输出，需 `--overwrite`
- 输入文件必须存在；输出扩展名必须在该操作白名单内
- 不用 `shell=True`，参数以列表传递
- ffmpeg/ffprobe 非零退出 → 打印 stderr，退出码 1；参数校验失败 → 退出码 2
- 输出父目录不存在时自动创建
- ffmpeg/ffprobe 路径为模块级变量（默认 `shutil.which`），测试可 monkeypatch

## 后果

- 用户与 agent 都通过统一 CLI 入口操作，命令可预期、可测试
- 覆盖常用操作的白名单受控，agent 无法拼出破坏性命令
- 代价：比纯 Markdown 多一层封装，新增操作需改代码（有测试护航）
