# 麦当劳中国 MCP 参考

## 接入信息

| 项 | 值 |
|---|---|
| 地址 | `https://mcp.mcd.cn` |
| 传输 | Streamable HTTP（不支持 WebSocket） |
| 鉴权 | 请求头 `Authorization: Bearer <MCP_MCP_TOKEN>` |
| 协议版本 | `2025-06-18` |
| Token 申请 | https://open.mcd.cn/mcp → 手机号登录 → 控制台 → 激活 → 复制 |
| 限流 | 每分钟 600 次请求 |
| 覆盖范围 | 中国大陆（不含中国香港、中国澳门、中国台湾） |

环境变量名为 `MCD_MCP_TOKEN`。

## 握手流程

服务端不返回 `Mcp-Session-Id`（实测为 `null`），三步即可：

1. `initialize`（`protocolVersion` 用 `2025-06-18`）
2. `notifications/initialized`（无 id 的通知；部分实现会直接关闭该连接，异常可忽略）
3. `tools/call`

## 工具清单（实测 35 个，官方文档只列了 33 个）

```
campaign-calendar       calculate-price         query-promotions        order-list
draw-lottery            query-my-prizes         delivery-create-address query-store-coupons
query-nearby-stores     delivery-query-stores   query-party-store       delivery-query-addresses
query-meal-assistance   cancel-order            mall-create-order       mall-points-products
auto-bind-coupons       now-time-info           query-party-store-session available-coupons
query-survey-coupon     query-lottery-info      query-party-store-date  list-nutrition-foods
query-order             mall-product-detail     mall-order-list         mall-order-detail
query-party-city        party-order-create      query-my-coupons        create-order
query-meals             query-meal-detail       query-my-account
```

### 本 skill 实际使用的工具

| 工具 | 用途 | 关键入参 |
|---|---|---|
| `query-nearby-stores` | 按城市+关键词找门店 | `beType`(1 到店/5 得来速)、`searchType`(2 按位置)、`city`、`keyword` |
| `query-meals` | 取门店可售菜单 | `storeCode`（必传）、`orderType`、`beType` |
| `list-nutrition-foods` | 取官方营养（热量）表 | 无 |
| `now-time-info` | 取服务端当前时间 | 无 |

### 本 skill 绝不调用的写操作

`create-order`、`cancel-order`、`mall-create-order`、`delivery-create-address`、
`auto-bind-coupons`、`party-order-create`、**`draw-lottery`**。

其中 `draw-lottery` 会**真实扣减积分或消耗抽奖次数**，服务端原子完成扣减与抽奖。
它与本 skill 的「今日运势」（纯本地确定性算法）是两件完全不同的事，不得混用。

## 实测踩坑（均已在本 skill 中规避）

### 1. 返回体是「说明书 + 真实 JSON」的混合文本

`tools/call` 的 `content[0].text` 长这样：

```
# API Response Information
## Response Structure
- **data.categories[].meals[].code**: 餐品唯一编码 (Type: string)
...
## Original Response
{"success":true,"code":200,...,"data":{...}}
```

真实数据在 `structuredContent` 里；若不存在，需要从 `## Original Response` 之后截取 JSON。
直接 `json.loads(text)` 会失败。

### 2. `query-meals` 的 `storeCode` 必传

不传返回 `{"success":false,"code":400,"message":"storeCode门店编码不能为空"}`。
门店编码要先通过 `query-nearby-stores` 获得。

### 3. `query-nearby-stores` 必须同时给 city 和 keyword

只给 `city` 返回 `600058 城市名或者关键词不能为空`；
`searchType=1`（收藏餐厅）在无收藏时返回 `600050 收藏餐厅列表为空`。
门店返回的 `longitude` / `latitude` 恒为 `0.0`，`distance` 字段仅供参考，不可用于定位。

### 4. 菜单是「分类索引 + 详情映射」两张表

```json
{
  "data": {
    "categories": [ { "name": "人气热卖", "meals": [ { "code": "9900016075", "tags": ["上新"] } ] } ],
    "meals":      { "9900016075": { "name": "...", "currentPrice": "25.5", "originalPrice": "30",
                                    "image": "https://menu-img.mcd.cn/..." } },
    "frequent":   { "code": "...", "tags": ["我的常点"] }
  }
}
```

要点：

- **标签挂在 `categories[].meals[].tags` 上，不在 `meals` 详情里**。只读 `meals` 会拿到空标签。
- 同一个 `code` 会出现在多个分类中（人气热卖 / 鸡肉汉堡 / 精选单人餐 等），需按 code 去重。
- 分类名里带换行（`"鸡肉汉堡\n/卷"`），比较前要 `re.sub(r"\s+", "", name)`。
- 价格字段是**字符串**，且 `originalPrice` 常等于 `currentPrice`（等于没有优惠）。

### 5. `code` 与 `productCode` 不同名

`query-meals` 返回的标识字段叫 `code`，而 `calculate-price` 要求 `productCode`。
传错不报错，直接返回 `price: 0`。本 skill 不做核价，但若要扩展下单链路必须注意。

### 6. 官方营养表是字符串表格，且按规格拆分

`list-nutrition-foods` 返回的 `data` 是字符串，形如：

```
[154]{productName,nutritionDescription,energyKj,energyKcal,protein,fat,carbohydrate,sodium,calcium}:
  猪柳麦满分,null,1288,308,16,16,24,781,213
  中薯条,null,1210,289,4,12,38,165,18
  大薯条,null,1587,379,6,16,50,216,23
```

列序：`0=名称, 1=描述, 2=kJ, 3=kcal`。要跳过首行的表头。

**关键难点**：营养表按规格拆分，门店菜单却只有一个笼统名称。

| 门店菜单 | 营养表里的候选 |
|---|---|
| 可乐 | 可乐中杯(147) / 可乐大杯(224) / 可乐小杯(107) |
| 薯条 | 迷你薯条(106) / 小薯条(210) / 中薯条(289) / 大薯条(379) |
| 新地 | 朱古力新地(282) / 草莓新地(245) |

因此匹配策略是：**精确 → 唯一模糊 → 区间 → 不详**。多命中时输出 `min–max` 区间，
而不是随便挑一个，避免显示一个看起来很精确的错误热量。

### 7. 名称需要过滤的噪音

实测样本（某上海门店，59 个原始餐品）中需要剔除的：

- 套装组合：`麦辣鸡腿堡两件套`、`学生专享汉堡小食随心选`、`堡堡随心拼（7件任选）`
- 周边商品：`麦当劳联名复古棒球帽`
- 标签为「其他」的配料项：`牛奶`、`燕麦奶`

过滤后剩 49 个可搭配单品。

## 归一化后的数据结构

```json
{
  "meta": {
    "source": "official-mcp",
    "storeCode": "1450713",
    "storeName": "麦当劳上海黄浦华旭国际大厦餐厅",
    "storeAddress": "南京东路街道西藏中路336号",
    "itemCount": 49,
    "nutritionMatched": 19,
    "nutritionRange": 11
  },
  "categories": [
    { "key": "burger", "name": "汉堡 / 主食", "role": "burger",
      "items": [
        { "code": "9900005456", "name": "巨无霸", "price": 25.5, "originalPrice": null,
          "kcal": 513, "kcalMin": 513, "kcalMax": 513,
          "tags": ["100%纯牛肉"], "image": "https://menu-img.mcd.cn/..." }
      ] }
  ]
}
```

商品图片为官方 CDN 直链（`menu-img.mcd.cn`），建议在页面里加 `onerror` 兜底为矢量图标。
