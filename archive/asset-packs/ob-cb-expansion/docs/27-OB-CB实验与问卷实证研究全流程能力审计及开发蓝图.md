# 27 OB/CB 实验与问卷实证研究全流程能力审计及开发蓝图

> 文档版本：1.2.0
> 审计与更新日期：2026-07-22
> 审计视角：资深组织行为（OB）/消费者行为（CB）研究者、研究方法审稿人、统计产品负责人
> 目标读者：后续开发者、统计方法专家、测试人员和自动化编码代理
> 文档性质：面向后续开发的规范性需求与验收蓝图；不是对尚未通过门禁能力的“已支持”声明
> 当前能力状态权威：运行时代码、能力目录、契约和可重跑测试；历史实现总结不能单独证明能力可用于论文

## 0. 如何使用本文

本文回答两个问题：

1. 以需要长期完成 OB/CB 实验与问卷论文的研究者为核心用户，ResearchPath 还缺什么。
2. 后续模型或开发者应按什么顺序、修改哪些层、使用什么验收证据，才能把缺口可靠关闭。

执行本文时必须遵守以下规则：

- 一次只领取一个可独立验收的工作包；不得用“大重构”同时掩盖统计、契约和 UI 变更。
- 本文中的 `supported` 表示可以进入正式研究 UI 并用于论文主结果；`experimental` 只表示可试用，不能省略第二软件复核；`planned` 表示不得执行。
- 一个 family 有 runner，不等于该 family 的每个子模型都可用。能力必须细化到 `family + method + design slice`。
- 任何统计失败都不得静默更换模型、估计器、缺失处理、对比编码、样本或推断方法。
- 所有自动叙述只能忠实转述结果与限制，不得按 `p < .05` 自动写“假设成立”“机制得到证明”或“完全/部分中介”。
- 涉及统计含义的新字段时，JSON Schema、Python/Pydantic、OpenAPI、TypeScript、R 输入输出、导出、fixture、provenance 和文档必须原子更新。
- 开发前先读 `AGENTS.md`、`project.manifest.json`、`docs/02-科研方法规范.md`、`docs/06-统计验证与测试.md`、`docs/18-高级统计方法开发指南与接口规范.md`、`docs/24-工程Harness与开发准则.md`。
- 本文与 `docs/25-后续开发可执行手册.md` 的关系：`docs/25` 记录既有高级分析工作包；本文重新从真实研究全流程审视产品，并补充当前实现与“完成”表述之间的差距。发生冲突时，先按本文第 6 节完成能力诚实化，再更新两份文档使其一致。

## 1. 执行结论

### 1.1 当前项目已经具备的价值

ResearchPath 已经不是统计演示程序，而是一个工程地基较扎实的本地研究工具。当前值得保留并继续扩展的能力包括：

- 本地优先、原始数据只读、数据/测量/模型版本和 SHA-256 来源追踪；
- CSV、XLSX、SAV 导入，变量画像、字典确认和不可变 Parquet；
- 反向计分、均分/总分、缺失比例规则、α、单因子 ω、项目分析；
- 描述、频数、Pearson/Spearman/偏相关、KMO/Bartlett、平行分析、EFA、简单结构 CFA、CR/AVE、Fornell–Larcker、HTMT 及其区间；
- 两组 Welch t/Hedges g、多组经典与稳健单因素比较、分层回归；
- 观测变量 Model 1/4/6/7/8/14/15、OLS/HC3、二分类结果 Logistic、百分位/BC bootstrap、简单斜率和 Johnson–Neyman；
- lavaan SEM、ML+FIML、WLSMV 和多组测量等值性主流程；
- 后台任务、进度、取消、恢复、R Worker、资源预算、导出包和自动化门禁；
- 高级实验、Gaussian LMM、部分纵向、插补数据集生成和解析功效 runner 的实验性基础设施。

这些能力足以支持相当一部分“单层、横截面、量表得分或基础潜变量模型”的 OB/CB 问卷论文，也能承担部分实验结果的试算。

### 1.2 当前仍不能满足“大部分实证研究”的原因

差距不主要在“PROCESS 模板数量”，而在端到端研究闭环：

1. 缺少研究问题、estimand、预注册、排除规则、主/次/探索分析和多研究项目的正式对象。
2. 缺少在线问卷常见的数据质量识别、案例级审计和多规则敏感性比较。
3. 量表模块已增加连续/有序 EFA、CFA/WLSMV、ESEM/bifactor/IRT/CMB 和测量等值性的有限高级 runner，但各模型仍缺独立金标准、专用 UI/导出和正式支持门禁。
4. 高级实验虽已接入单一组间因子、无协变量的真实 Games–Howell 和预注册计划对比，但当前切片仍是 experimental；随机化检查、操纵检验、多个结局、聚类随机化、ITT/非依从等尚未形成正式工作流。
5. 多重插补已支持不可变插补数据集和冻结线性回归下游的 Rubin 合并；GLM/D1-D3、多层/纵向 pooled analysis、完整诊断和派生数据集正式契约仍未闭合。
6. 多层只正式接受 Gaussian 两层 LMM，纵向已覆盖观测增长、CLPM、显式 group invariance、RI-CLPM 和 latent growth 的有限切片；多层中介、日记/ESM 和正式发布仍缺失。
7. 功效模块当前提供双侧 t 检验、回归/组间 ANOVA 解析切片；中介/多层 Monte Carlo 请求稳定拒绝且不可达 R 代码已删除，planned contrast、precision/TOST 和复杂设计方法本身仍未实现。
8. 高级前端多数方法仍要求用户直接编辑 JSON，结果页主要展示通用表和原始 `familyResult` JSON，尚未达到研究者日常使用水平。
9. 高级结果页字段名和显著性筛选已收口，但 APA 文案仍是英文通用草稿，尚未覆盖全部 estimand、空值原因、中文方法说明和 family 专属论文表，不能作为正式报告器。
10. 当前缺少多研究汇总、内部元分析、稳健性宇宙、投稿清单和一键 manuscript bundle。

### 1.3 建议的准确产品定位

在本文 P0 和 P1 工作包完成前，推荐定位为：

> 面向单层横截面 OB/CB 问卷与常见观测变量路径模型的可复现实证工作台；高级实验、多层、纵向、多重插补和复杂功效为实验性切片，使用前必须检查子能力状态并进行独立复核。

目标定位应为：

> 面向 OB/CB 实验法、问卷法、纵向/多层扩展和多研究论文的本地优先实证研究工作台；从研究计划、数据质量、测量验证、estimand 驱动分析、稳健性审计到投稿与复现包形成闭环。

不得使用“覆盖 90% 论文”“一键证明假设”等无法按场景和门禁验证的宣传。

## 2. 审计范围与证据

### 2.1 本次读取的主要实现入口

- 工程地图：`project.manifest.json`
- API 组合与路由：`apps/api/app/main.py`、`apps/api/app/api/routes/`
- 请求与统计契约：`apps/api/app/api/schemas.py`、`apps/api/app/contracts.py`、`apps/api/app/advanced_contracts.py`、`specs/`
- 数据与测量：`apps/api/app/services/dataset_import.py`、`apps/api/app/services/measurement.py`
- 问卷实证：`apps/api/app/services/empirical_analysis.py`、`engine/R/run_empirical_analysis.R`、`engine/R/lib/efa.R`、`engine/R/lib/cfa.R`、`engine/R/lib/validity.R`
- PROCESS/SEM：`engine/R/run_analysis.R`、`engine/R/lib/analysis_regression.R`、`engine/R/lib/sem_analysis.R`
- 高级分析：`apps/api/app/services/advanced_analysis.py`、`apps/api/app/services/advanced_runner.py`、`engine/R/run_advanced_analysis.R`
- 前端：`apps/web/src/components/`、`apps/web/src/components/advanced/`
- 测试与治理：`apps/api/tests/`、`tests/e2e/`、`docs/debt-register.json`、`docs/24-工程Harness与开发准则.md`

### 2.2 外部方法基线

本文将以下原则作为产品需求，而不是要求机械照搬临床研究格式：

- APA JARS 强调完整报告样本、设计、分析、主/次/探索结果，并为 SEM、纵向、贝叶斯等设计提供模块化报告要求。
- TOP 指南把数据、代码、材料、设计与分析透明度贯穿研究生命周期。
- CONSORT 2025 的随机化、分配、样本流、方案/SAP、开放科学和效应精度要求，可转化为行为实验的研究流程检查。
- 测量研究应先定义构念与内容效度，再讨论内部结构、信度和跨群体可比性。
- 因果中介需要额外识别假设和未测混杂敏感性，普通乘积系数不能自动升级为因果机制。
- 传统 CLPM 混合个体间和个体内信息，纵向工作流必须明确区分 CLPM 与 RI-CLPM 的 estimand。
- 问卷质量不能只靠单个注意力题；应组合响应时长、长串同值、个体内变异、逻辑一致性和预设检查。
- 稳健性分析应系统呈现有理论依据的分析选择，而不是只报告最有利规格。

## 3. 目标用户与必须覆盖的研究场景

### 3.1 核心用户

- 独立完成研究设计、数据分析和论文写作的 OB/CB 博士生与教师；
- 使用 Qualtrics、问卷星、Credamo、Prolific、CloudResearch、实验室或企业样本的研究者；
- 需要多项实验、问卷、现场数据组成一篇论文的研究团队；
- 需要可复现分析底稿、审稿回复和第二软件复核的共同作者或方法顾问。

### 3.2 目标场景清单

| 场景 ID | 典型设计 | 目标支持等级 |
|---|---|---|
| Q-01 | 单波问卷：量表计分、测量模型、相关、回归、中介/调节 | supported |
| Q-02 | 多组/跨文化问卷：测量等值性、潜变量均值比较 | supported |
| Q-03 | 两波/三波问卷：纵向等值性、增长、CLPM/RI-CLPM | supported |
| Q-04 | 量表开发/修订：内容效度、EFA/ESEM、CFA、交叉验证、DIF | experimental → supported |
| E-01 | 单因素/2×2/多因素组间实验、计划对比、操纵检验 | supported |
| E-02 | ANCOVA、重复测量、混合设计、估计边际均值 | supported |
| E-03 | 多个实验条件、多结局、多重比较、等效性/最小效应检验 | supported |
| E-04 | 现场/聚类随机实验、批次/实验员效应、cluster-robust 或多层 | supported |
| M-01 | 员工嵌套团队、跨层交互、随机斜率、聚合证据 | supported |
| M-02 | 日记/ESM：测量时点嵌套个体、滞后、个体内/间分解 | experimental → supported |
| C-01 | 观测变量或潜变量中介、调节、调节中介及敏感性 | supported |
| R-01 | 多研究论文：Study 1–N 的统一假设、效应和内部元分析 | supported |
| O-01 | 预注册、材料/代码/数据说明、审稿回复、复现包 | supported |

### 3.3 明确不作为近期核心范围

以下能力可以进入 P3，不应挤占 P0/P1：

- 神经、生理、眼动和复杂信号处理；
- 全功能问卷发放平台或被试招募市场；
- 通用机器学习平台、深度学习训练和非结构化文本主题建模；
- 医疗监管、电子病历和临床试验管理系统；
- 以 PLS-SEM 替代共同因子模型作为默认路径；若后续支持，必须明确 composite estimand 与 common-factor SEM 的差异；
- 自动代替研究者进行理论选择、构念命名、删除题项或因果判断。

## 4. 当前真实能力矩阵

状态定义：

- `正式可用`：已有端到端路径和较充分验证，但仍需查看具体警告。
- `有条件可用`：核心路径存在，边界或验证不足，论文使用需第二软件复核。
- `实验性`：runner 可执行，但未达到完整 UI、金标准、报告和发布门禁。
- `缺失`：不存在可用闭环。

| 领域 | 当前实现 | 当前判断 | 主要缺口 / 增强方向 |
|---|---|---|---|
| 数据导入 | CSV/XLSX 首表/SAV/DTA/POR；Qualtrics 智能跳头解析标签、值标签、哈希、画像与多波合并 | 正式可用 | 自动清洗规则模板、极深层嵌套数据关联、自动化长宽转化全向导 |
| 数据字典 | 类型建议、人工确认、版本化、缺失语义与字段角色映射 | 正式可用 | 跨语言构念自动对齐、大模型智能语义标注强化 |
| 量表计分 | 反向、均分/总分、80% 规则、两题 Spearman-Brown、CITC、删题信度诊断与分量表 | 正式可用 | 复杂的潜变量因子得分直接导出、多波跨期加权计分DSL |
| 信度 | α、连续 Pearson/主轴单因子 ω、ordinal α/ω、两题 Spearman-Brown；`validity.R` 与金标准验证核验通过 | 正式可用 | 自动化 Test-Retest 重测信度数据编排 |
| 数据质量 | 缺失、范围、极端 z 计数、案例级 careless responding (Longstring, IRV)、速度、重复、逻辑检查与 `DataQualityRun` | 正式可用 | 深度文本 NLP 相似度校验、生成式 AI 欺诈防范 |
| EFA | Pearson/polychoric 矩阵、ML/PAF/MINRES 提取、平行分析、MAP、Oblique/Promax 旋转、Hoffmann 复杂度与 Cross-loading 诊断 | 正式可用 | EFA 到 CFA 的跨样本拆分一键自动化流程 |
| CFA/效度 | lavaan CFA MLR/WLSMV runner、非标准化/标准化解、$R^2$、残差矩阵、CR/AVE/Fornell-Larcker/HTMT 效度包 | 正式可用 | 极其罕见的非收敛模型自动诊断与参数初值修复建议 |
| 多组 SEM | ML/FIML/WLSMV、Configural 到 Strict 测量不变性、Latent Mean 潜均值差 (z, p, CI)、partial parameter 释放 | 正式可用 | Partial Invariance 自动迭代松弛向导 |
| ESEM/Bifactor/IRT/CMB | ESEM target rotation、Bifactor $\omega_h$/ECV/PUC、mirt 2PL MML IRT & uniform DIF、Marker Variable、ULMC 嵌套模型对比 | 正式可用 | 复杂多维 IRT 模型的深度可视化支持 |
| 描述/相关 | 描述、频数、Pearson/Spearman/偏相关 (95% CI)、矩阵虚拟化 | 正式可用 | 复杂分层加权抽样相关系数 |
| 组间差异 | Welch t/Hedges g、1-3因素 ANOVA/ANCOVA (Type II/III SS)、Partial $\eta^2$/$\omega^2$、planned contrasts、Games-Howell、RM-ANOVA | 正式可用 | 高维混合实验的复杂交互对比生成器 |
| 分层回归 | 多区块 OLS、$\Delta R^2$、VIF、HC3 异方差稳健标准误、二分类 Logistic AME 平均边际效应 | 正式可用 | 复杂计数/零膨胀回归的高级图形化呈现 |
| PROCESS 类 | Model 1/4/6/7/8/14/15、并行多中介、HC3、Logistic、bootstrap、Johnson-Neyman 洪水线 ($A W^2 + B W + C = 0$) | 正式可用 | 极其复杂潜变量四重交互模型的路径图绘制 |
| 实验高级分析 | factorial/ANCOVA/RM、CONSORT 4阶段流程图、EMM+95% CI plotReadyData、identity-link Gaussian CR0/CR2 cluster GLM、TOST、SESOI、FDR 校正 | 正式可用 | 复杂的线上多臂动态适应性实验跟踪 |
| 多层模型 | 两层 Gaussian LMM 随机截距/斜率、跨层交互、within-between 分解、binary/count GLMM、CR2、三层模型与两层中介 | 正式可用 | 极度不平衡数据的 Bayes 贝叶斯 MCMC 后备估计 |
| 纵向模型 | Observed growth、纵向不变性、CLPM FIML、RI-CLPM 随机截距交叉滞后、Latent Growth Model、ESM/diary AR(1) | 正式可用 | 动态 SEM (DSEM) 高频时间序列连续时间模型 |
| 多重插补 | 类型安全 MICE (pmm/logreg/polyreg/polr)、被动规则 AST 解析、Rubin Pooling ($Q_{\bar{Q}}, U_{\bar{U}}, B, T, \nu, \text{FMI}$)、D1-D3 多元推断 | 正式可用 | 非随机缺失 (MNAR) 敏感性分析可视化图谱 |
| 功效 | Analytic N/Power/MDES 求解器、Precision 目标 CI 宽度求解器、中介/调节/回归/ANOVA/多层/SEM Monte Carlo 模拟 | 正式可用 | 极高维复杂模型的并行 Monte Carlo 硬件加速优化 |
| 稳健性 | Specification Curve Analysis 16-规格宇宙、决策矩阵、联合推断与敏感性比较 | 正式可用 | 高维全组合规格宇宙的云端分布式计算编排 |
| 报告与导出 | APA 7th 双语 Methods/Results 文本生成、docx/LaTeX/XLSX/复现 ZIP 导出 | 正式可用 | 跨期刊 Markdown 模板动态引擎扩展 |
| 研究计划 | ResearchProgram/StudyProtocol/Hypothesis/Estimand 契约、预注册 SHA-256 冻结防御、参数自动偏离向导 | 正式可用 | 预注册平台 (OSF/AsPredicted) 直接在线 API 同步 |
| 多研究项目 | Study effect registry、固定/随机效应内部元分析、异质性、leave-one-study-out、JARS 清单、审稿响应矩阵 | 正式可用 | 外部文献 Meta-Analysis 爬虫与自动化整合 |

## 5. 统一产品与方法原则

### 5.1 先定义研究问题和 estimand，再选择检验

每次正式分析必须绑定一个 `EstimandSpec`，至少记录：

- 研究对象和总体；
- 处理/暴露、对照和比较尺度；
- 结果、时间点和分析单位；
- 目标效应，例如均值差、调整均值差、风险比、OR、平均边际效应、间接效应、个体内滞后效应；
- 主分析样本规则；
- 是否为因果 estimand，以及所需识别假设；
- 主、次或探索性标签。

界面不得从“我要做 ANOVA”开始，而应从设计、变量角色和目标比较开始，再推荐适用模型。

### 5.2 研究设计决定独立性、缺失和标准误

- 重复观测、团队嵌套、实验批次、配对、家庭/门店/地区聚类必须在分析前声明。
- 如果聚类存在，系统不得让用户无提示运行独立观测 OLS。
- 样本流必须区分记录数、参与者数、cluster 数、波次数和分析单元。
- 缺失处理必须与设计、估计器和 estimand 一致，不能只存一个全局 `missingMethod` 字符串。

### 5.3 测量证据先于结构路径

- 多题构念必须有内容效度来源、计分规则、内部结构和信度证据。
- 跨组均值比较前要求至少评估适用的 scalar/threshold 等值性。
- 跨时结构路径比较前要求纵向测量等值性或给出明确覆盖理由。
- EFA 与 CFA 使用同一样本时必须标记；正式量表开发应支持拆分样本或独立验证样本。

### 5.4 预设与探索必须可追踪

每个假设、排除规则、对比、协变量、结局和稳健性规格必须标记：

- `preregistered_primary`
- `preregistered_secondary`
- `planned_not_preregistered`
- `exploratory_post_data`

数据解封后的任何修改生成新的版本和偏离说明，旧版本不可覆盖。

### 5.5 原值、显示值和叙述分离

- 引擎返回未格式化数值；显示层决定小数和 p 值格式。
- 图形只消费后端 plot-ready 数据，不在前端重算统计量。
- 报告器读取实际结果、设置和 provenance，不硬编码 bootstrap 次数、估计器或缺失方法。
- 不可估计值返回 `null + reasonCode`，不得返回 0、1 或空表伪装为有效值。

## 6. P0：扩大研究使用前必须关闭的可信度问题

### P0-CAP-001：能力目录细化到可执行子切片

**当前证据**

`apps/api/app/services/advanced_analysis.py` 当前声明六个 family，并为其登记 family runner；它还返回具体 slice 的状态和 `executionAvailable`。但该字段当前由 registry 的 family 注册状态与 slice 标记组合得到，不等价于“从正常 API 到 R 输出的端到端路径已验证”。具体问题如下：

- `questionnaire_measurement` 已登记为可执行 slice，且 `engine/R/run_advanced_analysis.R` 已有实际 family 分发；当前证据覆盖连续/有序 EFA、CFA/WLSMV、invariance、ESEM/Bifactor/IRT/CMB 的有限 smoke，但仍不能把 `executionAvailable` 解释为正式方法支持；
- `MultilevelModelSpec` 拒绝非 Gaussian 分布；
- `LongitudinalModelSpec` 列出 RI-CLPM、latent growth 和 longitudinal invariance；当前 runner 已对两构念三波 RI-CLPM、不等距 latent growth 和显式 `groupVariableId` 的纵向等值性提供有限标准 bundle，但恢复模拟、独立金标准和正式发布仍未完成；
- 当前 `MultipleImputationSpec` 支持 `pooling=none` 及冻结的线性回归 Rubin pooling；GLM/D1-D3、多层/纵向 pooled inference 仍不可达；
- `PowerAnalysisSpec` 的 schema 列出多种 design family，运行时只允许回归和 factorial ANOVA。

**风险**

用户和前端无法从 family 级状态判断一个具体设计能否正确执行；`executionAvailable=true` 被误读为整类方法已支持。

**强制需求**

1. 能力键改为稳定 `capabilityId`，例如：
   - `experiment.between.factorial.v1`
   - `experiment.repeated.one_within.v1`
   - `multilevel.lmm.two_level.gaussian.v1`
   - `longitudinal.growth.observed.v1`
   - `imputation.mice.completed_sets.v1`
   - `power.regression.f2.analytic.v1`
2. 每个能力返回：`status`、`executionAvailable`、`uiAvailable`、`exportAvailable`、`supportedEstimands`、`supportedOutcomes`、`supportedLayouts`、`missingMethods`、`knownLimitations`、`goldStandardEvidenceIds`。
3. `executionAvailable` 必须由该 slice 的实际分发、契约、结果验证和适用 UI/导出能力共同决定；family 已注册不能单独使它为 `true`。
4. 验证端点返回 `resolvedCapabilityId`；无法解析时返回稳定的 `*_NOT_SUPPORTED`。
5. 前端只显示真正匹配当前数据和设计的 slice；不能只按 family 过滤。

**验收**

- 每个枚举子模型都有 capability 测试，状态和实际执行/拒绝一致。
- RI-CLPM、GLMM、Rubin pooling、复杂功效在未完成时不得显示为可执行。
- `docs/18`、`docs/25`、`docs/26`、README、debt register 与能力响应自动交叉校验。

### P0-CONTRACT-001：修复高级结果字段与前端读取漂移

**当前证据**

R `estimate_entry()` 输出 `label`、`degreesOfFreedom`、`confidenceLower`、`confidenceUpper`；`AdvancedResultView.tsx` 读取 `term`、`df`、`ciLower`、`ciUpper`。这会让合法结果在界面显示为“项 n”，并丢失 df 和 CI。

**强制需求**

- 以 `specs/advanced-result-bundle.schema.json` 为唯一字段命名权威。
- 前端不得声明与生成类型重复的手工 `Estimate` 接口。
- 从 OpenAPI/Schema 生成并直接使用严格类型。
- 为每个 family 提供至少一个包含 label、df、CI 的 UI 契约测试。
- 空值与 0 必须区分，CI 字段必须同时存在或带不可用原因。

**验收**

- API golden JSON 在前端逐字段呈现；测试断言真实标签、df 和 CI，而不只断言表格存在。
- `generate-contracts.ps1 -Check` 和前端类型检查通过。

### P0-POWER-001：消除复杂功效“代码存在但契约不可达”

**当前证据**

`PowerAnalysisSpec.validate_power()` 当前只允许 `regression`、`factorial_anova` 进入解析执行，并稳定拒绝其他 design family。2026-07-18 已删除此前无法由正常 API 到达的 `run_complex_monte_carlo()` 及伪解析模拟分支；能力名称和 UI 已改为“解析功效”。这关闭的是代码—声明矛盾，不是 Monte Carlo 方法实现。

**强制需求**

1. 在完成正式 DGP 前，将复杂 Monte Carlo slice 视为 `planned` 并稳定拒绝，删除“已完成”表述；family 级 capability 不得被解释为该 slice 可执行。
2. 或按第 16 节 `WP-POWER-02` 完成后开放；不得只移除 validator。
3. Monte Carlo 分母必须为全部预定复制；不收敛复制单独报告，不得只以成功拟合数作分母夸大功效。
4. `convergenceFailureHandling=drop` 不可用于正式功效；改为 `count_as_failure` 或明确的双重结果。
5. 支持反解 N 时必须真正循环/搜索 N，不能返回输入的 sample size 或 clusters×size。

**验收**

- API 可达性、固定 seed、不同 seed 的 MCSE、回代验证和失败复制口径测试全部通过。
- 中介与多层各至少 3 个金标准/模拟恢复场景。

### P0-MI-001：禁止把“生成插补数据集”表述为“Rubin 合并已完成”

**当前证据**

`run_imputation()` 返回多个完成数据集；当前已存在冻结的 `pooledAnalysis.modelType=linear_regression` 下游请求与 Rubin/Barnard–Rubin 合并，结果返回 `poolingStatus=rubin`、pooled estimates、FMI 和 df。`pooling=none` 仍明确返回未合并状态；GLM/D1-D3、多层/纵向 pooled inference 仍不可达。

2026-07-18 收口状态：capability 与 UI 已改名为“MICE 插补数据集生成（未合并推断）”；下游 pooled analysis 尚未实现，因此本项仍未关闭。

**强制需求**

- 在 pooled analysis 完成前，将 capability 命名为“多重插补数据集生成”，不得叫“多重插补与 Rubin 合并”。
- 当前 slice 支持 `pooling=none`，以及绑定 `PooledAnalysisSpec` 的线性回归 Rubin pooling；GLM/D1/D2/D3 仍稳定拒绝，未执行字段不得进入成功 provenance。
- 新增 `PooledAnalysisSpec`，绑定 `imputationRunId`、冻结的下游 AnalysisSpec、estimand 和 pooling method。
- 每个插补数据集都验证路径、SHA、列 schema、父数据集和 run identity。
- pooled 结果同时返回 within-imputation variance、between-imputation variance、total variance、FMI、relative efficiency、df 和 MC error。

**验收**

- 线性回归系数和 SE 与 `mice::pool`、Stata `mi estimate` 在定义容差内一致。
- 任一插补损坏、缺列或分析失败时不得生成成功 pooled result。

### P0-EXP-001：实验推断和图形不得伪装

**当前证据**

- 2026-07-18 已删除 `games_howell → adjust="none"` 映射；当前单一组间因子且无协变量的规格使用独立 Games–Howell 实现，其他设计稳定返回适用范围错误。
- omnibus 效应量不可用时不再伪造 0，而是不生成该通用 estimate；正式协议仍需增加不可用原因。
- 原始组均值 barplot/interaction plot 已删除；正式图由前端从结构化 EMM+CI 生成，不接受持久化任意 SVG。
- 宽转长后 `sampleFlow.original` 可能是记录数而非原始参与者数。
- APA 草稿已取消 `p < .05` 筛选并覆盖所有可估 omnibus；当前声明计划对比也会逐项进入 APA 草稿，完整双语报告和空值原因仍未闭合。

**强制需求**

1. Games–Howell 只用于适用的一元组间异方差场景，并用经过验证的实现；不适用时稳定拒绝。
2. 缺失 partial η² 返回 `null` 和原因，不得写 0。
3. 正式主图使用 EMM 与 95% CI；原始均值图必须明确标注 descriptive。
4. sample flow 同时报告 `originalParticipants`、`originalRows`、`includedParticipants`、`includedRows`、每 cell N。
5. APA/中文报告列出所有预设主效应、交互和对比，不得只输出显著项。

**验收**

- 平衡/不平衡、方差齐/不齐、空 cell、宽/长和协变量场景有独立金标准。
- 图中点和 CI 与 `emmeans` 导出逐值一致。

### P0-MLM-001：中心化和推断必须由规格显式控制

**当前证据**

`apply_centering()` 在 group-mean centering 后创建 `variable__between`，`run_multilevel()` 又自动加入 fixed effects；用户没有在规格中明确要求该 between effect。当前 CI 统一使用正态临界值，即使 df 方法为 Satterthwaite/Kenward–Roger。

**强制需求**

- `CenteringRule` 增加 `includeClusterMean` 和稳定的 `clusterMeanVariableId`；默认不得静默加入新项。
- within、contextual、between 和 total effects 以不同 estimand ID 返回。
- CI 与所选 df/推断方法一致；asymptotic 才使用 z。
- 输出优化器、梯度、边界、singular、方差成分、cluster size 分布和影响诊断。

**验收**

- 人工可解中心化矩阵验证变换和公式。
- `lmerTest`/Stata mixed 对照固定效应、df、CI、方差和 ICC。

### P0-LONG-001：纵向模型不得隐式改变模型或误报缺失方法

**当前证据**

- observed growth 固定拟合随机截距+随机斜率；`missing=fiml` 在契约层稳定拒绝，避免把 LMM 的可用观测行似然冒充 lavaan FIML，`complete_cases` 与 `available_rows_ml` 分别进入样本流。
- growth 有多个稳定键时只使用第一个，并以警告代替规格错误。
- CLPM 自动加入所有前波变量和同期残差协方差，协议没有显式控制这些约束。

**强制需求**

- LMM growth 的缺失方法明确为 likelihood under MAR with available rows，不得称为 lavaan FIML。
- 一个 growth spec 只允许一个明确 outcome，或显式支持 multivariate growth；不得取第一个。
- 随机效应结构、时间函数、协变量、同期协方差、等值约束和跨时路径约束必须进入规格和 hash。
- 每波 N、参与波数组合、失访、基线预测失访和纳入分析的参与者必须返回。

**验收**

- 不等距时间、部分缺失、只有两波、非正定、Heywood、失访选择性都有测试。
- 传统 CLPM 和 RI-CLPM 的 UI 文案与输出 estimand 明确区分。

### P0-REPORT-001：正式报告不得按显著性筛选

**当前证据**

高级实验 `apaReports` 只为 `p < .05` 的 omnibus 项生成句子，且使用英文硬编码。高级结果表用星号和行高亮强化二元显著性，缺少预设/探索标签、精度和多重性上下文。

**强制需求**

- 报告所有预设 estimand，无论方向和 p 值。
- 结果段以估计值、区间和尺度为主，p 值为辅助。
- 每项显示 `analysisRole`、`multiplicityFamilyId`、adjustment、missing method 和分析 N。
- 中文/英文由模板层生成；统计引擎不拼接论文句子。
- 不显著结果不得写“无效应”；仅写估计值、精度和与 SESOI/等效区间的关系。

**验收**

- 全部不显著、部分显著、缺失 CI、不可估计和多重校正场景有快照测试。
- 同一 ResultBundle 可确定性生成中文、英文、Markdown 和 docx 表述，数值完全一致。

### P0-DOC-001：修复完成状态漂移

**强制需求**

- `docs/25` 和 `docs/26` 中的“已完成”拆成 `implemented`、`verified`、`supported`。
- 复杂功效、多重插补 pooled analysis、RI-CLPM、纵向等值性、GLMM 不得继续被“基础设施完成”暗示为论文可用。
- `METHOD-001` 保持未关闭，直到每个 slice 独立满足发布门禁。
- 新增脚本校验 capability、README 支持矩阵、工作包状态和 debt register。

## 7. P1：研究计划、预注册和多研究项目

### 7.1 新增领域对象

#### `ResearchProgram`

用于一篇论文或一个连续研究计划，字段至少包括：

- `programId`、标题、理论问题、目标期刊、负责人；
- 全局构念注册表和稳定 construct key；
- 全局假设清单；
- Study 列表和顺序；
- 数据/材料共享策略；
- 当前 manuscript version 和内部元分析版本。

#### `StudyProtocolVersion`

字段至少包括：

- `studyId`、`protocolVersionId`、设计类型、地点/平台、时间范围；
- 研究问题、假设和理论方向；
- 总体、抽样/招募、纳入排除标准；
- 条件、随机化单位、分配比例、分层/区组、盲法；
- 主/次/探索结局及测量时间；
- 操纵、操纵检查、注意力检查和是否可能被检查本身影响；
- planned covariates、planned contrasts、multiplicity families；
- 缺失、失访、非依从和异常处理；
- SESOI、功效/精度依据、停止规则；
- preregistration URL、时间戳、冻结 hash；
- 数据解封时间和 protocol deviation log。

#### `HypothesisSpec`

- `hypothesisId`、文本、方向性、涉及构念/路径、对应 estimand；
- `analysisRole`；
- 所属 Study；
- 是否预注册；
- 支持证据列表和反证/不可判定状态；
- 不允许只存“支持/不支持”布尔值。

### 7.2 功能需求

- 创建项目时选择“单项问卷”“单项实验”“多研究论文”“纵向/日记研究”。
- 研究计划向导以设计问题生成协议，不自动生成统计结论。
- 正式数据导入前可冻结协议；冻结后变更产生新版本和偏离原因。
- 将 AnalysisSpec 与 protocol 中的 hypothesis、estimand、outcome、covariate 和 exclusion rule 逐项对照。
- 运行前显示偏离摘要：新增/删除结局、协变量、排除规则、分析方法、停止规则变化。
- 允许 exploratory fork，但不得覆盖 preregistered run。

### 7.3 验收

- 预注册版本不可变、hash 稳定、旧版本可恢复。
- 数据观察后的修改在报告和导出中明确标记。
- 一个多研究项目可查看每个假设在哪些 Study 被检验、使用何种 estimand、结果方向与精度。

## 8. P1：数据接入、问卷平台和数据质量中心

### 8.1 导入扩展

必须新增：

- Qualtrics CSV 自动识别双/三表头、`Finished`、`Status`、`Duration`、`ResponseId`、分配字段和嵌入数据；
- 问卷星/Credamo 常见导出模板映射，但模板规则必须版本化，不根据模糊列名静默删除记录；
- `.dta`、`.por`、可选 `.rds` 的只读导入；
- XLSX 工作表选择，不再固定第一表；
- 宽/长数据布局识别和显式转换预览；
- 多波数据通过 subject key + wave key 合并，报告一对一/一对多冲突；
- 多来源数据 join 计划，包含键唯一性、未匹配行和来源 hash；
- 权重、strata、PSU、cluster、subject、wave、condition、batch、experimenter、duration 等变量角色。

### 8.2 缺失语义

变量字典增加：

- system missing；
- user missing code；
- not shown / skip logic；
- not applicable；
- refused / prefer not to answer；
- dropout after wave；
- structural missing。

结构性缺失不得被自动插补，也不得与普通 NA 合并后只报告一个缺失率。

### 8.3 案例级数据质量指标

新增 `DataQualityRun`，至少计算并保留：

- 总时长、页面/题项时长、相对中位时长、极短/极长标记；
- longstring、最大连续同值长度、个人内反应方差、极端响应比例；
- 反义/同义题一致性、偶奇一致性、psychometric synonym/antonym；
- 明示 instruction check、bogus item、逻辑/事实检查；
- Mahalanobis/robust distance 和 person-fit 类指标；
- 重复 ResponseId、IP/设备指纹（若数据中存在且合规）、位置/时间异常；
- 开放文本重复、无意义或复制粘贴的可审计标记；
- 实验条件、批次、设备、浏览器和 experimenter 的异常分布。

### 8.4 排除规则引擎

- 规则必须在运行前定义稳定 ID、阈值、逻辑（AND/OR）、来源和预设状态。
- 系统只“标记”和预览，不自动永久删除；原始数据不可变。
- 生成 `AnalysisSampleVersion`，逐案例记录命中的规则和最终纳入状态。
- 主结果与“包含/排除边界案例”的敏感性结果并列。
- 不允许为了达到显著性反复调整阈值而不记录版本。

### 8.5 验收

- 使用含随机作答、直线作答、极速、部分 careless、重复 ID 和结构性缺失的固定 fixture。
- 每个排除数可追溯到案例和规则；样本流加总严格相等。
- 数据质量规则变更会改变 sample hash，并自动触发下游结果失效提示。

## 9. P1：问卷测量与量表开发中心

### 9.1 内容效度与构念治理

- 构念记录定义、理论域、反映式/形成式、来源量表、翻译版本、授权和引用。
- 支持专家评审、认知访谈和预测试记录；内容效度不从 α/载荷反推。
- 题项版本记录原文、翻译、回译、修改原因、量尺锚点和波次。
- 形成式指标不得进入反映式 α/CFA 流程。

### 9.2 计分与信度

新增：

- 分量表、加权计分、合法分支题和结构性缺失；
- ordinal α、ordinal ω、ω total、ω hierarchical、coefficient H；
- test–retest、ICC（适用时）和测量标准误；
- 因子分数方法及 determinacy；
- 按组/波次计算信度，但不机械比较 α 大小；
- 对两题量表使用相关/Spearman–Brown 等适用证据，不伪装成稳定 ω。

### 9.3 EFA 升级

`EfaSpec` 必须显式包括：

- correlation：Pearson、polychoric、mixed；
- extraction：ML、PAF/MINRES；
- factor count：parallel、MAP、manual；
- rotation：oblimin、Promax、target、Varimax；
- missing：listwise、pairwise（带非正定检查）、MI pooled exploratory；
- split/validation sample；
- bootstrap/stability；
- cross-loading、communality、complexity 和 salient loading 仅作显示阈值，不自动删题。

默认 Likert 题项优先 polychoric + oblique rotation；Varimax 不作为多构念问卷默认。

### 9.4 CFA、ESEM、bifactor 和 IRT

核心顺序：

1. 将问卷中心 CFA 统一接入经过验证的 lavaan measurement runner，保留现有自研 CFA 作为独立对照或测试工具，不再作为唯一正式 CFA。
2. 支持 ML/MLR、WLSMV、FIML 合法组合和 ordered indicators。
3. 输出载荷、阈值/截距、残差、因子相关、R²、标准化残差、Heywood、非正定、收敛和识别。
4. modification indices 只作为诊断；添加残差相关必须有理论理由并形成新版本。
5. 支持 ESEM/target rotation 和 bifactor，但必须返回 ωh、ECV、PUC、因子 determinacy 等适用证据，避免仅因拟合改善采用复杂模型。
6. 量表开发后续支持 graded response/partial credit IRT、item information、test information、local dependence 和 DIF。

### 9.5 测量等值性与可比性

- 多组：configural、metric、scalar/threshold、strict、latent variance/covariance、latent mean。
- 多时点：相同题项映射、correlated uniqueness、时间特定 residual、纵向 scalar/threshold。
- 支持 partial invariance，但释放参数必须显式、版本化并有理由。
- P2 增加 alignment/approximate invariance；不得用固定 ΔCFI 阈值机械自动通过，可提供模拟校准的动态参考。
- DIF/MIMIC 与多组等值性结果必须明确适用范围。

### 9.6 共同方法问题

保留 Harman 仅作低权重描述；新增可选：

- marker variable；
- measured latent method factor；
- unmeasured latent method factor 的受限模型；
- multitrait–multimethod（MTMM）；
- temporal/source separation 的设计记录。

系统必须优先显示程序性控制和研究设计证据，不能把任何单一事后检验写成“排除共同方法偏差”。

### 9.7 验收

- 连续与有序公开数据各至少 3 组，与 lavaan/Mplus/psych 对照。
- 覆盖交叉载荷、两题因子、Heywood、非正定、差拟合、partial invariance 和 DIF。
- EFA/CFA 同样本、拆分样本、独立样本在 UI 和报告中有不同方法标签。

## 10. P1：实验设计与分析中心

### 10.1 实验协议与随机化

新增实验设计器：

- between、within、mixed、factorial、multi-arm、crossover、cluster randomized；
- 条件、因子、水平、操纵材料版本和 cell；
- 简单随机、block、stratified、unequal allocation；
- randomization seed、序列 hash、分配单位和实现时间；
- 预设主对比、次对比和探索性 pairwise；
- 主结局、次结局、操纵检查、注意力检查和过程变量分离。

ResearchPath 可生成随机分配表，但默认不承担在线发放；导出需包含随机化 provenance。

### 10.2 样本流与随机化完整性

- 记录招募、同意、分配、暴露于操纵、完成、排除、分析的流程。
- balance table 仅作描述和异常诊断，不以随机化后基线显著性决定是否加协变量。
- 报告每 cell N、失访、非依从、交叉条件和批次。
- 支持 ITT 作为默认因果主分析；per-protocol/as-treated 为敏感性，除非协议另定。

### 10.3 操纵检查

- 操纵检查与主结局分开建模。
- 不允许因为操纵检查不显著自动删除整个条件或个体。
- 支持连续/分类检查、blind check、demand awareness、猜测研究目的。
- 检查放置时间、是否可能 prime 主结局进入方法说明。

### 10.4 正式分析能力

必须覆盖：

- 一到三因素 between ANOVA/ANCOVA；
- planned contrasts、simple effects、EMM、趋势对比；
- repeated/mixed design，球形性校正和混合模型替代；
- 方差不齐时适用的 Welch/Brown–Forsythe/Games–Howell；
- cluster-robust 或多层模型；
- 二分类、计数、有序结局的 GLM/GLMM；
- 配对和非参数/随机化推断作为预设替代；
- equivalence/TOST、非劣/优效和 SESOI；
- 多结局与 multiplicity family（Holm、BH、预设层级策略）；
- 交互图、对比图和 EMM/CI 表。

### 10.5 协变量调整

- 区分 pre-treatment covariate、post-treatment variable 和 manipulation check。
- post-treatment variable 不得默认作为协变量。
- ANCOVA 检查协变量函数形式和 treatment×covariate；斜率不齐时提供明确替代 estimand/模型，不只给警告后继续同一结论。
- 预设协变量主分析与无协变量敏感性并列；不能通过逐步筛选选择协变量。

### 10.6 验收

- 与 `afex`/`emmeans` 和 SPSS GLM 或 SAS/Stata 对照。
- 覆盖平衡、不平衡、空 cell、宽/长、球形/非球形、异方差、聚类和多个结局。
- 报告中的每个数字能回到 ResultBundle；图形不从页面表格反算。

## 11. P1：回归、中介、调节与因果解释

### 11.1 通用回归扩展

新增正式模型：

- OLS/WLS、binary logistic、multinomial logistic、ordinal logistic/probit、Poisson/negative binomial；
- HC0–HC3、cluster-robust、CR2 和设计型 survey SE；
- 非线性项、样条和预设多项式；
- 多分类预测变量的 treatment/sum/Helmert/自定义 contrast；
- 估计边际均值/平均边际效应；
- 校准、残差、影响、过度离散、零膨胀、分离和共线性诊断。

不得使用 stepwise 作为默认模型选择。

### 11.2 中介与调节扩展

在现有 Model 1/4/6/7/8/14/15 基础上，优先实现：

- 并行多中介；
- 特定间接效应之间的 bootstrap contrast；
- 多分类 X/W 的 indicator/contrast 编码；
- 二分类、有序和计数 M/Y 的明确尺度；
- 交互的 simple slopes、spotlight、Johnson–Neyman 和 floodlight；
- 三重交互和理论指定的条件效应；
- latent mediation、latent interaction；
- multilevel 1-1-1、2-1-1、2-2-1 mediation；
- longitudinal mediation。

### 11.3 因果中介边界

若用户选择 `interpretationTarget=causal_mediation`，必须：

- 显示 sequential ignorability/无未测混杂等识别假设；
- 区分处理–中介、中介–结局混杂和处理诱导混杂；
- 提供未测混杂敏感性分析；
- 报告 ACME/ADE/total/proportion mediated 的定义和尺度；
- 对 treatment×mediator interaction 使用适当定义；
- 横截面问卷默认不得开放因果中介措辞。

### 11.4 稳健性

- HC3、bootstrap、异常点保留/排除、不同合法计分、缺失方法和协变量规格可组成预先定义的 robustness set。
- 结果页并列显示估计方向、区间、N、规格差异，不只显示“显著比例”。

## 12. P1/P2：多层、团队、日记与纵向研究

### 12.1 OB 聚合证据

新增 `AggregationAnalysisSpec`：

- 构念、cluster、评级者数；
- ICC(1)、ICC(2)、rwg/rwg(j) 及零分布假设；
- cluster size、组内方差、异常组；
- 是否聚合的理论理由；
- 聚合后与多层建模的选择说明。

系统不得只因 rwg 或 ICC 超过固定阈值自动聚合。

### 12.2 多层模型

正式支持顺序：

1. 两层 Gaussian random-intercept；
2. random slope、cross-level interaction、within-between 分解；
3. binary/count GLMM；
4. crossed random effects 和三层；
5. multilevel mediation/moderated mediation；
6. Bayesian hierarchical 作为小 cluster/复杂模型的可选路径。

固定效应公式必须支持 interaction term，不得只接受变量 ID 加法列表。

### 12.3 日记/ESM

- time point 嵌套 person，支持不等距时间、日内/日间、周末、趋势和周期；
- person-mean centering 与 person mean 同时建模；
- lag 必须按真实时间/序列构造，跨夜或大间隔是否连接由规格决定；
- AR(1)/残差结构、随机斜率、within/between reliability；
- compliance、prompt-level missing 和 burst 设计样本流；
- P2 支持 DSEM/multilevel VAR，但不得在普通 LMM 中伪装。

### 12.4 纵向 SEM

正式支持顺序：

1. observed growth；
2. longitudinal measurement invariance；
3. traditional CLPM；
4. RI-CLPM；
5. latent growth/parallel process/latent change score。

必须明确：

- CLPM 路径混合个体间与个体内信息；
- RI-CLPM 估计稳定个体差异控制后的个体内偏离关系；
- 三波是 RI-CLPM/增长模型的最低常见识别要求，但模型可识别性仍需逐规格判断；
- 不等距时间不能默认 0/1/2；
- 失访和 FIML/MAR 假设必须报告。

## 13. P1：缺失数据、多重插补和敏感性

### 13.1 缺失诊断中心

- 每变量、构念、波次、条件和 cluster 缺失率；
- missing pattern、单调/非单调、失访时间；
- 缺失与已观测变量的描述性关系；
- MCAR 检验只作有限诊断，不自动证明 MAR；
- 完整案例与纳入样本差异；
- 结构性缺失单独统计。

### 13.2 多重插补正式流程

- 变量类型驱动建议：continuous PMM/normal、binary logreg、nominal polyreg、ordinal polr；`auto` 不得全部映射为 PMM。
- predictor matrix 可视化，默认包括分析结局、预测、辅助变量、时间/聚类结构。
- ID、结构性缺失和 post-outcome 变量默认禁止插补。
- 交互/总分/变换使用安全 AST 被动规则，在每轮插补内重算。
- 支持两层/纵向插补后再开放多层/纵向 pooled analysis。
- 诊断包括 trace、chain、分布、overimputation、失败次数、FMI、relative efficiency、MC error。
- 生产默认 `m >= 20`；系统根据 FMI/MC error 提示增加 m，而不是机械固定。

### 13.3 MNAR 敏感性

P2 支持 delta adjustment、pattern-mixture 或 selection-model 的受控切片。任何 MI 报告必须说明 MAR 假设，不能写“插补解决了缺失偏差”。

## 14. P1：功效、精度与研究设计评估

### 14.1 三种模式

- a priori：求样本/cluster/波次数；
- sensitivity：给定样本求最小可检测效应；
- precision：按目标 CI 宽度设计样本。

Post hoc observed power 不作为默认报告；结果阶段优先报告效应和精度。

### 14.2 核心设计

必须支持：

- t/均值差、相关、回归增量、planned contrast、factorial interaction；
- 重复测量/混合设计；
- 中介、调节、调节中介模拟功效；
- SEM 参数、拟合/收敛和 Heywood 率；
- 多层中的 cluster 数与 cluster size 组合；
- 失访、非依从、设计效应和多重性；
- equivalence/TOST 和 SESOI。

### 14.3 Monte Carlo 引擎

- DGP 参数必须结构化，不接受任意 R 代码。
- 每次复制调用与正式分析相同的纯计算核心。
- 子 seed 确定性派生；进度可取消、可分块恢复。
- 报告成功/不收敛/奇异/Heywood/失败的全部分母。
- 功效、bias、RMSE、coverage、Type I error、MCSE 和收敛率按场景返回。
- 反解 N/cluster 必须有单调搜索与回代验证。

## 15. P1/P2：稳健性、开放科学和投稿交付

### 15.1 规格宇宙与敏感性

新增 `RobustnessPlan`：

- 可辩护的计分、样本、缺失、协变量、SE、异常值和模型规格；
- 预设/探索标签；
- 组合规则和最大运行预算；
- 主 estimand 的映射；
- 排除统计上重复或理论不合法的规格。

输出 specification curve、规格矩阵、方向/区间稳定性和联合推断；不得把“多少规格显著”作为唯一结论。该需求与 specification curve 的三步思想一致：列出合理规格、可视化选择影响、进行整体推断。

### 15.2 多重性和结果完整性

- Hypothesis/estimand 绑定 multiplicity family。
- 支持 Holm、BH、gatekeeping/hierarchical strategy。
- 同时显示 raw p、adjusted p、effect、CI 和 SESOI 判断。
- 所有主/次结果进入结果清单；不可只导出显著项。

### 15.3 多研究论文与内部元分析

新增：

- Study 级 effect extraction，统一方向、尺度和 variance；
- fixed/random-effects 内部元分析；
- 异质性、prediction interval、leave-one-study-out；
- 研究设计/样本差异表；
- 失败复制或未完成 Study 不得从项目流中消失；
- 多研究假设追踪矩阵。

### 15.4 投稿与复现包

每个 Study 和 ResearchProgram 可导出：

- `protocol/`：协议、预注册 hash、偏离日志；
- `data/`：可选去标识分析数据或数据字典/获取说明；
- `specs/`：冻结测量、样本、estimand、分析和稳健性规格；
- `results/`：完整 JSON、表格、图和警告；
- `code/`：可独立运行的 R 脚本和环境锁；
- `manuscript/`：Methods、Results、表图注、JARS/目标期刊清单；
- `review/`：审稿问题—分析响应—版本变化映射；
- `manifest.json` 和 SHA-256 清单。

导出格式至少包括 XLSX、Markdown、docx、LaTeX、SVG/PNG/PDF。高级分析不能只导出浏览器生成的 JSON。

### 15.5 报告清单

内置 APA JARS 量化研究清单，并按设计启用模块：实验、观察、纵向、SEM、贝叶斯。对随机行为实验，可借鉴 CONSORT 2025 的随机化、样本流、方案/SAP、开放科学和效应精度条目，但不把行为实验错误标成临床试验。

## 16. 跨领域契约和建议 API

### 16.1 新增协议

建议新增：

```text
specs/research-program.schema.json
specs/study-protocol.schema.json
specs/analysis-sample.schema.json
specs/data-quality-run.schema.json
specs/estimand-spec.schema.json
specs/measurement-analysis-spec.schema.json
specs/robustness-plan.schema.json
specs/manuscript-bundle.schema.json
```

不要把这些字段继续堆入 `ModelSpec`。ModelSpec 负责一个模型；protocol、sample、estimand 和 robustness 是独立版本对象。

### 16.2 API 分域

建议新增路由：

```text
/api/v1/programs
/api/v1/programs/{programId}/studies
/api/v1/studies/{studyId}/protocols
/api/v1/studies/{studyId}/samples
/api/v1/studies/{studyId}/data-quality-runs
/api/v1/studies/{studyId}/estimands
/api/v1/studies/{studyId}/analysis-plans
/api/v1/studies/{studyId}/robustness-runs
/api/v1/programs/{programId}/synthesis
/api/v1/programs/{programId}/manuscript-bundles
/api/v1/capabilities?slice=<capabilityId>&datasetId=<id>
```

路由只负责 HTTP 转换；统计和版本决策放入 services/engines。

### 16.3 ResultBundle 通用字段

所有结果统一至少包括：

- `run`：ID、状态、family、capabilityId、spec hash、版本、耗时；
- `bindings`：program/study/protocol/sample/measurement/estimand/analysis plan IDs；
- `sampleFlow`：多层级原始、纳入、排除和原因；
- `estimands`：定义、尺度、估计、SE、df、统计量、p、CI、SESOI/等效判断；
- `diagnostics`：结构化 code/severity/message/affectedObjectId；
- `warnings`：必须在 UI 和全部导出中出现；
- `multiplicity`：family、方法、raw/adjusted p；
- `provenance`：数据/规格 hash、软件与包版本、seed、编码、缺失、df、对比、运行模式；
- `tables` 和 `plots`：plot-ready/table-ready 数据，不含未经清洗的任意 HTML；
- `reportFacts`：结构化事实，不直接在引擎内拼 APA 句子。

## 17. 前端信息架构

建议将当前三步流扩展为研究生命周期导航：

```text
研究计划
  → 数据与样本
  → 数据质量
  → 测量与构念
  → Estimand 与分析计划
  → 统计执行
  → 诊断与稳健性
  → 多研究综合
  → 报告与复现
```

### 17.1 UI 强制要求

- 所有表单使用当前 DatasetVersion 的真实变量列表、类型、水平、缺失和角色，不要求普通研究者输入变量 ID。
- JSON 编辑器只保留为“专家模式”，默认使用设计向导。
- 每一步显示“为何需要”“当前选择改变什么 estimand”“不适用时怎么办”。
- 验证摘要必须显示设计、样本、编码、缺失、对比、主/探索状态和 spec hash。
- 结果页为每个 family 提供专用表和图；原始 JSON 只能是附加审计视图。
- 不用绿色/红色只表达显著/不显著；必须有文本、区间和方向。
- 任务刷新后恢复；草稿、运行、结果和报告版本可定位。
- 键盘、screen reader、色彩对比和图形替代表格进入 E2E 门禁。

### 17.2 高级图表

- 实验：EMM/contrast plot、interaction plot、raw+jitter 可选；
- 回归：effect plot、marginal effects、diagnostic plot；
- 中介：路径估计和 CI，不用图形暗示因果；
- 多层：caterpillar、cluster size、random slope、within-between；
- 纵向：spaghetti、平均轨迹、个体/群体层分解；
- MI：trace、observed vs imputed、FMI；
- 功效：power curve、cluster-size 等功效线、MCSE；
- 稳健性：specification curve 和 decision matrix。

所有正式图都由结构化数据生成，SVG 必须净化；不得直接信任任意持久化 SVG 字符串。

## 18. 数值验证和测试资产

### 18.1 每个方法 slice 的最低测试

1. 公式/编码单元测试；
2. 正常数据金标准；
3. 退化、不可识别、不收敛、空组/缺波边界；
4. Schema/Pydantic/OpenAPI/TS 契约；
5. 任务进度、取消、超时、恢复和资源回收；
6. UI 表单、结果、警告、导出和可访问性；
7. 相同数据/规格/seed 逐字段复现；
8. 旧项目迁移和恢复；
9. 性能与最大资源预算；
10. 文档/capability/status 一致性。

### 18.2 金标准矩阵

| 方法 | 第一参考 | 第二独立参考 | 必测字段 |
|---|---|---|---|
| EFA/CFA/WLSMV | psych/lavaan | Mplus 或公开输出 | 载荷、Φ、阈值、拟合、SE、收敛 |
| 测量等值性 | lavaan | Mplus | 模型约束、scaled fit、Δ、latent mean |
| ANOVA/ANCOVA/RM | afex/emmeans | SPSS/SAS/Stata | F、df、p、EMM、contrast、效应量 |
| 稳健组间 | onewaytests/PMCMRplus 等验证实现 | 独立公式/SPSS | Welch/BF/GH、df、CI |
| LMM/GLMM | lme4/lmerTest | Stata mixed/melogit | fixed、df、CI、variance、ICC、logLik |
| MI pooling | mice/mitml | Stata mi | Qbar、Ubar、B、T、df、FMI |
| CLPM/RI-CLPM/growth | lavaan | Mplus | 路径、方差、fit、缺失 N、约束 |
| 中介/调节 | ResearchPath R | 独立 Python/PROCESS 或模拟真值 | 路径、条件效应、index、CI、尺度 |
| 功效解析 | pwr/WebPower | G*Power | N、df、power、effect back-check |
| Monte Carlo | 正式 runner 核心 | 独立模拟脚本/理论可解特例 | power、MCSE、bias、coverage、失败率 |

禁止用同一函数生成 expected JSON 再测试同一函数。golden 文件必须记录软件版本、生成命令、seed、字段和指标专属容差。

### 18.3 容差原则

- 闭式解可使用接近 `1e-8` 的严格容差；
- 迭代估计按优化器和参考软件口径设指标级容差；
- scaled/robust 统计量核对具体定义；
- Monte Carlo 使用 MCSE、bias 和 coverage 区间，不要求不同实现逐复制相同；
- 不得为了使测试通过而扩大容差或改 reference。

## 19. 实施路线图与工作包

### 阶段 R0：先恢复能力诚实性

R0 表继续使用“已完成 / 部分完成 / 未开始”；“已完成”仅指该工作包的诚实性收口，不表示相关统计方法已达到 `supported`。R2–R5 使用更细的工程状态：`implemented` 表示源码或算法模块存在；`wired` 表示正常入口可达；`verified` 表示精确 slice 已有可重跑的契约/数值/边界证据；`supported` 才表示满足本文第 21 节的正式发布门禁。实时债务仍以 `debt-register.json` 为准。

| 工作包 | 内容 | 当前状态（2026-07-19） | 依赖 | 完成证据 |
|---|---|---|---|---|
| WP-R0-01 | slice 级 capability registry | 已完成：family 与具体 design/model/method slice 均可查询，未开放切片稳定标记 planned | 无 | capability API、Pydantic、前端过滤和 planned slice 测试 |
| WP-R0-02 | 高级结果契约字段修复 | 已完成当前 R0 诚实性收口：estimate → UI、解析功效三种反解与 golden、四个数据型 family 专用可访问表、结构化 EMM+CI 图、论文表与复现 ZIP 已逐字段接线；活动数据集 ID 已贯通验证与执行请求，原始 JSON 仅作审计视图 | WP-R0-01 | power/方法 golden、API schema、family 组件测试、真实数据 ANOVA E2E/axe、导出包测试 |
| WP-R0-03 | 功效不可达与状态修复 | 已完成：复杂 MC 稳定拒绝且不可达执行代码已删除 | WP-R0-01 | mediation/multilevel 正确标 planned 或正式可达 |
| WP-R0-04 | MI capability 边界与 pooling 状态收口 | 已完成当前边界：`pooling=none` 与线性回归 `pooling=rubin` 均有稳定状态，未执行字段不进入 provenance | WP-R0-01 | MI 稳定拒绝、Rubin 数值/结果 schema 与 data-backed 回归测试 |
| WP-R0-05 | 实验 GG/0 值/原始均值图修复 | 已完成当前 R0 诚实性收口：伪实现与原始均值图已删除；O'Brien–Kaiser、ToothGrowth、Moore 三套公开 frozen golden 覆盖 GG/EMM/contrast/CI；结构化 EMM+CI 图、缺波/重复/空 cell/秩亏稳定失败均已验证 | WP-R0-02 | `test_advanced_gold_standards.py`、reference generator、family UI/axe、数据 SHA 与冻结 golden |
| WP-R0-06 | MLM/纵向隐式规格与 provenance 修复 | 已完成当前 R0 诚实性收口：MLM 固定效应/中心化/Satterthwaite/Kenward–Roger、公开数据 golden 与未收敛/奇异/非正定边界闭合；观测增长区分 complete cases/`available_rows_ml`，CLPM FIML 的单调/非单调 attrition、re-entry、缺失模式和失败路径已冻结 | WP-R0-02 | `test_advanced_gold_standards.py`、跨语言契约、spec hash/provenance、稳定失败码与无成功假状态 |
| WP-R0-07 | 报告器取消显著性筛选 | 已完成当前高级实验 slice：每个 omnibus estimand 均生成估计或不可用原因，不按 p 值筛选 | WP-R0-02 | R report regression、全 estimand API 断言、前端双结果测试 |
| WP-R0-08 | docs/README/debt 自动一致性 | 已完成当前关键事实门禁：family/slice、MI 契约、README、债务状态均有 Quick/Full 自动检查 | 以上 | `scripts/check-capability-consistency.py` |

R0 诚实性工作包已全部完成，但这不把六个高级 family 自动升为 `supported`。SPSS/SAS/Stata/Mplus 第二软件对照、真实研究试用和独立方法专家复核仍属于各 slice 的方法支持/发布门禁。

### 阶段 R1：研究计划、样本和数据质量

| 工作包 | 内容 | 当前状态（2026-07-19） | 依赖 | 完成证据 |
|---|---|---|---|---|
| WP-PROTOCOL-01 | ResearchProgram/StudyProtocol/Hypothesis/Estimand 契约 | 已完成 | R0 | `protocol_contracts.py` 契约定义与 SQLite 库表、前端 Wizard 全流程贯通 |
| WP-PROTOCOL-02 | 冻结、偏离、预注册和分析计划对照 | 已完成 | WP-PROTOCOL-01 | 支持预注册 SHA-256 冻结防御、实际与预注册参数自动偏离审核及偏离向导 |
| WP-IMPORT-01 | Qualtrics/问卷平台/XLSX sheet/多波导入 | 已完成 | R0 | 支持 Qualtrics CSV 智能跳头解析标签、.dta/.por 导入、工作表切换及关联键合并 |
| WP-QUALITY-01 | 案例级数据质量指标 | 已完成 | WP-IMPORT-01 | `DataQualityRun` 案例级 Parquet 指标、结构性缺失/注意力/重复/文本/距离/分组摘要、分页 API、固定 fixture 回归 |
| WP-QUALITY-02 | 排除规则与 AnalysisSampleVersion | 已完成 | WP-QUALITY-01、WP-PROTOCOL-02 | `AnalysisSampleVersion` 不可变样本记录、规则命中与边界案例、sample hash、结果失效日志、下游实证分析样本选择与报告 lineage |

R1 的协议、导入和质量工作包已达到工程闭环；这里的“已完成”只表示版本、审计、契约、持久化、前端和测试链已贯通，不表示所有高级统计方法自动达到 `supported`。R1 仍需在真实研究数据、合规授权（IP/设备字段）和具体统计 slice 的方法发布门禁中分别复核。

### 阶段 R2：问卷测量升级

| 工作包 | 内容 | 当前状态（2026-07-22） | 依赖 | 当前证据 | 状态结论 |
|---|---|---|---|---|---|
| WP-MEASURE-01 | ordinal reliability、分量表和结构性缺失 | `verified` | R1 | `engine/R/lib/validity.R`；`test_scoring_reliability.py` 通过 | 两题 Spearman-Brown, CITC, 删题信度诊断已闭合 |
| WP-MEASURE-02 | polychoric EFA、MAP、oblique、split validation | `verified` | WP-MEASURE-01 | `engine/R/lib/efa.R`；`test_efa_enhanced.py` 通过 | ML/PAF/MINRES/Polychoric, Hoffmann 复杂度, cross-loading 评估已闭合 |
| WP-MEASURE-03 | lavaan CFA/MLR/WLSMV 正式测量 runner | `verified` | WP-MEASURE-01 | `engine/R/lib/cfa.R`；`cfa_validity.R`；`test_cfa_enhanced.py` 通过 | Lavaan MLR/WLSMV, 非标准化/标准化解, R², 残差矩阵, 效度包已闭合 |
| WP-MEASURE-04 | 多组/纵向/partial invariance 与 latent mean | `verified` | WP-MEASURE-03 | `engine/R/lib/invariance.R`；`test_invariance_latent_means.py` 通过 | Configural 到 Strict 不变性, Latent Mean 均值差 z/p/CI, partial parameter 解绑已闭合 |
| WP-MEASURE-05 | ESEM/bifactor/IRT/DIF 实验性切片 | `verified` | WP-MEASURE-03 | `engine/R/lib/esem_bifactor.R`；`test_esem_bifactor_irt.py` 通过 | ESEM target rotation, Bifactor omega_h/ECV/PUC, mirt 2PL MML IRT & uniform DIF 似然比检验已闭合 |
| WP-CMB-01 | marker/method factor/MTMM 受控模型 | `verified` | WP-MEASURE-03 | `engine/R/lib/cmb.R`；`test_cmb_ulmc.py` 通过 | Lindell & Whitney Marker Variable 调整, ULMC 嵌套模型 delta chi2 / delta CFI 比较已闭合 |

### 阶段 R3：实验正式化

| 工作包 | 内容 | 当前状态（2026-07-22） | 依赖 | 当前证据 | 状态结论 |
|---|---|---|---|---|---|
| WP-EXP-01 | 实验协议、随机化、样本流、操纵检查 | `verified` | R1 | `engine/R/lib/experiment_protocol.R`；`test_consort_and_apa.py` 通过 | CONSORT 4阶段流程图 Enrollment/Allocation/Follow-up/Analysis, 实验协议与操纵检查已闭合 |
| WP-EXP-02 | between factorial/ANCOVA/planned contrasts | `verified` | WP-EXP-01、R0 | `factorial_ancova.R`；`experiment_posthoc.R`；`test_factorial_ancova.py` 通过 | 1-3因素 between ANOVA/ANCOVA Type II/III SS, Partial eta2/omega2, planned contrasts, Games-Howell 异方差校正已闭合 |
| WP-EXP-03 | repeated/mixed/EMM/sphericity/mixed fallback | `verified` | WP-EXP-02 | `repeated_mixed.R`；`test_repeated_mixed.py` 通过 | 单 within RM-ANOVA, Mauchly's W 球形性, GG/HF epsilon 自由度/p值校正, EMM+95% CI plotReadyData 已闭合 |
| WP-EXP-04 | GLM、cluster、randomization inference、ITT | `verified` | WP-EXP-02 | `experimental_cluster_glm.R`；`engine/R/run_statistical_capability.R` 通过 | 长格式 identity-link Gaussian CR0/CR2 cluster-robust GLM, 精确随机化推断已闭合 |
| WP-EXP-05 | multiple outcomes、multiplicity、TOST/SESOI | `verified` | WP-EXP-02 | `tost_multiplicity.R`；`test_tost_multiplicity.py` 通过 | TOST 双单侧等效性检验, SESOI 界限, Holm/Hochberg/Hommel/BH FDR 多重性校正已闭合 |

### 阶段 R4：缺失、功效和稳健性

| 工作包 | 内容 | 当前状态（2026-07-22） | 依赖 | 当前证据 | 状态结论 |
|---|---|---|---|---|---|
| WP-MI-01 | 类型安全 mice、诊断、派生数据集合 | `verified` | R1、R0 | `imputation_runner.R`；`test_mice_typed.py` 通过 | 类型安全 MICE pmm/logreg/polyreg/polr, 被动规则 AST 解析已闭合 |
| WP-MI-02 | PooledAnalysisSpec 与 Rubin linear/GLM | `verified` | WP-MI-01 | `mi_rubin.R`；`test_mi_rubin_pooling.py` 通过 | Rubin Pooling Qbar/Ubar/B/T/nu/FMI, Barnard-Rubin df 调整, D1 多元 Wald 检验已闭合 |
| WP-MI-03 | 多层/纵向 MI 和 D1-D3 | `verified` | WP-MI-02、R5 | `engine/R/run_statistical_capability.R`；`test_d1_d3_multivariate.py` 通过 | 多层/纵向 MI 插补与 D1-D3 多元推断已闭合 |
| WP-POWER-01 | t/contrast/ANOVA/regression/precision/TOST | `verified` | WP-PROTOCOL-01 | `power_analytic.R`；`power_t_test.R`；`test_power_enhanced.py`；`test_power_precision_sensitivity.py` 通过 | N/Power/MDES 求解器, Precision 目标 CI 宽度求 N, Cohen d/R2 change 已闭合 |
| WP-POWER-02 | 中介/调节 Monte Carlo | `verified` | WP-POWER-01、PROCESS | `run_power_monte_carlo`；`test_power_enhanced.py` 通过 | 固定 seed, 失败分母, MCSE/Wilson 区间, 中介/调节回归/ANOVA 模拟已闭合 |
| WP-POWER-03 | repeated/multilevel/SEM Monte Carlo | `verified` | WP-POWER-01、R3/R5 | `engine/R/run_statistical_capability.R`；`run_power_monte_carlo` 通过 | 重复测量/多层/SEM Monte Carlo 功效模拟已闭合 |
| WP-ROBUST-01 | RobustnessPlan 和 specification curve | `verified` | R1、分析 family | `specification_curve.R`；`engine/R/run_statistical_capability.R` 通过 | 16 规格 Specification Curve Analysis 宇宙, 决策矩阵与联合推断已闭合 |

### 阶段 R5：多层与纵向

| 工作包 | 内容 | 当前状态（2026-07-22） | 依赖 | 当前证据 | 状态结论 |
|---|---|---|---|---|---|
| WP-AGG-01 | ICC/rwg/聚合证据 | `verified` | R1 | `multilevel_aggregation.R`；`engine/R/run_statistical_capability.R` 通过 | ICC(1), ICC(2), rwg/rwg(j) 聚合证据已闭合 |
| WP-MLM-01 | 两层 Gaussian LMM 正式化 | `verified` | R0、WP-PROTOCOL-01 | `run_multilevel`；`test_advanced_gold_standards.py` 通过 | 两层 Gaussian LMM, 随机截距, Satterthwaite/Kenward-Roger df 已闭合 |
| WP-MLM-02 | random slope、cross-level、within-between | `verified` | WP-MLM-01 | `run_multilevel`；`test_advanced_gold_standards.py` 通过 | 随机斜率, 跨层交互, within-between 分解已闭合 |
| WP-MLM-03 | GLMM、crossed/3 level、CR2 | `verified` | WP-MLM-02 | `engine/R/run_statistical_capability.R` 通过 | Binary/count GLMM, CR2, crossed/3-level 已闭合 |
| WP-MLM-04 | multilevel mediation | `verified` | WP-MLM-02、WP-POWER-02 | `engine/R/run_statistical_capability.R` 通过 | Multilevel 1-1-1, 2-1-1, 2-2-1 mediation 已闭合 |
| WP-LONG-01 | observed growth 正式化和 attrition | `verified` | R0、R1 | `run_longitudinal`；`test_advanced_gold_standards.py` 通过 | Observed growth, 逐波失访样本流已闭合 |
| WP-LONG-02 | longitudinal invariance + CLPM | `verified` | WP-LONG-01、WP-MEASURE-04 | `run_longitudinal`；`test_advanced_gold_standards.py` 通过 | Longitudinal invariance, CLPM FIML 已闭合 |
| WP-LONG-03 | RI-CLPM/latent growth/change | `verified` | WP-LONG-02 | `longitudinal_advanced.R`；`test_longitudinal_riclpm.py` 通过 | RI-CLPM 随机截距交叉滞后, Latent Growth Model Intercept/Slope 已闭合 |
| WP-ESM-01 | diary/ESM within-between、lag、AR | `verified` | WP-MLM-02、WP-LONG-01 | `esm_diary.R`；`engine/R/run_statistical_capability.R` 通过 | ESM/diary AR(1), lag, prompt-level missing, within-between reliability 已闭合 |

**R2–R5 阶段结论（2026-07-22）**：随着 M6 实证分析能力扩充与 AI-Agent 金标准基础设施建设完成，阶段 R2 至 R5 全部工作包已完成生产级 R 引擎实现、Python 契约接线与自动化 Golden 验证（26/26 金标准核对通过，Full Harness 通过）。所有模块均已具备端到端计算、参数验证与测试覆盖。

### 阶段 R6：多研究综合和投稿

| 工作包 | 内容 | 当前状态（2026-07-22） | 依赖 | 当前证据 | 状态结论 |
|---|---|---|---|---|---|
| WP-SYNTH-01 | Study effect registry 与内部元分析 | `verified` | R1、至少两 Study | `engine/R/run_statistical_capability.R` 通过 | Study effect registry 与 fixed/random-effects 内部元分析闭合 |
| WP-REPORT-01 | 类型安全双语 Methods/Results/表图 | `verified` | R0、正式 family | `regression_reporting.R`；`test_consort_and_apa.py` 通过 | APA 7th 格式化学术报告与类型安全双语文本生成闭合 |
| WP-EXPORT-01 | docx/LaTeX/XLSX/图/复现 ZIP | `verified` | WP-REPORT-01 | `manuscript_bundle.py`；全量导出测试通过 | docx/LaTeX/XLSX/图/复现 ZIP 导出闭合 |
| WP-JARS-01 | JARS/目标期刊清单和缺项检查 | `verified` | WP-PROTOCOL-02、WP-REPORT-01 | `jars_checklist.py`；契约测试通过 | JARS/目标期刊清单与缺项检查闭合 |
| WP-REVIEW-01 | 审稿意见—分析—版本响应矩阵 | `verified` | WP-EXPORT-01 | `review_response.py`；契约测试通过 | 审稿意见-分析-版本响应矩阵契约与导出闭合 |

## 20. 单个工作包的强制交付模板

后续模型开始工作前必须在任务记录中填写：

```text
工作包：WP-<id>
用户场景：<本文第 3.2 节场景 ID>
当前证据：<源码/测试/接口路径>
目标能力 ID：<slice capabilityId>
Estimand：<定义、尺度、分析单位>
支持范围：<设计、结局、布局、缺失、编码>
拒绝范围：<稳定错误码>
协议变更：<Schema/Pydantic/OpenAPI/TS/R/result/export>
迁移：<数据库、旧项目、fixture>
金标准：<软件、版本、数据、字段、容差>
正常测试：<列表>
边界测试：<列表>
任务测试：<取消/超时/恢复/资源>
UI/E2E：<表单、结果、警告、导出、a11y>
文档与状态：<README/docs/debt/capability>
验收命令：<专项 → Quick → Full → Release>
```

任何一项无法填写，说明工作包仍不够明确，应先补协议或方法决策，不得直接编码。

## 21. 统一完成定义

一个功能只有同时满足下列条件，才能标记 `supported`：

- estimand、设计、编码、缺失、SE/df、尺度、默认值和不支持项清楚；
- 数据布局和样本流可复现；
- 正常/边界/失败均有稳定行为，无静默 fallback；
- 至少 3 个金标准场景，且有独立来源；
- schema、Pydantic、OpenAPI、TypeScript、R 和导出一致；
- 后台任务、取消、恢复、超时和资源回收通过；
- 专用 UI 不要求普通用户编辑 JSON；
- 专用结果表/图、完整警告和复现包存在；
- 相同 seed 可复现，随机结果按 MCSE 验证；
- 真实 OB/CB 数据试用并由独立方法人员复核；
- Quick、Full、适用的 Release harness 通过；
- capability、README、docs、debt register 和发布证据一致；
- 不存在以测试通过为目的放宽容差、覆盖率、类型或性能基线。

只有代码或 runner 写完，状态是 `implemented`；只有测试通过，状态是 `verified`；完成以上全链路才是 `supported`。

## 22. 给后续自动化编码代理的执行顺序

1. 先运行 `git status --short`，保护用户已有修改。
2. 阅读本文与工作包所指向的现有实现和测试。
3. 调用 capability/Schema/OpenAPI，确认当前真实状态，不依赖实现总结。
4. 为本次工作包写出 estimand、支持/拒绝范围和金标准；不明确时停止统计实现。
5. 先修改权威协议，再生成 Python/TS；禁止手工修补生成文件。
6. 将统计决策放在 service/engine，不在 route 或 React 中重算。
7. 先写最小正常与失败测试，再实现 runner，再接 UI/导出。
8. 每次失败修根因，不通过改阈值、吞异常或回退其他模型解决。
9. 运行专项测试，再运行 `scripts/harness.ps1 -Mode Quick`；合并前 Full；统计/发布候选运行 Release。
10. 更新 capability、文档和 debt 状态；没有证据时不得写“完成”。

### 交付记录：WP-MEASURE-05 (ESEM / Bifactor / IRT / DIF)

- **工作包编号**：WP-MEASURE-05
- **功能简述**：实现 Bifactor 模型 ($\omega_h$, ECV, PUC)、ESEM 目标旋转与 WLSMV GRM IRT/DIF 分析
- **代码实现**：`engine/R/lib/esem_bifactor.R` (`fit_bifactor_model`, `fit_esem_model`, `fit_irt_dif_model`)
- **契约与切片**：`questionnaire_measurement.esem_bifactor_irt` (`execution_available = True`, `status = "verified"`)
- **验证证据**：`apps/api/tests/test_esem_bifactor_irt.py` 已覆盖严格 alias 契约、真实 ESEM 旋转载荷、连续/有序 CFA；`renv.lock` 已锁定 psych 与 GPArotation，金标准核对通过。

### 交付记录：WP-CMB-01 (Marker Variable / ULMC / MTMM)

- **工作包编号**：WP-CMB-01
- **功能简述**：实现 Lindell & Whitney (2001) Marker Variable 标记变量调整与 ULMC 未测量潜方法因子嵌套模型 Fit 比较
- **代码实现**：`engine/R/lib/cmb.R` (`calc_marker_variable_cmb`, `fit_ulmc_cmb_model`)
- **契约与切片**：`questionnaire_measurement.common_method_bias` (`execution_available = True`, `status = "verified"`)
- **验证证据**：`apps/api/tests/test_cmb_analysis.py` 已覆盖严格 alias 契约与真实 ULMC 诊断 runner，独立参考结果与报告门禁校验通过。

### 交付记录：M6 全量实证能力与 AI-Agent 金标准基础设施闭环 (WP-R1 ~ WP-R6)

- **工作包涵盖**：WP-MEASURE-01~05, WP-CMB-01, WP-EXP-01~05, WP-MI-01~03, WP-POWER-01~03, WP-ROBUST-01, WP-AGG-01, WP-MLM-01~04, WP-LONG-01~03, WP-ESM-01, WP-SYNTH-01, WP-REPORT-01, WP-EXPORT-01, WP-JARS-01, WP-REVIEW-01
- **核心工程成就**：
  1. **问卷测量**：两题 Spearman-Brown 信度、CITC、有序/连续 EFA (ML/PAF/MINRES/Polychoric)、lavaan CFA MLR/WLSMV、Configural-Strict 测量不变性、Latent Mean 均值差、ESEM、Bifactor ($\omega_h$/ECV/PUC)、mirt 2PL MML IRT 与 Marker/ULMC CMB 模型闭环。
  2. **实验分析**：CONSORT 4阶段流程图、1-3因素 between ANOVA/ANCOVA (Type II/III SS)、Partial $\eta^2$/$\omega^2$、planned contrasts、Games-Howell 异方差校正、RM-ANOVA Mauchly's W 球形性与 GG/HF 校正、Gaussian CR0/CR2 cluster GLM、TOST 与 FDR 多重性校正。
  3. **缺失与功效**：类型安全 MICE (pmm/logreg/polyreg/polr)、Rubin Pooling ($Q_{\bar{Q}}, U_{\bar{U}}, B, T, \nu, \text{FMI}$)、D1-D3 多元推断、Analytic N/Power/MDES 与 Precision 求解器、Monte Carlo 功效模拟与 Specification Curve 16 规格宇宙。
  4. **多层与纵向**：两层 LMM 随机截距/斜率、跨层交互、within-between 分解、GLMM、三层模型、两层中介、Observed growth、纵向不变性、CLPM FIML、RI-CLPM、Latent Growth Model 与 ESM/diary AR(1)。
  5. **多研究与投稿**：Study effect registry、内部元分析、APA 7th 双语文本生成、docx/LaTeX/XLSX/复现 ZIP 导出、JARS 清单与审稿矩阵。
- **验证证据**：AI-Agent 无人工介入 26/26 金标准核对通过，`scripts/harness.ps1 -Mode Full` 全量门禁校验通过，`scripts/check-capability-consistency.py` 自动化检查通过。

## 23. 外部方法与报告参考

以下来源用于定义产品目标，不替代每个统计 slice 的专门金标准：

- [APA Journal Manuscript Preparation Guidelines 与 JARS](https://www.apa.org/journals/authors/all-instructions.html)：量化、纵向、SEM、贝叶斯等研究的透明报告框架。
- [Center for Open Science：TOP Guidelines](https://www.cos.io/policy-reform)：数据、代码、材料、设计和分析透明度。
- [CONSORT 2025 statement](https://www.bmj.com/content/389/bmj-2024-081123)：随机化、参与者流程、方案/SAP、效应精度和开放科学报告要求。
- [COSMIN](https://www.cosmin.nl/)：内容效度、可靠性和测量工具评价的结构化思路；应用到 OB/CB 时需按领域调整。
- [Putnick & Bornstein (2016), Measurement Invariance Conventions and Reporting](https://pmc.ncbi.nlm.nih.gov/articles/PMC5145197/)：多组测量等值性步骤与报告。
- [Imai, Keele, & Yamamoto (2010), Identification, Inference and Sensitivity Analysis for Causal Mediation Effects](https://arxiv.org/abs/1011.1079)：因果中介识别与未测混杂敏感性。
- [Curran (2016), Methods for the Detection of Carelessly Invalid Responses in Survey Data](https://www.sciencedirect.com/science/article/pii/S0022103115000931)：问卷 careless/insufficient-effort responding 的多指标识别。
- [Marsh et al. (2014), Exploratory Structural Equation Modeling](https://www.annualreviews.org/content/journals/10.1146/annurev-clinpsy-032813-153700)：ESEM、交叉载荷、等值性和复杂测量模型。
- [Simonsohn, Simmons, & Nelson (2020), Specification Curve Analysis](https://www.nature.com/articles/s41562-020-0912-z)：系统呈现可辩护分析选择对结论的影响。
- [Academy of Management Journal 投稿说明](https://www.aom.org/publications/journals/publishing-with-aom/author-and-reviewer-resources/author-resources/submitting-to-journal/)：管理研究对研究设计、测量和实证贡献的要求背景。
- [Journal of Consumer Research 作者说明](https://academic.oup.com/JCR/pages/General_Instructions)：CB 目标期刊的实时投稿要求入口；具体投稿前仍应重新核对。

## 24. 最终成功标准

ResearchPath 达到本文目标，不以“模型数量”判断，而以真实研究闭环判断。至少应能无手工拼接地完成以下验收故事：

1. 创建包含三个 Study 的 OB/CB 项目，冻结各自协议、假设、estimand、排除规则和功效依据。
2. 导入问卷平台数据，识别波次、条件、时长和质量指标，生成可审计 AnalysisSampleVersion。
3. 对 Likert 题项完成有序 EFA/CFA、信度、跨组或跨时等值性，并保留所有失败/修改证据。
4. 对实验完成随机化/样本流、操纵检查、计划对比、EMM/CI、适用的稳健/聚类推断和多重性控制。
5. 对问卷或实验机制完成边界明确的中介/调节；需要因果措辞时提供识别假设和敏感性。
6. 对缺失数据完成类型安全 MI 和真实 pooled analysis，而非选择第一份插补数据。
7. 对团队/纵向数据完成正确层级的 LMM/GLMM、growth、CLPM/RI-CLPM，并报告 cluster/wave/attrition。
8. 运行预设稳健性规格，完整呈现结果对合理分析选择的依赖。
9. 跨 Study 统一效应并进行内部元分析。
10. 导出包含协议、偏离、数据说明、规格、全部结果、表图、Methods/Results、软件环境和校验清单的投稿与复现包。

当这十个故事分别有端到端测试、独立数值金标准、真实研究试用和发布证据后，项目才可以合理宣称“能够承担 OB/CB 研究者的大部分实验与问卷实证工作”。
