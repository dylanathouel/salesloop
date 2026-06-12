## 1. Modèle de données (schéma validé — le respecter)

Toutes les tables ont un `id UUID` PK et timestamps timezone-aware (`created_at`, `updated_at` quand pertinent). FK avec `ondelete` explicites.

- **tenant** : name, plan (default `trial`), is_active
- **user** : tenant_id FK, manager_id FK self-ref nullable (SET NULL), email, full_name, phone nullable, password_hash, role (`commercial|manager|direction`), is_active. Contrainte unique `(tenant_id, email)`.
- **conversation** : tenant_id, user_id, agent_type (`collector|trainer`), status (`active|completed|abandoned`), extracted_data JSONB, total_tokens, started_at, ended_at nullable
- **message** : conversation_id, sender (`user|agent`), content, token_count, created_at
- **report** : tenant_id, period_type (`daily|weekly|monthly`), period_start, period_end, summary, insights JSONB, metrics JSONB, generated_at + table de liaison `report_conversation` (M2M)
- **directive** : tenant_id, created_by FK user, content, priority (`low|medium|high`), status (`active|archived`)
- **training_content** : tenant_id, title, raw_content, content_type, chunk_metadata JSONB, is_embedded bool
- **training_chunk** (nouvelle table pour le RAG) : training_content_id FK, chunk_text, embedding vector, chunk_index

Utilise des `Enum` Python mappés en String côté DB pour les champs à valeurs fermées (role, status, agent_type, etc.) — pas de magic strings dispersées.

## 2. Architecture backend

```
backend/
  app/
    main.py                 # app factory, CORS, lifespan, exception handlers
    config.py               # Settings pydantic-settings
    database.py             # engine, session, Base
    models/                 # 1 fichier par modèle + enums.py
    schemas/                # Pydantic schemas séparés des routers (1 fichier par domaine)
    routers/                # auth, users, tenants, conversations, reports, directives, training
    services/               # logique métier pure, testable sans HTTP
      auth.py
      llm/                  # client OpenRouter + interface abstraite LLMProvider
        client.py
        prompts.py          # tous les prompts système (FR)
      agents/
        collector.py        # logique conversationnelle + clôture + extraction
        trainer.py          # logique RAG + quiz/roleplay
      extraction.py         # extraction JSON structuré post-conversation
      reports.py            # génération de rapports périodiques
      rag/
        chunking.py         # découpage sémantique des training_content
        embeddings.py       # interface EmbeddingProvider + implémentation
        retrieval.py        # recherche par similarité pgvector, filtrée par tenant
    core/
      security.py           # JWT, hashing
      permissions.py        # dépendances FastAPI par rôle (require_manager, etc.)
      exceptions.py         # exceptions métier → HTTP mappées dans main
  alembic/                  # migrations versionnées, jamais create_all en prod
  tests/
    conftest.py             # DB de test isolée, fixtures user/tenant, client async
    test_auth.py, test_conversations.py, test_permissions.py, test_extraction.py, ...
```
## 3. Sécurité & config

- `.env.example` commité, `.env` dans `.gitignore`. **Jamais de secret en dur.**
- CORS configuré par env (origins explicites)
- Rate limiting basique sur /auth (slowapi ou équivalent)
- Login sans tenant_id exposé : login par email seul (email globalement unique) OU par sous-domaine/slug tenant — choisis et justifie, mais l'utilisateur ne doit pas saisir un UUID.
- Validation stricte des UUID en path params
- Les erreurs API ne leakent jamais de stack trace

