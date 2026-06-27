# odoo-social

Social media management for Odoo Community Edition — built by Vertel AB (AGPL-3).

## Modules

| Module | Description | Auto-install |
|---|---|---|
| `social_marketing` | Core — posts, accounts, streams, UTM tracking | No |
| `social_marketing_linkedin` | LinkedIn — official API, cookie-based, Playwright browser automation | Yes |
| `social_marketing_facebook` | Facebook — Graph API publishing, inbox, stream | No |
| `social_marketing_instagram` | Instagram — Graph API publishing (2-step), inbox, stream | No |
| `social_planner` | Communication planning, policy, approval, AI, competitor analysis, unified inbox | No |

## Dependencies

```bash
# Core (installed by Odoo)
# requests

# LinkedIn — cookie-based auth
pip install linkedin-api

# LinkedIn — Playwright browser automation
pip install playwright && playwright install chromium
```

## Branch Compatibility

- **18.0** — Odoo 18 Community Edition

## License

AGPL-3 — Vertel AB
