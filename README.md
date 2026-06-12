# SalesLoop AI

Plateforme SaaS multi-tenant d'agents conversationnels IA pour équipes commerciales.

- **Agent Collector** : debriefing post-RDV conversationnel (style WhatsApp) avec extraction
  structurée (résultat, objections, concurrents, lacunes produit) en fin de conversation.
- **Agent Trainer** *(à venir)* : coach commercial s'appuyant sur les contenus de formation
  du tenant (RAG) et les lacunes détectées par le Collector.
- **Dashboard manager** *(à venir)* : activité d'équipe, rapports LLM périodiques, directives.

## Stack

| Couche | Techno |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 async, PostgreSQL 16, Alembic |
| LLM | OpenRouter (modèle configurable via `OPENROUTER_MODEL`) |
| Frontend *(à venir)* | React 18 + TypeScript, Vite, TailwindCSS, TanStack Query |
| Infra | Docker Compose, Makefile, GitHub Actions |

## Démarrage (3 commandes)

```bash
cp .env.example .env   # puis renseigner OPENROUTER_API_KEY, JWT_SECRET, etc.
make up                # postgres + backend (migrations appliquées au démarrage)
make logs              # suivre le backend — API sur http://localhost:8000/docs
```

Adminer (exploration DB) : http://localhost:8080.

## Développement

```bash
make venv      # venv local backend/.venv avec les dépendances de dev
make test      # pytest (crée une DB de test dédiée, LLM mocké)
make lint      # ruff + mypy
make format    # ruff format + fixes auto
make migrate   # alembic upgrade head dans le conteneur
make makemigration m="description"   # nouvelle migration autogénérée
```

## Architecture backend

```
backend/app/
  main.py          # app factory, CORS, exception handlers, lifespan
  config.py        # settings (pydantic-settings, variables d'env)
  database.py      # engine async, session, Base
  models/          # SQLAlchemy (1 fichier par modèle + enums.py)
  schemas/         # Pydantic (entrées/sorties API)
  routers/         # endpoints fins : validation → service → schéma
  core/            # security (JWT/hash), permissions (rôles), exceptions métier
  services/        # logique métier pure
    llm/           # interface LLMProvider + client OpenRouter (retry, usage tokens)
    agents/        # logique conversationnelle des agents
```

Principes : isolation stricte par tenant sur tout accès DB, permissions par rôle en
dépendances FastAPI réutilisables, appels LLM derrière une interface mockable, aucune
stack trace exposée par l'API.

## Rôles

- `commercial` : voit ses propres données
- `manager` : voit son équipe
- `direction` : voit tout le tenant
