# MCP 集成说明

本文件说明项目实际使用的麦当劳 MCP Server、工具、调用流程与业务价值。所有结论均来自**真实调用实测**，非文档推断。

## 1. MCP Server

| 项 | 值 |
|---|---|
| 名称 | 麦当劳中国官方 MCP Server |
| 地址 | `https://mcp.mcd.cn` |
| 传输 | Streamable HTTP（不支持 WebSocket） |
| 鉴权 | 请求头 `Authorization: Bearer <MCD_MCP_TOKEN>` |
| 协议版本 | `2025-06-18` |
| Token 申请 | https://open.mcd.cn/mcp → 手机号登录 → 控制台 → 激活 → 复制（免费） |
| 限流 | 每分钟 600 次请求 |
| 覆盖范围 | 中国大陆（不含中国香港、中国澳门、中国台湾） |

环境变量名：`MCD_MCP_TOKEN`（仓库内不写入任何真实值，参见 `mcp-config.example.json`）。

## 2. 实际使用的 Tool（4 个，全部为只读）

服务端实际返回 **35 个工具**（官方公开文档只列了 33 个）。本项目只调用其中 4 个只读工具：

| Tool | 用途 | 关键入参 | 在代码中的位置 |
|---|---|---|---|
| `query-nearby-stores` | 按城市 + 关键词定位门店，取得 `storeCode` | `city`、`keyword`、`beType`、`searchType` | `scripts/mcd_menu.py` → `find_stores()` |
| `query-meals` | 取门店可售菜单（分类索引 + 餐品详情 + 官方图 + 现价/划线价） | `storeCode`（**必传**）、`orderType`、`beType` | `scripts/mcd_menu.py` → `fetch_meals()` |
| `list-nutrition-foods` | 取官方营养（热量）表 | 无 | `scripts/mcd_menu.py` → `fetch_nutrition()` |
| `now-time-info` | 取服务端当前时间，用于运势日期对齐 | 无 | `scripts/mcd_menu.py` → `server_now()` |

## 3. 明确不调用的 Tool

下列工具会改变用户账户状态或产生真实资金/积分消耗，**本项目一律不调用**：

`create-order`、`cancel-order`、`mall-create-order`、`party-order-create`、
`delivery-create-address`、`auto-bind-coupons`、**`draw-lottery`**。

特别说明：`draw-lottery` 会在服务端原子完成抽奖并**真实扣减积分/消耗抽奖次数**。它与本项目「今日运势」的**纯本地确定性算法**是两件完全不同的事，二者不得混用——页面上的摇签动画不产生任何远程调用。

## 4. 调用流程

```
┌──────────────────────────────────────────────────────────────┐
│  ① initialize          protocolVersion = 2025-06-18          │
│  ② notifications/initialized    （无 id 通知，可忽略异常）      │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│  ③ tools/call  query-nearby-stores(city, keyword)            │
│         → storeCode                                            │
│  ④ tools/call  query-meals(storeCode)                        │
│         → 分类 + 餐品 + 价格 + 官方图                            │
│  ⑤ tools/call  list-nutrition-foods()                        │
│         → 官方营养表（kcal）                                    │
│  ⑥ tools/call  now-time-info()   （可选，对齐日期）             │
└──────────────────────────────────────────────────────────────┘
                          ↓
        本地归一化 → 分类清洗 → 套餐搭配 → 运势计算 → HTML
```

服务端不返回 `Mcp-Session-Id`（实测为 `null`），三步握手后直接 `tools/call`。

## 5. 业务价值

1. **把选择困难变成仪式感**：用户每天最常问的一句话是「今天吃什么」。项目把随机选择包装成抽签，给出情绪价值（签等、签诗、宜忌），再落到一个具体、可执行的麦当劳方案。
2. **数据全部来自官方实时源**：餐品名称、现价、划线价、商品图、热量均来自 MCP，不内置硬编码价格。用户看到的 ¥ 和 kcal 是「这一家店此刻」的真实值。
3. **热量显示诚实**：官方营养表按规格拆分（如可乐分中/大/小杯），而门店菜单只有一个笼统名。项目采用「精确 → 唯一模糊 → 区间 → 不详」四级策略，宁可显示 `107–224 kcal` 或 `≥ N kcal`，也不猜一个看似精确的错误值。
4. **零依赖交付**：最终产物是一个单文件 HTML，菜单数据已内嵌，无需后端、无需数据库，可直接发给别人打开。
5. **给 MCP 开发者一份可复用的踩坑记录**：返回体结构、必传参数、标签位置、`code` 与 `productCode` 不同名等 7 个坑，均已在代码中规避并写入 `skill/references/mcd-mcp-tools.md`。

## 6. 实测踩坑（已在代码中规避）

| # | 现象 | 处理 |
|---|---|---|
| 1 | `tools/call` 返回的是「字段说明书 + `## Original Response` + 真实 JSON」的混合文本，直接 `json.loads` 失败 | 优先取 `structuredContent`；否则从 `## Original Response` 之后截取 JSON |
| 2 | `query-meals` 不传 `storeCode` 报 `storeCode门店编码不能为空` | 先用 `query-nearby-stores` 取门店编码 |
| 3 | `query-nearby-stores` 只给城市报 `600058`；必须同时给 `city` + `keyword` | 两个参数都必传；`searchType=1` 无收藏时返回 `600050` |
| 4 | 门店返回的经纬度恒为 `0.0`，`distance` 不可用于定位 | 只把门店当"选一个店"，不做距离计算 |
| 5 | 餐品标签挂在 `categories[].meals[].tags`，不在 `meals` 详情里 | 从分类索引读标签，按 code 去重合并 |
| 6 | 分类名含换行（`"鸡肉汉堡\n/卷"`） | 比较前 `re.sub(r"\s+", "", name)` |
| 7 | 营养表按规格拆分（可乐 107/147/224），门店菜单只有一个名字 | 多命中时输出热量区间，总热量标 `≥ N kcal` 并注明几项不详 |
| 8 | `query-meals` 的标识字段叫 `code`，而 `calculate-price` 要求 `productCode`，传错不报错但返回 `price: 0` | 本项目不做核价；扩展下单链路时需注意字段转换 |

## 7. 数据降级策略

未配置 `MCD_MCP_TOKEN` 或网络不可用时，项目自动降级到内置参考菜单（页面底部会标注数据来源与降级原因），保证功能可用、结果不误导。降级数据不含真实价格承诺，仅作演示。

## 8. 安全边界

- Token 只通过环境变量 `MCD_MCP_TOKEN` 传入，不写入仓库、不写入生成产物、不打入安装包。
- 生成的 HTML 单文件已通过检查，不含任何 Token 或凭证。
- 只调用 4 个只读工具；不调用任何下单、领券、抽奖等写操作。
