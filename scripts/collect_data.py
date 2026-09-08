from __future__ import annotations

import concurrent.futures
import hashlib
import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from lxml import html


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_CACHE_DIR = DATA_DIR / "raw_cache"
TEAM_CACHE_DIR = DATA_DIR / "team_cache"

UEFA_FIXTURES = (
    "https://www.uefa.com/uefachampionsleague/news/"
    "02a8-2176fa83582b-d99f0b27f405-1000--champions-league-league-phase-fixtures-by-team/"
)
UEFA_PROFILES = (
    "https://www.uefa.com/uefachampionsleague/news/"
    "02a8-2171a88881a0-c70193b972c6-1000--meet-the-2026-27-champions-league-league-phase-teams/"
)
UEFA_COEFFICIENTS = "https://www.uefa.com/nationalassociations/uefarankings/club/?year=2026"
TM_PARTICIPANTS = (
    "https://www.transfermarkt.com/uefa-champions-league/teilnehmer/"
    "pokalwettbewerb/CL/saison_id/2026"
)
FOOTBALL_DB = "https://footballdatabase.com/ranking/world/{page}"

TEAM_ZH = {
    "AEK Athens": "AEK雅典",
    "Arsenal": "阿森纳",
    "Aston Villa": "阿斯顿维拉",
    "Atlético de Madrid": "马德里竞技",
    "Atleti": "马德里竞技",
    "Barcelona": "巴塞罗那",
    "Bayern München": "拜仁慕尼黑",
    "Bodø/Glimt": "博德闪耀",
    "Borussia Dortmund": "多特蒙德",
    "Club Brugge": "布鲁日",
    "Como": "科莫",
    "Fenerbahçe": "费内巴切",
    "Feyenoord": "费耶诺德",
    "Galatasaray": "加拉塔萨雷",
    "Inter": "国际米兰",
    "LASK": "LASK林茨",
    "Leipzig": "RB莱比锡",
    "Lens": "朗斯",
    "Lille": "里尔",
    "Liverpool": "利物浦",
    "Man City": "曼彻斯特城",
    "Manchester City": "曼彻斯特城",
    "Man United": "曼彻斯特联",
    "Manchester United": "曼彻斯特联",
    "Napoli": "那不勒斯",
    "Paris": "巴黎圣日耳曼",
    "Paris Saint-Germain": "巴黎圣日耳曼",
    "Porto": "波尔图",
    "PSV": "埃因霍温",
    "PSV Eindhoven": "埃因霍温",
    "Real Betis": "皇家贝蒂斯",
    "Real Madrid": "皇家马德里",
    "Roma": "罗马",
    "Sabah": "萨巴赫",
    "Shakhtar": "顿涅茨克矿工",
    "Shakhtar Donetsk": "顿涅茨克矿工",
    "Slavia Praha": "布拉格斯拉维亚",
    "Slovan Bratislava": "布拉迪斯拉发",
    "Sporting CP": "葡萄牙体育",
    "Stuttgart": "斯图加特",
    "Viking": "维京",
    "Villarreal": "比利亚雷亚尔",
}

COUNTRY_ZH = {
    "GRE": "希腊",
    "ENG": "英格兰",
    "ESP": "西班牙",
    "GER": "德国",
    "NOR": "挪威",
    "BEL": "比利时",
    "ITA": "意大利",
    "TUR": "土耳其",
    "NED": "荷兰",
    "POR": "葡萄牙",
    "AUT": "奥地利",
    "FRA": "法国",
    "AZE": "阿塞拜疆",
    "UKR": "乌克兰",
    "CZE": "捷克",
    "SVK": "斯洛伐克",
}

TM_NAME = {
    "AEK Athens": "AEK Athens",
    "Arsenal": "Arsenal FC",
    "Aston Villa": "Aston Villa",
    "Atlético de Madrid": "Atlético de Madrid",
    "Atleti": "Atlético de Madrid",
    "Barcelona": "FC Barcelona",
    "Bayern München": "Bayern Munich",
    "Bodø/Glimt": "FK Bodø/Glimt",
    "Borussia Dortmund": "Borussia Dortmund",
    "Club Brugge": "Club Brugge KV",
    "Como": "Como 1907",
    "Fenerbahçe": "Fenerbahce",
    "Feyenoord": "Feyenoord Rotterdam",
    "Galatasaray": "Galatasaray",
    "Inter": "Inter Milan",
    "LASK": "LASK",
    "Leipzig": "RB Leipzig",
    "Lens": "RC Lens",
    "Lille": "LOSC Lille",
    "Liverpool": "Liverpool FC",
    "Man City": "Manchester City",
    "Man United": "Manchester United",
    "Napoli": "SSC Napoli",
    "Paris": "Paris Saint-Germain",
    "Porto": "FC Porto",
    "PSV": "PSV Eindhoven",
    "Real Betis": "Real Betis Balompié",
    "Real Madrid": "Real Madrid",
    "Roma": "AS Roma",
    "Sabah": "Sabah FK",
    "Shakhtar": "Shakhtar Donetsk",
    "Slavia Praha": "SK Slavia Prague",
    "Slovan Bratislava": "Slovan Bratislava",
    "Sporting CP": "Sporting CP",
    "Stuttgart": "VfB Stuttgart",
    "Viking": "Viking FK",
    "Villarreal": "Villarreal CF",
}

FDB_ALIASES = {
    "AEK Athens": ["AEK", "AEK Athens"],
    "Arsenal": ["Arsenal"],
    "Aston Villa": ["Aston Villa"],
    "Atlético de Madrid": ["Atlético Madrid", "Atletico Madrid"],
    "Atleti": ["Atlético Madrid", "Atletico Madrid"],
    "Barcelona": ["Barcelona"],
    "Bayern München": ["Bayern München", "Bayern Munich"],
    "Bodø/Glimt": ["Bodø / Glimt", "Bodø/Glimt", "Bodo/Glimt"],
    "Borussia Dortmund": ["Borussia Dortmund"],
    "Club Brugge": ["Club Brugge"],
    "Como": ["Como 1907", "Como"],
    "Fenerbahçe": ["Fenerbahçe", "Fenerbahce"],
    "Feyenoord": ["Feyenoord"],
    "Galatasaray": ["Galatasaray"],
    "Inter": ["Inter Milan", "Internazionale"],
    "LASK": ["LASK Linz", "LASK"],
    "Leipzig": ["RB Leipzig", "Leipzig"],
    "Lens": ["Lens"],
    "Lille": ["Lille"],
    "Liverpool": ["Liverpool FC", "Liverpool"],
    "Man City": ["Manchester City"],
    "Man United": ["Manchester United"],
    "Napoli": ["SSC Napoli", "Napoli"],
    "Paris": ["Paris Saint-Germain", "PSG"],
    "Porto": ["FC Porto", "Porto"],
    "PSV": ["PSV Eindhoven", "PSV"],
    "Real Betis": ["Real Betis"],
    "Real Madrid": ["Real Madrid"],
    "Roma": ["AS Roma", "Roma"],
    "Sabah": ["Sabah FK", "Sabah"],
    "Shakhtar": ["Shakhtar Donetsk"],
    "Slavia Praha": ["Slavia Prague", "Slavia Praha"],
    "Slovan Bratislava": ["Slovan Bratislava"],
    "Sporting CP": ["Sporting", "Sporting CP", "Sporting Lisbon"],
    "Stuttgart": ["VfB Stuttgart", "Stuttgart"],
    "Viking": ["Viking", "Viking FK"],
    "Villarreal": ["Villarreal"],
}

FDB_COUNTRY = {
    "AEK Athens": "Greece", "Arsenal": "England", "Aston Villa": "England",
    "Atleti": "Spain", "Barcelona": "Spain", "Bayern München": "Germany",
    "Bodø/Glimt": "Norway", "Borussia Dortmund": "Germany", "Club Brugge": "Belgium",
    "Como": "Italy", "Fenerbahçe": "Turkey", "Feyenoord": "Netherlands",
    "Galatasaray": "Turkey", "Inter": "Italy", "LASK": "Austria", "Leipzig": "Germany",
    "Lens": "France", "Lille": "France", "Liverpool": "England", "Man City": "England",
    "Man United": "England", "Napoli": "Italy", "Paris": "France", "Porto": "Portugal",
    "PSV": "Netherlands", "Real Betis": "Spain", "Real Madrid": "Spain", "Roma": "Italy",
    "Sabah": "Azerbaijan", "Shakhtar": "Ukraine", "Slavia Praha": "Czech Republic",
    "Slovan Bratislava": "Slovakia", "Sporting CP": "Portugal", "Stuttgart": "Germany",
    "Viking": "Norway", "Villarreal": "Spain",
}

POSITION_ZH = {
    "Goalkeeper": "门将",
    "Sweeper": "清道夫",
    "Centre-Back": "中后卫",
    "Left-Back": "左后卫",
    "Right-Back": "右后卫",
    "Full-Back": "边后卫",
    "Defensive Midfield": "防守型中场",
    "Central Midfield": "中前卫",
    "Right Midfield": "右中场",
    "Left Midfield": "左中场",
    "Attacking Midfield": "进攻型中场",
    "Left Winger": "左边锋",
    "Right Winger": "右边锋",
    "Winger": "边锋",
    "Second Striker": "影锋",
    "Centre-Forward": "中锋",
    "Attack": "前锋",
    "Midfield": "中场",
    "Defender": "后卫",
}

COACH_ZH = {
    "Marko Nikolić": "马尔科·尼科利奇",
    "Marko Nikolic": "马尔科·尼科利奇",
    "Mikel Arteta": "米克尔·阿尔特塔",
    "Unai Emery": "乌奈·埃梅里",
    "Diego Simeone": "迭戈·西蒙尼",
    "Hansi Flick": "汉斯·弗里克",
    "Vincent Kompany": "文森特·孔帕尼",
    "Kjetil Knutsen": "谢蒂尔·克努森",
    "Niko Kovač": "尼科·科瓦奇",
    "Niko Kovac": "尼科·科瓦奇",
    "Ivan Leko": "伊万·莱科",
    "Cesc Fàbregas": "塞斯克·法布雷加斯",
    "İsmail Kartal": "伊斯梅尔·卡尔塔尔",
    "Giovanni van Bronckhorst": "吉奥瓦尼·范布隆克霍斯特",
    "Cristian Chivu": "克里斯蒂安·齐沃",
    "Dietmar Kühbauer": "迪特马尔·屈鲍尔",
    "Martín Demichelis": "马丁·德米凯利斯",
    "Okan Buruk": "奥坎·布鲁克",
    "Peter Bosz": "彼得·博斯",
    "José Mourinho": "何塞·穆里尼奥",
    "Gian Piero Gasperini": "吉安·皮耶罗·加斯佩里尼",
    "Dino Toppmöller": "迪诺·托普穆勒",
    "Davide Ancelotti": "达维德·安切洛蒂",
    "Andoni Iraola": "安多尼·伊劳拉",
    "Enzo Maresca": "恩佐·马雷斯卡",
    "Michael Carrick": "迈克尔·卡里克",
    "Massimiliano Allegri": "马西米利亚诺·阿莱格里",
    "Luis Enrique": "路易斯·恩里克",
    "Francesco Farioli": "弗朗切斯科·法里奥利",
    "Manuel Pellegrini": "曼努埃尔·佩莱格里尼",
    "Valdas Dambrauskas": "瓦尔达斯·丹布劳斯卡斯",
    "Arda Turan": "阿尔达·图兰",
    "Jindrich Trpisovsky": "因德日赫·特尔皮绍夫斯基",
    "Yaya Touré": "亚亚·图雷",
    "Rui Borges": "鲁伊·博尔热斯",
    "Sebastian Hoeneß": "塞巴斯蒂安·赫内斯",
    "Iñigo Pérez": "伊尼戈·佩雷斯",
    "Bjarte Lunde Aarsheim": "比亚特·伦德·奥尔斯海姆",
    "Morten Jensen": "莫滕·延森",
}

PROFILE_LAST_SEASON_ZH = {
    "Champions League winners": "欧冠冠军",
    "Champions League final": "欧冠亚军",
    "Semi-finalists": "欧冠四强",
    "Quarter-finalists": "欧冠八强",
    "Champions League quarter-finals": "欧冠八强",
    "Champions League round of 16": "欧冠16强",
    "Champions League knockout phase play-offs": "欧冠淘汰赛附加赛",
    "Champions League league phase": "欧冠联赛阶段",
}


def fetch(url: str, attempts: int = 4, timeout: int = 45) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read().decode("utf-8", "replace")
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url}: {last_error}")


def fetch_tm(url: str, markers: tuple[str, ...] = ()) -> str:
    """Read Transfermarkt directly when possible, otherwise use Jina's read-only rendering."""
    RAW_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = RAW_CACHE_DIR / f"{hashlib.sha1(url.encode()).hexdigest()}.txt"
    if cache_path.exists():
        cached = cache_path.read_text(encoding="utf-8")
        if not markers or any(marker in cached for marker in markers):
            return cached
    try:
        direct = fetch(url, attempts=1, timeout=20)
        if not markers or any(marker in direct for marker in markers):
            cache_path.write_text(direct, encoding="utf-8")
            return direct
    except Exception:  # noqa: BLE001
        pass
    last_error: Exception | None = None
    for _ in range(4):
        try:
            rendered = fetch("https://r.jina.ai/" + url, attempts=1, timeout=90)
            if rendered.count("\n") < 20 and "\\n" in rendered:
                rendered = rendered.replace("\\n", "\n")
            if markers and not any(marker in rendered for marker in markers):
                raise ValueError(f"missing expected page marker: {markers}")
            cache_path.write_text(rendered, encoding="utf-8")
            return rendered
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(2)
    raise RuntimeError(f"Transfermarkt page unavailable: {url}: {last_error}")


def jina(url: str) -> str:
    return fetch("https://r.jina.ai/" + url)


def normalize_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def canonical_team(value: str) -> str:
    value = value.strip()
    aliases = {
        "Manchester City": "Man City",
        "Manchester United": "Man United",
        "Atlético de Madrid": "Atleti",
        "Paris Saint-Germain": "Paris",
        "PSV Eindhoven": "PSV",
        "Shakhtar Donetsk": "Shakhtar",
    }
    return aliases.get(value, value)


def parse_profiles(markdown: str) -> dict[str, dict]:
    headings = list(
        re.finditer(r"(?m)^(?:\*\*)?([^,\r\n]{2,50}) \(([A-Z]{3})\)(?:\*\*)?\s*$", markdown)
    )
    profiles: dict[str, dict] = {}
    for index, heading in enumerate(headings):
        raw_name, association = heading.group(1).strip(), heading.group(2)
        name = canonical_team(raw_name)
        end = headings[index + 1].start() if index + 1 < len(headings) else len(markdown)
        block = markdown[heading.end() : end]

        def field(pattern: str) -> str | None:
            match = re.search(pattern, block, flags=re.I)
            return match.group(1).strip() if match else None

        coefficient = field(r"UEFA coefficient ranking.*?\*\*:\s*(N/A|\d+)")
        last_season = field(r"\*\*Last season\*\*:\s*([^*\r\n]+)")
        coach = field(r"\*\*Coaches?:\s*(.+?)\*\*")
        big_signing = field(r"\*\*Big summer signing:\s*(.+?)\*\*")
        coach_desc = ""
        if coach:
            marker = re.search(r"\*\*Coaches?:\s*.+?\*\*", block)
            if marker:
                tail = block[marker.end() :]
                parts = [x.strip() for x in re.split(r"\r?\n\s*\r?\n", tail) if x.strip()]
                if parts and not parts[0].startswith("**"):
                    coach_desc = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", parts[0])
        last_season_clean = (last_season or "").replace("\ufeff", "").strip()
        profiles[name] = {
            "official_name": raw_name,
            "association_code": association,
            "association": COUNTRY_ZH[association],
            "coefficient_rank": None if coefficient in (None, "N/A") else int(coefficient),
            "last_season_raw": last_season_clean or None,
            "last_ucl": PROFILE_LAST_SEASON_ZH.get(last_season_clean, "未参加2025-26赛季欧冠"),
            "uefa_coach": coach,
            "uefa_coach_zh": COACH_ZH.get(coach or "", coach),
            "coach_profile_note": coach_desc,
            "big_summer_signing": big_signing,
            "source_url": UEFA_PROFILES,
        }
    return profiles


def parse_fixtures(markdown: str) -> list[dict]:
    pattern = re.compile(
        r"(?m)^(\d{2}/\d{2}/\d{4})\s+\[([^\]]+?)\s+vs\s+([^\]]+?)\]"
        r"\((https://www\.uefa\.com/uefachampionsleague/match/[^\)]+)\)"
        r"(?:\s+\((\d{2}:\d{2})\))?\s*$"
    )
    grouped: dict[str, list[dict]] = defaultdict(list)
    for date_raw, home, away, url, time_raw in pattern.findall(markdown):
        date_obj = datetime.strptime(date_raw, "%d/%m/%Y")
        if date_obj.month == 1 and date_obj.year == 2026:
            date_obj = date_obj.replace(year=2027)
        if date_obj.month == 1 and date_obj.day == 28:
            date_obj = date_obj.replace(day=27)
        match_id = re.search(r"/match/(\d+)", url).group(1)
        grouped[match_id].append(
            {
                "id": match_id,
                "date": date_obj.strftime("%Y-%m-%d"),
                "time_cet": time_raw or "21:00",
                "home_en": canonical_team(home),
                "away_en": canonical_team(away),
                "source_url": url,
            }
        )
    fixtures: list[dict] = []
    for match_id, records in grouped.items():
        signatures = Counter(
            (r["date"], r["home_en"], r["away_en"], r["time_cet"]) for r in records
        )
        date, home, away, kickoff = signatures.most_common(1)[0][0]
        fixtures.append(
            {
                "id": match_id,
                "date": date,
                "time_cet": kickoff,
                "home": TEAM_ZH[home],
                "away": TEAM_ZH[away],
                "home_en": home,
                "away_en": away,
                "source_url": records[0]["source_url"],
            }
        )
    fixtures.sort(key=lambda item: (item["date"], item["time_cet"], item["id"]))
    return fixtures


def parse_market_value(raw: str) -> float:
    raw = raw.replace("€", "").replace(",", "").strip()
    if raw.endswith("bn"):
        return round(float(raw[:-2]) * 1000, 2)
    if raw.endswith("m"):
        return round(float(raw[:-1]), 2)
    if raw.endswith("k"):
        return round(float(raw[:-1]) / 1000, 2)
    return float(raw)


def get_tm_clubs() -> dict[str, dict]:
    source = fetch_tm(TM_PARTICIPANTS, ("Participating teams", "participants"))
    if "Markdown Content:" in source:
        clubs: dict[str, dict] = {}
        for row in source.splitlines():
            if "/startseite/verein/" not in row or "€" not in row:
                continue
            club_match = re.search(
                r"https://www\.transfermarkt\.com/([^/]+)/startseite/verein/(\d+) \"([^\"]+)\"",
                row,
            )
            values = re.findall(r"€[0-9.]+(?:bn|m|k)", row)
            if not club_match or not values:
                continue
            slug, club_id, name = club_match.groups()
            clubs[name] = {
                "tm_name": name,
                "tm_id": club_id,
                "tm_slug": slug,
                "market_value_m": parse_market_value(values[0]),
                "market_value_source": TM_PARTICIPANTS,
            }
        return clubs
    doc = html.fromstring(source)
    clubs: dict[str, dict] = {}
    for row in doc.xpath('//table[contains(@class,"items")]/tbody/tr'):
        cells = row.xpath("./td")
        links = row.xpath('.//a[contains(@href,"/startseite/verein/") and normalize-space(text())]')
        if not links or len(cells) < 6:
            continue
        name = " ".join(links[0].text_content().split())
        href = links[0].get("href")
        club_id = re.search(r"/verein/(\d+)", href).group(1)
        slug = href.strip("/").split("/")[0]
        clubs[name] = {
            "tm_name": name,
            "tm_id": club_id,
            "tm_slug": slug,
            "market_value_m": parse_market_value(" ".join(cells[-2].text_content().split())),
            "market_value_source": TM_PARTICIPANTS,
        }
    return clubs


def first_text(node, xpath: str) -> str:
    values = node.xpath(xpath)
    if not values:
        return ""
    value = values[0]
    return " ".join((value if isinstance(value, str) else value.text_content()).split())


def absolute_tm(href: str) -> str:
    return urllib.parse.urljoin("https://www.transfermarkt.com", href)


def transfer_kind(fee: str, direction: str, partner: str) -> str:
    low = fee.casefold()
    partner_low = partner.casefold()
    if "loan fee" in low or low == "loan transfer":
        return "租借转入" if direction == "in" else "租借转出"
    if "end of loan" in low:
        return "租借回归" if direction == "in" else "租借期满"
    if "free transfer" in low or partner_low in {"without club", "retired"}:
        return "免签" if direction == "in" else "自由离队"
    if any(x in partner_low for x in ("u19", "u21", "u23", "ii", "b team", "youth")):
        return "梯队提拔" if direction == "in" else "梯队调整"
    return "转入" if direction == "in" else "转出"


def fee_to_display(fee: str) -> tuple[str, float | None]:
    low = fee.casefold().strip()
    match = re.search(r"€\s*([0-9.,]+)\s*(bn|m|k)", low)
    if match:
        number = float(match.group(1).replace(",", ""))
        unit = match.group(2)
        if unit == "bn":
            number *= 1000
        elif unit == "k":
            number /= 1000
        return f"{number:.2f}", round(number, 3)
    if low.startswith("end of loan"):
        return "租借期满", None
    labels = {
        "free transfer": "免转会费",
        "loan transfer": "租借",
        "end of loan": "租借期满",
        "-": "未公开",
        "?": "未公开",
    }
    return labels.get(low, fee or "未公开"), None


def parse_transfer_rows(box, direction: str, page_url: str) -> list[dict]:
    output: list[dict] = []
    for row in box.xpath('.//table[contains(@class,"items")]/tbody/tr'):
        cells = row.xpath("./td")
        if len(cells) < 6:
            continue
        player_links = row.xpath('.//a[contains(@href,"/profil/spieler/") and normalize-space(text())]')
        if not player_links:
            continue
        player_link = player_links[0]
        player = " ".join(player_link.text_content().split())
        player_href = player_link.get("href")
        player_id_match = re.search(r"/spieler/(\d+)", player_href)
        position = first_text(cells[1], './/table[contains(@class,"inline-table")]/tr[2]')
        club_links = cells[4].xpath('.//a[contains(@href,"/startseite/verein/") and normalize-space(text())]')
        partner = " ".join(club_links[0].text_content().split()) if club_links else first_text(cells[4], ".")
        fee = first_text(cells[5], ".")
        fee_display, fee_m = fee_to_display(fee)
        detail_links = cells[5].xpath('.//a[contains(@href,"/jumplist/transfers/")]')
        source_url = absolute_tm(detail_links[0].get("href")) if detail_links else page_url
        kind = transfer_kind(fee, direction, partner)
        position_zh = POSITION_ZH.get(position, position or "未标注位置")
        if direction == "in":
            impact = f"补充{position_zh}位置人员，并增加该位置的轮换选择。"
        else:
            impact = f"离队后，球队在{position_zh}位置少一名可用球员。"
        if kind == "租借回归":
            impact = f"结束外租后回归，补充{position_zh}位置人员。"
        elif kind == "梯队提拔":
            impact = f"进入一线队人员范围，补充{position_zh}位置。"
        elif kind == "租借期满":
            impact = f"租借期满离队，{position_zh}位置的临时人员配置结束。"
        output.append(
            {
                "direction": direction,
                "kind": kind,
                "player": player,
                "player_zh": player,
                "player_id": player_id_match.group(1) if player_id_match else None,
                "position": position,
                "position_zh": position_zh,
                "partner": partner or "未公开",
                "fee_raw": fee,
                "fee": fee_display,
                "fee_m": fee_m,
                "impact": impact,
                "source_url": source_url,
            }
        )
    return output


def build_transfer_record(
    *, direction: str, player: str, player_url: str, player_id: str | None,
    position: str, partner: str, fee: str, source_url: str,
) -> dict:
    fee_display, fee_m = fee_to_display(fee)
    kind = transfer_kind(fee, direction, partner)
    position_zh = POSITION_ZH.get(position, position or "未标注位置")
    impact = (
        f"补充{position_zh}位置人员，并增加该位置的轮换选择。"
        if direction == "in"
        else f"离队后，球队在{position_zh}位置少一名可用球员。"
    )
    if kind == "租借回归":
        impact = f"结束外租后回归，补充{position_zh}位置人员。"
    elif kind == "梯队提拔":
        impact = f"进入一线队人员范围，补充{position_zh}位置。"
    elif kind == "租借期满":
        impact = f"租借期满离队，{position_zh}位置的临时人员配置结束。"
    return {
        "direction": direction,
        "kind": kind,
        "player": player,
        "player_zh": player,
        "player_id": player_id,
        "position": position,
        "position_zh": position_zh,
        "partner": partner or "未公开",
        "fee_raw": fee,
        "fee": fee_display,
        "fee_m": fee_m,
        "impact": impact,
        "source_url": source_url or player_url,
    }


def parse_transfer_markdown(section: str, direction: str, page_url: str) -> list[dict]:
    records: list[dict] = []
    for row in section.splitlines():
        if "/profil/spieler/" not in row or "/jumplist/transfers/" not in row:
            continue
        player_match = re.search(
            r"\[([^\]]+)\]\((https://www\.transfermarkt\.com/[^)]*/profil/spieler/(\d+)) \"([^\"]+)\"\)\s*([^|]+?)\s*\|",
            row,
        )
        fee_match = re.search(
            r"\|\s*\[([^\]]+)\]\((https://www\.transfermarkt\.com/jumplist/transfers/spieler/[^)]+)\)\s*\|",
            row,
        )
        if not player_match or not fee_match:
            continue
        partners = re.findall(
            r"https://www\.transfermarkt\.com/[^)]*/startseite/verein/\d+(?:/saison_id/\d+)? \"([^\"]+)\"",
            row,
        )
        records.append(
            build_transfer_record(
                direction=direction,
                player=player_match.group(4),
                player_url=player_match.group(2),
                player_id=player_match.group(3),
                position=" ".join(player_match.group(5).split()),
                partner=partners[-1] if partners else "未公开",
                fee=fee_match.group(1).replace("_", "").strip(),
                source_url=fee_match.group(2) or page_url,
            )
        )
    return records


def get_manager(staff_url: str) -> dict:
    source = fetch_tm(staff_url, ("Name/Position", "Appointed"))
    if "Markdown Content:" in source:
        managers: list[dict] = []
        for row in source.splitlines():
            if " Manager |" not in row or "/profil/trainer/" not in row:
                continue
            match = re.search(
                r"\[([^\]]+)\]\((https://www\.transfermarkt\.com/[^)]*/profil/trainer/(\d+)) \"([^\"]+)\"\) Manager",
                row,
            )
            parts = row.split("|")
            if not match or len(parts) < 7:
                continue
            previous = re.findall(r'/startseite/verein/\d+(?:/saison_id/\d+)? \"([^\"]+)\"', parts[6])
            name = match.group(4)
            managers.append({
                "name": name,
                "name_zh": COACH_ZH.get(name, name),
                "appointed": parts[4].strip(),
                "contract": parts[5].strip(),
                "previous_club": previous[-1] if previous else "无前任俱乐部记录",
                "profile_url": match.group(2),
                "formation": "资料页未登记固定阵型",
            })
        return {"managers": managers, "staff_source_url": staff_url}
    doc = html.fromstring(source)
    managers: list[dict] = []
    for table in doc.xpath("//table"):
        rows = table.xpath("./tbody/tr")
        if not rows:
            continue
        header = " ".join(table.xpath("string(.//thead)").split())
        if "Name/Position" not in header or "Appointed" not in header:
            continue
        for row in rows:
            cells = row.xpath("./td")
            if len(cells) < 5:
                continue
            role = first_text(cells[0], './/table[contains(@class,"inline-table")]/tr[2]')
            if role != "Manager":
                continue
            manager_links = cells[0].xpath('.//a[contains(@href,"/profil/trainer/") and normalize-space(text())]')
            if not manager_links:
                continue
            link = manager_links[0]
            previous_links = cells[-1].xpath('.//a[contains(@href,"/startseite/verein/")]')
            previous_href = previous_links[0].get("href") if previous_links else ""
            managers.append(
                {
                    "name": " ".join(link.text_content().split()),
                    "name_zh": COACH_ZH.get(" ".join(link.text_content().split()), " ".join(link.text_content().split())),
                    "appointed": first_text(cells[3], "."),
                    "contract": first_text(cells[4], "."),
                    "previous_club": previous_href.strip("/").split("/")[0].replace("-", " ").title() if previous_href else "无前任俱乐部记录",
                    "profile_url": absolute_tm(link.get("href")),
                }
            )
        break
    if not managers:
        return {"managers": [], "staff_source_url": staff_url}
    for manager in managers:
        try:
            profile_source = fetch(manager["profile_url"])
            formation_match = re.search(r"Preferred formation\s*:\s*</th>\s*<td[^>]*>\s*([^<]+)", profile_source, re.I)
            if not formation_match:
                formation_match = re.search(r"Preferred formation\s*:\s*([0-9][0-9\-\sA-Za-z]+)", re.sub(r"<[^>]+>", " ", profile_source), re.I)
            manager["formation"] = " ".join(formation_match.group(1).split()) if formation_match else "资料页未登记固定阵型"
        except Exception:  # noqa: BLE001
            manager["formation"] = "资料页未登记固定阵型"
    return {"managers": managers, "staff_source_url": staff_url}


def scrape_tm_team(canonical: str, tm: dict) -> tuple[str, dict]:
    slug, club_id = tm["tm_slug"], tm["tm_id"]
    transfers_url = f"https://www.transfermarkt.com/{slug}/transfers/verein/{club_id}/saison_id/2026"
    staff_url = f"https://www.transfermarkt.com/{slug}/mitarbeiter/verein/{club_id}"
    source = fetch_tm(transfers_url, ("## Arrivals", ">Arrivals<"))
    arrivals: list[dict] = []
    departures: list[dict] = []
    if "Markdown Content:" in source:
        arrivals_section = source.split("## Arrivals", 1)[1].split("## Departures", 1)[0]
        departures_section = source.split("## Departures", 1)[1].split("## Transfer record", 1)[0]
        arrivals = parse_transfer_markdown(arrivals_section, "in", transfers_url)
        departures = parse_transfer_markdown(departures_section, "out", transfers_url)
    else:
        doc = html.fromstring(source)
        for box in doc.xpath('//div[contains(concat(" ", normalize-space(@class), " "), " box ")]'):
            title = first_text(box, ".//h2")
            if title == "Arrivals":
                arrivals = parse_transfer_rows(box, "in", transfers_url)
            elif title == "Departures":
                departures = parse_transfer_rows(box, "out", transfers_url)
    try:
        manager = get_manager(staff_url)
    except Exception:  # noqa: BLE001
        manager = {"managers": [], "staff_source_url": staff_url}
    if not manager["managers"]:
        uefa_name = tm.get("uefa_coach") or "UEFA球队页所列教练组"
        manager["managers"] = [{
            "name": uefa_name,
            "name_zh": tm.get("uefa_coach_zh") or uefa_name,
            "appointed": "赛季前已在任",
            "contract": "俱乐部未公开",
            "previous_club": "俱乐部未公开",
            "profile_url": tm.get("source_url", UEFA_PROFILES),
            "formation": "资料页未登记固定阵型",
        }]
    print(f"完成 {canonical}: 转入{len(arrivals)} 转出{len(departures)} 教练{len(manager['managers'])}", flush=True)
    return canonical, {
        **tm,
        "transfers_url": transfers_url,
        "arrivals": arrivals,
        "departures": departures,
        **manager,
    }


def scrape_football_db_page(page: int) -> list[dict]:
    url = FOOTBALL_DB.format(page=page)
    source = fetch(url)
    doc = html.fromstring(source)
    records: list[dict] = []
    for row in doc.xpath("//table//tbody/tr"):
        cells = row.xpath("./td")
        if len(cells) < 3:
            continue
        rank_text = first_text(cells[0], ".")
        if not rank_text.isdigit():
            continue
        links = cells[1].xpath('.//a[contains(@href,"/clubs-ranking/")]')
        if links:
            label = links[0].xpath('.//*[contains(concat(" ", normalize-space(@class), " "), " limittext ")]')
            name = " ".join((label[0] if label else links[0]).text_content().split())
        else:
            name = first_text(cells[1], ".")
        country_links = cells[1].xpath('.//a[contains(@href,"/ranking/") and contains(@class,"sm_logo-name")]')
        country = " ".join(country_links[0].text_content().split()) if country_links else ""
        records.append({"rank": int(rank_text), "name": name, "country": country, "source_url": url})
    return records


def get_world_rankings() -> list[dict]:
    rows: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for page_rows in pool.map(scrape_football_db_page, range(1, 31)):
            rows.extend(page_rows)
    return rows


def enrich_manager_formation(manager: dict) -> str:
    url = manager.get("profile_url")
    if not url:
        return "资料页未登记固定阵型"
    try:
        source = fetch_tm(url, ("Preferred formation",))
        plain = re.sub(r"<[^>]+>", " ", source)
        match = re.search(r"Preferred formation\s*:?\s*\|?\s*([0-9][0-9\- ]+(?:Attacking|Defending|Flat)?)", plain, re.I)
        return " ".join(match.group(1).split()) if match else "资料页未登记固定阵型"
    except Exception:  # noqa: BLE001
        return "资料页未登记固定阵型"


def apply_world_rankings(teams: dict[str, dict], rankings: list[dict]) -> None:
    normalized = {(normalize_name(row["name"]), row.get("country")): row for row in rankings}
    for canonical, team in teams.items():
        match = None
        for alias in FDB_ALIASES[canonical]:
            match = normalized.get((normalize_name(alias), FDB_COUNTRY[canonical]))
            if match:
                break
        if not match:
            raise ValueError(f"FootballDatabase ranking missing: {canonical}")
        team["world_rank"] = match["rank"]
        team["world_rank_source"] = match["source_url"]


def wikipedia_zh_titles(names: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    unique = sorted({name for name in names if name})
    for offset in range(0, len(unique), 30):
        batch = unique[offset : offset + 30]
        params = urllib.parse.urlencode(
            {
                "action": "query",
                "prop": "langlinks",
                "lllang": "zh",
                "lllimit": "1",
                "redirects": "1",
                "format": "json",
                "formatversion": "2",
                "titles": "|".join(batch),
            }
        )
        try:
            # 中文百科只是译名增强来源。限流时立即跳过，不能阻塞事实数据落盘。
            payload = json.loads(fetch("https://en.wikipedia.org/w/api.php?" + params, attempts=1, timeout=12))
        except Exception:  # noqa: BLE001
            continue
        alias = {item["from"]: item["to"] for item in payload.get("query", {}).get("normalized", [])}
        alias.update({item["from"]: item["to"] for item in payload.get("query", {}).get("redirects", [])})
        pages = payload.get("query", {}).get("pages", [])
        by_title = {page.get("title"): page for page in pages}
        for original in batch:
            title = original
            visited = set()
            while title in alias and title not in visited:
                visited.add(title)
                title = alias[title]
            page = by_title.get(title)
            links = page.get("langlinks", []) if page else []
            if links:
                result[original] = links[0]["title"]
    return result


def validate(data: dict) -> None:
    teams = data["teams"]
    fixtures = data["fixtures"]
    if len(teams) != 36:
        raise ValueError(f"Expected 36 teams, got {len(teams)}")
    if len(fixtures) != 144:
        raise ValueError(f"Expected 144 fixtures, got {len(fixtures)}")
    by_team = defaultdict(list)
    associations = {team["name_zh"]: team["association"] for team in teams.values()}
    pairs = set()
    for fixture in fixtures:
        by_team[fixture["home"]].append(("home", fixture))
        by_team[fixture["away"]].append(("away", fixture))
        pair = tuple(sorted((fixture["home"], fixture["away"])))
        if pair in pairs:
            raise ValueError(f"Duplicate opponents: {pair}")
        pairs.add(pair)
        if associations[fixture["home"]] == associations[fixture["away"]]:
            raise ValueError(f"Same-association fixture: {fixture}")
    for team_name, games in by_team.items():
        venue_count = Counter(venue for venue, _ in games)
        if len(games) != 8 or venue_count != {"home": 4, "away": 4}:
            raise ValueError(f"Invalid schedule for {team_name}: {len(games)} {venue_count}")
    for canonical, team in teams.items():
        if team.get("market_value_m") is None or team.get("world_rank") is None:
            raise ValueError(f"Missing ranking/value for {canonical}")
        if not team.get("managers"):
            raise ValueError(f"Missing manager for {canonical}")
        if not team.get("arrivals") and not team.get("departures"):
            raise ValueError(f"Missing transfer data for {canonical}")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print("读取 UEFA 官方名单与球队档案", flush=True)
    profile_markdown = jina(UEFA_PROFILES)
    profiles = parse_profiles(profile_markdown)
    print(f"UEFA 球队档案: {len(profiles)}", flush=True)
    print("读取 UEFA 官方赛程", flush=True)
    fixture_markdown = jina(UEFA_FIXTURES)
    fixtures = parse_fixtures(fixture_markdown)
    print(f"UEFA 赛程去重后: {len(fixtures)}", flush=True)
    if len(profiles) != 36:
        raise ValueError(f"UEFA profiles parsed {len(profiles)} teams")

    tm_clubs = get_tm_clubs()
    teams: dict[str, dict] = {}
    for canonical, profile in profiles.items():
        tm_name = TM_NAME[canonical]
        if tm_name not in tm_clubs:
            raise ValueError(f"Transfermarkt participant missing: {canonical} -> {tm_name}")
        teams[canonical] = {
            "key": canonical,
            "name_zh": TEAM_ZH[canonical],
            **profile,
            **tm_clubs[tm_name],
        }

    print("读取 Transfermarkt 转会、教练与阵型", flush=True)
    TEAM_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    pending: list[tuple[str, dict]] = []
    for canonical, team in teams.items():
        cache_file = TEAM_CACHE_DIR / f"{normalize_name(canonical)}.json"
        if cache_file.exists():
            detail = json.loads(cache_file.read_text(encoding="utf-8"))
            teams[canonical].update(detail)
            print(f"使用缓存 {canonical}: 转入{len(detail['arrivals'])} 转出{len(detail['departures'])}", flush=True)
        else:
            pending.append((canonical, team))
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(scrape_tm_team, canonical, team) for canonical, team in pending]
        for future in concurrent.futures.as_completed(futures):
            canonical, detail = future.result()
            teams[canonical].update(detail)
            cache_file = TEAM_CACHE_DIR / f"{normalize_name(canonical)}.json"
            cache_file.write_text(json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8")

    print("补充主教练常用阵型", flush=True)
    manager_refs = [team["managers"][0] for team in teams.values() if team.get("managers")]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        formations = list(pool.map(enrich_manager_formation, manager_refs))
    for manager, formation in zip(manager_refs, formations):
        manager["formation"] = formation
        manager["name_zh"] = COACH_ZH.get(manager.get("name", ""), manager.get("name_zh") or manager.get("name"))

    print("读取 FootballDatabase 世界排名", flush=True)
    rankings = get_world_rankings()
    apply_world_rankings(teams, rankings)

    data = {
        "meta": {
            "season": "2026-27",
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "data_date": "2026-09-08",
            "sources": {
                "uefa_fixtures": UEFA_FIXTURES,
                "uefa_profiles": UEFA_PROFILES,
                "uefa_coefficients": UEFA_COEFFICIENTS,
                "transfermarkt_participants": TM_PARTICIPANTS,
                "football_database": "https://footballdatabase.com/ranking/world/1",
            },
        },
        "teams": teams,
        "fixtures": fixtures,
    }
    validate(data)
    output = DATA_DIR / "site_data.json"
    # 先保存全部核心事实。即使可选的中文译名服务限流，成果也不会丢失。
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"核心数据已写入 {output}", flush=True)

    major_player_names = []
    for team in teams.values():
        big_signing = team.get("big_summer_signing")
        for transfer in team["arrivals"] + team["departures"]:
            transfer["player_zh"] = transfer["player"]
            if (transfer.get("fee_m") or 0) >= 10 or transfer["player"] == big_signing:
                major_player_names.append(transfer["player"])
    print(f"非阻塞查询主要交易中文译名: {len(set(major_player_names))}", flush=True)
    zh_titles = wikipedia_zh_titles(major_player_names)
    for team in teams.values():
        for transfer in team["arrivals"] + team["departures"]:
            transfer["player_zh"] = zh_titles.get(transfer["player"], transfer["player"])
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"译名增强完成，已更新 {output}", flush=True)


if __name__ == "__main__":
    main()
