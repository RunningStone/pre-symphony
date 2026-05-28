# pre-symphony 决策树(DECISION_TREE)

Last updated: 2026-05-28 · 关联:[PLAN](20260528-pre-symphony_PLAN.md) / [CHECKER](20260528-pre-symphony_CHECKER.md)

> 本文件记录**只能靠动手验证才能定**的项目级岔路。每个决策点给三档结果区间与对应 PIVOT。架构层面的取舍见 [CDECISION_TREE](../CODE-DESIGN/20260528-pre-symphony_CDECISION_TREE.md)。

---

## DP1 — linear-cli 的 `api` 子命令能否覆盖关系 / state / label?(M3 关口)

`linear issue create` / `milestone create` / `issue query` 已确认可用;但 `blockedBy` 关系、初始 state(Backlog/Todo)、label、priority 是否能通过 `linear api`(原始 GraphQL)完成,需实测。

| 档 | 结果 | PIVOT |
|---|---|---|
| 🟢 乐观 | `linear api` 能跑任意 mutation(`issueRelationCreate`/`issueUpdate`/`issueLabelCreate`) | 全部经 linear-cli,无需自带 client。`linear_client` 只是薄封装 |
| 🟡 中等 | 部分能(如能 create issue 但关系/state 要拼 GraphQL,且 auth 可复用) | `linear_client` 内置一组固定 GraphQL 文档,经 `linear api` 透传执行 |
| 🔴 悲观 | `linear api` 受限(无法透传任意 mutation 或 auth 不可复用) | 自带最小 GraphQL HTTP 客户端(`httpx` + `LINEAR_API_KEY`),linear-cli 仅用于交互/查询便利 |

**决策记录**:2026-05-28 / 依据:linear-cli `src/commands/api.ts` 确认 `linear api '<query>' --variables-json <json>` 可执行任意 GraphQL(含 mutation),并复用 CLI auth(`LINEAR_API_KEY`/`.linear.toml`/`auth login`)/ **选档:🟢(机制已确认)** / PIVOT:全部经 `linear api`,`linear_client` 仅薄封装,不自带 GraphQL HTTP 客户端 / 影响:`pre_symphony/linear_client.py` 已按此实现。**遗留:GraphQL 字段名(IssueCreateInput 等)待真实 creds 的集成测试校验**(`tests/integration/`,gated)。

---

## DP2 — hash 幂等键稳定性

hash 覆盖「SPEC 锚点 + 节点角色」。问题:实际 PLAN 迭代中,节点正文/标题改动是否频繁导致 hash 漂移、误判为新 issue?

| 档 | 结果 | PIVOT |
|---|---|---|
| 🟢 乐观 | 稳定子集足够,迭代中 hash 不漂 | 维持纯 hash 方案 |
| 🟡 中等 | 偶有漂移 | reconcile 时加**模糊匹配**(标题相似度 + 同 milestone)兜底,命中则 update 而非新建 |
| 🔴 悲观 | 漂移频繁,误建严重 | 引入半显式键:PLAN 节点带可选 `slug`,缺省回退 hash(违反"纯自动"初衷,需用户复核) |

**决策记录**:_(待填)_

---

## DP3 — 上游 PLAN 输入契约的松紧

契约太松 → 建图歧义、决策节点/依赖识别不准;太紧 → 上游 agent 难产出、增加幻觉。

| 档 | 结果 | PIVOT |
|---|---|---|
| 🟢 乐观 | 轻量 markdown 约定(标题层级 + 少量标记)即可稳定建图 | 维持轻契约,靠 `validate` 兜底 |
| 🟡 中等 | 需要结构化块(front-matter / 显式依赖列表) | 契约升级为半结构化,提供模板给上游 |
| 🔴 悲观 | 自由 markdown 无法可靠建图 | 在 pre-symphony 内置一个「PLAN 规整」LLM 前处理步骤,把自由 PLAN 先normalize |

**决策记录**:_(待填)_

---

## 决策组合 → 实现路线

- (DP1🟢, DP2🟢, DP3🟢)→ 最轻实现:薄 linear-cli 封装 + 纯 hash + 轻契约。
- 任一转 🔴 → 触发对应 PIVOT,更新 PLAN 预估(M3 上浮)与 CPLAN 相应模块。

## 决策记录模板
```
- 日期:YYYY-MM-DD
- 决策点:DPx
- 实测/依据:
- 选档:🟢/🟡/🔴
- 采取的 PIVOT:
- 影响(PLAN/CPLAN 哪些项需改):
```
