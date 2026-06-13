# SalesLoop AI

Plateforme SaaS multi-tenant d'agents conversationnels IA pour équipes commerciales.

- **Agent Collector** : debriefing post-RDV conversationnel (style WhatsApp) avec extraction
  structurée (résultat, objections, concurrents, lacunes produit) en fin de conversation.
- **Agent Trainer** : coach commercial s'appuyant sur les contenus de formation
  du tenant (RAG pgvector) et les lacunes détectées par le Collector.
- **Dashboard manager** : conversations d'équipe (KPI, graphiques, recherche & filtres),
  rapports LLM périodiques, directives.
- **Admin direction** : gestion des utilisateurs, upload des contenus de formation (texte/PDF).
- **Interface** : thème clair/sombre, navigation latérale, page profil (changement de mot de passe),
  notifications toast — composants maison, sans lib UI lourde.

## Stack

| Couche | Techno |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 async, PostgreSQL 16, Alembic |
| LLM | OpenRouter (modèle configurable via `OPENROUTER_MODEL`) |
| Frontend | React 18 + TypeScript, Vite, TailwindCSS, TanStack Query |
| RAG | pgvector + embeddings OpenAI-compatibles (configurable) |
| Infra | Docker Compose, Makefile, GitHub Actions |

## Démarrage (3 commandes)

```bash
cp .env.example .env   # puis renseigner OPENROUTER_API_KEY, JWT_SECRET, etc.
make up                # postgres + backend + frontend (migrations au démarrage)
make seed              # jeu de démo : tenant, comptes, debriefings, formation
```

Application : http://localhost:5173 · Docs API (Swagger) : http://localhost:8000/docs ·
Adminer (exploration DB) : http://localhost:8080.

### Comptes de démonstration

Après `make seed`, connecte-toi (mot de passe commun : `demo1234`) :

| Email | Rôle | Voit |
|---|---|---|
| `direction@demo.salesloop.fr` | direction | tout le tenant, admin, formation |
| `manager@demo.salesloop.fr` | manager | son équipe, rapports, directives |
| `sofia@demo.salesloop.fr` | commercial | ses propres conversations |
| `karim@demo.salesloop.fr` | commercial | ses propres conversations |

> Les embeddings RAG nécessitent une `EMBEDDING_API_KEY` (endpoint compatible OpenAI).
> Sans clé, les contenus de formation sont stockés non indexés ; réindexe-les depuis
> la page Admin une fois la clé renseignée. `make seed-fresh` réinitialise la démo.

### Configuration (`.env`)

| Variable | Rôle |
|---|---|
| `OPENROUTER_API_KEY` / `OPENROUTER_MODEL` | accès LLM (agents, extraction, rapports) |
| `EMBEDDING_API_KEY` / `EMBEDDING_BASE_URL` / `EMBEDDING_MODEL` | embeddings RAG (optionnel) |
| `JWT_SECRET` | signature des tokens |
| `CORS_ORIGINS` | origines autorisées (séparées par des virgules) |
| `AUTH_RATE_LIMIT` | limite sur `/auth` (ex. `10/minute`) |

## Développement

```bash
make venv          # venv local backend/.venv avec les dépendances de dev
make test          # pytest (crée une DB de test dédiée, LLM mocké)
make test-frontend # vitest + typecheck
make lint          # ruff + mypy
make format        # ruff format + fixes auto
make migrate       # alembic upgrade head dans le conteneur
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

## Endpoints principaux

Documentation interactive complète sur `/docs`. Les écritures `directives` et `reports`
sont réservées aux rôles manager/direction ; `training` à la direction.

| Méthode | Route | Rôle | Description |
|---|---|---|---|
| POST | `/auth/register` | public | Inscription entreprise (crée le tenant + 1er compte direction) |
| POST | `/auth/login` | public | Connexion par email (token JWT) |
| POST | `/auth/users` | manager+ | Créer un compte dans son tenant |
| GET | `/users/me` · `/users/` | tous | Profil courant · liste scopée au rôle |
| PATCH | `/users/{id}` | manager+ | Activation, rattachement à un manager |
| POST | `/conversations/` | tous | Démarrer une session (1er message agent généré) |
| POST | `/conversations/{id}/messages` | propriétaire | Envoyer un message → réponse de l'agent |
| POST | `/conversations/{id}/close` | propriétaire | Clôturer (extraction structurée pour le Collector) |
| GET | `/conversations/` | tous | Conversations visibles selon le rôle |
| CRUD | `/directives/` | manager+ écriture | Consignes injectées dans le prompt du Collector |
| POST | `/reports/generate` | manager+ | Synthèse LLM des conversations closes d'une période |
| POST | `/training/` · `/training/upload` | direction | Ajout d'un contenu (texte ou PDF) |
| PATCH/POST | `/training/{id}` · `/{id}/reindex` | direction | Édition · réindexation RAG |
| GET | `/health` | public | Disponibilité service + base |

## Rôles

- `commercial` : voit ses propres données
- `manager` : voit son équipe (utilisateurs et conversations)
- `direction` : voit tout le tenant + administration

## Tests & qualité

- **Backend** : `make test` (pytest, ~57 tests — isolation tenant, agents avec LLM
  mocké, RAG, permissions). `make lint` (ruff + mypy strict raisonnable).
- **Frontend** : `make test-frontend` (Vitest + `tsc`).
- **CI** : GitHub Actions exécute lint + mypy + pytest (service Postgres) et
  Vitest + build à chaque push.
