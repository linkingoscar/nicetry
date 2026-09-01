# 研径 ResearchPath

ResearchPath 是一个 Windows 本地优先、按研究范式组织的实证研究与可视化建模工作台。React 负责交互，FastAPI 负责任务、契约和持久化，R 负责统计估计；原始数据默认留在本机。

## 当前产品

导入数据或制定研究计划后，先选择研究范式，界面再生成相应流程：

1. **横截面问卷**：数据与测量 → 实证分析 → 条件过程/SEM → 方法与功效。
2. **纵向面板**：数据与测量 → 波次、等值性与纵向模型 → 方法与功效。
3. **日记 / ESM**：数据与测量 → 时间质检、中心化与多层模型 → 方法与功效。
4. **实验与准实验**：数据与测量 → 实验设计与功效；功效分析也可在没有活动数据集时先行。

共享能力包括 CSV/XLSX/SAV 导入、测量版本、引导/专家分析模式、实验设计、功效与精度、多重插补，以及 ESEM/Bifactor/GRM IRT/DIF。PROCESS 画布可搜索、预览并直接应用 55 个当前预编程编号，14 个常用编号另保留为快捷入口；自由画布也可反向识别编号。合法但未命中编号的自定义拓扑可保存和导出设计，暂不开放运行。

PROCESS 与高级方法都以后端返回的 `executionAvailable=true` 作为运行依据。高级方法当前整体状态为 `experimental`。完整能力边界见 [项目现状与产品边界](docs/00-项目现状与产品边界.md) 和 [能力矩阵](docs/07-能力矩阵与路线图.md)。

## 桌面轻应用

首次安装：

```powershell
./scripts/setup.ps1
./scripts/install-app.ps1
```

安装脚本会构建生产前端，并在桌面创建带专用图标的“研径 ResearchPath”快捷方式。以后双击图标即可在 Edge 独立应用窗口中使用：

- 无地址栏、标签栏和常驻终端；
- FastAPI 在 `127.0.0.1:9999` 同源托管 API 与生产静态文件；
- 使用独立 Edge 配置目录，不影响日常浏览器资料；
- 同一时间只允许一个实例；
- 关闭应用窗口后自动清理本轮本地服务；
- 日志：`.researchpath/logs/`

根目录 `启动研径.cmd` 是没有快捷方式时的备用入口。升级前端代码后，重新运行 `scripts/install-app.ps1` 即可刷新生产构建和快捷方式。

## 开发与验证

使用 PowerShell 7：

```powershell
./scripts/dev.ps1
./scripts/harness.ps1 -Mode Quick
./scripts/harness.ps1 -Mode Full
./scripts/harness.ps1 -Mode Release
```

开发模式仍使用 Vite `127.0.0.1:5173` 和 FastAPI `127.0.0.1:9999`，会保留终端以显示生命周期；它与面向日常使用的桌面轻应用是两条独立入口。

- Quick：架构、lint、类型和契约漂移；
- Full：Python、R `testthat`、Web、E2E、构建和 bundle；
- Release：Full、依赖审计、R 性能基准和发布证据。

详细规则见 [工程开发与验证](docs/04-工程开发与验证.md)。

## 项目结构

| 目录 | 内容 |
| --- | --- |
| `apps/web/` | React/Vite 前端 |
| `apps/api/` | FastAPI API、服务、任务和导出 |
| `engine/R/` | 模型、实证、高级方法 R 入口与单测 |
| `specs/` | JSON Schema 与跨语言契约 |
| `scripts/` | 安装、开发、门禁、备份和维护 |
| `tests/` | Playwright E2E |
| `docs/` | 文档导航、10 份主题文档和机器治理文件 |
| `archive/asset-packs/` | 未启用或部分恢复的开发资产 |
| `archive/project-history/` | 历史审计、ADR 和旧基线 |

机器可读入口见 [project.manifest.json](project.manifest.json)，文档按 [docs/README.md](docs/README.md) 阅读，归档规则见 [archive/README.md](archive/README.md)。

## 产品原则

- 原始数据只读，派生数据、测量和模型版本化；
- 同一数据、规格、版本和种子应可复现；
- 统计方法、回退、警告和实际执行路径必须对用户可见；
- 不自动搜索显著模型，不把横截面关联写成因果；
- 资产包中的文件和历史报告不等于当前可执行能力。

## 使用与授权

本仓库公开用于查看和评估，目前没有根级开源许可证，因此不能将公开可见性理解为复制、修改或再分发许可，也不应把项目描述为开源软件。具体边界见 [NOTICE.md](NOTICE.md)；官方 PROCESS for R 5.0 宏不包含在本仓库中。
