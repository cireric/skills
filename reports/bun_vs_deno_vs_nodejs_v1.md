---
topic: 'Bun vs Deno vs Node.js'
goal_type: competitive_comparison
audience: engineer
depth: deep
version: 1
date: 2026-06-11
lang: zh
sources_count: 25
search_rounds: 4
quality: reviewed
---

# Bun vs Deno vs Node.js：2026 深度技术对比

> **结论速览**：Bun 赢在**性能**（2-4× HTTP、10-30× 包安装、3-4× 启动），Deno 赢在**安全**（默认零 I/O 沙箱），Node.js 赢在**生态**（3.5M 包、LTS、零迁移成本）。真实生产环境差距缩小至 1.5-2×。选型取决于瓶颈在哪：运行时速度（Bun）、威胁模型（Deno）、还是生态需求（Node.js）。

---

## 1. 架构深度对比

三大运行时采用完全不同的技术栈，这是性能和安全差异的根源。

### 1.1 核心架构

| 维度               | Bun 1.3+                          | Deno 2.x               | Node.js 24                     |
| ------------------ | --------------------------------- | ---------------------- | ------------------------------ |
| **JS 引擎**        | JavaScriptCore (Safari)           | V8 (Chrome)            | V8 13.6 (Chrome)               |
| **实现语言**       | Rust（原 Zig，2026.5 重写）       | Rust                   | C++                            |
| **I/O 模型**       | io_uring (Linux) / kqueue (macOS) | Tokio (Rust async)     | libuv (C 线程池)               |
| **JS→Native 桥接** | JSC C API                         | `#[op2]` 宏 + rusty_v8 | N-API / node-gyp               |
| **模块系统**       | ESM + CJS (npm 兼容)              | ESM 优先 + npm: 兼容   | CJS + ESM 双轨                 |
| **TypeScript**     | 原生全语法支持                    | 原生全语法支持         | 类型擦除（仅 erasable syntax） |

### 1.2 JIT 管线：为什么 Bun 启动快

这是最关键的架构差异。JavaScriptCore 的 4 层 JIT 管线与 V8 完全不同：

| JIT 层级 | JavaScriptCore (Bun) | V8 (Node.js/Deno)                 |
| -------- | -------------------- | --------------------------------- |
| 解释器   | LLInt                | Ignition                          |
| 基线 JIT | **~6 次调用后触发**  | **~100 次调用后触发** (Sparkplug) |
| 中层优化 | DFG (~60 次)         | Maglev (~400 次)                  |
| 峰值优化 | FTL (via B3/LLVM)    | TurboFan                          |

**实战影响**：一个处理 10 个请求就被回收的 serverless 函数，JSC 已经在运行优化代码，而 V8 还在解释执行。这就是 Bun 冷启动 3-4× 快于 Node 的底层原因。

> 来源：[Lucio Durán 深度分析](https://lucioduran.com/blog/bun-v2-runtime-internals-deep-dive) | [JSC 4-tier pipeline](https://readoss.com/en/webKit/webkit/inside-javascriptcore-the-4-tier-execution-pipeline)

### 1.3 I/O 路径：io_uring vs libuv vs Tokio

```
Bun:    JS → JSC → Zig/Rust → io_uring → Linux kernel    (零拷贝、零系统调用开销)
Deno:   JS → V8 → rusty_v8 → Tokio → epoll/io_uring      (Rust 异步运行时)
Node:   JS → V8 → N-API → libuv → thread pool → syscall  (线程池抽象，上下文切换开销)
```

Bun 在 Linux 上通过 `io_uring` 直接与内核通信，绕过 libuv 的线程池和上下文切换。这解释了 Bun 文件 I/O ~2× 快于 Node 的现象。macOS 上无 `io_uring`，差距缩小至 ~1.5×。

### 1.4 Zig→Rust 重写（2026 年 5 月）

Bun 于 2026 年 5 月用 Claude Code 将整个代码库从 Zig 重写为 Rust：1M+ 行代码，2,188 文件变更，Linux x64 glibc 测试兼容性 99.8%。已合并入 main 分支。最后一个 Zig 版本为 **v1.3.14**（2026.5.12）。

> ⚠️ **稳定性风险**：虽然测试通过率 99.8%，但百万行重写的回归风险真实存在。对稳定性敏感的部署建议锁定 v1.3.14。
>
> 来源：[heise.de](https://www.heise.de/en/news/AI-Porting-Claude-Rewrites-Bun-Codebase-in-Rust-11294318.html)

---

## 2. 性能基准对比

### 2.1 测试版本与方法论

| 来源                  | Bun    | Deno   | Node.js | 硬件                 |
| --------------------- | ------ | ------ | ------- | -------------------- |
| TechPlained (2026.2)  | 1.2    | 2.2    | 22.14   | Ryzen 9 7950X, 64GB  |
| nodewire.net (2026.4) | 1.3.13 | 2.7.14 | 24 LTS  | DigitalOcean droplet |
| RepoFlow (2026.2)     | 1.3.9  | 2.6.9  | 25.6.1  | M4 Mac               |
| bufferings (2025.12)  | 1.3.2  | 2.5.6  | 22.21.0 | —                    |

### 2.2 冷启动时间

> **关键场景**：Serverless / CLI 工具 / 自动扩缩容

| 运行时           | 冷启动 (ms) | 含 TypeScript (ms) | 倍率 vs Node | 备注                         |
| ---------------- | :---------: | :----------------: | :----------: | ---------------------------- |
| **Bun**          |  **5–30**   |      **~14**       |   **3–4×**   | JSC 快速 Baseline JIT        |
| Deno             |    15–80    |        ~25         |    1.5–2×    | V8 snapshot 加速             |
| Node.js 24 (ESM) |   ~60–80    |   ~280 (需 tsx)    |      1×      | Maglev 优化                  |
| Node.js 20 (CJS) |  ~120–200   |       ~350+        |     0.5×     | 无 Maglev，大量 require 开销 |

> 注：Node.js 冷启动区间较宽主要因为版本差异——Node 24 默认启用 Maglev 编译器显著改善启动性能，而 Node 20 使用传统 Sparkplug 路径。CJS 模式下的 `require()` 加载链也会增加启动时间。

> 来源：[TechPlained](https://www.techplained.com/bun-vs-nodejs-vs-deno) | [DrCodes](https://drcodes.com) | [DevToolReviews](https://www.devtoolreviews.com/reviews/bun-vs-node-vs-deno-2026-comparison)

### 2.3 HTTP 吞吐量

> **关键场景**：API 服务器 / Edge Functions / 高流量服务

#### 原生 HTTP 服务器

| 测试环境              | Bun (req/s) | Deno (req/s) | Node.js (req/s) | Bun vs Node |
| --------------------- | :---------: | :----------: | :-------------: | :---------: |
| TechPlained (Ryzen 9) | **312,000** |   178,000    |     142,000     |    2.2×     |
| Sachin Sharma (AWS)   | **245,000** |   180,000    |     95,000      |    2.6×     |
| Anton Putra (K8s)     | **85,000**  |    62,000    |     48,000      |    1.8×     |

#### 框架对比（bufferings benchmark, 2025.12）

| 运行时  | 框架    | Ping (req/s) |
| ------- | ------- | :----------: |
| **Bun** | Elysia  | **282,461**  |
| Deno    | Hono    |   102,452    |
| Bun     | Hono    |    78,709    |
| Node    | Fastify |    65,513    |
| Node    | Hono    |    46,079    |
| Node    | Express |    14,807    |

> 来源：[TechPlained](https://www.techplained.com/bun-vs-nodejs-vs-deno) | [bufferings/bun-http-framework-benchmark](https://github.com/bufferings/bun-http-framework-benchmark)

### 2.4 WebSocket

| 运行时  |    消息/秒    | vs Node  |
| ------- | :-----------: | :------: |
| **Bun** | **2,536,227** | **5.8×** |
| Deno    |   1,320,525   |   3.0×   |
| Node.js |    435,099    |    1×    |

> ⚠️ 此数据来自 Bun 官方基准，未经独立验证。实际差距可能小于标称值。
>
> 来源：[bun.sh 官方基准](https://bun.sh)（Linux x64, 32 并发客户端）

### 2.5 文件 I/O

| 运行时  | 顺序读 (MB/s) | 顺序写 (MB/s) | 关键技术         |
| ------- | :-----------: | :-----------: | ---------------- |
| **Bun** |   **4,200**   |   **3,800**   | io_uring (Linux) |
| Node.js |     2,100     |     1,900     | libuv 线程池     |
| Deno    |     1,850     |     1,700     | Tokio async      |

> 来源：[TechPlained](https://www.techplained.com/bun-vs-nodejs-vs-deno)（Ryzen 9 7950X, Ubuntu 24.04）

### 2.6 SQLite

| 运行时  | 插入 (rows/s) | 查询 (rows/s) | API                    |
| ------- | :-----------: | :-----------: | ---------------------- |
| **Bun** |  **890,000**  | **1,200,000** | `bun:sqlite` (原生)    |
| Deno    |    620,000    |    850,000    | `@db/sqlite`           |
| Node.js |    580,000    |    780,000    | `node:sqlite` (实验性) |

> 来源：[TechPlained](https://www.techplained.com/bun-vs-nodejs-vs-deno)（Ryzen 9 7950X, 64GB RAM, 2026.2）

### 2.7 包安装速度

| 工具            | 小型项目 | 大型 monorepo (1,847 deps) |
| --------------- | :------: | :------------------------: |
| **bun install** | **1.6s** |          **47s**           |
| deno install    |    4s    |             —              |
| pnpm            |  8–12s   |            4min            |
| npm             |   14s    |           28min            |

> 来源：[nodewire.net](https://nodewire.net/nodejs-vs-deno-vs-bun/) | [dev.to](https://dev.to/jsgurujobs/bun-vs-deno-vs-nodejs-in-2026-benchmarks-code-and-real-numbers-2l9d)

### 2.8 打包/构建速度

| 工具            |    小型库    | 10K 模块应用 |
| --------------- | :----------: | :----------: |
| **Bun bundler** | **37–200ms** | **0.5–0.8s** |
| esbuild         |  200–300ms   |   1.2–1.4s   |
| Rspack          |     87ms     |     3.6s     |
| Vite            |     1.2s     |     2.0s     |
| Webpack         |     2.6s     |     17s      |

> 来源：[rolldown/benchmarks](https://github.com/rolldown/benchmarks) | [bun.sh](https://bun.sh)

### 2.9 内存使用

| 运行时  | 空闲 (MB) | 持续负载 (MB) |   稳定性    |
| ------- | :-------: | :-----------: | :---------: |
| **Bun** | **28–48** |  ~210 (波动)  | ⚠️ 波动较大 |
| Deno    |   42–72   |     ~158      |  ✅ 较稳定  |
| Node.js |   45–68   |     ~142      | ✅ 最可预测 |

> ⚠️ Bun 的 JavaScriptCore GC 在持续负载下内存波动比 V8 大，对长期运行的生产服务需关注。

### 2.10 真实生产迁移数据

**Trigger.dev**（2026.3，生产环境 k6 负载测试）：

| 指标     | Node.js     | Bun         | 提升     |
| -------- | ----------- | ----------- | -------- |
| 吞吐量   | 4,534 req/s | 9,434 req/s | **2.1×** |
| p50 延迟 | 10.1ms      | 4.5ms       | **2.2×** |
| p95 延迟 | 14.9ms      | 7.4ms       | **2.0×** |
| 最大延迟 | 403ms       | 22ms        | **18×**  |
| 容器镜像 | 180MB       | 68MB        | **2.6×** |

> 来源：[Trigger.dev — Why we replaced Node.js with Bun for 5x throughput](https://trigger.dev/blog/firebun)（2026.3.27, k6 负载测试, 500 controllers, 50 VUs, 30s）

### 2.11 性能总结

| 指标           |    🥇    |   🥈    |   🥉   |
| -------------- | :------: | :-----: | :----: |
| 启动时间       | **Bun**  |  Deno   |  Node  |
| HTTP 吞吐      | **Bun**  |  Deno   |  Node  |
| 文件 I/O       | **Bun**  |  Node   |  Deno  |
| WebSocket      | **Bun**  |  Deno   |  Node  |
| SQLite         | **Bun**  |  Deno   |  Node  |
| 包安装         | **Bun**  |  Deno   |  npm   |
| 打包速度       | **Bun**  | esbuild | Rspack |
| 内存（空闲）   | **Bun**  |  Deno   |  Node  |
| 内存（稳定性） | **Node** |  Deno   |  Bun   |

---

## 3. 生态成熟度对比

### 3.1 npm 兼容性

| 运行时      | Node.js 测试套件通过率 | Top 50K 包兼容率 | 关键缺口                                           |
| ----------- | :--------------------: | :--------------: | -------------------------------------------------- |
| **Node.js** |          100%          |       100%       | 无                                                 |
| **Bun**     |    ~90%+ (Bun 1.2)     |     ~93–98%¹     | `node:vm`、V8 内部 C++ API、部分原生插件           |
| **Deno**    |      76.4% (2.8)       |      ~89.2%      | `node:http2`、`node:tls`、`node:v8`、旧 N-API 插件 |

> ¹ Bun Top 50K 包兼容率区间 93–98% 来自不同测试方法/版本（Bun 官方声称 ~98%，第三方独立测试 ~93%），真实兼容率可能在此区间内波动。Node.js 测试套件通过率 ~90%+ 为 Bun 1.2 时期数据，Bun 1.3 版本可能更高。

> 来源：[Bun 1.2 Blog](https://bun.sh/blog/bun-v1.2) | [Deno 2.8 Medium](https://medium.com/@gosu0x/deno-2-8-makes-the-node-compatibility-bet-real-48f3e4db07b1) | [The Editorial](https://theeditorial.news/programming/deno-20-npm-compatibility-89-pass-rate-on-50000-packages-where-it-still-breaks-mpdnvftz)

### 3.2 原生插件（最大痛点）

| 插件             | Node.js |   Bun   |  Deno   |
| ---------------- | :-----: | :-----: | :-----: |
| sharp (图像处理) |   ✅    | ⚠️ 部分 | ⚠️ 部分 |
| bcrypt (加密)    |   ✅    | ⚠️ 部分 | ⚠️ 部分 |
| better-sqlite3   |   ✅    |   ⚠️    |   ⚠️    |
| Prisma Engine    |   ✅    |   ✅    |   ✅    |
| canvas           |   ✅    |   ❌    |   ❌    |

**Bun 的应对策略**：在 JSC 中实现 V8 公共 C++ API，支持 `cpu-features` 等使用 V8 内部的包——但不使用 V8。

### 3.3 npm 安全风险

2025 年 npm 新增 **171,740 个恶意包**，838,778 个发布含 CVSS 9.0+ 漏洞。供应链攻击是三大运行时共同面临的威胁，但 Deno 的默认沙箱提供了唯一的运行时级防线。

> 来源：[Sonatype SSSC 2026](https://www.sonatype.com/state-of-the-software-supply-chain/2026/software-infrastructure-growth)

### 3.4 框架支持

| 框架    | Node.js |      Bun       | Deno |
| ------- | :-----: | :------------: | :--: |
| Next.js |   ✅    |       ✅       |  ❌  |
| Express |   ✅    | ✅ (3× faster) |  ✅  |
| Fastify |   ✅    |       ✅       |  ✅  |
| Hono    |   ✅    |       ✅       |  ✅  |
| NestJS  |   ✅    |       ✅       |  ⚠️  |
| Elysia  |   ❌    | ✅ (Bun 专属)  |  ❌  |
| Fresh   |   ❌    |       ❌       |  ✅  |

---

## 4. 安全模型对比

这是三大运行时差异最大的维度。

### 4.1 安全架构

| 维度           | Bun      | Deno                        | Node.js          |
| -------------- | -------- | --------------------------- | ---------------- |
| **默认姿态**   | 完全信任 | **零 I/O**                  | 完全信任         |
| **权限粒度**   | 无       | 路径/域名/环境变量级        | 进程级（粗粒度） |
| **运行时沙箱** | ❌       | ✅                          | ⚠️ 实验性        |
| **权限代理**   | ❌       | ✅ (外部策略进程)           | ❌               |
| **审计日志**   | ❌       | ✅ (DENO_AUDIT_PERMISSIONS) | ❌               |
| **供应链防护** | ❌       | 运行时权限阻断              | ❌               |

### 4.2 Deno 权限系统详解

```bash
# 精细权限控制
deno run \
  --allow-read=/app/data \
  --allow-net=api.stripe.com:443 \
  --allow-env=DATABASE_URL \
  --allow-run=git,psql \
  server.ts
```

Deno 2.5+ 支持在 `deno.json` 中声明权限集合：

```json
{
	"permissions": {
		"default": {
			"read": ["./data"],
			"net": ["api.stripe.com:443"]
		}
	}
}
```

**权限代理**（企业级）：通过 `DENO_PERMISSION_BROKER_PATH` Unix socket，所有权限检查委托给外部策略进程——实现集中化策略控制。

> 来源：[Deno Security Docs](https://docs.deno.com/runtime/fundamentals/security/) | [Deno 2.5 Blog](https://deno.com/blog/v2.5)

### 4.3 Node.js Permission Model

Node.js 24 的 `--permission` 已稳定，但官方文档明确标注：

> "This is a seat belt, not a security boundary."

`node:sqlite` 可绕过文件系统权限。恶意代码可通过多种路径逃逸。

> 来源：[Node.js Permissions API](https://nodejs.org/api/permissions.html)

---

## 5. 开发体验与工具链

### 5.1 内置工具对比

| 工具                 |           Bun            |            Deno            |         Node.js         |
| -------------------- | :----------------------: | :------------------------: | :---------------------: |
| **运行时**           |            ✅            |             ✅             |           ✅            |
| **包管理器**         |     ✅ `bun install`     |     ✅ `deno install`      |      ✅ npm (外部)      |
| **打包器**           |      ✅ `bun build`      | ⚠️ `deno bundle` (legacy¹) |           ❌            |
| **测试运行器**       |      ✅ `bun test`       |       ✅ `deno test`       |    ✅ `node --test`     |
| **格式化**           |            ❌            |       ✅ `deno fmt`        |           ❌            |
| **Linter**           |            ❌            |       ✅ `deno lint`       |           ❌            |
| **TypeScript**       |        ✅ 全语法         |         ✅ 全语法          |       ⚠️ 类型擦除       |
| **文档生成**         |            ❌            |       ✅ `deno doc`        |           ❌            |
| **基准测试**         |            ❌            |      ✅ `deno bench`       |           ❌            |
| **Jupyter**          |            ❌            |     ✅ `deno jupyter`      |           ❌            |
| **SQLite**           |     ✅ `bun:sqlite`      |         ⚠️ via npm         |         ⚠️ 实验         |
| **Postgres**         |       ✅ `Bun.sql`       |             ❌             |           ❌            |
| **MySQL**            |       ✅ `Bun.sql`       |             ❌             |           ❌            |
| **Redis**            |      ✅ `Bun.redis`      |             ❌             |           ❌            |
| **S3**               |       ✅ `Bun.s3`        |             ❌             |           ❌            |
| **单文件编译**       | ✅ `bun build --compile` |     ✅ `deno compile`      | ⚠️ `--build-sea` (实验) |
| **Dev Server (HMR)** |            ✅            |             ❌             |           ❌            |
| **Cron**             |      ✅ `Bun.Cron`       |             ❌             |           ❌            |
| **Shell**            |         ✅ 内置          |             ❌             |           ❌            |

**Bun 的定位**：一体化运行时 + 全栈工具链 + 内置数据库客户端
**Deno 的定位**：一体化运行时 + 代码质量工具链 + 安全优先
**Node.js 的定位**：最小运行时 + 外部生态自由组合

> ¹ `deno bundle` 在 Deno 2 中已标记为 legacy。官方推荐使用 `deno compile`（生成独立二进制）或 esbuild 等外部打包工具进行前端打包。

### 5.2 TypeScript 支持

| 特性        |   Bun   |      Deno       |                Node.js                 |
| ----------- | :-----: | :-------------: | :------------------------------------: |
| 类型擦除    |   ✅    |       ✅        |             ✅ (amaro/oxc)             |
| 类型检查    | ✅ 内置 | ✅ `deno check` |               ❌ 需 tsc                |
| 枚举 (enum) |   ✅    |       ✅        | ❌ 需 `--experimental-transform-types` |
| 装饰器      |   ✅    |       ✅        |                   ❌                   |
| 命名空间    |   ✅    |       ✅        |                   ❌                   |
| JSX/TSX     |   ✅    |       ✅        |               ⚠️ 需配置                |

---

## 6. 生产就绪度与治理

### 6.1 治理与 LTS

| 维度            | Bun                      | Deno           | Node.js            |
| --------------- | ------------------------ | -------------- | ------------------ |
| **治理**        | Anthropic (2025.12 收购) | Deno Land Inc. | OpenJS Foundation  |
| **LTS 策略**    | ❌ 无正式策略            | ✅ Deno 2 LTS  | ✅ 可预测 LTS 周期 |
| **当前 LTS**    | —                        | 2.x            | 24 (至 2028.4)     |
| **商业支持**    | Anthropic 内部使用       | Deno Deploy    | 多家商业支持       |
| **Docker 镜像** | ~89MB                    | ~73MB          | ~180MB             |

> 来源：[endoflife.date/bun](https://endoflife.date/bun) | [Node.js Releases](https://nodejs.org/en/about/previous-releases)

### 6.2 企业采用信号

| 运行时      | 采用案例                                                                      |
| ----------- | ----------------------------------------------------------------------------- |
| **Bun**     | Midjourney, Replit, Cursor, Lovable, CodeRabbit, Trigger.dev                  |
| **Deno**    | deno.com, deco.cx (巴西头部电商平台, 5× 页面加载提速), Deno Deploy Subhosting |
| **Node.js** | Netflix, Uber, PayPal, LinkedIn, NASA, 几乎所有 Fortune 500                   |

### 6.3 已知风险

| 风险               | Bun                                                                                                  | Deno        | Node.js         |
| ------------------ | ---------------------------------------------------------------------------------------------------- | ----------- | --------------- |
| Zig→Rust 重写回归  | ⚠️ 高 (2026.5)                                                                                       | —           | —               |
| 原生插件兼容       | ⚠️ 中                                                                                                | ⚠️ 中       | ✅ 完整         |
| 内存泄漏 (原生 DB) | ⚠️ 曾报告 (2025.2, [Anton Putra K8s 基准](https://www.youtube.com/@AntonPutra)，具体视频 URL 待确认) | —           | —               |
| 无安全沙箱         | ⚠️ 高                                                                                                | ✅ 有       | ⚠️ 弱           |
| LTS 缺失           | ⚠️ 中                                                                                                | ✅ 有       | ✅ 有           |
| 供应链攻击         | ⚠️ 无运行时防护                                                                                      | ✅ 权限阻断 | ⚠️ 无运行时防护 |

---

## 7. 选型决策指南

### 7.1 何时选择 Bun

- ✅ **Serverless / Edge Functions** — 冷启动是核心指标，Bun 3-4× 优势
- ✅ **CLI 工具** — 启动快、单文件编译成熟
- ✅ **新项目** — 无迁移成本，享受一体化工具链
- ✅ **CI/CD 加速** — `bun install` 比 npm 快 10-30×
- ✅ **全栈 API** — 内置 DB 客户端省去外部依赖
- ❌ **重度原生插件依赖** — sharp、bcrypt、canvas 等可能不工作
- ❌ **企业级安全需求** — 无沙箱、无权限模型
- ❌ **需要 LTS 保障** — 无正式支持策略

### 7.2 何时选择 Deno

- ✅ **运行不受信代码** — 默认沙箱是唯一运行时级防线
- ✅ **安全敏感服务** — 权限代理、审计日志、精细 I/O 控制
- ✅ **零配置团队** — 一个二进制替代 prettier + eslint + jest + tsc
- ✅ **Web 标准优先** — fetch、WebSocket、Request/Response 原生对齐
- ✅ **单文件分发** — `deno compile` 成熟且跨平台
- ❌ **重度 npm 生态依赖** — 89% 兼容率可能不够
- ❌ **Next.js 等生态** — Fresh 仍在成熟中
- ❌ **追求极致性能** — HTTP 吞吐介于 Node 和 Bun 之间

### 7.3 何时选择 Node.js

- ✅ **现有项目** — 零迁移成本，3.5M 包触手可及
- ✅ **原生插件依赖** — N-API 生态完整，sharp/bcrypt/canvas 全部可用
- ✅ **企业 LTS 需求** — 可预测的支持周期，OpenJS Foundation 治理
- ✅ **长尾包需求** — 冷门企业集成包只存在于 npm
- ✅ **生产稳定性** — 十余年行星级规模验证
- ❌ **追求开发效率** — 需组装大量外部工具
- ❌ **Serverless 冷启动** — 60-200ms vs Bun 5-30ms
- ❌ **CI 速度** — npm install 慢 10-30×

### 7.4 多运行时策略（务实选择）

越来越多团队采用混合策略：

| 场景       | 运行时                          | 原因                         |
| ---------- | ------------------------------- | ---------------------------- |
| 开发/CI    | **Bun**                         | 安装快、启动快、测试快       |
| 生产 API   | **Node.js**                     | 稳定性、生态完整性、APM 支持 |
| 不受信代码 | **Deno**                        | 安全沙箱                     |
| CLI 工具   | **Bun** (`bun build --compile`) | 单文件分发 + 快启动          |

> 来源：[Trigger.dev — Why we replaced Node.js with Bun](https://trigger.dev/blog/firebun) | [nodewire.net](https://nodewire.net/nodejs-vs-deno-vs-bun/)

---

## 8. 方法论

### 数据来源

本报告综合 4 轮并行研究（Bun 架构、Deno 架构、Node.js 现状、基准对比），覆盖 25+ 来源：

- **官方文档**：bun.sh/docs, docs.deno.com, nodejs.org
- **官方基准**：bun.sh benchmarks, deno.com benchmarks
- **独立基准**：TechPlained (Ryzen 9 7950X), bufferings framework benchmark, Anton Putra (K8s), RepoFlow (M4 Mac)
- **生产案例**：Trigger.dev 迁移报告
- **行业报告**：Sonatype SSSC 2026
- **深度分析**：Lucio Durán JSC 深度分析, ReadOSS Deno 扩展系统分析

### 局限性

1. **跨源基准对比**：不同来源使用不同硬件、版本、测试工具，数字仅方向性参考
2. **版本快速迭代**：Bun 1.0→1.3、Deno 1→2.8、Node 20→24 期间性能变化显著，旧基准可能已不适用
3. **合成基准 vs 真实负载**：Hello World 基准放大运行时差异；真实应用中 DB/业务逻辑占主导，差距缩小至 1.5-2×
4. **Vendor 基准**：Bun 官方基准在有利条件下测试，应与独立基准交叉验证

### 数据收集时间

2025 年 Q3 — 2026 年 Q2

---

## 附录：来源索引

| #   | 来源                           | URL                                                                                                                           |
| --- | ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------- |
| 1   | Bun 官方文档                   | https://bun.sh/docs                                                                                                           |
| 2   | Bun 1.2 发布博客               | https://bun.sh/blog/bun-v1.2                                                                                                  |
| 3   | Bun 1.3 发布博客               | https://bun.sh/blog/bun-v1.3                                                                                                  |
| 4   | Bun GitHub                     | https://github.com/oven-sh/bun                                                                                                |
| 5   | Deno 安全文档                  | https://docs.deno.com/runtime/fundamentals/security/                                                                          |
| 6   | Deno CLI 参考                  | https://docs.deno.com/runtime/reference/cli/                                                                                  |
| 7   | Deno 2.0 发布                  | https://deno.com/blog/v2.0                                                                                                    |
| 8   | Deno 2.5 发布                  | https://deno.com/blog/v2.5                                                                                                    |
| 9   | Deno Node 兼容                 | https://docs.deno.com/runtime/fundamentals/node/                                                                              |
| 10  | Node.js 24 发布                | https://nodejs.org/en/blog/announcements/v24-release-announce                                                                 |
| 11  | Node.js Permissions            | https://nodejs.org/api/permissions.html                                                                                       |
| 12  | Node.js 发布时间表             | https://nodejs.org/en/about/previous-releases                                                                                 |
| 13  | TechPlained 基准               | https://www.techplained.com/bun-vs-nodejs-vs-deno                                                                             |
| 14  | nodewire.net 对比              | https://nodewire.net/nodejs-vs-deno-vs-bun/                                                                                   |
| 15  | DevToolReviews                 | https://www.devtoolreviews.com/reviews/bun-vs-node-vs-deno-2026-comparison                                                    |
| 16  | bufferings framework benchmark | https://github.com/bufferings/bun-http-framework-benchmark                                                                    |
| 17  | rolldown benchmarks            | https://github.com/rolldown/benchmarks                                                                                        |
| 18  | Lucio Durán JSC 分析           | https://lucioduran.com/blog/bun-v2-runtime-internals-deep-dive                                                                |
| 19  | JSC 4-tier pipeline            | https://readoss.com/en/webKit/webkit/inside-javascriptcore-the-4-tier-execution-pipeline                                      |
| 20  | ReadOSS Deno 扩展系统          | https://readoss.com/en/denoland/deno/v8-bridge-deno-extension-system-rust-to-javascript                                       |
| 21  | Zig→Rust 重写                  | https://www.heise.de/en/news/AI-Porting-Claude-Rewrites-Bun-Codebase-in-Rust-11294318.html                                    |
| 22  | Sonatype SSSC 2026             | https://www.sonatype.com/state-of-the-software-supply-chain/2026/software-infrastructure-growth                               |
| 23  | npm 50K 包兼容测试             | https://theeditorial.news/programming/deno-20-npm-compatibility-89-pass-rate-on-50000-packages-where-it-still-breaks-mpdnvftz |
| 24  | Bun 兼容性 2026                | https://www.alexcloudstar.com/blog/bun-compatibility-2026-npm-nodejs-nextjs                                                   |
| 25  | Deno 2.8 深度分析              | https://medium.com/@gosu0x/deno-2-8-makes-the-node-compatibility-bet-real-48f3e4db07b1                                        |
| 26  | endoflife.date/bun             | https://endoflife.date/bun                                                                                                    |
| 27  | Trigger.dev 迁移               | https://trigger.dev/blog/firebun                                                                                              |
