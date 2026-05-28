# pre-symphony — RESUME(下次打开先读这个)

Last updated: 2026-05-28 · 仓库:github.com/RunningStone/pre-symphony(public)· 分支:main
本地:`/Users/runningstone/Documents/2026_06_02_pavo_auto_tools/PERSONAL_TOOLs/pre-symphony`

> 本文件是「续命/接力」入口:给出当前进度、已锁定决策、架构地图、怎么跑、下一步。
> 细节不复制,指向对应文件。读完这一篇 + 看一眼 PRD 即可继续。

---

## 1. 这是什么

把 coding agent 基于 SPEC 写的 **PLAN** 转成 **Symphony 友好的 Linear issue**。
背景:[Symphony](https://github.com/openai/symphony) 只「读」tracker(Linear)、自己**不建 issue**;
pre-symphony 填这段空白:`PLAN → 带约束分阶段的 DAG → 原子、带依赖的 Linear issue`,交给 Symphony 追踪执行。

数据流:`claude-code(SPEC+PLAN) → pre-symphony(本项目) → Linear → Symphony + Codex`
所属工作区:`pavo_auto_tools`(`0_organiser`=规则,`PERSONAL_TOOLs`=自研工具含本项目,`REPOs/symphony`=外部开源)。

完整需求见 **[DOCs/PRD/20260528-pre-symphony-requirements.md](PRD/20260528-pre-symphony-requirements.md)**。

---

## 2. 当前进度(一句话:M0–M4 全部实现完,只差真实 Linear 联调)

| 里程碑 | 内容 | 状态 |
|---|---|---|
| M0 | 需求 + PRD/PLAN/CPLAN 三件套 | ✅ |
| M1 | parse_plan / build_graph / validate | ✅ |
| M2 | plan_stages / synth_issues / visualize | ✅ |
| M3 | linear_client / push_linear(reconcile 幂等) | ✅ 代码完成,**实跑待 creds** |
| M4 | state_store / CLI 全流程 / SKILL.md | ✅ 本地端到端通 |

**测试**:`34 passed, 2 skipped`(unit + smoke 全绿;2 个 integration 因缺 `LINEAR_API_KEY/TEAM/PROJECT` 自动 skip)。
跑测试:`.venv/bin/python -m pytest -ra`

**唯一剩下的事**:真实 Linear 联调(见 §6)。进度勾选见
[DOCs/PLAN/20260528-pre-symphony_CHECKER.md](PLAN/20260528-pre-symphony_CHECKER.md)(M3/M4 末尾几项未勾即是)。

---

## 3. 已锁定的决策(别再纠结,改动需更新 PRD)

1. **完整图本地、只推活跃前沿**:整棵 DAG 存本地用于规划/可视化/回滚;只把「不在决策下游」的节点推到 Linear。决策节点=人工门,选定后**重跑** pre-symphony 展开被选分支,未选分支永不创建。(PRD §5.3 / §9.A.1)
2. **排序用 Todo + blockedBy**(不是 Backlog):依据 Symphony `SPEC §8.2`——Todo issue 在 blocker 未终结前不会被派发。所以推送节点都给 `Todo`,靠 `blockedBy` 自动定序。(比 PRD 初版「其余→Backlog」更优,已采用)
3. **阶段标志 = Linear milestone**,且 milestone 是**本地完整 DAG 的一等概念**,Linear milestone 只是活跃部分的投影。
4. **幂等键 = 自动 hash**:`node_id = sha256(spec_anchor + kind + role)[:12]`,**正文/标题不进 hash**;不要 LLM 写 id,依赖用 `role` 引用。(CDECISION_TREE CD-4)
5. **幂等回收双保险**:issue 描述里藏 `<!-- pre-symphony:node=<hash> -->` 标记 + 本地 `state/linear_map.json`。(CD-5)
6. **document 更新式上传**:只保留当前活跃前沿,闭合段落删除,单文档替换而非累积。(FR11)
7. **不用 MCP**:Linear 访问走 `vendor/linear-cli` 的 `linear api` 原始 GraphQL。**DP1 已定**:统一用 `linear api`(机制确认;GraphQL 字段名待实跑校验)。
8. **多 Agent 并行**:暂不做,后续。

---

## 4. 架构地图(代码在 `pre_symphony/`)

管线:`build → validate → synth → preview →(人工确认)→ push`

| 模块 | 职责 |
|---|---|
| `models.py` | PlanNode/Edge/Graph、IssueRecord、LinearMap、`compute_node_id`、序列化 |
| `parse_plan.py` | PLAN markdown → ParsedPlan(定义了输入契约) |
| `build_graph.py` | role→id 解析、建边、label 合并、重复检测 |
| `validate.py` | 无环 / 悬空边 / 缺验收·验证 / 决策缺 options(错误);粒度过大(警告) |
| `plan_stages.py` | 拓扑波次、初始状态(前沿→Todo)、活跃前沿(决策下游排除) |
| `synth_issues.py` | → IssueRecord(描述含 AC/Validation/provenance/marker),仅活跃前沿 |
| `visualize.py` | Mermaid 图 + dry-run 摘要 |
| `linear_client.py` | `CliLinearClient`:`linear api` 原始 GraphQL(create/update/relation/milestone/document/query)**(未实跑)** |
| `push_linear.py` | `reconcile` 幂等核心(create/update/skip + marker 回收)+ document upsert(**单测覆盖**) |
| `state_store.py` | 读写 `state/{plan_graph,issues,linear_map}.json` |
| `__main__.py` | CLI:build/validate/synth/preview/push(无 `--yes` 只本地预览=确认门) |

架构细节:[DOCs/CODE-DESIGN/20260528-pre-symphony_CPLAN.md](CODE-DESIGN/20260528-pre-symphony_CPLAN.md);
架构取舍 ADR:[..._CDECISION_TREE.md](CODE-DESIGN/20260528-pre-symphony_CDECISION_TREE.md);
测试设计:[..._CCHECKER.md](CODE-DESIGN/20260528-pre-symphony_CCHECKER.md)。

**PLAN 输入契约**(简版):front-matter(`spec`/`project`/`default_labels`)+ 每节点
`## [work|decision|milestone_marker] 标题 @role` 后跟一个 ```yaml 块(`milestone`/`spec_anchor`/
`priority`/`depends_on`(roles)/`labels`/`touch`/`body`/`acceptance`/`validation`/`options`)。
完整样例:`tests/fixtures/sample_plan.md`。

---

## 5. 怎么跑

```bash
cd .../PERSONAL_TOOLs/pre-symphony
git submodule update --init --recursive          # 首次:拉 vendor/linear-cli
uv venv --python 3.13 && uv pip install -e ".[dev]"
.venv/bin/python -m pytest -ra                   # 34 passed, 2 skipped

# 本地管线(不触网)
.venv/bin/python -m pre_symphony build    tests/fixtures/sample_plan.md
.venv/bin/python -m pre_symphony validate --plan tests/fixtures/sample_plan.md
.venv/bin/python -m pre_symphony synth    --plan tests/fixtures/sample_plan.md
.venv/bin/python -m pre_symphony preview  --plan tests/fixtures/sample_plan.md
.venv/bin/python -m pre_symphony push     --plan tests/fixtures/sample_plan.md   # 仅预览(确认门)
```

**凭证**:根目录有 `.env`(已 gitignore,**不在 git 里**),含 `LINEAR_API_KEY`,以及待填的
`LINEAR_TEAM_ID` / `LINEAR_PROJECT_ID`。`.env` **不会自动加载**,用前先:
```bash
set -a; source .env; set +a
```
(`linear` 二进制:`brew install schpet/tap/linear` 或 `deno install -A -g -n linear jsr:@schpet/linear-cli`)

---

## 6. 下一步(真实 Linear 联调,按顺序)

1. `set -a; source .env; set +a`
2. 只读自检:`linear api 'query { viewer { id name } }'`(确认 key 有效)
3. 查并填 `.env` 里的 id:
   `linear api 'query { teams { nodes { id key name } } }'` /
   `linear api 'query { projects { nodes { id name } } }'`
4. **校验 DP1 遗留**:首跑可能要修 `linear_client.py` 里的 GraphQL 字段名(`IssueCreateInput`、
   `issueRelationCreate` 方向、`projectMilestoneCreate`、`documentCreate`)对真实 schema 是否对。
5. 跑 integration(会从 skip 转实跑):
   `LINEAR_API_KEY=… LINEAR_TEAM_ID=… LINEAR_PROJECT_ID=… .venv/bin/python -m pytest tests/integration -q`
6. 首次真推:`python -m pre_symphony push --plan <PLAN> --yes --team <id> --project <id>`
7. 通过后:勾掉 CHECKER 里 M3/M4 剩余项,在 `DOCs/PROGRESS/` 写端到端记录。

**可选改进**(非阻塞):CLI 自动加载 `.env`(python-dotenv)、Graphviz 导出、多 Agent 并行。

---

## 7. 关键文件索引

- 需求:`DOCs/PRD/20260528-pre-symphony-requirements.md`
- 项目管理三件套:`DOCs/PLAN/20260528-pre-symphony_{PLAN,CHECKER,DECISION_TREE}.md`
- 架构三件套:`DOCs/CODE-DESIGN/20260528-pre-symphony_{CPLAN,CCHECKER,CDECISION_TREE}.md`
- 入口技能:`SKILL.md` · 样例:`tests/fixtures/sample_plan.md`
- 本文件:`DOCs/RESUME.md`(随进度更新)
