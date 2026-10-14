# 🍔 今天吃什么 · 麦门运势

> 摇一支签，让金拱门替你决定这一顿。

一个基于**麦当劳中国官方 MCP** 开发的 Skill：把「今天吃什么」这个世纪难题，变成一次有仪式感的抽签——先摇今日运势，再随机搭配一整套麦当劳套餐。价格、热量、商品图全部来自官方实时数据。

🎮 **[▶ 在线体验（打开即玩，无需安装）](https://yfw17562-cyber.github.io/mcd-what-to-eat/)**

🏆 2026 麦当劳程序员创意开发大赛参赛作品（使用 WorkBuddy 开发）

---

## ✨ 功能特性

- **今日运势**：6 级签等，各配专属 emoji——🎉 大吉 / ✨ 吉 / 😊 中吉 / 🍀 小吉 / 🌤️ 末吉 / 😐 平；附签诗、宜/忌、幸运数字、幸运色、幸运时段
- **确定性抽签**：种子 = `SHA256(日期 + 签主 + 重抽序号)`。同一天同一个人永远抽到同一支签，不会刷一次变一次；想换签点「再抽一签」
- **真实菜单**：拉取指定门店的官方实时菜单——餐品名、现价、划线价、官方商品图
- **热量诚实**：官方营养表按规格拆分（可乐中杯 147 / 大杯 224 / 小杯 107），多命中时输出**区间**而不是猜一个数；总热量只要有一项不详就标 `≥ N kcal`
- **像素风视觉**：星露谷（Stardew Valley）风格界面，金拱门像素 Logo + 漂浮的汉堡/冰淇淋像素装饰，全部内联 SVG 绘制，无外部图片依赖
- **单文件交付**：最终产物是一个零依赖 HTML，可直接发给别人打开
- **优雅降级**：没有 Token 或断网时自动切到内置参考菜单，页面底部标注数据来源

## 🚀 快速开始

### 第 1 步：申请麦当劳 MCP Token（免费）

前往 <https://open.mcd.cn/mcp> → 手机号登录 → 右上角「控制台」→「激活」→ 复制 Token。

### 第 2 步：配置 MCP 连接器

参照仓库内的 [`mcp-config.example.json`](mcp-config.example.json)，把 `${MCD_MCP_TOKEN}` 换成你的真实 Token：

```json
{
  "mcpServers": {
    "mcd-mcp": {
      "type": "streamablehttp",
      "url": "https://mcp.mcd.cn",
      "headers": { "Authorization": "Bearer ${MCD_MCP_TOKEN}" }
    }
  }
}
```

在 WorkBuddy 中的路径：左侧边栏【连接器】→ 右上角【自定义连接器】→【配置 MCP】→ 粘贴上述配置 → 保存并启用。

其他客户端（Cursor / Cherry Studio / Trae / VSCode）配置方式相同。

### 第 3 步：安装为 WorkBuddy Skill

```bash
# 把 skill/ 目录复制到用户级技能目录
cp -r skill ~/.workbuddy/skills/mcd-what-to-eat
```

重启 WorkBuddy，然后直接说 **「今天吃什么」** 即可触发；也可以输入 `/mcd-what-to-eat` 激活。

### 第 4 步（可选）：不用 Agent，直接命令行跑

```bash
export MCD_MCP_TOKEN="你的Token"

# 生成交互式页面（星露谷像素风）
python3 scripts/build_page.py -o 麦门运势.html --city 上海 --keyword 人民广场

# 只看运势
python3 scripts/fortune.py --date 2026-10-14 --signer 小林 --pretty

# 找门店 / 看菜单 / 试搭配
python3 scripts/mcd_menu.py stores --city 上海 --keyword 人民广场
python3 scripts/mcd_menu.py menu   --city 上海 --keyword 人民广场
python3 scripts/mcd_menu.py pick   --city 上海 --keyword 人民广场 --prefer spicy --budget 40
```

打开生成的 `麦门运势.html`：选口味（随便 / 吃辣 / 不吃辣 / 清淡点）、填预算和签主名，点「今天吃什么」走摇签动画，即出运势 + 套餐两栏结果。

**无 Token 也能跑**：`python3 scripts/build_page.py -o demo.html`，会自动降级到内置参考菜单并在页面标注。

## 💻 使用示例

```
$ python3 scripts/fortune.py --date 2026-10-14 --signer 小林 --pretty

【2026-10-14 · 小林】
  签等：🎉 大吉  （今天点单不用看价格）
  宜：加个鸡腿、把下午茶提前半小时
  忌：空腹点餐
  幸运数字：42    幸运色：芝士黄
  幸运时段：17:30 - 19:30（晚饭档）

    金拱门下喜相逢，巨无霸里藏欢容。
    薯条酥脆财气旺，一杯可乐万事通。
```

```
$ python3 scripts/mcd_menu.py pick --city 上海 --keyword 人民广场 --prefer spicy --budget 40

  门店: 麦当劳上海黄浦华旭国际大厦餐厅 (1450713)
   - 麦辣鸡腿汉堡      ¥22.0   | kcal=516
   - 麦辣鸡翅（2块）    ¥13.5   | kcal=290
   - 可口可乐           ¥10.0   | kcal=147–224
   合计 ¥45.5  →  超预算，自动去掉最便宜一项
   合计 ¥35.5  | 约 953 kcal
```

## 👥 目标用户

| 人群 | 用法 |
|---|---|
| **选择困难症** | 每天中午不知道吃什么的人，一句话获得有仪式感的答案 |
| **麦门信徒** | 想要抽签仪式感和「麦门人格」氛围的麦当劳爱好者 |
| **MCP 开发者** | 想了解「商业 MCP 数据 → 有趣应用」怎么落地的参考实现（含 7 个实测踩坑） |
| **Skill 开发者** | 想了解 Skill 结构（SKILL.md + scripts + references）如何组织的模板 |

## 📁 项目结构

```
mcd-what-to-eat/
├── README.md                  # 本文件
├── CONTEST_DECLARATION.md     # 参赛声明（官方原样文件，内容不可改动）
├── MCP_INTEGRATION.md         # MCP 集成说明：Server / Tool / 调用流程 / 业务价值
├── mcp-config.example.json    # 脱敏 MCP 配置示例（仅环境变量占位符）
├── workbuddy.md               # 使用 WorkBuddy 开发的对话上下文记录
├── skill/
│   ├── SKILL.md               # Skill 入口：触发条件、五步工作流、安全边界
│   └── references/
│       └── mcd-mcp-tools.md   # 麦当劳 MCP 参考：35 个工具清单 + 实测踩坑
├── scripts/
│   ├── mcd_menu.py            # 官方 MCP 客户端 + 菜单归一化 + 套餐搭配
│   ├── fortune.py             # 确定性运势引擎
│   └── build_page.py          # 单文件交互式 HTML 生成器
└── examples/
    └── 今天吃什么-麦门运势.html   # 真实数据生成的效果示例（用官方门店数据跑出）
```

## 🔒 数据与隐私

- Token **只**通过环境变量 `MCD_MCP_TOKEN` 传入，仓库内不含任何真实凭证
- 只调用 4 个**只读**工具（`query-nearby-stores`、`query-meals`、`list-nutrition-foods`、`now-time-info`）
- **绝不调用** `create-order`、`cancel-order`、`auto-bind-coupons`、`draw-lottery` 等写操作——尤其 `draw-lottery` 会真实扣减积分，与页面上的「今日运势」（纯本地算法）毫无关系
- 生成的 HTML 单文件已校验不含 Token

## ⚠️ 免责声明

本项目为独立开发作品，**非麦当劳官方产品**。「麦当劳」「金拱门」为麦当劳公司商标。运势结果仅供娱乐，不构成医疗、营养或其他专业建议；餐品信息、价格及供应状态以麦当劳官方渠道的实时结果为准。

## 📄 许可

MIT
