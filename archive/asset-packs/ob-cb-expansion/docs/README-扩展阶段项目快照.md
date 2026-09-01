# 研径 ResearchPath

[![CI](https://github.com/linkingoscar/nicetry/actions/workflows/ci.yml/badge.svg)](https://github.com/linkingoscar/nicetry/actions/workflows/ci.yml)
[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/release/python-3109/)
[![Node.js 24](https://img.shields.io/badge/node.js-24-green.svg)](https://nodejs.org/en/download)
[![R 4.6.1](https://img.shields.io/badge/R-4.6.1-blue.svg)](https://cran.r-project.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19-61DAFB.svg?style=flat&logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.3-blue.svg?style=flat&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-5.0-646CFF.svg?style=flat&logo=vite&logoColor=white)](https://vitejs.dev/)
[![Ruff](https://img.shields.io/badge/Ruff-treated-FF0000.svg)](https://github.com/astral-sh/ruff)
[![Biome](https://img.shields.io/badge/Biome-formatted-60A5FA.svg)](https://biomejs.dev/)
[![Pyright](https://img.shields.io/badge/Pyright-passing-43B581.svg)](https://github.com/microsoft/pyright)
[![Playwright](https://img.shields.io/badge/Playwright-1.61-2EAD33.svg?style=flat&logo=playwright&logoColor=white)](https://playwright.dev/)
[![pytest](https://img.shields.io/badge/pytest-7.4-0A9EDC.svg?style=flat&logo=pytest&logoColor=white)](https://docs.pytest.org/)

面向个人实证研究的本地可视化问卷分析工作台。项目从题项数据导入开始，经过变量确认、量表构建、模型拖拽、统计估计、结果诊断，最终生成可复现的分析记录和报告。

当前状态：面向横截面、单层 CB/OB 问卷研究的本地实证工作台。真实上传数据可完成变量确认、构念计分、描述/频数/相关、KMO/Bartlett、EFA（Varimax/Promax）、简单结构 CFA、CR/AVE、Fornell–Larcker、HTMT、稳健组间差异、分层回归，以及 Model 1/4/6/7/8/14/15。后端与前端还提供潜变量 SEM、ML+FIML、WLSMV 和多组测量等值性的已实现切片。结果可导出论文表格 Excel 或带校验清单的可复现 ZIP；研究设计、材料、完整样本治理、高级方法切片和论文级全链路仍按 OB/CB 蓝图建设，不能把“有入口”理解为全部完成。

## 当前统计口径与支持边界（2026-07）

- 连续结果方程：OLS，可选经典或 HC3 标准误；中介类效应使用固定 seed 的 percentile 或 bias-corrected（BC，非 BCa）bootstrap。
- 二分类结果方程：任意两个可识别水平会显式编码为 0/1，使用 binomial-logit；报告 z、HC3（如选择）、OR 与 OR 置信区间。拟合失败或完全/近完全分离会终止，不回退 OLS。二分类中介的乘积效应含 log-odds 尺度，只能按所列尺度解释。
- SEM：连续指标用 ML，可选真正的 FIML；有序/Likert 指标用 WLSMV（theta 参数化），其标量等值约束 thresholds。WLSMV 不提供 FIML。
- EFA：最大似然优先，支持 Varimax/Promax；Promax 输出模式矩阵、因子相关 Φ、结构矩阵和斜交共同度。平行分析默认 1,000 次并记录 seed。
- CFA：基础问卷中心保留自研的 N-scaled normal-theory ML 简单结构 CFA 对照；高级 `questionnaire_measurement` runner 已提供 lavaan 的 ML/MLR/WLSMV 正式 CFA，并按连续/有序题项显式区分估计口径。
- 组间比较：两组 Welch t + Hedges g；多组同时给出经典 ANOVA、Brown–Forsythe、Welch ANOVA、Tukey/Bonferroni/Games–Howell。
- 自动解读只陈述统计证据与限制，不自动宣称“假设成立”或因果机制成立。
- 金标准自动核对：26 个 Capability 资产包均具备真实生产 `sut/run.py`、主参考重算、动态行置换不变量和隔离突变测试。严格资格复核后不再把单参考、单场景资产表述为发布候选；当前 `power.t_test.analytic.v1` 已补齐四类场景、SciPy 与独立 mpmath 积分双参考、G3/G6、多源消解和能力级 23/23 突变证据，升为 `autoverified_l3`，其余 25 项仍为 `autoverified_l1`。容器 digest 与离线复现等证据补齐前仍不会升级为发布候选。详见[开发记录](docs/30-AI-Agent金标准自动核对基础设施开发记录.md)与[金标准规范](docs/31-AI-Agent无人工介入金标准设立与自动核对规范.md)。
- 高级入口当前按 family 与具体 slice 双层声明：实验、受限 Games–Howell、两层 Gaussian LMM、观测增长/传统 CLPM/RI-CLPM/潜增长、问卷测量高级切片、MICE 插补及冻结线性回归的 Rubin 合并、回归/组间 ANOVA 解析与有限 Monte Carlo 功效均有实际 runner；这些仍保持 `experimental`，不等同于正式方法发布。Monte Carlo 当前仅开放显式 Gaussian 回归和均衡组间 ANOVA DGP，并返回有效模拟数、失败数、MCSE、Wilson 区间与反解回代。CR2 与两层中介已具备生产统计引擎和独立 Golden 闭环，但尚未作为 Advanced API/UI 的正式支持 slice；GLMM、三层和复杂 MI pooled 模型仍保持 planned 或稳定拒绝。高级成功结果可从结果页导出含/不含数据的复现 ZIP，但这不改变实验性边界。逐项实施见[后续开发可执行手册](docs/25-后续开发可执行手册.md)，整体产品蓝图见[OB/CB 全流程能力审计及开发蓝图](docs/27-OB-CB实验与问卷实证研究全流程能力审计及开发蓝图.md)。

下文 M0–M5 为实现历史；如与当前规范冲突，以机器事实源、`00`—`11`、`18`、`24`、`27` 和当前界面/API 为准。

## 快速运行

本机使用 PowerShell 7：

```powershell
pwsh -NoLogo -NoProfile -File '.\scripts\setup.ps1'
pwsh -NoLogo -NoProfile -File '.\scripts\dev.ps1'
```

`setup.ps1` 会建立项目私有 Python/R 环境并安装前端依赖；`dev.ps1` 只监听 `127.0.0.1`，随后打开本地网页。运行全部测试：

```powershell
pwsh -NoLogo -NoProfile -File '.\scripts\test.ps1'
```

仓库入口、路由、前端 API、统计引擎、协议和治理文档的机器可读地图见 [`project.manifest.json`](project.manifest.json)；文档权威层级见[立项总览](docs/00-立项总览.md)，本轮代码—业务—文档收口结论见[仓库收口审计](docs/28-代码-业务-文档一致性与仓库收口审计.md)，OB/CB 全流程需求与 45 个工作包见[开发蓝图](docs/27-OB-CB实验与问卷实证研究全流程能力审计及开发蓝图.md)，日常治理规则见[开发债务总账与持续治理执行手册](docs/22-开发债务总账与持续治理执行手册.md)，实时状态以 capability API 与机器可读的 [`docs/debt-register.json`](docs/debt-register.json) 为准。只检查目录与依赖方向可运行 `scripts/check-architecture.ps1`；运行参考独立性防火墙检查可执行 `python scripts/check-reference-independence.py`；全量离线核对金标准包可运行 `python tools/goldens/verify.py --all`。

日常开发统一从工程 harness 进入：`scripts/harness.ps1 -Mode Quick` 用于小步反馈，`-Mode Full` 用于合并前验证，`-Mode Release` 用于依赖审计、性能基准和发布证据收口。经验与完成定义见[工程 Harness 与开发准则](docs/24-工程Harness与开发准则.md)；普通 AI 代理接手后续工作时按[后续开发可执行手册](docs/25-后续开发可执行手册.md)执行。

## M0 历史实现记录

- ModelSpec Draft 2020-12 JSON Schema 与单一中介语义校验；
- ResultBundle JSON Schema；
- React/TypeScript 模型画布和结果面板；
- FastAPI 本地 API；
- R/base `lm` 路径估计与百分位 bootstrap；
- NumPy 独立 OLS 数值对照；
- Python、前端组件、类型检查和生产构建测试；
- 项目私有 R 运行时及一键 setup/dev/test 脚本。

## M1 历史实现记录

- CSV：UTF-8/GB18030 编码和逗号/制表符/分号探测；
- XLSX：读取首个工作表并提示多工作表情况；
- SAV：保留变量标签和值标签；
- 50 MB 上传边界、文件名净化、SHA-256 和只读原件；
- SQLite DatasetVersion 元数据与 Parquet 规范化数据；
- 缺失、唯一值、范围、样本值、常量和高缺失画像；
- 连续、二分类、名义、有序、ID 和文本类型建议及推断理由；
- 人工调整和版本化字典确认；
- 前端数据工作台、原始文件来源和字典状态。

## M2 历史实现记录

- 多构念题项分组，同一题项不得跨构念重复归属；
- 人工确认理论上下限，按 `min + max - original` 反向计分；
- 有效题项均分/总分和默认 80% 最少有效题项规则；
- Cronbach's α、单因子 McDonald's ω 和完整案例数；
- 校正项目–总分相关、删题后 α/ω、题项均值、标准差、缺失与地板/天花板比例；
- 量表得分分布、转换预览、转换日志和方法边界提示；
- MeasurementVersion JSON Schema、SQLite 版本日志和不可变派生 Parquet；
- 超出理论范围或非数值题项的阻断式校验；
- 前端构念编辑器、测量报告及“可接入模型画布”交接状态。

## M3 历史实现记录

- M2 构念得分和已确认原始数值变量接入模型变量库；
- 原生拖放与下拉选择双入口分配 X、M、Y、W 和控制变量；
- React Flow 节点拖动、路径连接、删除、标签与假设编号编辑；
- 调节关系绑定具体路径，编译预检自动加入 W 主效应和乘积项；
- 控制变量逐项分配到 M、Y 或两个方程；
- Model 1、4、7、14 规范模板；
- Schema、重复 ID/变量、角色、悬空引用、循环、数据类型和模板结构校验；
- 基于派生 Parquet 的完整案例、零方差、完全共线和小样本预检；
- 650 ms 防抖草稿自动保存、稳定排序模型哈希和不可变冻结版本；
- 横截面中介等方法警告必须填写覆盖理由后才能冻结。

## M4 统计 MVP 历史核心

- 冻结 ModelVersion 才能触发真实数据分析，结果与后续草稿隔离；
- 当时的通用 R 方程编译器支持 Model 1、4、7 和 14；当前核心工作流已扩展到 Model 1/4/6/7/8/14/15；
- OLS 系数、经典或手工 HC3 协方差、t、p、置信区间和 R²；
- 模型内共同完整案例以及按方程配置的控制变量；
- Model 4 间接效应、总效应和固定种子百分位 bootstrap；
- 连续调节的均值、均值 ±1 SD 简单斜率和 Johnson–Neyman 临界点；
- Model 7/14 条件间接效应与调节中介指数 bootstrap；
- ResultBundle 0.2、方程系数表、效应表、简单斜率和方法警告；
- 残差标准误、最大杠杆值、最大 Cook 距离和 Breusch–Pagan 辅助回归诊断；
- AnalysisRun 结果落盘并记录派生数据 SHA-256、模型哈希、版本、标准误、重复次数和种子。

## M4 发布硬化

- 分析提交改为持久化后台任务，提供查询与取消 API；阶段、百分比和 bootstrap 完成数可轮询；
- 取消请求写入协作标记并在必要时终止/杀死 R 子进程，取消任务不会产生成功 ResultBundle；
- 服务重启会把遗留的排队/运行任务标成明确失败，避免永久假运行；
- 前端显示真实进度、迭代数、取消状态和终态错误；
- 成功运行可导出含报告、图、三层版本规格、结果、R 脚本、会话信息、日志和 SHA-256 清单的 ZIP；
- 导出支持含分析数据与不含数据两种隐私模式；
- 四模板的关键估计扩展到独立 NumPy 矩阵金标准，固定种子结果逐字段复现；
- 自动测试覆盖真正取消、导出清单完整性和 5,000 次 bootstrap 20 秒 MVP 门槛。

## M5 问卷实证分析中心历史记录

- 独立三步主流程：数据与测量 → 问卷实证分析 → 模型画布与 PROCESS；
- 构念得分和非题项数值变量的 N、缺失、均值、标准差、范围、偏度、峰度与极端 z 值；
- 二分类、名义和有序人口统计变量的频数与百分比；
- Pearson 相关、成对样本量和显著性矩阵；
- Harman 未旋转首因子解释率、KMO 和 Bartlett 球形检验；
- 最大似然/varimax EFA，并在不可估计时明确回退到主成分载荷；
- 纯 base R 简单结构最大似然 CFA，输出 χ²、CFI、TLI、RMSEA、SRMR 和标准化载荷；
- α、ω、CR、AVE、Fornell–Larcker 和 HTMT 聚合/区分效度证据；
- 可选二组 Welch t + Hedges g；多组经典/稳健 ANOVA、η²及事后比较；
- 可配置结果构念、区块 1 控制变量和区块 2 核心预测构念的分层 OLS、ΔR²、F-change、置信区间与 VIF；
- 当前导出器定义最多 23 个命名主题工作表，覆盖描述/频数、相关 p/N、诊断、信效度、Fornell/HTMT 及其 CI、EFA/CFA、稳健差异与事后比较、回归和方法来源；实际数量随可选分析而变化；
- 提供可直接导入的消费者/组织行为风格三构念示例问卷数据。

## 立项包导航

| 文档 | 用途 |
| --- | --- |
| [00-立项总览](docs/00-立项总览.md) | 项目章程、核心决策和文档索引 |
| [01-产品需求文档](docs/01-产品需求文档.md) | 用户、场景、范围、功能和非功能需求 |
| [02-科研方法规范](docs/02-科研方法规范.md) | 数据、量表、中介、调节和结果报告规则 |
| [03-信息架构与交互](docs/03-信息架构与交互.md) | 页面结构、主流程和画布交互语义 |
| [04-领域模型与协议](docs/04-领域模型与协议.md) | 核心对象、状态流转和 ModelSpec 编译规则 |
| [05-技术架构](docs/05-技术架构.md) | 本地应用架构、技术选型、存储和安全边界 |
| [06-统计验证与测试](docs/06-统计验证与测试.md) | 数值对照、测试分层和发布质量门槛 |
| [07-路线图与工作分解](docs/07-路线图与工作分解.md) | 历史 MVP 阶段与任务依赖；当前路线图见 27 |
| [08-风险与治理](docs/08-风险与治理.md) | 科研、工程、数据和范围风险 |
| [09-验收与发布清单](docs/09-验收与发布清单.md) | 工程发布与方法 slice 支持的分层检查表 |
| [10-术语表](docs/10-术语表.md) | 产品与统计术语的统一口径 |
| [11-需求追踪矩阵](docs/11-需求追踪矩阵.md) | 需求、里程碑、测试与验收的对应关系 |
| [12-M0实现记录](docs/12-M0实现记录.md) | 首个可运行纵向切片、验证结果和当前限制 |
| [13-M1实现记录](docs/13-M1实现记录.md) | 数据导入、画像、字典确认和验证记录 |
| [14-M2实现记录](docs/14-M2实现记录.md) | 构念计分、信度、项目分析和派生数据版本记录 |
| [15-M3实现记录](docs/15-M3实现记录.md) | 模型画布、四模板、语义预检和冻结版本记录 |
| [16-M4统计MVP实现记录](docs/16-M4统计MVP实现记录.md) | 四模型统计闭环、数值验证和剩余发布门槛 |
| [17-M5问卷实证分析中心实现记录](docs/17-M5问卷实证分析中心实现记录.md) | 问卷全实证证据、算法、导出与验证记录 |
| [18-高级统计方法开发指南与接口规范](docs/18-高级统计方法开发指南与接口规范.md) | 实验、多层、纵向、插补和功效分析的协议、计算规范与验收门禁 |
| [19-仓库结构与技术债治理](docs/19-仓库结构与技术债治理.md) | 模块入口、调用定位、已偿还技术债与持续门禁 |
| [20-性能债审计与优化路线图](docs/20-性能债审计与优化路线图.md) | 性能基线、已确认债务、优化顺序和自动门禁 |
| [21-长期可持续开发债务复审与治理基线](docs/21-长期可持续开发债务复审与治理基线.md) | 跨领域债务复审、地基硬化顺序、统一完成定义与长期验收条件 |
| [22-开发债务总账与持续治理执行手册](docs/22-开发债务总账与持续治理执行手册.md) | 债务分类、状态流转、优先级、完成定义和分层门禁 |
| [24-工程 Harness 与开发准则](docs/24-工程Harness与开发准则.md) | 本轮开发经验、统一反馈回路、代理工作准则和发布收口入口 |
| [25-后续开发可执行手册](docs/25-后续开发可执行手册.md) | 真实能力缺口、实现顺序、文件入口、金标准、测试与逐项发布门禁 |
| [27-OB/CB 实验与问卷实证研究全流程能力审计及开发蓝图](docs/27-OB-CB实验与问卷实证研究全流程能力审计及开发蓝图.md) | 资深 OB/CB 研究视角下的端到端能力缺口、P0 修复、详细需求、验收标准与实施路线图 |
| [28-代码—业务—文档一致性与仓库收口审计](docs/28-代码-业务-文档一致性与仓库收口审计.md) | 当前仓库的接线追踪、清理决定、保留理由、规划入口和交付验证证据 |
| [29-M6-全量实证分析能力与发版工程实现汇总记录](docs/29-M6-全量实证分析能力与发版工程实现汇总记录.md) | M6 里程碑全量实证分析能力、表格与发版工程实现总结 |
| [30-AI-Agent金标准自动核对基础设施开发记录](docs/30-AI-Agent金标准自动核对基础设施开发记录.md) | 26 个真实生产 SUT、主参考、动态不变量、突变门禁与严格资格复核记录 |
| [31-AI-Agent无人工介入金标准设立与自动核对规范](docs/31-AI-Agent无人工介入金标准设立与自动核对规范.md) | GoldenPlan、双独立参考、场景矩阵、证据等级、来源治理、漂移检测与自动发布资格规范 |
| [机器可读债务总账](docs/debt-register.json) | 实时债务状态、证据、责任角色、目标里程碑和关闭条件 |
| [审计与复验证据索引](docs/audits/README.md) | 历史计量审查、修复复验结论与实时证据职责边界 |
| [ADR-001：本地优先架构](docs/adr/ADR-001-本地优先架构.md) | 已确认架构决策及其影响 |
| [ModelSpec JSON Schema](specs/model-spec.schema.json) | 模型中间表示的机器可读约束 |
| [ResultBundle JSON Schema](specs/result-bundle.schema.json) | 统计结果的机器可读约束 |
| [AdvancedAnalysisSpec JSON Schema](specs/advanced-analysis-spec.schema.json) | 五类高级方法的当前 0.1 输入协议；可达性仍受 Pydantic 和 slice 校验约束 |
| [AdvancedResultBundle JSON Schema](specs/advanced-result-bundle.schema.json) | 高级方法成功结果的最小通用协议 |
| [DatasetVersion JSON Schema](specs/dataset-version.schema.json) | 导入数据版本和变量画像的机器可读约束 |
| [MeasurementVersion JSON Schema](specs/measurement-version.schema.json) | 构念、计分、测量报告和派生数据版本约束 |
| [Model 4 示例](examples/model-4.example.json) | M0 单一中介纵向切片 |
| [Model 7 示例](examples/model-7.example.json) | 调节中介模型示例 |

## 已确认边界

- 仅供个人、本地使用，不公开部署、不商用。
- Windows 为首个支持平台，服务仅监听 `127.0.0.1`。
- MVP 不依赖大模型；数据类型推断和统计计算必须是确定性逻辑。
- 当前支持观测变量 Model 1、4、6、7、8、14、15 的等价结构，不宣称覆盖全部 PROCESS 模板或全部 CB/OB 设计。
- 原始数据只读、不可覆盖；每次运行均保留数据哈希、模型、参数、随机种子和软件版本。
- 潜变量 SEM 已进入预览可用阶段；多层、纵向、复杂实验与缺失数据多重插补仍未进入正式支持范围。高级接口的 `valid=true` 只代表规格通过当前校验，family 的 `executionAvailable=true` 只代表 runner 已注册；正式使用还必须核对具体 slice、方法警告和验证证据。

## 开工入口

编码前依次完成：ADR 确认、ModelSpec 评审、金标准数据集建立、前端垂直切片。任务顺序见 [07-路线图与工作分解](docs/07-路线图与工作分解.md)。
