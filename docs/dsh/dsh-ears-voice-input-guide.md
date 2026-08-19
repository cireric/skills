# dsh + dsh-ears 语音输入上手指南

> 适用场景：想用口语/语音直接给 DeepSeek 下提示词，代替打字。  
> 参考来源：[deepseek-harness](https://github.com/deepseek-ai/deepseek-harness) · [dsh-ears](https://github.com/WizisCool/dsh-ears) · [V2EX 讨论帖](https://www.v2ex.com/t/1235546)  
> 文档生成日期：2026-08-19

---

## 0. 这是什么

**dsh（DeepSeek Harness）** 是 DeepSeek 官方开源的 agent harness，核心理念是「everything is a plugin」，基于 [Cordis](https://github.com/cordiverse/cordis) 框架构建。它提供一个 Web UI（默认 `http://127.0.0.1:3080`）作为主入口。

**dsh-ears** 是 dsh 的一个开源语音输入插件，口号是「给纯文本 DeepSeek 一对耳朵」。它把语音接入 dsh 的提示词输入流程：

```
麦克风 → 语音转写(ASR) → 可选 LLM 润色 → 可编辑草稿 → 手动发送
```

核心能力：

- **多 ASR 后端**：Web Speech（浏览器原生）、本地 Whisper、Groq、阿里云百炼、自定义 OpenAI 兼容接口。
- **LLM 润色**：转写后的文字常有口头禅、语气词、说错又纠正的内容，插件可调用 dsh 已接入的任意模型自动润色（去口头禅、修错字、整理口语），提示词可自定义。润色复用 dsh 自身的模型路由，**无需额外配 key**。
- **手动确认**：转写文本先进入输入框，编辑确认后再发送，避免误发。

> ⚠️ dsh 目前处于 **developer preview**，官方明确「会有破坏性变更」。dsh-ears 要求 dsh 版本 `0.1.0-rc.6` 或 `rc.7`，两端版本建议对齐。

---

## 1. 环境准备

| 项目      | 要求                         | 说明                                                    |
| ------- | -------------------------- | ----------------------------------------------------- |
| Node.js | `^22.19.0 \|\| >=24.0.0`   | 推荐 Node 22 LTS（如 22.22.x）。本地 Whisper 走 Python，无需 Node |
| 网络      | 可访问 npm / GitHub           | 使用云端 ASR 后端还需能访问对应 API（Groq / 阿里云）                    |
| 浏览器     | Chromium 内核（Chrome / Edge） | Web Speech 后端依赖浏览器原生识别                                |
| 麦克风     | 任意系统/浏览器可识别的麦              | 无特殊硬件要求，详见附录推荐                                        |

> Windows 用户直接用 Git Bash 或 PowerShell 跑下面的 `npx` 命令即可。  
> 本机若已装 Node 22.22.2（managed）可满足版本要求；若用系统 Node 请先确认 `node -v` ≥ 22.19。

---

## 2. 安装与启动 dsh（Web UI）

### 方式 A：npx 直接运行（推荐，最省事）

```sh
npx @deepseek-ai/dsh web
```

浏览器访问 **<http://127.0.0.1:3080>** 即为 dsh Web UI。

> 为避免每次拉到不兼容的新版本，建议固定版本（与 dsh-ears 对齐）：
>
> ```sh
> npx @deepseek-ai/dsh@0.1.0-rc.7 web
> ```

### 方式 B：从源码运行

```sh
git clone https://github.com/deepseek-ai/deepseek-harness.git
cd deepseek-harness
pnpm install
pnpm run build
pnpm dsh web
```

---

## 3. 安装 dsh-ears 插件

在**另一个终端**（或 dsh 启动前）执行：

```sh
npx @deepseek-ai/dsh plugin --profile web add dsh-ears
```

- `--profile web` 表示把插件装进 Web UI 的插件配置里。
- 执行后**刷新** <http://127.0.0.1:3080> 页面，输入框右侧会出现一个**麦克风图标**。

卸载：

```sh
npx @deepseek-ai/dsh plugin --profile web remove dsh-ears
```

> 从源码安装 dsh-ears 本地仓库时，用 `dsh plugin --profile web add "$PWD"`，之后需 `pnpm build` / `pnpm dev:watch`，移除需手动删。

---

## 4. 选择与配置 ASR 后端

在 dsh-ears 的**插件设置页**选择识别后端。各后端差异如下：

| 后端                | 是否需 Key  | 工作方式                                | 注意点                                                       |
| ----------------- | -------- | ----------------------------------- | --------------------------------------------------------- |
| **Web Speech**    | 否        | 浏览器实时识别，边说边出字                       | 需 Chromium 内核浏览器；音频可能经浏览器厂商处理                             |
| **本地 Whisper**    | 否（需本地算力） | 停止录音后由本机 `whisper` 转写               | 需在设置页下载模型权重（不随插件打包）；`medium` 及以上纯 CPU 很难在 120 秒内跑完，建议 GPU |
| **Groq**          | 是（免费）    | Host 把录音发 Groq Whisper API          | 在 groq.com 申请 key                                         |
| **阿里云百炼**         | 是（有免费额度） | DashScope 同步转写（Flash 系列）            | 需 HTTPS 源站、API key、模型名；**单次上限 300 秒**                     |
| **自定义 OpenAI 兼容** | 是        | POST 到指定 `/audio/transcriptions` 端点 | 填端点地址、API key、模型名                                         |

### 4.1 Groq（免费，最易上手）

1. 打开 <https://console.groq.com> ，注册/登录。
2. 进入 **API Keys** 页面，点击 Create Key 生成 API key。
3. 在 dsh-ears 设置页选 **Groq** 后端，填入该 key，保存。

### 4.2 阿里云百炼 / DashScope

1. 打开 <https://dashscope.console.aliyun.com> ，用阿里云账号登录并开通「百炼」模型服务。
2. 进入 **API key 管理**，创建并复制 DashScope API key（新用户有免费额度）。
3. 在 dsh-ears 设置页选 **阿里云百炼**，填入 API key 与模型名。
   - 模型名填写 DashScope 当前支持的语音识别（ASR）模型；项目文档示例为 Flash 系列语音模型，具体以百炼控制台为准。
   - 注意单次转写上限 **300 秒**，长段录音请分段。

### 4.3 本地 Whisper

- 在插件设置页选择 **本地 Whisper**，首次使用需在设置里下载模型权重。
- 若机器无 GPU，建议选 `tiny` / `base` / `small` 等小模型；`medium` 及以上纯 CPU 转写会很慢。

---

## 5. 配置「润色」（强烈推荐开启）

转写文本往往带口头禅、语气词、自我纠正，直接发出既浪费 token 也容易让模型误判。开启润色可显著改善质量。

配置步骤：

1. 在 **dsh 的模型设置**中选好一个已配置好的模型（插件会复用这里接入的 LLM，无需额外 key）。
2. 在 **dsh-ears 插件设置**中开启润色，可选用内置默认提示词，或自定义系统提示词（例如：去口头禅、修错字、把口语整理成清晰指令）。
3. 润色走 dsh 自身的模型路由，不消耗额外配置。

> 提示词示例（可自定义）：「请将下面的口语转写整理为清晰、简洁、可直接作为 AI 指令的中文文本，去除口头禅和重复表达，修正明显口误，但保留原意。」

---

## 6. 使用流程

1. 打开 <http://127.0.0.1:3080，确认麦克风图标已出现。>
2. 点击麦克风图标，或按快捷键 **`Ctrl+Shift+Space`** 开始录音；再次触发停止录音。
3. 录音停止后，ASR 后端转写文本，经（可选）润色后填入输入框。
4. **检查/编辑**草稿，确认无误后手动点击发送。

---

## 7. 麦克风选购建议（按价位）

dsh-ears 对麦克风**没有特殊硬件要求**——只要系统/浏览器能识别即可。选麦的唯一目标是：把干净人声送进电脑、尽量少带环境噪音（噪音会拖累 ASR 准确率、也浪费润色 token）。优先选**心形/超心形指向、抗噪、USB 即插即用**的型号。

| 价位   | 型号                           | 到手价            | 说明                           |
| ---- | ---------------------------- | -------------- | ---------------------------- |
| 入门尝鲜 | 罗技 H390 有线 USB 耳麦            | ~¥150          | 带 boom 麦、物理降噪、插上即用，语音输入抗噪首选  |
| 入门尝鲜 | Fifine K669B / K688 USB 电容麦  | ~¥130–200      | 桌面麦，心形指向性价比高；K688 带静音键       |
| 中端   | Jabra Evolve2 30 / 40 USB 耳麦 | ~¥400–600      | 嘈杂环境神器，商务降噪，ASR 抗噪极强         |
| 中端   | 铁三角 AT2020USB+               | ~¥700          | 经典入门电容麦，人声清晰通透               |
| 中端   | 雷蛇 Seiren X / Mini           | ~¥350–450      | 超心形、小巧桌面麦                    |
| 高端   | 舒尔 Shure MV7                 | ~¥1500         | 人声标杆，USB+XLR 双模、心形，语音输入/播客都佳 |
| 高端   | 罗德 Rode NT-USB Mini / NT-USB | ~¥900 / ~¥1200 | 温暖人声，桌面麦口碑好                  |
| 高端   | 森海塞尔 Profile USB             | ~¥900          | 新出桌面 USB 麦，操作直观              |

**不推荐**：

- **AirPods / 蓝牙耳机麦**做主力：蓝牙带宽压缩丢人声细节，云端识别准确率下降明显，仅适合安静环境临时用。
- **全指向电容麦**（如 Blue Yeti 默认模式）：易收环境噪音，语音输入要小心摆位。

**一句话建议**：先拿手头耳机麦试通流程；想长期舒服用 **Jabra Evolve2 30（耳麦抗噪）** 或 **Fifine K688（便宜桌面麦）**；预算一步到位直接 **Shure MV7**。

---

## 8. 常见问题 / 排错

| 现象                 | 可能原因                       | 处理                                      |
| ------------------ | -------------------------- | --------------------------------------- |
| 输入框旁没有麦克风图标        | 插件未装进 `web` profile，或页面未刷新 | 确认命令含 `--profile web`；刷新页面；重启 `dsh web` |
| 浏览器提示无麦克风权限        | 系统/浏览器未授权                  | 在浏览器地址栏允许麦克风；Windows 隐私设置里开启麦克风访问       |
| Web Speech 不工作     | 用的不是 Chromium 内核浏览器        | 改用 Chrome / Edge                        |
| 本地 Whisper 转写极慢/超时 | 纯 CPU 跑大模型                 | 换 `tiny/base/small` 模型，或上 GPU           |
| 百炼报超长错误            | 单次录音 > 300 秒               | 分段录音，每段控制在 300 秒内                       |
| Groq / 百炼 key 报错   | key 无效或额度用尽                | 重新生成 key；确认账号有可用额度                      |
| 插件/后端选项缺失          | dsh 与 dsh-ears 版本不匹配       | 两端对齐到 `0.1.0-rc.6` / `rc.7`             |

---

## 9. 版本与兼容性提醒

- dsh 处于 **developer preview**，官方声明「THERE WILL BE COMPATIBILITY-BREAKING CHANGES」。
- dsh-ears 当前要求 dsh `0.1.0-rc.6` 或 `rc.7`；建议用 `npx @deepseek-ai/dsh@0.1.0-rc.7 web` 固定版本，避免被新版本打断。
- 插件仓库更新频繁（2026-08 密集提交），新后端/新特性以 GitHub README 为准；遇到问题时优先查 [dsh-ears Issues](https://github.com/WizisCool/dsh-ears/issues)。

---

## 10. 快速命令清单（可直接复制）

```sh
# 1) 启动 dsh Web UI（固定版本，推荐）
npx @deepseek-ai/dsh@0.1.0-rc.7 web

# 2) 另一个终端：安装语音插件
npx @deepseek-ai/dsh plugin --profile web add dsh-ears

# 3) 浏览器打开并刷新
#    http://127.0.0.1:3080  → 出现麦克风图标

# 4) 在插件设置页选择 ASR 后端（Groq / 百炼等）并填 key
# 5) 在 dsh 模型设置选好润色用的模型，开启 dsh-ears 润色
# 6) Ctrl+Shift+Space 开始/停止录音 → 编辑 → 发送
```
