# ASCIT31/.github

Default community health files and the organization profile shown at [github.com/ASCIT31](https://github.com/ASCIT31).

| Path | Purpose |
|---|---|
| `profile/README.md` | The organization profile page |
| `profile/assets/` | Self-hosted SVG artwork (hero, banners, stats tiles, repo cards, team avatars, logos). No third-party widget can break the page. |
| `profile/fonts/` | Brand fonts used to render text as paths (all SIL Open Font License) |
| `profile/data/stats.json` | Live numbers fetched from the GitHub API, refreshed daily |
| `scripts/build_assets.py` | Generator for everything in `profile/assets/` |
| `.github/workflows/refresh-profile.yml` | Daily job that regenerates the stats tiles and repo cards |
| `SECURITY.md`, `CODE_OF_CONDUCT.md` | Organization-wide defaults |

Regenerate locally:

```bash
pip install fonttools
GITHUB_TOKEN=$(gh auth token) python3 scripts/build_assets.py
```
