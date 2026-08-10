# Cross-Cutting Principles

Principles that apply across multiple skills, discovered during observation.

---

## Active Principles

### 1. CLI 命令必须开箱可执行

**Added:** 2026-08-07
**Applies to:** all skills with CLI commands
**Requirement:** Skill 文档中的命令必须以文档所在环境可直接执行的方式给出。模块不在默认 import 路径时（如 `-m scripts.cli` 而 scripts 包在 skill 子目录），文档必须写明 PYTHONPATH 等环境变量配置，且示例须在目标平台（含 Windows PowerShell）验证过。
**Propagation:** immediate
**Status:** active

### 2. 验证标记不得扭曲作者选材

**Added:** 2026-08-07
**Applies to:** all skills with verification/marker mechanisms
**Requirement:** 验证标记（如 †/‡）是来源属性标注，不是质量惩罚。若作者为规避标记而丢弃有信息量的来源（如 Tier 3/4 张力来源），标记机制失败。技能文档应显式说明：标记是数据注解，保留多样化来源并按 tier 措辞呈现。
**Propagation:** immediate
**Status:** active

### 3. 收敛判据应区分理论最优与领域可达

**Added:** 2026-08-07
**Applies to:** all research/verification skills with tier thresholds
**Requirement:** 固定 tier 阈值（如"每个 DQ ≥1 个 Tier 1-2 来源"）对不存在高 tier 来源的新兴领域会制造虚假失败感或诱导降低质量。技能应区分理论最优阈值与实际可达阈值，并对"该领域为何缺高 tier 来源"给出说明惯例。
**Propagation:** opportunistic
**Status:** active

---


