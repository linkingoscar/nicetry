# 多重统计验证实验室资产包

## 状态

`dormant`：不进入默认 Quick、Full 或 Release。

## 保存内容

- 26 个 capability、95 个场景和约两千个 Golden 资产文件；
- GoldenPlan、主/次参考、SUT 适配器、reconciliation 和 provenance；
- 变形、不变量、突变、模拟恢复、来源审计和离线复现工具；
- G0—G7 与无人值守发布候选的历史规范；
- 对应测试、配置、R 统计能力入口和前端证据类型。
- 36 个历史 Golden 案例构建/修正规则脚本；
- 1 份规格曲线空输入的历史运行输出。

## 补充资源清单

### `historical-tooling/golden-case-builders/`

原项目根目录 `scratch/` 中的 36 个 Python 脚本已经原样归档至此：

- 17 个 `setup_*.py`：生成 Golden case 的数据、分析规格、参考运行器和 manifest；
- 19 个 `fix_*.py`：修正比较规则、二级参考运行器或个别边界案例。

它们是验证实验室建设期间的一次性开发工具，不是产品运行代码，当前源码、Harness 和发布脚本均不引用它们。脚本内写有归档前的绝对项目路径，并假定 `tests/goldens`、`reference` 和 `tools/goldens` 位于仓库根目录，因此在当前归档位置**不能直接运行**。

恢复时应先：

1. 选择具体 capability，而不是批量恢复全部脚本；
2. 将脚本涉及的 Golden case、参考生成器和工具恢复至活动目录；
3. 把绝对路径改为由项目根目录参数或环境变量解析；
4. 在隔离分支运行并检查脚本可能覆盖的文件。

### `historical-outputs/specification-curve-empty-output.json`

这是原项目根目录 `out.json`。内容显示一次规格曲线/多模型稳健性计算没有产生任何 specification：

- `total_specifications = 0`；
- `median_effect = "NA"`；
- `significant_ratio = "NaN"`；
- `specifications_summary = []`；
- 运行器仍报告 `diagnostics.converged = true`。

它属于调试或联调输出，不是输入数据、正式 Golden 结果或当前产品配置。保留它用于追查历史空结果行为，但不应作为统计正确性的证据，也不参与任何默认运行。

## 何时恢复

- PROCESS/统计核心被重写；
- R 包或估计器发生重大升级；
- 出现明确的跨软件认证或外部审计要求；
- 新增高风险自研估计器。

普通 UI、数据、报告或成熟 R 包薄封装变更不应恢复整套实验室。

## 恢复步骤

1. 明确需要验证的 capability，不默认选择 `--all`。
2. 将所需 `tools/goldens`、case、plan 和脚本迁回原相对路径。
3. 检查归档期间的 import、schema 和 SUT 入口漂移。
4. 先运行单 case，再运行能力级验证。
5. 只有产品明确采用认证制度时，才重新接入 Harness/Release。

历史命令和路径保存在本包文档中；它们在归档位置不保证可直接执行。

内部规范中的 `docs/...` 引用保持归档时原貌，可能不再指向活动文件。恢复前先读仓库根目录 `docs/README.md`、`docs/04-工程开发与验证.md` 和 `project.manifest.json`，不要按历史链接直接接线。
