# workbuddy.md — 使用 WorkBuddy 开发的对话上下文

> 本文件记录本项目使用 **WorkBuddy** 完成开发的全过程，供「麦当劳程序员创意开发大赛 × WorkBuddy 联动奖励」核验。
> 所有凭证均已脱敏；开发过程中 Token 仅通过环境变量 `MCD_MCP_TOKEN` 使用，从未写入任何文件。

---

## 1. 开发环境

| 项 | 值 |
|---|---|
| 开发工具 | WorkBuddy（Agent 模式） |
| 会话日期 | 2026-10-14（16:00 – 18:20） |
| 运行环境 | Windows + Git Bash |
| 使用运行时 | Python 3.13.12（WorkBuddy 托管）、Node 22.22.2（仅用于 `node --check` 语法校验） |
| 使用的 WorkBuddy 能力 | Skill（skill-creator）、Bash、WebSearch / WebFetch、TaskCreate 任务管理、本地文件读写、present_files 交付、workspace memory 记忆 |

## 2. 开发时间线（按用户指令推进）

### 阶段 0 · 需求提出
> **用户**：`@scene#18:"Skill 开发" 基于麦当劳的 MCP 能力做一个今天吃什么随机生成器，显示今日运势`

WorkBuddy 先检查本地连接器：`list_installed_plugins` 与 `search_plugins` 均未返回麦当劳官方连接器，随后用 WebSearch 确认**麦当劳中国官方 MCP 已开放**（`https://mcp.mcd.cn`，Streamable HTTP + Bearer Token），决定做成"可自动降级"的 Skill：有 Token 走真实菜单，没有则用内置菜单。

### 阶段 1 · 按规范搭骨架
加载 `skill-creator` 技能，按其规范在用户级技能目录创建结构：

```
~/.workbuddy/skills/mcd-what-to-eat/
├── SKILL.md
├── scripts/    mcd_menu.py · fortune.py · build_page.py
├── references/ mcd-mcp-tools.md
└── assets/
```

用 TaskCreate 拆分 4 项任务跟踪进度（骨架 → 菜单适配层 → 运势引擎 → 交互页面），逐项完成后即时更新状态。

### 阶段 2 · 用户提供 Token，实测打通官方 MCP
> **用户**：提供了一个麦当劳 MCP Token（**已脱敏**，以下称 `<MCD_MCP_TOKEN>`）

WorkBuddy 用该 Token 实测 `https://mcp.mcd.cn`，发现与宣传材料不一致的地方（均已记录到 `skill/references/mcd-mcp-tools.md`）：

- 官方文档说 33 个工具，**实际返回 35 个**
- 返回体是「字段说明书 + `## Original Response` + 真实 JSON」的混合文本，不能直接 `json.loads`
- `query-meals` 的 `storeCode` 必传
- `query-nearby-stores` 必须**同时**给 `city` 和 `keyword`，只给城市报 `600058`
- 菜单标签挂在 `categories[].meals[].tags`，不在 `meals` 详情里
- 官方营养表**按规格拆分**（可乐中杯 147 / 大杯 224 / 小杯 107），而门店菜单只有一个笼统名

### 阶段 3 · 数据层返工
实测拿到真实门店（上海黄浦华旭国际大厦餐厅）126 个原始餐品，经多轮清洗：
剔除套装组合、周边商品、配料项 → 剩余 **49 个可搭配单品**，其中 30 项匹配到官方热量。

热量匹配策略定为「精确 → 唯一模糊 → 给出区间 → 不详」，**宁可输出区间也不猜错值**。

### 阶段 4 · 生成与校验
用官方数据生成单文件交互页面。校验方式：抽取页面内嵌 JSON 校验数据完整性 + `node --check` 校验 JS 语法 + 检查 Token 无泄漏。
（未做浏览器截图验证：本环境未安装 agent-browser，下载 Chromium 约 500MB，判断不划算。）

最后用 skill-creator 的 `quick_validate.py` + `package_skill.py` 完成校验与打包。

### 阶段 5 · 视觉改版三轮迭代
> **用户**：`整体设计风格变成星露谷像素游戏风`

重写 `build_page.py` 视觉层：像素字体（Zpix + Press Start 2P）、草地天空背景、奶油木质窗体（4px 硬描边 + 内阴影）、像素按钮、商品图相框、摇签时签等闪烁像素色。数据与逻辑零改动。

> **用户**：`字体加粗，无衬线字体，投影咋这么丑`

根因定位：像素字体配了 `font-weight:400` 导致字细，且用了彩色硬投影。
处理：移除两个像素字体（连带去掉字体 CDN 依赖，离线一致），改无衬线系统字体族，全局 700 / 重点位 900；删除全部 `text-shadow`；窗体投影从 8px 纯色厚块改为柔和阴影，仅保留 4px 薄下沉。

> **用户**：`其他不变，加上麦当劳Logo，汉堡冰淇淋像素化图形装饰`

新增：header 的金拱门像素 Logo（SVG `crispEdges`）+ 4 个漂浮的汉堡/冰淇淋像素装饰（`floaty` 动画，小屏自动隐藏）。全部内联 SVG，零外部资源。

> **用户**：`抽完签后显示大吉等运势结果配上对应emoji`

给 6 个签等各配 emoji（🎉大吉 / ✨吉 / 😊中吉 / 🍀小吉 / 🌤️末吉 / 😐平），数据层与展示层同时接入。
**顺手修掉一个隐藏 bug**：原 `renderFortune` 写 `el.textContent = f.level`，而 `f.level` 实为对象，签等位置会渲染成 `[object Object]`。

### 阶段 6 · 整理参赛仓库（当前阶段）
> **用户**：按大赛要求整理 README.md / CONTEST_DECLARATION.md / MCP_INTEGRATION.md / 源代码 / workbuddy.md 并上传 GitHub 公开

## 3. 关键设计决策

| 决策 | 理由 |
|---|---|
| 运势用**确定性随机**而非系统随机 | 同一天同一个人永远同一支签，仪式感不沦为"刷到满意为止"；换签靠显式的「再抽一签」 |
| 热量多命中时输出**区间**而非单值 | 官方营养表按规格拆分，猜一个数会显示一个"看起来很精确的错误值" |
| 抽签与官方 `draw-lottery` **彻底隔离** | 后者会真实扣减用户积分；页面摇签是纯本地算法，零远程调用 |
| Token 只走**环境变量** | 不在源码、页面、zip 包中留下任何真实凭证 |
| 无 Token 时**降级到内置菜单** | 保证功能可用，页面底部标注数据来源与降级原因 |
| 最终产物是**单文件 HTML** | 零依赖、可分享，无需后端 |
| 不装 Chromium 做截图验证 | 500MB 下载成本不划算，用 JSON 抽取校验 + `node --check` 替代 |

## 4. 安全与合规处理

- 用户在对话中贴过 MCP Token。WorkBuddy 仅通过环境变量使用，**未写入任何文件、未打入 zip 包、未出现在生成的 HTML 中**（每次生成后均校验 `TOKEN泄漏: False`）。
- 已在交付时提醒用户：该 Token 已在对话中明文出现，建议前往 `open.mcd.cn/mcp` 控制台**重新生成**。
- 仓库内 MCP 配置仅使用 `${MCD_MCP_TOKEN}` 占位符（见 `mcp-config.example.json`）。
- Skill 为**纯只读**：只调用 4 个查询类工具，明确禁止调用下单、领券、抽奖等写操作。

## 5. 产出清单

| 产物 | 位置 |
|---|---|
| Skill 源码 | `skill/` + `scripts/`（共约 1555 行 Python） |
| 参赛文档 | `README.md`、`CONTEST_DECLARATION.md`、`MCP_INTEGRATION.md`、本文件 |
| 脱敏配置 | `mcp-config.example.json` |
| 效果示例 | `examples/今天吃什么-麦门运势.html`（用官方门店真实数据生成） |
| 已安装 Skill | `~/.workbuddy/skills/mcd-what-to-eat/` |

## 6. 核验方式

- 本地 Skill 目录中保留了同一套代码，可与仓库逐一比对
- `skill/references/mcd-mcp-tools.md` 记录了实测细节（35 个工具清单、7 个坑），可直接复现验证
- 设置 `MCD_MCP_TOKEN` 后运行 `python3 scripts/build_page.py -o test.html --city 上海 --keyword 人民广场`，可复现页面与数据
