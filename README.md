# Campus Customs — Homework 4

A Yale apparel shop website with an AI shopping assistant, **Handsome Dan**.

- **Frontend:** React + Vite + TypeScript
- **Backend:** Python FastAPI
- **Assistant:** a PydanticAI agent using OpenAI's `gpt-5.6-luna` through Portkey. It answers stock and price questions from the shop database, shows search results on the page, and remembers logged-in customers.

## What's in this folder

| Path | Contents |
|---|---|
| `frontend/` | React + Vite + TypeScript website |
| `backend/` | FastAPI app. `main.py` (API), `agent.py` (PydanticAI agent), `models.py` (Pydantic types), `tools.py` (agent tools), `prompts/prompt.md` (system prompt + safety rules), plus `auth.py`, `security.py`, `chat_history.py`, `model_usage.py`, `audit.py` |
| `output/` | `harness.md` (how the system works: start here), `usability.md`, `design.md`, `app_check.html` + `app_check_images/` (tested screenshots), `audit_trail.json` (append-only agent log) |
| `AI_prompts.md` | The prompts used for each problem |
| `requirements.txt` | Python packages for the backend |
| `.env.example` | Template for the API key file |

**Not included** (see `.gitignore`): `.env` (secret key), the database `campus_customs.db`, and the product images. You add these yourself, as described below.

## Requirements
- **Python 3.11+** (tested with 3.14)
- **Node.js 20.19+** (tested with 24)
- A **Portkey API key** with access to OpenAI models

## 1. Place the data pack

Unzip the course data pack (`data.zip`) **inside this `hw4/` folder**, so you end up with:

```
hw4/
└── data/
    ├── campus_customs.db
    └── products/          (102 product .jpg images)
```

```bash
cd hw4
unzip data.zip            # creates hw4/data/
```

The backend reads `hw4/data/campus_customs.db` and serves images from `hw4/data/products/`. When it starts, it adds a few tables it needs (`sessions`, `chat_usage`) to the database; existing data isn't changed.

## 2. Add your API key

```bash
cd hw4
cp .env.example .env
```

Then open `.env` and replace `your-portkey-api-key-here` with your Portkey key. The key is read by `backend/agent.py` and is never sent to the browser.

## 3. Run the backend (terminal 1)

```bash
cd hw4/backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r ../requirements.txt
uvicorn main:app --reload --port 8000
```

You should see `Chat model: gpt-5.6-luna … cheapest approved model` and `Application startup complete`. Check it at http://localhost:8000/api/health.

Next time, you only need:

```bash
cd hw4/backend && source .venv/bin/activate && uvicorn main:app --reload --port 8000
```

## 4. Run the frontend (terminal 2)

```bash
cd hw4/frontend
npm install
npm run dev
```

Open **http://localhost:5173**. The dev server forwards `/api` and `/images` requests to the backend on port 8000, so keep both running.

## 5. Try it

- **Shop:** browse **Products**, filter by size, color and price, and open a product to see its sizes, stock and "You might also like".
- **Chat with Handsome Dan** (bottom-right button). Try:
  - "how many are left in medium?" on a product page
  - "what quarter-zips do you have?" (the results appear on the page)
  - "do you have that in blue?"
- **Accounts:** log in with the test account `test@campuscustoms.yale.edu` / `password`, or create your own. Logged-in chats are saved and reload when you come back.

## Troubleshooting

| Problem | Fix |
|---|---|
| Products page says "Could not load products" | The backend isn't running, or `hw4/data/campus_customs.db` is missing (step 1) |
| Product images don't show | `hw4/data/products/` is missing or in the wrong place (step 1) |
| Chat says "The shop assistant isn't set up yet" | `hw4/.env` is missing or has no `PORTKEY_API_KEY` (step 2); restart the backend |
| `Address already in use` / `Port 5173 is already in use` | A copy is already running; stop it with Ctrl+C in its terminal |
| `uvicorn: command not found` | Activate the virtual environment first: `source .venv/bin/activate` |

## More detail

[`output/harness.md`](output/harness.md) explains the whole system:
- an architecture diagram
- every `models.py` field and why it was chosen
- the agent's tools and abilities
- the safety rules
- specs (loop limits, result caps, models)
- the audit trail

Check the audit trail's integrity with `python audit.py` from `backend/`.
