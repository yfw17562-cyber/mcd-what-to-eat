#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成单文件交互式「今天吃什么 · 麦门运势」页面。

用法：
  python build_page.py -o out.html
  python build_page.py -o out.html --city 北京 --keyword 国贸 --store-code 1950564
  python build_page.py -o out.html --source builtin
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fortune as fortune_mod  # noqa: E402
import mcd_menu  # noqa: E402

TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>今天吃什么 · 麦门运势</title>
<style>
  :root{
    --green:#6abe30; --green-d:#4c8a22; --gold:#f7c948; --gold-d:#c79a1e;
    --red:#c0392b; --red-d:#97271b; --blue:#5aa9e6;
    --panel:#f7eccf; --panel-2:#efddb0; --line:#e3cd9b;
    --ink:#3a2a16; --ink-2:#6c5638; --ink-3:#9a8254;
    --border:#2b1d0e; --shadow:#1a1106; --yellow:#f7c948; --card:#f7eccf;
  }
  *{box-sizing:border-box;}
  body{
    margin:0; padding:24px 16px 64px;
    font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","HarmonyOS Sans SC","Microsoft YaHei","Noto Sans SC",system-ui,"Segoe UI",Roboto,Arial,sans-serif;
    font-weight:700;
    color:var(--ink);
    background:linear-gradient(180deg,#aee3ef 0%,#aee3ef 19%,#8ec96a 19%,#6abe30 56%,#4f9e2a 100%);
    background-attachment:fixed;
    min-height:100vh;
  }
  body::before{
    content:""; position:fixed; inset:0; pointer-events:none; z-index:0;
    background-image:repeating-linear-gradient(0deg, rgba(0,0,0,.045) 0 2px, transparent 2px 4px);
    mix-blend-mode:multiply;
  }

  /* ---- 像素装饰：金拱门 Logo + 漂浮汉堡/冰淇淋 ---- */
  .logo-m{ width:26px; height:26px; vertical-align:-6px; margin-right:7px; }
  .deco{
    position:fixed; z-index:0; pointer-events:none;
    filter:drop-shadow(0 4px 0 rgba(26,17,6,.22));
    animation:floaty 4.5s ease-in-out infinite;
  }
  .deco svg{ width:70px; height:70px; display:block; }
  .deco-1{ left:22px;  top:128px; }
  .deco-2{ right:22px; top:208px; animation-delay:-1.4s; }
  .deco-3{ left:46px;  bottom:70px; animation-delay:-2.6s; }
  .deco-4{ right:46px; bottom:128px; animation-delay:-0.8s; }
  @keyframes floaty{0%,100%{transform:translateY(0) rotate(-3deg);}50%{transform:translateY(-13px) rotate(3deg);}}
  @media(max-width:980px){ .deco{ display:none; } }
  .wrap{max-width:1060px; margin:0 auto; position:relative; z-index:1;}

  .panel,.card{
    border:4px solid var(--border);
    background:var(--panel);
    box-shadow:inset -4px -4px 0 0 rgba(0,0,0,.12), inset 4px 4px 0 0 rgba(255,255,255,.42), 0 10px 24px -12px rgba(26,17,6,.55);
  }

  header{text-align:center; margin-bottom:26px; position:relative;}
  .brand{
    display:inline-block; font-size:11.5px; letter-spacing:.16em; color:var(--red-d); font-weight:800;
    background:var(--panel-2); border:3px solid var(--border);
    padding:5px 12px; margin-bottom:12px;
    box-shadow:inset -3px -3px 0 rgba(0,0,0,.12), inset 3px 3px 0 rgba(255,255,255,.34);
  }
  h1{font-size:clamp(27px,5vw,44px); margin:2px 0 6px; letter-spacing:.02em; font-weight:900; line-height:1.25; color:var(--ink);}
  h1 em{font-style:normal; color:var(--red);}
  .sub{color:var(--ink-2); font-size:13.5px; margin:0; line-height:1.7; font-weight:700;}
  .today{color:var(--ink-2); font-size:12px; font-weight:800; margin-top:10px; background:rgba(43,29,14,.08); display:inline-block; padding:4px 12px; border:2px solid var(--border);}

  .panel{ padding:20px 18px; margin-top:22px; }
  .row{display:flex; flex-wrap:wrap; gap:10px 18px; align-items:center;}
  .row + .row{margin-top:14px; padding-top:14px; border-top:3px dashed var(--line);}
  .lab{font-size:12px; font-weight:800; color:var(--ink-2); letter-spacing:.08em; min-width:52px;}
  .chips{display:flex; flex-wrap:wrap; gap:8px;}
  .chip{
    border:3px solid var(--border); background:var(--panel-2); color:var(--ink); font-weight:800;
    padding:7px 14px; font-size:13px; cursor:pointer; font-family:inherit;
    box-shadow:inset -3px -3px 0 rgba(0,0,0,.12), inset 3px 3px 0 rgba(255,255,255,.34);
    transition:.08s;
  }
  .chip:hover{filter:brightness(1.06);}
  .chip:active{transform:translateY(2px); box-shadow:inset 3px 3px 0 rgba(0,0,0,.16);}
  .chip.on{background:var(--green); color:#fff; border-color:var(--border);}
  input[type=text],input[type=number]{
    font-family:inherit; font-size:13px; font-weight:800; color:var(--ink);
    border:3px solid var(--border); padding:8px 10px; background:var(--panel-2);
    outline:none; box-shadow:inset 3px 3px 0 rgba(0,0,0,.1);
  }
  input::placeholder{color:var(--ink-3); font-weight:600;}
  input:focus{border-color:var(--green-d); background:#fff;}
  input[type=text]{width:150px;} input[type=number]{width:96px;}

  .go{
    display:flex; align-items:center; justify-content:center; gap:10px;
    width:100%; margin-top:18px; padding:15px; border:4px solid var(--border);
    background:var(--red); color:#fff;
    font-size:17px; font-weight:900; letter-spacing:.08em; cursor:pointer; font-family:inherit;
    box-shadow:inset -4px -4px 0 rgba(0,0,0,.2), inset 4px 4px 0 rgba(255,255,255,.22), 0 4px 0 var(--shadow);
    transition:.08s;
  }
  .go:hover{filter:brightness(1.07);}
  .go:active{transform:translateY(3px); box-shadow:inset -4px -4px 0 rgba(0,0,0,.2), inset 4px 4px 0 rgba(255,255,255,.22), 0 1px 0 var(--shadow);}
  .go[disabled]{opacity:.7; cursor:default; transform:none;}

  .grid{display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1.12fr); gap:22px; margin-top:22px; align-items:start;}
  @media(max-width:860px){.grid{grid-template-columns:1fr;}}

  .card{ padding:22px 20px; }
  .card-h{display:flex; align-items:center; justify-content:space-between; gap:10px; margin:0 0 16px; padding-bottom:12px; border-bottom:3px solid var(--line);}
  .card-h h2{margin:0; font-size:16.5px; font-weight:900; letter-spacing:.04em; color:var(--ink);}
  .tag{font-size:11px; font-weight:800; color:var(--ink-2); background:var(--panel-2); border:3px solid var(--border); padding:3px 10px; white-space:nowrap; box-shadow:inset -2px -2px 0 rgba(0,0,0,.1);}

  .level-box{text-align:center; padding:6px 0 14px;}
  .level{
    display:inline-block; font-size:44px; font-weight:900; letter-spacing:.08em;
    padding:8px 24px; border:4px solid currentColor;
    background:var(--panel-2);
    box-shadow:inset -4px -4px 0 rgba(0,0,0,.12), inset 4px 4px 0 rgba(255,255,255,.34), 0 4px 0 var(--shadow);
    line-height:1.15; transition:color .2s, opacity .2s;
  }
  .level .lv-emoji{ font-size:1.12em; margin-right:8px; vertical-align:-3px; line-height:1; }
  .level.rolling{opacity:.95; animation:wob .25s steps(2) infinite;}
  @keyframes wob{0%{transform:translateY(0);}100%{transform:translateY(-3px);}}
  .level-hint{margin-top:14px; font-size:12.5px; font-weight:700; color:var(--ink-2); line-height:1.7;}

  .block{margin-top:18px;}
  .block-t{font-size:12px; font-weight:900; color:var(--ink-2); letter-spacing:.12em; margin-bottom:9px; padding-left:8px; border-left:6px solid var(--green);}
  .pills{display:flex; flex-wrap:wrap; gap:8px;}
  .pill{font-size:12.5px; font-weight:800; padding:6px 12px; border:3px solid var(--border); background:var(--panel-2); color:var(--ink); box-shadow:inset -2px -2px 0 rgba(0,0,0,.1);}
  .pill.yi{background:#cfe8c0; border-color:#3f7a2e; color:#234d18;}
  .pill.ji{background:#f2cfc8; border-color:#9b2d20; color:#7a1c12;}

  .stats{display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:10px; margin-top:18px;}
  .stat{border:3px solid var(--border); padding:12px 8px; text-align:center; background:var(--panel-2); box-shadow:inset -3px -3px 0 rgba(0,0,0,.1), inset 3px 3px 0 rgba(255,255,255,.34);}
  .stat .k{font-size:10.5px; font-weight:800; color:var(--ink-2); letter-spacing:.06em;}
  .stat .v{font-size:18px; font-weight:900; margin-top:6px; color:var(--ink);}
  .stat .v.small{font-size:12.5px; line-height:1.5; font-weight:800;}
  .swatch{display:inline-block; width:14px; height:14px; vertical-align:-2px; margin-right:5px; border:2px solid var(--border);}

  .poem{
    margin-top:18px; padding:16px 14px; text-align:center; position:relative;
    background:var(--panel-2); border:3px solid var(--border);
    box-shadow:inset -3px -3px 0 rgba(0,0,0,.1), inset 3px 3px 0 rgba(255,255,255,.34);
    font-size:14.5px; line-height:2; color:var(--ink); letter-spacing:.03em; font-weight:700; white-space:pre-line;
  }
  .poem-lab{font-size:10px; font-weight:900; letter-spacing:.3em; color:var(--ink-2); margin-bottom:8px;}

  /* ---- 套餐 ---- */
  .items{display:flex; flex-direction:column; gap:6px;}
  .item{display:flex; align-items:center; gap:12px; padding:10px 8px; border:3px solid var(--line); background:var(--panel); transition:.08s; box-shadow:inset -2px -2px 0 rgba(0,0,0,.06);}
  .item:hover{background:var(--panel-2);}
  .thumb{
    position:relative; width:56px; height:56px; flex:0 0 56px;
    background:var(--panel-2); border:3px solid var(--border); overflow:hidden; display:grid; place-items:center;
    box-shadow:inset -3px -3px 0 rgba(0,0,0,.12), inset 3px 3px 0 rgba(255,255,255,.34);
  }
  .thumb svg{width:26px; height:26px;}
  .thumb img{position:absolute; inset:0; width:100%; height:100%; object-fit:cover; image-rendering:pixelated;}
  .item .nm{flex:1; min-width:0;}
  .item .nm b{display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; font-size:14px; font-weight:800; letter-spacing:.01em; line-height:1.4;}
  .item .nm .meta{font-size:11px; font-weight:700; color:var(--ink-2); margin-top:4px; display:flex; flex-wrap:wrap; gap:6px; align-items:center;}
  .mini{border:2px solid var(--border); background:var(--panel-2); color:var(--ink-2); padding:1px 6px; font-size:10px; font-weight:800; line-height:1.5; box-shadow:inset -1px -1px 0 rgba(0,0,0,.08);}
  .mini.hot{border-color:#9b2d20; background:#f2cfc8; color:#7a1c12;}
  .mini.new{border-color:#27608f; background:#cfe3f2; color:#1b4a6e;}
  .item .pr{text-align:right; white-space:nowrap;}
  .item .pr .now{font-size:15px; font-weight:900; color:var(--ink);}
  .item .pr .was{font-size:10px; font-weight:600; color:var(--ink-3); text-decoration:line-through; margin-left:4px;}
  .item .pr .kc{display:block; font-size:10px; font-weight:700; color:var(--ink-2); margin-top:3px;}

  .total{
    display:flex; align-items:center; justify-content:space-between; gap:12px;
    margin-top:16px; padding:15px 17px;
    border:4px solid var(--border);
    background:var(--green-d); color:#fff;
    box-shadow:inset -4px -4px 0 rgba(0,0,0,.18), inset 4px 4px 0 rgba(255,255,255,.14), 0 4px 0 var(--shadow);
  }
  .total .l{font-size:11px; font-weight:800; letter-spacing:.1em; color:#eaf6df;}
  .total .amt{font-size:27px; font-weight:900; color:var(--gold); line-height:1.1;}
  .total .amt sup{font-size:14px; vertical-align:6px; margin-right:1px;}
  .total .r{text-align:right; font-size:11px; font-weight:700; color:#eaf6df; line-height:1.6;}

  .share{margin-top:16px; width:100%; padding:12px; cursor:pointer; border:3px solid var(--border); background:var(--panel-2); color:var(--ink); font-family:inherit; font-size:13px; font-weight:800; box-shadow:inset -3px -3px 0 rgba(0,0,0,.1), inset 3px 3px 0 rgba(255,255,255,.34); transition:.08s;}
  .share:hover{filter:brightness(1.06);}
  .share:active{transform:translateY(2px);}

  footer{max-width:1060px; margin:30px auto 0; text-align:center; font-size:11px; font-weight:700; color:var(--ink-2); line-height:1.9; position:relative; z-index:1;}
  footer b{color:var(--ink);}
  .src{display:inline-flex; align-items:center; gap:7px; border:3px solid var(--border); background:var(--panel); padding:5px 12px; margin-bottom:8px; font-weight:800; box-shadow:inset -2px -2px 0 rgba(0,0,0,.1);}
  .dot{width:9px; height:9px; background:var(--gold); border:2px solid var(--border); flex:0 0 9px;}
  .dot.mcp{background:var(--green);}

  .hide{display:none !important;}
  @keyframes rise{from{opacity:0; transform:translateY(10px);} to{opacity:1; transform:none;}}
  .rise{animation:rise .42s cubic-bezier(.2,.8,.3,1) both;}
</style>
</head>
<body>
<div class="wrap">

  <header>
    <div class="brand">
      <svg class="logo-m" viewBox="0 0 32 32" shape-rendering="crispEdges" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <g fill="#FFC72C" stroke="#6B3E12" stroke-width="1">
          <rect x="3" y="7" width="4" height="19"/><rect x="11" y="7" width="4" height="19"/><rect x="3" y="7" width="12" height="4"/>
          <rect x="17" y="7" width="4" height="19"/><rect x="25" y="7" width="4" height="19"/><rect x="17" y="7" width="12" height="4"/>
        </g>
      </svg>Golden Arches Oracle
    </div>
    <h1>今天吃什么 · <em>麦门运势</em></h1>
    <p class="sub">摇一支签，让金拱门替你决定这一顿。</p>
    <div class="today" id="todayLine"></div>
  </header>

  <section class="panel">
    <div class="row">
      <div class="lab">口味</div>
      <div class="chips" id="preferChips"></div>
    </div>
    <div class="row">
      <div class="lab">预算</div>
      <input type="number" id="budget" placeholder="不限" min="1" step="1">
      <div class="lab" style="margin-left:10px;">签主</div>
      <input type="text" id="signer" placeholder="anonymous" maxlength="12">
    </div>
    <button class="go" id="go">今天吃什么</button>
  </section>

  <div class="grid hide" id="grid">

    <section class="card rise">
      <div class="card-h"><h2>今日运势</h2><span class="tag" id="fortuneTag">麦门签筒</span></div>
      <div class="level-box">
        <div class="level" id="level">大吉</div>
        <div class="level-hint" id="levelHint"></div>
      </div>

      <div class="block">
        <div class="block-t">宜</div>
        <div class="pills" id="yi"></div>
      </div>
      <div class="block">
        <div class="block-t">忌</div>
        <div class="pills" id="ji"></div>
      </div>

      <div class="stats">
        <div class="stat"><div class="k">幸运数字</div><div class="v" id="num">—</div></div>
        <div class="stat"><div class="k">幸运色</div><div class="v small" id="color">—</div></div>
        <div class="stat"><div class="k">幸运时段</div><div class="v small" id="slot">—</div></div>
      </div>

      <div class="poem"><div class="poem-lab">签 诗</div><span id="poem"></span></div>
    </section>

    <section class="card rise" style="animation-delay:.06s">
      <div class="card-h"><h2>今日套餐</h2><span class="tag" id="comboTag">搭配中</span></div>
      <div class="items" id="items"></div>
      <div class="total">
        <div>
          <div class="l">应付合计</div>
          <div class="amt" id="totalPrice"><sup>¥</sup>0</div>
        </div>
        <div class="r" id="totalMeta"></div>
      </div>
      <button class="share" id="share">复制一句分享文案</button>
    </section>

  </div>

  <footer>
    <div class="src"><span class="dot" id="srcDot"></span><span id="srcLabel">数据来源</span></div>
    <div id="srcNote"></div>
    <div style="margin-top:8px">本页面由 Skill <b>mcd-what-to-eat</b> 生成 · 运势结果仅供娱乐 · 「麦当劳」「金拱门」为麦当劳公司商标</div>
  </footer>

</div>

<div class="deco deco-1" aria-hidden="true">
  <svg viewBox="0 0 32 32" shape-rendering="crispEdges" xmlns="http://www.w3.org/2000/svg">
    <rect x="6" y="4" width="20" height="3" fill="#F2C14E"/><rect x="5" y="7" width="22" height="4" fill="#F2C14E"/><rect x="6" y="11" width="20" height="2" fill="#F2C14E"/>
    <rect x="10" y="6" width="2" height="2" fill="#FFF"/><rect x="18" y="8" width="2" height="2" fill="#FFF"/><rect x="14" y="5" width="2" height="2" fill="#FFF"/>
    <rect x="5" y="13" width="22" height="2" fill="#7CB342"/><rect x="6" y="15" width="20" height="4" fill="#8B5A2B"/>
    <rect x="6" y="19" width="20" height="2" fill="#E0A94A"/><rect x="5" y="21" width="22" height="4" fill="#F2C14E"/>
  </svg>
</div>
<div class="deco deco-2" aria-hidden="true">
  <svg viewBox="0 0 32 32" shape-rendering="crispEdges" xmlns="http://www.w3.org/2000/svg">
    <rect x="15" y="4" width="3" height="3" fill="#E53935"/>
    <rect x="11" y="8" width="10" height="3" fill="#FFD1DC"/><rect x="10" y="11" width="12" height="3" fill="#FFF"/><rect x="11" y="14" width="10" height="4" fill="#FFF"/>
    <rect x="13" y="18" width="6" height="2" fill="#E0A040"/><rect x="12" y="20" width="8" height="2" fill="#E0A040"/><rect x="11" y="22" width="10" height="2" fill="#E0A040"/>
    <rect x="10" y="24" width="12" height="2" fill="#E0A040"/><rect x="9" y="26" width="14" height="3" fill="#E0A040"/>
  </svg>
</div>
<div class="deco deco-3" aria-hidden="true">
  <svg viewBox="0 0 32 32" shape-rendering="crispEdges" xmlns="http://www.w3.org/2000/svg">
    <rect x="15" y="4" width="3" height="3" fill="#E53935"/>
    <rect x="11" y="8" width="10" height="3" fill="#FFD1DC"/><rect x="10" y="11" width="12" height="3" fill="#FFF"/><rect x="11" y="14" width="10" height="4" fill="#FFF"/>
    <rect x="13" y="18" width="6" height="2" fill="#E0A040"/><rect x="12" y="20" width="8" height="2" fill="#E0A040"/><rect x="11" y="22" width="10" height="2" fill="#E0A040"/>
    <rect x="10" y="24" width="12" height="2" fill="#E0A040"/><rect x="9" y="26" width="14" height="3" fill="#E0A040"/>
  </svg>
</div>
<div class="deco deco-4" aria-hidden="true">
  <svg viewBox="0 0 32 32" shape-rendering="crispEdges" xmlns="http://www.w3.org/2000/svg">
    <rect x="6" y="4" width="20" height="3" fill="#F2C14E"/><rect x="5" y="7" width="22" height="4" fill="#F2C14E"/><rect x="6" y="11" width="20" height="2" fill="#F2C14E"/>
    <rect x="10" y="6" width="2" height="2" fill="#FFF"/><rect x="18" y="8" width="2" height="2" fill="#FFF"/><rect x="14" y="5" width="2" height="2" fill="#FFF"/>
    <rect x="5" y="13" width="22" height="2" fill="#7CB342"/><rect x="6" y="15" width="20" height="4" fill="#8B5A2B"/>
    <rect x="6" y="19" width="20" height="2" fill="#E0A94A"/><rect x="5" y="21" width="22" height="4" fill="#F2C14E"/>
  </svg>
</div>

<script>
/* ==================== 数据 ==================== */
const MENU = __MENU_JSON__;
const CFG  = __CFG_JSON__;

/* ==================== 确定性随机 ==================== */
function xmur3(str){
  let h = 1779033703 ^ str.length;
  for (let i = 0; i < str.length; i++){
    h = Math.imul(h ^ str.charCodeAt(i), 3432918353);
    h = (h << 13) | (h >>> 19);
  }
  return function(){
    h = Math.imul(h ^ (h >>> 16), 2246822507);
    h = Math.imul(h ^ (h >>> 13), 3266489909);
    return (h ^= h >>> 16) >>> 0;
  };
}
function mulberry32(a){
  return function(){
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function prng(){
  const args = Array.prototype.slice.call(arguments).join('|');
  return mulberry32(xmur3(args)());
}
function pickWeighted(rnd, list, wkey){
  const total = list.reduce((s, x) => s + x[wkey], 0);
  let r = rnd() * total;
  for (const x of list){ r -= x[wkey]; if (r <= 0) return x; }
  return list[list.length - 1];
}
function sampleN(rnd, arr, n){
  const copy = arr.slice(), out = [];
  for (let i = 0; i < n && copy.length; i++){
    out.push(copy.splice(Math.floor(rnd() * copy.length), 1)[0]);
  }
  return out;
}

/* ==================== 运势 ==================== */
function drawFortune(date, signer, reroll){
  const rnd = prng('mcd-fortune', date, signer, reroll);
  const level = pickWeighted(rnd, CFG.levels, 'weight');
  const yi = sampleN(rnd, CFG.yi, 2);
  const jiPool = CFG.ji.filter(j => yi.indexOf(j) === -1);
  const ji = sampleN(rnd, jiPool, 1)[0];
  const color = CFG.colors[Math.floor(rnd() * CFG.colors.length)];
  const slot = CFG.slots[Math.floor(rnd() * CFG.slots.length)];
  const poems = CFG.poems[level.level];
  const poem = poems[Math.floor(rnd() * poems.length)];
  return { level, yi, ji, color, slot, poem, luckyNumber: 1 + Math.floor(rnd() * 99) };
}

/* ==================== 套餐 ==================== */
const ICONS = {
  burger:'<svg viewBox="0 0 24 24" fill="none" stroke="#C1550F" stroke-width="1.7" stroke-linecap="round"><path d="M4 10h16M4 13.5h16M5.5 17h13"/><path d="M4 10c0-3 3.6-5 8-5s8 2 8 5"/></svg>',
  side:'<svg viewBox="0 0 24 24" fill="none" stroke="#C1550F" stroke-width="1.7" stroke-linecap="round"><path d="M6 9.5v8M10.5 7v10.5M15 8.5v9M19 10.5v7"/><path d="M4.5 20.5h15"/></svg>',
  drink:'<svg viewBox="0 0 24 24" fill="none" stroke="#C1550F" stroke-width="1.7" stroke-linecap="round"><path d="M6.5 7h11l-1.4 12.2a1.5 1.5 0 0 1-1.5 1.3H9.4a1.5 1.5 0 0 1-1.5-1.3L6.5 7Z"/><path d="M5.5 7h13M10 3.5l1.6 3"/></svg>',
  dessert:'<svg viewBox="0 0 24 24" fill="none" stroke="#C1550F" stroke-width="1.7" stroke-linecap="round"><path d="M7 9.5A5 5 0 0 1 17 9.5Z"/><path d="M7.2 9.5h9.6l1 7.5a2 2 0 0 1-2 2.3H8.2a2 2 0 0 1-2-2.3l1-7.5Z"/></svg>'
};
const ROLE_NAME = { burger:'主食', side:'小食', drink:'饮品', dessert:'甜品' };

function kcalOf(i){
  if (i.kcal) return { text: i.kcal + ' kcal', mid: i.kcal, known: true };
  if (i.kcalMin) return { text: i.kcalMin + '–' + i.kcalMax + ' kcal', mid: Math.round((i.kcalMin + i.kcalMax) / 2), known: false };
  return { text: '热量不详', mid: 0, known: false };
}

function pickCombo(rnd, prefer, budget){
  const byRole = {};
  MENU.categories.forEach(c => { byRole[c.role] = c.items; });

  function pool(role){
    const items = (byRole[role] || []).slice();
    if (prefer === 'spicy'){
      const h = items.filter(i => i.name.indexOf('辣') >= 0 || (i.tags || []).some(t => t.indexOf('辣') >= 0));
      return h.length ? h : items;
    }
    if (prefer === 'mild'){
      const h = items.filter(i => i.name.indexOf('辣') < 0 && !(i.tags || []).some(t => t.indexOf('辣') >= 0));
      return h.length ? h : items;
    }
    if (prefer === 'light'){
      const h = items.filter(i => (i.kcalMax || i.kcal || 9999) <= 350);
      return h.length ? h : items;
    }
    return items;
  }

  const picked = [];
  ['burger','side','drink'].forEach(role => {
    const p = pool(role);
    if (p.length) picked.push({ role: role, item: p[Math.floor(rnd() * p.length)] });
  });
  if (rnd() < 0.65){
    const p = pool('dessert');
    if (p.length) picked.push({ role: 'dessert', item: p[Math.floor(rnd() * p.length)] });
  }

  const sum = arr => Math.round(arr.reduce((s, p) => s + p.item.price, 0) * 100) / 100;
  let total = sum(picked);
  if (budget && total > budget && picked.length > 2){
    let worst = 0;
    picked.forEach((p, idx) => { if (p.item.price < picked[worst].item.price) worst = idx; });
    picked.splice(worst, 1);
    total = sum(picked);
  }

  let kcalSum = 0, unknown = 0;
  picked.forEach(p => {
    const k = kcalOf(p.item);
    if (!k.known && k.mid === 0) unknown += 1;
    kcalSum += k.mid;
  });

  return { picked: picked, total: total, kcalSum: kcalSum, unknown: unknown };
}

/* ==================== 渲染 ==================== */
const $ = id => document.getElementById(id);
let PREFER = 'any';
let REROLL = 0;

const nowD = new Date();
const DATE_STR = nowD.getFullYear() + '-' + String(nowD.getMonth() + 1).padStart(2, '0') + '-' + String(nowD.getDate()).padStart(2, '0');
const WEEK = ['星期日','星期一','星期二','星期三','星期四','星期五','星期六'];
$('todayLine').textContent = DATE_STR + ' ' + WEEK[nowD.getDay()] + ' · 麦门签筒已开';

const PREFERS = [
  { key:'any', label:'随便' }, { key:'spicy', label:'吃辣' },
  { key:'mild', label:'不吃辣' }, { key:'light', label:'清淡点' }
];
PREFERS.forEach(p => {
  const b = document.createElement('button');
  b.className = 'chip' + (p.key === 'any' ? ' on' : '');
  b.textContent = p.label;
  b.onclick = () => {
    PREFER = p.key;
    [].forEach.call(document.querySelectorAll('#preferChips .chip'), c => c.classList.remove('on'));
    b.classList.add('on');
  };
  $('preferChips').appendChild(b);
});

const LEVEL_META = CFG.levels;   // 每个签等自带 emoji / color / hint

function tagClass(t){
  if (t.indexOf('辣') >= 0 || t.indexOf('人气') >= 0 || t.indexOf('爆款') >= 0 || t.indexOf('热卖') >= 0) return 'mini hot';
  if (t.indexOf('上新') >= 0 || t.indexOf('限定') >= 0 || t.indexOf('回归') >= 0) return 'mini new';
  return 'mini';
}

function levelHTML(lv){
  return '<span class="lv-emoji">' + lv.emoji + '</span>' + lv.level;
}

function renderFortune(f){
  const el = $('level');
  el.innerHTML = levelHTML(f.level);
  el.style.color = f.level.color;
  $('levelHint').textContent = f.level.emoji + ' ' + f.level.hint;
  $('yi').innerHTML = f.yi.map(t => '<span class="pill yi">' + t + '</span>').join('');
  $('ji').innerHTML = '<span class="pill ji">' + f.ji + '</span>';
  $('num').textContent = f.luckyNumber;
  $('color').innerHTML = '<span class="swatch" style="background:' + f.color.hex + '"></span>' + f.color.name;
  $('slot').textContent = f.slot;
  $('poem').textContent = f.poem;
}

function renderCombo(c){
  $('items').innerHTML = c.picked.map(p => {
    const i = p.item;
    const ic = ICONS[p.role] || ICONS.side;
    const img = i.image
      ? '<img src="' + i.image + '" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.remove()">'
      : '';
    const tags = (i.tags || []).slice(0, 2).map(t => '<span class="' + tagClass(t) + '">' + t + '</span>').join('');
    const was = i.originalPrice ? '<span class="was">¥' + i.originalPrice.toFixed(1) + '</span>' : '';
    const k = kcalOf(i);
    return '<div class="item">' +
        '<div class="thumb">' + ic + img + '</div>' +
        '<div class="nm"><b>' + i.name + '</b>' +
          '<div class="meta"><span>' + ROLE_NAME[p.role] + '</span>' + tags + '</div>' +
        '</div>' +
        '<div class="pr"><span class="now">¥' + i.price.toFixed(1) + '</span>' + was +
          '<span class="kc">' + k.text + '</span></div>' +
      '</div>';
  }).join('');

  $('totalPrice').innerHTML = '<sup>¥</sup>' + c.total.toFixed(1);
  const kcalTxt = c.unknown > 0
    ? '≥ ' + c.kcalSum + ' kcal（' + c.unknown + ' 项不详）'
    : '约 ' + c.kcalSum + ' kcal';
  $('totalMeta').innerHTML = '共 ' + c.picked.length + ' 件<br>' + kcalTxt;
}

function renderSource(){
  const m = MENU.meta;
  const isMcp = m.source === 'official-mcp';
  $('srcDot').className = 'dot' + (isMcp ? ' mcp' : '');
  let label = m.sourceLabel;
  if (isMcp && m.storeName) label += ' · ' + m.storeName;
  $('srcLabel').textContent = label;
  let note = m.note || '';
  if (isMcp && m.storeAddress) note = '门店地址：' + m.storeAddress + '（' + m.storeCode + '）。' + note;
  if (m.fallbackReason) note += '（降级原因：' + m.fallbackReason + '）';
  $('srcNote').textContent = note;
}

$('comboTag').textContent = MENU.meta.source === 'official-mcp' ? '官方实时菜单' : '内置参考菜单';

/* 抽签动画 */
let rolling = false;
function roll(){
  if (rolling) return;
  rolling = true;
  $('go').disabled = true;
  $('grid').classList.remove('hide');

  const el = $('level');
  el.classList.add('rolling');
  const t0 = Date.now();
  const timer = setInterval(() => {
    const lv = LEVEL_META[Math.floor(Math.random() * LEVEL_META.length)];
    el.innerHTML = levelHTML(lv);
    el.style.color = lv.color;
    if (Date.now() - t0 > 1000){
      clearInterval(timer);
      el.classList.remove('rolling');
      settle();
    }
  }, 62);
}

function settle(){
  const signer = ($('signer').value || '').trim() || 'anonymous';
  const budget = $('budget').value ? parseFloat($('budget').value) : null;

  renderFortune(drawFortune(DATE_STR, signer, REROLL));
  renderCombo(pickCombo(prng('mcd-combo', DATE_STR, signer, REROLL, PREFER), PREFER, budget));

  $('fortuneTag').textContent = signer + ' · 第 ' + (REROLL + 1) + ' 签';
  [].forEach.call(document.querySelectorAll('.rise'), n => {
    n.style.animation = 'none'; void n.offsetWidth; n.style.animation = '';
  });
  $('go').textContent = '再抽一签';
  $('go').disabled = false;
  rolling = false;
}

$('go').onclick = () => {
  if ($('grid').classList.contains('hide')){ roll(); return; }
  REROLL += 1;
  roll();
};

$('share').onclick = () => {
  const signer = ($('signer').value || '').trim() || 'anonymous';
  const budget = $('budget').value ? parseFloat($('budget').value) : null;
  const f = drawFortune(DATE_STR, signer, REROLL);
  const c = pickCombo(prng('mcd-combo', DATE_STR, signer, REROLL, PREFER), PREFER, budget);
  const names = c.picked.map(p => p.item.name).join(' + ');
  const txt = '【' + DATE_STR + ' 麦门运势】' + f.level + '｜宜：' + f.yi.join('、') + '｜忌：' + f.ji +
    '｜今日套餐：' + names + '，共 ¥' + c.total.toFixed(1) +
    '｜幸运数字 ' + f.luckyNumber + '，幸运色 ' + f.color.name;
  const done = () => { $('share').textContent = '已复制，去分享吧'; setTimeout(() => { $('share').textContent = '复制一句分享文案'; }, 1800); };
  if (navigator.clipboard && navigator.clipboard.writeText){
    navigator.clipboard.writeText(txt).then(done).catch(() => window.prompt('复制这段文案：', txt));
  } else {
    window.prompt('复制这段文案：', txt);
  }
};

renderSource();
</script>
</body>
</html>
"""


def build(output_path: str, source: str = "auto", store_code: str | None = None,
          city: str = "上海", keyword: str = "人民广场") -> str:
    menu = mcd_menu.load_menu(store_code=store_code, city=city, keyword=keyword,
                              force_builtin=(source == "builtin"))

    cfg = {
        "levels": [dict(lv) for lv in fortune_mod.LEVELS],
        "yi": fortune_mod.YI,
        "ji": fortune_mod.JI,
        "colors": [{"name": n, "hex": h} for n, h in fortune_mod.LUCKY_COLORS],
        "slots": fortune_mod.LUCKY_SLOTS,
        "poems": fortune_mod.POEMS,
    }

    html = (TEMPLATE
            .replace("__MENU_JSON__", json.dumps(menu, ensure_ascii=False))
            .replace("__CFG_JSON__", json.dumps(cfg, ensure_ascii=False)))

    out_dir = os.path.dirname(os.path.abspath(output_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(html)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="生成麦门运势交互页")
    parser.add_argument("-o", "--output", required=True, help="输出 HTML 路径")
    parser.add_argument("--source", choices=["auto", "builtin", "mcp"], default="auto")
    parser.add_argument("--store-code", default=None)
    parser.add_argument("--city", default="上海")
    parser.add_argument("--keyword", default="人民广场")
    args = parser.parse_args()

    path = build(args.output, args.source, args.store_code, args.city, args.keyword)
    print(f"已生成: {path}  ({os.path.getsize(path)/1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
