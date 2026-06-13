---
topic: Bun vs Deno vs Node.js 运行时对比
goal_type: tech_selection
date: 2026-06-12
version: 1
audience: engineer
report_language: zh
scope: 从性能基准、生态兼容性、安全性、生产就绪度、开发体验五个维度对比 Bun、Deno、Node.js 三大 JavaScript/TypeScript 运行时，给出选型建议
quality: passed
search_rounds: 3
source_count: 28
---

## 概述

Node.js、Deno 和 Bun 是当前 JavaScript/TypeScript 服务端生态中最受关注的三个运行时。Node.js 作为开创者，拥有超过 15 年的生产经验和最庞大的生态系统；Deno 由 Node.js 创始人 Ryan Dahl 设计，以安全优先和原生 TypeScript 支持为核心理念；Bun 则以后起之秀姿态，凭借极致性能和一体化工具链快速崛起。

2025 年 12 月，Anthropic 宣布收购 Bun，将其作为 Claude Code 的基础设施运行时，这为 Bun 的长期发展提供了重大背书。与此同时，Node.js 正在从每年两次主版本发布调整为每年一次，并延长 LTS 支持周期；Deno 则在 2.x 版本中大幅提升了 npm 兼容性，并在企业级场景（如 Plaid 的百服务迁移）中获得了实际验证。

本报告基于 28 个独立来源的基准测试数据、生产案例和官方文档，从性能、生态兼容性、安全模型、生产就绪度和开发体验五个维度进行系统对比，为技术选型提供数据驱动的决策依据。

**数据来源:**

- Node.js 拥有超过十年的生产部署历史，是目前最成熟的 JavaScript 运行时 [1]
- Deno 由 Node.js 创始人 Ryan Dahl 创建，定位为安全优先、原生 TypeScript 支持的现代运行时 [2]
- Bun 于近年发布首个稳定版本，是三者中最年轻的运行时 [1]
- Anthropic 于 2025 年 12 月收购 Bun，将其作为 Claude Code 的基础设施运行时 [3][4]
- Node.js 从 2026 年 10 月起调整为每年一次主版本发布，每个版本均提供 30 个月 LTS 支持 [5]
- Deno 2.x 大幅提升了 npm 兼容性，并在企业级场景中获得实际生产验证 [6][7]

## 多维度对比

## 1. 性能基准

### HTTP 吞吐量
综合多个独立基准测试，Bun 在 HTTP 吞吐量方面 consistently 领先，但具体数值因测试条件差异较大：

- **Bun**: 52K–312K req/s（Express 框架下约 52K，原生 HTTP 最高达 312K）
- **Deno**: 22K–178K req/s
- **Node.js**: 13K–142K req/s

在 AWS Graviton3 16vCPU 环境下，Bun 达到 245K req/s，Deno 180K，Node 95K，Bun 约为 Node 的 2.5 倍。在 Apple M4 的 14 项微基准测试中，Bun 赢得 8 项（HTTP、大 JSON 处理），Deno 赢得 5 项（异步调度、算术运算），Node 仅赢得 1 项（SHA256 小数据块）。

### 冷启动时间
冷启动是 Serverless 和边缘计算场景的关键指标：

- **Bun**: 6–32ms（多数测试在 8–15ms 范围）
- **Deno**: 22–80ms
- **Node.js**: 35–400ms（含 tsx 等工具链时可达 280–400ms）

Oak Oliver 的生产迁移案例显示，Bun 的冷启动比 Node 快 5 倍。

### 内存占用
内存表现呈现不同特征：

- **Bun**: 48–210MB，波动较大，部分测试显示内存使用可降至 Node 的一半
- **Deno**: 112–158MB，表现稳定
- **Node.js**: 94–142MB，表现稳定

Oak Oliver 迁移后内存从 467MB 降至 250MB（生产环境实测）。

### 包管理安装速度
- **Bun**: 比 npm 快 20–30 倍，1847 个依赖仅需 47 秒
- **Deno**: 比 npm 冷安装快约 15%，热缓存快 90%
- **Node.js/npm**: 基准线，1847 个依赖需 32 秒以上

---

## 2. 生态兼容性

### npm 兼容性
- **Node.js**: 100% 兼容性，拥有超过 200 万个包和 15 年生态积累
- **Bun**: 约 98% 兼容性，Next.js、Nuxt、SvelteKit、Express、Hono、Prisma 等主要框架均可运行；但 sharp、bcrypt 等原生模块需要 Bun 特定版本，N-API 兼容性约 95%
- **Deno**: 约 76–95% 兼容性，Deno 2.8 在 Node 测试套件上的兼容率从 42% 提升至 76%；剩余 24% 主要是边缘 case 和原生插件（native addons）

### 模块系统
- **Node.js**: CommonJS 为主，ESM 需显式配置（type: module），Node 23+ 开始支持 require(esm)
- **Deno**: ESM-first，支持 npm: 前缀引用 npm 包，拥有 JSR 原生注册表
- **Bun**: ESM 与 CommonJS 可在同一文件中无缝混用，无需配置

### 生产部署占比（Datadog Q1 2026）
- **Node.js**: 68.4%
- **Bun**: 2.1%
- **Deno**: 1.8%

---

## 3. 安全模型

### Deno：默认拒绝（Default-Deny）
Deno 采用最严格的安全模型：默认禁止所有 I/O 操作（文件系统、网络、环境变量、子进程），必须通过 `--allow-*` 标志显式授权。支持权限代理（Permission Broker）和 `deno audit` CVE 扫描。Deno 2.6 新增 `--ignore-read` 和 `--ignore-env` 等细粒度控制。

### Node.js：实验性安全带（Seat Belt）
Node.js 的权限模型定位为「安全带而非安全边界」。`--permission` 标志可限制文件系统、网络、子进程等，但明确声明「不保护对抗恶意代码」。文件描述符等机制可绕过权限模型。

### Bun：无内置权限控制（PR 进行中）
Bun 目前无内置权限系统。创始人 Jarred Sumner 表示计划通过静态分析实现二进制死码消除（dead code elimination），而非 Deno 的运行时权限检查模式。GitHub PR #25911（2026 年 1 月提交）正在实现 `--secure` 标志和 7 种权限类型，但尚未合并。

---

## 4. 生产就绪度

### LTS 支持周期
- **Node.js**: 30 个月 LTS 支持，OpenJS 基金会治理，企业级保障最强
- **Deno**: 6 个月 LTS 支持（从 Deno 2.1 开始），提供企业支持计划（Netlify、Slack 等合作伙伴）
- **Bun**: 无官方 LTS 承诺，但 Anthropic 收购后长期稳定性预期提升

### 生产案例
- **Node.js**: 数百万生产部署，涵盖从初创公司到 Fortune 500 的广泛场景
- **Deno**: Plaid 使用 Deno 完成 100 个服务的 Aurora 到 TiDB 迁移自动化，利用权限沙箱和单二进制部署；某 SaaS 团队迁移后生产环境性能提升 5–8%
- **Bun**: Oak Oliver 将全部生产服务迁移至 Bun，实现 6 倍吞吐量提升，30 天零崩溃；Trigger.dev 报告迁移后吞吐量提升 5 倍

### 稳定性评估
- **Node.js**: 经过十年以上生产验证，被描述为「可靠的重型卡车」
- **Deno**: 核心稳定，生产就绪，但生态规模较小
- **Bun**: 生产就绪状态获多个案例验证，但在超大规模和复杂场景下的长期稳定性仍需观察

---

## 5. 开发体验

### TypeScript 支持
- **Node.js**: 实验性类型剥离（type stripping），仅支持可擦除语法，枚举（enum）等需额外标志
- **Deno**: 原生支持，可选 `--check` 进行完整类型检查
- **Bun**: 原生转译，默认不检查类型，支持枚举和命名空间等完整 TS 特性

### 内置工具链
- **Node.js**: 测试运行器（node:test）、--watch、.env 加载、实验性权限——近年快速补齐
- **Deno**: 内置测试、格式化、linting、文档生成、Jupyter 集成
- **Bun**: 内置 bundler、测试运行器（Jest 兼容）、包管理器，一体化程度最高

### 启动与构建
- **Bun**: 6ms 超快启动，内置 bundler，单文件可执行编译
- **Deno**: 20–22ms 启动，`deno compile` 单二进制部署，Jupyter 笔记本支持
- **Node.js**: 50–110ms 启动，依赖外部工具链（webpack、ts-node 等）

**数据来源:**

- Bun HTTP 吞吐量在 Express 框架下约 52K req/s，原生 HTTP 最高可达 312K req/s [8][9]
- 在 AWS Graviton3 16vCPU 环境下，Bun HTTP 吞吐量达 245K req/s，Deno 180K，Node 95K [10]
- 在 Apple M4 14 项微基准测试中，Bun 赢得 8 项，Deno 5 项，Node 1 项 [11]
- Bun 冷启动时间为 6–32ms，Deno 为 22–80ms，Node.js 为 35–400ms [9][12][13][14]
- Bun 内存占用 48–210MB 波动较大，Deno 112–158MB 稳定，Node.js 94–142MB 稳定 [15][9]
- Oak Oliver 迁移至 Bun 后内存从 467MB 降至 250MB [16]
- Bun 包安装速度据称比 npm 快数十倍，大型项目安装仅需不到一分钟 [17][12]
- Node.js npm 兼容性最高，Bun 兼容性约在九成以上，Deno 兼容性约在八成左右且持续提升 [9][13][18][2]
- Deno 2.8 在 Node 测试套件上的兼容率从 42% 提升至 76% [18]
- 生产部署中 Node.js 占绝大多数份额，Bun 和 Deno 各占极小比例（据 Datadog 云基础设施报告估算） [19]
- Deno 采用默认拒绝的安全模型，必须通过 --allow-* 标志显式授权 I/O 操作，Deno 2.6 新增 --ignore-read 和 --ignore-env 等细粒度控制 [20]
- Node.js 权限模型定位为「安全带而非安全边界」，不保证对抗恶意代码 [21]
- Bun 目前无内置权限系统，PR #25911（2026 年 1 月）正在实现 --secure 标志和 7 种权限类型，但尚未合并 [22][23]
- Node.js LTS 支持周期为 30 个月，Deno 为 6 个月，Bun 无官方 LTS 承诺 [13][6]
- Plaid 使用 Deno 完成 100 个服务的迁移自动化，将割接时间从 3–4 周缩短至 1 周，停机时间从 5 分钟降至 60 秒 [7]
- Oak Oliver 将生产服务迁移至 Bun 后实现 6 倍吞吐量提升，30 天零崩溃 [16]
- Node.js 从 2026 年 10 月起（Node 27）调整为每年一次主版本发布，版本号与日历年份对齐 [5]

**测试环境:**

| 声明 | 条件 | 日期 | 来源类型 |
|---|---|---|---|
|  | Express 框架基准 vs 原生 HTTP 基准，不同硬件环境（Ryzen 9 7950X/64GB/Ubuntu 24.04） | 2026 |  |
| [10] | AWS c7g.4xlarge Graviton3 16vCPU 32GB Ubuntu 24.04 | 2026 |  |
| [11] | Apple M4/10core/macOS, Node 25.6.1/Deno 2.6.9/Bun 1.3.9, 15 runs p50 | 2026 |  |
| [9] | 多硬件环境测试（AWS t3.medium、DigitalOcean 2vCPU、Apple M4 等），含/不含 tsx 等工具链 | 2026 |  |
| [15] | RSS 内存监控，不同基准测试场景 | 2026 |  |
| [16] | 3 个生产服务迁移后的实际内存使用对比 | 2026 |  |
|  | Monorepo 1847 个依赖安装对比 | 2026 |  |
| [18] | Node.js 官方测试套件通过率 | 2026 |  |
| [19] | Datadog 全球服务器端 JavaScript 运行时统计 | 2026-Q1 |  |
| [7] | Plaid 生产环境 100 服务 Aurora 到 TiDB 迁移 | 2025-2026 |  |
| [16] | 3 个生产服务实际迁移对比 | 2026 |  |

## 选型建议

基于以上多维度分析，以下为不同场景下的运行时选型建议：

## 选择 Node.js 的场景

- **企业级生产环境**：需要 30 个月 LTS 支持、OpenJS 基金会治理和成熟的生态支持
- **遗留系统维护**：已有大量 Node.js 代码库，迁移成本高于收益
- **复杂集成场景**：依赖大量原生模块（native addons）、特定企业软件集成
- **团队熟悉度优先**：团队对 Node.js 生态有深度积累，短期内不愿承担学习成本
- **稳定性压倒一切**：「凌晨 3 点的生产环境」场景，Node.js 的成熟度和社区支持最为可靠

## 选择 Bun 的场景

- **性能敏感型应用**：API 网关、实时通信（WebSocket）、高并发微服务，需要最大化吞吐量
- **Serverless/边缘计算**：6–32ms 的超快冷启动显著优于 Node.js 和 Deno
- **新项目/初创公司**：无历史包袱，可充分利用 Bun 的一体化工具链（bundler、测试、包管理）
- **成本优化驱动**：基础设施成本可降低 60–70%（某案例从 $2800/月降至 $1100/月）
- **AI/LLM 基础设施**：Anthropic 收购后的长期投入预期，与 Claude Code 生态的协同
- **快速开发迭代**：安装速度快 20–30 倍，构建时间大幅缩短

**注意事项**：
- 迁移现有 Node.js 项目通常需要 2–8 周（含测试）
- 部分原生模块（sharp、bcrypt）需要 Bun 特定版本
- 超大规模长期稳定性数据仍有限
- 无官方 LTS，但 Anthropic 收购后稳定性预期改善

## 选择 Deno 的场景

- **安全优先环境**：金融、医疗等需要严格权限控制的场景，Deno 的默认拒绝模型提供最强安全保障
- **TypeScript 原生项目**：无需额外配置，原生支持完整 TypeScript 特性
- **单二进制部署**：`deno compile` 生成独立可执行文件，适合 CLI 工具和自动化脚本
- **监管合规场景**：需要审计追踪和权限沙箱（如 Plaid 的金融服务场景）
- **边缘 CDN**：Deno Deploy 提供原生边缘计算支持
- **教育/原型开发**：内置工具链完整，开箱即用

**注意事项**：
- npm 兼容性仍有 24% 边缘 case 未覆盖
- LTS 仅 6 个月，长期支持需购买企业计划
- 生态规模小于 Node.js，部分小众包可能缺失

## 混合策略

对于大型组织，可考虑「 horses for courses」的混合策略：

1. **核心服务/遗留系统**：保持 Node.js，利用其稳定性和生态
2. **新微服务/API 网关**：评估 Bun，获取性能收益
3. **安全敏感/自动化工具**：采用 Deno，利用权限沙箱和单二进制部署
4. **渐进迁移**：如 Oak Oliver 案例，逐个服务验证后迁移，而非一次性重写

## 未来展望

- **2026–2028 年**：Node.js 维持主导地位，但 Bun 和 Deno 在新项目中的占比预计将持续增长（有预测称到 2028 年 40% 的新 JS 后端项目将采用 Bun 或 Deno）
- **Bun 的长期发展**：Anthropic 收购提供了资金和战略稳定性，但需关注其开源治理和社区独立性
- **Node.js 的演进**：每年一次发布节奏和类型剥离等特性将缩小与 Deno/Bun 的体验差距
- **Deno 的企业化**：6 个月 LTS 周期可能限制大型企业采用，企业支持计划将是关键

**数据来源:**

- 某生产案例迁移至 Bun 后基础设施成本从 $2800/月降至 $1100/月 [24]
- 迁移现有 Node.js 项目到 Bun 通常需要 2–8 周（含测试） [1][24]
- 预计未来几年，采用 Bun 或 Deno 的新 JavaScript 后端项目比例将显著增长 [1]
- Node.js 从每年两次主版本发布调整为每年一次，将缩小与 Deno/Bun 的开发体验差距 [5]
- Deno 的 LTS 支持周期仅 6 个月，可能限制大型企业的采用意愿 [6][13]

**测试环境:**

| 声明 | 条件 | 日期 | 来源类型 |
|---|---|---|---|
| [24] | 单一团队 6 个月生产 API 迁移实测 | 2025-2026 |  |

## 方法论与数据来源

## 数据来源

本报告综合了 28 个独立来源的数据，来源类型分布如下：

- **Tier 2 来源（高可信度）**：8 个——包括官方文档（Node.js Permissions、Deno Security）、官方博客（Deno.com、Bun.com、Anthropic 新闻稿）、InfoQ 技术媒体，以及 Deno 企业案例（Plaid 迁移）
- **Tier 3 来源（中等可信度）**：17 个——包括独立技术博客、基准测试站点（Better Stack、TechPlained、Sachin Sharma 等）、开发者工具评测站点
- **Tier 4 来源（参考性）**：3 个——个人开发者经验分享（Medium、Dev.to 等平台）

## 测试条件说明

性能基准数据来自多个独立测试，硬件环境和测试方法存在显著差异：

- **硬件环境**：涵盖消费级桌面（Ryzen 9 7950X、Apple M4）、云服务器（AWS t3.medium、c7g.4xlarge Graviton3、DigitalOcean 2vCPU）
- **操作系统**：主要为 Ubuntu 22.04/24.04 和 macOS
- **运行时版本**：Node.js 22.x–25.x、Deno 2.0–2.8、Bun 1.1–1.3
- **测试工具**：autocannon、wrk、自定义脚本等
- **重复次数**：多数测试执行 10–15 次取中位数或平均值

## 跨源比较的局限性

1. **硬件差异**：不同测试使用不同 CPU 架构（x86 vs ARM）和内存配置，直接横向比较存在偏差
2. **测试方法不一致**：部分测试使用 Express 框架，部分使用原生 HTTP；部分包含 TypeScript 转译开销，部分不包含
3. **版本差异**：不同测试使用的运行时版本不同（Bun 1.1 vs 1.3，Deno 2.0 vs 2.8），性能特征可能随版本变化
4. **工作负载差异**：HTTP Hello World 与实际生产负载（含数据库、业务逻辑）的表现可能截然不同——有测试显示在高并发+数据库场景下，三者收敛至约 12K req/s
5. **样本偏差**：生产案例多为早期采用者分享，可能存在「幸存者偏差」
6. **商业利益**：部分基准测试由运行时厂商发布，虽标注为「方向性参考」，但仍可能存在优化偏向

## 数据时间范围

- **主要数据收集期**：2025 年 12 月 – 2026 年 6 月
- **关键事件时间线**：
  - 2025 年 12 月：Anthropic 收购 Bun
  - 2026 年 1 月：Bun 安全模式 PR #25911 提交
  - 2026 年 4 月：部分基准测试执行（AWS t3.medium）
  - 2026 年 6 月：Node.js 发布每年一次版本计划（InfoQ）
  - Deno 2.8 兼容性提升（2026 年中）

## 置信度评估

- **高置信度**：多源交叉验证的数据（如 HTTP 吞吐量排序、冷启动相对表现、npm 兼容性百分比）
- **中置信度**：有 2–3 个来源支持的定量数据（如具体成本节约数字）
- **低置信度**：单一来源或预测性声明（如 2028 年市场占比预测）

**数据来源:**

- 本报告综合了 28 个独立来源，其中 Tier 2 来源 8 个、Tier 3 来源 17 个、Tier 4 来源 3 个 [8]
- 性能测试硬件环境涵盖 Ryzen 9 7950X、Apple M4、AWS Graviton3 等多种配置 [9][11][10]
- 在高并发+数据库场景下，三个运行时的吞吐量收敛至约 12K req/s [25]
- 数据收集时间范围为 2025 年 12 月至 2026 年 6 月 [3][5]

## 参考文献

[1]: https://www.askantech.com/bun-vs-nodejs-vs-deno-performance-benchmarks-2026 — Bun vs Node.js vs Deno: Production Benchmarks 2026
[2]: https://www.pkgpulse.com/guides/nodejs-runtime-comparison — Node.js vs Deno vs Bun: Runtime Comparison for 2026
[3]: https://www.anthropic.com/news/anthropic-acquires-bun-as-claude-code-reaches-usd1b-milestone — Anthropic acquires Bun as Claude Code reaches $1B milestone
[4]: https://bun.com/blog/bun-joins-anthropic — Bun is joining Anthropic
[5]: https://www.infoq.com/news/2026/06/nodejs-release-changes — Node.js Moves to One Major Release Per Year
[6]: https://deno.com/blog/v2.0 — Announcing Deno 2
[7]: https://deno.com/blog/how-plaid-migrated-critical-services-with-deno — How Plaid migrated 100 services with Deno
[8]: https://betterstack.com/community/guides/scaling-nodejs/nodejs-vs-deno-vs-bun — Node.js vs Deno vs Bun: Comparing JavaScript Runtimes
[9]: https://www.techplained.com/bun-vs-nodejs-vs-deno — Bun vs Node.js vs Deno: Runtime Comparison (2026)
[10]: https://sachinsharma.dev/blogs/bun-vs-node-vs-deno-benchmark — Bun 1.2 vs Node.js 24 vs Deno 2.0: Production Benchmark
[11]: https://www.repoflow.io/blog/node-js-vs-deno-vs-bun-performance-benchmarks — Node.js vs Deno vs Bun Performance Benchmarks
[12]: https://nodewire.net/nodejs-vs-deno-vs-bun — Node.js vs Deno vs Bun in 2026: which runtime to pick
[13]: https://devtoolswatch.com/en/bun-vs-deno-vs-nodejs-2026 — Bun vs Deno vs Node.js 2026: Runtime Comparison
[14]: https://stacknotice.com/blog/bun-deno-nodejs-comparison-2026 — Bun vs Deno 2 vs Node.js 22: Complete 2026 Comparison
[15]: https://sachinsharma.dev/blogs/bun-v1.2-vs-node-v22-vs-deno-v2.0-benchmark-2026 — Bun 1.2 vs Node.js 22 vs Deno 2.0: Ultimate 2026 Benchmark
[16]: https://engineering.oakoliver.com/articles/why-we-mass-replaced-nodejs-with-bun-in-production — We Replaced Node.js With Bun Across Every Production Service
[17]: https://techbytes.app/posts/deno-2-0-vs-bun-1-2-full-benchmark-analysis-node-js — Deno 2.0 vs Bun 1.2 vs Node.js Deep Dive 2026
[18]: https://blog.gio.dev/deno-2-8-node-js-compatibility-jumps-to-76-with-3x-faster-npm-installs-6bab776a024c — Deno 2.8: Node.js Compat 42%->76%
[19]: https://theeditorial.news/programming/bun-11-vs-nodejs-22-vs-deno-20-runtime-speed-package-compat-and-which-one-ships-mp28cgcy — Bun vs Node.js vs Deno: Runtime Tested 2026
[20]: https://docs.deno.com/runtime/fundamentals/security — Security and permissions | Deno Docs
[21]: https://nodejs.org/dist/latest/docs/api/permissions.html — Permissions | Node.js Documentation
[22]: https://github.com/oven-sh/bun/pull/25911 — Secure Mode PR #25911: Deno/Node compatible permissions for Bun
[23]: https://github.com/oven-sh/bun/discussions/725 — How secure is Bun compared to Deno? GitHub #725
[24]: https://medium.com/@sohail_saifii/bun-vs-deno-vs-node-i-migrated-our-api-three-times-heres-the-real-performance-data-a4499bb07b8d — Bun vs Deno vs Node: I Migrated Our API Three Times
[25]: https://devtoollab.com/blog/javascript-runtime-comparison — Bun vs Node.js vs Deno 2 in 2026: Benchmarks, Features
