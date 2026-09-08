from __future__ import annotations

import html
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "site_data.json"
RESULTS = ROOT / "data" / "results.json"
TEAMS_DIR = ROOT / "teams"
ASSETS_DIR = ROOT / "assets"

SLUGS = {
    "AEK Athens": "aek-athens", "Arsenal": "arsenal", "Aston Villa": "aston-villa",
    "Atleti": "atletico-madrid", "Barcelona": "barcelona", "Bayern München": "bayern-munich",
    "Bodø/Glimt": "bodo-glimt", "Borussia Dortmund": "borussia-dortmund",
    "Club Brugge": "club-brugge", "Como": "como", "Fenerbahçe": "fenerbahce",
    "Feyenoord": "feyenoord", "Galatasaray": "galatasaray", "Inter": "inter-milan",
    "LASK": "lask", "Leipzig": "rb-leipzig", "Lens": "lens", "Lille": "lille",
    "Liverpool": "liverpool", "Man City": "manchester-city", "Man United": "manchester-united",
    "Napoli": "napoli", "Paris": "paris-saint-germain", "Porto": "porto", "PSV": "psv",
    "Real Betis": "real-betis", "Real Madrid": "real-madrid", "Roma": "roma", "Sabah": "sabah",
    "Shakhtar": "shakhtar-donetsk", "Slavia Praha": "slavia-prague",
    "Slovan Bratislava": "slovan-bratislava", "Sporting CP": "sporting-cp",
    "Stuttgart": "stuttgart", "Viking": "viking", "Villarreal": "villarreal",
}

PLAYER_ZH = {
    "Bruno Guimarães": "布鲁诺·吉马良斯", "Ezri Konsa": "埃兹里·孔萨",
    "Piero Hincapié": "皮耶罗·因卡皮耶", "Christos Tzolis": "赫里斯托斯·佐利斯",
    "Gabriel Martinelli": "加布里埃尔·马丁内利", "Nicolas Jackson": "尼古拉斯·杰克逊",
    "João Gomes": "若昂·戈麦斯", "Zion Suzuki": "铃木彩艳",
    "Matteo Ruggeri": "马泰奥·鲁杰里", "Morgan Rogers": "摩根·罗杰斯",
    "Ollie Watkins": "奥利·沃特金斯", "Youri Tielemans": "尤里·蒂勒曼斯",
    "Donyell Malen": "多尼尔·马伦", "Morten Hjulmand": "莫滕·尤尔曼德",
    "Kang-in Lee": "李刚仁", "Cristian Romero": "克里斯蒂安·罗梅罗",
    "Thiago Almada": "蒂亚戈·阿尔马达", "Anthony Gordon": "安东尼·戈登",
    "Rodri": "罗德里", "Karim Adeyemi": "卡里姆·阿德耶米",
    "Ferran Torres": "费兰·托雷斯", "Ismael Saibari": "伊斯梅尔·塞巴里",
    "Trevoh Chalobah": "特雷沃·查洛巴", "Mason Greenwood": "梅森·格林伍德",
    "Rafael Leão": "拉斐尔·莱奥", "Djed Spence": "杰德·斯彭斯",
    "Gabriel Jesus": "加布里埃尔·热苏斯", "Leandro Trossard": "莱安德罗·特罗萨德",
    "Jakub Kiwior": "雅库布·基维奥尔", "Ethan Nwaneri": "伊桑·恩瓦内里",
    "Christian Nørgaard": "克里斯蒂安·诺尔高", "Reiss Nelson": "赖斯·尼尔森",
}

CLUB_ZH = {
    "Newcastle United": "纽卡斯尔联", "Aston Villa": "阿斯顿维拉", "Bayer 04 Leverkusen": "勒沃库森",
    "Club Brugge KV": "布鲁日", "Leeds United": "利兹联", "FC Porto": "波尔图",
    "Al-Hilal SFC": "利雅得新月", "Besiktas JK": "贝西克塔斯", "FC Barcelona": "巴塞罗那",
    "Hamburger SV": "汉堡", "Everton FC": "埃弗顿", "SV Werder Bremen": "云达不来梅",
    "Feyenoord Rotterdam": "费耶诺德", "Borussia Dortmund": "多特蒙德", "Real Madrid": "皇家马德里",
    "Manchester City": "曼彻斯特城", "Manchester United": "曼彻斯特联", "Liverpool FC": "利物浦",
    "Chelsea FC": "切尔西", "Paris Saint-Germain": "巴黎圣日耳曼", "Inter Milan": "国际米兰",
    "Atlético de Madrid": "马德里竞技", "SSC Napoli": "那不勒斯", "AC Milan": "AC米兰",
    "SL Benfica": "本菲卡", "AFC Bournemouth": "伯恩茅斯", "Rayo Vallecano": "巴列卡诺",
    "Villarreal CF": "比利亚雷亚尔", "Eintracht Frankfurt": "法兰克福",
    "Olympique Lyon": "里昂", "Ajax Amsterdam": "阿贾克斯", "West Ham United": "西汉姆联",
    "RCD Mallorca": "马略卡", "Burnley FC": "伯恩利", "VfL Wolfsburg": "沃尔夫斯堡",
    "Middlesbrough FC": "米德尔斯堡", "Atalanta BC": "亚特兰大",
    "TSG 1899 Hoffenheim": "霍芬海姆", "Brazil": "巴西国家队", "Germany": "德国国家队",
    "Spain": "西班牙国家队", "Saudi Arabia": "沙特阿拉伯国家队",
    "Without Club": "无俱乐部", "Retired": "退役",
}

KIND_ORDER = ["转入", "免签", "租借转入", "租借回归", "梯队提拔", "转出", "自由离队", "租借转出", "租借期满", "梯队调整"]


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def format_date(value: str) -> str:
    dt = datetime.strptime(value, "%Y-%m-%d")
    return f"{dt.year}年{dt.month}月{dt.day}日"


def fee_label(item: dict) -> str:
    if item.get("fee_m") is not None:
        return f"€{item['fee_m']:.2f}m"
    return esc(item.get("fee") or "未公开")


def player_name(item: dict) -> str:
    raw = item.get("player", "")
    translated = item.get("player_zh", raw)
    return PLAYER_ZH.get(raw, translated)


def club_name(value: str) -> str:
    return CLUB_ZH.get(value, value)


def coach_style(formation: str) -> str:
    clean = formation.replace("Attacking", "").replace("Defending", "").replace("Flat", "").strip()
    if clean.startswith("4-3-3"):
        return f"常用阵型为{clean}；四后卫之后配置三名中场，前场由两侧边锋与中锋展开。"
    if clean.startswith("4-2-3-1"):
        return f"常用阵型为{clean}；双后腰保护中路，三名攻击型球员在单前锋身后活动。"
    if clean.startswith(("3-4-", "3-5-")):
        return f"常用阵型为{clean}；三中卫构成后场基础，翼卫负责提供边路宽度。"
    if clean.startswith("4-4-2"):
        return f"常用阵型为{clean}；中后场采用两条四人线，前场保留双前锋配置。"
    if re.match(r"^[0-9-]+$", clean):
        return f"Transfermarkt教练资料页登记的常用阵型为{clean}。"
    return "资料来源未登记固定阵型；页面不据此推断打法。"


def layout(title: str, body: str, *, depth: int = 0, description: str = "") -> str:
    prefix = "../" if depth else ""
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="{esc(description or title)}"><title>{esc(title)}</title>
<link rel="stylesheet" href="{prefix}assets/style.css"></head><body>
<a class="skip-link" href="#main">跳到正文</a>{body}
</body></html>"""


def load_results() -> dict:
    if not RESULTS.exists():
        return {"meta": {"completed_matches": 0}, "results": {}, "standings": [], "reports": {}}
    return json.loads(RESULTS.read_text(encoding="utf-8"))


def stat(report: dict, side: str, key: str, fallback: str = "官方统计尚未发布") -> str:
    value = (report.get(f"{side}_stats") or {}).get(key)
    return str(value) if value is not None else fallback


def report_cell(report: dict, side: str, kind: str) -> str:
    s = report.get(f"{side}_stats") or {}
    if kind == "attack":
        return f"进球 {stat(report, side, 'goals')} · 射门 {stat(report, side, 'attempts')} · 射正 {stat(report, side, 'attempts_on_target')} · 控球 {stat(report, side, 'ball_possession')}%"
    if kind == "defense":
        return f"扑救 {stat(report, side, 'saves')} · 抢断 {stat(report, side, 'tackles')} · 犯规 {stat(report, side, 'fouls_committed')}"
    if kind == "injuries":
        return report.get("injuries", {}).get(side, "本场未见官方伤停通报")
    if kind == "cards":
        return f"黄牌 {stat(report, side, 'yellow_cards', '0')} · 红牌 {stat(report, side, 'red_cards', '0')}"
    lineup = (report.get("lineups") or {}).get(side) or {}
    coach = "、".join(lineup.get("coaches") or []) or "官方阵容资料未列教练"
    return f"首发名单 {lineup.get('starting_count', '—')} 人 · 场边教练：{coach}"


def report_team_link(key: str, data: dict, depth: int = 0) -> str:
    prefix = "../" * depth
    return f'<a class="report-team" href="{prefix}teams/{SLUGS[key]}.html">{esc(data["teams"][key]["name_zh"])}</a>'


def render_report_row(game: dict, report: dict, data: dict, depth: int = 0) -> str:
    home = report_team_link(game["home_en"], data, depth)
    away = report_team_link(game["away_en"], data, depth)
    detail = f'{"../" * depth}matches/{game["id"]}.html'
    duel = f'<div class="report-link"><span><a href="{detail}">{home}</a> <b>{game.get("home_score", "—")} — {game.get("away_score", "—")}</b> <a href="{detail}">{away}</a></span><small><a href="{detail}">查看单场简报 ↗</a></small></div>'
    cells = [duel]
    for kind in ("attack", "defense", "injuries", "cards", "tactics"):
        cells.append(f'<div class="report-lines"><p><span>主</span>{esc(report_cell(report, "home", kind))}</p><p><span>客</span>{esc(report_cell(report, "away", kind))}</p></div>')
    return "<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>"


def render_matchday_page(date: str, games: list[dict], data: dict, result_data: dict) -> str:
    rows = "".join(render_report_row(g, result_data.get("reports", {}).get(str(g["id"]), {}), data, 1) for g in games)
    body = f'''<header class="team-top"><a class="back" href="../matchdays.html">← 返回比赛日追踪</a><span>官方赛果与比赛简报</span></header>
<main id="main" class="tracking-main"><section class="tracking-hero"><p>比赛日追踪 · {esc(format_date(date))}</p><h1>{esc(format_date(date))}</h1><p>按对手汇总进攻、防守、伤停、牌面与教练战术资料。每项只展示官方比赛资料。</p></section>
<section class="report-card"><div class="table-scroll"><table class="report-table"><thead><tr><th>比赛</th><th>进攻情况</th><th>防守情况</th><th>伤停情况</th><th>红黄牌</th><th>教练战术</th></tr></thead><tbody>{rows}</tbody></table></div><p class="data-note">统计与阵容资料来源：UEFA官方比赛接口；未发布项目按页面说明显示。</p></section></main><footer class="team-footer"><span>欧洲冠军联赛 · 2026—27</span><span>数据来源：UEFA官方</span></footer>'''
    return layout(f"{format_date(date)}比赛日追踪", body, depth=1, description=f"{format_date(date)}欧冠比赛日五项比赛追踪")


def render_match_page(game: dict, report: dict, data: dict) -> str:
    h = data["teams"][game["home_en"]]["name_zh"]
    a = data["teams"][game["away_en"]]["name_zh"]
    sections = []
    for title, kind in (("进攻情况", "attack"), ("防守情况", "defense"), ("伤停情况", "injuries"), ("红黄牌", "cards"), ("教练战术", "tactics")):
        sections.append(f'<section class="match-detail-section"><h2>{title}</h2><div class="match-side"><div><h3>{esc(h)}</h3><p>{esc(report_cell(report, "home", kind))}</p></div><div><h3>{esc(a)}</h3><p>{esc(report_cell(report, "away", kind))}</p></div></div></section>')
    body = f'''<header class="team-top"><a class="back" href="../matchdays/{game["date"]}.html">← 返回比赛日</a><span>官方比赛简报</span></header><main id="main" class="tracking-main"><section class="tracking-hero match-hero"><p>{esc(format_date(game["date"]))} · {esc(game["time_cet"])} 中欧时间</p><h1>{esc(h)} <span>{game.get("home_score", "—")} — {game.get("away_score", "—")}</span> {esc(a)}</h1></section>{"".join(sections)}</main><footer class="team-footer"><span>欧洲冠军联赛 · 2026—27</span><span>数据来源：UEFA官方</span></footer>'''
    return layout(f"{h} vs {a}｜比赛简报", body, depth=1, description=f"{h}对阵{a}的比赛日五项资料简报")


def render_matchdays_index(data: dict, result_data: dict) -> str:
    by_date = defaultdict(list)
    fixture_map = {str(g["id"]): g for g in data["fixtures"]}
    for match_id, result in result_data.get("results", {}).items():
        game = fixture_map.get(str(match_id))
        if game:
            by_date[game["date"]].append({**game, **result})
    cards = "".join(f'<a class="matchday-card" href="matchdays/{date}.html"><span>{esc(format_date(date))}</span><b>{len(games)}场</b><small>查看五项比赛追踪 ↗</small></a>' for date, games in sorted(by_date.items(), reverse=True))
    empty = '<div class="tracking-empty">首场比赛结束后，这里会自动生成按比赛日整理的五项追踪表。</div>' if not cards else cards
    body = f'''<header class="team-top"><a class="back" href="index.html">← 返回首页</a><span>2026—27 · 欧冠联赛阶段</span></header><main id="main" class="tracking-main"><section class="tracking-hero"><p>比赛日追踪 · 自动更新</p><h1>比赛日简报</h1><p>每个比赛日一张表，按对手记录进攻、防守、伤停、红黄牌与教练战术。</p></section><section class="matchday-grid">{empty}</section></main><footer class="team-footer"><span>欧洲冠军联赛 · 2026—27</span><span>数据来源：UEFA官方</span></footer>'''
    return layout("2026-27赛季欧冠比赛日追踪", body, description="按比赛日和对手整理欧冠五项比赛资料")


def result_for(game: dict, results: dict) -> dict | None:
    return results.get(str(game["id"]))


def render_index(data: dict) -> str:
    result_data = load_results()
    teams = sorted(data["teams"].values(), key=lambda x: x["name_zh"])
    cards = "".join(
        f'<li><a href="teams/{SLUGS[t["key"]]}.html"><span>{esc(t["name_zh"])}</span><b aria-hidden="true">↗</b></a></li>'
        for t in teams
    )
    data_date = datetime.strptime(data["meta"]["data_date"], "%Y-%m-%d")
    month_games = [game for game in data["fixtures"] if game["date"].startswith(data_date.strftime("%Y-%m"))]
    games_by_day: dict[str, list[dict]] = defaultdict(list)
    for game in month_games:
        games_by_day[game["date"]].append(game)
    match_days = "".join(
        f"""<section class="match-day"><div class="day-label"><time datetime="{date}"><b>{date[8:10]}</b><span>{data_date.month}月{int(date[8:10])}日</span></time><small>{len(games)}场</small></div>
<ol class="match-list">{"".join(f'''<li class="month-match"><time>{esc(game['time_cet'])}</time><div class="match-pair"><a href="teams/{SLUGS[game['home_en']]}.html">{esc(game['home'])}</a><span>vs</span><a href="teams/{SLUGS[game['away_en']]}.html">{esc(game['away'])}</a></div></li>''' for game in sorted(games, key=lambda x: (x['time_cet'], x['id'])))}</ol></section>"""
        for date, games in sorted(games_by_day.items())
    )
    body = f"""
<header class="home-hero"><div class="eyebrow">2026—27 · UEFA CHAMPIONS LEAGUE</div>
<div class="hero-mark" aria-hidden="true">36</div><h1>欧冠联赛阶段<br>俱乐部档案</h1>
<p>先看本月比赛，再进入球队档案。</p><nav class="home-hero-links"><a href="standings.html">查看联赛积分榜 <b>↗</b></a><a href="matchdays.html">比赛日追踪 <b>↗</b></a></nav></header>
<main id="main" class="home-main"><section class="home-section month-section" aria-labelledby="month-title"><div class="home-section-head"><div><p>赛程总览</p><h2 id="month-title">{data_date.month}月比赛日</h2></div><span>{len(month_games)}场比赛 · 所有队名均可跳转</span></div>
<div class="month-board">{match_days}</div></section>
{"" if not result_data.get('results') else render_latest_results(data, result_data)}
<section class="home-section team-section" aria-labelledby="teams-title"><div class="home-section-head"><div><p>俱乐部档案</p><h2 id="teams-title">36支球队</h2></div><span>赛程、转会、教练</span></div><nav aria-label="36支球队"><ol class="team-grid">{cards}</ol></nav></section></main>
<footer class="site-footer"><span>欧洲冠军联赛 · 2026—27</span><span>离线静态资料站</span></footer>"""
    return layout("2026-27赛季欧冠36队档案", body, description="2026-27赛季欧冠联赛阶段36支球队中文资料站")


def render_latest_results(data: dict, result_data: dict) -> str:
    teams = data["teams"]
    results = list(result_data.get("results", {}).values())
    results.sort(key=lambda item: (item.get("date") or "", item["id"]), reverse=True)
    rows = []
    for item in results[:8]:
        rows.append(f"<li><time>{esc(item.get('date', ''))}</time><a href=\"teams/{SLUGS[item['home_en']]}.html\">{esc(teams[item['home_en']]['name_zh'])}</a><b>{item['home_score']} — {item['away_score']}</b><a href=\"teams/{SLUGS[item['away_en']]}.html\">{esc(teams[item['away_en']]['name_zh'])}</a><a class=\"report-link\" href=\"matches/{item['id']}.html\">五项简报 ↗</a></li>")
    return f"""<section class="home-section latest-section" aria-labelledby="latest-title"><div class="home-section-head"><div><p>已结束比赛</p><h2 id="latest-title">最新赛果</h2></div><span>已同步{result_data['meta'].get('completed_matches', len(results))}场官方赛果 · <a href=\"matchdays.html\">查看比赛日简报</a></span></div><ol class="latest-results">{''.join(rows)}</ol></section>"""


def render_standings(data: dict, result_data: dict) -> str:
    team_map = data["teams"]
    standings = {row["key"]: row for row in result_data.get("standings", [])}
    rows = []
    for key, team in sorted(team_map.items(), key=lambda pair: (standings.get(pair[0], {}).get("rank", 999) if standings.get(pair[0], {}).get("played", 0) else 999, pair[1]["name_zh"])):
        row = standings.get(key, {})
        played = row.get("played", 0)
        rank = row.get("rank") if played else "—"
        rows.append(f"""<tr><th scope="row">{rank}</th><td><a class="table-team-link" href="teams/{SLUGS[key]}.html">{esc(team['name_zh'])}</a></td><td>{played}</td><td>{row.get('won', 0)}</td><td>{row.get('drawn', 0)}</td><td>{row.get('lost', 0)}</td><td>{row.get('goals_for', 0)}</td><td>{row.get('goals_against', 0)}</td><td class="gd">{row.get('goal_difference', 0):+d}</td><td class="points">{row.get('points', 0)}</td></tr>""")
    completed = result_data.get("meta", {}).get("completed_matches", 0)
    updated = result_data.get("meta", {}).get("updated_at", "尚未同步")
    body = f"""<header class="team-top"><a class="back" href="index.html">← 返回首页</a><span>2026—27 · 欧冠联赛阶段</span></header>
<main id="main" class="standings-main"><section class="standings-hero"><p>联赛阶段 · 官方实时汇总</p><h1>积分榜</h1><div class="standings-meta"><span>已结束比赛 <b>{completed}</b></span><span>数据同步 <b>{esc(updated[:16].replace('T', ' '))}</b></span></div></section>
<section class="standings-card"><div class="table-scroll"><table class="standings-table"><thead><tr><th>排名</th><th>球队</th><th>场</th><th>胜</th><th>平</th><th>负</th><th>进球</th><th>失球</th><th>净胜球</th><th>积分</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div><p class="data-note">排名、积分、进失球与净胜球来自 UEFA 官方积分榜；比赛结束后由自动任务同步。</p></section></main><footer class="team-footer"><span>欧洲冠军联赛 · 2026—27</span><span>数据来源：UEFA官方</span></footer>"""
    return layout("2026-27赛季欧冠积分榜", body, description="2026-27赛季欧冠联赛阶段官方积分榜、进失球与净胜球")


def fixture_for(team: dict, fixtures: list[dict]) -> list[dict]:
    games = []
    for game in fixtures:
        if game["home_en"] == team["key"]:
            games.append({**game, "venue": "主场", "opponent": game["away"]})
        elif game["away_en"] == team["key"]:
            games.append({**game, "venue": "客场", "opponent": game["home"]})
    return sorted(games, key=lambda x: (x["date"], x["time_cet"]))


def render_fixtures(team: dict, fixtures: list[dict], results: dict) -> str:
    games = fixture_for(team, fixtures)
    items = []
    for game in games:
        venue_cls = "home" if game["venue"] == "主场" else "away"
        opponent_key = game["away_en"] if game["venue"] == "主场" else game["home_en"]
        score = result_for(game, results)
        score_text = f"<span class=\"fixture-score\">{score['home_score']} — {score['away_score']}</span>" if score else "<span class=\"fixture-score upcoming\">未开赛</span>"
        items.append(f"""<li class="fixture">
<time datetime="{game['date']}"><small>{game['date'][5:7]}/{game['date'][8:10]}</small>{format_date(game['date'])}</time>
<span class="venue {venue_cls}">{game['venue']}</span><strong><a class="opponent-link" href="{SLUGS[opponent_key]}.html">{esc(game['opponent'])}</a></strong>{score_text}
<span class="kickoff">{esc(game['time_cet'])} 中欧时间</span></li>""")
    return "".join(items)


def render_transfer_group(kind: str, rows: list[dict]) -> str:
    if not rows:
        return ""
    direction_label = "来自" if rows[0]["direction"] == "in" else "去向"
    table_rows = "".join(f"""<tr><th scope="row"><span class="player-name">{esc(player_name(row))}</span>
<small>{esc(row['player']) if player_name(row) != row['player'] else '官方注册名'}</small></th>
<td>{esc(row['position_zh'])}</td><td>{esc(club_name(row['partner']))}</td><td class="fee">{fee_label(row)}</td>
<td>{esc(row['impact'])}</td></tr>""" for row in rows)
    is_open = " open" if kind in {"转入", "转出"} else ""
    return f"""<details class="transfer-group"{is_open}><summary><span>{esc(kind)}</span><b>{len(rows)}笔</b></summary>
<div class="table-scroll"><table><thead><tr><th>球员</th><th>位置</th><th>{direction_label}</th><th>费用</th><th>人员配置影响</th></tr></thead>
<tbody>{table_rows}</tbody></table></div></details>"""


def render_transfers(team: dict) -> str:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in team["arrivals"] + team["departures"]:
        grouped[item["kind"]].append(item)
    for rows in grouped.values():
        rows.sort(key=lambda x: (-(x.get("fee_m") or -1), x["player"]))
    groups = "".join(render_transfer_group(kind, grouped[kind]) for kind in KIND_ORDER if grouped[kind])
    return f"""<div class="transfer-lead"><div><b>{len(team['arrivals'])}</b><span>转入及回归</span></div>
<div><b>{len(team['departures'])}</b><span>转出及外租</span></div></div>{groups}
<p class="data-note">无通行中文译名的球员保留官方注册名；“人员配置影响”仅描述已发生的人员位置增减。</p>"""


def render_coach(team: dict) -> str:
    manager = team["managers"][0]
    appointed = manager.get("appointed", "")
    is_new = appointed.endswith("2026")
    status = "新任主教练" if is_new else "留任主教练"
    if re.match(r"\d{2}/\d{2}/\d{4}$", appointed):
        dt = datetime.strptime(appointed, "%d/%m/%Y")
        appointed_zh = f"{dt.year}年{dt.month}月{dt.day}日"
    else:
        appointed_zh = appointed
    previous = club_name(manager.get("previous_club", "俱乐部未公开"))
    change = (
        f"于{appointed_zh}上任；上任前所在球队或机构为{previous}。前任离任原因未在所用俱乐部资料页列示。"
        if is_new else f"于{appointed_zh}开始现职，新赛季继续留任。"
    )
    return f"""<div class="coach-grid"><div class="coach-name"><span>{status}</span><h3>{esc(manager['name_zh'])}</h3>
<p>{esc(manager['name'])}</p></div><div class="coach-facts"><p><b>任职记录</b>{esc(change)}</p>
<p><b>阵型与打法结构</b>{esc(coach_style(manager.get('formation', '')))}</p></div></div>"""


def render_team_page(team: dict, all_teams: list[dict], fixtures: list[dict], result_data: dict) -> str:
    idx = next(i for i, item in enumerate(all_teams) if item["key"] == team["key"])
    prev_team = all_teams[(idx - 1) % len(all_teams)]
    next_team = all_teams[(idx + 1) % len(all_teams)]
    coefficient = team.get("coefficient_rank")
    coeff_label = f"第{coefficient}位" if coefficient else "本赛季新列入"
    standing = next((row for row in result_data.get("standings", []) if row["key"] == team["key"]), {})
    played = standing.get("played", 0)
    rank = standing.get("rank") if played else "—"
    record_markup = f"""<section class="team-record" aria-label="当前联赛阶段统计"><div><span>当前排名</span><b>{rank}</b></div><div><span>已赛</span><b>{played}</b></div><div><span>胜 / 平 / 负</span><b>{standing.get('won', 0)} / {standing.get('drawn', 0)} / {standing.get('lost', 0)}</b></div><div><span>进球 / 失球</span><b>{standing.get('goals_for', 0)} / {standing.get('goals_against', 0)}</b></div><div><span>净胜球</span><b>{standing.get('goal_difference', 0):+d}</b></div><div><span>积分</span><b>{standing.get('points', 0)}</b></div></section>"""
    body = f"""
<header class="team-top"><a class="back" href="../index.html">← 返回36队</a><span>2026—27 · 欧冠联赛阶段</span></header>
<main id="main"><section class="club-hero"><div class="club-index">{idx + 1:02d}</div><p>{esc(team['official_name'])}</p>
<h1>{esc(team['name_zh'])}</h1><div class="fact-strip">
<div><span>全球俱乐部排名</span><b>第{team['world_rank']}位</b></div>
<div><span>阵容总身价</span><b>€{team['market_value_m']:,.2f}m</b></div>
<div><span>UEFA系数排名</span><b>{coeff_label}</b></div>
<div><span>上赛季欧冠</span><b>{esc(team['last_ucl'])}</b></div></div></section>
<section class="content-section route-section"><div class="section-head"><span>01</span><div><p>联赛阶段</p><h2>当前战绩</h2></div></div>{record_markup}<ol class="fixture-route">{render_fixtures(team, fixtures, result_data.get('results', {}))}</ol></section>
<section class="content-section"><div class="section-head"><span>02</span><div><p>2026年夏季窗口</p><h2>转会明细</h2></div></div>{render_transfers(team)}</section>
<section class="content-section coach-section"><div class="section-head"><span>03</span><div><p>教练档案</p><h2>现任主教练</h2></div></div>{render_coach(team)}</section>
<nav class="page-switch" aria-label="切换球队"><a href="{SLUGS[prev_team['key']]}.html"><small>上一队</small>{esc(prev_team['name_zh'])}</a>
<a class="next" href="{SLUGS[next_team['key']]}.html"><small>下一队</small>{esc(next_team['name_zh'])}</a></nav></main>
<footer class="team-footer"><span>资料更新：2026年9月8日</span><span>数据来源：UEFA官方、俱乐部官宣、Transfermarkt、FootballDatabase、FBref等</span></footer>"""
    return layout(f"{team['name_zh']}｜2026-27欧冠", body, depth=1, description=f"{team['name_zh']}2026-27赛季欧冠赛程、转会和教练资料")


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    result_data = load_results()
    TEAMS_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    (ROOT / "index.html").write_text(render_index(data), encoding="utf-8")
    (ROOT / "standings.html").write_text(render_standings(data, result_data), encoding="utf-8")
    (ROOT / "matchdays.html").write_text(render_matchdays_index(data, result_data), encoding="utf-8")
    matchdays_dir = ROOT / "matchdays"
    matches_dir = ROOT / "matches"
    matchdays_dir.mkdir(exist_ok=True)
    matches_dir.mkdir(exist_ok=True)
    fixture_map = {str(g["id"]): g for g in data["fixtures"]}
    by_date: dict[str, list[dict]] = defaultdict(list)
    for match_id, result in result_data.get("results", {}).items():
        game = fixture_map.get(str(match_id))
        if game:
            full = {**game, **result}
            by_date[game["date"]].append(full)
            report = result_data.get("reports", {}).get(str(match_id), {})
            (matches_dir / f"{match_id}.html").write_text(render_match_page(full, report, data), encoding="utf-8")
    for date, games in by_date.items():
        (matchdays_dir / f"{date}.html").write_text(render_matchday_page(date, games, data, result_data), encoding="utf-8")
    all_teams = sorted(data["teams"].values(), key=lambda x: x["name_zh"])
    for team in all_teams:
        page = render_team_page(team, all_teams, data["fixtures"], result_data)
        (TEAMS_DIR / f"{SLUGS[team['key']]}.html").write_text(page, encoding="utf-8")
    print(f"已生成首页与{len(all_teams)}个球队子页面")


if __name__ == "__main__":
    main()
