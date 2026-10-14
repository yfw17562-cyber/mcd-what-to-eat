#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
今日运势引擎。

特性：
  - 确定性：同一天 + 同一签主 → 永远同一支签（用 SHA-256 做种子，不用系统随机数）。
  - 可重抽：传入不同的 reroll 序号即可换签。
  - 麦门风味：宜忌事项目光落在「今天吃什么」这件事上，兼带一点生活提醒。

用法：
  python fortune.py --date 2026-10-14
  python fortune.py --date 2026-10-14 --signer 小林 --reroll 1
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys

# 签等级与出现权重（总权重可不等）
LEVELS = [
    {"level": "大吉", "weight": 8, "color": "#DA291C", "emoji": "🎉", "hint": "今天点单不用看价格"},
    {"level": "吉", "weight": 22, "color": "#E8551F", "emoji": "✨", "hint": "想吃的都点得上"},
    {"level": "中吉", "weight": 25, "color": "#F2A21B", "emoji": "😊", "hint": "稳稳的幸福"},
    {"level": "小吉", "weight": 25, "color": "#8FBF3F", "emoji": "🍀", "hint": "小确幸正在派送"},
    {"level": "末吉", "weight": 15, "color": "#3FA9BF", "emoji": "🌤️", "hint": "晚一点吃更好"},
    {"level": "平", "weight": 5, "color": "#9AA0A6", "emoji": "😐", "hint": "平平淡淡才是真"},
]

YI = [
    "加个鸡腿", "把薯条蘸冰淇淋", "给同事带一杯咖啡", "多点一份麦乐鸡",
    "把可乐换成无糖", "试试当季限定新品", "向喜欢的人问一句早安",
    "吃完饭走两站路", "把番茄酱挤成一个笑脸", "给外卖小哥点个好评",
    "点大份薯条不心虚", "把下午茶提前半小时", "认真夸一次自己",
    "坐在窗边慢慢吃完这顿", "把套餐升级成超大份",
]

JI = [
    "空腹点餐", "深夜加单", "跟朋友抢最后一块麦乐鸡", "边吃饭边开视频会",
    "让外卖在门口放凉", "一边减肥一边点双层吉士", "把薯条泡到软掉",
    "算 AA 算到小数点后两位", "对着热量表吃饭", "在麦门前立 flag",
    "把冰可乐放在暖气片上", "连吃三顿油炸", "对服务员不耐烦",
]

LUCKY_COLORS = [
    ("麦门红", "#DA291C"), ("芝士黄", "#FFC72C"), ("生菜绿", "#5FA83C"),
    ("可乐棕", "#4A2C1A"), ("奶昔白", "#F5EFE6"), ("番茄酱红", "#C8102E"),
    ("冰蓝", "#6EC1E4"), ("夜宵黑", "#2B2B2B"), ("纸袋棕", "#B07B4F"),
]

LUCKY_SLOTS = [
    "11:00 - 13:00（正餐档）", "14:30 - 16:30（下午茶）",
    "17:30 - 19:30（晚饭档）", "21:00 - 23:00（深夜档）",
]

POEMS = {
    "大吉": [
        "金拱门下喜相逢，巨无霸里藏欢容。\n薯条酥脆财气旺，一杯可乐万事通。",
        "今日麦门开大门，想吃什么都对味。\n加份鸡块不算多，好运正在配送中。",
    ],
    "吉": [
        "薯条成双好运来，鸡块五块正相宜。\n不必纠结吃什么，随手指到就是它。",
        "可乐气泡往上冒，好事一件接一件。\n今日点单莫犹豫，第一眼看中的最香。",
    ],
    "中吉": [
        "板烧微焦正当时，一杯拿铁解千愁。\n无需刻意求惊喜，平常滋味最长久。",
        "玉米一杯清且甜，小食一份足解馋。\n今日宜稳不宜冲，吃完散步更悠然。",
    ],
    "小吉": [
        "小薯一份也是福，圆筒一个甜到心。\n莫嫌今日收获少，细水长流总相逢。",
        "麦乐鸡块四五枚，配上一杯冰红茶。\n小确幸在转角处，抬眼便见金拱门。",
    ],
    "末吉": [
        "今日莫急点大餐，缓上一刻味道佳。\n待到黄昏灯亮起，热食入口胜千金。",
        "冰品虽好莫贪多，一杯温水也养人。\n迟一点吃不算亏，好饭从来不怕晚。",
    ],
    "平": [
        "平平淡淡又一餐，白开水里也回甘。\n没有惊喜也无妨，饱腹即是好时光。",
        "无事发生即是福，按部就班过一天。\n若问今日吃什么，昨天那份再来一遍。",
    ],
}


def _rng(date: str, signer: str, reroll: int) -> random.Random:
    key = f"mcd-fortune|{date}|{signer}|{reroll}".encode("utf-8")
    seed = int(hashlib.sha256(key).hexdigest()[:16], 16)
    return random.Random(seed)


def draw_fortune(date: str, signer: str = "anonymous", reroll: int = 0) -> dict:
    rng = _rng(date, signer, reroll)

    level = rng.choices(LEVELS, weights=[l["weight"] for l in LEVELS], k=1)[0]

    yi = rng.sample(YI, 2)
    ji = rng.sample([j for j in JI if j not in yi], 1)[0]
    color_name, color_hex = rng.choice(LUCKY_COLORS)
    slot = rng.choice(LUCKY_SLOTS)
    poem = rng.choice(POEMS[level["level"]])

    return {
        "date": date,
        "signer": signer,
        "reroll": reroll,
        "level": level["level"],
        "levelColor": level["color"],
        "levelEmoji": level["emoji"],
        "levelHint": level["hint"],
        "yi": yi,
        "ji": ji,
        "luckyNumber": rng.randint(1, 99),
        "luckyColor": {"name": color_name, "hex": color_hex},
        "luckySlot": slot,
        "poem": poem,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="麦门今日运势")
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--signer", default="anonymous", help="签主名字")
    parser.add_argument("--reroll", type=int, default=0, help="重抽序号")
    parser.add_argument("--pretty", action="store_true", help="输出中文排版的文本签文")
    args = parser.parse_args()

    data = draw_fortune(args.date, args.signer, args.reroll)

    if args.pretty:
        print(f"【{data['date']} · {data['signer']}】")
        print(f"  签等：{data['levelEmoji']} {data['level']}  （{data['levelHint']}）")
        print(f"  宜：{data['yi'][0]}、{data['yi'][1]}")
        print(f"  忌：{data['ji']}")
        print(f"  幸运数字：{data['luckyNumber']}    幸运色：{data['luckyColor']['name']}")
        print(f"  幸运时段：{data['luckySlot']}")
        print()
        for line in data["poem"].split("\n"):
            print(f"    {line}")
        return 0

    json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
