# Pars — football fixtures & results widget for KDE Plasma 6

<img src="branding/final/logo-256.png" alt="Pars logo" width="200">

A minimal plasmoid that shows recent results and upcoming fixtures for one competition at a time. Currently tracking the **2026 FIFA World Cup**.

![Pars widget](screenshots/main.png)

## How it works

The widget is intentionally dumb: it fetches a single static JSON file over HTTPS and renders it. All the intelligence (data collection, formatting, scheduling) lives on the producer side. This cache-proxy design means:

- **Zero per-user API cost** — thousands of users hit one cached JSON file, not a sports API.
- **Swappable data source** — the feed can be maintained by hand, by a cron script, or by anything that writes valid JSON. The widget never changes.
- **Tiny footprint** — one QML file, no daemons, no dependencies beyond Plasma 6 itself.

The feed currently lives in this repo and is served via GitHub raw (`data/worldcup.json`), refreshed by the widget every 30 minutes.

On the producer side, `producer/update_feed.py` merges live results from the free [TheSportsDB](https://www.thesportsdb.com) API into the curated bracket and pushes on change (a systemd timer runs it every 10 minutes). Scores are **near-live**: the free API tier does not stream in-play scores, so a match result typically appears shortly after full-time rather than minute-by-minute.

## Feed schema

```json
{
  "league": "Display name shown as the widget title",
  "updated": "2026-07-16",
  "matches": [
    { "home": "Spain", "away": "Argentina", "score": "–", "info": "FINAL · Jul 19" }
  ]
}
```

`score` is a preformatted string ("2 - 1" or "–" for unplayed). `info` is a free-form line (round, date, kickoff time). The producer formats; the widget displays.

## Install

```bash
git clone https://github.com/parsapp/pars-plasmoid
kpackagetool6 --type Plasma/Applet --install pars-plasmoid/package
```

Then right-click your desktop or panel → *Add Widgets* → search for **Pars**.

To update an existing install: `kpackagetool6 --type Plasma/Applet --upgrade pars-plasmoid/package`

For development, run it standalone without installing:

```bash
plasmoidviewer --applet pars-plasmoid/package
```

## Roadmap

- [x] Remote JSON feed with 30-min auto-refresh
- [ ] Settings page: choose competition / custom feed URL
- [ ] Compact panel representation (icon + next kickoff)
- [ ] Turkish Süper Lig feed (new season)
- [ ] Automated feed producer (daily cron)
- [ ] Publish on store.kde.org

## License

MIT
