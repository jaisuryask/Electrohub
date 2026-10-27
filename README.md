# ElectroLab

Django web app for embedded-systems & IoT projects: descriptions, parts lists, auto-drawn wiring diagrams,
copy/download code, step-by-step instructions, embedded YouTube tutorials and an AI mentor.

## Run

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed          # loads 6 starter projects (safe to re-run)
python manage.py createsuperuser   # optional, for /admin/
python manage.py runserver
```

Open http://127.0.0.1:8000

## AI features (free models, server-side)

The browser only calls this Django backend (`/api/ai/*`). The backend calls the free model, so no API key
ever reaches the website. With no keys it uses the keyless Pollinations model; add a free Groq or Gemini key
in `.env` (see `.env.example`) for faster answers. If all providers fail, a built-in local engine answers.

| Feature | Where | Backend |
|---|---|---|
| Project assistant (chat) | floating button on every page | `hub/ai.py: ask()` |
| Semantic search | nav bar, `/projects/?q=` | TF-IDF in `hub/ai.py: search()` |
| Part Finder | `/ai-lab/` | `hub/ai.py: recommend()` |
| Troubleshooter | `/ai-lab/`, project → AI help | `hub/ai.py: troubleshoot()` |
| Code explainer | project → Code → “Explain with AI” | `hub/ai.py: explain_code()` |

## Backend map

`electrolab/` settings + URLs · `hub/models.py` database · `hub/views.py` pages + JSON API ·
`hub/ai.py` AI engine · `hub/diagram.py` wiring SVG · `hub/seed_data.py` starter content.

## API

`GET /api/projects/`, `GET /api/search/?q=`, `POST /api/ai/chat|recommend|troubleshoot/`, `POST /api/ai/explain/<id>/`.

## Add projects

Use `/admin/` (inline parts, wiring, code files, steps) or extend `hub/seed_data.py`.
