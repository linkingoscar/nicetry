# OB/CB 扩展平台资产包

## 状态

`partially-restored`：资产包整体仍不是可直接启用的平台，只有清单登记的聚焦切片进入默认前端导航、FastAPI 路由、R 入口、OpenAPI 契约和日常测试。

> 本资产包 `docs/` 子目录保留的是归档时点的旧文档树与内部索引，链接指向当时仓库路径，不保证当前有效；当前文档体系以 `docs/` 为准，历史档案入口见 `archive/README.md`。

截至2026-07-29，已按明确需求恢复七个聚焦切片：

- `cluster-aggregation-diagnostics`：ICC(1)、ICC(2)、设计效应和rwg(j)；
- `longitudinal-panel`：CLPM、RI-CLPM、LCM-SR、纵向等值性、ULMC敏感性和专用Monte Carlo功效；
- `daily-diary-multilevel`：日记/ESM LMM、广义/零值GLMM、交叉分类、观测变量Bayesian DSEM、多层中介、二层插补和专用功效。
- `experimental-design-workbench`：factorial ANOVA、ANCOVA、受限重复测量/混合设计和 cluster-robust Gaussian GLM；
- `general-power-precision-workbench`：回归、t 检验、ANOVA 的通用功效、精度、MDES 和 Monte Carlo；
- `general-multiple-imputation-workbench`：类型感知 MICE、不可变插补集、逐份拟合与 Rubin 合并；
- `advanced-questionnaire-measurement-workbench`：ESEM、Bifactor、GRM IRT 和 DIF。

当前活动路径和输出以仓库根目录`project.manifest.json.restoredAssetSlices`为准。本目录中的原始helper、runner、UI和测试继续作为历史资产保留；已恢复切片不代表整个高级多层、纵向或动态SEM family均已恢复。

## 活动与休眠边界

- 只有`project.manifest.json.restoredAssetSlices[*].activePaths`列出的执行、契约、配置和结果消费者属于当前产品；
- 纵向面板与日记/ESM使用独立结果页签，均从已持久化实证报告的`longitudinal`片段读取真实结果；
- 正式结果区不允许渲染固定示例、随机轨迹或Mock参与者；机器记录中的`prototypeDataAllowed=false`是该边界；
- 资产包内或活动源码中没有消费者的界面文件不构成可达能力，也不能作为完成证据；
- 新恢复切片必须同时声明专用入口、真实结果来源和失败/未配置状态，不能仅迁回组件文件。
- 高级方法工作台只展示 registry 同时声明 family 与 slice 均可执行的四组能力；资产中的通用多层和纵向 family 仍不接受活动请求。

## 保存内容

- 高级实验、LMM、纵向、MI、功效和高级测量的 Python/R runner；
- 高级分析 React UI、前端 API 和类型；
- 研究协议/预注册入口；
- AdvancedAnalysisSpec/AdvancedResultBundle；
- 高级方法测试、公开数据夹具和历史开发蓝图；
- 收口前的 README 与立项总览快照。

目录尽量保留原仓库相对结构，例如原
`apps/api/app/services/advanced_runner.py` 当前位于
`apps/api/app/services/advanced_runner.py` 的资产包镜像路径下。

## 恢复步骤

1. 从明确研究需求确定 family 和最小 slice。
2. 只迁回该 slice 所需的 contract、runner、R helper、route 和 UI。
3. 恢复 `ApiServices`/`main.py` 的任务管理器接线及 `ROUTERS`。
4. 恢复对应 schema，并运行 `scripts/generate-contracts.ps1`。
5. 把所需测试迁回活动测试目录，修复与当前核心契约的漂移。
6. 更新 `project.manifest.json` 和核心范围文档。
7. 运行专项测试、Quick 和 Full。

不要整包直接覆盖当前源码；资产形成于扩展阶段，与当前核心可能已经发生契约漂移。

本包内部文档保留归档时的路径和交叉引用，其中部分 `docs/...` 链接已随活动文档收束而失效。这些引用是历史快照的一部分，不应批量改写；当前入口以仓库根目录 `docs/README.md` 和 `project.manifest.json` 为准。
