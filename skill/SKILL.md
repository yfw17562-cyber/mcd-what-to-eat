---
name: mcd-what-to-eat
description: This skill should be used when the user needs to decide "今天吃什么" at McDonald's (麦当劳/金拱门) in mainland China, draw a daily fortune (今日运势/抽签/摇签), or check McDonald's menu, prices, store info, or meal calories. It combines the McDonald's China official MCP real-time menu with a deterministic fortune engine to produce a meal combo plus a signed fortune, and can render a standalone interactive HTML page.
---

# 麦当劳 今天吃什么 · 麦门运势

## 用途

把「今天吃什么」这个问题变成一次可复现的抽签：从麦当劳中国官方实时菜单里搭配一份套餐
（主食 + 小食 + 饮品 + 可选甜品），同时给出当天的运势签（签等、宜忌、幸运数字/颜色/时段、签诗）。

结果同时支持两种交付形态：

1. **文本回答** —— 直接在对话里报出套餐与签文。
2. **交互页面** —— 生成单文件 HTML，内含摇签动画与套餐卡片，可离线打开。

## 何时使用

- 用户说「今天吃什么」「帮我决定午饭」「随便来一份麦当劳」「摇个签」。
- 用户要查某地麦当劳的门店、菜单、价格、热量。
- 用户想要一个「决定吃什么」的小工具 / 页面 / 抽签器。

不适用：实际下单、支付、领券、积分兑换。本 skill 只做「选什么」和「运势」，不产生任何交易副作用
（官方 MCP 中确实存在 `create-order`、`draw-lottery` 等写操作工具，本 skill 一律不调用，详见下节）。

## 前置条件

在 `https://open.mcd.cn/mcp` 用麦当劳账号登录 → 控制台 → 激活 → 复制 Token，
然后设置环境变量：

```bash
export MCD_MCP_TOKEN="你的token"
```

没有 Token 时 skill 不会失败，会自动降级到内置参考菜单（价格与热量为约值），链路照常可用。
判断当前数据来源看返回里的 `meta.source`：`official-mcp` 或 `builtin-fallback`。

## 工作流

### 第一步：确定数据来源与门店

官方 `query-meals` 必须传 `storeCode`，所以要先把门店定下来。两种方式：

```bash
# A. 按城市 + 关键词找店，取返回列表第一个
python3 scripts/mcd_menu.py stores --city 上海 --keyword 人民广场

# B. 已知门店编码直接用
python3 scripts/mcd_menu.py menu --store-code 1450713
```

`--city` 与 `--keyword` 必须同时提供，只给城市官方会返回 `600058 城市名或者关键词不能为空`。
若用户未指明地点，先问一句城市，不要凭空假设。

### 第二步：取菜单

```bash
python3 scripts/mcd_menu.py menu --city 上海 --keyword 人民广场
```

输出结构：`meta`（数据来源、门店、营养匹配情况）+ `categories[]`（按 `burger` / `side` / `drink` /
`dessert` 四个角色归好类的单品）。脚本已经处理掉官方返回的三类脏数据：套装组合、周边商品、
以及无法唯一对应的热量，详见 `references/mcd-mcp-tools.md`。

### 第三步：抽签

运势是**确定性**的：种子取自 `日期 + 签主 + 重抽序号` 的 SHA-256，同一天同一签主永远得到同一支签，
换签靠递增 `--reroll`。不要用系统随机数替代，否则「今天的运势」会变成每刷新一次就变一次。

```bash
python3 scripts/fortune.py --date 2026-10-14 --signer 小林 --pretty   # 人类可读
python3 scripts/fortune.py --date 2026-10-14 --signer 小林            # JSON
python3 scripts/fortune.py --date 2026-10-14 --signer 小林 --reroll 1 # 重抽
```

日期用真实当天日期，不确定时先取系统时间，不要凭记忆推算。

### 第四步：搭配套餐

```bash
python3 scripts/mcd_menu.py pick --seed 20261014 --city 上海 --keyword 人民广场 --prefer light --budget 45
```

`--prefer` 取值 `any` / `spicy` / `mild` / `light`；`--seed` 建议用 `日期 + 签主` 派生的整数，
保证同一天同一人拿到同一份套餐。`--budget` 超预算时会自动去掉最便宜的一项（而不是换掉最贵的一项，
这样更贴近「少点一份」的真实决策）。

### 第五步（可选）：生成交互页面

```bash
python3 scripts/build_page.py -o 今天吃什么.html --city 上海 --keyword 人民广场
```

产出单文件 HTML，无外部依赖，包含摇签动画、套餐卡片、官方商品图、分享文案复制。
生成后用 `present_files` 打开给用户看。页面里的抽签是前端重算的（同一套确定性算法），
所以用户可以在页面上反复「再抽一签」而不需要重跑脚本。

## 输出约定

回答用户时至少包含：

- **签等** 与一句话解（`levelHint`）
- **宜 / 忌**（各 1–2 条）
- **幸运数字、幸运色、幸运时段**
- **套餐清单**：每项名称 + 单价 + 热量，以及合计金额；热量不确定的项要如实标注，不要编造
- **数据来源**：说明是官方实时菜单（附门店名）还是内置参考价

## 数据诚实原则

- 热量只接受官方营养表的**精确命中**或**唯一模糊命中**；命中多个规格时输出区间（如 `107–224 kcal`）
  而不是挑一个看起来精确的错值。无法匹配就显示「热量不详」。
- 套餐总热量只要有一项不详，就必须写成 `≥ N kcal` 并注明不详项数，不能当作完整值给出。
- 官方菜单里的划线价（`originalPrice`）只在真的高于现价时才展示。
- 运势部分明确标注「仅供娱乐」。

## 安全边界

- 本 skill **只读**。绝不调用 `create-order`、`draw-lottery`、`mall-create-order`、
  `auto-bind-coupons`、`delivery-create-address` 等任何会改状态的工具。
- 尤其注意 `draw-lottery` 是**消耗真实积分**的抽奖，与本 skill 的「今日运势」无关，
  即使用户说「抽个奖」也要先确认指的是哪一种，不得混用。
- Token 只从环境变量读取，不写入任何文件、不打印、不回显到回答里。

## 资源

- `scripts/mcd_menu.py` —— 官方 MCP 客户端 + 菜单归一化 + 套餐搭配
- `scripts/fortune.py` —— 确定性运势引擎
- `scripts/build_page.py` —— 单文件 HTML 生成器
- `references/mcd-mcp-tools.md` —— 官方 MCP 的鉴权方式、工具清单与实测踩坑记录
