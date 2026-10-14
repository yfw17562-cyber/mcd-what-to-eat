#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麦当劳菜单适配层 —— 对接麦当劳中国官方 MCP Server。

官方服务：https://mcp.mcd.cn   （Streamable HTTP + Bearer Token）
Token 申请：https://open.mcd.cn/mcp  → 手机号登录 → 控制台 → 激活 → 复制
本脚本读取环境变量 MCD_MCP_TOKEN。

数据来源优先级：
  1. 官方 MCP：query-nearby-stores → query-meals → 关联 list-nutrition-foods 热量
  2. 内置离线菜单（fallback）：无 Token 或调用失败时自动降级，保证链路可用

用法：
  python mcd_menu.py stores --city 上海 --keyword 人民广场
  python mcd_menu.py menu --city 上海 --keyword 人民广场
  python mcd_menu.py menu --store-code 1450048
  python mcd_menu.py menu --source builtin
  python mcd_menu.py pick --seed 12345 --store-code 1450048 --prefer spicy --budget 45

实测踩坑记录（已在本文件内规避）：
  - query-meals 的 storeCode 为必传；不传返回 code=400。
  - query-nearby-stores 必须同时给 city + keyword，只给城市会返回 600058。
  - MCP 返回是「说明书文本 + ## Original Response」的混合体，真实 JSON 在
    structuredContent 或 Original Response 段里，需要二次抽取。
  - 门店接口不返回可用经纬度（恒为 0.0），距离字段仅供参考。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

MCP_ENDPOINT = "https://mcp.mcd.cn"
MCP_PROTOCOL_VERSION = "2025-06-18"
TOKEN_ENV = "MCD_MCP_TOKEN"


# --------------------------------------------------------------------------
# 内置离线菜单（参考价，单位：元；热量为约值，单位 kcal）
# --------------------------------------------------------------------------
BUILTIN_MENU = {
    "meta": {
        "source": "builtin-fallback",
        "sourceLabel": "内置参考菜单",
        "currency": "CNY",
        "note": "价格为参考价、热量为约值，实际以门店为准。",
    },
    "categories": [
        {
            "key": "burger", "name": "汉堡 / 主食", "role": "burger",
            "items": [
                {"code": "9900005456", "name": "巨无霸", "price": 25.5, "kcal": 500, "tags": ["牛肉", "经典"]},
                {"code": "9900005457", "name": "板烧鸡腿堡", "price": 23.5, "kcal": 430, "tags": ["鸡肉", "不辣", "招牌"]},
                {"code": "9900005458", "name": "麦辣鸡腿堡", "price": 21.5, "kcal": 480, "tags": ["鸡肉", "辣"]},
                {"code": "9900005459", "name": "双层吉士汉堡", "price": 22.0, "kcal": 429, "tags": ["牛肉", "芝士"]},
                {"code": "9900005460", "name": "麦香鱼", "price": 17.5, "kcal": 340, "tags": ["鱼", "不辣", "轻食"]},
                {"code": "9900005461", "name": "麦香鸡", "price": 17.5, "kcal": 369, "tags": ["鸡肉", "不辣"]},
                {"code": "9900005463", "name": "吉士汉堡包", "price": 12.5, "kcal": 294, "tags": ["牛肉", "芝士", "小份"]},
            ],
        },
        {
            "key": "side", "name": "小食", "role": "side",
            "items": [
                {"code": "9900005501", "name": "大薯条", "price": 12.0, "kcal": 379, "tags": ["经典"]},
                {"code": "9900005502", "name": "中薯条", "price": 10.5, "kcal": 289, "tags": ["经典"]},
                {"code": "9900005503", "name": "麦乐鸡 5 块", "price": 12.5, "kcal": 213, "tags": ["鸡肉"]},
                {"code": "9900005504", "name": "小杯玉米杯", "price": 9.0, "kcal": 53, "tags": ["轻食", "不辣"]},
                {"code": "9900005507", "name": "麦辣鸡翅 2 块", "price": 12.0, "kcal": 224, "tags": ["鸡肉", "辣"]},
            ],
        },
        {
            "key": "drink", "name": "饮品", "role": "drink",
            "items": [
                {"code": "9900005601", "name": "可口可乐(中)", "price": 9.0, "kcal": 150, "tags": ["碳酸"]},
                {"code": "9900005602", "name": "零度可乐(中)", "price": 9.5, "kcal": 1, "tags": ["碳酸", "无糖"]},
                {"code": "9900005603", "name": "雪碧(中)", "price": 9.0, "kcal": 145, "tags": ["碳酸"]},
                {"code": "9900005604", "name": "冰红茶(中)", "price": 9.0, "kcal": 130, "tags": ["茶"]},
                {"code": "9900005605", "name": "橙汁", "price": 12.0, "kcal": 110, "tags": ["果汁"]},
                {"code": "9900005606", "name": "美式咖啡", "price": 15.0, "kcal": 5, "tags": ["咖啡", "提神", "无糖"]},
                {"code": "9900005607", "name": "拿铁", "price": 17.0, "kcal": 120, "tags": ["咖啡"]},
            ],
        },
        {
            "key": "dessert", "name": "甜品", "role": "dessert",
            "items": [
                {"code": "9900005701", "name": "圆筒冰淇淋", "price": 5.0, "kcal": 93, "tags": ["冰"]},
                {"code": "9900005702", "name": "草莓新地", "price": 10.0, "kcal": 245, "tags": ["冰", "甜"]},
                {"code": "9900005703", "name": "奥利奥麦旋风", "price": 13.0, "kcal": 266, "tags": ["冰", "甜"]},
                {"code": "9900005705", "name": "香芋派", "price": 8.0, "kcal": 232, "tags": ["甜"]},
                {"code": "9900005706", "name": "菠萝派", "price": 8.0, "kcal": 221, "tags": ["甜"]},
            ],
        },
    ],
}


# --------------------------------------------------------------------------
# MCP 传输层
# --------------------------------------------------------------------------
class McpError(RuntimeError):
    pass


def get_token() -> str:
    return os.environ.get(TOKEN_ENV, "").strip()


def _post(payload: dict, token: str, session_id: str | None = None):
    """发送一次 JSON-RPC 请求，返回 (消息, session_id)。"""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Authorization": f"Bearer {token}",
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    req = urllib.request.Request(
        MCP_ENDPOINT, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        sid = resp.headers.get("Mcp-Session-Id")
    if not raw.strip():
        return None, sid
    msg = None
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            chunk = line[5:].strip()
            if chunk and chunk != "[DONE]":
                try:
                    msg = json.loads(chunk)
                except json.JSONDecodeError:
                    continue
    if msg is None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise McpError(f"无法解析 MCP 响应: {raw[:200]}") from exc
    return msg, sid


class McpClient:
    """一次会话内复用握手结果。"""

    def __init__(self, token: str):
        self.token = token
        self.sid: str | None = None
        self._next_id = 100

    def connect(self):
        msg, sid = _post(
            {
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "mcd-what-to-eat", "version": "1.1.0"},
                },
            },
            self.token,
        )
        if msg and "error" in msg:
            raise McpError(f"initialize 失败: {msg['error']}")
        self.sid = sid
        try:
            _post({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}, self.token, self.sid)
        except Exception:
            pass  # 部分实现直接关闭该连接，不影响后续
        return msg

    def call(self, tool: str, arguments: dict | None = None) -> dict:
        if self.sid is None:
            self.connect()
        self._next_id += 1
        msg, _ = _post(
            {
                "jsonrpc": "2.0", "id": self._next_id, "method": "tools/call",
                "params": {"name": tool, "arguments": arguments or {}},
            },
            self.token, self.sid,
        )
        if msg is None:
            raise McpError(f"{tool} 返回空响应")
        if "error" in msg:
            raise McpError(f"{tool} 调用失败: {msg['error']}")
        result = msg.get("result", {})
        if result.get("structuredContent") is not None:
            return result["structuredContent"]
        for block in result.get("content", []):
            if block.get("type") == "text":
                return _extract_payload(block["text"])
        return result

    def tools(self) -> list[dict]:
        if self.sid is None:
            self.connect()
        self._next_id += 1
        msg, _ = _post(
            {"jsonrpc": "2.0", "id": self._next_id, "method": "tools/list", "params": {}},
            self.token, self.sid,
        )
        return msg["result"]["tools"]


def _extract_payload(text: str) -> dict:
    """MCP 文本块 = 字段说明书 + '## Original Response' + 真实 JSON。"""
    marker = "## Original Response"
    idx = text.find(marker)
    if idx != -1:
        tail = text[idx + len(marker):].strip()
        start = tail.find("{")
        if start != -1:
            try:
                return json.loads(tail[start:].strip())
            except json.JSONDecodeError:
                pass
    start = text.find("{")
    if start != -1:
        try:
            return json.loads(text[start:])
        except json.JSONDecodeError:
            pass
    return {"raw": text}


# --------------------------------------------------------------------------
# 业务接口
# --------------------------------------------------------------------------
def query_nearby_stores(client: McpClient, city: str, keyword: str, be_type: int = 1) -> list[dict]:
    res = client.call("query-nearby-stores", {"beType": be_type, "searchType": 2, "city": city, "keyword": keyword})
    if not res.get("success"):
        raise McpError(f"门店查询失败: {res.get('message')} (code={res.get('code')})")
    return res.get("data") or []


NUTRITION_PREFIX = "麦当劳"
KJ_PER_KCAL = 4.184


def list_nutrition_foods(client: McpClient) -> dict[str, int]:
    """返回 {餐品名: kcal}。官方以表格字符串下发，需要按行拆。"""
    res = client.call("list-nutrition-foods")
    blob = res.get("data") if isinstance(res, dict) else None
    if not isinstance(blob, str):
        return {}
    table: dict[str, int] = {}
    for line in blob.splitlines()[1:]:
        line = line.strip().rstrip(",")
        if not line or line.startswith("#"):
            continue
        cols = [c.strip() for c in line.split(",")]
        if len(cols) < 4:
            continue
        name, kcal_raw = cols[0], cols[3]
        try:
            kcal = float(kcal_raw)
        except ValueError:
            continue
        if kcal > 0:
            table[name] = int(round(kcal))
    return table


def _norm_name(s: str) -> str:
    return re.sub(r"[\s()（）【】\[\]·・\-—－/、,，.。™®]", "", s or "").replace(NUTRITION_PREFIX, "")


def match_kcal(name: str, table: dict[str, int]) -> dict:
    """匹配官方营养数据，返回 {"kcal", "kcalMin", "kcalMax"}。

    官方营养表按规格拆分（可乐中杯 / 可乐大杯 / 可乐小杯），而门店菜单里
    往往只有一个笼统的「可乐」。策略：
      - 精确命中           → 给确定值
      - 唯一模糊命中       → 给确定值
      - 多个模糊命中       → 给区间（min~max），绝不猜一个看起来精确的错数
    """
    if not table:
        return {"kcal": None, "kcalMin": None, "kcalMax": None}
    n = _norm_name(name)
    if not n:
        return {"kcal": None, "kcalMin": None, "kcalMax": None}

    norm_table = {_norm_name(k): v for k, v in table.items()}
    if n in norm_table:
        return {"kcal": norm_table[n], "kcalMin": norm_table[n], "kcalMax": norm_table[n]}

    hits = [v for c, v in norm_table.items() if n in c]
    if len(hits) == 1:
        return {"kcal": hits[0], "kcalMin": hits[0], "kcalMax": hits[0]}
    if len(hits) > 1:
        return {"kcal": None, "kcalMin": min(hits), "kcalMax": max(hits)}
    return {"kcal": None, "kcalMin": None, "kcalMax": None}


# 分类规则（按顺序匹配，先命中先归类）
NAME_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("burger", ("堡", "卷", "派斯", "三明治")),
    ("drink", ("可乐", "雪碧", "芬达", "咖啡", "拿铁", "美式", "卡布", "摩卡", "橙", "柠檬",
               "茶", "奶昔", "冰沙", "气泡", "矿泉水", "纯水", "果汁", "麦炫酷", "奶茶", "豆浆")),
    ("dessert", ("冰淇淋", "新地", "麦旋风", "圆筒", "甜筒", "派", "蛋糕", "布丁", "麦芬",
                 "可颂", "甜甜圈", "泡芙", "挞", "圣代")),
    ("side", ("薯条", "薯饼", "鸡块", "麦乐鸡", "鸡翅", "鸡腿", "玉米", "沙拉", "香肠",
              "鸡排", "鸡柳", "脆薯", "洋葱圈", "鸡扒")),
]

# 套餐 / 组合 / 非单品，不参与自动搭配
EXCLUDE_KEYWORDS = (
    "套餐", "件套", "套装", "单品", "精选", "随心配", "随心选", "任选", "1+1", "组合",
    "拼盘", "桶", "乐园", "卡", "券", "礼盒", "玩具", "图书", "联名", "周边", "棒球帽",
    "外送费", "配送费", "包装费", "早餐", "儿童", "学生专享",
)

# 命中这些标签的商品不参与搭配（多为配料 / 加购项，不是一份正经吃的）
EXCLUDE_TAGS = ("其他",)

ROLE_LABEL = {"burger": "汉堡 / 主食", "side": "小食", "drink": "饮品", "dessert": "甜品"}


def classify(name: str) -> str | None:
    for role, kws in NAME_RULES:
        if any(k in name for k in kws):
            return role
    return None


def normalize_meals(raw: dict, nutrition: dict[str, int]) -> dict:
    if not raw.get("success"):
        raise McpError(f"菜单查询失败: {raw.get('message')} (code={raw.get('code')})")

    data = raw.get("data") or {}
    meals_map: dict = data.get("meals") or {}
    categories = data.get("categories") or []

    # code -> 分类名 / 标签（标签挂在分类条目上，不在 meals 详情映射里）
    cat_of: dict[str, list[str]] = {}
    tags_of: dict[str, list[str]] = {}
    ordered_codes: list[str] = []
    for cat in categories:
        cname = re.sub(r"\s+", "", cat.get("name") or "")
        for m in cat.get("meals") or []:
            code = str(m.get("code") or "")
            if not code:
                continue
            cat_of.setdefault(code, []).append(cname)
            for t in m.get("tags") or []:
                if t and t not in tags_of.setdefault(code, []):
                    tags_of[code].append(t)
            if code not in ordered_codes:
                ordered_codes.append(code)

    buckets: dict[str, list[dict]] = {"burger": [], "side": [], "drink": [], "dessert": []}
    seen: set[str] = set()

    for code in ordered_codes:
        if code in seen:
            continue
        tags = tags_of.get(code, [])
        if any(t in EXCLUDE_TAGS for t in tags):
            continue

        info = meals_map.get(code) or {}
        name = (info.get("name") or "").strip()
        if not name or any(k in name for k in EXCLUDE_KEYWORDS):
            continue

        role = classify(name)
        if role is None:
            joined = "".join(cat_of.get(code, []))
            if "汉堡" in joined or "牛鱼肉堡" in joined or "厚牛堡" in joined:
                role = "burger"
            elif "咖啡" in joined or "饮品" in joined:
                role = "drink"
            elif "小食甜品" in joined:
                role = "dessert" if ("派" in name or "冰" in name) else "side"
            else:
                continue
        if role is None:
            continue

        try:
            price = float(info.get("currentPrice") or 0)
        except (TypeError, ValueError):
            price = 0.0
        if price <= 0:
            continue

        try:
            original = float(info.get("originalPrice") or 0)
        except (TypeError, ValueError):
            original = 0.0

        seen.add(code)
        kcal = match_kcal(name, nutrition)
        item = {
            "code": code,
            "name": name,
            "price": round(price, 2),
            "originalPrice": round(original, 2) if original > price else None,
            "kcal": kcal["kcal"],
            "kcalMin": kcal["kcalMin"],
            "kcalMax": kcal["kcalMax"],
            "tags": [t for t in tags if t not in ("单品",)],
            "image": info.get("image") or "",
        }
        buckets[role].append(item)

    out_cats = []
    for role in ("burger", "side", "drink", "dessert"):
        items = buckets[role]
        if items:
            items.sort(key=lambda i: i["price"])
            out_cats.append({"key": role, "name": ROLE_LABEL[role], "role": role, "items": items})

    if not out_cats:
        raise McpError("官方菜单中未解析到可搭配的单品")

    return {
        "meta": {
            "source": "official-mcp",
            "sourceLabel": "麦当劳官方 MCP 实时菜单",
            "endpoint": MCP_ENDPOINT,
            "currency": "CNY",
            "note": "数据来自麦当劳中国官方 MCP 服务 (mcp.mcd.cn)，价格与库存以门店实时状态为准。",
        },
        "categories": out_cats,
    }


# --------------------------------------------------------------------------
# 对外入口
# --------------------------------------------------------------------------
def _ensure_fields(menu: dict) -> dict:
    """补齐内置菜单缺失的字段，保证与官方数据的形状一致。"""
    for cat in menu.get("categories", []):
        for item in cat.get("items", []):
            item.setdefault("kcalMin", item.get("kcal"))
            item.setdefault("kcalMax", item.get("kcal"))
            item.setdefault("originalPrice", None)
            item.setdefault("image", "")
            item.setdefault("tags", [])
    return menu


def load_menu(
    store_code: str | None = None,
    city: str = "上海",
    keyword: str = "人民广场",
    force_builtin: bool = False,
) -> dict:
    token = get_token()
    if token and not force_builtin:
        try:
            client = McpClient(token)
            store_name, store_addr = "", ""
            if not store_code:
                stores = query_nearby_stores(client, city, keyword)
                if not stores:
                    raise McpError(f"{city} / {keyword} 未找到门店")
                store_code = str(stores[0]["storeCode"])
                store_name = stores[0].get("storeName", "")
                store_addr = stores[0].get("address", "")
            else:
                try:
                    for s in query_nearby_stores(client, city, keyword) or []:
                        if str(s.get("storeCode")) == str(store_code):
                            store_name, store_addr = s.get("storeName", ""), s.get("address", "")
                            break
                except McpError:
                    pass

            raw = client.call("query-meals", {"storeCode": str(store_code), "orderType": 1, "beType": 1})
            try:
                nutrition = list_nutrition_foods(client)
            except (McpError, urllib.error.URLError, OSError):
                nutrition = {}

            menu = normalize_meals(raw, nutrition)
            items = [i for c in menu["categories"] for i in c["items"]]
            menu["meta"].update(
                {
                    "storeCode": str(store_code),
                    "storeName": store_name,
                    "storeAddress": store_addr,
                    "city": city,
                    "itemCount": len(items),
                    "nutritionMatched": sum(1 for i in items if i.get("kcal")),
                    "nutritionRange": sum(1 for i in items if i.get("kcal") is None and i.get("kcalMin")),
                }
            )
            return menu
        except (McpError, urllib.error.URLError, OSError, TimeoutError, KeyError, ValueError) as exc:
            menu = _ensure_fields(json.loads(json.dumps(BUILTIN_MENU)))
            menu["meta"]["fallbackReason"] = f"{type(exc).__name__}: {exc}"
            return menu

    menu = _ensure_fields(json.loads(json.dumps(BUILTIN_MENU)))
    if not token:
        menu["meta"]["fallbackReason"] = f"未设置环境变量 {TOKEN_ENV}"
    return menu


def pick_combo(menu: dict, seed: int, prefer: str = "any", budget: float | None = None) -> dict:
    import random

    rng = random.Random(seed)
    cats = {c["role"]: c["items"] for c in menu["categories"]}

    def pool(role: str) -> list[dict]:
        items = cats.get(role, [])
        if prefer == "spicy":
            hits = [i for i in items if any("辣" in t for t in i.get("tags", [])) or "辣" in i["name"]]
            return hits or items
        if prefer == "mild":
            hits = [i for i in items if "辣" not in i["name"] and not any("辣" in t for t in i.get("tags", []))]
            return hits or items
        if prefer == "light":
            hits = [i for i in items if (i.get("kcalMax") or i.get("kcal") or 9999) <= 350]
            return hits or items
        return items

    chosen: list[tuple[str, dict]] = []          # (role, item)
    for role in ("burger", "side", "drink"):
        p = pool(role)
        if p:
            chosen.append((role, rng.choice(p)))
    if rng.random() < 0.65:
        p = pool("dessert")
        if p:
            chosen.append(("dessert", rng.choice(p)))

    def total_of(pairs):
        return round(sum(i["price"] for _, i in pairs), 2)

    total = total_of(chosen)
    if budget is not None and total > budget and len(chosen) > 2:
        cheapest = min(chosen, key=lambda p: p[1]["price"])
        chosen = [p for p in chosen if p is not cheapest]
        total = total_of(chosen)

    # 热量：确定值直接累加，区间取中值，无法匹配的不计入并标记
    kcal_sum, unknown = 0, 0
    for _, i in chosen:
        if i.get("kcal"):
            kcal_sum += i["kcal"]
        elif i.get("kcalMin") is not None:
            kcal_sum += (i["kcalMin"] + i["kcalMax"]) // 2
        else:
            unknown += 1

    return {
        "seed": seed,
        "prefer": prefer,
        "items": [dict(i, role=r) for r, i in chosen],
        "totalPrice": total,
        "totalKcal": kcal_sum if unknown == 0 else None,
        "totalKcalLowerBound": kcal_sum if unknown else None,
        "kcalUnknownCount": unknown,
        "menuSource": menu["meta"]["source"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="麦当劳菜单适配层（官方 MCP）")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def add_common(p):
        p.add_argument("--store-code", default=None)
        p.add_argument("--city", default="上海")
        p.add_argument("--keyword", default="人民广场")
        p.add_argument("--source", choices=["auto", "builtin", "mcp"], default="auto")

    p_stores = sub.add_parser("stores", help="查询附近门店")
    p_stores.add_argument("--city", default="上海")
    p_stores.add_argument("--keyword", default="人民广场")

    add_common(sub.add_parser("menu", help="输出菜单 JSON"))

    p_pick = sub.add_parser("pick", help="随机搭配一份套餐")
    p_pick.add_argument("--seed", type=int, required=True)
    p_pick.add_argument("--prefer", choices=["any", "spicy", "mild", "light"], default="any")
    p_pick.add_argument("--budget", type=float, default=None)
    add_common(p_pick)

    args = parser.parse_args()

    if args.cmd == "stores":
        client = McpClient(get_token())
        stores = query_nearby_stores(client, args.city, args.keyword)
        json.dump(stores, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0

    menu = load_menu(
        store_code=args.store_code,
        city=args.city,
        keyword=args.keyword,
        force_builtin=(args.source == "builtin"),
    )

    if args.cmd == "menu":
        json.dump(menu, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0

    combo = pick_combo(menu, args.seed, prefer=args.prefer, budget=args.budget)
    combo["menuMeta"] = menu["meta"]
    json.dump(combo, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
