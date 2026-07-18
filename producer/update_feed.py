#!/usr/bin/env python3
"""Pars feed producer — MERGE mode.

Keeps the curated match bracket in data/worldcup.json as the static source of
truth and only *merges* live facts from the free TheSportsDB v1 API into it:

  * a finished API result fills the score of the matching curated row
    ("–" -> "H - A"); it never rewrites round labels or reorders history,
  * the API's next fixture refreshes the top-level "next" line (and is
    appended as a new row only if it is genuinely absent from the bracket).

Matching is by team name, mapping the API's English names to our Turkish ones
(Spain=İspanya, Argentina=Arjantin, France=Fransa, England=İngiltere, ...).

Design rules:
- Single official source: TheSportsDB v1 (free test key "123"). No scraping.
- Never regenerate from scratch: the curated bracket must already exist.
- Fail loud: on any network / parse error the script raises and exits non-zero
  WITHOUT touching the existing JSON (atomic temp+rename, no partial writes).
- Commit+push only when the merged content actually changed.

Note: on the free tier live scores are not streamed; a result typically lands
shortly after full-time (see README, "near-live").
"""

import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------
API_KEY = "123"                       # TheSportsDB free test key
LEAGUE_ID = "4429"                    # FIFA World Cup
LEAGUE_TITLE = "Dünya Kupası 2026"    # widget title (feed "league" field)
BASE = f"https://www.thesportsdb.com/api/v1/json/{API_KEY}"
TIMEOUT = 20                          # seconds per request
TR = timezone(timedelta(hours=3))     # Turkey time (UTC+3, no DST)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEED_PATH = os.path.join(REPO, "data", "worldcup.json")

TR_MONTHS = ["", "Oca", "Şub", "Mar", "Nis", "May", "Haz",
             "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
TR_DAYS = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]

# Round labels keyed by intRound (TheSportsDB soccer coding) — only used when
# appending a genuinely new fixture; curated rows keep their own labels.
ROUND_TR = {1: "Grup", 2: "Grup", 3: "Grup", 125: "Final", 150: "Yarı Final",
            160: "Çeyrek Final", 170: "Son 16", 180: "Son 32", 200: "Son 16"}

# API English nation name -> our Turkish name. Falls back to the API name.
TR_COUNTRIES = {
    "Argentina": "Arjantin", "Australia": "Avustralya", "Austria": "Avusturya",
    "Belgium": "Belçika", "Bosnia-Herzegovina": "Bosna-Hersek", "Brazil": "Brezilya",
    "Cameroon": "Kamerun", "Canada": "Kanada", "Cape Verde": "Yeşil Burun",
    "Chile": "Şili", "Colombia": "Kolombiya", "Costa Rica": "Kosta Rika",
    "Croatia": "Hırvatistan", "Curaçao": "Curaçao", "Czech Republic": "Çekya",
    "Denmark": "Danimarka", "Ecuador": "Ekvador", "Egypt": "Mısır",
    "England": "İngiltere", "France": "Fransa", "Germany": "Almanya",
    "Ghana": "Gana", "Greece": "Yunanistan", "Haiti": "Haiti",
    "Honduras": "Honduras", "Iceland": "İzlanda", "Iran": "İran",
    "Italy": "İtalya", "Ivory Coast": "Fildişi Sahili", "Jamaica": "Jamaika",
    "Japan": "Japonya", "Mexico": "Meksika", "Morocco": "Fas",
    "Netherlands": "Hollanda", "New Zealand": "Yeni Zelanda", "Nigeria": "Nijerya",
    "Norway": "Norveç", "Panama": "Panama", "Paraguay": "Paraguay",
    "Peru": "Peru", "Poland": "Polonya", "Portugal": "Portekiz",
    "Qatar": "Katar", "Saudi Arabia": "Suudi Arabistan", "Scotland": "İskoçya",
    "Senegal": "Senegal", "Serbia": "Sırbistan", "Slovenia": "Slovenya",
    "South Africa": "Güney Afrika", "South Korea": "Güney Kore", "Spain": "İspanya",
    "Sweden": "İsveç", "Switzerland": "İsviçre", "Tunisia": "Tunus",
    "Turkey": "Türkiye", "Türkiye": "Türkiye", "Ukraine": "Ukrayna",
    "United States": "ABD", "USA": "ABD", "Uruguay": "Uruguay", "Wales": "Galler",
}


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def fetch(path):
    """GET a TheSportsDB endpoint, return parsed JSON. Raise on any problem."""
    url = f"{BASE}/{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "pars-feed/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        if r.status != 200:
            raise RuntimeError(f"HTTP {r.status} for {url}")
        raw = r.read().decode("utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Non-JSON response from {url}: {raw[:120]!r}") from e


def tr_team(name):
    return TR_COUNTRIES.get((name or "").strip(), (name or "?").strip())


def event_dt(e):
    """Event kickoff as Turkey-time datetime (from UTC timestamp), or None."""
    ts = e.get("strTimestamp")
    if ts:
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(TR)
        except ValueError:
            pass
    date, t = e.get("dateEvent"), (e.get("strTime") or "00:00:00")
    if date:
        try:
            return datetime.fromisoformat(f"{date}T{t[:8]}").replace(
                tzinfo=timezone.utc).astimezone(TR)
        except ValueError:
            return None
    return None


def round_label(e):
    try:
        ir = int(e.get("intRound"))
    except (TypeError, ValueError):
        ir = None
    sr = (e.get("strRound") or "").strip()
    if ir in ROUND_TR:
        return ROUND_TR[ir]
    if sr:
        return sr
    if ir is not None:
        return "Grup" if ir < 100 else f"Tur {ir}"
    return "Maç"


def curated_round(info):
    """Round label from an existing curated row's info (before the ' · ')."""
    return (info or "").split(" · ", 1)[0].strip()


def scored(e):
    hs, as_ = e.get("intHomeScore"), e.get("intAwayScore")
    return (hs, as_) if (hs is not None and as_ is not None) else None


# ----------------------------------------------------------------------------
# Merge
# ----------------------------------------------------------------------------
def merge(feed, past, nxt):
    """Mutate feed in place from API events. Return a list of change-log lines."""
    log = []
    fwd = {(m["home"], m["away"]): m for m in feed["matches"]}
    rev = {(m["away"], m["home"]): m for m in feed["matches"]}

    # PAST results -> fill the score of the matching curated row.
    for e in past:
        sc = scored(e)
        if not sc:
            continue
        hs, as_ = sc
        h, a = tr_team(e.get("strHomeTeam")), tr_team(e.get("strAwayTeam"))
        if (h, a) in fwd:
            row, new = fwd[(h, a)], f"{hs} - {as_}"
        elif (h, a) in rev:                       # listed in opposite order
            row, new = rev[(h, a)], f"{as_} - {hs}"
        else:
            log.append(f"past {h}-{a} {hs}-{as_}: bracket'te yok, atlandı")
            continue
        if row["score"] != new:
            log.append(f"fill {row['home']}-{row['away']}: '{row['score']}' -> '{new}'")
            row["score"] = new
        else:
            log.append(f"match {row['home']}-{row['away']}: skor zaten '{new}' (doğrulandı)")

    # NEXT fixture -> refresh top-level "next" (append only if truly missing).
    if nxt:
        e = nxt[0]
        h, a = tr_team(e.get("strHomeTeam")), tr_team(e.get("strAwayTeam"))
        dt = event_dt(e)
        if (h, a) in fwd:
            rnd = curated_round(fwd[(h, a)]["info"])
        elif (h, a) in rev:
            rnd = curated_round(rev[(h, a)]["info"])
        else:
            rnd = round_label(e)
            info = (f"{rnd} · {dt.day} {TR_MONTHS[dt.month]} {dt:%H:%M}"
                    if dt else rnd)
            feed["matches"].append({"home": h, "away": a, "score": "–", "info": info})
            log.append(f"next {h}-{a}: bracket'te yoktu, eklendi ({info})")
        when = f"{TR_DAYS[dt.weekday()]} {dt:%H:%M}" if dt else ""
        nt = f"{rnd} · {when}".strip(" ·")
        if nt and feed.get("next") != nt:
            log.append(f"next alanı: '{feed.get('next')}' -> '{nt}'")
            feed["next"] = nt
    return log


def meaningful(feed):
    """Parts we diff on (everything except the volatile 'updated' date)."""
    return {k: feed.get(k) for k in ("league", "next", "matches")}


def git(*args):
    return subprocess.run(["git", "-C", REPO, *args],
                          check=True, capture_output=True, text=True)


def main():
    if not os.path.exists(FEED_PATH):
        raise RuntimeError(f"{FEED_PATH} yok — merge tabanı gerekli, "
                           "sıfırdan üretmiyorum.")
    feed = json.load(open(FEED_PATH, encoding="utf-8"))
    original = json.loads(json.dumps(feed))          # deep copy for diffing
    if not feed.get("matches"):
        raise RuntimeError("Curated bracket boş; merge tabanı geçersiz.")

    past = fetch(f"eventspastleague.php?id={LEAGUE_ID}").get("events") or []
    nxt = fetch(f"eventsnextleague.php?id={LEAGUE_ID}").get("events") or []
    for line in merge(feed, past, nxt):
        print("  merge:", line)

    if meaningful(original) == meaningful(feed):
        print("No change; feed already up to date.")
        return 0

    feed["updated"] = datetime.now(TR).strftime("%Y-%m-%d")
    tmp = FEED_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(feed, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, FEED_PATH)
    print(f"Feed merged: {len(feed['matches'])} matches, next='{feed['next']}'")

    git("add", "data/worldcup.json")
    if subprocess.run(["git", "-C", REPO, "diff", "--cached", "--quiet",
                       "--", "data/worldcup.json"]).returncode == 0:
        print("Merged feed already matches HEAD; nothing to commit.")
        return 0
    stamp = datetime.now(TR).strftime("%Y-%m-%d %H:%M")
    git("commit", "-m", f"Auto feed update {stamp}")
    git("push", "origin", "HEAD")
    print(f"Committed + pushed at {stamp}.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # fail loud, leave existing JSON untouched
        print(f"update_feed failed: {exc}", file=sys.stderr)
        sys.exit(1)
