# "机器学习 → 强化学习" 完整学习路径

```
Stage 0          Stage 1           Stage 2            Stage 3           Stage 4
前置基础    →    ML基础       →    核心RL        →    深度RL       →    前沿方向
─────────────────────────────────────────────────────────────────────────────────
数学基础          监督学习          Bandits           函数近似           Model-Based RL
  线性代数        无监督学习        MDPs              DQN系列            Offline RL
  概率统计        深度学习          动态规划          策略梯度            Multi-Agent RL
  微积分          (MLP/CNN/         蒙特卡洛          Actor-Critic       RLHF/DPO/GRPO
  最优化           BP/Adam)         时序差分           PPO/SAC/TD3        Safe RL
编程基础                           Q-Learning                           RLVR
  Python/NumPy                     规划与整合                            Sim2Real
  PyTorch
```

---

## Stage 0: 前置基础（4-12周）

| 主题 | 为何RL需要 | 推荐资源 |
|---|---|---|
| **线性代数** | V(s)=wᵀφ(s)、策略梯度、神经网络权重 | 3Blue1Brown《线性代数的本质》(YouTube, 免费) |
| **概率统计** | Bandits、MC回报、随机策略、奖励分布 | Khan Academy 概率统计(免费) |
| **微积分** | 策略梯度定理、反向传播 | 3Blue1Brown《微积分的本质》(YouTube, 免费) |
| **最优化** | PPO/TRPO信赖域、约束RL | Boyd《Convex Optimization》(免费PDF) |
| **Python/NumPy/PyTorch** | 所有主流RL库的底层 | PyTorch官方教程; Karpathy《NN: Zero to Hero》(YouTube, 免费) |

---

## Stage 1: ML基础（4-8周）

| 主题 | 为何RL需要 | 推荐资源 |
|---|---|---|
| **监督学习** | 函数近似、奖励模型、SFT | Andrew Ng《ML Specialization》(Coursera, 免费旁听) |
| **深度学习** | DQN/策略网络/Actor-Critic的骨架 | Géron《Hands-On ML》3rd ed.; fast.ai(免费) |

---

## Stage 2: 核心RL（6-12周）— 按顺序学

**主线教材：Sutton & Barto《RL: An Introduction》2nd ed. (2018, 免费PDF)**

```
Ch.1-2  Bandits（探索vs利用，ε-greedy，UCB）
   ↓
Ch.3-4  MDPs + 动态规划（Bellman方程，策略/值迭代，GPI）
   ↓
Ch.5    蒙特卡洛方法（MC预测/控制，重要性采样）
   ↓
Ch.6-7  时序差分学习（TD(0), SARSA, Q-Learning, n-step）
   ↓
Ch.8    规划与整合（Dyna-Q）
```

**配套课程：** David Silver RL Course (UCL/DeepMind, YouTube免费) 或 UAlberta RL Specialization (Coursera)

---

## Stage 3: 深度RL（8-16周）

```
函数近似（S&B Ch.9-10，致命三要素）
   ↓
DQN系列（经验回放→目标网络→Double→Dueling→Rainbow）
   ↓
策略梯度（REINFORCE→方差缩减→优势函数）
   ↓
Actor-Critic（A2C/A3C）
   ↓
PPO / SAC / TD3（生产级算法）
```

**推荐课程：** Sergey Levine CS285 (Berkeley, YouTube免费) 或 Chelsea Finn CS224R (Stanford)

**实践项目递进：**

1. 从零实现 Tabular Q-Learning (Gridworld)
2. DQN on CartPole/LunarLander
3. PPO on MuJoCo — 先手写再对比 Stable-Baselines3
4. SAC on HalfCheetah

---

## Stage 4: 前沿方向（按兴趣选）

| 方向 | 核心内容 | 关键资源 |
|---|---|---|
| **Model-Based RL** | 世界模型、MCTS、AlphaZero/MuZero、DreamerV3 | Silver et al. 2017; Hafner et al. 2023 |
| **Offline RL** | 分布偏移、CQL、IQL、Decision Transformer | Levine et al. 2020 tutorial |
| **Multi-Agent RL** | CTDE、MADDPG、QMIX、MAPPO | Albrecht et al. 2024 教科书(免费PDF) |
| **RL for LLMs** | RLHF→DPO→GRPO→RLVR | Lambert《RLHF Book》(免费); HuggingFace TRL; DeepLearning.AI GRPO课程(2025) |
| **Safe RL** | 约束MDP、Sim2Real、鲁棒RL | Robust-Gymnasium (ICLR 2025) |

---

## 推荐课程

| 课程 | 讲师 | 级别 | 侧重 | 访问 |
|---|---|---|---|---|
| **RL Specialization** (4门) | Martha White, Adam White (UAlberta) | 入门-中级 | 表格RL→函数近似→完整RL系统 | Coursera (免费旁听) |
| **CS234: RL** (Stanford, 2026) | Emma Brunskill | 中级 | MDP到深度RL，理论+实践 | Stanford online |
| **CS285: Deep RL** (Berkeley, 2026) | Sergey Levine | 中级-高级 | 深度RL、策略梯度、Model-Based、Offline RL | YouTube免费 |
| **CS224R: Deep RL** (Stanford, 2025/2026) | Chelsea Finn | 中级-高级 | 机器人/LLM方向；模仿学习、Offline、Meta-RL | 课程网站 |
| **David Silver RL Course** (UCL/DeepMind) | David Silver | 入门-中级 | 经典RL基础 | YouTube免费 |
| **Hugging Face Deep RL Course** (v2.0) | Thomas Simonini | 入门-中级 | 动手实践：Q-learning→DQN→PPO→多智能体 | 免费在线 |
| **DeepLearning.AI: GRPO微调LLM** | Travis Addair, Arnav Garg | 中级 | GRPO用于LLM推理 | 免费限时 |

---

## 推荐书籍

| 书 | 作者 | 年份 | 侧重 | 访问 |
|---|---|---|---|---|
| **RL: An Introduction** (2nd ed.) | Sutton & Barto | 2018 | RL"圣经"；表格方法到策略梯度 | 免费PDF |
| **A Course in RL** (2nd ed.) | Bertsekas | 2026 | DP视角；rollout、策略迭代、AlphaZero | 作者网站PDF |
| **Multi-Agent RL: Foundations and Modern Approaches** | Albrecht et al. | 2024 | MARL综合教科书 | MIT Press; 免费PDF |
| **RLHF Book** | Nathan Lambert | 2024 | RLHF、DPO、偏好学习、LLM对齐 | 免费在线: rlhfbook.com |
| **Deep RL** | Aske Plaat | 2022 | DRL算法、MCTS、AlphaZero架构 | Springer |

---

## 关键论文

### 奠基
- Bellman (1957) — *Dynamic Programming*
- Watkins (1989) — *Learning from Delayed Rewards* (Q-Learning)

### 深度RL突破
- Mnih et al. (2015) — *DQN* (Nature)
- Silver et al. (2016) — *AlphaGo*
- Schulman et al. (2017) — *PPO*
- Haarnoja et al. (2018) — *SAC*

### Model-Based
- Hafner et al. (2023) — *DreamerV3*
- Schrittwieser et al. (2020) — *MuZero*

### Offline RL
- Kumar et al. (2020) — *CQL*
- Kostrikov et al. (2022) — *IQL*

### RL for LLMs
- Ouyang et al. (2022) — *InstructGPT / RLHF*
- Rafailov et al. (2023) — *DPO*
- Shao et al. (2024) — *GRPO* (DeepSeekMath)
- DeepSeek-AI (2025) — *DeepSeek-R1* (RLVR at scale)

---

## 实践环境

| 环境 | 描述 | 适合 |
|---|---|---|
| **Gymnasium** (Farama) | OpenAI Gym继任者；标准RL API | 表格方法、DQN、PPO (CartPole, LunarLander) |
| **Atari (ALE)** | 街机游戏环境 | DQN, Rainbow, 视觉RL |
| **MuJoCo / DM Control** | 连续控制 | SAC, TD3, PPO, Model-Based RL |
| **PettingZoo** | 多智能体环境 | MARL算法 |
| **MiniGrid** | 网格世界导航 | 探索、分层RL |
| **D4RL** | 标准化Offline RL数据集 | Offline RL基准 |
| **Robust-Gymnasium** | 扰动鲁棒性测试 | 鲁棒RL研究 |

---

## 学习方法建议

1. **每学一个算法，从零实现一次** — 不用框架，只用NumPy/PyTorch，这是区分"懂了"和"会了"的关键
2. **Sutton & Barto 每章做习题** — 尤其是Ch.2-7的编程练习
3. **用 Gymnasium 做实验** — CartPole→LunarLander→MuJoCo 递进
4. **读论文前先看课程视频** — CS285/CS224R 的 lecture notes 比原论文更易入门
5. **加入社区** — HuggingFace Deep RL Course 有 Discord 和排行榜，可以对比自己的实现

---

## 时间估算

| 阶段 | 时长 | 内容 |
|---|---|---|
| **0** — 前置基础 | 4-12周 | 数学 + Python/NumPy/PyTorch |
| **1** — ML基础 | 4-8周 | 监督/无监督学习、深度学习 |
| **2** — 核心RL | 6-12周 | Bandits→MDPs→DP→MC→TD→Q-Learning (S&B Ch.1-8) |
| **3** — 深度RL | 8-16周 | 函数近似→DQN→策略梯度→Actor-Critic→PPO/SAC/TD3 |
| **4** — 前沿 | 持续 | Model-Based、Offline、MARL、RLHF/GRPO、Safe RL |

**Stage 0-3 达到工作熟练度：约 6-12个月（每周10小时）**
