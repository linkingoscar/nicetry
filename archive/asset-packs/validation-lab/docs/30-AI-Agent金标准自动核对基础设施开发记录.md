# 30 AI-Agent 金标准自动核对基础设施开发记录

> 文档性质：Golden 基础设施的工程开发、复核与验收记录。
> 适用代码：`tools/goldens/`（`schema.py`, `freeze.py`, `verify.py`, `plan.py`, `acquire.py`, `reconcile.py`, `evaluate_release.py`, `simulation.py`, `invariants.py`, `discover.py`, `build-references.py`, `sut_runner.py`）、`scripts/run-mutation-tests.py`、`scripts/check-reference-independence.py`、`tests/goldens/`。
> 上游依据现已按原文纳入仓库为 `31-AI-Agent无人工介入金标准设立与自动核对规范.md`；仓内文档 28 仍是 `28-代码-业务-文档一致性与仓库收口审计.md`，两者不是同一文件。

本轮开发建立了 12 项 Golden CLI、26 个能力资产包、字段比较器、哈希核验与突变测试基础。2026-07-22 复核先发现并撤销了复制 reference/expected 作为 SUT、把未执行变形测试计为通过等假阳性；随后完成 26 个生产 SUT 适配器、26 个可执行主参考入口、有效统计夹具、动态不变量和突变测试。后续严格按文档 31 复核发现：初始能力均只有一个 Case、一个主参考，Manifest 主要为 `G1/G2 + G7`，尚不满足发布候选要求。**因此原“26 项发布候选”结论已撤销。当前 `power.t_test.analytic.v1` 已补齐四象限、双参考、G3/G6、多源消解和能力级突变，状态为 `autoverified_l3`；其余 25 项为 `autoverified_l1`。所有能力在容器 digest 和离线复现等证据齐备前均不是发布候选。**

---

## 1. 核心架构与工具链建设

### 1.1 数据结构定义与 Schema 规范 (`tools/goldens/schema.py`)

根据规范第 4 节与第 11 节，定义了强类型的 Pydantic 模型（支持 Pydantic v2 `populate_by_name`）：

- `CaseManifest` / `CaseIdentity`：描述单个 Golden Case 的元数据、版本与哈希。
- `ComparisonRule` / `ComparatorKind`：支持 `exact`, `absolute`, `relative`, `absolute_relative`, `set_equivalent`, `sign_indeterminate`, `expected_failure` 等比较类型与指定容差。
- `EvidenceLevel`：定义 G0（自测）、G1（闭式解）、G2（官方包）、G3（第二独立实现）、G7（哈希与 provenance）等证据等级。

### 1.2 因子对齐、符号自动对齐与动态 Metamorphic Invariants 比较引擎 (`tools/goldens/verify.py` & `tools/goldens/invariants.py`)

根据规范第 14.1, 14.2 & 16.5 节：

- 集成了全局最小瓶颈二分分配的因子矩阵自动对齐判定，避免逐列贪心造成局部最优误判；为控制资源预算，当前最多支持 16 个因子列。
- 支持探索性/验证性因子分析（EFA/CFA）载荷矩阵的因子列顺序自动对齐与符号翻转（Sign Flip Alignment）。
- **`invariants.py` 动态 Metamorphic Invariants 变形测试库**：在隔离上下文中真正重新调用计算引擎执行行重排（Row Permutation）数据集重算，验证估算结果的不变性；并提供线性变换响应（`check_linear_transformation_response`）与对比权重正比例缩放（`check_contrast_weight_scaling_invariance`）下的断言。

### 1.3 参考实现独立性静态检查器 (`scripts/check-reference-independence.py`)

根据规范第 5 节，实现了防火墙检查：

- 遍历 `tests/goldens/` 与 `fixtures/` 中的参考 Python/R 脚本，使用 AST 解析禁止任何针对生产代码（`app.api`, `app.services`）的直接 import。
- 校验 CI 与 Pytest 运行逻辑，禁止在普通测试运行期间动态覆盖 `expected.json`。

### 1.4 Golden 自动化工具链 CLI 全家桶 (`tools/goldens/`)

根据规范第 8, 10.1, 22, 24 节：

- **`freeze.py`**：自动计算 Case 输入数据集（CSV/Parquet）、分析 Spec 和 Expected 输出文件的 SHA-256 哈希值，生成 `provenance/hashes.json`。
- **`verify.py`**：校验数据集 SHA-256（G7 证据），解析层级 key 并按字段级 tolerances 对齐比对，支持 `--require-sut` 强校验 SUT 输出。
- **`plan.py`**（规范 9 & 22.1）：自动化 GoldenPlan 生成与校验工具，管理 `golden-plans/<capabilityId>.yaml`。
- **`acquire.py`**（规范 7 & 22.3）：数据集获取、许可校验、防路径穿越校验及多重 SHA-256 哈希计算工具。
- **`reconcile.py`**（规范 12, 13.3 & 22.5）：证据融合器与动态容差推导器，推导 `max(10 * runtimeNoise, 2 * crossEngineDifference, theoreticalFloor)`，生成 consensus `expected.json`。
- **`evaluate_release.py`**（规范 28.1 & 3.1）：证据驱动的分级状态评估器。单参考冻结 Case 最多为 `autoverified_l1`；双独立参考和场景矩阵达到 L2；再具备 G5/G6 达到 L3；只有来源、环境、多源消解、能力级突变、离线复现和基础设施门禁全部通过时才提升至 `autonomously_verified_release_candidate`。
- **`simulation.py`**（规范 16.4 & 24）：蒙特卡洛参数恢复模拟引擎，在预定 $N$ 次复制下评估已收敛估算的 Bias、RMSE、覆盖率 Coverage（要求 $92.5\% \sim 97.5\%$）与收敛失败率；支持 `regression`, `t_test_two_sample`, `lmm_two_level`, `cfa_one_factor` 等多种 DGP。
- **`invariants.py`**（规范 16.5）：变形测试（Metamorphic Testing）动态不变性与响应断言库。
- **`discover.py`**（规范 6 & 22.2）：参考来源检索语法生成与 `sourceTrustScore` 评估器，自动生成/更新 `data/source.json`。
- **`build-references.py`**：容器化隔离参考运行器，无 Docker 环境时降级为 Subprocess 进程隔离；缺少 `primaryReference.command` 时明确失败，不再把 preserved asset 记为“已执行”。
- **`sut_runner.py`**：只执行 case 内显式的 `sut/run.py` 生产适配器，并为输出写入绑定 runner、manifest 与 output SHA-256 的 `sut/provenance.json`。缺少适配器时明确失败，禁止从 reference/expected 复制生成 SUT。

### 1.5 突变测试门禁 Mutation Testing Gate (`scripts/run-mutation-tests.py`)

根据规范第 27 节：

- 自动向分析结果关键字段注入统计与数据突变。
- 验证比较引擎对目标字段突变体的杀灭能力，确保 Mutation Score $\ge 85\%$。复核后突变在隔离副本中执行，不再覆盖或删除已存在的 SUT 产物；当前专项运行杀灭率为 $100.0\%$（95/95）。生产执行是否成立另由 `sut_runner.py` 的来源证明和 `verify.py --require-sut` 独立约束。

---

## 2. 全量 26 个能力金标准资产包列表 (Tier-1 ~ Tier-5)

已完成 `tests/goldens/<capabilityId>/cases/<caseId>/` 下 26 个能力包的单场景构建、真实执行与锁定。下表最后一列保留 2026-07-22 旧评估结果作为审计记录，该结果已撤销；当前统一状态为 `autoverified_l1`，且不替代应用级 Release Harness：

| Capability ID | Case ID | 证据等级 | 主要参考引擎 / 公式 | 核对字段 | 旧评估结果（已撤销） |
| --- | --- | --- | --- | --- | --- |
| `imputation.pooling.linear.rubin.v1` | `rubin_standard` | G1 + G7 | Python 纯数学 Rubin Pooling 公式 | `pooled_estimate`, `between_variance`, `se`, `df` | `autonomously_verified_release_candidate` |
| `power.t_test.analytic.v1` | `t_test_two_sample` | G1 + G7 | SciPy 非中心 t 分布公式 | `power`, `df`, `ncp` | `autonomously_verified_release_candidate` |
| `power.regression.f2.analytic.v1` | `regression_f2_standard` | G1 + G7 | SciPy 非中心 F 分布公式 | `power`, `u`, `v`, `ncp` | `autonomously_verified_release_candidate` |
| `experiment.between.factorial.gaussian.v1` | `toothgrowth_factorial` | G2 + G7 | R `afex` + `emmeans` | Omnibus $F$ 统计量、自由度、`emmean` | `autonomously_verified_release_candidate` |
| `experiment.emmeans.planned_contrast.v1` | `moore_ancova_contrasts` | G2 + G7 | R `afex` + `emmeans` | ANCOVA $F$ 统计量、边际均值 `emmean` | `autonomously_verified_release_candidate` |
| `multilevel.lmm.two_level.gaussian.random_slope.v1` | `sleepstudy_random_slope` | G2 + G7 | R `lmerTest` REML 拟合 | 固定效应 Estimate、Satterthwaite $df$ | `autonomously_verified_release_candidate` |
| `multilevel.icc.two_level.v1` | `icc_two_level_balanced` | G1 + G7 | Python 方差成分 ANOVA 分解 | `icc1`, `icc2`, `ms_between`, `var_between` | `autonomously_verified_release_candidate` |
| `measurement.efa.continuous.minres.v1` | `efa_minres_harman` | G2 + G7 | R `psych::fa` MINRES（全局因子对齐） | 旋转载荷矩阵 `loadings` (set_equivalent)、`communalities` | `autonomously_verified_release_candidate` |
| `measurement.cfa.continuous.mlr.v1` | `cfa_hs1939_mlr` | G2 + G7 | R `lavaan` MLR | Robust 拟合指数 (`cfi_robust`, `rmsea_robust`)`loadings` | `autonomously_verified_release_candidate` |
| `experiment.repeated.one_within.v1` | `obrien_kaiser_repeated` | G2 + G7 | R `afex` + `car` | Omnibus $F$ 统计量、Mauchly 球形检验、$GG \epsilon$ | `autonomously_verified_release_candidate` |
| `experiment.posthoc.games_howell.v1` | `games_howell_unequal_var` | G1 + G7 | Games–Howell 异方差公式 | `estimate`, `se`, `df`, `statistic`, `p_value` | `autonomously_verified_release_candidate` |
| `multilevel.se.cluster_robust.v1` | `cluster_robust_cr2` | G2 + G7 | clubSandwich CR2 | `estimate`, `se_cr2`, `df_satt`, `num_clusters` | `autonomously_verified_release_candidate` |
| `multilevel.lmm.within_between.v1` | `lmm_group_mean_centering` | G1 + G7 | LMM Group Mean Centering 公式 | `x_within`, `x_between` | `autonomously_verified_release_candidate` |
| `equivalence.tost.two_sample.v1` | `tost_two_sample_equivalence` | G1 + G7 | TOSTER 双单侧检验 | `mean_diff`, `p_lower`, `p_upper`, `equivalent` | `autonomously_verified_release_candidate` |
| `measurement.cfa.ordinal.wlsmv.v1` | `cfa_ordinal_wlsmv` | G2 + G7 | R `lavaan` WLSMV Delta 参数化 | Robust CFI/RMSEA 拟合、Thresholds、Loadings | `autonomously_verified_release_candidate` |
| `measurement.invariance.multi_group.v1` | `invariance_configural_metric` | G2 + G7 | R `lavaan` 多组等值性比较 | Configural CFI、Metric CFI、Chisq Difference Test | `autonomously_verified_release_candidate` |
| `measurement.bifactor.continuous.v1` | `bifactor_continuous_standard` | G2 + G7 | R `lavaan` 正交 Bifactor | 一般因子/特殊因子载荷、$\omega_h$, ECV, PUC | `autonomously_verified_release_candidate` |
| `longitudinal.ri_clpm.four_wave.v1` | `ri_clpm_four_wave_standard` | G2 + G7 | R `lavaan` RI-CLPM | Trait 随机截距方差、Autoregressive/Cross-lagged 路径 | `autonomously_verified_release_candidate` |
| `measurement.irt.dif.v1` | `irt_2pl_dif` | G2 + G7 | R `mirt` 2PL | 难度 $b$、区分度 $a$、DIF 均一卡方及 p 值 | `autonomously_verified_release_candidate` |
| `measurement.esem.target_rotation.v1` | `esem_target_rotation` | G2 + G7 | R `psych` ESEM Target Rotation | 旋转载荷矩阵、交叉载荷、因子相关 $\mathbf{\Phi}$ | `autonomously_verified_release_candidate` |
| `measurement.cmb.ulmc.v1` | `cmb_ulmc_marker` | G2 + G7 | R `lavaan` ULMC 未测量方法因子 | Baseline 与 ULMC 模型拟合差 $\Delta\chi^2, \Delta CFI$ | `autonomously_verified_release_candidate` |
| `experiment.randomization.inference.v1` | `randomization_inference_exact` | G1 + G7 | 精确随机化推断 / 置换检验 | 观察统计量、全置换数、精确双侧 p 值 | `autonomously_verified_release_candidate` |
| `imputation.mice.chain_diagnostics.v1` | `mice_chain_diagnostics` | G2 + G7 | R `mice` 链诊断 | 插补数据集个数、链收敛状态、被动变量保持 | `autonomously_verified_release_candidate` |
| `robustness.specification_curve.matrix.v1` | `specification_curve_multiverse` | G1 + G7 | R OLS / `MASS::rlm` 规格宇宙 | 规格总数、中位数效应、显著比例 | `autonomously_verified_release_candidate` |
| `longitudinal.esm.diary_ar1.v1` | `esm_diary_ar1` | G2 + G7 | R `nlme` 日记法 AR(1) | Prompt 自相关系数 $\phi$、组内/组间方差 | `autonomously_verified_release_candidate` |
| `multilevel.mediation.two_level.v1` | `two_level_mediation` | G1 + G7 | 两层多层中介效应分解 | 组间中介效应 $a_Bb_B$、组内中介效应 $a_Wb_W$ | `autonomously_verified_release_candidate` |

---

## 3. 架构控制与 CI/CD 接入

### 3.1 `project.manifest.json` 命令注册

在 `commands` 配置中显式注册新命令：

- `"goldenSut": "tools/goldens/sut_runner.py --all"`
- `"goldenVerify": "tools/goldens/verify.py --all"`
- `"goldenFreeze": "tools/goldens/freeze.py"`
- `"goldenPlan": "tools/goldens/plan.py"`
- `"goldenAcquire": "tools/goldens/acquire.py"`
- `"goldenReconcile": "tools/goldens/reconcile.py"`
- `"goldenEvaluate": "tools/goldens/evaluate_release.py"`
- `"goldenSimulation": "tools/goldens/simulation.py"`
- `"goldenInvariants": "tools/goldens/invariants.py"`
- `"goldenDiscover": "tools/goldens/discover.py"`
- `"goldenBuildReferences": "tools/goldens/build-references.py"`
- `"mutationTest": "scripts/run-mutation-tests.py"`
- `"checkReferenceIndependence": "scripts/check-reference-independence.py"`

### 3.2 关卡测试集成

- 在 `scripts/check-architecture.ps1` 校验逻辑中显式增加 `-Encoding UTF8`，确保在 Windows PowerShell 5.1 与 PowerShell 7 (`pwsh`) 环境下均能正确解析包含中文的声明路径并校验命令路径。
- 在 `apps/api/tests/test_advanced_gold_standards.py` 中把 26 个冻结 case 参数化为独立 pytest 项，Full 时由 xdist 平衡调度静态 manifest 核验和动态 Metamorphic 重算。SUT 生成、`--require-sut` 强核对、突变和综合资格评估仍由各自专项命令执行，避免在 API 层重复启动同一跨软件验证，同时不减少任何 Golden case。

---

## 4. 验证与验收结论

原记录曾列出 14 项全绿结果，其中第 4、5、10、12、13 项的语义被实现中的回退/跳过逻辑夸大：复制 reference 不是运行 SUT；缺少 runner 不是动态变形通过；`build-references.py` 的 preserved-asset fallback 不是 26 个参考引擎均已执行；旧 `evaluate_release.py` 也没有强制 SUT、变形和突变条件，且即使不合格仍返回 0。

2026-07-22 修复并完成真实实现后的可复跑结论：

1. `python tools/goldens/sut_runner.py --all`：PASS（26/26）；所有 case 均调用生产 R 引擎或生产统计能力引擎并生成来源证明，禁止 reference/expected 回退。
2. `python tools/goldens/verify.py --all --require-sut`：PASS（26/26）；数据、规格、Expected、SUT 输出及 provenance 哈希绑定有效。
3. `python tools/goldens/invariants.py --all`：PASS（26/26）；隔离目录中重新执行参考引擎，行顺序置换不影响核对结论。
4. `python scripts/run-mutation-tests.py`：PASS（95/95，100%）；全部目标突变被比较规则杀死。
5. 旧版 `python tools/goldens/evaluate_release.py --all` 曾 PASS（26/26），但门禁未强制第二独立参考、四类场景、G3、能力级突变、来源/环境和离线证据，因此该结果已撤销。严格评估器当前将 t-test power 判为 `autoverified_l3`、其余 25 项判为 `autoverified_l1`，并保持非零退出，直到全部发布条件具备。

6. 有效夹具替代了原 4–12 行的不可估计占位数据；CFA/不变性/双因子/IRT、RI-CLPM、MICE、ESM、CR2、两层中介和规格曲线均使用可复现的固定种子数据。
7. 新增并锁定 `mirt` 与 `clubSandwich` 依赖；IRT 使用 MML 2PL 参数估计与 logistic-LRT uniform DIF，CR2 使用 Satterthwaite 小样本自由度。

### 4.1 首个 L3 能力切片：双侧两独立样本 t 检验功效

`power.t_test.analytic.v1` 已从单一正常 Case 扩为 `normal_typical`、`legal_complex`、`degenerate_boundary`、`expected_failure` 四类场景。主参考使用 SciPy 非中心 t 分布，第二参考使用 mpmath 任意精度中心 t 分位数和卡方混合积分，不读取主参考输出；生产 R 引擎新增 one-sided、非法 alpha、非法样本量和非有限效应量的稳定拒绝。四个 Case 的 SUT、双参考 reconciliation、动态行置换均通过，能力级突变为 23/23。由于尚无按 digest 固定的参考容器和受控离线复现报告，该能力停在 `autoverified_l3`。

本轮还修复了双因子正交约束循环把最后一个特异因子方差错误固定为 0、数值 cluster ID 在聚合 ANOVA 中未因子化、隔离参考启动器依赖目录层级猜 capability 等生产/验证缺陷。当前基础设施质量评级为“26 项真实执行闭环”；应用级发布状态仍以文档 24 的 Full/Release Harness 当轮结果为准。

应用级历史证据：2026-07-22 的 Full Harness 在 4 个隔离 worker 下通过，API/R/Golden 为 306 passed、1 skipped，分支覆盖率 80.4810%，完整 Full 墙钟 310.12 秒。该次未执行完整 Release Harness。严格 Golden 资格评估现已成为 Release Harness 必需步骤；在第二参考、场景矩阵和完整治理证据补齐前，Release 应被门禁阻止。
