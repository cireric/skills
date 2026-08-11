# Skill Observation Log

Observations captured during task-oriented work.

**Status key:** OPEN = not yet actioned | ACTIONED (YYYY-MM-DD) = skill updated/created | DECLINED (YYYY-MM-DD) = user decided not to pursue — resolved statuses always carry their resolution date

---

### Observation 3: 对 direct-file URL(裸 mp4 链接而非站点页面),yt-dlp 泛型 extractor 不填充 duration/resolution,in

**Status:** ACTIONED (2026-08-11) — Applied to video-download SKILL.md core workflow step 2 (in-session correction, verified in iteration-2 eval)
**Date:** 2026-08-11
**Session context:** video-download skill 创建与 eval:iteration-1 的 eval-2 用 direct-file URL 查元数据
**Skill:** video-download
**Type:** internal
**Phase/Area:** cli.py info/formats 子命令 + SKILL.md 核心流程

**Issue:** 对 direct-file URL(裸 mp4 链接而非站点页面),yt-dlp 泛型 extractor 不填充 duration/resolution,info/formats 输出只有标题和格式数量;iteration-1 的 with_skill agent 被迫自行用 ffprobe 补充

**Suggested improvement:** SKILL.md 核心流程步骤 2 已加说明:direct-file URL 元数据稀疏时用 ffprobe 或 ffmpeg-toolkit 的 info 补充;iteration-2 验证修复生效

**Principle:** 工具封装型 skill 应显式文档化其底层工具在边缘输入(泛型 URL)下的元数据局限,而非假设字段永远完整

**Reference file:** video-download-workspace/iteration-1/eval-2-metadata-report/with_skill/run-1/outputs/metadata-report.md

### Observation 4: 因为技能 CLI 物理存在于共享工作区(仓库内 skills/ 目录),baseline(无技能)agent 自己发现了 skills/video-downlo

**Status:** OPEN
**Date:** 2026-08-11
**Session context:** video-download skill eval 方法论:iteration-2 baseline 被污染
**Skill:** skill-creator
**Type:** internal
**Phase/Area:** eval 设计与评分

**Issue:** 因为技能 CLI 物理存在于共享工作区(仓库内 skills/ 目录),baseline(无技能)agent 自己发现了 skills/video-download/cli.py 并直接使用,iteration-2 的 without_skill 与 with_skill 产出完全相同(连 mp3 都是 20035B),对比失去区分度

**Suggested improvement:** 对工具封装型 skill,若 CLI 在仓库内,with/without eval 需把 baseline 隔离到不含该 CLI 的副本工作区,或改用行为级断言(是否手拼命令/是否验证输出),仅结果导向断言无法区分

**Principle:** 评估工具封装型 skill 时,共享工作区本身就是基线污染源;结果导向断言对'已知工具的封装'无区分度,行为级断言或工作区隔离才有意义

### Observation 5: 真实站点被 Cloudflare 反爬拦截,CLI 无 --extractor-args/--add-header/impe

**Status:** ACTIONED (2026-08-11) — Applied to video-download cli.py (--impersonate + VIDEO_DOWNLOAD_YTDLP_BIN) and SKILL.md/USAGE.md error table (weekly review)
**Date:** 2026-08-11
**Session context:** video-download 技能真实使用:下载流媒体视频被 Cloudflare 拦截
**Skill:** video-download
**Type:** internal
**Phase/Area:** cli.py download 子命令 + SKILL.md 错误处理表

**Issue:** 真实站点被 Cloudflare 反爬拦截,CLI 无 --extractor-args/--add-header/impersonation 支持;按 SKILL.md 错误表加 --cookies-from-browser 无效,因为 cf_clearance 绑定 TLS 指纹,curl 即使带 cookies 也 403;最终靠 venv 装 yt-dlp[curl-cffi] + --extractor-args generic:impersonate + 浏览器 cookies 才提取到 m3u8

**Suggested improvement:** 给 cli.py 加 --impersonate 开关(映射 --extractor-args generic:impersonate)和 --add-header 透传;SKILL.md 错误表 403 行补充:先试 cookies,仍 403 则需 impersonation(curl_cffi)或 playwright 提取直链

**Principle:** 现代反爬(Cloudflare)是分层防御:header 检查→cookie 挑战→TLS 指纹;工具封装 skill 必须把'指纹伪造'能力纳入 CLI,否则真实站点场景必然失败,且错误表要写全升级路径而非只写第一层解法
