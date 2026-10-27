# ElectroLab — Embedded & IoT Project Hub with an AI Support Assistant

**Live site (HTTPS):** https://electrolab-lu87.onrender.com
**Repository:** https://github.com/jaisuryask/Electrohub

ElectroLab is a Django website with embedded-systems and IoT projects (ESP32, Arduino, Raspberry Pi Pico): parts lists,
auto-drawn wiring diagrams, copy/download code, step-by-step instructions and YouTube tutorials. A chat assistant on
every page answers from the FAQ, explains error codes and opens a support ticket when it cannot answer.

> The free Render plan sleeps when idle — the first request can take ~30 seconds.

## Pages
| Page | URL |
|---|---|
| Home / Projects / Project detail | `/`, `/projects/`, `/projects/<slug>/` |
| AI Lab (part finder, troubleshooter, search) | `/ai-lab/` |
| FAQ (13 questions, from SQL) | `/faq/` |
| Error codes (9, from SQL) | `/errors/` |
| Support (create / check tickets) | `/support/` |
| Health check (HTML or `?format=json`) | `/health/` |
| Custom 404 and 500 pages (with “Ask the assistant”) | any wrong address |

The chat widget (bottom-right) is on every page. Layout is responsive and uses a light theme.

## How the assistant answers
1. Greeting → friendly reply.
2. Error code or name (`404`, `429`, `EL-1001`, “Not Found”) → explanation from the `ErrorCode` table.
3. FAQ match (TF-IDF similarity over the `FAQ` table) → the stored answer.
4. Project question → answer from that project’s guide.
5. A free AI model (**Groq or Gemini free-tier key recommended**; the keyless fallback allows only 1 reply per 30 s per IP) answers **only** from FAQ + error-code + project context, or replies `CANNOT_ANSWER`.
6. Otherwise a **support ticket** (`ELT-0007`) is created in SQL; the user may add an email.

Users can rate every answer 👍/👎.

## Data stores
| Data | Store |
|---|---|
| Projects, FAQs, error codes, **support tickets** | SQL (SQLite via Django ORM) |
| **Chat logs and feedback** | **MongoDB** (`chat_logs`, `feedback` collections) |

If `MONGODB_URI` is missing or unreachable, documents are written to a local `.fallback/*.jsonl` file so the site keeps
working; `/health/` shows `mongodb` as degraded until it is connected.

## Requirements checklist
- Responsive, ≥3 pages, chat widget everywhere ✔
- ≥10 FAQs in SQL, shown on `/faq/` ✔ (13)
- ≥8 error codes: 400, 401, 403, 404, 429, 500, 503 + site-specific `EL-1001` (and `EL-2001`) ✔
- Custom 404 / 500 with “Ask the assistant” ✔
- Assistant: FAQ answers, error explanations, ticket creation ✔
- Tickets in SQL; chat logs + feedback in MongoDB ✔
- Secrets only in environment variables (`.env` is git-ignored; see `.env.example`) ✔
- Request logging (stdout, visible in Render Logs) + `/health/` ✔
- Extra third-party API with time limit + fallback: **YouTube oEmbed** (3 s timeout; falls back to the stored video credit) ✔
- Rate limiting: 20 AI requests / minute / IP → HTTP 429 ✔

## Run locally
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed            # projects, FAQs, error codes
python manage.py runserver
```
Copy `.env.example` to `.env` to set `MONGODB_URI` and optional AI keys.

## Deploy (Render)
Push to `main`; `render.yaml` + `build.sh` handle the build. Under **Environment** add `MONGODB_URI`
(free MongoDB Atlas cluster) and optionally `GROQ_API_KEY` / `GEMINI_API_KEY`. `DJANGO_SECRET_KEY` is generated.

## Backend map
`hub/models.py` data · `hub/views.py` pages + JSON API · `hub/assistant.py` support assistant ·
`hub/ai.py` AI providers + project search · `hub/mongo.py` MongoDB · `hub/middleware.py` request log + rate limit ·
`hub/integrations.py` YouTube oEmbed · `hub/faq_data.py`, `hub/seed_data.py` content.

## Proposed improvement
**Turn unanswered questions into new FAQs.** Tickets created by the assistant already record what users asked that the
FAQ could not answer. A staff view in `/admin/` could cluster these tickets by similarity, draft a suggested FAQ answer with the
AI model, and let an admin approve it in one click — so every unanswered question permanently improves the assistant and
reduces future tickets. Replacing the in-memory rate limiter with Redis would also make limits consistent across multiple servers.
