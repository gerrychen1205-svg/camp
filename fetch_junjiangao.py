#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓「潮汐表精灵」漳浦县将军澳站（国家海洋信息中心站号 586）的潮汐表，
产出同目录的 tide-586.json，供静态页面用 fetch('tide-586.json') 同源读取。

为什么要有这一步：
  eisk.cn 的页面没有 CORS 头，浏览器不能直接抓；所以用 GitHub Actions 定时
  在这里抓一次、存成 JSON 提交进仓库，页面只读自己域名下的文件。

用法：python3 fetch_junjiangao.py [输出目录] [天数，默认8]
"""
import json
import re
import sys
import time
import datetime
import urllib.request

BASE = "https://eisk.cn/Tides/586.html?date={d}"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
STATION = {
    "code": "586",
    "name": "将军澳",
    "locality": "福建省漳浦县",
    "source": "国家海洋信息中心（经潮汐表精灵 eisk.cn 发布）",
    "note": "距 HI LIVE 半岛落日营地十几分钟车程，同一片海湾；比厦门站更贴近现场",
}
RE_TYPE = re.compile(r'([0-9]{2}:[0-9]{2})<span[^>]*>(满潮|干潮)</span>([0-9.]+)米')
RE_LUNAR = re.compile(r'农历\[\s*([^\]]+?)\s*\]')
RE_TIDEKIND = re.compile(r'<title>[^<]*?\[([^\]]+)\]潮汐表')


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "ignore")


def parse_day(html, date):
    events = [{"time": t, "type": "high" if k == "满潮" else "low", "cm": round(float(cm) * 100)}
              for t, k, cm in RE_TYPE.findall(html)]
    if not events:
        return None
    lunar = RE_LUNAR.search(html)
    # 潮型与汛期：标题下方「农历[ 十二] 中潮(死汛) 星期三」
    kind = re.search(r'中潮|小潮|大潮|微潮', html)
    xun = re.search(r'死汛|活汛', html)
    return {
        "date": date,
        "lunar": lunar.group(1) if lunar else None,
        "tide_kind": kind.group(0) if kind else None,
        "xun": xun.group(0) if xun else None,
        "events": events,
    }


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else "."
    days_n = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    today = datetime.date.today()
    days = []
    for i in range(days_n):
        d = (today + datetime.timedelta(days=i)).isoformat()
        try:
            html = get(BASE.format(d=d))
            rec = parse_day(html, d)
        except Exception as e:
            print(f"  ⚠️ {d} 抓取失败：{e}")
            rec = None
        if rec:
            days.append(rec)
            ev = " | ".join(f"{e['time']}{'满' if e['type']=='high' else '干'}{e['cm']/100:.1f}" for e in rec["events"])
            print(f"  ✅ {d}  {rec['lunar'] or '':>4} {rec['tide_kind'] or '':>3}{rec['xun'] or '':>3}   {ev}")
        time.sleep(0.6)

    if not days:
        sys.exit("❌ 一天都没抓到，放弃（不覆盖已有 JSON）")

    out = {
        "station": STATION,
        "fetched_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "datum": "当地理论最低潮面（天文潮，不含气象增减水）",
        "unit": "cm",
        "days": days,
    }
    path = outdir.rstrip("/") + "/tide-586.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\n✅ 写入 {path}：{len(days)} 天")


if __name__ == "__main__":
    main()
