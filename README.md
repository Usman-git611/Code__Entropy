# LearnDNA

**Learn Smarter. Think Deeper. Build Your Future.**

LearnDNA is a MySQL-backed FastAPI application for personalized student learning. It includes secure role authentication, a student dashboard, missions, Learning DNA, Future Risk, thinking replay, a quiz workflow, teacher/parent views, community posts, dark mode, and a transparent local AI-demo mode.

## Quick start (Windows)

1. Create a MySQL database: `mysql -u root -p -e "CREATE DATABASE learndna CHARACTER SET utf8mb4;"`
2. Copy `.env.example` to `.env` and set `DATABASE_URL` with your MySQL password. If your local MySQL user has no password, omit the colon-password portion: `mysql+pymysql://root@localhost:3306/learndna`.
3. Create and activate a virtual environment: `python -m venv .venv` then `.\.venv\Scripts\Activate.ps1`
4. Install packages: `python -m pip install -r requirements.txt`
5. Start: `python -m uvicorn app.main:app --reload`
6. Open http://127.0.0.1:8000. API docs: http://127.0.0.1:8000/docs

On first start, tables and demo data are created automatically.

## Code Lab

Code Lab includes a 25-challenge Code Quest journey for Python, C, C++, MySQL, and Java. Python programs (variables, conditions, loops, lists, and simple functions) run in a restricted learning engine. MySQL exercises run as real read-only queries against a temporary lesson dataset.

C, C++, and Java native compilation is disabled by default because arbitrary compiler execution is unsafe on an ngrok tunnel or deployed website. To enable the protected C/C++ compiler on your **private local computer only**, add this to `.env`, then restart the app:

```env
LOCAL_COMPILER_ENABLED=true
```

Keep `LOCAL_COMPILER_ENABLED=false` for ngrok, online judging, and production deployment. Java challenges require a Java JDK (`javac`) to be installed.

## Demo accounts

| Role | Email | Password |
|---|---|---|
| Student | student@learndna.demo | LearnDNA123! |
| Teacher | teacher@learndna.demo | LearnDNA123! |
| Parent | parent@learndna.demo | LearnDNA123! |
| Admin | admin@learndna.demo | LearnDNA123! |

## AI modes

`AI_PROVIDER=demo` is clearly identified in the UI and uses rule-based feedback, not a fake model response. Its scoring rules are in `app/services/learning.py`.

### Enable real Nova AI (OpenAI)

1. Create an OpenAI API key in the API dashboard. Never put it in frontend code or share it.
2. In `.env`, set `AI_PROVIDER=openai`, add `OPENAI_API_KEY=...`, and choose `AI_MODEL=gpt-5` (or a model your API account can use).
3. Restart the server. Nova will call the real model from the backend and label answers as `Real OpenAI model`.

The API key remains on the server. If the provider is unreachable, Nova returns a friendly message instead of exposing technical details.

### Enable real Nova AI without an API key (Ollama)

1. Install Ollama for Windows from [ollama.com](https://ollama.com/).
2. Open a new PowerShell window and run: `ollama pull llama3.2:1b`.
3. In `.env`, set `AI_PROVIDER=ollama` and `OLLAMA_MODEL=llama3.2:1b`.
4. Restart LearnDNA. Nova will label responses as `Real local model: llama3.2:1b`.

Ollama runs locally at `http://127.0.0.1:11434`; LearnDNA calls its chat API from the backend. The first model download is several GB and local response speed depends on your computer.

## Tests

`python -m pytest -q`

## 24/7 deployment

Deploy the same app to a Python host (Railway, Render, Fly.io, or a VPS) with a managed MySQL database. Set all values from `.env.example` as host environment variables, use `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`, set a strong `SECRET_KEY`, and configure HTTPS/custom domain in the host dashboard. Do not expose a home MySQL server directly to the public internet.

For a VPS, put Nginx/Caddy in front for HTTPS and run Uvicorn under a service manager. Create the MySQL database and least-privilege database user there before starting the service.
