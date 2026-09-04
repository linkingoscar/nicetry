# ResearchPath UX / IA PRD 收口验收

> 状态日期：2026-09-04  
> 范围：`ResearchPath_UX_IA_Reorganization_PRD_v1.0` 的 Phase 0–7。  
> 原则：只记录活动代码可证明的实现；自动化检查不冒充真实参与者用户研究。

## 1. 收口结论

Phase 0–6 的仓库内实现已迁移到新 Data / Analyze / Output 架构；Phase 7 的视觉、响应式、键盘/屏读基础、文档同步和迁移清理已实现。最终质量门禁在本文件后续 `最终门禁证据` 节记录；门禁未通过前，不把当前分支称为发布完成。

唯一不能由仓库自动完成的 PRD 工作项是**真实参与者用户测试**。当前自动化覆盖任务可达性、键盘、axe、响应式和页面错误，但没有真实参与者的任务完成率、完成时间、错误率或主观量表，因此人工用户测试保持“需要外部参与者”的发布验收项。

## 2. Phase 0–7 验收矩阵

| Phase | PRD 目标 | 当前实现证据 | 状态 |
| --- | --- | --- | --- |
| 0 能力冻结 | UI 简化不丢能力 | `methodRegistry.json`、capability/method parity tests、PROCESS 55 catalog guards | 已实现 |
| 1 新应用外壳 | Data / Analyze / Output | `App.tsx`、`AppWorkspaceTabs.tsx`；旧“方法目录/路径与 SEM”不再是一级工作区 | 已实现 |
| 2 数据工作区 | Data/Variable/Scale、按需工具、局部确认 | `DataWorkspace*`、`VariableTable*`、`MeasurementWorkspace*`、DataGrid | 已实现 |
| 3 统一方法库 | 单一方法发现、方法局部守门、通用配置 | `ContextCapabilityCatalog`、method library presets、availability resolver | 已实现 |
| 4 Output / AnalysisDocument | 稳定分析对象、不可变运行、stale、复制、server/rebuild index | `AnalysisIndexService`、hidden analysis-index routes、`OutputWorkspace`、server/local bridge | 已实现 |
| 5 PROCESS/SEM 表单 | 常见 PROCESS + 基础 SEM 表单，复杂模型回高级编辑 | Model 1/4/6/7/14 common forms、parallel Model 4、`SemQuickSetupForm` | 已实现 |
| 6 高级方法迁移 | 统一发现/标题/运行检查/Output，保留专用配置器 | experiment/multilevel/power/MI/measurement/longitudinal/diary method-scoped adapters | 已实现 |
| 7 视觉/A11y/发布 | 去大面积 glass、响应式、键盘/屏读、文档、发布证据、迁移清理 | `workbench.css`、`expert-model.css`、删除 `liquid-glass.css`、skip link、forced colors、E2E | 实现完成，最终门禁待记录 |

## 3. Phase 4：最终 Output 架构

### 3.1 服务端 AnalysisIndex

`apps/api/app/services/analysis_index.py` 保存项目级：

- AnalysisDocument：标题、方法、来源、数据/测量身份、草稿引用、latest/primary run、pinned/archived；
- AnalysisRun：runId、analysisId、方法、来源、上游版本、状态和可选 result/report/model identity。

索引文件使用既有 atomic JSON IO。它不保存统计表、系数、诊断或图。

### 3.2 结果真值不迁移

- empirical → 既有 empirical job/report；
- PROCESS/SEM → 既有 model job/result；
- advanced/MI → 既有 advanced job/result。

Output 选择 run 后才读取权威状态/结果。AnalysisIndex 仅解决“项目中有哪些分析/运行”和刷新恢复问题。

### 3.3 可重建索引

AnalysisIndex 可遍历经过原有 path/identity 校验的 persisted model/empirical/advanced job state。浏览器 localStorage 被清除或 AnalysisIndex 缺失时，服务端仍可恢复 run reference。显式登记与重建会复用同一 run 的既有 analysisId，避免重复 AnalysisDocument。

## 4. Phase 5：常见 PROCESS 表单

统一方法库直接提供：

1. Model 4 简单中介；
2. Model 4 两中介并行中介；
3. Model 6 两中介链式中介；
4. Model 1 简单调节；
5. Model 7 第一阶段调节中介；
6. Model 14 第二阶段调节中介；
7. 完整 PROCESS 目录（高级）。

进入 common form 后不再出现第二个模型选择器。所有表单只写现有 ModelSpec 并复用 validation/freeze/run/result。Model 14 的中心化对象按真实被调节路径使用 M/W；Model 1/7 使用 X/W。

基础 SEM 继续提供两构念 X→Y form-first 路径，复杂测量、多组、高阶和约束模型回到 SEM Studio。

## 5. Phase 6：高级方法迁移

高级方法迁移的“统一”是外壳统一，而不是统计实现统一：

- ICC/rwg、两层 Gaussian LMM：common form；
- panel、diary/ESM：方法卡锁定具体模型身份；
- factorial ANOVA、ANCOVA、重复测量、混合设计：common form；cluster-robust GLM 保持 advanced；
- regression/t-test/ANOVA analytic power：common form；Monte Carlo 保持 specialist；
- MI：专用 ImputationPlan 编辑器，运行引用进入 Output；
- advanced measurement：按 reliability/EFA/CFA/invariance/ESEM/Bifactor/IRT/DIF/CMB 能力范围锁定专用配置。

没有因 UX 迁移替换 R runner、放宽统计门禁或提高 maturity/publication eligibility。

## 6. Phase 7：视觉与可访问性

### 6.1 视觉收敛

- `styles.css` 不再加载全局 glass stylesheet；
- `liquid-glass.css` 已删除；
- routine Data/Analyze/Output 使用 `workbench.css`：不透明背景、轻边框、紧凑 header、小圆角、无 backdrop blur/浮动卡片位移；
- 专家 PROCESS/SEM 的差异化样式隔离在 `expert-model.css`。

### 6.2 响应式

`workbench.css` 明确覆盖 1366、1024、760、420px；390px 浏览器验收检查页面级横向溢出。宽表格保留局部可聚焦滚动，而不是把整页撑宽。

### 6.3 键盘和屏读

- Data/Analyze/Output：APG roving tabIndex + Arrow/Home/End；
- skip link → 当前活动 tabpanel；
- 活动 tabpanel 可编程聚焦；
- links/buttons/forms/tabindex 均有 focus-visible；
- reduced motion、higher contrast、Windows forced-colors；
- 异步状态使用已有 live region/status 语义。

### 6.4 自动化可用性验收

`tests/e2e/prd-workbench.spec.ts` 覆盖：

- 三工作区语义与键盘切换；
- skip-link；
- routine Header/nav 的 computed backdrop-filter 为 `none`；
- axe WCAG A/AA critical/serious；
- 390×844 页面级横向溢出。

这属于机械可用性/无障碍证据，不是用户访谈或真实任务研究。

## 7. 迁移清理

- 新三工作区为 `App.tsx` 默认且唯一已有数据主路径；
- 旧顶层 empirical/model/method views 只作为新 Analyze 内部 surface，不再作为一级导航；
- global `analysisReady` 不再决定能否进入 Analyze；方法自身 requirements 决定运行前提；
- legacy glass stylesheet 已删除；
- localStorage 历史索引降级为兼容缓存，服务端 AnalysisIndex 为项目恢复层；
- 旧统计 runner、旧结果和兼容草稿没有因 UI 迁移被删除。

## 8. 文档同步

本批同步：

- 根 `README.md`：三工作区、统一方法库、common PROCESS forms、server OutputIndex；
- `docs/00-项目现状与产品边界.md`：活动产品边界；
- `docs/01-产品工作流与交互.md`：新的日常任务流和可访问性；
- `docs/03-系统架构与数据契约.md`：AnalysisIndex 与结果真值边界；
- 本文件：PRD Phase 0–7 验收矩阵。

## 9. 最终门禁证据

> 当前在实现提交阶段；这里不得预填“通过”。最终收口提交触发一次完整质量门禁后，把真实 run、API/Web/E2E/R/构建结果追加到本节。

- Full / hosted quality gate：**待最终收口提交**。
- 自动化 PRD workbench E2E：**待最终门禁执行**。
- 真实参与者用户测试：**未执行；需要外部参与者，不能由代码仓库自动补造**。
