# ResearchPath UX / IA PRD 收口验收

> 状态日期：2026-09-04  
> 范围：`ResearchPath_UX_IA_Reorganization_PRD_v1.0` 的 Phase 0–7。  
> 原则：只记录活动代码可证明的实现；自动化检查不冒充真实参与者用户研究。

## 1. 收口结论

Phase 0–6 的仓库内实现已迁移到新 Data / Analyze / Output 架构；Phase 7 的视觉、响应式、键盘/屏读基础、文档同步和迁移清理已实现。当前提交是修复首轮 release-validation 静态门禁问题后的第二个最终 PRD 收口候选；只有对应最终门禁实际成功后，才能把自动化发布验收标记为通过。

唯一不能由仓库自动完成的 PRD 工作项是**真实参与者用户测试**。当前自动化覆盖任务可达性、键盘、axe、响应式和页面错误，但没有真实参与者的任务完成率、完成时间、错误率或主观量表，因此人工用户测试保持“需要外部参与者”的外部验收项。

## 2. Phase 0–7 验收矩阵

| Phase | PRD 目标 | 当前实现证据 | 状态 |
| --- | --- | --- | --- |
| 0 能力冻结 | UI 简化不丢能力 | `methodRegistry.json`、capability/method parity tests、PROCESS 55 catalog guards | 已实现 |
| 1 新应用外壳 | Data / Analyze / Output | `App.tsx`、`AppWorkspaceTabs.tsx`；旧“方法目录/路径与 SEM”不再是一级工作区 | 已实现 |
| 2 数据工作区 | Data/Variable/Scale、按需工具、局部确认 | `DataWorkspace*`、`VariableTable*`、`MeasurementWorkspace*`、DataGrid | 已实现 |
| 3 统一方法库 | 单一方法发现、方法局部守门、通用配置 | `ContextCapabilityCatalog`、method library presets、availability resolver | 已实现 |
| 4 Output / AnalysisDocument | 稳定分析对象、不可变运行、stale、复制、server/rebuild index | `AnalysisIndexService`、`AnalysisIndexRecoveryMixin`、hidden analysis-index routes、`OutputWorkspace`、server/local bridge | 已实现 |
| 5 PROCESS/SEM 表单 | 常见 PROCESS + 基础 SEM 表单，复杂模型回高级编辑 | Model 1/4/6/7/14 common forms、parallel Model 4、`SemQuickSetupForm` | 已实现 |
| 6 高级方法迁移 | 统一发现/标题/运行检查/Output，保留专用配置器 | experiment/multilevel/power/MI/measurement/longitudinal/diary method-scoped adapters | 已实现 |
| 7 视觉/A11y/发布 | 去大面积 glass、响应式、键盘/屏读、文档、发布证据、迁移清理 | `workbench.css`、`expert-model.css`、删除 `liquid-glass.css`、skip link、forced colors、PRD E2E | 实现完成；等待本候选最终门禁 |

## 3. Phase 4：最终 Output 架构

### 3.1 服务端 AnalysisIndex

`apps/api/app/services/analysis_index.py` 保存项目级 AnalysisDocument 与 AnalysisRun 的导航身份和上游版本。索引文件使用既有 atomic JSON IO，不保存统计表、系数、诊断或图。持久化 CRUD 与 job 重建职责已拆分：`AnalysisIndexService` 负责索引读写与身份约束，`analysis_index_recovery.py` 负责从经过既有身份校验的任务状态重建导航引用；两个 service 都保持在仓库 source-line ceiling 内。

### 3.2 结果真值不迁移

- empirical → 既有 empirical job/report；
- PROCESS/SEM → 既有 model job/result；
- advanced/MI → 既有 advanced job/result。

Output 选择 run 后才读取权威状态/结果。AnalysisIndex 只解决“项目中有哪些分析/运行”和刷新恢复问题。

### 3.3 可重建索引

AnalysisIndex 可遍历经过原有 path/identity 校验的 persisted model/empirical/advanced job state。浏览器 localStorage 被清除或 AnalysisIndex 缺失时，服务端仍可恢复 run reference。显式登记与重建会复用同一 run 的既有 analysisId，避免重复 AnalysisDocument；模型和高级任务的测量身份从持久化 context lineage 恢复，stale 判定不会因索引重建而放松。

## 4. Phase 5：常见 PROCESS 表单

统一方法库直接提供 Model 4 简单中介、Model 4 两中介并行中介、Model 6 两中介链式中介、Model 1 简单调节、Model 7 第一阶段调节中介、Model 14 第二阶段调节中介，以及完整 PROCESS 高级目录。进入 common form 后不再出现第二个模型选择器。

所有表单只写现有 ModelSpec 并复用 validation/freeze/run/result。Model 14 的中心化对象按真实被调节路径使用 M/W；Model 1/7 使用 X/W。基础 SEM 继续提供两构念 X→Y form-first 路径，复杂测量、多组、高阶和约束模型回到 SEM Studio。

## 5. Phase 6：高级方法迁移

ICC/rwg、两层 Gaussian LMM、实验、解析功效等高频方法使用 common form；panel/diary、Monte Carlo、MI 和高级测量保留专用配置器，但共享统一方法库、标题/运行检查和 Output。没有因 UX 迁移替换 R runner、放宽统计门禁或提高 maturity/publication eligibility。

## 6. Phase 7：视觉与可访问性

- `liquid-glass.css` 已删除；routine Data/Analyze/Output 使用 `workbench.css`，专家 PROCESS/SEM 隔离在 `expert-model.css`；
- 1366/1024/760/420px 响应式，390px 浏览器检查页面级横向溢出；
- APG Data/Analyze/Output tabs、skip link、focus-visible、reduced motion、higher contrast、Windows forced-colors；
- `tests/e2e/prd-workbench.spec.ts` 覆盖三工作区键盘、skip-link、computed backdrop-filter、axe 和 390×844 溢出。

这些是机械可用性/无障碍证据，不是用户访谈或真实任务研究。

## 7. 迁移清理

新三工作区是已有数据的唯一一级路径；旧 empirical/model/method views 只作为 Analyze 内部 surface；global `analysisReady` 不再决定能否进入 Analyze；legacy glass stylesheet 已删除；localStorage 历史索引降级为兼容缓存；旧统计 runner、旧结果和兼容草稿没有因 UI 迁移被删除。

## 8. 文档同步

根 `README.md`、`docs/00`、`docs/01`、`docs/03`、`docs/README.md` 和本验收矩阵已同步。仓库没有独立于这些源文件之外的产品官网内容生成链；若未来另有外部站点仓库，应由其自己的发布流程同步，不能在本仓库伪造已更新状态。

## 9. 最终门禁证据

### 9.1 首轮 release-validation

首轮完整 hosted quality gate 已实际执行。R lock、R numeric baselines 与 R statistical test lane 没有进入失败列表；失败集中在两个静态工程 lane：

- `python-quality`：新增 AnalysisIndex 代码使 `reportOptionalMemberAccess` 从冻结最大值 1 增至 6，并使显式 `Any` 用量从 206 增至 210；
- `web-and-contracts`：Biome 报出 2 个冗余 Hook dependency 和 4 个测试中的 forbidden non-null assertion。

这些问题已在后续 `[skip ci]` 修复提交中处理：API route 返回类型改为 `JsonObject`，recovery 逻辑使用明确非空对象窄化并拆分到独立 service，Web Hook dependency 与测试断言按现有 lint 规则修正。**没有修改 Pyright baseline、Biome 规则、统计 contract 或数值基线来让门禁变绿。**

### 9.2 当前最终候选

- Full / hosted quality gate：**由当前非 `[skip ci]` 收口提交重新触发；结果以 PR #3 当前 head 的实际 GitHub Actions 检查为准。**
- 自动化 PRD workbench E2E：**纳入上述最终质量门禁；不得在运行完成前预写通过。**
- 真实参与者用户测试：**未执行；需要外部参与者，不能由代码仓库自动补造。**
