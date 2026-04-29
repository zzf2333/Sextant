[English](README.md)

<div align="center">

<img src="logo.svg" width="120" height="120" alt="Sextant Logo"/>

<h1>Sextant</h1>

<p><strong>一个让你在 AI 编码的不确定海域里判断自己在哪的工程心智框架</strong></p>

<p>
  <a href="https://github.com/zzf2333/Sextant/stargazers"><img src="https://img.shields.io/github/stars/zzf2333/Sextant?style=flat-square&color=a855f7" alt="GitHub Stars"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-10b981?style=flat-square" alt="License MIT"/></a>
  <img src="https://img.shields.io/badge/version-0.0.8-3b82f6?style=flat-square" alt="v0.0.8"/>
  <img src="https://img.shields.io/badge/Claude%20Code-adapter%20ready-f97316?style=flat-square" alt="Claude Code"/>
</p>

</div>

---

六分仪不能让船跑得更快——它让船长在每一个判断关头知道自己到底在哪。没有它，你只能凭感觉航行。

Sextant 做的是同一件事，但用在 AI 编码上。

模型生成的代码看起来都对，测试全绿，一切都显得正常。但你不知道自己有没有偏航——不知道这个方案是不是过度抽象，不知道实现是不是偏离了原始规格，不知道自己是不是在为想象中的未来需求付代价。

**Sextant 不是让 AI 更聪明的工具，也不是让你写得更快的工具。它是让你在每一个关键节点知道自己是不是还在正确航向上的工具。**

---

## 问题所在

你正在用 Claude Code 做一个功能。脑子里过了一遍规格，让 AI 去实现，测试通过，代码看起来很干净。三天后：

- 第二个 AI 会话重新引入了你早就否定过的抽象
- 实现比计划多了三个文件
- 审查者（精力耗尽的你）通过了一个解决了错误问题的 diff

这不是模型能力的问题。Claude、GPT、Gemini——它们都足够聪明。它们缺的是**嵌入工作流的工程心智**。

四个真实失败模式：

| 失败模式           | 实际发生了什么                                                                             |
| ------------------ | ------------------------------------------------------------------------------------------ |
| **没有项目整体观** | 每个会话把任务当孤岛处理。命名漂移、功能重叠、架构矛盾在静默中积累。                       |
| **过度工程化**     | 模型向"更完整的工程实践"滑坡：抽象层增加、文件数增加、扩展点增加。单点看合理，整体看失控。 |
| **自写自测的盲区** | 同一个心智流既出规格、又定方案、又写实现、再给自己验证。得到的是自洽，不是独立验证。       |
| **上下文失忆**     | 新会话不记得项目演变到哪、前几个任务做了什么、为什么要这么设计、哪些路径已经试过。         |

![Sextant 架构](docs/diagrams/01-architecture.png)

---

## 如何工作

Sextant 把工程心智外化为运行时协议：五个上下文隔离的角色、五个阶段、一套只保留"会改变当前工程判断的内容"的知识系统。

### 5 个角色

![角色交互](docs/diagrams/03-roles.png)

| 角色         | 职责                                                | 核心契约                                                                     |
| ------------ | --------------------------------------------------- | ---------------------------------------------------------------------------- |
| **spec**     | 把模糊需求收成可执行规格，明确边界与验收标准        | 输出：scope、constraints、ambiguities、acceptance criteria、open_decisions   |
| **planner**  | 给出最小可行方案，优先 boring default，避免过度构建 | 生成 1-2 个候选方案，选最经济路径，声明完整工程足迹                          |
| **builder**  | 按规格与方案实施，不私自扩需求                      | 发现 scope creep 时标记而非提交；完成前运行 hook-registry 检查               |
| **reviewer** | **Reduction-Review**——对抗者，不是审批者            | `deletion_proposals` 是强制字段。没有可删项时显式写 none。看产物，不看推理。 |
| **rca**      | 失败归因                                            | 仅在确认的失败、返工事件或事故后出场——不做预防性分析                         |

> reviewer 在**三个独立会话**中出场：spec 后、plan 后、build 后。每次都是全新的对抗上下文，只接收上游的结构化产物，绝不接收产物背后的推理过程。

### 5 个阶段

![工作流程](docs/diagrams/02-workflow.png)

**Spec → Plan → Build → Verify → Record**

Verify 是阶段，不是角色。由确定性工具栈（tests / types / lint / hooks）和 reviewer 审 diff 共同承担——不是由写代码的同一个 agent 承担。

### 3 档任务分级

任务在开始时分级，遵循"只升不降"原则：

| 级别                | 触发条件                                   | 要求流程                      |
| ------------------- | ------------------------------------------ | ----------------------------- |
| **L0** — 微任务     | 文案修改、小样式修复、低风险小 bug         | 本地验证 + 记录               |
| **L1** — 普通任务   | 新增页面、一个 API、小范围模块改造         | 完整 5 阶段流程               |
| **L2** — 高风险任务 | 数据模型变更、权限/支付/同步机制、架构迁移 | 严格 reviewer 介入 + 回退思考 |

支持 `--force-l0`、`--force-l1`、`--force-l2` 手动覆盖。

### 知识系统

四类知识文件住在你的项目里，随代码一起版本化。每类都有明确的失效时机——它不是档案馆：

| 文件                                 | 失效时机           | 内容                               |
| ------------------------------------ | ------------------ | ---------------------------------- |
| `.sextant/SEXTANT.md`                | 技术约束变了       | 当前技术栈、明确不做什么、默认偏好 |
| `modules/*/EVOLUTION.md`             | 模块历史路径变了   | 设计决策、被否定的路径、接受的权衡 |
| `.sextant/PROJECT_EVOLUTION_LOG.md`  | 项目级长期决策更新 | 跨模块选择、架构权衡               |
| `.sextant/hook-registry.json`        | 规则本身变了       | 可机械检测的护栏、确定性门控       |

**原则**：只保留会改变当前工程判断的内容。不做档案馆。

---

## 设计原则

1. **验证密度集中在最小产物上。** 花在规格层的每个 token 能阻止下游几十倍的错误代码。验证规格，不是实现。

2. **对抗结构 > 模型数量。** 真正的对抗来自上下文隔离 + 职责隔离 + 输出契约隔离，和模型品牌无关。

3. **能用确定性逻辑就别用 LLM。** 任务分级、工具门控、状态流转：优先确定性实现。LLM 只在确实需要判断时出场。

4. **验证独立性来自"看产物，不看推理"。** Reviewer 只接收上游的结构化产物，不接收推理过程或中间草稿。

5. **每层机制都必须可退役。** Sextant 服务于 2026 年的能力缺口。每层机制可独立关闭，随模型进步单独退出。这是健康，不是失败。

---

## 快速上手（Claude Code）

**前提：** Claude Code CLI 或桌面版。

```sh
# 克隆 Sextant
git clone https://github.com/zzf2333/Sextant
cd Sextant

# 一键安装：agents、commands、知识文件、CLAUDE.md snippet
./adapters/claude-code/install.sh --project --path /path/to/your-project
```

然后在 Claude Code 里启动第一个任务：

```
/sextant "描述你要做的事情"
```

就这样。`/sextant` 会自动运行 Spec、Plan、Build、Verify 和 Record——只在真正需要你做决定的时候暂停。正常的 L1 任务三次 `/sextant` 即可跑完完整流程。

需要逐阶段显式控制，或处理 L2 任务（数据模型、权限、支付）时：

```
/sextant-spec     # 定义任务范围和验收标准
/sextant-plan     # 给出最小可行实现方案
/sextant-build    # 在批准方案内实施
/sextant-verify   # 跑工具链 + 对抗审查
/sextant-record   # 写回知识，关闭任务
/sextant-status   # 查看当前阶段、阻塞点和下一步操作
/sextant-init     # 接入已有项目 — 检测技术栈并生成知识文件
```

每次 `record` 会更新项目知识文件（`.sextant/SEXTANT.md`、`EVOLUTION.md`、`.sextant/hook-registry.json`）；
下一个任务的 `spec` 会加载这些文件——这就是防止跨会话上下文失忆的知识循环。

详细步骤见 `docs/quickstart.md`。

---

## 当前状态

**当前版本：v0.0.8** — token/time 用量统计与知识目录打磨版本。

**下一版本：v0.1.0 Dogfood Gate** — 验证 Claude Code adapter 的真实闭环。代码侧
trace contract、lint 检查、指标门槛和 dogfood 报告模板已经就位；发布前必须满足
`docs/dogfood.md` 里的真实证据门槛：至少 10 个真实任务、闭环率 >= 80%、
reviewer 非空删除建议率 >= 50%、Verify 首次通过率 >= 60%、主动绕过率 <= 20%。

| 组件                    | 状态                                                                                      |
| ----------------------- | ----------------------------------------------------------------------------------------- |
| `core/roles/`           | 5 个角色 prompt（reviewer / spec / planner / builder / rca）                              |
| `core/templates/`       | 5 套结构化输出模板                                                                        |
| `core/rules/`           | 任务分级、阶段门控、回退规则                                                              |
| `core/knowledge/`       | 4 类知识文件初始化模板                                                                    |
| `adapters/claude-code/` | `/sextant` 主命令、5 个阶段命令、`/sextant-status`、`/sextant-init`、hooks（advisory/team/strict）、一键安装 |
| `scripts/bootstrap.sh`  | 知识布局初始化脚本                                                                        |

通用 LLM CLI 暂不进入 v0.1.0；等 Claude Code 闭环用真实 traces 证明后，再进入 v0.2。

---

## 许可证

MIT
