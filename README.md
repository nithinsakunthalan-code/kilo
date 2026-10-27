# KILO: calorie and workout tracker with an AI assistant

KILO is a minimalist Django web app for tracking meals, workouts and daily goals. It has a JSON REST API,
a chat assistant that answers FAQs and explains error codes, and support tickets.

**Live site:** https://YOUR-KILO.onrender.com  <!-- TODO: replace with your HTTPS link after deploying -->
**Health check:** https://YOUR-KILO.onrender.com/health/
**GitHub repository:** https://github.com/nithinsakunthalan-code/kilo

## Requirements checklist

| Requirement | Where |
|---|---|
| Responsive site, 3+ pages, chat widget on every page | Today, Meals, Workouts, Goals, FAQ, Errors, Support, Health, Sign in / up. The widget (`support/templates/support/chat_widget.html`, `support/static/support/chat.js`) is included from `myapp/templates/myapp/base.html`, so it is on every page |
| 10+ FAQs in SQL, shown on the FAQ page | `FAQ` model, 16 rows loaded by `support/migrations/0002_seed_content.py` and `0004_diet_plan_faq.py`, shown at `/faq/` |
| 8+ error codes (400, 401, 403, 404, 429, 500, 503 + site-specific) | `ErrorCode` model, loaded by the same migration, shown at `/errors/`. KILO-specific: **KILO-1001** (invalid chat message) and **KILO-2001** (food lookup fell back to the built-in list) |
| Custom 404 and 500 pages with "Ask the assistant" | `support/templates/404.html`, `500.html` (plus 400 and 403), registered in `myproject/urls.py` |
| Assistant answers from FAQ, explains error codes, creates a ticket when it cannot answer | `support/assistant.py` |
| Tickets in SQL | `Ticket` model (PostgreSQL in production), linked to the signed-in user when there is one |
| Chat logs and feedback in MongoDB | `support/mongo.py` (`chat_logs` and `feedback` collections) |
| API keys in environment variables, none in the repo | `myproject/settings.py` reads everything from the environment. `.env` is git-ignored and `.env.example` holds placeholders only |
| Request logging | `support/middleware.py`: one line per request (id, method, path, status, duration, user, ip) to the console and `logs/requests.log` |
| Health check page | `/health/` (HTML) and `/health/?format=json` |
| Third-party API with a time limit and fallback | `support/foods.py`: **Open Food Facts** powers "Look up food" on the Meals page. 4 s timeout, built-in list of common foods as fallback, results cached |
| README with live link and one proposed improvement | this file |

## What the app does

- **Today**: calorie ring, protein meter, macros, weekly sessions and a 7-day chart.
- **Meals / Workouts**: log, browse by day, delete. Meals can be filled in with **Look up food**.
- **Goals**: daily calories, daily protein, weekly workouts.
- **REST API** under `/api/` with token authentication. See [BACKEND.md](BACKEND.md).
- **Accounts**: every user only sees their own data.

## How the assistant works

1. **Small talk** (hi, thanks, bye): canned reply.
2. **Error code in the message** (e.g. "what does 429 mean"): explanation from the `ErrorCode` table.
3. **Nutrition coach** (`support/coach.py`): diet-plan, calorie and protein questions such as "I weigh 80 kg and want to lose 5 kg in a month" get a worked-out answer with no API key: maintenance calories, a daily calorie and protein target, a safe pace (it flags goals faster than about 1 % of body weight per week and never goes below a calorie floor), a meal split and how to set it on the Goals page. Height, age and sex, if given, make the estimate more accurate.
4. **FAQ search**: words in the question are matched against FAQ questions, keywords and answers (inverse-document-frequency weighted). A strong match is answered straight from the FAQ.
   If `ANTHROPIC_API_KEY` is set, Claude rephrases the answer using *only* the matching FAQ entries, with an 8 s timeout and a plain-FAQ fallback. It replies `NO_ANSWER` when the FAQ does not cover the question.
5. **Other fitness questions**: with `ANTHROPIC_API_KEY` set, Claude gives short general fitness and nutrition guidance. Off-topic questions fall through to a ticket.
6. **Otherwise**: a support ticket is created (`TKT-00012`) and the visitor can attach an email to it from the chat.

Safeguards: messages are limited to 500 characters (`KILO-1001`), 20 messages per minute per IP (`429`), CSRF protection on every POST, chat text is rendered with `textContent` (no HTML injection), IP addresses are stored only as salted hashes, and a MongoDB outage never breaks the chat (30 s circuit breaker).

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
copy .env.example .env            # macOS/Linux: cp .env.example .env  - then edit the values
python manage.py migrate          # creates tables and loads the FAQs and error codes
python manage.py createsuperuser  # optional: manage FAQs and tickets at /admin/
python manage.py runserver
```

Open http://127.0.0.1:8000/ and create an account. Without `MONGODB_URI` the chat works but nothing is logged, and `/health/` reports MongoDB as `not_configured` (status "degraded").

With `DEBUG=1` Django shows its own technical 404 page. To see the custom 404 and 500 pages locally, set `DEBUG=0` and `SECURE_COOKIES=0` in `.env` and run `python manage.py collectstatic` once.

Run the tests (65 tests; MongoDB is simulated with `mongomock`):

```bash
python manage.py test
```

## Deploy (Render, free tier, HTTPS included)

1. Push this repository to GitHub (`.env` and the database are git-ignored).
2. Create a free **MongoDB Atlas** cluster, add a database user, allow network access, and copy the connection string.
3. In Render choose **New, Blueprint** and select the repository. `render.yaml` creates the web service and a PostgreSQL database and generates `SECRET_KEY`.
4. When prompted, set `MONGODB_URI` and, optionally, `ANTHROPIC_API_KEY`.
5. After the first deploy open `https://<your-service>.onrender.com/health/`. It should say **All systems operational**.
6. Put the live URL at the top of this README.

## Verify before submitting

- [ ] Open the live site on a phone: the menu collapses, the chat button opens a near-full-width panel.
- [ ] Visit `/this-page-does-not-exist/`: the custom 404 appears with an **Ask the assistant** button.
- [ ] Ask the chat "what does error 429 mean?", then something unrelated: a ticket number is returned.
- [ ] On the Meals page search "banana" and pick a result: the form fills in.
- [ ] `/health/` shows the database and MongoDB as `ok`.
- [ ] No secrets in the repository: `git grep -iE "mongodb\+srv|sk-ant" -- . ":!README.md" ":!.env.example"` prints nothing.

## Proposed improvement

**Semantic search with embeddings.** The assistant finds FAQs by weighted keyword overlap, so a question phrased with different words ("is my info kept?") can miss the right FAQ and end up as a ticket. Storing an embedding vector per FAQ and ranking by cosine similarity (for example with `pgvector` in the existing PostgreSQL database) would match on meaning instead of exact words. The MongoDB "Not helpful" feedback could then be used to find the questions that most need new FAQ entries.

## Project layout

```
myproject/         settings, URLs, WSGI
myapp/             KILO tracker: models, views, REST API, services, templates
support/           assistant, FAQ, error codes, tickets, health, food lookup
  models.py        FAQ, ErrorCode, Ticket
  assistant.py     retrieval, error-code lookup, LLM call, ticket creation
  coach.py         built-in nutrition coach (calorie / protein plan from weight and goal)
  mongo.py         chat log + feedback storage with circuit breaker
  foods.py         Open Food Facts client (timeout + fallback + cache)
  middleware.py    request logging
  views.py         chat API, health check, food lookup API, error handlers
render.yaml        Render blueprint (web service + PostgreSQL)
```
