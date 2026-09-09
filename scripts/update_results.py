"""从 UEFA 官方 JSON 接口同步已结束赛果和联赛阶段积分榜。"""

from __future__ import annotations

import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "site_data.json"
RESULTS_PATH = ROOT / "data" / "results.json"
MATCHES_API = "https://match.uefa.com/v5/matches?competitionId=1&seasonYear=2027&phase=TOURNAMENT&order=DESC&offset=0&limit=200"
STANDINGS_API = "https://standings.uefa.com/v1/standings?competitionId=1&seasonYear=2027"
MATCHSTATS_API = "https://matchstats.uefa.com/v1/team-statistics/{match_id}"
LINEUPS_API = "https://match.uefa.com/v5/matches/{match_id}/lineups"


def fetch_json(url: str) -> object:
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "UCL-2026-27-static-site/1.0", "Accept": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=45) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"UEFA API unavailable: {url}: {last_error}")


def simplify_stats(payload: object) -> dict:
    allowed = {"goals", "attempts", "attempts_on_target", "ball_possession", "passes_accuracy", "saves", "corners", "fouls_committed", "yellow_cards", "red_cards", "tackles", "clearances", "interceptions", "blocks"}
    rows = []
    for item in payload if isinstance(payload, list) else []:
        values = {}
        for stat in item.get("statistics", []):
            name = stat.get("name")
            if name in allowed:
                raw = stat.get("value")
                try:
                    values[name] = float(raw) if "." in str(raw) else int(raw)
                except (TypeError, ValueError):
                    values[name] = raw
        rows.append({"team_id": str(item.get("teamId", "")), "stats": values})
    return {row["team_id"]: row["stats"] for row in rows if row["team_id"]}


def simplify_lineups(payload: object) -> dict:
    result = {}
    if not isinstance(payload, dict):
        return result
    for side in ("homeTeam", "awayTeam"):
        team = payload.get(side) or {}
        field = team.get("field") or []
        result["home" if side == "homeTeam" else "away"] = {
            "starting_count": len(field),
            "coaches": [c.get("person", {}).get("internationalName") or c.get("name") for c in team.get("coaches", []) if c.get("role") == "COACH"],
            "lineup_status": team.get("lineupStatus"),
        }
    return result


def fetch_report(match: dict) -> tuple[str, dict]:
    match_id = str(match["id"])
    stats_url = MATCHSTATS_API.format(match_id=match_id)
    lineups_url = LINEUPS_API.format(match_id=match_id)
    try:
        stats = simplify_stats(fetch_json(stats_url))
    except Exception:
        stats = {}
    try:
        lineups = simplify_lineups(fetch_json(lineups_url))
    except Exception:
        lineups = {}
    home_id = str((match.get("homeTeam") or {}).get("id", ""))
    away_id = str((match.get("awayTeam") or {}).get("id", ""))
    return match_id, {
        "home_stats": stats.get(home_id, {}), "away_stats": stats.get(away_id, {}),
        "lineups": lineups,
        "injuries": {"home": "本场未见官方伤停通报", "away": "本场未见官方伤停通报"},
        "source_urls": {"stats": stats_url, "lineups": lineups_url},
    }


def main() -> None:
    site_data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    team_keys = set(site_data["teams"])
    aliases = {
        "Manchester City": "Man City", "Manchester United": "Man United",
        "Atlético de Madrid": "Atleti", "Paris Saint-Germain": "Paris",
        "PSV Eindhoven": "PSV", "Shakhtar Donetsk": "Shakhtar",
        "Bayern Munich": "Bayern München", "RB Leipzig": "Leipzig",
        "Inter Milan": "Inter", "AS Roma": "Roma", "SSC Napoli": "Napoli",
        "Slavia Prague": "Slavia Praha", "Sporting CP": "Sporting CP",
        "Club Brugge": "Club Brugge", "AEK Athens": "AEK Athens",
        "B. Dortmund": "Borussia Dortmund", "Man Utd": "Man United",
    }

    matches = fetch_json(MATCHES_API)
    results: dict[str, dict] = {}
    finished_matches: dict[str, dict] = {}
    for match in matches if isinstance(matches, list) else []:
        score = match.get("score") or {}
        total = score.get("total") or score.get("regular") or {}
        status = match.get("status")
        if status not in {"FINISHED", "AWARDED"} or total.get("home") is None or total.get("away") is None:
            continue
        home_raw = (match.get("homeTeam") or {}).get("internationalName", "")
        away_raw = (match.get("awayTeam") or {}).get("internationalName", "")
        home_key = aliases.get(home_raw, home_raw)
        away_key = aliases.get(away_raw, away_raw)
        if home_key not in team_keys or away_key not in team_keys:
            continue
        results[str(match["id"])] = {
            "id": str(match["id"]),
            "date": (match.get("kickOffTime") or {}).get("date"),
            "home_en": home_key,
            "away_en": away_key,
            "home_score": int(total["home"]),
            "away_score": int(total["away"]),
            "status": status,
            "source_url": f"https://www.uefa.com/uefachampionsleague/match/{match['id']}/",
        }
        finished_matches[str(match["id"])] = match

    reports: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(fetch_report, match) for match in finished_matches.values()]
        for future in as_completed(futures):
            match_id, report = future.result()
            reports[match_id] = report

    standings_payload = fetch_json(STANDINGS_API)
    items = standings_payload[0].get("items", []) if isinstance(standings_payload, list) and standings_payload else []
    standings: list[dict] = []
    for item in items:
        team = item.get("team") or {}
        raw_name = team.get("internationalName", "")
        key = aliases.get(raw_name, raw_name)
        if key not in team_keys:
            continue
        standings.append({
            "key": key,
            "rank": int(item.get("rank", 0)),
            "played": int(item.get("played", 0)),
            "won": int(item.get("won", 0)),
            "drawn": int(item.get("drawn", 0)),
            "lost": int(item.get("lost", 0)),
            "goals_for": int(item.get("goalsFor", 0)),
            "goals_against": int(item.get("goalsAgainst", 0)),
            "goal_difference": int(item.get("goalDifference", 0)),
            "points": int(item.get("points", 0)),
        })
    standings.sort(key=lambda row: (row["rank"] if row["played"] else 999, row["key"]))
    old_payload = json.loads(RESULTS_PATH.read_text(encoding="utf-8")) if RESULTS_PATH.exists() else {}
    content = {"results": results, "standings": standings, "reports": reports}
    old_content = {"results": old_payload.get("results", {}), "standings": old_payload.get("standings", []), "reports": old_payload.get("reports", {})}
    updated_at = old_payload.get("meta", {}).get("updated_at") if content == old_content else datetime.now().astimezone().isoformat(timespec="seconds")
    payload = {
        "meta": {
            "updated_at": updated_at or datetime.now().astimezone().isoformat(timespec="seconds"),
            "matches_source": MATCHES_API,
            "standings_source": STANDINGS_API,
            "completed_matches": len(results),
        },
        "results": results,
        "standings": standings,
        "reports": reports,
    }
    RESULTS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已同步 UEFA 官方赛果 {len(results)} 场、积分榜 {len(standings)} 队")


if __name__ == "__main__":
    main()
