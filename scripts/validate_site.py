from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "site_data.json"


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    teams = data["teams"]
    fixtures = data["fixtures"]
    assert len(teams) == 36, len(teams)
    assert len(fixtures) == 144, len(fixtures)
    names = {team["name_zh"] for team in teams.values()}
    associations = {team["name_zh"]: team["association"] for team in teams.values()}
    by_team: dict[str, list[tuple[str, str]]] = defaultdict(list)
    pairs: set[tuple[str, str]] = set()
    for game in fixtures:
        assert game["date"] and game["source_url"].startswith("https://www.uefa.com/")
        assert game["home"] in names and game["away"] in names
        assert associations[game["home"]] != associations[game["away"]]
        pair = tuple(sorted((game["home"], game["away"])))
        assert pair not in pairs, pair
        pairs.add(pair)
        by_team[game["home"]].append(("主", game["away"]))
        by_team[game["away"]].append(("客", game["home"]))
    for name in names:
        venues = Counter(side for side, _ in by_team[name])
        opponents = [opponent for _, opponent in by_team[name]]
        assert len(opponents) == 8 and len(set(opponents)) == 8
        assert venues == {"主": 4, "客": 4}, (name, venues)

    pages = sorted((ROOT / "teams").glob("*.html"))
    assert len(pages) == 36, len(pages)
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    parser = LinkParser()
    parser.feed(index)
    team_links = [link for link in parser.links if link.startswith("teams/")]
    unique_team_links = set(team_links)
    assert len(unique_team_links) == 36
    assert len(team_links) > 36, "首页应同时包含球队入口与本月赛程跳转"
    for link in unique_team_links:
        assert (ROOT / link).exists(), link

    forbidden = re.compile(r"待核|实力评分|出线概率|赛程难度|胜率预测|夺冠概率")
    for page in [ROOT / "index.html", *pages]:
        text = page.read_text(encoding="utf-8")
        assert not forbidden.search(text), page
        if page.parent.name == "teams":
            assert text.count('class="fixture"') == 8, page
            assert "轮次" not in text, page
            assert "€" in text and "现任主教练" in text and "转会明细" in text
    for team in teams.values():
        assert team["arrivals"] and team["departures"]
        assert team["managers"] and team["market_value_m"] and team["world_rank"]
        for item in team["arrivals"] + team["departures"]:
            assert item["source_url"].startswith("http")
            assert item["position_zh"] and item["impact"]
            if item["fee_m"] is not None:
                assert isinstance(item["fee_m"], (int, float))
    print("通过：36队、144场、每队8场/4主4客、无同协会与重复对阵、36个子页面、转会教练与禁用词检查")


if __name__ == "__main__":
    main()
