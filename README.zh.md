# Sextant

**一个让你在 AI 编码的不确定海域里判断自己在哪的工程心智框架**

[English](README.md)

---

## Sextant 是什么

六分仪（sextant）是古代航海家用来在茫茫大海上判断自己位置的精密仪器——通过测量天体和地平线之间的角度，对照已知参考点，反推船此刻究竟在什么位置。它的存在不是为了让船跑得更快，而是让船长在每一个判断关头知道自己到底在哪。

Sextant 做的是同一件事，但用在 AI 编码上。

模型生成的代码看起来都对，测试全绿，一切都显得正常。但你不知道自己有没有偏航——不知道这个方案是不是过度抽象，不知道实现是不是偏离了原始规格，不知道自己是不是在为想象中的未来需求付代价。

**Sextant 不是让 AI 更聪明的工具，也不是让你写得更快的工具。它是让你在每一个关键节点知道自己是不是还在正确航向上的工具。**

## 为什么需要 Sextant？

当前 AI 编码工具的生成能力已经很强，但工程心智是缺失的。四个真实痛点：

1. **没有项目整体观。** 每个任务被当成孤岛处理。模型不知道当前功能在项目里的位置、和已有部分的关系、是否与别处重复。结果是命名漂移、功能重叠、架构矛盾。

2. **过度工程化。** 模型默认向"更完整的工程实践"滑坡：抽象层增加、文件数增加、接口数增加、未来扩展点增加。单点看合理，整体看失控。

3. **自写自测的盲区。** 同一个心智流既出规格、又定方案、又写实现、再给自己验证，得到的是"自洽"，不是"独立验证"。

4. **上下文失忆。** 新会话不记得项目演变到哪、前几个任务做了什么、为什么要这么设计、哪些失败路径已经试过。

## 如何工作

Sextant 把工程心智外化为运行时协议：

### 5 个角色

| 角色         | 职责                                                  |
| ------------ | ----------------------------------------------------- |
| **spec**     | 把模糊需求收成可执行规格，确认边界与不做什么          |
| **planner**  | 给出最小可行方案，优先 boring default，避免一次性扩面 |
| **builder**  | 按规格与方案实施，不私自扩需求                        |
| **reviewer** | Reduction-Review：找可删除内容、复杂度气味与验证盲区  |
| **rca**      | 失败归因——仅在失效、返工、事故后出场                  |

> Reviewer 的核心契约：输出必须包含 `deletion_proposals` 字段。即使没有可删项，也必须显式写 `none`。Reviewer 是对抗者，不是审批者。

### 5 个阶段

**Spec → Plan → Build → Verify → Record**

Verify 是阶段，不是角色。验证由确定性工具栈（tests / types / lint / hooks）和 reviewer 审 diff 共同承担。

### 3 档任务分级

- **L0** — 文案修改、小样式修复、低风险小 bug
- **L1** — 新增页面、一个 API、小范围模块改造
- **L2** — 数据模型变更、架构迁移、权限/支付/同步机制修改

分级遵循"只升不降"原则，支持 `--force-l0/l1/l2` 手动覆盖。

### 知识系统

4 类知识对象，各有明确的失效时机：

| 文件                       | 失效时机           |
| -------------------------- | ------------------ |
| `SEXTANT.md`               | 当前技术约束变了   |
| `modules/*/EVOLUTION.md`   | 模块历史路径变了   |
| `PROJECT_EVOLUTION_LOG.md` | 项目级长期决策更新 |
| `hook-registry.json`       | 规则本身变了       |

**原则**：只保留会改变当前工程判断的内容，不做档案馆。

## 设计原则

1. **验证密度集中在最小产物上。** 花在规格层的每个 token 能阻止下游几十倍的错误代码。
2. **对抗结构 > 模型数量。** 真正的对抗来自上下文隔离 + 职责隔离 + 输出契约隔离，和模型品牌无关。
3. **能用确定性逻辑就别用 LLM。** 分级判定、工具门控优先确定性实现，LLM 只在需要真正判断时出场。
4. **验证独立性来自"看产物，不看推理"。** Reviewer 只接收上游的结构化产物，不接收推理过程或中间草稿。
5. **每层机制都必须可退役。** Sextant 服务于 2026 年的能力缺口，每层机制可独立关闭，随模型进步单独退出。

## 快速上手（Claude Code）

**前提：** Claude Code CLI 或桌面版。

```sh
# 1. 克隆 Sextant
git clone https://github.com/SaoNian/Sextant

# 2. 在你的项目里初始化知识文件
cd Sextant
./scripts/bootstrap.sh --target /path/to/your-project

# 3. 安装 Claude Code adapter
./adapters/claude-code/install.sh --project --path /path/to/your-project

# 4. 把 Sextant 指令追加到项目 CLAUDE.md
cat adapters/claude-code/CLAUDE.md.snippet >> /path/to/your-project/CLAUDE.md
```

在 Claude Code 中使用：

```
/sextant-spec     # 定义任务范围和验收标准
/sextant-plan     # 给出最小可行实现方案
/sextant-build    # 在批准方案内实施
/sextant-verify   # 跑工具链 + 对抗审查
/sextant-record   # 写回知识，关闭任务
```

## 当前状态

**v0.0.1** — Core 文本层与 Claude Code adapter 已完成。

- `core/roles/` — 5 个角色 prompt（reviewer / spec / planner / builder / rca）
- `core/templates/` — 5 套输出模板
- `core/rules/` — 任务分级、阶段门控、回退规则
- `core/knowledge/` — 4 类知识文件初始化模板
- `adapters/claude-code/` — subagent、slash command、hook 示例、安装脚本
- `scripts/bootstrap.sh` — 知识布局初始化脚本

generic CLI 与 Trace 系统计划在 v0.2 实现。完整路线图见 [roadmap](docs/roadmap.md)。

## 许可证

MIT
