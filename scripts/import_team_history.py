"""导入用户提供的 2025-26 欧冠战绩，并为上赛季未参加欧冠的球队抓取最近五场。"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE_DATA = ROOT / "data" / "site_data.json"
OUTPUT = ROOT / "data" / "team_history.json"
SOURCE_HTML = Path(r"C:\Users\Administrator\Desktop\欧冠36强_2025-26完整战绩_分主客场.html")

HISTORY_NAME_MAP = {
    "巴黎圣日耳曼": "Paris", "拜仁": "Bayern München", "皇马": "Real Madrid", "利物浦": "Liverpool",
    "国米": "Inter", "曼城": "Man City", "阿森纳": "Arsenal", "巴萨": "Barcelona", "马竞": "Atleti",
    "多特蒙德": "Borussia Dortmund", "葡萄牙体育": "Sporting CP", "布鲁日": "Club Brugge",
    "埃因霍温": "PSV", "博德闪耀": "Bodø/Glimt", "那不勒斯": "Napoli", "比利亚雷亚尔": "Villarreal",
    "加拉塔萨雷": "Galatasaray", "布拉格斯拉维亚": "Slavia Praha",
}

ESPN_IDS = {
    "AEK Athens": 887, "Aston Villa": 362, "Como": 2572, "Fenerbahçe": 436, "Feyenoord": 142,
    "LASK": 4411, "Leipzig": 11420, "Lens": 175, "Lille": 166, "Man United": 360, "Porto": 437,
    "Real Betis": 244, "Roma": 104, "Sabah": 20298, "Shakhtar": 493, "Slovan Bratislava": 521,
    "Stuttgart": 134, "Viking": 510,
}

OPPONENT_ZH = {
    "AEK Athens": "AEK雅典", "LASK Linz": "LASK林茨", "Aris": "阿里斯", "Kifisia": "基菲夏",
    "Levski Sofia": "索菲亚列夫斯基", "Iraklis": "伊拉克利斯", "Club Brugge": "布鲁日",
    "Hull City": "赫尔城", "Arsenal": "阿森纳", "Brighton & Hove Albion": "布莱顿",
    "Borussia Mönchengladbach": "门兴格拉德巴赫", "Genoa": "热那亚", "Napoli": "那不勒斯",
    "Udinese": "乌迪内斯", "Liverpool": "利物浦", "Fenerbahce": "费内巴切",
    "Besiktas": "贝西克塔斯", "Samsunspor": "萨姆松体育", "Lyon": "里昂", "Konyaspor": "科尼亚体育",
    "NEC Nijmegen": "奈梅亨", "Feyenoord Rotterdam": "费耶诺德", "ADO Den Haag": "海牙",
    "SC Cambuur": "坎布尔", "Go Ahead Eagles": "前进之鹰", "Sparta Rotterdam": "鹿特丹斯巴达",
    "Werder Bremen": "云达不来梅", "Borussia Mönchengladbach": "门兴格拉德巴赫", "Eintracht Trier": "特里尔",
    "Bayern Munich": "拜仁慕尼黑", "Leeds United": "利兹联", "Lens": "朗斯", "Lorient": "洛里昂",
    "Strasbourg": "斯特拉斯堡", "AJ Auxerre": "欧塞尔", "Paris Saint-Germain": "巴黎圣日耳曼",
    "Sunderland": "桑德兰", "Toulouse": "图卢兹", "Angers": "昂热", "Everton": "埃弗顿",
    "Manchester City": "曼彻斯特城", "Moreirense": "莫雷伦斯", "Académico de Viseu": "维塞乌学院",
    "Arouca": "阿罗卡", "Rio Ave": "里奥阿维", "Real Madrid": "皇家马德里", "Levante": "莱万特",
    "Valencia": "瓦伦西亚", "Real Sociedad": "皇家社会", "Atalanta": "亚特兰大", "Lecce": "莱切",
    "Fiorentina": "佛罗伦萨", "VfB Stuttgart": "斯图加特", "FC Cologne": "科隆", "Hansa Rostock": "罗斯托克",
    "Fulham": "富勒姆", "Sandefjord": "桑讷菲尤尔", "Aalesund": "奥勒松", "Dinamo Zagreb": "萨格勒布迪纳摩",
    "Rosenborg": "罗森博格", "Sabah FC": "萨巴赫", "Terengganu FC": "登嘉楼", "Brunei DPMM FC": "文莱DPMM",
    "PDRM FC": "皇家警察", "Penang FC": "槟城", "Melaka FC": "马六甲", "Celtic": "凯尔特人",
    "NK Celje": "采列", "Mjällby AIF": "米亚尔比", "Iberia 1999": "伊比利亚1999",
    "Wolfsberger": "沃尔夫斯贝格", "SC Rheindorf Altach": "阿尔特阿赫", "Real Betis": "皇家贝蒂斯",
    "Ipswich Town": "伊普斯维奇", "AC Milan": "AC米兰", "Lille": "里尔", "Borussia Dortmund": "多特蒙德",
}


class UclHistoryParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.depth = 0
        self.card: dict | None = None
        self.cards: list[dict] = []
        self.in_name = False
        self.cell: str | None = None
        self.row: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "div" and "card" in (attrs_dict.get("class") or "").split():
            self.depth = 1
            self.card = {"participated": attrs_dict.get("data-participated") == "1", "name": "", "rows": []}
            return
        if not self.card:
            return
        if tag == "div":
            self.depth += 1
        if tag == "span" and attrs_dict.get("class") == "team-name":
            self.in_name = True
        if tag == "tr":
            self.row = []
        if tag == "td":
            self.cell = ""

    def handle_data(self, data: str) -> None:
        if self.card and self.in_name:
            self.card["name"] += data
        if self.card and self.cell is not None:
            self.cell += data

    def handle_endtag(self, tag: str) -> None:
        if not self.card:
            return
        if tag == "span" and self.in_name:
            self.in_name = False
        if tag == "td" and self.cell is not None:
            self.row = self.row or []
            self.row.append(self.cell.strip())
            self.cell = None
        if tag == "tr" and self.row is not None:
            if len(self.row) == 5:
                self.card["rows"].append(self.row)
            self.row = None
        if tag == "div":
            self.depth -= 1
            if self.depth == 0:
                self.cards.append(self.card)
                self.card = None


def fetch_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "UCL-2026-27-static-site/1.0", "Accept": "text/html"})
    with urllib.request.urlopen(request, timeout=45) as response:
        text = response.read().decode("utf-8", "ignore")
    marker = "window['__espnfitt__']="
    start = text.find(marker)
    if start < 0:
        raise RuntimeError(f"ESPN page data missing: {url}")
    return json.JSONDecoder().raw_decode(text[start + len(marker):])[0]


def fetch_recent_form(key: str, team_id: int) -> tuple[str, dict]:
    url = f"https://www.espn.com/soccer/team/results/_/id/{team_id}"
    events = fetch_json(url)["page"]["content"]["results"]["events"]
    matches = []
    for event in events:
        if not event.get("completed") or not event.get("score"):
            continue
        competitors = event.get("competitors", [])
        current = next((item for item in competitors if str(item.get("id")) == str(team_id)), None)
        opponent = next((item for item in competitors if str(item.get("id")) != str(team_id)), None)
        if not current or not opponent:
            continue
        scores = [int(x.strip()) for x in re.split(r"[-–]", event["score"]) if x.strip().isdigit()]
        if len(scores) != 2:
            continue
        is_home = bool(current.get("isHome"))
        own, opp = (scores[0], scores[1]) if is_home else (scores[1], scores[0])
        result = "胜" if own > opp else "平" if own == opp else "负"
        opponent_name = opponent.get("displayName", "")
        matches.append({
            "date": event.get("date", "")[:10], "competition": event.get("league", ""),
            "venue": "主场" if is_home else "客场", "opponent": opponent_name,
            "opponent_zh": OPPONENT_ZH.get(opponent_name, opponent_name),
            "score": f"{own}–{opp}", "result": result,
        })
        if len(matches) == 5:
            break
    return key, {"source_url": url, "matches": matches}


def main() -> None:
    site_data = json.loads(SITE_DATA.read_text(encoding="utf-8"))
    history: dict[str, list[dict]] = {}
    if SOURCE_HTML.exists():
        parser = UclHistoryParser()
        parser.feed(SOURCE_HTML.read_text(encoding="utf-8"))
        for card in parser.cards:
            key = HISTORY_NAME_MAP.get(card["name"])
            if key and card["participated"]:
                history[key] = [{"date": row[0], "venue": row[1], "opponent_zh": row[2], "score": row[3], "result": row[4]} for row in card["rows"]]
    recent: dict[str, dict] = {}
    new_teams = [key for key, team in site_data["teams"].items() if team["last_ucl"] == "未参加2025-26赛季欧冠" and key in ESPN_IDS]
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(fetch_recent_form, key, ESPN_IDS[key]) for key in new_teams]
        for future in as_completed(futures):
            key, form = future.result()
            recent[key] = form
    OUTPUT.write_text(json.dumps({"meta": {"history_source": SOURCE_HTML.name, "recent_source": "ESPN team results pages"}, "ucl_2025_26": history, "recent_form": recent}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已导入 {len(history)} 支球队的 2025-26 欧冠战绩，抓取 {len(recent)} 支新晋球队近期赛果")


if __name__ == "__main__":
    main()
