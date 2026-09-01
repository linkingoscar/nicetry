# AI-Coding 金标准剩余开发执行与验证规范

> 文档状态：可执行开发任务书
> 基线提交：`e29ed0f feat: harden golden qualification and add t-test L3 evidence`
> 编制日期：2026-07-22
> 适用范围：Golden 证据、capability registry、跨语言契约、高级分析字段化 UI、ResultBundle/导出一致性、任务生命周期、Harness、CI、性能与参数恢复
> 上位规范：`docs/18-高级统计方法开发指南与接口规范.md`、`docs/24-工程Harness与开发准则.md`、`docs/25-后续开发可执行手册.md`、`docs/27-OB-CB实验与问卷实证研究全流程能力审计及开发蓝图.md`、`docs/31-AI-Agent无人工介入金标准设立与自动核对规范.md`
> 工程事实记录：`docs/30-AI-Agent金标准自动核对基础设施开发记录.md`

## 1. 目的与使用方式

本文不是方向性路线图，而是可以直接交给 GPT-5.4 级别编码模型逐包实施的任务书。执行模型不得只生成测试夹具或改写文档；每个工作包都必须产出可执行的双参考证据、生产 SUT 结果、自动核对报告和可复现的门禁输出。

推荐一次只领取一个 capability。单次任务的输入格式如下：

```text
请按照 docs/32-AI-Coding金标准剩余开发执行与验证规范.md 实施
<capabilityId> 的完整工作包。必须从基线审计开始，完成该能力的
GoldenPlan、四类场景、独立双参考、reconciliation、freeze、SUT、
invariants、mutation report 和 release evaluation。不要降低任何阈值；
不能获得的外部证据必须明确标记为阻塞，不得伪造。
```

执行顺序采用本文第 6 节的优先级。同一 capability 未达到“能力级完成定义”前，不得宣称完成；可以将无法在当前环境取得的容器 digest 或商业软件交叉验证标为外部阻塞，但必须先完成其余可编码部分。

## 2. 当前仓库事实与剩余量

截至最新实施与门禁全量通过（2026-07-22）：

### 2.1 已完成与已验证的基础设施与工程贯通

- **板块 Ⅰ：基础设施与工程通用链 (INFRA & TRACK A/D/E)** 全量交付并通过 `scripts/harness.ps1 -Mode Quick` 快速门禁：
  - **INFRA-01**：`check-reference-independence.py` 与 `build-references.py` 完成参考运行器强隔离校验、网络套接字隔离与 `expected/` 写篡改防御；
  - **INFRA-02**：`tools/goldens/audit_sources.py` 完成全量 21 个 `data/source.json` 的 SHA-256 哈希、许可与 URL 审计，自动修复并新增 `test_source_auditor.py` 单元测试；
  - **INFRA-03**：`tools/goldens/plan.py` 实现了 GoldenPlan、Bundle 与磁盘 4-Case 场景矩阵的一致性门禁校验；
  - **INFRA-04**：`tools/goldens/normalization.py` 完成 Term 映射 (`(Intercept)` $\to$ `intercept`)、Pair 排序与因子载荷符号正向化，新增 `test_cross_engine_normalization.py`；
  - **INFRA-05**：`scripts/run-mutation-tests.py` 支持能力级突变算子，全量案例突变杀灭率达到 **100.0% (115/115 mutants killed)**；
  - **INFRA-06**：`tools/goldens/offline_replay.py` 实现了只读输入与离线哈希校验，全量 26 个 Golden Capability 离线烟弹重放通过；
  - **INFRA-07**：`evaluate_release.py` 升级实现了 Bundle 哈希与输入摘要不可逆绑定；
  - **INFRA-08 & TRACK A/D/E**：`select-affected-tests.py` 完成 git diff 精准依赖选择，`scripts/harness.ps1` 完整集成了源审计与独立性检查。

- **板块 Ⅲ：纵向 UI 与数据导出全链路贯通 (TRACK B, C, F)**：
  - **TRACK B**：交付向导基础设施 `ValidationSummary.tsx` 与 `DatasetVariablePicker.tsx`，并交付 `PowerWizard`, `ExperimentWizard`, `ImputationWizard`, `LongitudinalWizard` 可视化表达与 `AnalysisWizard.tsx` 解耦；
  - **TRACK C**：扩展 `specs/advanced-result-bundle.schema.json` 权威 `reportFacts` 模型，建立跨渠道字段核对器与导出包 ZIP 路径防逃逸测试；
  - **TRACK F**：`simulation.py` 实现 `stable_hash` 派生确定性子种子算法，验证线性回归与 t-检验参数恢复 Monte Carlo 门禁。

- **板块 Ⅱ：25 个统计能力 4-Case 金标准证据链构建（17 个能力已形成完整矩阵）**：
  这 17 个能力已形成专属 `GoldenPlan`、完整 4 场景矩阵 (`normal_typical`, `legal_complex`, `degenerate_boundary`, `expected_failure`) 和 SUT 严格断言。primary 使用 R 官方统计包或 R 侧验证，secondary 使用独立 Python 数值栈（SciPy、statsmodels、semopy、factor_analyzer 或独立闭式算法）；独立性门禁会拒绝 secondary 回调 primary/R generator。

  其中 51/68 个 case 已通过双参考 reconciliation 并冻结。以下 10 个能力的 4 个 case 均已达到共识：
  `multilevel.icc.two_level.v1`, `multilevel.lmm.within_between.v1`,
  `experiment.between.factorial.gaussian.v1`, `experiment.emmeans.planned_contrast.v1`,
  `experiment.repeated.one_within.v1`, `imputation.mice.chain_diagnostics.v1`,
  `multilevel.se.cluster_robust.v1`, `multilevel.mediation.two_level.v1`,
  `longitudinal.esm.diary_ar1.v1`, `robustness.specification_curve.matrix.v1`。

  其余 17 个 case 已保留真实跨引擎差异并标记为 `quarantined`，详细字段差异记录在各 case 的 `expected/reconciliation.json`；不得冻结、不得扩大 tolerance、不得计入无冲突 L2：
  `multilevel.lmm.two_level.gaussian.random_slope.v1`（2 case）、
  `longitudinal.ri_clpm.four_wave.v1`（2 case）、
  `measurement.cfa.continuous.mlr.v1`（3 case）、
  `measurement.cfa.ordinal.wlsmv.v1`（3 case）、
  `measurement.invariance.multi_group.v1`（3 case）、
  `measurement.efa.continuous.minres.v1`（3 case）、
  `measurement.bifactor.continuous.v1`（1 case）。

### 2.2 剩余待升级工作

- **17 个 quarantined case**：逐项校准 estimator、缺失数据、稳健 SE/df、旋转/识别和拟合指数定义；只有重新 reconciliation 达成共识后才允许 freeze。现有 tolerance 上限保持不变。
- **既有基础矩阵待补完整数据、独立双参考与全 case SUT**：`imputation.pooling.linear.rubin.v1`, `power.regression.f2.analytic.v1`, `equivalence.tost.two_sample.v1`, `experiment.randomization.inference.v1`, `experiment.posthoc.games_howell.v1`
- **批次 D（P1：测量模型）**：`measurement.cmb.ulmc.v1`, `measurement.esem.target_rotation.v1`, `measurement.irt.dif.v1`

每次开工前必须重新读取仓库事实，不能假设本文的数量永远不变：

```powershell
git status --short
git log -1 --oneline
Get-ChildItem tests/goldens -Directory
Get-ChildItem golden-plans -File
& .venv/Scripts/python.exe tools/goldens/evaluate_release.py --all `
  --report output/goldens/release-evaluation-before.json
```

最后一条命令允许非零退出；判断依据是生成的 JSON 中每个 capability 的 `qualificationStatus` 和 `reasons`，而不是把非零退出误判为工具故障。

## 3. AI-Coding 权限边界

### 3.1 可以由编码模型完整完成的事项

在依赖可安装、数据许可证允许且运行时可用时，编码模型可以独立完成：

1. 审计现有 manifest、分析规范、生产适配器及输出 schema。
2. 编写和校验 GoldenPlan。
3. 设计确定性参数夹具、合成数据和公开数据的固定切片。
4. 编写 primary/secondary 独立参考 runner、输出归一化器和 session-info 记录。
5. 编写生产 SUT 适配器，或将现有 adapter 接到真实 service/engine；不得以参考 runner 冒充 SUT。
6. 编写 comparator、方法不变量、失败原因码、回归测试和突变算子。
7. 运行 reconcile、freeze、SUT、verify、invariants、mutation 和 harness，并保存机器可读报告。
8. 编写容器文件、锁文件、离线缓存脚本和 CI 配置；环境具有容器运行能力时，可生成并验证 digest。
9. 修复工具链中妨碍确定性、隔离性或证据完整性的缺陷，但必须添加回归测试。

### 3.2 只能准备材料、不能自行宣称完成的事项

以下事项需要真实外部条件。编码模型可以生成操作说明和待签记录，但不得合成证据：

- 独立统计专家对 estimand、边界和方法定义的正式签字。
- Mplus、Stata、SPSS、SAS、G*Power 等未授权商业工具的真实输出。
- 受限数据的访问授权、再分发许可或伦理审批。
- 没有 Docker/Podman 时的真实镜像 digest、离线容器重放和供应链 attestation。
- 没有组织凭据时的签名、受保护分支设置、远程 CI 管理或制品发布。
- 用固定测试切片证明一个方法在所有科研场景中的理论有效性。

遇到上述阻塞时必须：完成所有不依赖该条件的代码；在 release evaluation 的 `reasons` 中保留失败；新增一份包含所需命令、预期文件、责任角色和验证方式的阻塞说明；不得填入占位 digest、虚构版本号或伪造截图。

## 4. 不可违反的实施约束

1. 先读 `AGENTS.md`、`docs/24-工程Harness与开发准则.md`、`docs/31-AI-Agent无人工介入金标准设立与自动核对规范.md` 和目标 capability 的全部现有文件。
2. service/engine 不得导入 `app.api` 或 `app.main`；HTTP 错误翻译留在 route，统计决策留在 service/engine。
3. 若改动跨语言契约，JSON Schema、Python contract、TypeScript type 必须同步。
4. 不得提高 tolerance、coverage、类型、bundle、性能或统计容差来绕过失败。
5. 浮点 tolerance 必须有来源：闭式误差分析、独立引擎实测差、Monte Carlo error 或算法收敛误差。禁止直接填写“看起来能过”的数值。
6. primary 与 secondary 必须在算法、语言或软件栈上实质独立。两个 runner 复制同一公式代码、共享核心函数或读取同一 expected JSON 均不独立。
7. `sut/normalized-output.json` 必须通过生产 adapter 生成；不得复制 primary/secondary/expected 文件。
8. 每个 case 的所有证据文件在 freeze 后必须由 `provenance/hashes.json` 覆盖。freeze 后再编辑任何被哈希文件，必须重新运行完整流水线。
9. expected failure 是稳定契约：必须核对 `status`、机器可读 `reasonCode` 和必要的消息字段；不能只接受“抛了异常”。
10. 新测试数据不得写入仓库根目录。临时文件和报告写入被忽略的 `output/` 或系统临时目录。
11. 工作区若有无关用户改动，必须保留并绕开；不能 reset、checkout 或覆盖。

## 5. 每个 capability 的标准交付结构

目标结构如下。四个 case 名应表达统计含义，不得只写 `case1` 至 `case4`。

```text
golden-plans/<capabilityId>.yaml
tests/goldens/<capabilityId>/
  bundle.yaml
  provenance/
    mutation-report.json
    offline-reproduction.json        # 真实离线重放后才可生成 passed
  cases/
    <normal_case>/
    <complex_case>/
    <boundary_case>/
    <failure_case>/
      manifest.yaml
      data/input.csv
      data/source.json
      data/LICENSE.txt               # 自有/合成夹具也应说明授权
      spec/analysis-spec.json
      reference/primary/run.py|run.R
      reference/primary/normalized-output.json
      reference/primary/session-info.txt
      reference/secondary/run.py|run.R
      reference/secondary/normalized-output.json
      reference/secondary/session-info.txt
      expected/expected.json
      expected/reconciliation.json
      expected/invariants.json       # 对该场景适用时
      sut/run.py
      sut/normalized-output.json
      sut/provenance.json
      provenance/hashes.json
```

### 5.1 GoldenPlan 最低内容

每个计划必须通过：

```powershell
& .venv/Scripts/python.exe tools/goldens/plan.py `
  --capability <capabilityId> --validate
```

并明确以下字段：

- `estimand.unit`：观测、被试、聚类、项目、时间点或参数的统计单位。
- `estimand.scale`：原始、标准化、概率、logit、Fisher-z 等尺度。
- `estimand.targets`：所有必须比较的叶节点路径所代表的量。
- `support`：结果类型、层级数和自由度/估计方法。
- `reject`：不支持、不可识别、数据不足和非法输入边界。
- `evidencePlan.primary/secondary`：工具及其独立性来源。
- `cases` 与 `scenarioTypes`：四类场景一一覆盖。
- `requiredFields`：成功与失败输出中不能缺失的字段。
- `tolerancePolicy`：引用项目内已定义策略或新增有测试的策略名。

### 5.2 Case manifest 最低内容

每个 manifest 必须包含有效的 `identity`、`scenarioType`、dataset hash/行列数、spec、双参考、comparison rules、evidence levels 和空的 unresolved conflicts。数值字段必须逐项声明 comparator；关键离散字段必须 `exact`。

容器化正式证据中，两个 reference 均应填写真实 `containerDigest: sha256:...`。本地开发阶段可以缺省，但缺省状态不得被报告成 RC。

### 5.3 数据来源规范

`data/source.json` 至少包含 sourceId、sourceType、title、publisher、canonicalUrl、retrievedAt、version、license、sha256、authorityScore、executabilityScore、sourceTrustScore、recommendation、allowedUse 和 notes。

- 合成数据：写明随机生成机制、seed、参数和不含真实个人信息。
- 参数夹具：写明它是 deterministic parameter fixture，不能冒充外部公开数据。
- 公开数据：canonical URL 必须可定位到具体版本；记录原始 hash、固定切片规则和许可证。
- 不得把仓库内文档 URL 写成外部数据权威来源；它只可用于自有确定性夹具的规范来源。

## 6. 25 个剩余 capability 的优先级和场景矩阵

优先级定义：P0 为闭式或可穷举能力，可快速形成可靠范本；P1 为成熟统计包可双实现能力；P2 为复杂潜变量、纵向或模拟能力。每个条目中的四个场景都是最低要求，可增加但不能删除。

### 6.1 P0：闭式、代数或可穷举能力

| Capability | 现有 case | 新增/保留四场景 | 双参考建议 | 关键验证量 |
| --- | --- | --- | --- | --- |
| `imputation.pooling.linear.rubin.v1` | `rubin_standard` | normal：标准多重插补池化；complex：不等 within variance；boundary：between variance 为 0；failure：少于 2 个插补或 df 非法 | primary：R `mice::pool.scalar`；secondary：Python 按 Rubin/Barnard-Rubin 独立公式 | pooled estimate、within/between/total variance、relative increase、df、CI |
| `power.regression.f2.analytic.v1` | `regression_f2_standard` | normal：中等 f²；complex：多 tested predictors 与较高 alpha；boundary：f²=0；failure：u≥N-1 或非法 power | primary：R `pwr::pwr.f2.test`；secondary：SciPy noncentral-F 独立求解 | u、v、N、lambda、critical F、power；单调性 |
| `multilevel.icc.two_level.v1` | `icc_two_level_balanced` | normal：正方差；complex：不平衡 cluster；boundary：组间方差为 0；failure：负方差/单 cluster | primary：R variance decomposition；secondary：Python 显式公式/ANOVA moment estimator | variance components、ICC、design effect；标签置换 |
| `equivalence.tost.two_sample.v1` | `tost_two_sample_equivalence` | normal：等价成立；complex：不等样本量；boundary：CI 端点等于界值；failure：lower≥upper/样本不足 | primary：R `TOSTER`；secondary：SciPy t-CDF 独立公式 | 两个单侧 t/p、CI、equivalent 判定、严格边界语义 |
| `experiment.randomization.inference.v1` | `randomization_inference_exact` | normal：小样本精确枚举；complex：分层/受限分配；boundary：统计量全相同；failure：assignment 与设计不一致 | primary：R 枚举；secondary：Python `itertools` 独立枚举 | 分配空间大小、观察统计量、单双侧 p、seed 不应影响 exact |
| `experiment.posthoc.games_howell.v1` | `games_howell_unequal_var` | normal：三组异方差；complex：严重不等 n；boundary：均值相同；failure：组样本量<2 | primary：R `rstatix`/`PMCMRplus`；secondary：Python studentized-range 公式 | pair、difference、SE、df、q、p adjusted、CI；pair 顺序映射 |
| `multilevel.lmm.within_between.v1` | `lmm_group_mean_centering` | normal：平衡组；complex：不平衡与不同组均值；boundary：within variation 为 0；failure：缺 cluster id | primary：R `lme4`；secondary：Python `statsmodels` MixedLM | within/between coefficient、SE、variance components；中心化恒等式 |

P0 额外完成条件：所有闭式/枚举场景必须有至少一个无需 primary 包核心函数的 secondary 算法；zero-effect/zero-variance 边界不得产生 NaN 或隐式除零；非法输入必须在执行统计计算前稳定拒绝。

### 6.2 P1：成熟模型和实验设计能力

| Capability | 现有 case | 新增/保留四场景 | 双参考建议 | 关键验证量 |
| --- | --- | --- | --- | --- |
| `experiment.between.factorial.gaussian.v1` | `toothgrowth_factorial` | normal：平衡 2×2；complex：不平衡含交互；boundary：零残差或空效应；failure：空 cell/秩亏 | primary：R `lm`/`car::Anova`；secondary：Python statsmodels | term mapping、SS/df/MS/F/p、effect size、contrast coding |
| `experiment.emmeans.planned_contrast.v1` | `moore_ancova_contrasts` | normal：均衡 contrast；complex：非正交权重与协变量；boundary：零权重；failure：权重长度/和约束非法 | primary：R `emmeans`；secondary：Python design matrix + covariance 公式 | estimate、SE、df、t、p、CI；权重缩放响应 |
| `multilevel.lmm.two_level.gaussian.random_slope.v1` | `sleepstudy_random_slope` | normal：随机截距斜率；complex：不平衡且相关随机效应；boundary：斜率方差趋零；failure：不可识别/每组观测不足 | primary：R `lme4`；secondary：statsmodels MixedLM | fixed effects、VCOV、random SD/correlation、logLik、convergence |
| `measurement.efa.continuous.minres.v1` | `efa_minres_harman` | normal：清晰双因子；complex：交叉载荷；boundary：近奇异相关矩阵；failure：非正定/因子数非法 | primary：R `psych::fa`；secondary：Python 独立 MINRES 或 `factor_analyzer`（先证明非同源） | communalities、uniqueness、loadings、fit；符号/列置换对齐 |
| `measurement.cfa.continuous.mlr.v1` | `cfa_hs1939_mlr` | normal：可识别 CFA；complex：非正态稳健 SE；boundary：近 Heywood；failure：不可识别模型 | primary：R `lavaan` MLR；secondary：semopy/独立 sandwich（需映射定义） | estimates、robust SE、scaled χ²、df、CFI/TLI/RMSEA/SRMR |
| `experiment.repeated.one_within.v1` | `obrien_kaiser_repeated` | normal：完整平衡；complex：违反球形性；boundary：相关=1 附近；failure：缺失 cell/重复键 | primary：R `afex`；secondary：Python statsmodels + 独立 GG/HF epsilon | uncorrected/GG/HF df、F、p、epsilon；被试行序不变 |
| `multilevel.se.cluster_robust.v1` | `cluster_robust_cr2` | normal：足够 clusters；complex：不平衡 leverage；boundary：单例 cluster；failure：clusters 太少/秩亏 | primary：R `clubSandwich` CR2；secondary：Python sandwich 线性代数实现 | coefficient、CR2 SE、Satterthwaite df、t/p、cluster count |

P1 额外完成条件：必须解决跨引擎参数名、contrast coding、因子符号/顺序、似然常数和自由度定义差异。允许在归一化层做有理论依据的映射，不允许删除不一致字段。不能统一的字段必须进入 reconciliation conflict 并保持非 RC。

### 6.3 P2：复杂潜变量、纵向、插补和稳健性能力

| Capability | 现有 case | 新增/保留四场景 | 双参考建议 | 关键验证量 |
| --- | --- | --- | --- | --- |
| `measurement.cfa.ordinal.wlsmv.v1` | `cfa_ordinal_wlsmv` | normal：3+级有序题；complex：不平衡 thresholds；boundary：稀疏类别；failure：单类别/非正定 polychoric | primary：lavaan WLSMV；secondary：OpenMx/独立 polychoric + DWLS | thresholds、loadings、robust fit、scaling correction |
| `measurement.invariance.multi_group.v1` | `invariance_configural_metric` | normal：configural；complex：metric/scalar 序列；boundary：极小 ΔCFI；failure：组内不可识别 | primary：lavaan；secondary：semopy/OpenMx | 每层 χ²/df/fit、delta metrics、约束集合、判定 |
| `measurement.bifactor.continuous.v1` | `bifactor_continuous_standard` | normal：一般+组因子；complex：不等组负荷；boundary：组方差近零；failure：交叉约束不可识别 | primary：lavaan；secondary：OpenMx/semopy | loadings、factor covariance constraints、omegaH、ECV、fit |
| `longitudinal.ri_clpm.four_wave.v1` | `ri_clpm_four_wave_standard` | normal：稳定四波；complex：cross-lag 不对称；boundary：RI 方差近零；failure：少于四波/不可识别 | primary：lavaan；secondary：OpenMx/semopy，固定同一参数化 | RI variances、autoregressive/cross-lag paths、covariances、fit |
| `measurement.irt.dif.v1` | `irt_2pl_dif` | normal：无 DIF 基线；complex：uniform+nonuniform DIF；boundary：极小 DIF；failure：组内无变异/未锚定 | primary：R `mirt`；secondary：Python IRT 或显式 likelihood optimizer | a/b、DIF contrast、LR/Wald、p adjustment、anchor set |
| `measurement.esem.target_rotation.v1` | `esem_target_rotation` | normal：目标矩阵清晰；complex：交叉载荷；boundary：旋转局部不唯一；failure：target 维度错误 | primary：R `MplusAutomation` 替代时用 lavaan/EFA 开源路径；secondary：Python rotation | rotated loadings、target loss、factor correlations、fit；Procrustes 对齐 |
| `measurement.cmb.ulmc.v1` | `cmb_ulmc_marker` | normal：marker 方法因子；complex：不等 marker loading；boundary：方法方差为 0；failure：未识别方法因子 | primary：lavaan；secondary：OpenMx/semopy | trait/method loadings、method variance、fit、identification status |
| `imputation.mice.chain_diagnostics.v1` | `mice_chain_diagnostics` | normal：稳定链；complex：多变量缺失；boundary：无缺失/零方差；failure：不支持类型/链不足 | primary：R `mice`；secondary：Python independent diagnostics over frozen chains | chain mean/SD、R-hat 或自相关、iteration count、seed、warnings |
| `robustness.specification_curve.matrix.v1` | `specification_curve_multiverse` | normal：小型全矩阵；complex：有互斥规格；boundary：单规格；failure：零合法规格 | primary：R 枚举；secondary：Python 独立枚举和拟合 | total/legal/failed specs、ordered estimates、median/share-significant、exclusion reasons |
| `longitudinal.esm.diary_ar1.v1` | `esm_diary_ar1` | normal：平衡 AR(1)；complex：不规则时间/缺测；boundary：rho=0 或近 1；failure：每人时间点不足 | primary：R `nlme`/`glmmTMB`；secondary：Python state-space/GEE（定义一致后） | fixed effects、rho、variance、time mapping、convergence |
| `multilevel.mediation.two_level.v1` | `two_level_mediation` | normal：2-1-1 mediation；complex：within/between 分解；boundary：a 或 b=0；failure：层级/cluster 不足 | primary：R multilevel SEM；secondary：Python product-of-coefficients + bootstrap/MC | a/b/c'、indirect/direct/total、SE/CI、level attribution |

P2 额外完成条件：明确“该固定参数化与固定数据切片”的支持范围。不得因为一个简化 runner 能输出数字，就宣称覆盖所有 WLSMV、ESEM、RI-CLPM、DIF 或多层中介变体。含旋转或标签不确定性的能力必须实现可验证的对齐算法；含随机链、bootstrap 或 Monte Carlo 的能力必须固定 seed、保存 RNG/迭代配置并以 MCSE 推导容差。

## 7. 单个 capability 的标准实施流程

### 阶段 A：基线审计

1. 列出目标目录所有文件并读取 bundle、case manifest、spec、reference runner、SUT runner 和生产 adapter。
2. 从生产代码反向确认真实输出字段、失败类型和 capability registry；不能只依据 expected JSON 猜测契约。
3. 运行目标能力当前的 SUT、verify 和 evaluation，保存 before 报告到 `output/goldens/`。
4. 检查 primary runner 是否调用生产实现、expected 文件或共享核心函数；若是，登记 `REFERENCE_NOT_INDEPENDENT` 并重写。
5. 审核 `source.json` 的 hash、许可证和 URL 是否与实际 input 一致。

最低基线命令：

```powershell
& .venv/Scripts/python.exe tools/goldens/sut_runner.py --capability <capabilityId>
& .venv/Scripts/python.exe tools/goldens/verify.py `
  --capability <capabilityId> --require-sut
& .venv/Scripts/python.exe tools/goldens/evaluate_release.py `
  --capability <capabilityId> `
  --report output/goldens/<capabilityId>-before.json
```

### 阶段 B：计划与契约

1. 新建 `golden-plans/<capabilityId>.yaml`，四类场景全部显式列出。
2. 把 estimand 定义到可比较叶节点，不用“模型结果”“统计量”等笼统词。
3. 列出支持域和拒绝域；failure case 至少覆盖最高风险拒绝条件。
4. 先决定跨引擎参数化与归一化映射，再编写 runner。
5. 若新增 reason code 或字段，同步 schema/Python/TypeScript 契约和测试。

阶段门禁：GoldenPlan validate 通过，所有新 case ID 唯一，bundle 和 plan 的 case 集合一致。

### 阶段 C：四类场景与来源

1. `normal_typical`：代表官方支持域的常规输入，数值不应退化。
2. `legal_complex`：仍合法但包含不平衡、非正交、相关、缺测或复杂约束。
3. `degenerate_boundary`：零效应、近奇异、方差边界、稀疏类别等合法或明确拒绝的边界。
4. `expected_failure`：稳定的非法/不支持输入，验证结构化失败契约。

合成数据必须由可重复脚本或明确公式产生。若保留生成脚本，应将脚本本身纳入 hash；禁止每次运行随机改写冻结 input。

### 阶段 D：独立双参考

1. primary 与 secondary 分别读取 `data/input.csv` 和 `spec/analysis-spec.json`，各自计算输出。
2. 二者只能共享输入 schema 和最终 JSON 字段定义，不能共享统计核心实现。
3. runner 必须在 case 目录之外不能意外读取 expected 或 SUT 输出；添加独立性静态检查和针对越界读取的回归测试。
4. 输出必须先归一化再 reconcile；保留原软件版本、包版本、平台、命令、seed 和警告。
5. 开发期可使用 `--no-docker`，但正式证据必须使用只读输入、无网络、固定依赖和不可变 digest 的容器路径。

开发运行：

```powershell
& .venv/Scripts/python.exe tools/goldens/build-references.py `
  --capability <capabilityId> --no-docker
& .venv/Scripts/python.exe scripts/check-reference-independence.py
```

正式运行时去掉 `--no-docker`。若容器不可用，保留非 RC，不得让 subprocess 报告冒充容器离线证明。

### 阶段 E：Reconcile 与 tolerance 证明

```powershell
& .venv/Scripts/python.exe tools/goldens/reconcile.py `
  --capability <capabilityId>
```

每个比较路径必须满足：

- exact 字段完全一致；
- 数值差异低于有依据的 abs/rel tolerance；
- primary/secondary 均包含 required fields；
- 无未解释的冲突；
- failure 场景 reasonCode 一致。

容差证据必须记录在 plan、manifest 注释可追溯位置或专用 policy 文件中。对确定性闭式公式，默认目标是 `1e-8` 或更严，但最终值由误差分析决定；对迭代模型应通过多平台重复运行与收敛误差确定；对模拟结果使用 `k * sqrt(MCSE_primary² + MCSE_secondary²)` 类规则并记录 k。

### 阶段 F：Freeze、SUT 与严格核对

```powershell
& .venv/Scripts/python.exe tools/goldens/freeze.py `
  --capability <capabilityId>
& .venv/Scripts/python.exe tools/goldens/sut_runner.py `
  --capability <capabilityId>
& .venv/Scripts/python.exe tools/goldens/verify.py `
  --capability <capabilityId> --require-sut
```

验收要求：四个 case 均执行；SUT provenance 能定位生产 adapter 和版本；verify 不允许 missing SUT；篡改 input、spec、reference output 或 expected 后 verify 必须失败；恢复后重新 freeze 并通过。

### 阶段 G：不变量与突变测试

先为每个 case 选择适用的不变量：

- 行重排：所有不依赖顺序的表格方法。
- cluster/group 标签置换：多层、多组和分层随机化方法。
- 因子列/符号置换对齐：EFA、ESEM 和部分潜变量模型。
- 对比权重缩放：planned contrast。
- 线性变换响应：线性模型、效应估计和中介路径。
- 零效应、单调性、范围约束：power、ICC、p value、概率和方差。
- seed 重放：MICE、bootstrap、模拟和随机化抽样。

运行：

```powershell
& .venv/Scripts/python.exe tools/goldens/invariants.py `
  --case <caseId>
& .venv/Scripts/python.exe scripts/run-mutation-tests.py `
  --capability <capabilityId> --write-reports
```

每个 capability 至少注入以下关键突变中的适用项：字段删除、符号翻转、尺度倍乘、df ±1、p 值替换、reasonCode 替换、分组标签错配、参数顺序交换、收敛状态伪造、容差边界外漂移。关键突变必须全部被杀死，整体 mutation score 必须 ≥0.85。突变报告必须由脚本生成，不得手写 passed。

### 阶段 H：离线重现与 RC 评估

离线证据的含义是从固定镜像和本地输入开始，在网络禁用状态下重新生成双参考并得到同一规范化输出；仅仅“当前电脑无网络也能打开 expected JSON”不算重现。

`offline-reproduction.json` 至少记录 schemaVersion、capabilityId、generatedAt、镜像 digest、networkDisabled、readOnlyInputs、executedCases、output hashes、status 和失败详情。只有命令真实成功后才能写 `status: passed`。

```powershell
& .venv/Scripts/python.exe tools/goldens/evaluate_release.py `
  --capability <capabilityId> `
  --report output/goldens/<capabilityId>-after.json
```

能力可宣称 RC 的必要条件：GoldenPlan 完整；四类场景存在；双参考独立且均可执行；strict provenance 通过；reconciliation 通过；SUT 严格核对通过；mutation report 达标；offline reproduction 通过；所有 reference 有真实 immutable container digest；无 unresolved conflicts。

## 8. 基础设施级剩余工作包

以下工作不属于某一个统计能力，但仍可由 AI-coding 完成，应在 P0 能力铺开前后并行推进。

### INFRA-01：参考运行器强隔离

目标：确保 reference runner 不能读取 expected、SUT、其他 reference 输出或联网下载依赖。

实施要求：

- Docker/Podman 路径使用固定 digest 镜像，不使用 `latest`。
- input/spec 只读挂载，输出目录单独可写；根文件系统尽可能只读。
- 禁网、非 root、限制 CPU/内存/PID、设置超时。
- local `--no-docker` 明确标记为 development evidence，不能生成 offline passed。
- 拒绝包含路径逃逸、shell 注入或工作区外写入的 manifest command。
- 增加恶意 runner 回归测试：读取 expected、写入 data、访问网络、无限循环、超预算，均应失败且输出稳定 reason code。

验收：相关单元测试通过；`build-references.py --no-docker` 与容器模式报告能被机器区分；release evaluator 不接受 local subprocess 作为容器证明。

### INFRA-02：来源与许可证审计器

目标：自动发现缺失/占位/不一致的 `source.json` 和 LICENSE。

实施要求：校验 source schema、input hash、URL/version、license、allowedUse、分数范围、retrievedAt 时区；检测同一个 sourceId 对应不同内容；检测公共数据被错误标为自有 fixture；提供 `--all` 和 JSON report；接入 Quick harness。

验收：对缺 hash、错误 hash、未知许可证、占位 URL、重复 sourceId 的测试夹具均报错；26 个现有 capability 的真实问题被报告而非静默跳过。

### INFRA-03：GoldenPlan/Bundle/Case 一致性门禁

目标：plan、bundle 和磁盘 case 集合完全一致。

实施要求：校验 capabilityId、methodFamily、case ID、scenarioType、requiredFields、reject reason code、evidence plan 与 manifest reference；发现孤儿 case、重复场景或少于四类时失败。

验收：对每种结构漂移都有单元测试；P0 能力加入后 Quick harness 自动执行该门禁。

### INFRA-04：跨引擎归一化和对齐库

目标：统一处理 term 名、contrast coding、pair 顺序、factor 符号/列置换、group label 和 parameter table 排序。

实施要求：归一化只能消除表示差异，不能改变统计值；每个转换返回 mapping/provenance；出现一对多或不确定匹配时失败；禁止按 expected 值选择最有利排列。

验收：golden fixtures 覆盖合法重排、符号翻转、歧义匹配、缺参数和多余参数；歧义必须失败。

### INFRA-05：能力级 mutation 生成器

目标：从 manifest comparison paths 与方法插件生成针对性 mutants，而不只做通用 JSON 扰动。

实施要求：为 power、ANOVA/contrast、multilevel、measurement、imputation/longitudinal 五类注册突变；关键字段突变列表版本化；报告列出 mutant ID、目标路径、变换、是否被杀和失败核对器。

验收：所有能力均至少有一个关键 mutant；没有适用 mutant 时 evaluator 失败；报告不可通过减少 mutant 总数规避历史失败。

### INFRA-06：离线重放编排器

目标：一条命令对 capability 构建/拉取固定镜像、断网重放、比较输出并写离线报告。

实施要求：镜像引用必须解析为 digest；第一次准备缓存可联网，正式重放必须禁网；验证输入只读和工作区无未授权写入；记录命令、运行时版本、资源使用、输出 hashes；失败不写 passed。

验收：断网重放成功样例、缺镜像、digest 不符、网络访问、写输入和输出漂移都有集成测试。

### INFRA-07：发布评估的解释性和防伪

目标：每个非 RC 原因可定位到 capability/case/file/check，并防止手写报告冒充执行结果。

实施要求：报告带 schema、tool version、input evidence hashes；mutation/offline 报告与当前 bundle hash 绑定；过期报告自动失效；退出码与 JSON status 一致。

验收：修改 freeze 后文件、复用其他 capability 报告、回拨 generatedAt、伪造 digest 均被拒绝。

### INFRA-08：CI 和周期漂移检测

目标：PR 做受影响能力核对，定期任务做全量双参考重建和依赖漂移检测。

实施要求：使用 `scripts/select-affected-tests.py` 选择 PR 范围；定期全量任务不自动覆盖 frozen expected；发现 drift 生成差异制品并隔离；只有明确 review 流程才能更新基线。

验收：PR 修改 schema/production adapter 能选中相关 Golden；依赖升级导致输出变动时 CI 失败并附 reconciliation diff；没有静默自动接受新值。

## 9. 完成定义与验证规范

### 9.1 Case 级完成定义

一个 case 只有同时满足以下条件才完成：

- manifest schema 正确、identity/status/scenarioType 正确；
- data hash、行列数、source metadata 和 license 一致；
- spec 明确 estimand、输入、方法、选项、seed 和拒绝语义；
- primary/secondary 可独立执行且输出字段完整；
- reconciliation 无未解决冲突；
- comparison rules 覆盖所有 required fields，容差有依据；
- expected 由已 reconcile 的证据冻结；
- SUT 通过生产路径生成且 provenance 完整；
- strict verify 通过；
- 适用不变量通过；
- 任意 frozen asset 被改动后 hash 门禁会失败。

### 9.2 Capability 级完成定义

一个 capability 只有同时满足以下条件才完成 AI-coding 工作：

- GoldenPlan validate 通过；
- plan、bundle 和磁盘 case 集合一致；
- 四类场景至少各一个；
- 4 个 case 全部达到 case 级完成定义；
- capability mutation report 由脚本生成，关键突变全杀死且 score ≥0.85；
- `evaluate_release.py` 的剩余失败只允许是本文 3.2 节列出的真实外部条件；若环境具备条件，则必须做到 RC；
- 目标单元/集成测试、architecture check 和 Quick harness 通过；合并前 Full harness 通过。

### 9.3 仓库级完成定义

25 个工作包与 8 个基础设施包完成后，必须运行：

```powershell
& .venv/Scripts/python.exe tools/goldens/plan.py `
  --capability <逐个 capabilityId> --validate
& .venv/Scripts/python.exe scripts/check-reference-independence.py
& .venv/Scripts/python.exe tools/goldens/build-references.py --all
& .venv/Scripts/python.exe tools/goldens/reconcile.py --all
& .venv/Scripts/python.exe tools/goldens/sut_runner.py --all
& .venv/Scripts/python.exe tools/goldens/verify.py --all --require-sut
& .venv/Scripts/python.exe tools/goldens/invariants.py --all
& .venv/Scripts/python.exe scripts/run-mutation-tests.py --write-reports
& .venv/Scripts/python.exe tools/goldens/evaluate_release.py --all `
  --report output/goldens/release-evaluation-final.json
& ./scripts/check-architecture.ps1
& ./scripts/harness.ps1 -Mode Quick
& ./scripts/harness.ps1 -Mode Full
```

说明：`plan.py` 当前没有 `--all`，必须逐个 capability 校验，或者先完成 INFRA-03 后使用新增的全量入口。`build-references.py --all` 的正式验收不得带 `--no-docker`。`harness.ps1 -Mode Release` 只在发布候选环境运行，并要求所有外部制品和容器条件真实具备。

### 9.4 必须保留的负向验证

每项功能不仅要证明“正确输入能通过”，还必须自动证明以下错误会失败：

1. 删除 required output field。
2. 把数值改到 tolerance 内与 tolerance 外，确认边界语义正确。
3. 修改 input/spec/reference/expected 后不重新 freeze。
4. primary 和 secondary 改成同一 engine 或同一路径。
5. secondary 缺失、不可执行或读取 expected。
6. SUT 缺失、SUT 直接复制 expected、SUT provenance 不完整。
7. source hash/license/URL 不一致。
8. scenarioType 缺失或 plan/bundle/case 集合漂移。
9. mutation/offline report 属于另一 capability 或早于当前 freeze。
10. failure reasonCode 错误但消息文本相似。

## 10. 每次 AI 任务的交付报告模板

执行模型完成一个工作包后，最终回复必须给出以下事实，不得只说“已完成”：

```markdown
### 实施范围
- capabilityId：
- 新增/修改 case：
- 生产路径：
- primary/secondary 及独立性说明：

### 证据
- GoldenPlan validate：PASS/FAIL
- Reference build：PASS/FAIL（container/local，digest）
- Reconciliation：x/x
- SUT strict verify：x/x
- Invariants：x/x
- Mutation：killed/total，score
- Release evaluation：qualificationStatus；剩余 reasons
- Architecture：PASS/FAIL
- Harness Quick/Full：PASS/FAIL/未运行及原因

### 文件
- 关键文件的仓库路径
- 机器可读报告路径

### 未完成与外部阻塞
- 阻塞条件、不能伪造的原因、解除阻塞所需命令和验收文件
```

如果任一必需命令未运行，必须写明“未运行”和原因；不得用“应当通过”“理论上通过”代替结果。若测试失败，先判断是本次回归还是既有失败，并提供可复现命令和最小错误摘要。

## 11. 推荐领取顺序

建议按以下批次推进，以便先用可独立验证的能力磨稳基础设施，再进入复杂模型：

1. 批次 A：`imputation.pooling.linear.rubin.v1`、`power.regression.f2.analytic.v1`、`multilevel.icc.two_level.v1`、`equivalence.tost.two_sample.v1`。
2. 批次 B：`experiment.randomization.inference.v1`、`experiment.posthoc.games_howell.v1`、`multilevel.lmm.within_between.v1`。
3. 批次 C：实验设计、EMMeans、随机斜率、重复测量和 CR2。
4. 批次 D：EFA 与连续 CFA；完成归一化/对齐基础设施后再扩展。
5. 批次 E：有序 CFA、不变性、bifactor、DIF、ESEM、ULMC。
6. 批次 F：RI-CLPM、MICE diagnostics、specification curve、ESM AR1、多层中介。
7. 每批结束运行全量 strict verify、mutation、architecture 和 Full harness；不要等 25 个能力全部改完才发现基础设施设计不适用。

批次 A 开工前优先完成 INFRA-03；批次 C 前完成 INFRA-01；批次 D 前完成 INFRA-04；任何能力申请 RC 前完成 INFRA-05、INFRA-06 和 INFRA-07；全量铺开前完成 INFRA-02 和 INFRA-08。

## 12. 禁止性结论

出现以下任一情况时，执行模型必须停止宣称该能力完成：

- 为通过核对而放宽 tolerance 或删除 comparison field。
- primary、secondary 或 SUT 之间复制 normalized output。
- 用相同核心函数包装成两个 runner，声称独立参考。
- 手写 mutation/offline passed 报告或虚构 container digest。
- 只验证一个 happy path，却把 capability 标为 L3/RC。
- 把收敛警告、不可识别、边界解或 engine 定义冲突静默丢弃。
- 公开数据缺许可证/版本/hash，或合成数据冒充权威外部数据。
- 没有实际运行验证命令，却报告 PASS。

正确的交付可以是“AI-coding 部分全部完成，但由于缺少商业软件授权/容器运行时/专家签字，release evaluation 仍非 RC”。这比制造一个表面全绿、无法审计的金标准更符合本项目的无人介入核对目标。

---

## 13. 本文剩余纵向开发总路线

第 1～12 节解决“每个统计 capability 的 Golden 是否可信”。本节之后解决“可信证据是否真实进入能力目录、普通 UI、任务生命周期、导出、Harness 和 CI”。这些工作都可由 AI-coding 完成，但必须按依赖顺序实施：

```text
TRACK-A：STATUS-01 → DOC-01
TRACK-B：UI-FOUNDATION-01 → UI-PWR-01 / UI-EXP-01 / UI-MI-01 / UI-LONG-01
TRACK-C：RESULT-01 → PRESENTATION-01 → PRESENTATION-02
TRACK-D：TASK-01 → TASK-02
TRACK-E：HARNESS-01 → HARNESS-02 → CI-01 → PERF-01 → EVIDENCE-01
TRACK-F：SIM-01 → SIM-02 → SIM-03

发布顺序：
power.t_test.analytic.v1 样板
→ 一个完整字段化功效切片
→ 一个完整实验切片
→ 一个完整 MI 切片
→ 一个完整纵向切片
→ 扩展到其余 capability
```

并行规则：TRACK-A 可与 Golden P0 同步；TRACK-B 必须以真实 contract 和 capability slice 为输入；TRACK-C 必须先定义唯一事实源；TRACK-E 不得在功能和测试集合仍剧烈变化时冻结性能基线；TRACK-F 不能阻塞闭式、解析或成熟包可以直接验证的 capability。

每个纵向切片必须经过以下状态，禁止跳级：

```text
implemented → wired → verified → release_candidate
```

`supported` 不属于无人工流程的自动终态。若缺少项目规定的人工方法审查或正式发布批准，AI 最多写入 `release_candidate`。

## 14. TRACK-A：能力状态、证据接线与文档事实

### STATUS-01：三轴 capability 状态模型

#### 目标

把“代码是否存在”“自动证据是否完整”“产品是否允许发布”分开表达，消除单一 `planned|experimental|supported` 无法区分 SUT 通过、Golden L1 和 RC 的问题。

#### 权威字段

在 slice 级 capability 响应中新增：

```json
{
  "engineeringStatus": "planned|implemented|wired|verified",
  "automatedEvidenceStatus": "none|partial|complete",
  "releaseStatus": "planned|experimental|release_candidate|supported",
  "executionAvailable": true,
  "evidenceSummary": {
    "qualificationLevel": "none|L1|L2|L3|RC",
    "evaluatedAt": "ISO-8601|null",
    "bundleSha256": "sha256|null",
    "caseCount": 0,
    "scenarioTypes": [],
    "blockingReasonCodes": []
  }
}
```

`status` 旧字段保留一个兼容周期，值由 `releaseStatus` 映射，不再作为内部权威字段。兼容映射必须在单一函数中实现：planned→planned，experimental/release_candidate→experimental，supported→supported。

#### 实现范围

- 修改 `apps/api/app/services/advanced_analysis.py` 的 `AdvancedCapabilitySlice`，不得在 route 中拼接状态。
- 修改 `apps/api/app/api/responses.py`、OpenAPI、生成 TypeScript 类型和前端 capability 类型。
- 新增读取机器评估摘要的 service；只读取受治理报告，不在 GET capability 请求中现场运行 Golden。
- 机器报告必须与当前 bundle hash、commit 和 evaluator schema 绑定；过期或 hash 不符时返回 `partial` 并给出 `EVIDENCE_STALE`。
- `executionAvailable` 只表示生产入口可达，不由 RC 状态推导；但不可达 slice 绝不能因存在 Golden 而显示为可执行。
- 不允许前端根据 case 数自行推断状态。

#### 状态判定

| 条件 | engineeringStatus | automatedEvidenceStatus | releaseStatus |
| --- | --- | --- | --- |
| 无 runner | planned/implemented | none | planned |
| 正常入口可达但无严格证据 | wired | none/partial | experimental |
| SUT、严格核对和适用测试通过 | verified | partial | experimental |
| evaluator 对当前 bundle 返回 RC | verified | complete | release_candidate |
| 另有正式人工发布批准 | verified | complete | supported |

#### 测试

- service 单元测试覆盖全部映射和旧字段兼容。
- contract 测试证明 JSON Schema/Pydantic/OpenAPI/TS 原子更新。
- 过期、损坏、其他 capability、其他 bundle hash 和未来 schema 报告均不得升级状态。
- capability API 不得因报告缺失而 500，应返回 `none/partial` 和稳定原因码。
- 前端用可访问文本显示三个状态，不只依赖颜色。

#### 验收

```powershell
& .venv/Scripts/python.exe -m pytest apps/api/tests/test_advanced_analysis_contracts.py -q
& .venv/Scripts/python.exe -m pytest apps/api/tests/test_golden_release_evaluation.py -q
& ./scripts/generate-contracts.ps1
& ./scripts/generate-contracts.ps1 -Check
& ./scripts/harness.ps1 -Mode Quick
```

### DOC-01：机器事实驱动的文档纠偏

#### DOC-01 目标

修复 `docs/29` 中“发布资格 26/26”与机器报告不一致的问题，并阻止同类漂移再次出现。

#### 强制术语

- `SUT x/x`：生产适配器完成执行，不表示数值正确。
- `strict verify x/x`：按冻结 expected 和 comparator 核对通过。
- `Golden L1/L2/L3`：仅表示自动证据等级。
- `Golden release_candidate x/x`：当前 bundle、环境、mutation、offline 和 provenance 全部满足 evaluator。
- `Full passed`：合并门禁通过，不等于 Release。
- `Release passed`：未跳项 Release Harness 通过，仍不自动等于人工 `supported`。

#### 实现要求

- 更新 `docs/29`，保留历史运行事实，但把“发布资格 26/26”改为当时真实等级；如无法证明，写为“严格核对 26/26，RC 未证明”。
- 新增文档一致性检查：若文档声明 `release_candidate N/N`，必须引用存在、未过期且 hash 匹配的机器报告。
- `docs/debt-register.json` 的 `closed` 只能表示该债务验收条件完成，不能被解释为 capability supported。
- README、docs/18、25、27、29、30、31、32 中的状态词必须通过统一词典检查。

#### 负向测试

伪造不存在的报告路径、篡改报告、修改 bundle 后复用旧报告、把 Full 写成 Release、把 L1 写成 RC，文档门禁都必须失败并指出文件和行号。

## 15. TRACK-B：普通用户字段化分析向导

### UI-FOUNDATION-01：共享向导契约与变量选择基础设施

#### UI-FOUNDATION-01 目标

普通模式不要求用户编辑 JSON 或输入变量 ID；JSON 仅保留在显式“专家模式”中。所有 family 复用同一数据字典、Estimand、验证摘要和 capability slice 解析机制。

#### 共享组件

```text
DatasetVariablePicker
RoleAssignmentPanel
EstimandEditor
MethodOptionsPanel
MissingDataPanel
InferenceOptionsPanel
CapabilityResolutionPanel
ValidationSummary
ExpertJsonEditor
```

变量选择器输入必须来自数据字典 API，至少显示 label、name、类型、取值水平、缺失率和角色兼容性。提交时保存稳定 ID，UI 显示人类标签。禁止自由文本输入变量 ID 作为普通模式默认路径。

`ValidationSummary` 必须展示：

- dataset/measurement/sample/protocol version；
- 参与者数、记录数、cluster 数、波次数及各波 N；
- outcome、predictor、mediator、moderator、covariate 和 grouping；
- estimand 的 population、analysisUnit、comparison、effectScale、analysisRole、causalTarget；
- 编码、参考组、缺失方法、SE、df、置信水平、多重性；
- resolved family、slice ID、executionAvailable、三个状态轴；
- spec hash、数据 hash、已知限制和稳定拒绝条件。

缺少任何无法从当前分析推导的字段时显示“未指定 + reasonCode”，不得显示伪默认值。`0`、`false` 与缺失必须区分。

#### 状态与可恢复性

- 草稿保存到受版本治理的后端对象；localStorage 只可作为恢复提示，不能成为唯一副本。
- 刷新后恢复已选 family、字段、验证结果和活动 run。
- 数据版本改变后旧草稿必须标为 stale，不能静默绑定新数据。
- 从 visual 切换到 expert JSON 再切回时，等价字段不得丢失；无法可视化的专家字段必须显式提示，不能静默删除。

#### UI-FOUNDATION-01 测试

- 组件测试覆盖键盘、screen reader label、错误聚焦和无颜色语义。
- property 测试覆盖 visual↔JSON 往返等价。
- API 测试覆盖数据版本身份绑定和 stale 草稿。
- E2E 覆盖普通用户从数据选择到成功运行，全程不编辑 JSON。

### UI-PWR-01：功效、精度和敏感性字段化向导

支持范围先限定到已真实可达的 t 检验、回归和组间 ANOVA 解析/有限 Monte Carlo slice。字段包括 solveFor、designFamily、testType、alternative、alpha、targetPower、effectSize metric/value、groups/predictors、allocation、attrition、rounding 和 seed/simulations。

强制行为：

- 一/双侧由用户显式选择；生产不支持时在提交前返回稳定错误，不自动改为双侧。
- 样本量的“每组/总计”语义在 UI 和结果中同时显示。
- effect size 输入必须显示尺度解释和允许范围。
- 不默认提供 post hoc observed power。
- Monte Carlo 显示有效/失败复制、MCSE、Wilson 区间、seed 和回代结果。
- 当前不支持的 allocation ratio、复杂 mediation/multilevel/SEM Monte Carlo 不出现在普通表单，专家请求仍稳定拒绝。

E2E 最低场景：解析求 N、求 achieved power、求 MDES、非法单侧或非整除 N、刷新恢复、取消 Monte Carlo。

### UI-EXP-01：实验分析字段化向导

字段包括 outcome、between/within factors、subject ID、covariates、layout、SS type、contrast coding、planned contrasts、post-hoc、multiplicity、SE/df、TOST SESOI 和 missing policy。

强制行为：

- planned contrast 权重按 factor level 展示并验证长度、顺序和必要约束。
- Type II/III、coding 和参考组必须在验证摘要和导出中出现。
- 重复测量宽/长格式映射必须预览，重复键、缺 cell 和被试内水平不完整在执行前拒绝。
- Games–Howell、EMM、Mauchly/GG/HF 和 TOST 只在适用设计显示。
- 不得根据显著性自动选择 post-hoc、校正或报告内容。

E2E 最低场景：factorial happy path、planned contrast、球形性警告、非法空 cell、TOST 边界、导出。

### UI-MI-01：多重插补和 pooled analysis 字段化向导

字段包括变量、类型、每变量方法、predictor matrix、m、iterations、seed、被动变量受限表达式、diagnostics 和 pooling model。

强制行为：

- `auto` 映射必须在运行前展开成 pmm/logreg/polyreg/polr 等真实方法并显示。
- 被动变量只接受 contract 已批准的受限表达式；任意 R/Python 代码必须拒绝。
- “生成插补数据集”“链诊断”“Rubin pooled linear/GLM”是不同 slice，UI 不得混写完成状态。
- 结果显示每个插补状态、失败数、within/between/total variance、df/FMI 和模型级警告。
- 任一插补损坏时 pooled run 整体失败，不忽略坏文件。

E2E 最低场景：typed MICE、无缺失边界、非法被动表达式、链诊断、pooled linear、刷新恢复。

### UI-LONG-01：纵向与有限多层字段化向导

字段包括 subject、cluster、真实 time value、wave mapping、construct/item mapping、modelType、random effects、centering、missing、estimator 和 constraints。

强制行为：

- 波次不是仅显示标签；必须保存真实 timeValue 并检测重复/不等距。
- within/between/cluster mean 是否进入模型由用户规格显式控制，禁止自动加入 `__between`。
- available-row likelihood 不得标为 lavaan FIML。
- CLPM/RI-CLPM 必须显示其个体间/个体内解释边界，不使用因果语言。
- 少波次、缺映射、不可识别、Heywood/非正定均返回稳定错误码。

E2E 最低场景：observed growth、随机斜率、within/between、RI-CLPM、少波次失败、刷新恢复和取消。

### UI 系列统一完成定义

每个 family 只有同时满足以下条件才完成：字段化 happy path；专家 JSON 仍可用但非默认；验证摘要完整；普通表单只暴露真实可执行 slice；成功/警告/失败/刷新/取消 E2E 均通过；WCAG 自动检查通过；UI 不重算统计量；导出与页面事实一致。

## 16. TRACK-C：ResultBundle、报告事实与跨渠道一致性

### RESULT-01：唯一权威事实模型

#### RESULT-01 目标

建立一个供 API、UI、图和所有导出共同消费的规范化事实层，避免每个渠道重新推导统计量。

`AdvancedResultBundle` 至少统一包含：

```text
run
bindings
sampleFlow
estimands
familyResult
diagnostics
warnings
multiplicity
provenance
tables
plots
reportFacts
```

`reportFacts` 只能引用原始数值字段路径和稳定事实模板，不保存按显著性筛选后的段落。建议结构：

```json
{
  "facts": [{
    "factId": "...",
    "kind": "estimate|fit|diagnostic|warning|sample_flow",
    "sourcePaths": ["familyResult.estimates[term=...].estimate"],
    "values": {},
    "templates": {"zh-CN": "...", "en": "..."}
  }]
}
```

模板不得写“假设成立”“机制得到证明”“完全中介”“无效应”。因果词只有 `causalTarget=true` 且识别假设完整时才允许进入事实模板，并仍应表述为估计目标而非自动结论。

#### 契约与迁移

- 先修改 `specs/advanced-result-bundle.schema.json`，再同步 Python、OpenAPI、TS。
- 旧结果缺少 reportFacts 时可用版本化迁移器从原始字段生成；迁移器不得读取 UI 格式化文本。
- `null` 必须带 reasonCode 或结构化不可估计说明。
- 原始数值与显示字符串分离；API 保留全精度，渠道层只格式化。

### PRESENTATION-01：字段级跨渠道核对器

#### 核对渠道

最低要求：API JSON、前端专用表、plot-ready 数据、Markdown、XLSX、复现 ZIP 内 JSON/manifest。docx/LaTeX 只有在项目正式支持后才进入必需矩阵。

#### 核对方法

- 为每个表格 cell、plot point/error bar、报告事实建立稳定 `fieldId` 或 `sourcePath`。
- UI 测试读取渲染值对应的 sourcePath，比较格式化前值。
- XLSX 读取实际单元格值和隐藏 provenance sheet，不以截图验证。
- Markdown 通过结构化生成记录或解析器核对，不仅搜索字符串。
- ZIP 验证成员清单、SHA、spec/result identity 和警告完整性。
- 所有预设 estimand、警告、诊断必须在适用渠道出现；不得只检查一个显著结果。

#### Golden 场景

至少覆盖：正常多结果、含 null/reasonCode、含警告、极大/极小数、Unicode 标签、无 plot、多个 estimand。每个场景注入删除字段、交换行、四舍五入越界、警告丢失和 plot CI 反向等突变，门禁必须杀死。

### PRESENTATION-02：复现包与导出安全

- 导出前验证 run ID、数据库对象身份和 result path 绑定。
- 默认不包含原数据；`includeData=true` 必须明确授权并记录。
- ZIP 成员数、总字节、单成员字节和压缩比预算在创建前/流式过程中执行。
- 导出使用临时文件原子替换，失败后无半成品；取消后清理临时目录。
- manifest 记录每个成员 SHA、MIME、大小、生成器版本、spec/result hash。
- 导出测试覆盖路径遍历、symlink/reparse point、身份错配、重复成员和资源超限。

#### TRACK-C 验收

```powershell
& .venv/Scripts/python.exe -m pytest apps/api/tests/test_advanced_export_tables.py -q
& .venv/Scripts/python.exe -m pytest -m export -q
& npm run test:web
& npm run test:e2e
& ./scripts/harness.ps1 -Mode Full
```

上述 `-m export` 在工作包实施后必须能选择到非空测试集；空选择不得算通过。

## 17. TRACK-D：任务取消、恢复、超时与资源回收

### TASK-01：统一任务生命周期契约

状态机固定为：

```text
queued → running → succeeded|failed|cancelled
queued|running → cancelling → cancelled|failed
```

要求：终态不可回退；重复取消幂等；取消请求、进程终止和数据库终态可审计；应用重启后 queued/running 任务按明确规则恢复或标记 interrupted；结果只保留一个权威副本。

任务响应至少包含 runId、status、progress、phase、cancelRequested、created/started/finished timestamps、failure reasonCode、recoverability 和 result identity。前端轮询、刷新恢复和后端状态使用同一契约。

### TASK-02：能力与资源矩阵

每个 runner family 至少有以下代表性测试：

1. queued 取消，不启动统计进程；
2. running 合作式取消；
3. 不合作进程树强制终止并替换 worker；
4. 超时返回 `ANALYSIS_TIMEOUT`；
5. 进程崩溃返回稳定失败并释放资源；
6. 应用重启后恢复/解释终态；
7. 页面刷新后恢复任务和结果；
8. 临时目录、句柄、R worker 和端口无持续增长；
9. 同一 run 并发取消/完成竞态只有一个合法终态；
10. stale run/result identity 被拒绝。

长模拟额外要求 checkpoint：完成 replication 位图、子 seed、DGP/spec hash、部分汇总和环境版本。resume 必须得到与不中断运行等价的最终汇总；若输入/hash/版本改变，拒绝恢复。

测试必须实际使用 `@pytest.mark.task`；Release 任务门禁应断言选择数量大于零。Windows 资源计数和跨平台通用测试分开标记，平台不支持时明确记录 incomplete，不能把全部资源测试 skip 后宣称 Release。

## 18. TRACK-E：Targeted Harness、CI、性能与发布证据

### HARNESS-01：单一门禁注册表

#### HARNESS-01 目标

消除 `harness.ps1` 与 `test.ps1` 公共步骤重复，并使每种模式的实际步骤、文档矩阵和发布证据从同一注册表生成。

建议新增机器可读文件：

```yaml
# config/harness-gates.yaml
gates:
  architecture:
    command: scripts/check-architecture.ps1
    modes: [quick, full, release]
  python-unit-contract:
    command: ...
    modes: [quick, full, release]
  golden-release:
    command: ...
    modes: [release]
```

注册表字段至少包含 id、command、modes、dependencies、timeout、artifact patterns、allowSkip、evidenceRequired 和 platforms。PowerShell 只负责编排，不重复硬编码步骤集合。

### HARNESS-02：Targeted 与 AutomatedEvidenceOnly

新增入口：

```powershell
./scripts/harness.ps1 -Mode Targeted -Capability <capabilityId>
./scripts/harness.ps1 -Mode Release -AutomatedEvidenceOnly -Capability <capabilityId>
```

语义：

- Targeted 根据 capability、改动文件和 impact map 运行最小可信集合；无法映射时回退到整个 family，而非空集。
- Targeted 不替代合并前 Full。
- AutomatedEvidenceOnly 生成自动 RC 证据，但不能写 `supported`；缺外部条件时状态为 failed/incomplete。
- 修改公共 Schema、shared R utility、runner runtime 或 comparator 时强制扩展到全部依赖 family。
- `scripts/select-affected-tests.py` 输出机器 JSON：选择原因、规则、fallback、测试和 Golden capability。

修复并验证 `config/test-impact-map.yaml` 中不存在的测试路径；门禁应拒绝映射到不存在文件。Quick 应执行快速 unit/contract/service 与受影响的 r_numeric/golden，而不是只做静态检查。

### CI-01：并行 CI 与最终汇总

推荐 job：Python unit/contract/service、API/migration、R numeric/Golden、task/resource、Web/type/build、E2E/a11y、docs/capability/debt、dependency audit、coverage combine、final gate。

要求：

- job 之间不重复执行同一测试集合；coverage 使用 parallel data 后统一 combine。
- 每个 job 上传 JUnit、日志和受治理产物；final gate 只汇总，不重跑。
- PR 运行受影响 Golden；main/nightly 全量；Release 运行完整 evaluator、benchmark 和资源回收。
- CI 和本地 Release 步骤差异必须显式建模，不能都叫 Release passed。
- actions 固定 commit SHA，权限最小化，失败产物也尽可能上传。

### PERF-01：性能基线与预算纠偏

当前性能文档中的 coverage budget、批准 baseline 和实测值必须统一。禁止用未完成的 Full 运行作为完整 Full 提速分母。

新基线必须记录：commit、dirty、机器/CPU/RAM、OS、Python/Node/R、worker 数和分发策略、数据规模、测试数、collection/setup/call/teardown、R 启动数、migration/fixture/generation 次数、CPU/内存/磁盘峰值、五次独立运行结果和原始报告 hash。

预算验收：

- 数值、测试数量和关键分支不减少；
- 连续 5 次无随机失败；
- 并行与串行结果一致；
- API/Full/Quick 相对目标基于完整同机基线；
- `rProcessStartMaxRelativeToBaseline` 必须有实际计数，不能只有预算字段；
- 覆盖率只引用 `docs/baselines/api-coverage.json` 的批准值，其他文档引用而不复制权威数值。

### EVIDENCE-01：逐步骤 Release 证据

升级 `scripts/release-evidence.py`，每个步骤记录 id、status、startedAt、finishedAt、duration、exitCode、command digest、stdout/stderr artifact、skip reason 和授权来源。环境增加 CPU、RAM、并行度和关键包/锁摘要；产物清单按注册表要求完整哈希。

防伪要求：必需产物缺失时 evidenceComplete=false；dirty 工作树永远不能生成正式批准证据；报告 schema/version、commit 和 run ID 绑定；失败证据保留已完成步骤；证据写入失败不能覆盖原始失败码。

#### TRACK-E 负向验收

- Targeted 空选择、impact map 无效路径、未知 capability 必须失败。
- Release 跳过依赖审计或 benchmark 必须为 incomplete 和非零退出。
- 任一 job 缺 JUnit/coverage/Golden/benchmark 必需产物，final gate 失败。
- 修改批准 baseline 但无独立变更说明，治理检查失败。
- 同一报告用于不同 commit/run ID，证据校验失败。

## 19. TRACK-F：结构化参数恢复与 Monte Carlo 门禁

### SIM-01：DGP Schema 与确定性子种子

现有 `tools/goldens/simulation.py` 只能作为原型。新增版本化 DGP Schema，不接受任意 R/Python 代码。字段至少包含 capabilityId、scenarioId、estimand、sample structure、true parameters、distribution、missingness、replications、masterSeed、stopping policy 和 resource budget。

子 seed 使用稳定哈希：

```text
seed_i = stable_hash(schemaVersion + capabilityId + scenarioId + masterSeed + replicationIndex)
```

不得使用任务执行顺序、worker ID 或简单的共享全局 RNG。串行、不同 worker 数和 resume 后每个 replication 的输入必须一致。

### SIM-02：正式 estimator、全分母与 checkpoint

- DGP 与 estimator 分离；估计必须调用目标正式计算核心或独立参考核心，不能用 OLS/ANOVA 近似冒充 LMM/CFA。
- 预定复制数是 power、coverage、Type I error 和失败率的审计分母；同时报告条件于成功拟合的 bias/RMSE，并明确分母。
- 报告 convergence、singular、Heywood、non-positive-definite 和各 failure reason。
- 计算 bias、relative bias、RMSE、coverage、Type I error、power、MCSE 和区间。
- checkpoint 原子写入，支持取消和恢复；重复 resume 幂等；损坏或 hash 不一致拒绝。
- 支持 smoke/quick/release profile，但复制数由 MCSE 目标控制；未达到 MCSE 不得标为通过。

### SIM-03：方法级参数恢复矩阵

优先顺序：CFA、Gaussian LMM、RI-CLPM/latent growth，再考虑 ESEM/bifactor、IRT/DIF、多层中介。每个方法至少包含真值为零、典型效应、较强效应、合法复杂和预期失败 DGP；多个 N/cluster/wave/category 条件用于识别样本结构敏感性。

每个发布矩阵至少验证：固定 seed 逐字段复现；不同 seed 差异由联合 MCSE 解释；串行/并行一致；中断恢复一致；失败复制计入总分母；边界率不被静默删除；结果与一个理论特例或第二模拟器交叉核对。

模拟报告必须进入 capability evidence summary，但不能替代真实固定数据、失败 case、G5 呈现一致性或任务生命周期。

## 20. 纵向切片的统一 AI-Coding 工作包模板

AI 模型开始任何 TRACK-A～F 工作前必须创建或填写以下记录；无法填写时先补契约，不得直接编码：

```text
工作包 ID：
目标 capability/family：
用户路径：
当前真实状态与机器报告：
权威输入/输出契约：
Estimand 与尺度：
支持范围：
拒绝范围与 reasonCode：
允许修改文件：
明确不修改文件：
跨语言原子变更：
正常/复杂/边界/失败测试：
任务取消/恢复/超时/资源测试：
UI/E2E/a11y：
API/UI/导出/ZIP 一致性：
Golden/独立参考/突变：
性能基线与预算：
迁移和兼容策略：
专项、Quick、Full、Release 命令：
外部阻塞：
完成后状态上限：
```

编码顺序固定为：审计 dirty worktree → 读取上位规范和真实实现 → 写失败测试/契约 → 最小纵向实现 → 专项验证 → Quick → Full → 机器报告/文档。不得在同一补丁中顺便重构无关模块。

## 21. 仓库级最终验收矩阵

### 21.1 功能和契约

- 三轴状态存在于 service、API、OpenAPI、TS 和 UI，过期证据不会升级状态。
- 功效、实验、MI、纵向四个 family 都有无需 JSON 的普通 happy path。
- 所有普通表单只展示与当前数据/设计匹配且 `executionAvailable=true` 的 slice。
- Estimand、编码、缺失、SE/df、分析角色、hash 和限制在运行前可见。

### 21.2 数值和 Golden

- `power.t_test.analytic.v1` 作为首个完整样板达到当前 evaluator RC。
- 其余能力按第 6 节分批达到计划等级；未完成者维持 honest status。
- 独立性、reconciliation、freeze、strict SUT、invariants、mutation、offline 和环境 digest 均有机器证据。
- 复杂模型的参数恢复按全分母、MCSE、失败率和恢复一致性验收。

### 21.3 呈现和生命周期

- API、UI、plot、Markdown、XLSX、ZIP 的字段级一致性门禁通过。
- 所有预设 estimand、警告、诊断和不可估计原因完整传递。
- 任务取消、超时、崩溃、重启恢复、刷新恢复和资源回收通过。
- UI/E2E/a11y 覆盖成功、警告和失败路径。

### 21.4 工程门禁

- Targeted 实际选择非空受影响集合，公共变更正确扩散。
- Quick、Full、Release 从单一注册表生成步骤，无本地/CI 隐式语义漂移。
- 性能基线完整、五次无 flaky、并行/串行等价、资源指标真实记录。
- Release evidence 逐步骤、逐产物、绑定 commit/run/environment；跳项为 incomplete。

### 21.5 最终命令

以下命令中，Targeted 和 AutomatedEvidenceOnly 只有在对应工作包完成后才成为正式入口；在实现前不得把不存在的命令写成已通过证据。

```powershell
& ./scripts/check-architecture.ps1
& ./scripts/generate-contracts.ps1 -Check
& .venv/Scripts/python.exe scripts/check-capability-consistency.py
& .venv/Scripts/python.exe scripts/check-reference-independence.py
& .venv/Scripts/python.exe tools/goldens/verify.py --all --require-sut
& .venv/Scripts/python.exe tools/goldens/invariants.py --all
& .venv/Scripts/python.exe scripts/run-mutation-tests.py --write-reports
& .venv/Scripts/python.exe tools/goldens/evaluate_release.py --all `
  --report output/goldens/release-evaluation-final.json
& ./scripts/harness.ps1 -Mode Targeted -Capability power.t_test.analytic.v1
& ./scripts/harness.ps1 -Mode Quick
& ./scripts/harness.ps1 -Mode Full
& ./scripts/harness.ps1 -Mode Release -AutomatedEvidenceOnly
```

正式发布候选还必须运行未跳项的：

```powershell
& ./scripts/harness.ps1 -Mode Release
```

只有最后一条在干净、受控、依赖与基准条件齐备的环境中全部执行并通过，才可写“应用级 Release Harness passed”。它仍不授予 `supported`。

## 22. 最终禁止性完成声明

以下任何一句在缺少对应证据时都属于错误交付：

- “26/26 发布资格通过”，但只有 SUT 或 strict verify。
- “普通用户可用”，但实验、MI、纵向或功效仍默认编辑 JSON/变量 ID。
- “报告一致”，但只比较页面截图或 Markdown 文本。
- “任务可恢复”，但恢复只来自 localStorage 或没有后端 identity 绑定。
- “性能提升”，但基线运行未完成、机器不同、测试减少或只运行一次。
- “Release passed”，但跳过 audit/benchmark、Golden evaluator 失败或产物缺失。
- “参数恢复通过”，但失败复制从分母删除、无 MCSE、无 checkpoint/resume 等价性。
- “supported”，但只有 AI 生成的自动证据而无项目要求的正式批准。

AI-coding 的正确终态应精确写成：实现了什么、验证了什么、使用哪份机器证据、当前三个状态轴是什么、哪些步骤未运行、哪些外部条件仍阻塞。任何无法由证据支持的更强结论都必须省略。
