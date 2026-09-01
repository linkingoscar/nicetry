# AI-Agent 无人工介入金标准设立与自动核对规范

> 文档版本：1.0.0
> 编制日期：2026-07-20
> 适用项目：ResearchPath / OB–CB 实验、问卷、缺失数据、多层与纵向统计能力
> 适用对象：Codex、自动化编码代理、验证代理、CI/CD 维护代理
> 文档属性：规范性开发与验收文件
> 上游依据：`27-OB-CB实验与问卷实证研究全流程能力审计及开发蓝图.md` 第 18、20、21、22 节
> 目标：在**没有人工参与金标准生成和逐项核对**的条件下，由 AI-agent 通过公式、独立代码、权威软件包、公开可复现资料、模拟真值和性质测试，自动建立、冻结、核验和维护统计金标准资产。

---

## 0. 一页执行摘要

AI-agent 接到任一统计能力开发任务后，必须执行以下闭环：

```text
解析 capability slice
→ 冻结 estimand 与支持边界
→ 建立 GoldenPlan
→ 自动检索至少两类独立证据
→ 获取并校验公开数据/代码/输出
→ 在隔离环境运行参考实现
→ 规范化不同软件结果
→ 建立字段级期望值与容差
→ 运行生产实现
→ 多源比对 + 性质测试 + 模拟恢复
→ 冲突归因或隔离
→ 冻结 golden bundle
→ 接入 Quick / Full / Release CI
→ 更新 capability 状态和证据索引
```

无人工介入模式下，AI-agent **不得把自己完成的验证直接等同于最终 `supported`**。本规范允许达到的最高自动状态为：

```text
autonomously_verified_release_candidate
```

它表示：

- 主体统计实现已存在且正常入口可达；
- 至少三类自动化证据已通过；
- 至少两个计算上独立的参考路径一致；
- 边界、失败、性质和模拟恢复通过；
- 所有资产可离线重跑、可审计、可冻结；
- 未发现需要人工裁决的未消解冲突。

它**不替代**原蓝图要求的独立方法专家复核、真实 OB/CB 研究试用和商业/第二软件正式签字。因此：

```text
autonomously_verified_release_candidate ≠ supported
```

若产品决定采用“纯自动化发布制度”，必须在产品文档中单独声明其证据边界，不得沿用原蓝图中含人工门禁的 `supported` 定义。

---

## 1. 目的与适用范围

### 1.1 目的

本规范解决以下问题：

1. AI-agent 应如何自主判断某个统计方法需要什么金标准。
2. 如何通过网络搜索找到可用于验证的数据、代码、示例输出和官方定义。
3. 如何防止“同一段代码生成 expected，再测试同一段代码”的伪验证。
4. 如何冻结软件版本、数据哈希、命令、环境和容差。
5. 不同软件结果不一致时，如何自动定位定义差异。
6. 无法获得商业软件时，如何用独立公式、第二语言实现、模拟真值和性质测试构成足够强的证据。
7. R2–R5 每类方法应采用哪些参考路径、测试数据和比较字段。
8. 如何让金标准资产进入 CI，并在依赖升级后安全更新。

### 1.2 适用范围

本规范覆盖：

- R2：信度、EFA、CFA、WLSMV、测量等值性、ESEM、bifactor、IRT/DIF、CMB；
- R3：ANOVA、ANCOVA、重复测量、混合设计、EMM、计划对比、Games–Howell、聚类稳健、多重性、TOST；
- R4：MICE、多重插补合并、解析功效、Monte Carlo 功效、稳健性规格宇宙；
- R5：ICC/rwg、Gaussian LMM、随机斜率、within–between、增长模型、CLPM、RI-CLPM、latent growth、ESM；
- 支撑层：数据获取、版本冻结、容器、哈希、CI、变更审计和供应链安全。

### 1.3 不适用范围

本规范不允许 AI-agent：

- 用网络文章的结论代替可执行参考结果；
- 用论文表格中被四舍五入的数值作为唯一精确金标准；
- 未核对模型定义便比较不同软件的“同名指标”；
- 把同一生产函数包装一次后称为“独立实现”；
- 因测试失败而扩大容差、删除失败样本或替换参考来源；
- 从不明来源下载并执行任意脚本；
- 自动接受需要理论判断的题项删除、partial invariance 参数释放或模型修正；
- 在无法消解冲突时选择“多数值”并强制通过。

---

## 2. 规范性术语

本文使用以下强制词：

- **必须（MUST）**：违反即不得通过自动验证。
- **不得（MUST NOT）**：明确禁止。
- **应（SHOULD）**：除非记录充分理由，否则必须遵循。
- **可以（MAY）**：可选实现。
- **金标准场景（Golden Case）**：一个冻结的数据、规格、参考环境和期望结果组合。
- **金标准包（Golden Bundle）**：一个 capability 下全部场景、参考脚本、环境和证据的集合。
- **参考实现（Reference Implementation）**：不依赖生产统计核心、用于产生比较结果的独立计算路径。
- **生产实现（System Under Test, SUT）**：ResearchPath 正式 runner。
- **独立来源**：在代码、依赖、作者实现、语言或计算路径中至少有一项实质独立。
- **规范化（Canonicalization）**：把不同软件的命名、顺序、编码和尺度映射到统一语义。
- **证据隔离（Quarantine）**：因冲突、来源不可信或定义不明而禁止升级状态。
- **冻结（Freeze）**：资产、哈希、版本和结果进入只读基线，普通 CI 不得覆盖。
- **变形测试（Metamorphic Test）**：通过数据或参数变换后结果应满足的数学关系验证实现。
- **参数恢复（Parameter Recovery）**：从已知生成参数的模拟数据中检验估计偏差、覆盖率和失败率。

---

## 3. 自动验证状态模型

### 3.1 推荐状态

```text
planned
implemented
wired
autoverified_l1
autoverified_l2
autoverified_l3
autonomously_verified_release_candidate
supported
```

定义如下：

| 状态 | 自动化要求 |
| --- | --- |
| `planned` | 只有规格或路线图，不可执行 |
| `implemented` | 存在生产代码，但未证明正常入口可达 |
| `wired` | API/runner 可达，结果契约可解析 |
| `autoverified_l1` | 至少一个权威参考或闭式解正常场景通过 |
| `autoverified_l2` | 至少两个独立计算路径通过，含边界与失败测试 |
| `autoverified_l3` | 多源一致、性质测试、参数恢复或统计覆盖率通过 |
| `autonomously_verified_release_candidate` | 全部自动门禁通过、资产冻结、CI 离线可重跑、无未解冲突 |
| `supported` | 还需满足原蓝图规定的人工方法复核、真实研究试用等门禁 |

### 3.2 自动证据等级

每个 Golden Case 必须标注证据等级：

| 等级 | 名称 | 说明 |
| --- | --- | --- |
| G0 | 仅生产自测 | 不构成金标准 |
| G1 | 闭式解/手工可解 | 公式与生产实现分离 |
| G2 | 权威开源参考 | 官方包、官方示例或维护者发布实现 |
| G3 | 第二独立实现 | 不同包、不同语言或不同算法 |
| G4 | 冻结外部输出 | Mplus、Stata、SPSS、SAS 等公开或可合法获得输出 |
| G5 | 模拟真值 | 参数恢复、覆盖率、I 类错误、功效和失败率 |
| G6 | 性质/变形证据 | 排序、缩放、重编码、标签置换等数学性质 |
| G7 | 供应链与复现证据 | 哈希、锁文件、容器 digest、签名或 attestation |

单个 capability 达到自动发布候选时，至少满足：

```text
(G1 或 G2) + G3 + (G5 或 G6) + G7
```

对于复杂潜变量、混合模型或 Monte Carlo 方法，建议满足：

```text
G2 + G3 + G5 + G6 + G7
```

---

## 4. 金标准的构成

一个合格 Golden Case 不是单独的 `expected.json`，而是以下不可分割的整体：

```text
数据资产
+ 数据许可与来源
+ 数据 SHA-256
+ 精确 capabilityId
+ 完整 AnalysisSpec
+ estimand 定义
+ 参考实现代码
+ 参考软件及包版本
+ 容器或运行环境
+ 随机种子与 RNG 类型
+ 原始参考输出
+ 规范化输出
+ 字段级比较规则
+ 边界/失败预期
+ 生成日志
+ 供应链 provenance
```

### 4.1 强制目录结构

```text
tests/
  goldens/
    <capabilityId>/
      bundle.yaml
      README.md
      cases/
        <caseId>/
          manifest.yaml
          data/
            input.csv
            input.parquet
            source.json
            LICENSE.txt
          spec/
            analysis-spec.json
            estimand.json
          reference/
            primary/
              run.R
              raw-output.json
              normalized-output.json
              session-info.txt
              stdout.log
              stderr.log
            secondary/
              run.py
              raw-output.json
              normalized-output.json
              environment.txt
              stdout.log
              stderr.log
          expected/
            expected.json
            diagnostics.json
            invariants.json
          sut/
            normalized-output.json
          comparison/
            report.json
            report.md
          provenance/
            hashes.json
            source-discovery.json
            container.json
            attestation.json
```

### 4.2 Bundle 与 Case

- `bundle.yaml` 描述整个 capability 的支持范围和场景矩阵。
- `manifest.yaml` 描述单个场景。
- 一个 capability 至少三个场景，但复杂方法通常需要 6–15 个。
- 普通 CI 只读取冻结资产，不联网重新生成。
- 网络检索和 Golden 更新只能在独立的 `golden-refresh` 工作流执行。

---

## 5. 独立性防火墙

### 5.1 禁止的伪独立

以下均不构成独立参考：

- 生产函数 `fit_model()` 与测试中再次调用 `fit_model()`；
- 生产函数复制到另一个文件但逻辑完全相同；
- 生产 runner 与参考 runner 调用同一个内部工具函数；
- 两个脚本都调用同一个底层包并使用同一提取器；
- 用生产 JSON 重新排序后作为 expected；
- AI-agent 先观察 SUT 输出，再反向填写 expected；
- 参考实现 import 生产项目包；
- 参考实现读取生产实现生成的中间设计矩阵或协方差矩阵，而没有独立核对。

### 5.2 独立参考的最低条件

参考路径应至少满足以下两项：

- 不同语言：例如生产 R，参考 Python；
- 不同统计包：例如生产 `lavaan`，参考 `semopy`、Mplus 冻结输出或独立矩阵公式；
- 不同算法：例如生产 QR，参考正规方程/SVD；
- 不同作者团队维护的软件；
- 独立设计矩阵和对比矩阵构造；
- 独立数据预处理与缺失处理实现；
- 独立结果提取器。

### 5.3 自动静态检查

AI-agent 必须实现 `check-reference-independence`，至少检查：

```text
reference/ 是否 import apps.api、engine.R 或生产包
参考脚本是否包含生产函数名
参考脚本与生产文件的 token/AST 相似度
依赖图是否完全重合
expected 是否在测试运行中被覆盖
参考输出时间是否晚于 SUT 输出且由同一命令生成
```

建议阈值：

```yaml
maxTokenSimilarity: 0.55
maxAstSimilarity: 0.65
allowSharedDependencies:
  - base R
  - numpy
  - scipy
denyProductionImports: true
denyExpectedOverwriteInCi: true
```

相似度超阈值时，Case 自动进入 `REFERENCE_NOT_INDEPENDENT`。

---

## 6. 网络检索与来源治理

## 6.1 来源优先级

AI-agent 必须按以下顺序检索：

### Tier A：官方定义与官方实现

- R 官方与 CRAN 正式包页面、参考手册、vignette；
- 包维护者官方站点；
- lavaan 官方教程；
- Mplus 官方 User’s Guide examples、Web Notes 和示例输入输出；
- Stata、SAS、IBM SPSS 官方算法或命令文档；
- Python 官方包文档；
- GitHub 官方 release、tag、commit、artifact attestation；
- 期刊作者官方补充材料；
- OSF registration；
- Zenodo DOI record。

### Tier B：公开可执行研究材料

- OSF 项目与注册；
- Zenodo 数据集、软件和附件；
- Dataverse；
- 期刊官方 supplementary files；
- 作者仓库中与论文版本对应的 tag/release；
- 软件包内置 dataset 和官方 example。

### Tier C：同行评议方法论文

仅用于确认定义、公式和算法，不应作为唯一数值金标准。必须优先寻找其代码、数据或补充材料。

### Tier D：二级教程

只能帮助发现关键词或来源，不得直接作为 expected 的权威依据。

### 禁用来源

下列来源不得作为正式金标准：

- 搜索引擎摘要；
- 未注明软件版本的博客输出；
- 问答论坛；
- 无数据、无代码、无完整输出的截图；
- 无法确认作者或出处的网盘；
- 聚合转载；
- AI 生成文章；
- 已被撤回或明确存在错误的材料；
- 许可不明且无法合法保存的私有数据。

## 6.2 搜索查询模板

Agent 必须针对 capability 自动生成查询，而不是只搜索方法名称。

示例：

```text
"<method>" official example dataset output
"<package>" "<function>" reference manual
site:lavaan.ugent.be "<estimator>" "<model>"
site:statmodel.com usersguide "<model>"
site:cran.r-project.org "<package>" PDF
site:amices.org/mice "<pooling method>"
site:osf.io "<method>" data code
site:zenodo.org "<method>" dataset software
site:github.com "<package>" release tag
"<dataset name>" license
"<method>" parameter recovery simulation code
```

测量方法示例：

```text
lavaan WLSMV categorical official tutorial
psych polychoric fa official documentation
measurement invariance official example output
Mplus bifactor example input output
mirt DIF official example
```

实验方法示例：

```text
afex repeated measures official example
emmeans custom contrasts official vignette
Games Howell independent formula reference
OBrienKaiser afex example
```

多层与纵向示例：

```text
lmerTest Satterthwaite official documentation
lme4 sleepstudy example
Mplus growth model example input output
lavaan growth Demo.growth
RI-CLPM official code data supplementary
```

## 6.3 自动来源评分

每个候选来源计算 `sourceTrustScore`：

```text
score =
  0.25 × authority
+ 0.20 × executability
+ 0.15 × versionSpecificity
+ 0.15 × independence
+ 0.10 × artifactCompleteness
+ 0.10 × persistence
+ 0.05 × licenseClarity
```

各项取值 `[0,1]`。

推荐规则：

```yaml
acceptAsPrimary: score >= 0.85
acceptAsSecondary: score >= 0.75
discoveryOnly: 0.50 <= score < 0.75
reject: score < 0.50
```

任何来源只要存在下列情况，直接拒绝：

```text
无法确定数据许可
下载内容哈希变化但版本号未变化
代码引用远程未固定分支
输出与代码版本不匹配
缺少模型规格
需要执行不可信二进制
```

## 6.4 来源记录

`source.json` 至少包含：

```json
{
  "sourceId": "src_lavaan_hs1939_001",
  "sourceType": "official_package_dataset",
  "title": "Holzinger and Swineford 1939",
  "publisher": "lavaan",
  "canonicalUrl": "https://...",
  "retrievedAt": "2026-07-20T12:00:00Z",
  "version": "package-version-or-record-version",
  "commitSha": null,
  "doi": null,
  "license": "package-license-or-dataset-license",
  "sha256": "...",
  "authorityScore": 1.0,
  "executabilityScore": 1.0,
  "sourceTrustScore": 0.94,
  "allowedUse": [
    "testing",
    "redistribution"
  ],
  "notes": []
}
```

---

## 7. 数据资产获取规则

### 7.1 优先使用的数据

1. 官方包内置数据；
2. 官方方法教程数据；
3. OSF/Zenodo/Dataverse 中带版本和许可的数据；
4. 公开论文补充材料；
5. AI-agent 按冻结 DGP 生成的合成数据；
6. 极小的人工可解确定性 fixture。

### 7.2 数据许可

Agent 必须自动确认：

- 是否允许下载；
- 是否允许测试使用；
- 是否允许把数据提交到仓库；
- 是否需要仅保存下载脚本和哈希；
- 是否含个人信息或敏感字段；
- 是否需要去标识；
- 是否有引文要求。

若许可允许使用但不允许再分发：

```text
不得提交原数据
只提交 downloader、来源元数据、预期 SHA 和最小派生统计
CI 中按许可和凭据策略决定是否下载
常规离线 CI 不依赖受限数据
```

### 7.3 数据最小化

用于数值验证的 fixture 应尽量：

- 去除无关列；
- 使用公开或合成数据；
- 保留触发方法特征所需的最小结构；
- 不保存 IP、设备、文本等无关敏感数据；
- 对公开大数据生成可重建的最小子集，并记录抽样 seed 和规则。

### 7.4 数据哈希

至少生成：

```text
原始下载文件 SHA-256
解压文件 SHA-256
规范化 CSV/Parquet SHA-256
列 schema hash
行顺序 hash
```

不得只对文件名或下载 URL 建立身份。

---

## 8. 环境冻结与供应链安全

### 8.1 R 环境

每个参考 R 环境必须记录：

```text
R 完整版本
平台与架构
BLAS/LAPACK
locale
timezone
RNGkind
包版本
包来源
renv.lock
sessionInfo() 或 sessioninfo::session_info()
```

`renv.lock` 用于记录直接和传递依赖。参考环境不得依赖未固定的 GitHub `main` 分支。

### 8.2 Python 环境

必须：

```text
固定 Python major.minor.patch
固定所有依赖版本
requirements 文件包含哈希
使用 pip --require-hashes 或等价机制
记录 NumPy/SciPy/BLAS 信息
```

### 8.3 容器

容器必须按 digest 固定，而不是仅使用 tag：

```text
image: repository/name@sha256:<digest>
```

记录：

```text
base image digest
Dockerfile hash
构建 commit
构建时间
OS 包清单
R/Python lockfile hash
```

### 8.4 构建 provenance

若使用 GitHub Actions，应为 Golden Bundle 生成 artifact attestation，并在消费时验证签名、时间戳和构建身份。

### 8.5 不可信代码隔离

网络获得的脚本必须：

- 先静态扫描；
- 禁止网络写操作；
- 禁止读取宿主秘密；
- 禁止访问项目外目录；
- 在无特权容器运行；
- 设置 CPU、内存、文件数、进程数和时间限制；
- 只读挂载数据；
- 输出到临时目录；
- 执行完成后销毁容器。

---

## 9. GoldenPlan：开发前的强制计划

每个 capability 开发前必须生成：

```text
golden-plans/<capabilityId>.yaml
```

示例：

```yaml
schemaVersion: 1
capabilityId: multilevel.lmm.two_level.gaussian.v1
methodFamily: multilevel
estimand:
  unit: participant
  scale: identity
  targets:
    - fixed_effect
    - variance_component
    - intraclass_correlation
support:
  outcomes:
    - continuous
  levels: 2
  randomEffects:
    - intercept
    - slope
  dfMethods:
    - satterthwaite
    - kenward_roger
reject:
  - binary_outcome
  - three_level
  - crossed_random_effects
evidencePlan:
  primary:
    type: official_open_source
    tool: lmerTest
  secondary:
    type: independent_language
    tool: statsmodels
  additional:
    - parameter_recovery
    - metamorphic
    - frozen_public_dataset
cases:
  - lmm_sleepstudy_standard
  - lmm_unbalanced_clusters
  - lmm_group_mean_centering
  - lmm_singular_random_slope
  - lmm_nonidentifiable
requiredFields:
  - fixedEffects
  - standardErrors
  - degreesOfFreedom
  - confidenceIntervals
  - varianceComponents
  - icc
  - logLikelihood
tolerancePolicy: iterative_mixed_model_v1
```

若以下任一项为空，Agent 必须停止统计开发：

- estimand；
- 支持范围；
- 拒绝范围；
- 主参考；
- 独立参考；
- 必测字段；
- 容差策略；
- 正常、边界和失败场景。

---

## 10. Reference Runner 设计

### 10.1 进程隔离

生产与参考必须在不同进程运行：

```text
SUT container
Primary reference container
Secondary reference container
Comparator container
```

不得在同一 R session 中同时加载生产项目和参考包。

### 10.2 输入统一

所有 runner 只读取：

```text
data file
analysis-spec.json
estimand.json
seed
```

参考 runner 不读取 SUT 输出。

### 10.3 输出两层结构

每个参考 runner 输出：

1. `raw-output.json`：保留软件原始字段；
2. `normalized-output.json`：映射到 ResearchPath 统一语义。

原始输出不得被覆盖；规范化器可升级，但必须版本化。

### 10.4 规范化器

规范化必须处理：

- 参数命名；
- 因子/条件水平顺序；
- treatment、sum、Helmert、custom contrast；
- 截距含义；
- 标准化解类型；
- 行列顺序；
- 方差与标准差；
- logit 与概率尺度；
- SE、df、z/t；
- robust/scaled test statistic；
- 置信区间方法；
- 缺失处理；
- 样本 N、cluster N、wave N；
- 不可估计值和失败码。

---

## 11. Manifest 规范

单个 `manifest.yaml` 推荐结构：

```yaml
schemaVersion: 1

identity:
  goldenCaseId: cfa_ordinal_hs1939_wlsmv
  capabilityId: measurement.cfa.ordinal.wlsmv.v1
  caseVersion: 1.0.0
  status: frozen

dataset:
  files:
    - path: data/input.csv
      sha256: "..."
  sourceRecord: data/source.json
  rowCount: 301
  columnCount: 12
  rowOrderSemantics: fixed
  licenseVerified: true

spec:
  analysisSpec: spec/analysis-spec.json
  estimandSpec: spec/estimand.json
  specSha256: "..."
  requiredExplicitDefaults:
    estimator: WLSMV
    parameterization: delta
    missing: pairwise
    orderedIndicators:
      - x1
      - x2

randomness:
  stochastic: false
  seed: null
  rngKind: null

primaryReference:
  engine: lavaan
  version: "<pinned>"
  containerDigest: "sha256:..."
  command: "Rscript reference/primary/run.R"
  normalizedOutput: reference/primary/normalized-output.json

secondaryReference:
  engine: "<independent implementation>"
  version: "<pinned>"
  containerDigest: "sha256:..."
  command: "python reference/secondary/run.py"
  normalizedOutput: reference/secondary/normalized-output.json

comparison:
  canonicalizerVersion: 1
  fields:
    - path: estimates[*].estimate
      comparator: absolute_relative
      absTolerance: 0.00001
      relTolerance: 0.0001
    - path: fit.cfi
      comparator: absolute
      absTolerance: 0.0001
    - path: diagnostics.converged
      comparator: exact

evidence:
  levels:
    - G2
    - G3
    - G6
    - G7
  sourceTrustMinimum: 0.85
  unresolvedConflicts: []

freeze:
  generatedAt: "2026-07-20T00:00:00Z"
  generatorCommit: "<sha>"
  bundleSha256: "..."
  expectedUpdateAllowedOnlyBy: golden-refresh
```

---

## 12. Expected 结果规范

### 12.1 Expected 不是单来源抄写

`expected.json` 应由证据融合器生成：

```text
primary normalized output
+ secondary normalized output
+ 解析公式或模拟真值
+ 规范化规则
→ consensus expected
```

### 12.2 字段分类

每个字段必须标注：

```yaml
fieldType:
  - exact
  - deterministic_numeric
  - iterative_numeric
  - set_equivalent
  - order_invariant
  - sign_indeterminate
  - stochastic_summary
  - diagnostic_code
  - expected_failure
```

示例：

- `N`、模型 df、条件数目：`exact`
- OLS 系数：`deterministic_numeric`
- CFA 载荷：`iterative_numeric`
- 因子顺序：`set_equivalent`
- 特征向量/因子方向：`sign_indeterminate`
- Monte Carlo power：`stochastic_summary`
- 空 cell：`expected_failure`

### 12.3 禁止只比较 p 值

至少优先比较：

- 原始估计；
- SE；
- df；
- test statistic；
- CI；
- variance/covariance；
- 样本流；
- 收敛与边界；
- 参考尺度；
- 原始与校正 p 值。

p 值仅用于辅助发现差异，不应成为唯一门禁。

---

## 13. 容差体系

### 13.1 通用规则

比较器使用：

```text
|actual - expected| <= absTol + relTol × |expected|
```

但不得对所有字段使用同一容差。

### 13.2 容差等级

| 类型 | 推荐起点 |
| --- | --- |
| 整数、布尔、枚举、错误码 | exact |
| 闭式解与确定性矩阵 | `abs=1e-8`，必要时 `rel=1e-8` |
| OLS/相关/简单效应量 | `1e-7`–`1e-6` |
| EMM/contrast | `1e-6`–`1e-5` |
| 迭代 ML/REML | `1e-5`–`1e-4` |
| WLSMV/robust/scaled fit | 按具体定义，常为 `1e-4`–`1e-3` |
| 方差接近边界 | 绝对容差 + 边界状态共同判断 |
| Bootstrap quantile | 基于固定 seed 和算法；否则用区间级比较 |
| Monte Carlo | 使用 MCSE、coverage interval，不逐复制比较 |

以上只是起点。Agent 必须从理论精度、跨平台复现和独立实现差异中推导实际容差。

### 13.3 自动推导容差

流程：

1. 在同一锁定环境重复运行参考实现 10 次；
2. 在至少两个平台或两个 BLAS 环境运行；
3. 计算字段的最大数值抖动；
4. 取得：

   ```text
   runtimeNoise = max pairwise difference
   crossEngineDifference = primary-secondary difference
   theoreticalFloor = method-specific floor
   ```

5. 容差候选：

   ```text
   max(10 × runtimeNoise, 2 × crossEngineDifference, theoreticalFloor)
   ```
6. 若容差候选超过方法上限，Case 不得通过，进入冲突分析。
7. 容差必须写入理由和证据，不得由测试失败动态扩展。

### 13.4 指标上限

建议设置硬上限：

```yaml
closedFormMaxAbsTolerance: 1e-7
olsMaxAbsTolerance: 1e-5
emmMaxAbsTolerance: 1e-4
iterativeEstimateMaxAbsTolerance: 1e-3
fitIndexMaxAbsTolerance: 0.002
```

超出上限通常说明：

- 模型并不相同；
- 编码不一致；
- 估计器不一致；
- 缺失处理不同；
- 标准化定义不同；
- 软件算法存在实质差异；
- 参考来源不适合。

---

## 14. 特殊比较规则

### 14.1 因子符号不确定

EFA、PCA、部分潜变量解可能整体乘以 `-1`。比较前应在保持协方差结构的前提下进行符号对齐。

不得因单纯符号反转判定失败。

### 14.2 因子排列不确定

对探索性因子解：

1. 计算绝对载荷相似矩阵；
2. 使用 Hungarian matching 对齐因子；
3. 对齐符号；
4. 再比较载荷、Φ 和共同度。

同时必须比较：

- 因子数；
- 拟合；
- 共同度；
- 旋转类型；
- 相关矩阵类型。

### 14.3 类别与参数标签

不同软件可能使用：

```text
A2 - A1
A1 - A2
condition2
factor[level2]
```

规范化器必须根据 AnalysisSpec 的稳定 level ID 映射，不得根据显示文本猜测。

### 14.4 标准化系数

必须区分：

- unstandardized；
- std.lv；
- std.all；
- partially standardized；
- OR；
- log-odds；
- probability marginal effect。

不同尺度不得直接比较。

### 14.5 Robust 与 scaled 统计量

必须记录：

- estimator；
- test correction；
- scaling factor；
- reference statistic；
- nested comparison method。

例如 WLSMV 模型比较不能把普通卡方差直接当作正确差异检验。

### 14.6 不可估计和失败

失败也是金标准：

```json
{
  "expectedStatus": "failed",
  "reasonCode": "EMPTY_CELL",
  "mustNotReturnEstimates": true,
  "mustNotFallback": true
}
```

不得仅断言“抛出异常”，而应断言：

- 稳定错误码；
- 受影响对象；
- 没有成功结果；
- 没有模型替换；
- 没有部分伪输出；
- 任务资源已回收。

---

## 15. 自动冲突解决

### 15.1 首先假设是定义差异

当 primary、secondary、SUT 不一致时，按以下顺序核对：

1. 数据行和缺失样本是否一致；
2. 分类变量水平和基准组；
3. contrast 编码；
4. 是否包含截距；
5. sums of squares 类型；
6. ML/REML；
7. 估计器与 robust correction；
8. df 方法；
9. 协方差结构；
10. 标准化尺度；
11. 置信区间方法；
12. multiple-comparison adjustment；
13. cluster 定义；
14. 权重；
15. 有序变量阈值和参数化；
16. 优化器、起始值和收敛阈值。

### 15.2 自动归因标签

```text
DATA_MISMATCH
SPEC_MISMATCH
CODING_MISMATCH
ESTIMATOR_MISMATCH
DF_METHOD_MISMATCH
STANDARDIZATION_MISMATCH
MISSING_METHOD_MISMATCH
REFERENCE_IMPLEMENTATION_DISAGREEMENT
NUMERICAL_INSTABILITY
SUT_DEFECT
UNRESOLVED
```

### 15.3 一致性规则

可自动接受的情况：

- 两个参考实现和 SUT 都在规定容差内；
- primary 与公式一致，secondary 只在已知软件定义字段上不同，并可明确映射；
- 结果在数学等价变换后完全一致；
- Monte Carlo 差异落在联合 MCSE 范围内。

不得自动接受：

- 只有 SUT 与其中一个来源一致；
- 两个参考来源差异无法归因；
- 通过删除不一致字段才一致；
- 需要扩大容差超过上限；
- 只有 p 值方向一致而估计量不同；
- 来源版本或模型命令不明。

### 15.4 证据隔离

无法消解时：

```text
case.status = quarantined
capability.status <= autoverified_l1
releaseCandidate = false
```

Agent 必须输出：

- 冲突字段；
- 三方数值；
- 已排除原因；
- 剩余假设；
- 需要新增的独立证据；
- 是否疑似生产缺陷。

---

## 16. 五种自主金标准构建模式

## 16.1 模式 A：闭式解与极小可解数据

适用：

- 均值、方差、协方差；
- Pearson/Spearman 的小样本；
- OLS；
- Welch t；
- Hedges’ g；
- 简单 planned contrast；
- Rubin pooling；
- ICC 的简化情形；
- 解析功效。

要求：

- 独立 Python/NumPy 或纯标准库实现；
- 不调用生产函数；
- 使用 4–20 行的可人工检查小数据；
- 保存中间矩阵和公式分解；
- 使用严格容差。

## 16.2 模式 B：权威开源包

适用：

- psychometric；
- ANOVA/EMM；
- LMM；
- MI；
- SEM；
- IRT。

要求：

- 固定版本；
- 使用官方文档支持的函数；
- 保存完整命令；
- 输出 `sessionInfo`；
- 不使用生产内部封装；
- 参考提取器单独实现。

## 16.3 模式 C：公开冻结商业软件输出

适用：

- Mplus SEM/增长/等值性；
- Stata mixed/mi；
- SPSS GLM；
- SAS mixed。

来源可以是：

- 软件官方示例；
- User’s Guide example；
- 官方技术说明；
- 论文官方补充文件；
- 合法公开的输入与输出文件。

要求：

- 输入文件和输出文件必须配对；
- 记录软件版本；
- 解析原始输出；
- 不能只使用论文中四舍五入表格；
- 若无法确认完整设置，只能作为辅助证据。

## 16.4 模式 D：模拟真值

适用：

- CFA/WLSMV；
- ESEM/bifactor；
- IRT/DIF；
- GLMM；
- RI-CLPM；
- latent growth；
- multilevel mediation；
- Monte Carlo power。

要求：

- DGP 与分析模型分离；
- 参数结构化，不接受任意脚本字符串；
- 至少 500–2000 个复制，视复杂度决定；
- 报告 bias、RMSE、coverage、Type I error、power、收敛率；
- 失败复制进入分母；
- seed 树确定性派生；
- 允许分块恢复。

## 16.5 模式 E：性质与变形测试

示例：

### OLS

- Y 加常数：斜率不变，截距平移；
- X 乘常数：系数按倒数缩放；
- 行重排：结果不变；
- 分类标签重命名但 level ID 不变：结果不变。

### EFA/CFA

- 题项顺序改变：同一模型语义不变；
- 因子 marker 改变：适当标准化解等价；
- 因子符号反转：拟合不变；
- 完美共线：稳定失败。

### ANOVA/EMM

- cell 行顺序改变：结果不变；
- 对比权重乘常数：估计和 SE 同比例变化，t/F 不变；
- factor level 重命名：稳定 ID 下结果不变。

### LMM

- cluster 标签置换：结果不变；
- cluster 内行顺序改变：结果不变；
- 随机效应方差接近零：singular/边界状态正确；
- within 与 between 人工分离数据：可恢复两种效应。

### MI

- m=1 时不得宣称 Rubin 合并；
- 所有插补估计相同：between variance 为 0；
- 破坏任一插补列：整体 pooled result 失败；
- 插补顺序变化：pooled 结果不变。

---

## 17. R2 方法专用金标准策略

## 17.1 WP-MEASURE-01：Ordinal reliability

推荐证据：

```text
Primary: psych 或经核验的 polychoric + omega 实现
Secondary: 独立 polychoric 矩阵 + 矩阵公式/另一包
Additional: 合成 tau-equivalent、congeneric、bifactor 数据
```

场景：

1. 连续近似正态；
2. 5 点 ordinal；
3. 极端偏态类别；
4. 两题量表；
5. 反向题；
6. 结构性缺失；
7. 非正定 polychoric；
8. 单题或常量题失败。

必测：

- Pearson α；
- ordinal α；
- omega total；
- omega hierarchical（适用时）；
- item-total；
- 有效 N；
- correlation matrix；
- 失败与警告。

不得：

- 两题量表强制计算复杂 omega；
- polychoric 非正定后静默改 Pearson；
- 无一般因子模型时输出 ωh。

## 17.2 WP-MEASURE-02：EFA

推荐数据：

- `psych` 官方示例；
- 包内公开人格或认知数据；
- 合成已知载荷数据；
- ordinal 离散化版本；
- 小样本非正定 fixture。

Primary：

```text
psych::fa / psych::fa.parallel / polychoric
```

Secondary：

```text
独立因子分解、另一包或 Python factor_analyzer
```

必测：

- 相关矩阵；
- 因子数；
- eigenvalues；
- MAP/parallel；
- unrotated loadings；
- rotated loadings；
- Φ；
- communalities；
- uniqueness；
- fit 与收敛；
- factor matching 后的数值。

边界：

- 两因子高度相关；
- 交叉载荷；
- Heywood；
- 类别稀疏；
- pairwise 导致非正定；
- 因子数过多。

## 17.3 WP-MEASURE-03：CFA/MLR/WLSMV

推荐数据：

- lavaan 官方 `HolzingerSwineford1939`；
- lavaan `PoliticalDemocracy`；
- ordinal 化的公开数据；
- 合成 CFA 数据。

Primary：

```text
lavaan 官方实现
```

Secondary：

```text
独立 SEM 包、Mplus 官方冻结输出或独立矩阵推导特例
```

必测：

- estimate；
- SE；
- z；
- CI；
- loadings；
- intercepts/thresholds；
- residual variance；
- latent variance/covariance；
- CFI/TLI/RMSEA/SRMR；
- robust/scaled statistic；
- N 与 missing pattern；
- converged；
- Heywood；
- positive definite。

特别规则：

- ML、MLR、WLSMV 分开建 Case；
- WLSMV 记录 delta/theta parameterization；
- categorical model 不把普通 ML 结果作为等价参考；
- robust fit 必须比较相同修正定义。

## 17.4 WP-MEASURE-04：Measurement invariance

Case：

1. configural；
2. metric；
3. scalar/threshold；
4. strict；
5. known partial invariance；
6. 非等值模拟；
7. 小组样本不平衡；
8. ordinal thresholds。

必测：

- 每一级模型语法；
- equality constraints；
- free/fixed parameters；
- fit；
- scaled difference；
- latent mean reference group；
- released parameters；
- 样本 N。

自动化限制：

- Agent 可以验证用户明确指定的 partial release；
- Agent 不得根据 modification indices 自主释放参数并将其作为正式金标准；
- 若测试 partial invariance，释放集合必须预先写入 fixture。

## 17.5 WP-MEASURE-05：ESEM/Bifactor/IRT/DIF

必须以模拟恢复为核心。

### Bifactor

必测：

- general/specific loadings；
- ωh；
- ECV；
- PUC；
- factor determinacy；
- Heywood；
- general factor 弱时的警告。

### ESEM

必测：

- target matrix；
- rotation criterion；
- factor correlation；
- cross-loadings；
- factor matching。

### IRT/DIF

必测：

- discrimination；
- thresholds/difficulty；
- item/test information；
- local dependence；
- DIF effect；
- linking/reference group；
- category sparsity。

至少包含：

```text
无 DIF 真值
均匀 DIF
非均匀 DIF
低区分题
类别空缺
样本不平衡
```

## 17.6 WP-CMB-01：Marker/ULMC

由于 CMB 不存在“检验通过即排除偏差”的真值，金标准只验证计算和模型行为。

必测：

- marker adjustment 公式；
- baseline 与 method-factor 模型；
- fit difference；
- method loadings；
- 不可识别；
- method factor 与 trait 高相关；
- 无方法因子模拟；
- 有方法因子模拟。

报告不得自动生成“共同方法偏差不存在”。

---

## 18. R3 方法专用金标准策略

## 18.1 Between factorial / ANCOVA

推荐数据：

- `ToothGrowth`；
- `Moore`；
- 合成平衡 2×2；
- 不平衡 2×3；
- 空 cell；
- rank deficiency。

Primary：

```text
afex / base lm / car + emmeans
```

Secondary：

```text
独立设计矩阵和 contrast 公式；公开 SPSS/Stata/SAS 输出
```

必测：

- model matrix；
- sums of squares 类型；
- F、df、p；
- adjusted means；
- EMM；
- planned contrasts；
- contrast covariance；
- CI；
- effect size；
- per-cell N。

## 18.2 Repeated / Mixed

推荐数据：

- `OBrienKaiser`；
- 合成球形数据；
- 合成非球形数据；
- 缺失波次；
- 重复 subject-wave 行；
- 不完整 cell。

必测：

- subject mapping；
- within factor 顺序；
- Mauchly；
- GG/HF epsilon；
- corrected df；
- EMM；
- contrast；
- participant N 与 row N。

不得：

- 缺失波次时静默改 LMM；
- 宽转长后把行数当参与者数；
- GG 不可用时返回 0。

## 18.3 Games–Howell

Primary：

```text
独立公式实现或权威实现
```

Secondary：

```text
第二包/公开软件输出
```

场景：

- 单一组间因子；
- 组数 3、4；
- 极端异方差；
- 不等 N；
- 某组 N<2；
- 有协变量时稳定拒绝；
- 多因素时稳定拒绝。

必测：

- mean difference；
- Welch-type SE；
- df；
- studentized range p；
- CI；
- adjustment 标识。

## 18.4 EMM 与计划对比

Primary：

```text
emmeans 官方实现
```

Secondary：

```text
独立 reference grid + Lβ + variance formula
```

必须冻结：

- reference grid；
- weighting；
- nuisance averaging；
- contrast weights；
- adjustment；
- df method；
- response/link scale。

## 18.5 Cluster robust / randomization inference

CR0、CR1、CR2 必须作为不同 capability 或明确方法字段。

必测：

- cluster 数；
- cluster size；
- bread/meat；
- finite sample correction；
- df；
- singleton cluster；
- 小 cluster 警告；
- cluster label permutation invariance。

Randomization inference：

- 冻结 assignment mechanism；
- 枚举或抽样空间；
- seed；
- test statistic；
- 双侧定义；
- 不合规和缺失的处理。

## 18.6 Multiplicity / TOST

Multiplicity：

- Holm；
- BH；
- 无调整；
- family ID；
- raw/adjusted p；
- 排序与并列。

TOST：

- lower/upper equivalence bound；
- 两个单侧检验；
- CI 与 SESOI；
- equivalence/nonequivalence/indeterminate；
- 不得以“不显著”替代等效。

---

## 19. R4 方法专用金标准策略

## 19.1 MICE 数据集生成

Primary：

```text
mice 官方实现
```

Secondary：

```text
独立插补检查、已知 MAR 合成数据或另一实现
```

注意：随机插补不应逐单元格比较。比较：

- method assignment；
- predictor matrix；
- seed；
- chain trace；
- observed/imputed distribution；
- missing cells only；
- 结构性缺失保持；
- 被动变量一致；
- 完成数据 schema；
- 数据 lineage；
- 失败次数。

## 19.2 Rubin pooling

此部分优先建立 G1 闭式解。

输入：

```text
每个插补的 Q_j
每个插补的 U_j
m
complete-data df
```

必测：

- Qbar；
- Ubar；
- B；
- T；
- r；
- df；
- lambda；
- FMI；
- CI；
- relative efficiency。

Primary：

```text
独立 Python 公式
```

Secondary：

```text
mice::pool / pool.scalar
```

边界：

- B=0；
- m=1；
- 某插补模型失败；
- 参数缺失；
- dfcom 不同；
- robust SE。

## 19.3 解析功效

应同时验证：

```text
forward power
solve N
solve effect size
back-check
```

Primary：

```text
独立非中心分布公式
```

Secondary：

```text
pwr/WebPower 或公开 G*Power 结果
```

必测：

- α；
- 双/单侧；
- effect definition；
- df；
- allocation ratio；
- integer rounding；
- achieved power；
- infeasible request。

## 19.4 Monte Carlo 功效

不得把单次成功率当金标准。

必须验证：

- DGP；
- 正式分析核心；
- target hypothesis；
- alpha；
- total replicates；
- fit success；
- convergence failure；
- singular；
- Heywood；
- rejection count；
- power；
- MCSE；
- coverage；
- bias；
- RMSE；
- Type I error；
- seed tree；
- resume 后结果等价。

自动门禁示例：

```yaml
powerDifferenceMax:
  formula: "2 * sqrt(mcse_primary^2 + mcse_secondary^2)"
coverageTarget:
  lower: 0.925
  upper: 0.975
maxConvergenceFailureRate: 0.05
allReplicatesInDenominator: true
```

## 19.5 Robustness / specification curve

验证重点不是某个“正确结果”，而是编排和完整性：

- 合法规格数；
- 去重；
- 每个规格的 hash；
- 失败规格保留；
- estimand 映射；
- 排序；
- curve 数据；
- 规格过滤规则；
- 预算、取消和恢复；
- 不得只统计显著比例。

---

## 20. R5 方法专用金标准策略

## 20.1 ICC / rwg

Case：

- 组内高度一致；
- 无组间差异；
- 不平衡 cluster；
- 小 cluster；
- 单人 cluster；
- 不同零分布假设。

必测：

- ICC(1)；
- ICC(2)；
- rwg/rwg(j)；
- cluster N；
- cluster size；
- ANOVA components；
- 不可估计原因。

## 20.2 Gaussian LMM

推荐数据：

- `sleepstudy`；
- `Penicillin` 或其他官方示例；
- 合成已知随机截距/斜率；
- 不平衡 cluster；
- singular 数据。

Primary：

```text
lme4/lmerTest
```

Secondary：

```text
statsmodels MixedLM、nlme 或公开 Stata mixed 输出
```

分开验证：

- ML 与 REML；
- random intercept；
- random slope；
- correlated/uncorrelated random effects；
- Satterthwaite；
- Kenward–Roger；
- asymptotic。

必测：

- fixed effects；
- SE；
- df；
- CI；
- random variance/covariance；
- residual variance；
- ICC；
- logLik；
- convergence；
- gradient；
- singular；
- cluster size。

## 20.3 Within–between 与中心化

建立人工可解 fixture：

```text
x = person mean + within deviation
y = β_between * person mean + β_within * deviation + error
```

必测：

- cluster mean；
- centered variable；
- within effect；
- between/contextual effect；
- 自动新增项是否被禁止；
- missing cluster；
- single-observation cluster。

## 20.4 Observed growth

Primary：

```text
lme4/nlme
```

Secondary：

```text
独立 mixed model 或公开软件输出
```

场景：

- 等距时间；
- 不等距时间；
- random intercept；
- random slope；
- 部分缺失；
- 只有两波；
- 选择性失访；
- re-entry。

必须区分：

```text
complete_cases
available_rows_ml
lavaan_fiml
```

三者不得混名。

## 20.5 CLPM / RI-CLPM / latent growth

以 G2 + G3 + G5 为最低要求。

数据：

- lavaan 官方 growth 数据；
- Mplus 官方示例；
- 合成三波/四波 DGP；
- 稳定 trait + within deviation 的 RI-CLPM 数据；
- 不等距 growth 数据。

必测：

- model syntax；
- equality constraints；
- autoregressive paths；
- cross-lagged paths；
- random intercept variances；
- within residuals；
- growth factor means/variances；
- time scores；
- fit；
- missing N；
- Heywood；
- nonpositive definite；
- parameter recovery；
- coverage。

不得：

- 把 CLPM 和 RI-CLPM 当同一 estimand；
- 三波以下自动拟合 RI-CLPM；
- 时间分数默认 0/1/2 而忽略真实间隔；
- 只因模型收敛即通过。

## 20.6 Diary / ESM

由于公开统一金标准较少，应以合成 DGP 和性质测试为核心。

必测：

- prompt 嵌套 person；
- person mean；
- within deviation；
- lag 构造；
- 跨夜连接规则；
- 不等距时间；
- AR(1)；
- random slope；
- compliance；
- prompt-level missing；
- burst；
- person 标签置换；
- 时间顺序错误时稳定拒绝。

---

## 21. 场景矩阵设计

每个 capability 的场景必须覆盖四象限：

| 类型 | 目的 |
| --- | --- |
| 正常典型 | 验证主路径 |
| 合法复杂 | 验证不平衡、缺失、稳健或多组 |
| 退化边界 | 验证奇异、近边界、类别稀疏 |
| 明确失败 | 验证稳定拒绝且无 fallback |

推荐最少数量：

| 方法复杂度 | 场景数 |
| --- | ---: |
| 闭式简单 | 3–5 |
| 常见回归/实验 | 5–8 |
| EFA/CFA/LMM | 8–12 |
| WLSMV/等值性/IRT | 10–15 |
| RI-CLPM/Monte Carlo/多层中介 | 12–20 |

---

## 22. 自动 Golden 生成流程

建议提供以下命令：

```bash
python tools/goldens/plan.py \
  --capability measurement.cfa.ordinal.wlsmv.v1

python tools/goldens/discover.py \
  --plan golden-plans/measurement.cfa.ordinal.wlsmv.v1.yaml

python tools/goldens/acquire.py \
  --discovery build/goldens/discovery.json

python tools/goldens/build-references.py \
  --capability measurement.cfa.ordinal.wlsmv.v1

python tools/goldens/reconcile.py \
  --capability measurement.cfa.ordinal.wlsmv.v1

python tools/goldens/freeze.py \
  --capability measurement.cfa.ordinal.wlsmv.v1

python tools/goldens/verify.py \
  --capability measurement.cfa.ordinal.wlsmv.v1 \
  --offline
```

### 22.1 `plan.py`

输出：

- estimand；
-支持与拒绝；
- 所需证据；
- 查询；
- 场景；
- 字段；
- 容差策略。

### 22.2 `discover.py`

职责：

- 调用官方 API 或搜索；
- 生成来源候选；
- 评分；
- 去重；
- 检查许可；
- 不执行代码。

### 22.3 `acquire.py`

职责：

- 下载；
- 验证 Content-Type；
- 检查大小；
- 计算 SHA；
- 解压安全检查；
- 保存许可和来源；
- 禁止路径穿越。

### 22.4 `build-references.py`

职责：

- 在隔离容器运行 primary/secondary；
- 保存 raw 和 normalized；
- 收集环境信息；
- 限制资源；
- 不读取 SUT 结果。

### 22.5 `reconcile.py`

职责：

- 规范化；
- 对齐；
- 计算差异；
- 推导容差；
- 冲突归因；
- 生成 expected 候选。

### 22.6 `freeze.py`

职责：

- 只接受无未解冲突的 Case；
- 写入 hash；
- 将 status 设为 frozen；
- 生成只读 bundle；
- 生成 attestation；
- 不允许普通分支直接覆盖。

### 22.7 `verify.py`

职责：

- 默认离线；
- 校验所有 hash；
- 运行 SUT；
- 比较；
- 输出机器和人类可读报告；
- 不修改 expected。

---

## 23. Comparator 伪代码

```python
def verify_case(case):
    assert_hashes(case)
    assert_reference_independence(case)
    spec = load_spec(case)
    expected = load_expected(case)

    sut_result = run_sut_in_isolation(
        data=case.dataset,
        spec=spec,
        seed=case.seed,
    )
    normalized = canonicalize_sut(sut_result, spec)

    failures = []
    for rule in case.comparison_rules:
        actual_value = jsonpath_get(normalized, rule.path)
        expected_value = jsonpath_get(expected, rule.path)

        outcome = compare_by_rule(
            actual=actual_value,
            expected=expected_value,
            rule=rule,
        )
        if not outcome.passed:
            failures.append(outcome)

    invariant_failures = run_metamorphic_checks(case, normalized)
    failures.extend(invariant_failures)

    return VerificationReport(
        passed=len(failures) == 0,
        failures=failures,
        provenance=collect_provenance(),
    )
```

---

## 24. 模拟恢复伪代码

```python
def parameter_recovery(plan):
    results = []

    for replication in range(plan.replicates):
        seed = derive_seed(plan.master_seed, replication)

        data = generate_data_from_structured_dgp(
            dgp=plan.dgp,
            seed=seed,
        )

        fit = run_formal_analysis_core(
            data=data,
            spec=plan.analysis_spec,
        )

        results.append({
            "replication": replication,
            "converged": fit.converged,
            "singular": fit.singular,
            "heywood": fit.heywood,
            "estimates": fit.estimates,
            "covered": evaluate_coverage(fit, plan.true_parameters),
        })

    return summarize_all_replicates(
        results=results,
        denominator=plan.replicates,
    )
```

强制要求：

```text
denominator = 全部预定复制
```

不收敛、奇异或 Heywood 不得从分母中删除。

---

## 25. CI/CD 分层

### 25.1 Pull Request：Quick

- 不联网；
- 校验 bundle hash；
- 每个受影响 capability 跑 1–3 个核心 Case；
- 运行独立性静态检查；
- expected 不得更新；
- 失败阻止合并。

### 25.2 Main/Nightly：Full

- 不联网或只访问内部缓存；
- 全部 Golden Case；
- 全部性质测试；
- 参数恢复的缩减复制；
- 多平台运行；
- 资源与超时。

### 25.3 Scheduled Golden Refresh

- 允许联网；
- 检查参考包新版本；
- 不直接替换冻结 goldens；
- 在新目录生成 candidate；
- 同时用旧版和新版参考运行；
- 输出版本差异报告；
- 若定义变化，创建新 caseVersion 或 capability version；
- 若只是数值微小变化，仍需保留旧证据。

### 25.4 Release

- 全部冻结 Case；
- 完整参数恢复；
- SBOM；
- artifact attestation；
- capability/status/docs 一致性；
- `unresolvedConflicts == []`；
- 自动状态最高升至 `autonomously_verified_release_candidate`。

---

## 26. Golden 更新策略

### 26.1 禁止自动覆盖

普通测试中：

```text
expected.json 必须只读
```

以下行为应导致 CI 失败：

- expected 文件修改但无 `golden-refresh` 标记；
- manifest hash 不匹配；
- reference 版本改变但 caseVersion 未变；
- 数据变化但来源记录未更新；
- 容差扩大；
- 删除失败 Case；
- 删除不一致字段。

### 26.2 版本升级

使用语义化版本：

- Patch：文档或不影响数值的元数据修复；
- Minor：新增场景或新增字段，不改变原 estimand；
- Major：估计器、编码、尺度、缺失、df 或 estimand 变化。

### 26.3 漂移检测

每次依赖升级比较：

```text
旧参考 → 旧 expected
新参考 → candidate expected
旧 SUT → 旧 expected
新 SUT → candidate expected
```

区分：

- reference drift；
- SUT drift；
- dependency drift；
- canonicalizer drift；
- intended method change。

---

## 27. Mutation Testing

金标准必须证明能发现错误，而不仅是当前代码能通过。

每个 capability 至少注入以下一类突变：

- 交换基准组；
- 改变 contrast 符号；
- 将 ML 改 REML；
- 删除 robust correction；
- 把 row N 当 participant N；
- 把 missing 当 0；
- 把 CI 临界值从 t 改 z；
- 改变方差分母；
- 删除一个随机效应；
- 失败后回退简单模型；
- Monte Carlo 只以成功拟合作分母；
- 因子载荷未做排列/符号对齐；
- Rubin pooling 忽略 between variance。

要求：

```text
每个关键突变至少被一个 Golden Case 或 invariant 检出
```

Mutation score 低于门槛时，不得升为自动发布候选。

建议门槛：

```yaml
minimumMutationScore: 0.85
criticalMutantsKilled: 1.0
```

---

## 28. 自动决策规则

### 28.1 可升级

```python
release_candidate = (
    all_required_cases_frozen
    and all_cases_pass
    and independent_reference_count >= 2
    and evidence_levels_satisfied
    and no_unresolved_conflicts
    and mutation_score >= threshold
    and offline_reproduction_passed
    and docs_registry_consistent
)
```

### 28.2 不可升级

任一条件成立即禁止：

```text
参考来源只有一个
参考与生产共享核心函数
存在未解数值冲突
容差超过方法上限
依赖未固定
数据许可不明
随机结果没有 MCSE
失败场景会静默 fallback
expected 可被普通 CI 覆盖
网络断开后无法验证
```

---

## 29. AI-Agent 工作记录模板

```markdown
# Golden Build Record

## Identity
- Work package:
- capabilityId:
- agent run ID:
- code commit:

## Estimand
- Target:
- Scale:
- Unit:
- Missing:
- SE/df:
- Coding:

## Support boundary
- Supported:
- Rejected:
- Stable error codes:

## Sources
| Source | Type | Version | Trust score | License | SHA |
|---|---|---:|---:|---|---|

## Reference independence
- Primary:
- Secondary:
- Shared dependencies:
- Static independence check:

## Cases
| Case | Normal/Boundary/Failure | Evidence | Status |
|---|---|---|---|

## Reconciliation
- Matching fields:
- Conflicts:
- Resolutions:
- Unresolved:

## Tolerances
- Policy:
- Cross-platform noise:
- Cross-engine difference:
- Final limits:

## Mutation testing
- Mutants:
- Killed:
- Survived:
- Score:

## CI
- Quick:
- Full:
- Release:
- Offline reproduction:

## Status decision
- Previous:
- New:
- Reason:
```

---

## 30. 失败码建议

```text
GOLDEN_PLAN_INCOMPLETE
SOURCE_NOT_AUTHORITATIVE
SOURCE_LICENSE_UNKNOWN
SOURCE_HASH_CHANGED
SOURCE_VERSION_UNPINNED
UNTRUSTED_CODE_BLOCKED
REFERENCE_NOT_INDEPENDENT
REFERENCE_EXECUTION_FAILED
REFERENCE_OUTPUT_INCOMPLETE
REFERENCE_CONFLICT
SPEC_MISMATCH
DATA_MISMATCH
CANONICALIZATION_FAILED
TOLERANCE_EXCEEDS_POLICY
EXPECTED_MUTATED_IN_CI
GOLDEN_HASH_MISMATCH
PARAMETER_RECOVERY_FAILED
COVERAGE_OUT_OF_RANGE
MONTE_CARLO_DENOMINATOR_INVALID
MUTATION_SCORE_TOO_LOW
OFFLINE_REPRODUCTION_FAILED
UNRESOLVED_GOLDEN_CONFLICT
```

错误必须包含：

```json
{
  "code": "REFERENCE_CONFLICT",
  "capabilityId": "...",
  "goldenCaseId": "...",
  "affectedFields": ["..."],
  "evidenceIds": ["..."],
  "message": "...",
  "suggestedNextEvidence": "..."
}
```

---

## 31. 无人工模式的现实边界

纯自动金标准系统可以高质量证明：

- 代码是否按冻结规格运行；
- 结果是否与权威实现一致；
- 数值是否可复现；
- 边界是否稳定失败；
- 模拟参数是否可恢复；
- 算法是否满足数学性质；
- 版本和数据是否可审计；
- 变更是否引起结果漂移。

它不能完全证明：

- 研究者选的 estimand 是否最有理论意义；
- partial invariance 应释放哪一个参数；
- 某个复杂模型是否应在真实论文中采用；
- 某个诊断阈值是否适合特定研究场景；
- 软件输出的实质解释是否符合领域理论；
- 真实数据中未观测的偏差是否被充分处理。

因此，本系统的自动结论必须使用：

```text
“该 capability 在冻结规格和验证场景内通过自动化多源数值验证”
```

不得使用：

```text
“该方法在所有研究中正确”
“该模型具有理论有效性”
“该结果无需任何方法复核”
```

---

## 32. 首批实施顺序

建议按以下顺序建立自主 Golden Pipeline：

### 第一批：闭式和成熟方法

1. `imputation.pooling.linear.rubin.v1`
2. `experiment.between.factorial.gaussian.v1`
3. `experiment.emmeans.planned_contrast.v1`
4. `power.t_test.analytic.v1`
5. `power.regression.f2.analytic.v1`
6. `multilevel.icc.two_level.v1`
7. `multilevel.lmm.two_level.gaussian.random_intercept.v1`

### 第二批：成熟迭代模型

1. `measurement.efa.continuous.minres.v1`
2. `measurement.efa.ordinal.polychoric.v1`
3. `measurement.cfa.continuous.mlr.v1`
4. `measurement.cfa.ordinal.wlsmv.v1`
5. `experiment.repeated.one_within.v1`
6. `multilevel.lmm.two_level.gaussian.random_slope.v1`
7. `longitudinal.growth.observed.gaussian.v1`

### 第三批：复杂潜变量与模拟

1. `measurement.invariance.multigroup.continuous.v1`
2. `measurement.invariance.ordinal.threshold.v1`
3. `measurement.bifactor.continuous.v1`
4. `measurement.irt.grm.v1`
5. `longitudinal.clpm.three_wave.v1`
6. `longitudinal.riclpm.three_wave.v1`
7. `longitudinal.latent_growth.linear.v1`
8. `power.mediation.monte_carlo.v1`

### 暂缓自动升级

- 自动 partial invariance 搜索；
- 自动模型修正；
- MTMM 大型模型；
- 多层中介；
- 复杂 ESM/DSEM；
- 三层/交叉 GLMM；
- 高维 DIF；
- 任意用户自定义 SEM 语法。

这些能力可以开发和验证固定切片，但不得在没有额外约束的情况下开放为通用自主支持。

---

## 33. 最终验收清单

每个 capability 在标记 `autonomously_verified_release_candidate` 前，Agent 必须逐项回答“是”：

### 规格

- [ ] estimand 完整；
- [ ] 支持和拒绝范围完整；
- [ ] estimator、missing、coding、SE/df、scale 明确；
- [ ] 无静默 fallback。

### 证据

- [ ] 至少三个 Golden Case；
- [ ] 至少两个独立参考；
- [ ] 至少一类 G5 或 G6；
- [ ] 来源可信度达标；
- [ ] 数据许可和 SHA 完整。

### 环境

- [ ] R/Python 版本固定；
- [ ] 依赖有 lock/hash；
- [ ] 容器按 digest 固定；
- [ ] session info 完整；
- [ ] artifact provenance 可验证。

### 数值

- [ ] 核心估计、SE、df、CI 已比较；
- [ ] fit/variance/sample flow 已比较；
- [ ] 容差有推导依据；
- [ ] 未超过方法上限；
- [ ] 不只比较 p 值。

### 边界

- [ ] 退化场景；
- [ ] 明确失败场景；
- [ ] 不可识别/不收敛；
- [ ] 无成功假状态；
- [ ] 任务资源回收。

### 强度

- [ ] 性质测试通过；
- [ ] 参数恢复或闭式解通过；
- [ ] mutation score 达标；
- [ ] 多平台或多环境验证；
- [ ] 离线重跑通过。

### 治理

- [ ] expected 在普通 CI 中只读；
- [ ] 无未解冲突；
- [ ] capability registry 已更新；
- [ ] docs/debt/status 一致；
- [ ] 自动状态没有越权写成 `supported`。

---

## 34. 推荐权威来源入口

以下来源用于 AI-agent 自动检索和环境构建。实际使用时必须记录访问时间、版本、文件哈希和许可。

### 统计方法与参考实现

- lavaan 官方教程：<https://lavaan.ugent.be/tutorial/>
- lavaan categorical/WLSMV：<https://lavaan.ugent.be/tutorial/cat.html>
- lavaan multiple groups：<https://lavaan.ugent.be/tutorial/groups.html>
- lavaan features/estimators：<https://lavaan.ugent.be/about/features.html>
- psych CRAN 文档：<https://search.r-project.org/CRAN/refmans/psych/html/00Index.html>
- emmeans 官方站点：<https://rvlenth.github.io/emmeans/>
- emmeans CRAN：<https://stat.ethz.ch/CRAN/web/packages/emmeans/index.html>
- lmerTest CRAN：<https://stat.ethz.ch/CRAN/web/packages/lmerTest/index.html>
- afex CRAN 文档：<https://cran.r-project.org/web/packages/afex/refman/afex.html>
- mice pooling：<https://amices.org/mice/reference/pool.html>
- mice scalar pooling：<https://amices.org/mice/reference/pool.scalar.html>
- Mplus User’s Guide Chapter 6 examples：<https://www.statmodel.com/usersguide/chapter6.shtml>
- Mplus examples：<https://www.statmodel.com/examples/penn.shtml>

### 开放材料与数据检索

- OSF API v2：<https://developer.osf.io/>
- Zenodo REST API：<https://developers.zenodo.org/>
- CRAN：<https://cran.r-project.org/>
- GitHub Releases API：<https://docs.github.com/rest/releases/releases>

### 复现与供应链

- renv：<https://opensource.posit.co/software/renv/>
- renv lockfiles：<https://rstudio.github.io/renv/reference/lockfiles.html>
- Docker image digests：<https://docs.docker.com/dhi/core-concepts/digests/>
- pip secure installs/hash checking：<https://pip.pypa.io/en/stable/topics/secure-installs/>
- GitHub artifact attestations：<https://docs.github.com/actions/security-for-github-actions/using-artifact-attestations>
- GitHub attestation REST API：<https://docs.github.com/en/rest/users/attestations>

---

## 35. 与原开发蓝图的关系

本规范是原蓝图“数值验证和测试资产”“统一完成定义”和“自动化编码代理执行顺序”的细化文件。

原蓝图规定：

- 每个方法 slice 至少包含公式/编码、正常金标准、退化边界、契约、任务、UI、复现、迁移、性能和文档一致性测试；
- 金标准必须有独立来源；
- 禁止使用同一函数生成 expected 再测试同一函数；
- golden 必须记录软件版本、命令、seed、字段和指标专属容差；
- 闭式解使用严格容差，迭代估计按具体定义，Monte Carlo 使用 MCSE、bias 和 coverage；
- 至少三个独立金标准场景只是 `supported` 的一部分，而不是全部。

本文件在此基础上补充：

- 纯自动验证状态；
- 来源可信度和网络检索规则；
- 独立性防火墙；
- 自动冲突裁决；
- 数据许可与供应链；
- GoldenPlan/Manifest；
- Mutation Testing；
- R2–R5 方法专用矩阵；
- 离线 CI 与定期刷新工作流。

---

## 36. Agent 最终执行指令

接到“为某 capability 建立金标准”的任务时，AI-agent 必须按以下顺序执行：

```text
1. 检查 git 工作区，保护现有修改。
2. 读取 AGENTS.md、项目 manifest、统计规范、原蓝图和本文件。
3. 查询 capability registry，确认当前 slice 状态。
4. 写 GoldenPlan；缺 estimand 或边界时停止。
5. 先建立闭式/合成最小 fixture。
6. 搜索两个以上权威且独立的参考路径。
7. 记录来源、许可、版本、哈希和可信度。
8. 在隔离环境执行参考实现。
9. 保存原始输出，再做规范化。
10. 核对数据、编码、估计器、缺失、df、尺度和调整。
11. 生成字段级 comparison rules。
12. 建立正常、复杂、退化和失败 Case。
13. 运行性质测试和参数恢复。
14. 注入关键 mutation，确认 Golden 能检错。
15. 解决全部冲突；不能解决则 quarantine。
16. 冻结 Golden Bundle 和 provenance。
17. 接入 Quick、Full、Release。
18. 离线重跑一次。
19. 更新 capability、文档和 debt。
20. 最高标记 autonomously_verified_release_candidate；不得自动写 supported。
```

任何一步通过修改 expected、放宽容差、删除失败场景或共享生产实现来“解决”问题，均视为验证失败。
