# ResearchPath (研径) UI/UX 与科研可视化深度审查及升级方案报告

> **审计基准时间**: 2026-08-11
> **审计覆盖规范与 Skill**:
> 1. `ui-ux-pro-max` (高级 UI/UX 设计智能、设计系统、色彩与微动效守卫)
> 2. `web-design-guidelines` (Vercel Web Interface Guidelines, 布局排版与 WCAG 2.2 无障碍规范)
> 3. `scientific-visualization` (Nature / Science / IEEE 学术科研可视化与数据表达规范)

---

## 1. 总体评估与综合评分 (Executive Summary)

ResearchPath (研径) 作为面向心理学、管理学及社会科学领域的本地优先 (Local-First) 实证研究与高级统计分析工作台，在功能完备度、R/Python 引擎统计严密性、图表导出 (SVG 矢量 + 300 DPI PNG) 方面展现出了极高水平。然而，在前端 UI 视觉美学、CSS 设计 Token 统一性、 Web 接口标准（WCAG / WAI-ARIA）以及科研可视化的色盲安全与刊物规范上，仍存在显著的重构与升级空间。

### 综合评分面板 (Out of 100)

| 审查维度 | 得分 | 评估等级 | 核心亮点 | 主要短板 |
| :--- | :---: | :---: | :--- | :--- |
| **`ui-ux-pro-max` (视觉与交互)** | **76 / 100** | B+ (良好) | 支持明暗主题、具有流程化工作区、部分组件有渐变/毛玻璃效果 | 缺少统一动态渐变/微动效，大量内联样式写死 Hex，主题切换覆盖不完整，Bento 布局缺乏层次 |
| **`web-design-guidelines` (Web 标准)** | **72 / 100** | B- (需改进) | DOM 盒模型基本规范，具有基础键盘快捷键 (Ctrl+K) 支持 | 存在大量物理内联魔数、语义化 `h1-h3` 标题层级跳过、部分按钮缺少 `:focus-visible` 和 async loading 状态 |
| **`scientific-visualization` (科研可视化)** | **78 / 100** | B+ (良好) | 提供了 JN 图、简单斜率图、热力图、矢量/300 DPI 导出及基础 Preset 切换 | 相关热力图硬编码红绿/蓝绿 RGB，不符合色盲安全标准；缺少 85mm/175mm 单双栏打印字号适配 |
| **综合加权得分** | **75.3 / 100** | **B+ (亟待升级)** | **具备坚实的统计与工具底座** | **视觉精致度、WCAG 合规性与学术刊物定制能力需全面重构** |

---

## 2. 维度一：`ui-ux-pro-max` 深度审查结果

`ui-ux-pro-max` 旨在为 AI 驱动的应用提供现代化、高美感、具备深层次交互反馈的设计守卫。以下是针对项目的详细审查：

### 2.1 色彩体系与主题系统 (Color Systems & Theme)
- ❌ **硬编码 Hex/RGB 毁坏主题切换**:
  - 在 [CorrelationHeatmap.tsx](../apps/web/src/components/empirical/CorrelationHeatmap.tsx) 中，`cellColor()` 使用了硬编码函数：正相关 `rgb(240-x, 249-x, 255-x)`（蓝色系），负相关 `rgb(254-x, 243-x, 199-x)`（琥珀色系）。在 `dark-theme` 下，热力图卡片背景被强制写死 `#ffffff`（Line 83），打破了暗色模式的视觉连贯性。
  - 在 `DataQualityWorkspace.tsx`、`JohnsonNeymanPlot.tsx`、`SimpleSlopePlot.tsx` 等多个组件中，大量的 `#0f172a`, `#1f5a49`, `#64748b`, `#f8faf9` 等颜色直接作为 style 属性写死在 React 组件中，而非引用 [tokens.css](../apps/web/src/styles/tokens.css) 定义的 `--bg-surface`, `--text-main`, `--brand-primary`。
- ⚠️ **品牌 Multi-Stop 渐变缺失**:
  - 项目在 [tokens.css](../apps/web/src/styles/tokens.css) 中定义了 `--brand-gradient: linear-gradient(135deg, #173f35 0%, #0d5c46 100%)`，但在 Header、Hero Banner、主按钮上使用率较低，主要标题缺少现代 UI 常见的 `background-clip: text` 多色渐变（如 `#6366f1` -> `#a855f7` -> `#ec4899` 或 Emerald-to-Teal 渐变）。

### 2.2 字体栈与排版层级 (Typography & Hierarchy)
- ⚠️ **字体栈缺少现代排版优化**:
  - 当前 [tokens.css](../apps/web/src/styles/tokens.css) 中为避开外链使用 `"Segoe UI", "Microsoft YaHei"`。虽然符合本地隐私规范，但标题缺少 `letter-spacing: -0.025em` 紧凑字距，且 body 文本未显式设置 `font-feature-settings: "cv02", "cv03", "cv04"`。
- ❌ **字号比例阶梯未标准化**:
  - 项目标题字号呈现随意性（如 25px、20px、18px、15px、13px、11px、9px），缺少 `rem` / `em` 响应式比例阶梯与明确的 Hero Title (`2.75rem`-`4rem`, `font-weight: 800`) 规范。

### 2.3 现代布局范式 (Layout Patterns)
- ⚠️ **Bento Grid Layout 运用不足**:
  - 在数据准备（DataWorkspace）、实证概览（EmpiricalOverviewTab）中，卡片仍采用传统的单栏或对称双栏网格，未能有效运用不对称 Bento Grid（2:1 或 3:1:2 的跨列/跨行卡片组合），导致视觉信息密度散乱。
- ⚠️ **Glassmorphism (毛玻璃) 局限**:
  - 仅在 JN Plot 悬浮提示框中使用了 `backdrop-filter: blur(10px)`。Toast 通知、Header 悬浮条、Command Palette 弹窗等未充分融合 `background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(16px)` 级联视觉。
- ❌ **Card Hover Elevation 缺失微动效**:
  - 大部分面板卡片在 `:hover` 时仅有 `border-color` 变化，缺少 `transform: translateY(-4px)` 与 Spring 缓动 (`transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1)`) 阴影浮起效果。

### 2.4 交互微动效 (Micro-Animations)
- ❌ **按钮点击无反馈 (Active Scaling)**:
  - 按钮没有统一配置 `:active { transform: scale(0.98); }` 物理按压反馈。
- ❌ **焦点环 (Focus Glow)**:
  - 内联 Style 的按钮缺少 `:focus-visible` 自定义 Halo 环 (`box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.25)`)。

### 2.5 占位符与空状态 (Placeholders & Empty States)
- ❌ **纯文本空状态文案**:
  - [App.tsx](../apps/web/src/App.tsx#L226) 中的未就绪状态仅为一段朴素的 `<p>请先导入数据、确认变量并完成构念计分。</p>`。缺乏高质感 SVG 矢量插图或动态交互引导引导图卡。

---

## 3. 维度二：`web-design-guidelines` 深度审查结果

基于 Vercel Web Interface Guidelines 与 WCAG 2.2 可访问性规范，对项目 HTML/CSS/JSX 的审查结果如下：

### 3.1 Typography & DOM Hierarchy (DOM 结构与标题)
- ❌ **跳过 Heading 层级或使用非语义化标签**:
  - [CorrelationHeatmap.tsx](../apps/web/src/components/empirical/CorrelationHeatmap.tsx) 使用 `<strong style={{ fontSize: '14px' }}>` 代替 `<h3>` 或 `<h4>` 标题。
  - [JohnsonNeymanPlot.tsx](../apps/web/src/components/results/JohnsonNeymanPlot.tsx) 使用 `<strong style={{ color: '#1f5a49' }}>` 充当卡片标题，未包裹在 `<h3>` 中，导致屏幕阅读器 (Screen Reader) 无法通过 H 快捷键建立页面大纲。
- ⚠️ **Touch Device Input 缩放预防**:
  - 部分数码/阈值输入框（如 `DataQualityWorkspace.tsx` Line 266 `width: 80px`）字号未达到 `16px` (目前为 `12px`/`13px`)，在 iOS Safari 上获取焦点时会触发自动页面缩放。

### 3.2 Layout, Spacing & Alignment (间距、网格与魔数)
- ❌ **严重的魔数 (Magic Numbers) 滥用与 CSS 内联写死**:
  - 在 React 组件中大量存在硬编码物理像素：
    - [CorrelationHeatmap.tsx](../apps/web/src/components/empirical/CorrelationHeatmap.tsx): `left = 140`, `top = 50`, `cellSize = Math.min(48, Math.max(32, Math.floor(450 / variables.length)))`, `margin: '18px 0'`。
    - [JohnsonNeymanPlot.tsx](../apps/web/src/components/results/JohnsonNeymanPlot.tsx): `width = 560`, `height = 280`, `left = 58`, `right = 22`, `top = 22`, `bottom = 42`。
    - [SimpleSlopePlot.tsx](../apps/web/src/components/results/SimpleSlopePlot.tsx): `width = 480`, `height = 260`, `left = 50`, `bottom = 40`。
  - 未绑定 4px/8px 网格尺度 tokens (`4, 8, 12, 16, 24, 32, 48, 64px`)，破坏了响应式弹性伸缩能力。

### 3.3 Interactive Elements & Controls (交互控制)
- ❌ **内联按钮缺失 `:focus-visible` 和 `:active` 伪类**:
  - 使用内联 `style={{ ... }}` 的按钮无法定义伪类（`:hover`, `:focus-visible`, `:active`），点击时出现浏览器默认外边框或无反应。
- ⚠️ **异步操作防重复点击与 Loading State**:
  - 部分“一键运行”、“导出 300 DPI PNG”等操作在异步生成期间，按钮没有禁用 (`disabled={loading}`) 或显示 Spinner 加载转轮。

### 3.4 Color & Contrast Rules (颜色与对比度)
- ❌ **低对比度辅助文本**:
  - 图表底部的说明文字（如 `#64748b` 字色在 `#f8faf9` 背景上，字号 10px / 11px），对比度约 `3.8:1`，低于 WCAG 2.2 AA 规范要求的 `4.5:1` 标准。
- ⚠️ **非颜色辅助指示器**:
  - 相关系数热力图中，数值正负与显著性仅通过单元格背景颜色与小号字体表达，未向单元格提供 `aria-label="变量X与变量Y的相关系数为0.45，显著性p<.001"` 等屏幕阅读器文案。

### 3.5 Media & Asset Rules (媒体与 CLS)
- ⚠️ **SVG 图表 ViewBox 与布局重排 (CLS)**:
  - SVG 图表普遍直接渲染内联 `<svg width="100%" height={height}>`，没有通过 CSS `aspect-ratio` 预留纵横比容器空间，在数据加载完成后渲染会导致页面下方内容发生二次跳变 (Layout Shift)。

---

## 4. 维度三：`scientific-visualization` 深度审查结果

基于 Nature, Science, IEEE 等顶级期刊可视化标准及学术表达规范，审查结果如下：

### 4.1 配色与色盲安全 (Colorblind Safety)
- ❌ **热力图硬编码红/蓝/绿（色盲不安全）**:
  - [CorrelationHeatmap.tsx](../apps/web/src/components/empirical/CorrelationHeatmap.tsx) 采用了自定义 RGB 混合算法（蓝色表示正相关，琥珀/红色表示负相关）。这种配色对于红绿色盲 (Deuteranopia / Protanopia) 用户极难准确区分强弱梯度与正负转向。
  - 缺乏 **Viridis**, **Plasma**, **Cividis**, **Okabe-Ito** 等学术界公认的感知均匀 (Perceptually Uniform) 色盲安全色板选择。
- ⚠️ **期刊 Preset 未覆盖全部图表**:
  - 虽然 [JournalPresetSelector.tsx](../apps/web/src/components/shared/JournalPresetSelector.tsx) 提供了 `Emerald`, `AMJ Navy`, `Psychology Classic`, `Monochrome` 四套 Preset，但目前仅接入了 `JohnsonNeymanPlot` 和 `SimpleSlopePlot`，相关热力图、EFA 碎石图（[ScreePlot.tsx](../apps/web/src/components/empirical/ScreePlot.tsx)）、PROCESS 路径图等均未接入统一 Preset 选择器。

### 4.2 导出品质与刊物单双栏排版 (Publication Standards & Formats)
- 🛠️ **矢量/300 DPI 导出能力 (项目亮点)**:
  - 项目已具备 `exportSvgAsFile` (SVG) 与 `exportSvgAs300DpiPng` (300 DPI 高清 PNG)，表现优异！
- ❌ **单/双栏尺寸适配与字号缩放 (Column Width Scaling)**:
  - 顶级期刊论文对插图尺寸有严格限制：
    - **单栏 (Single Column)**: 85 mm (3.35 inch / 约 240-300 px 显示宽度)
    - **双栏 (Double Column)**: 175 mm (6.9 inch / 约 500-600 px 显示宽度)
  - 当前图表定死 ViewBox 为 `560x280` 或 `480x260`，当用户把导出图表缩小嵌入 85mm 单栏论文时，10px 的坐标轴标签会缩小到 4pt 以下，导致在印刷版面中**彻底无法辨认**。

### 4.3 图表矩阵与统计表达规范 (Chart Matrix & APA 7th)
- ❌ **碎石图 (`ScreePlot.tsx`) 交互与信息量匮乏**:
  - 当前 ScreePlot 仅绘制了静态折线，缺少鼠标 Hover 交互、精确特征值 (Eigenvalue) 提示、累积方差解释率 (% Variance Explained) 柱状图辅助，且无 300 DPI / SVG 导出按钮。
- ⚠️ **APA 7th 统计数值格式化标准**:
  - APA 7th 规范要求：
    1. $p$ 值、相关系数 $r$、判定系数 $R^2$ 等取值不超过 1 的统计量，**不得带有前导零**（应书写为 `.001`、`.45` 而非 `0.001`、`0.45`）。
    2. 统计符号（如 *p*, *r*, *N*, *F*, *t*, *CI*）必须使用斜体。
  - 当前 Tooltip 和说明文案中（如 `P 值: {p.toFixed(3)}`、`样本数 (N): {n}`）未完全遵循 APA 7th 斜体与前导零规则。

---

## 5. 综合升级方案与落地路线图 (Actionable Upgrade Plan)

针对上述审查发现的问题，提出以下三阶段重构与升级方案：

### 5.1 阶段一：设计 Token 与主题系统全量重构 (`ui-ux-pro-max`)

#### 目标
1. 彻底清除 React 组件中的硬编码 Hex/RGB 颜色与内联魔数样式。
2. 建立完整的 CSS Variable Token 体系，全面适配 Light / Dark 模式。
3. 引入 Bento Grid 布局规范、Glassmorphism 级联与卡片 Spring Hover 微动效。

#### 具体落地方案

1. **增强 [tokens.css](../apps/web/src/styles/tokens.css)**:
   ```css
   :root {
     /* 1. 现代化多级渐变 Token */
     --gradient-hero: linear-gradient(135deg, #0d5c46 0%, #10b981 50%, #06b6d4 100%);
     --gradient-accent: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);

     /* 2. 毛玻璃与高阶阴影 */
     --glass-bg: rgba(255, 255, 255, 0.75);
     --glass-border: rgba(255, 255, 255, 0.3);
     --glass-blur: blur(16px);
     --shadow-spring: 0 20px 25px -5px rgba(15, 23, 42, 0.08), 0 8px 10px -6px rgba(15, 23, 42, 0.04);

     /* 3. 4px/8px 网格空间 Tokens */
     --space-1: 4px;
     --space-2: 8px;
     --space-3: 12px;
     --space-4: 16px;
     --space-6: 24px;
     --space-8: 32px;
     --space-12: 48px;

     /* 4. 标题与正文 Scale */
     --font-hero: 800 2.5rem/1.15 var(--font-main);
     --font-h1: 700 1.75rem/1.25 var(--font-main);
     --font-h2: 600 1.25rem/1.35 var(--font-main);
     --font-h3: 600 1.0rem/1.4 var(--font-main);
     --font-body: 400 0.9375rem/1.6 var(--font-main);
     --font-caption: 400 0.8125rem/1.5 var(--font-main);
   }

   /* 暗色模式适配 */
   [data-theme="dark"], body.dark-theme {
     --glass-bg: rgba(30, 41, 59, 0.75);
     --glass-border: rgba(255, 255, 255, 0.1);
     --shadow-spring: 0 20px 25px -5px rgba(0, 0, 0, 0.4);
   }
   ```

2. **卡片动效类与 Bento Grid 布局公共 CSS ([components.css](../apps/web/src/styles/components.css))**:
   ```css
   .bento-grid {
     display: grid;
     grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
     gap: var(--space-6);
   }

   .bento-card {
     background: var(--bg-surface);
     border: 1px solid var(--border-subtle);
     border-radius: var(--radius-lg);
     padding: var(--space-6);
     box-shadow: var(--shadow-sm);
     transition: transform 0.25s var(--ease-out-spring), box-shadow 0.25s var(--ease-out-spring);
   }

   .bento-card:hover {
     transform: translateY(-4px);
     box-shadow: var(--shadow-hover);
   }

   .btn-primary {
     background: var(--brand-primary);
     color: #ffffff;
     border: none;
     border-radius: var(--radius-md);
     padding: var(--space-2) var(--space-4);
     font-weight: 600;
     transition: all 0.2s var(--ease-out-spring);
     cursor: pointer;
   }

   .btn-primary:active {
     transform: scale(0.98);
   }

   .btn-primary:focus-visible {
     outline: 2px solid var(--brand-accent);
     outline-offset: 2px;
   }
   ```

---

### 5.2 阶段二：Web 规范、DOM 语义化与 A11y 强化 (`web-design-guidelines`)

#### 目标
1. 修复 HTML/DOM 标题跳过问题，将 `<strong style="...">` 升级为语义化 `<h2>` / `<h3>` 标题。
2. 为所有按钮与下拉框增加 `:focus-visible` / `:active` / `disabled` 状态。
3. 优化 WCAG 对比度与非颜色辅助指示器。

#### 核心代码改造点 (示例: [JohnsonNeymanPlot.tsx](../apps/web/src/components/results/JohnsonNeymanPlot.tsx))

```tsx
// 改造前：
// <strong style={{ color: '#1f5a49', fontSize: '13px' }}>
//   Johnson–Neyman 条件效应图：{predictorLabel} × {moderatorLabel}
// </strong>

// 改造后：符合 DOM 语义、组件样式与 A11y
<div className="chart-header">
  <h3 className="chart-title">
    <span>Johnson–Neyman 条件效应图：</span>
    <span className="chart-title-vars">{predictorLabel} × {moderatorLabel}</span>
  </h3>
  <span className="chart-badge-tip" role="note">
    💡 沿曲线滑动鼠标可查看条件效应与 95% CI
  </span>
</div>
```

---

### 5.3 阶段三：学术可视化与色盲安全顶级增强 (`scientific-visualization`)

#### 目标
1. **重构相关系数热力图 ([CorrelationHeatmap.tsx](../apps/web/src/components/empirical/CorrelationHeatmap.tsx))**：引入学术界标准的 **Viridis** / **Cividis** / **Okabe-Ito** 色盲安全连续色板，彻底淘汰硬编码 RGB！
2. **重构碎石图 ([ScreePlot.tsx](../apps/web/src/components/empirical/ScreePlot.tsx))**：注入 Tooltip 交互、累积方差贡献率柱状图、期刊 Preset 与双格式导出。
3. **增加 85mm / 175mm 论文排版字号适配模式**：在导出选单中提供“单栏 85mm 论文模式”与“双栏 175mm 论文模式”，自动调整 viewBox 缩放与坐标轴字号。

#### 相关热力图色盲安全色板 (Viridis & Okabe-Ito 方案)

```typescript
// 学术色盲安全色彩映射函数 (Perceptually Uniform Viridis & Diverging Okabe-Ito)
export function getScientificCellColor(value: number | null, paletteType: 'cividis' | 'viridis' | 'okabe_ito' = 'viridis') {
  if (value === null) return 'var(--bg-subtle)'
  const absVal = Math.abs(value)

  if (paletteType === 'viridis') {
    // Viridis 蓝紫-绿-黄单调渐变
  } else if (paletteType === 'okabe_ito') {
    // Okabe-Ito (2002) 盲人友好双极对比色:
    // 正相关: 蓝色 #0072B2 -> 浓蓝 #009E73
    // 负相关: 朱红 #D55E00 -> 琥珀 #E69F00
    if (value >= 0) {
      return `rgba(0, 114, 178, ${0.15 + absVal * 0.85})`
    } else {
      return `rgba(213, 94, 0, ${0.15 + absVal * 0.85})`
    }
  }
}
```

#### APA 7th 格式化格式器 (`apaFormatter.ts`)

```typescript
/**
 * APA 7th 格式化统计量：小于 1 的概率/相关系数自动省略前导 0
 */
export function formatAPASatistic(val: number | null | undefined, digits = 3): string {
  if (typeof val !== 'number' || isNaN(val)) return '—'
  const str = val.toFixed(digits)
  if (Math.abs(val) < 1) {
    return str.replace(/^(-?)0\./, '$1.')
  }
  return str
}

export function formatAPAPValue(p: number | null | undefined): string {
  if (typeof p !== 'number' || isNaN(p)) return '—'
  if (p < 0.001) return '< .001'
  return formatAPASatistic(p, 3)
}
```

---

## 6. 总结与下一阶段行动建议

本审查报告系统梳理了 ResearchPath 项目在 UI/UX 设计系统、Web 接口规范及科研可视化上的优势与短板。

### 建议优先落地的改动点 (Quick Wins)
1. **相关系数热力图 ([CorrelationHeatmap.tsx](../apps/web/src/components/empirical/CorrelationHeatmap.tsx)) 色盲安全改造**：接入 Okabe-Ito / Viridis 配色与 APA 7th Tooltip。
2. **内联魔数样式抽取到 CSS Tokens ([tokens.css](../apps/web/src/styles/tokens.css) & [components.css](../apps/web/src/styles/components.css))**：统一主题切换卡死问题。
3. **图表导出选单扩展**：为 ScreePlot 补全导出功能，为全图表增加单栏 (85mm) / 双栏 (175mm) 打印字号适配选项。

---
*本报告由 AI Coding Assistant 基于 `ui-ux-pro-max`, `web-design-guidelines`, `scientific-visualization` 技能库全量自动生成。*
