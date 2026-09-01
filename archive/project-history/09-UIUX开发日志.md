# ResearchPath UI/UX 当前实现快照

> 状态日期：2026-08-02。本文记录活动前端，不把已删除组件、设计稿或资产包写成现有能力。

## 信息架构

顶层流程已经从固定“问卷研究四步”改为研究范式驱动：

| 范式 | 当前步骤 |
| --- | --- |
| 横截面问卷 | 数据与测量 → 问卷实证分析 → 条件过程/SEM → 方法与功效 |
| 纵向面板 | 数据与测量 → 纵向分析 → 方法与功效 |
| 日记 / ESM | 数据与测量 → 日记分析 → 方法与功效 |
| 实验与准实验 | 数据与测量 → 实验设计与功效 |

`ResearchParadigmSwitcher` 负责范式选择，`App.tsx` 负责生成步骤和切换后的默认落点。功效分析允许无活动数据集进入，避免把研究规划错误地放到数据分析末尾。

结构与计划现在也进入同一条可审计路径：结构角色先由服务端运行画像，再保存为不可变版本；随机/准实验至少声明 group 或 treatment，质量警告必须填写覆盖理由。规划工作台可以编辑研究问题、estimand、主分析、变量角色、构念、稳健性路线和功效参数，保存为 revision，冻结后再映射到真实数据。规划工作台按需加载，不把规划代码压入首屏。

顶部步骤状态栏右侧提供紧凑的“清空工作台”操作。该操作先显示确认说明，只退出当前数据与测量上下文并返回导入页，不删除本机已经保存的数据版本；移动端收敛为图标按钮。

## 实证配置体验

`EmpiricalAnalysisConfig` 提供引导和专家两种模式：

- 引导模式先询问研究问题，再推荐方法、说明推荐理由并显示配置完整度；
- 专家模式保留按基础、测量、回归、纵向和日记组织的直接配置；
- 高级参数默认不抢占首屏，未满足前置条件时给出具体检查项；
- 结果页签只根据当前结果 bundle 中的真实 segment 开放。
- 回归、响应面、纵向、日记和 SEM 的变量组统一使用配置卡片、紧凑图例与响应式表单，不再直接暴露浏览器原生 `fieldset` 外观。

这套编排降低新用户的术语扫描成本，同时不压缩专家用户的直接控制能力。

## PROCESS 5.0 模型画布

模板入口按研究问题分组，不再把 14 个常用快捷模板平铺成按钮墙。快捷模板与自定义模式初始化时默认呈现空槽位节点（如“拖入 X 变量进行绑定”），不强制预填数据变量。用户可以从空白画布或空骨架模板自由构建 X、最多十个 M、Y、W、Z、控制变量和调节目标路径：

- **空槽位骨架**：快捷模板和自定义模式生成未绑定变量的占位节点，由用户自变量库拖入目标节点完成绑定；
- **拖入空白自由连线**：拖入画布空白处放置独立未连线节点，不自动触发角色推断或自动添加回归边；
- **右键上下文菜单**：在画布节点上点击右键浮层菜单，支持一键更改节点角色（X / M / Y / W / Z / 控制变量）以及“🗑 从画布移除该变量”；
- **调节智能连线**：从调节节点（W/Z）拖出 Handle 连向目标节点时，自动检测目标节点上的回归入边并转换为 Moderation 指向；
- **撤销/重做历史栈**：内置不可变 `useModelHistory` 快照栈，支持按钮与 `Ctrl+Z` / `Ctrl+Y` 热键还原画布操作；
- **拖拽智能磁贴辅助线**：节点拖拽时自动计算中心坐标，距离 $\le 8px$ 时弹出对齐虚线并进行像素级吸附。

画布验证由服务端返回并拆成三种可区分状态：

1. 结构无效：说明节点、路径或调节目标错误；
2. 结构有效且命中 PROCESS 5.0 目录：显示模型编号和名称；
3. 结构有效但未命中编号：显示自定义模型。

当前目录的 55 个编号均可反向识别并运行；界面明确区分“55 个编号可运行”和“14 个快捷模板”。合法自定义模型仍可保存、冻结和导出设计，但运行按钮保持关闭，不把未编号结构伪装成 PROCESS 模型。

## 结果可视化

高级方法结果已从单一通用表扩展为按证据类型呈现：

- MICE：有逐次迭代链值时显示链图；
- 功效：有样本量/功效点时显示敏感性曲线；
- Bifactor：显示实际返回的模型级指标；
- IRT/DIF：显示实际返回的题目区分度和 DIF 效应。

任何专属图都只消费后端结果字段。没有足够数据时展示解释性空状态，不补造轨迹、曲线或结论。图、表、文字和导出继续引用同一结果 bundle。

数据质量卡片同样只显示当前质量运行返回的数值；质量运行不生成未经预注册的单一总分，尚未运行时显示“尚未运行”和破折号，不再把横截面数据渲染成固定的纵向留存率或重测 ICC。上游上下文变化后，草稿失效提示会列出变更来源、受影响对象、历史可用性和下一步动作。

## 示例数据

- 横截面问卷示例：260 人，三构念各 3 个 Likert 题项，包含平衡分组、年龄协变量、少量可审计缺失和预设的中介信号；
- 经典连续变量中介示例：260 人；
- 纵向面板示例：240 人、5 个波次；
- 日记与密集 ESM 示例继续采用 80 人 × 10 天和 30 人 × 25 次测量，保留多层研究需要的“个体 × 时点”结构。

生成器使用固定随机种子；自动测试检查样本规模、分组平衡、量表范围、缺失率和预设相关信号。

## 视觉与交互规范

- 主导航、模型状态和主要操作统一使用中文；英文保留给方法名、统计符号和 APA 输出语境；
- 功能图标采用同一套线性/SVG 语言，避免 Emoji、文本符号和正式图标混用；
- 长任务 ID 在主界面使用短标识，完整值保留在详情与复制操作；
- 状态徽章只保留对当前决策有用的信息，窄屏转为可换行或分层布局；
- 画布支持侧栏折叠、专注视图和布局复位；密集表格使用可滚动容器及吸顶表头；
- 焦点、键盘操作、错误说明、加载态和空状态均作为正式交互状态处理。

## 已移除或不再宣称

- 已删除、未接线的 SEM Modal 不属于当前产品入口；
- `RobustnessComparisonView.tsx` 已删除，不再宣称存在独立 FDR/Bonferroni 稳健性矩阵；
- 固定 Mock 纵向泳道、ESM 轨迹和高级方法示例图不进入正式结果链路；
- 历史资产包和旧 UI 日志不能作为当前可达性的证据。

## 验证基线

最近一次 Release 门禁（2026-08-02）通过：

- API 471 passed、1 skipped，combined line/branch coverage 80.0876%；
- Web 36 个测试文件、91 个测试；
- Playwright 1 个核心 E2E（1/1 通过）；
- R `testthat`、7 组数值金标准、生产构建与 bundle budget 通过；首屏 gzip 93.2 KiB，最大异步块 gzip 88.7 KiB。

本文只描述截至该时点的实现；Release 证明核心 E2E、生产构建和发布门禁通过，第 10 号规格中的八条真实业务路径另已完成逐条业务验收。后续状态以活动代码、测试、`project.manifest.json` 和最新 Harness 输出为准。

---

## 2026-08-06 UI/UX 审美与体验深度优化记录

基于 Canva Design Review (7-Lens) 评估框架与现代 Web 审美标准，对系统的视觉审美、极客暗色模式、图形画布微交互及学术数据表进行了全量重构与优化：

1. **设计 Token 与动画微交互** (`tokens.css`):
   - 引入贝塞尔微动画 Token `--ease-out-spring: cubic-bezier(0.16, 1, 0.3, 1)` 与 `--transition-fast`，提升全站按钮、卡片 hover 悬浮与面板微交互弹性质感。
   - 暗色模式（Dark Mode）对比度升级：提高 `--text-muted`（提升至 `#a1b2c6`）与 `--border-card`（`#3d4e66`），严格满足 WCAG AA（对比度 > 4.5:1）无障碍标准。
   - 引入柔和绿边发光 Token `--shadow-glow`，用于节点与选定控件的平滑外发光。

2. **PROCESS 5.0 模型画布微交互与无障碍标示** (`ModelCanvas.tsx`, `ModelNodeCard.tsx`, `model-builder.css`):
   - 节点选中状态：新增 `#10b981` 柔和绿边发光与 1.02× 动态放大，鼠标悬停时增加 -2px 向上浮起反馈。
   - 角色无障碍辅助标记：节点 Role Badge 注入 `[X]`、`[M]`、`[Y]`、`[W]`、`[Cov]` 文本符号与缩写，消除了单靠色彩区分的盲区。

3. **学术结果数据表 APA 7th 样式重构** (`components.css`, `ResultPanel.tsx`):
   - 引入规范的 `.apa-table` 样式组，使 `ResultPanel` 中的 `.result-table` 统一应用 APA 第七版标准三线表（Top line, Header separator, Bottom line）排版与 `tabular-nums` 数值等宽对齐。
   - 暗色模式下的角色 Badge 采用半透明暗调高亮，消除刺眼感。

4. **研究配置顶部栏响应式优化** (`layout.css`):
   - `.study-context-groups` 重构为弹性自适应网格 (`repeat(auto-fit, minmax(260px, 1fr))`)，解决中等屏幕（1280px）下单选文本与说明文字重叠挤压问题。

5. **全量测试与验证**:
   - `scripts/check-architecture.ps1` 架构无违规校验通过；
   - Web 单元测试 37 个测试文件、101 个测试点 100% 全量通过 (`npm run test:web`)；
   - Production Vite 构建通过（`npm run build:web`，345 个模块编译正常）。

---

## 2026-08-06 理论模型画布撤销/重做与智能对齐磁贴重构记录

针对理论模型自由构建与学术分析交互体验，完成了第二阶段全量重构：

1. **画布操作撤销 / 重做不可变历史栈 (`useModelHistory.ts`, `ModelBuilderToolbar.tsx`, `ModelBuilder.tsx`)**:
   - 设计并实现了轻量级不可变状态历史 Hook `useModelHistory`，保持最近 25 步 `ModelSpec` 的快照记录。
   - 工具栏新增 `↩ 撤销` 与 `↪ 重做` 操作按钮，绑定 `canUndo` / `canRedo` 动态置灰反馈，并接入全局键盘快捷键 `Ctrl+Z` 与 `Ctrl+Y`。

2. **拖拽智能磁贴与像素级对齐辅助线 (`ModelCanvas.tsx`, `model-builder.css`)**:
   - 节点拖拽 `onNodeDrag` 实时计算几何中心点与边界，在距离其他节点 $\le 8px$ 时生成 `.canvas-alignment-guide` 水平/垂直对齐虚线并完成物理吸附。

3. **交互式 Johnson-Neyman 探针与多维置信区间展示 (`JohnsonNeymanPlot.tsx`)**:
   - 条件效应曲线悬浮互动：光标移动时插值计算临近调节变量 $W$ 取值、效应估值及 95% 置信区间，弹出悬浮卡片 (`jn-probe-tooltip`)。

4. **架构解耦与单文件行数硬门禁治理 (`ModelBuilderSidebar.tsx`)**:
   - 将 `ModelBuilder.tsx` 侧边栏抽离降解为独立的 `ModelBuilderSidebar.tsx` 组件，使 `ModelBuilder.tsx` 的手写代码行数严格控制在 **738 行**（小于 `scripts/check-architecture.ps1` 规定的 800 行硬上限）。

5. **验证基线**:
   - 架构门禁 `scripts/check-architecture.ps1` 校验通过；
   - 包含 OpenAPI 契约、TypeScript 5.8 严格类型检查 (`typecheck:web`) 与 Biome Lint (`lint:web`) 的 `scripts/harness.ps1 -Mode Quick` 100% 零错误全绿通过 (`The command exited with code 0`)。

6. **画布缩放百分比徽章与 Shift 框选多节点交互增量** (`ModelCanvas.tsx`, `model-builder.css`):
   - **缩放百分比数值徽章 (`ZoomScaleBadge`)**：实时监听 `useViewport` 的 `zoom` 缩放倍率，在 ReactFlow 控制面板旁渲染动态 `🔍 100%` 徽章，点击调用 `zoomTo(1)` 平滑复位至 100% 标准缩放。
   - **Shift 拖拽框选多节点 (`selectionMode={SelectionMode.Partial}`)**：配置按住 `Shift` 键触发多节点选区框选，支持批量选中多中介/多调节节点并完成整体平移排列。

7. **工具栏按钮组隔离、高清吸附虚线发光与 JN 探针毛玻璃动画** (`ModelBuilderToolbar.tsx`, `model-builder.css`, `JohnsonNeymanPlot.tsx`):
   - **工具栏功能区隔离 (`.toolbar-divider`)**：在历史记录控制与视图切换按钮之间插入细分居中线，并在激活状态应用深翡翠绿渐变 (`linear-gradient(135deg, #173f35 0%, #0d5c46 100%)`) 与发光阴影。
   - **吸附导线高清发光**：优化 `.canvas-alignment-guide` 对齐虚线，在暗色模式下应用 `#38bdf8` 蓝色发光与点阵高清度。
   - **JN 探针毛玻璃动画**：为 `JohnsonNeymanPlot` 探针卡片注入 `backdropFilter: blur(10px)`、`pointerEvents: none` 防抖与平滑淡入淡出动画。

---

## 2026-08-06 全站视觉精致化、Toast通知系统、App.tsx架构解耦与画布计算流微动效重构记录

基于全站 UI/UX 深度评估与代码架构治理要求，完成了 4 大核心关键优化：

1. **无阻塞毛玻璃 Toast 通知系统与全站原生 alert() / Emoji 替换 (`Toast.tsx`, `Icons.tsx`, `ResultPanel.tsx`, `DataWorkspace.tsx`, `components.css`)**:
   - 彻底废除浏览器原生 `alert()` 阻塞性白底框，引入支持全局事件派发的毛玻璃 Toast 浮层 Notification 机制 (`showToast(message, type)`)，具备平滑 Slide-in 动画与轻量级反馈。
   - 建立矢量 SVG Icon 库 (`Icons.tsx`)，收拢全站 `🔍`、`🩺`、`📝` 等原生 Emoji 渲染，消除 Windows/macOS 系统间黑边与渲染样式差异。

2. **App.tsx 巨型组件解耦与工作区状态抽离 (`useWorkspaceState.ts`, `App.tsx`)**:
   - 提取 `useWorkspaceState.ts` 专用 Hook，集中封装 LocalStorage 状态同步、数据/测量版本水合、`saveStudyContext` 乐观锁并发保存队列及 `Ctrl+K` / `Ctrl+1..4` 快捷键机制。
   - `App.tsx` 手写代码行数从 600+ 行大幅缩减至 260 行纯粹 Layout 声明壳，彻底消除 Mega-Component 风险。

3. **ReactFlow 画布计算流动微动效 (`ModelCanvas.tsx`, `model-builder.css`)**:
   - 当分析处于运行状态（`analysisStatus === 'running'`）时，为路径边（包含统计路径、调节路径及控制变量边）赋予柔和高亮 Glowing (`#2563eb` / `#f59e0b`)、动态 `stroke-dasharray` 虚线流动动画（`edge-dash` @ 0.55s - 0.6s linear infinite）与 SVG `animateMotion` 沿着路径流动的粒子光斑，显著提升计算过程中的能量流视觉沉浸感。

4. **验证基线**:
   - 架构门禁 `scripts/check-architecture.ps1` 校验通过；
   - 包含 TypeScript 5.8 严格类型检查 (`typecheck:web`) 与 Biome Lint (`lint:web`) 的 `scripts/harness.ps1 -Mode Quick` 100% 零警告零错误全绿通过。


