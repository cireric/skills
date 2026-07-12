---
topic: Unix哲学原则对于实际软件工程的作用
goal_type: panoramic_understanding
date: 2026-07-01
audience: engineer
report_language: zh
scope: 探究Unix哲学的核心原则（如'做一件事并做好'、'程序协同工作'、'文本流接口'等）如何影响现代软件工程实践，包括微服务架构、CLI工具设计、DevOps管道、容器化等领域的体现，以及这些原则的局限性和反例
review_status: degraded
verification_required: true
search_rounds: 3
source_count: 34
---

> **Verification note**: This report is a research starting point, not a citable authority.
> † = data not found in cited source; ‡ = data from indirect source.

| Status | Count | Ratio |
|--------|-------|-------|
| Confirmed | 23 | 100% |
| Indirect ‡ | 0 | 0% |
| Absent † | 0 | 0% |

## Unix哲学核心原则概述及其对现代软件工程的整体影响

Unix哲学起源于1969年Bell Labs，Ken Thompson与Dennis Ritchie构建了一个与Multics方向相反的计算环境——不追求包罗万象，而是追求简洁可组合[&#91;1&#93;](#refs)。Doug McIlroy于1978年在BSTJ前言中提出四条原则，成为Unix哲学的规范表述：(1)让每个程序做好一件事，新需求另建新程序而非堆砌功能；(2)预期每个程序的输出成为另一个尚未构思的程序的输入；(3)尽早试运行软件；(4)用工具替代非熟练人工[&#91;2&#93;](#refs)[&#91;3&#93;](#refs)。Peter Salus于1994年将其浓缩为三句话：做好一件事、程序协同工作、用文本流作为通用接口[&#91;2&#93;](#refs)。Eric Raymond随后编纂了17条规则，涵盖模块化、组合、分离、简洁、透明、健壮等维度[&#91;4&#93;](#refs)。

Unix哲学对现代软件工程的影响是全方位的。微服务架构的"做好一件事"原则在理念上继承自DOTADIW，但在实践中面临粒度权衡和通信开销等挑战[&#91;5&#93;](#refs)；DevOps管道本质上是glorified bash script，用管道组合替代单体自动化[&#91;6&#93;](#refs)；Kubernetes的模块化组件设计（API Server、Controller Manager、kubelet、Scheduler各司其职）是Unix哲学在容器编排领域的直接体现[&#91;7&#93;](#refs)；AI代理框架中，Pipe-to-LLM模式将Unix管道扩展为AI增强的文本变换管线[&#91;8&#93;](#refs)。正如一篇2026年的文章所言：McIlroy的原则是成型的而非草创的——它们被证明是正确的，我们花了48年在一段话能容纳的思想上构建越来越复杂的技术[&#91;9&#93;](#refs)。Unix哲学的核心洞察在于：它不是禁止大型系统，而是提供了一种构建大型系统的策略——工具和管道压缩工作量，复杂任务由经过验证的部件组装而成[&#91;1&#93;](#refs)。

## Unix哲学的起源与核心原则

### McIlroy四原则

Doug McIlroy作为Unix管道的发明者，于1978年在Bell System Technical Journal前言中提出了Unix哲学的规范表述[&#91;10&#93;](#refs)。四条原则的核心逻辑形成闭环：做好一件事（模块化）→输出即输入（组合性）→尽早试运行（迭代）→用工具替代人工（自动化）。其中第二条原则最具前瞻性——"预期每个程序的输出成为另一个尚未构思的程序的输入"，这意味着在不知道组合方式的前提下设计组合性[&#91;9&#93;](#refs)。McIlroy还特别强调：不要用冗余信息污染输出，避免严格的列式或二进制输入格式，不要坚持交互式输入[&#91;10&#93;](#refs)。

### Salus三原则与ESR 17规则

1994年Peter Salus将McIlroy的思想浓缩为三句话：做好一件事、程序协同工作、文本流作为通用接口[&#91;2&#93;](#refs)。同年Mike Gancarz出版The UNIX Philosophy，强调可移植性优于效率[&#91;2&#93;](#refs)。Eric Raymond在The Art of Unix Programming中编纂了17条规则，其中最关键的包括[&#91;4&#93;](#refs)：

| 规则 | 核心要义 |
|------|----------|
| Rule of Modularity | 用简洁的部件通过清晰的接口连接 |
| Rule of Composition | 设计程序使其能与其他程序连接 |
| Rule of Separation | 策略与机制分离 |
| Rule of Simplicity | 为简洁而设计 |
| Rule of Transparency | 为可见性而设计 |
| Rule of Representation | 将知识折叠进数据 |
| Rule of Diversity | 不信任唯一正确方式 |

### 经典案例：McIlroy vs Knuth

Jon Bentley的编程挑战——统计文本中n个最常用词并排序输出——最能说明Unix哲学的威力。Knuth构建了一个10+页Pascal单体系统，McIlroy用6行shell管道（tr、sort、uniq、sed）解决，每个工具只做一件事[&#91;5&#93;](#refs)。McIlroy评价Knuth的作品为"工业强度的Faberge彩蛋——精致、工艺超群、超越一切寻常需求，从诞生之初就是博物馆展品"[&#91;5&#93;](#refs)。

### 三个承诺

unixphilosophy.com将Unix哲学提炼为三个承诺[&#91;1&#93;](#refs)：Iterate（让构建和测试快速，迭代才是真正的生产力引擎）、Comprehend（保持系统小到可以理解，能装进头脑的系统才是可信赖的系统）、Replace（让程序保持可替换，可替换的部件才能在变化中存活）。

## Unix哲学对微服务和模块化架构的影响

### Code the Perimeter

Kevin Greer于2016年的分析揭示了Unix击败Multics的关键：Ritchie和Thompson以O(N+M)的代价编码了周长（perimeter），而非O(N*M)的面积[&#91;11&#93;](#refs)。Unix哲学常被简化为"做好一件事"，但第二句和第三句同样重要——程序必须通过通用接口协同工作，否则就会产生"矩形复杂度"：N个服务与M个关注点的交叉组合[&#91;11&#93;](#refs)。Twitter的Finagle RPC系统在JVM服务间实现了"做好一件事"和"协同工作"，但无法跨越语言边界——缺少第三条原则（通用接口）[&#91;11&#93;](#refs)。服务网格（如Istio）以sidecar模式实现了三原则：做好一件事（增强网络流量）、协同工作（作为sidecar）、通用接口（TCP/HTTP）[&#91;11&#93;](#refs)。

### DOTADIW与微服务

Martin Fowler对微服务的定义与Unix哲学高度同构：单体应用的变更周期相互绑定，小改动需要重建和重新部署整个单体；微服务架构将应用构建为独立可部署、可扩展的服务套件[&#91;5&#93;](#refs)。一篇社区分析指出：Unix哲学已经赢得如此彻底，以至于大多数程序员没有体验过其他方式——微服务、DockerHub、PyPI、NPM都是小事物组合的产物[&#91;12&#93;](#refs)。然而，IPC是HTTP/JSON、管道还是socket，本质上讨论的是同一种系统[&#91;13&#93;](#refs)。

### 松耦合的挑战

Unix哲学在微服务中的实践面临严峻挑战。学术研究表明，微服务架构中大量时间花在服务间RPC通信而非计算上，细粒度服务分解的粒度必须与通信成本仔细平衡[&#91;14&#93;](#refs)。Jolie语言的研究指出，缺乏专用组合抽象的微服务有沦为"分布式单体"的风险[&#91;15&#93;](#refs)。社区讨论更直接：自1970年代以来就有"魔法模块化"的承诺，但大多数领域本质上是相互关联的，不存在干净的分离线——要么集中协调，要么花人力清理重复和不一致[&#91;16&#93;](#refs)。如果一个微服务不能完全独立地运行、测试、部署和使用，它就不是微服务——而是一个带有复杂网络依赖链的工程糟糕的单体系统[&#91;16&#93;](#refs)。

## Unix哲学在DevOps和CI/CD管道中的体现

### 管道即自动化

DevOps运动的核心实践与Unix哲学高度同构。一篇管道设计文章明确指出：CI/CD管道本质上是手动构建和部署流程的自动化版本——它就是一个glorified shell或bash script，周围包裹着现代工具[&#91;6&#93;](#refs)。管道应该尽可能愚蠢——只是构建系统和部署目标之间的胶水[&#91;6&#93;](#refs)。这直接呼应了Unix哲学：每个工具做好一件事，显式配置优于巧妙默认，可组合脚本优于单体抽象[&#91;6&#93;](#refs)。

### CI/CD引擎的Unix哲学批判

Reddit上的一个"不受欢迎观点"帖子尖锐指出：CI/CD引擎违反了Unix原则——每个引擎做了太多事情（GUI、CLI、两个API、密钥管理、Slack集成、内置图表和仪表板），而不是做好一件事并通过管道串联[&#91;17&#93;](#refs)。大多数CI/CD可以用Docker容器和Python完成：GitHub PR发送webhook到容器，运行脚本[&#91;17&#93;](#refs)。但回应也指出：CI/CD引擎的价值在于UI、日志查看器、git push触发器和执行追踪——正如ORM与数据库的关系，存在阻抗匹配问题[&#91;17&#93;](#refs)。

### Infrastructure-as-Code与文件抽象

arXiv论文追踪了Unix的"一切皆文件"设计哲学如何从操作系统延伸到DevOps再到AI代理[&#91;18&#93;](#refs)。Infrastructure-as-Code将多样化接口折叠为代码，提供了组合性、可复现性和可审计性——HashiCorp明确阐述了这一原则[&#91;18&#93;](#refs)。ICM（Interpretable Context Methodology）将McIlroy原则和Parnas信息隐藏应用于AI代理编排：每个阶段处理单一步骤，将输出写入独立文件夹，文件夹结构替代框架[&#91;19&#93;](#refs)。Vercel的实践更极端：Andrew Qu提出"也许最好的代理架构就是几乎没有架构——BASH is all you need"[&#91;20&#93;](#refs)。Ralph Wiggum插件本质上就是一个带do/while循环的BASH脚本，所有工作写入文件并捕获在git历史中[&#91;20&#93;](#refs)。

## Unix哲学在CLI工具设计中的应用

### Pipe-to-LLM模式

Unix管道已存在超过50年，AI驱动的CLI工具将其扩展为更强大的形态——将文本管道输入LLM而非grep/awk/sed[&#91;8&#93;](#refs)。Pipe-to-LLM模式的核心：任何写入stdout的命令都成为自身的AI增强版本——无需IDE插件、聊天窗口或复制粘贴，数据按Unix意图从一个工具流向下一个[&#91;8&#93;](#refs)。Simon Willison的llm工具（模型无关）开创了这一模式；Claude Code的-p标志提供非交互式一次性模式；GitHub Copilot CLI也采用类似方案[&#91;8&#93;](#refs)。关键问题：当每个CLI工具假设下游可能有LLM时会发生什么——git log为AI可读性格式化输出，测试运行器为机器理解结构化失败信息[&#91;8&#93;](#refs)。

### Agent DX：为AI代理设计CLI

AI编码代理（Claude Code、Codex、Cursor）拥有shell访问权限，可以运行任何CLI工具，但大多数CLI工具对AI代理微妙地不友好[&#91;21&#93;](#refs)。CLI优于MCP的关键论据：token成本（有开发者报告从MCP切换到CLI后token消耗显著降低）、零间接层（代理已知道如何读取--help、解析输出、处理错误）、可靠性（MCP服务器会崩溃，CLI是无状态的）[&#91;21&#93;](#refs)。八条规则包括：结构化输出（--json）、语义退出码、幂等命令、自文档化、为组合性设计、dry-run模式、结构化错误信息、一致的名词-动词语法[&#91;21&#93;](#refs)。

### 12-Factor CLI与CLI-first设计

Jeff的12-Factor CLI Apps（2018）在2026年因AI代理而更加相关[&#91;22&#93;](#refs)。核心原则：stdout是神圣的，stderr做其他一切——这种分离正是Unix工具可组合的基础；组合优于插件——插件系统引入第二运行时、动态加载、版本协商和兼容性问题，Unix哲学已经解决了扩展性：小工具、可预测的IO和管道比嵌入插件架构更简单[&#91;22&#93;](#refs)。CLI-first设计的深层含义：终端本身是次要的，真正的设计选择是先定义命令模型——稳定的操作集、输入、结果和失败状态，可支持CLI、GUI、API或代理工具[&#91;23&#93;](#refs)。MCP vs CLI的争论中，Unix管道惯例经过50+年硬化，每个边界情况都被发现和修复，LLM从训练数据中内化了这些模式[&#91;24&#93;](#refs)。

## Unix哲学与容器化

### Kubernetes的模块化设计

Kubernetes拥抱Unix哲学的"做好一件事"，其模块化架构将功能分解为专门化组件，通过API通信[&#91;7&#93;](#refs)。如同Unix工具（grep搜索、sed编辑），K8s将架构划分为：API Server（控制平面网关）、Controller Manager（不同资源的多个控制器）、kubelet（管理每个节点上的Pod生命周期）、Scheduler（分配Pod到节点）[&#91;7&#93;](#refs)。kube-scheduler的唯一工作是确定节点分配——它不管理网络、存储或控制循环，这种隔离允许调度器独立演进或替换而不影响其他组件[&#91;7&#93;](#refs)。

### CRI/CNI/CSI接口：Unix通用接口的容器化版本

K8s的可插拔接口体系是Unix通用接口原则的直接体现。用户可以选择不同的网络插件（Calico、Flannel）、通过CSI接入存储提供商、使用自定义调度器[&#91;7&#93;](#refs)。CRI（Container Runtime Interface）将容器运行时与kubelet解耦，CNI（Container Network Interface）标准化网络插件，CSI（Container Storage Interface）统一存储接入——每个接口做好一件事，组件通过标准接口协同工作[&#91;7&#93;](#refs)。

### Kubernetes：新Unix还是新Multics？

HN讨论提出了一个深刻的问题：K8s是我们这一代的Multics，等待更简单的类Unix替代品？还是K8s本身就是新Unix？[&#91;25&#93;](#refs)。从"许多小组件各做好一件事"的角度看，K8s甚至比Unix更Unix——K8s中几乎所有东西都是特定资源类型的控制器[&#91;25&#93;](#refs)。但Docker将许多关注点混为一体：元数据、仓库、客户端、运行时、cgroups管理器、网络层、编排器[&#91;25&#93;](#refs)。K8s的核心设计围绕少量核心思想：控制器循环、Pod、电平触发事件、完全开放且标准化的声明式RESTful API[&#91;25&#93;](#refs)。挑战在于：监控和排查多个独立组件是复杂的，每个组件有自己的日志和配置，需要集中监控（Prometheus/Grafana）和日志聚合[&#91;7&#93;](#refs)。这种张力——模块化组件符合Unix哲学但整体复杂度接近Multics式的过度工程——正是K8s同时体现Unix哲学延续与超越的核心悖论。

## Unix哲学的批评与局限性

### systemd争议：Unix哲学的最大现实挑战

systemd是Unix哲学在当代面临的最突出挑战。systemd不仅是init系统——它管理服务、日志（journald）、网络（networkd）、DNS（resolved）、时间同步（timesyncd）和登录会话（logind）[&#91;26&#93;](#refs)。批评者称之为范围蔓延，违反"做好一件事"；支持者称之为正确方向的集成。两者都对——这正是令人沮丧之处[&#91;26&#93;](#refs)。systemd的并行服务启动是真正的突破，相比SysV init通常有70-80%的启动时间改善；Unit文件比init脚本更可读、声明式、无隐藏状态[&#91;26&#93;](#refs)。但journald以二进制格式存储日志，无法grep或cat——当journald本身故障时，你无法用标准文本工具诊断，诊断故障所需的工具正是造成故障的系统[&#91;26&#93;](#refs)。2026年仍有15个活跃维护的Linux发行版坚持不使用systemd[&#91;27&#93;](#refs)。

### 松耦合迷思

自1970年代以来就有"魔法模块化"的承诺——可复用的乐高积木。但大多数领域本质上是相互关联的，几乎所有切分点都是竞争需求的妥协[&#91;16&#93;](#refs)。要么集中协调，要么花人力清理重复和不一致——没有免费的午餐。智能模块化需要软件工程经验和领域理解的双重积累[&#91;16&#93;](#refs)。

### 文本流的限制

Kernighan和Pike的DOTADIW原则在实践中遇到瓶颈：Unix程序只能通过文本流单向通信，该模型从未成功迁移到桌面OS[&#91;28&#93;](#refs)。对于前端，模型完全失败——用户想要集成体验。Obsidian的解决方案是成为"多细胞生物"：每个部分是独立的专门化单元，整体实现Kernighan和Pike意图的涌现行为[&#91;28&#93;](#refs)。

### 非程序员排斥

HN讨论引用Unix-Haters Handbook的观点：Unix最灾难性的失败是假设每个人都想成为程序员。使Unix强大的互操作性和组合性以非程序员完全无法理解的方式实现——不透明的文档、零标准化的命令选项、荒谬的命令名称选择使Unix对用户极度不友好[&#91;29&#93;](#refs)。Brian Will更激进地提出：Unix userland需要根本性重新设计——用内核级依赖管理替代共享文件系统，用请求-响应机制替代环境变量和全局配置[&#91;30&#93;](#refs)。

## Unix哲学在现代的相关性

### AI代理与文件抽象的延续

arXiv论文系统追踪了Unix的"一切皆文件"设计哲学如何从1970年代操作系统延伸到现代AI代理系统[&#91;18&#93;](#refs)。文件抽象提供了通用句柄——无论是从磁盘、键盘读取还是与另一个进程通信，都使用相同的系统调用。这使得组合成为可能：程序使用相同约定读写文件描述符，输出可以馈入其他程序的输入[&#91;18&#93;](#refs)。对于AI代理，文件系统优势提供了熟悉的、可组合的接口，代理可以用少量操作（list、read、write、search、execute）操控[&#91;18&#93;](#refs)。统一策略是：将多样化接口折叠为统一抽象，接受一些专业化损失以换取组合性和可处理性。Anthropic的多代理研究系统严重依赖类文件记忆抽象；AIGNE框架提出代理文件系统，将异构资源挂载到统一命名空间[&#91;18&#93;](#refs)。

### 2026年的体现

一篇2026年的文章指出：当年三大技术趋势——AI代理、微服务架构和homelab运动——都是Unix哲学在新领域的表达[&#91;9&#93;](#refs)。在生产中有效的AI代理框架围绕可组合的、单一用途的组件通过标准接口连接来设计；失败的框架试图构建做一切事情的单体系统——与1980年代单体Unix替代品失败的原因相同[&#91;9&#93;](#refs)。Vercel的实践验证了这一点：模型越来越聪明，上下文窗口越来越大，也许最好的代理架构就是几乎没有架构——回归Unix基本要素：文件系统、shell、进程、命令行[&#91;20&#93;](#refs)。grep已经50岁了，仍然做着我们需要的事——我们曾为Unix已经解决的问题构建自定义工具[&#91;20&#93;](#refs)。

### 文本作为通用接口的持久价值

文本输出优于二进制不是因为效率——文本并不更高效——而是因为文本是每个其他程序已经知道如何读取的接口[&#91;9&#93;](#refs)。文本是使组合成为可能的最低公共分母[&#91;31&#93;](#refs)。Unix文化的教诲是：将每个中间产物视为你可能想要检查、保存、diff或重用的东西——这种假设强制纪律，而纪律可以扩展[&#91;3&#93;](#refs)。Unix哲学之所以持续有效，不是因为它关于Unix——而是关于管理由你无法完全控制的部件构建的系统中的复杂性[&#91;1&#93;](#refs)。

## 参考文献


<a id="refs"></a>

- [1] [The Unix Philosophy - From Bell Labs to everywhere (★★☆☆ Tier 2)](https://unixphilosophy.com/)
- [2] [Unix philosophy - Wikipedia (★★☆☆ Tier 2)](https://en.wikipedia.org/wiki/unix_philosophy)
- [3] [Ancient Tools from Unix: Writing, Thinking, and Composability (★☆☆☆ Tier 3)](https://medium.com/@christopher.brew/ancient-tools-from-unix-writing-thinking-and-composability-97cd9ba20fc0)
- [4] [Basics of the Unix Philosophy - The Art of Unix Programming (★★☆☆ Tier 2)](http://catb.org/~esr/writings/taoup/html/ch01s06.html)
- [5] [Coming back to the UNIX Philosophy, again and again (★☆☆☆ Tier 3)](https://medium.com/@johannesboyne/coming-back-to-the-unix-philosophy-again-and-again-f5f9c99583a6)
- [6] [On The Design of an easy-to-maintain, fast, reliable and clean CI/CD Pipeline (★☆☆☆ Tier 3)](https://medium.com/@hatamabolghasemi/on-the-design-of-an-easy-to-maintain-fast-reliable-and-clean-ci-cd-pipeline-0ad7b26b0b0b)
- [7] [How Kubernetes Embraces the Unix Philosophy (★☆☆☆ Tier 3)](https://medium.com/@rahulbansod519/how-kubernetes-embraces-the-unix-philosophy-building-a-powerful-system-with-small-mighty-parts-5bce5a979923)
- [8] [The Pipe-to-LLM Pattern: How Unix Philosophy Meets AI on the Command Line (★☆☆☆ Tier 3)](https://medium.com/code-factory-berlin/the-pipe-to-llm-pattern-how-unix-philosophy-meets-ai-on-the-command-line-7ab4a67beded)
- [9] [Unix Was Designed in 1969. It Is Still Winning Arguments in 2026. (★☆☆☆ Tier 3)](https://medium.com/@ayeshha2398/unix-was-designed-in-1969-it-is-still-winning-arguments-in-2026-26ee87eed684)
- [10] [Doug McIlroy, The Unix Philosophy (★☆☆☆ Tier 3)](https://medium.com/programming-philosophy/doug-mcilroy-the-unix-philosophy-676e7bb89800)
- [11] [Unix and Microservice Platforms - Code the Perimeter (★☆☆☆ Tier 3)](https://medium.com/@brandondbloom/unix-and-microservice-platforms-5c2831c482a4)
- [12] [How does the Unix Philosophy matter in modern times? (☆☆☆☆ Tier 4)](https://reddit.com/r/linux/comments/mjmfd1/how_does_the_unix_philosophy_matter_in_modern)
- [13] [Unix philosophy = do one thing well - Hacker News (☆☆☆☆ Tier 4)](https://news.ycombinator.com/item?id=14416176)
- [14] [The Architectural Implications of Microservices in the Cloud (★★★☆ Tier 1)](https://arxiv.org/abs/1805.10351)
- [15] [Microservices: a Language-based Approach (★★★☆ Tier 1)](https://arxiv.org/abs/1704.08073)
- [16] [Microservices and the myth of loose coupling (☆☆☆☆ Tier 4)](https://reddit.com/r/programming/comments/qhhfxd/microservices_and_the_myth_of_loose_coupling)
- [17] [Unpopular opinion: CI/CD engines are an awful idea (☆☆☆☆ Tier 4)](https://reddit.com/r/devops/comments/10t0xqj/unpopular_opinion_cicd_engines_are_an_awful_idea)
- [18] [From 'Everything is a File' to 'Files Are All You Need': How Unix Philosophy Informs the Design of Agentic AI Systems (★★★☆ Tier 1)](https://arxiv.org/abs/2601.11672)
- [19] [Interpretable Context Methodology: Folder Structure as Agent Architecture (★★★☆ Tier 1)](https://arxiv.org/html/2603.16021v2)
- [20] [The Key to Agentic Success? BASH Is All You Need (★☆☆☆ Tier 3)](https://thenewstack.io/the-key-to-agentic-success-let-unix-bash-lead-the-way)
- [21] [Writing CLI Tools That AI Agents Actually Want to Use (☆☆☆☆ Tier 4)](https://dev.to/uenyioha/writing-cli-tools-that-ai-agents-actually-want-to-use-39no)
- [22] [How To Write Great CLI Applications That Age Well (★☆☆☆ Tier 3)](https://medium.com/@pthapa1/on-writing-great-cli-applications-that-age-well-ed8bedbbe82c)
- [23] [Why I Design CLI-first Software (★☆☆☆ Tier 3)](https://medium.com/@saehwanpark/why-i-design-cli-first-software-ef1171c023b9)
- [24] [MCP vs. CLI for AI agents: When to Use Each (☆☆☆☆ Tier 4)](https://manveerc.substack.com/p/mcp-vs-cli-ai-agents)
- [25] [Kubernetes is our generation's Multics - Hacker News (☆☆☆☆ Tier 4)](https://news.ycombinator.com/item?id=27903720)
- [26] [systemd Is Either the Best or Worst Thing to Happen to Linux (★☆☆☆ Tier 3)](https://medium.com/@kp9810113/systemd-is-either-the-best-or-worst-thing-to-happen-to-linux-there-is-no-middle-ground-d3e176e0aa6f)
- [27] [One Program Controls How 90% of Linux Machines Boot (★☆☆☆ Tier 3)](https://canartuc.medium.com/one-program-controls-how-90-of-linux-machines-boot-3f1504fc7f1d)
- [28] [Kernighan and Pike were right: Do one thing, and do it well (★☆☆☆ Tier 3)](https://medium.com/source-and-buggy/do-one-thing-and-do-it-well-886b11a5d21)
- [29] [The Collapse of the Unix Philosophy - Hacker News Discussion (☆☆☆☆ Tier 4)](https://news.ycombinator.com/item?id=13777077)
- [30] [Unix Userland should be replaced (★☆☆☆ Tier 3)](https://medium.com/@brianwill/unix-userland-should-be-replaced-5605fe47cac0)
- [31] [The Case for Composable Notations - UNIX Already Showed Us the Way (★☆☆☆ Tier 3)](https://programmingsimplicity.substack.com/p/the-case-for-composable-notations-f31)
