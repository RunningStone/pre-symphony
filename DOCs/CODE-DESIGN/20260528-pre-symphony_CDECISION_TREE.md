# pre-symphony 架构决策(CDECISION_TREE)

Last updated: 2026-05-28 · 关联:[CPLAN](20260528-pre-symphony_CPLAN.md) / [CCHECKER](20260528-pre-symphony_CCHECKER.md)

> 代码侧的决策记录(ADR 风格),是项目级 [DECISION_TREE](../PLAN/20260528-pre-symphony_DECISION_TREE.md) 在架构层的对应物。每条:选项 / 取舍 / **现选** / 重审条件。技术不确定、需实测的归 DP(项目 DECISION_TREE);此处是**当下可定的架构取舍**。

---

## CD-1 图的表示

- 选项:(a) `networkx`;(b) 手写 dict 邻接表 + 拓扑/环检测。
- 取舍:networkx 省事但加依赖;本图规模小(几十节点),手写可控、零依赖、易序列化。
- **现选**:(b) 手写,封装在 `build_graph` / `plan_stages`。
- 重审:若需复杂图算法(最短路、社区发现)再引 networkx。

## CD-2 状态/产物格式

- 选项:(a) 多个 JSON 文件(`plan_graph.json`/`issues.json`/`linear_map.json`);(b) SQLite。
- 取舍:JSON 可读、可 git diff、契合 NFR5 可观测;SQLite 利于并发/查询但不可读、与单 Agent 串行不匹配。
- **现选**:(a) JSON 文件。
- 重审:多 Agent 并行(§9.B.5)落地、并发写状态时再考虑 SQLite/锁。

## CD-3 Linear 访问机制(关联 DP1)

- 选项:(a) 全部经 `linear-cli`(含 `linear api` 透传 GraphQL);(b) create/query 用 CLI,关系/state/label 用自带 `httpx` GraphQL;(c) 完全自带 GraphQL 客户端。
- 取舍:(a) 复用 CLI 的 auth/keyring 最省;(c) 最可控但要自管 auth,且违背"用 submodule 保证访问"的初衷。
- **现选**:**待 DP1 实测**;默认倾向 (a),不足则退 (b)。`linear_client` 接口对上层屏蔽此差异。
- 重审:DP1 结论落定即固化。

## CD-4 node_id hash 设计(落实 G9 / §9.A.3)

- 选项:(a) hash 全节点内容;(b) hash 稳定子集;(c) LLM 显式 id。
- 取舍:(a) 正文一改就漂、误判新 issue;(c) 引入幻觉(已被用户否决);(b) 折中。
- **现选**:(b) `sha256(spec_anchor + "\n" + kind + "\n" + role_key)[:12]`,**正文/标题不进 hash**;`role_key` 为节点在其 milestone 内的稳定角色标识。
- 重审:DP2 若判 🟡/🔴,加模糊匹配或半显式 slug。

## CD-5 幂等标记(双保险)

- 选项:(a) 只靠本地 `linear_map.json`;(b) 只靠 issue 描述里的隐藏标记;(c) 两者都用。
- 取舍:本地 map 可能丢/不同步;描述标记随 issue 走、最可靠但需查询解析。
- **现选**:(c) 描述内 `<!-- pre-symphony:node=<hash> -->` 为权威,`linear_map.json` 为加速缓存;reconcile 时以标记回收、用 map 提速。
- 重审:Linear 描述不支持隐藏注释时改用专用 label/自定义字段。

## CD-6 可视化工具

- 选项:(a) Mermaid;(b) Graphviz(dot)。
- 取舍:Mermaid 文本内联、GitHub/IDE 原生渲染、契合"GUI 辅助/降认知负担";Graphviz 排版强但需外部二进制。
- **现选**:(a) Mermaid 为主,`to_mermaid` 输出;Graphviz 作可选导出。
- 重审:大图(>50 节点)Mermaid 排版差时补 Graphviz。

## CD-7 linear-cli 调用方式

- 选项:(a) subprocess 调 Deno 二进制;(b) 复刻其 GraphQL 逻辑。
- 取舍:它是 Deno/TS,不能直接 import 进 Python;subprocess 最直接。
- **现选**:(a) `linear_client` 用 subprocess + JSON 解析(`--json`)。
- 重审:见 CD-3(若转自带 GraphQL,则 subprocess 仅保留交互便利)。

---

## 决策记录模板
```
- 日期:YYYY-MM-DD
- 决策点:CD-x
- 背景/触发:
- 现选 → 改为:
- 影响(CPLAN 哪些模块/接口需改):
```
