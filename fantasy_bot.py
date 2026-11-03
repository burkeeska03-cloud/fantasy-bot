#!/usr/bin/env python3
"""Post current ESPN Fantasy Football matchups to a GroupMe bot.

Runs locally with ``python3 fantasy_bot.py --post`` and on AWS Lambda via
``lambda_handler``.  It depends only on Python's standard library.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SECRET_KEYS = {"ESPN_LEAGUE_ID", "ESPN_SEASON", "ESPN_SWID", "ESPN_S2", "GROUPME_BOT_ID"}
_ssm_parameter_loaded = False


def load_env(path: Path = ROOT / ".env") -> None:
    """Load simple KEY=value values for local use; Lambda uses its environment."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing {name}. Add it to .env or Lambda configuration.")
    return value


def load_ssm_parameter() -> None:
    """Load private configuration from one SecureString SSM parameter in Lambda."""
    global _ssm_parameter_loaded
    if _ssm_parameter_loaded:
        return

    parameter_name = os.getenv("SSM_PARAMETER_NAME", "").strip()
    if not parameter_name:
        return

    try:
        import boto3

        response = boto3.client("ssm").get_parameter(
            Name=parameter_name, WithDecryption=True
        )
        values = json.loads(response["Parameter"]["Value"])
    except (ImportError, KeyError, TypeError, ValueError) as error:
        raise RuntimeError("Could not load the SSM Parameter Store configuration.") from error
    except Exception as error:
        raise RuntimeError("Could not retrieve the SSM Parameter Store configuration.") from error

    if not isinstance(values, dict):
        raise RuntimeError("The SSM parameter value must be a JSON object.")
    for key in SECRET_KEYS:
        value = values.get(key)
        if value is not None:
            os.environ.setdefault(key, str(value))
    _ssm_parameter_loaded = True


def espn_league() -> dict:
    league_id = require("ESPN_LEAGUE_ID")
    season = require("ESPN_SEASON")
    swid = require("ESPN_SWID")
    espn_s2 = require("ESPN_S2")
    base = (
        "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/"
        f"seasons/{urllib.parse.quote(season)}/segments/0/leagues/"
        f"{urllib.parse.quote(league_id)}"
    )
    query = urllib.parse.urlencode([("view", "mMatchup"), ("view", "mTeam")])
    request = urllib.request.Request(
        f"{base}?{query}",
        headers={
            "Accept": "application/json",
            "User-Agent": "ESPN-Fantasy-GroupMe-Bot/1.0",
            "Cookie": f"SWID={swid}; espn_s2={espn_s2}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code in (401, 403):
            raise RuntimeError(
                "ESPN rejected the request. Refresh ESPN_SWID and ESPN_S2."
            ) from error
        raise RuntimeError(f"ESPN request failed: HTTP {error.code}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Could not reach ESPN: {error.reason}") from error


def team_name(team: dict) -> str:
    name = str(team.get("name", "")).strip()
    if not name:
        name = " ".join(
            filter(None, [team.get("location", ""), team.get("nickname", "")])
        ).strip()
    return name or f"Team {team.get('id', '?')}"


def score(value: object) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "0.00"


def matchup_message(league: dict) -> str:
    teams = {team.get("id"): team_name(team) for team in league.get("teams", [])}
    week = league.get("scoringPeriodId", "?")
    matchups = [
        matchup
        for matchup in league.get("schedule", [])
        if matchup.get("matchupPeriodId") == week
    ]
    if not matchups:
        return f"🏈 ESPN Fantasy Football — Week {week}\nNo current matchups found."

    lines = [f"🏈 ESPN Fantasy Football — Week {week}"]
    for matchup in matchups:
        home = matchup.get("home", {})
        away = matchup.get("away", {})
        if not home or not away:
            continue
        away_name = teams.get(away.get("teamId"), f"Team {away.get('teamId', '?')}")
        home_name = teams.get(home.get("teamId"), f"Team {home.get('teamId', '?')}")
        lines.append(
            f"{away_name} {score(away.get('totalPoints'))} — "
            f"{home_name} {score(home.get('totalPoints'))}"
        )
    return "\n".join(lines)


def post_groupme(message: str) -> None:
    payload = json.dumps({"bot_id": require("GROUPME_BOT_ID"), "text": message}).encode(
        "utf-8"
    )
    request = urllib.request.Request(
        "https://api.groupme.com/v3/bots/post",
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "ESPN-Fantasy-GroupMe-Bot/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.status not in (200, 201, 202):
                raise RuntimeError(f"GroupMe returned HTTP {response.status}")
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"GroupMe rejected the post: HTTP {error.code}") from error


def lambda_handler(event: dict, context: object) -> dict:
    """AWS Lambda entry point: fetch and post one matchup update."""
    load_ssm_parameter()
    message = matchup_message(espn_league())
    post_groupme(message)
    print(message)
    return {"statusCode": 200, "body": "Posted current-week matchup report."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--post", action="store_true", help="Send the report to GroupMe.")
    args = parser.parse_args()
    load_env()
    try:
        message = matchup_message(espn_league())
        if args.post:
            post_groupme(message)
            print("Posted current-week matchup report to GroupMe.")
        else:
            print(message)
            print("\nDry run only. Add --post to send this message to GroupMe.")
    except (ValueError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
