"""Demo seed: a ready-to-explore tenant with users, closed debriefings,
directives and training content.

Deterministic and LLM-free: conversation messages and their extracted data
are written by hand, so seeding is fast, reproducible and needs no API key.
Training content is embedded through the real provider when EMBEDDING_API_KEY
is set, and stored unembedded otherwise (re-index later from the admin page).

Usage:
    python -m app.seed            # no-op if the demo tenant already exists
    python -m app.seed --fresh    # delete the demo tenant first, then reseed
"""

import asyncio
import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select

from app.core.security import hash_password
from app.database import async_session
from app.models.conversation import Conversation
from app.models.directive import Directive
from app.models.enums import (
    AgentType,
    ConversationStatus,
    DirectivePriority,
    MessageSender,
    UserRole,
)
from app.models.message import Message
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.training import TrainingContentCreate
from app.services import training as training_service
from app.services.rag.embeddings import OpenAICompatibleEmbeddingProvider

DEMO_PASSWORD = "demo1234"
DIRECTION_EMAIL = "direction@demo.salesloop.fr"

# (email, full_name, role, manager_key) — manager_key links commercials to a manager
USERS = [
    ("direction@demo.salesloop.fr", "Camille Direction", UserRole.DIRECTION, None),
    ("manager@demo.salesloop.fr", "Marc Manager", UserRole.MANAGER, None),
    ("sofia@demo.salesloop.fr", "Sofia Vendeuse", UserRole.COMMERCIAL, "manager"),
    ("karim@demo.salesloop.fr", "Karim Commercial", UserRole.COMMERCIAL, "manager"),
]

DIRECTIVES = [
    (
        "Mettez systématiquement en avant la nouvelle gamme bio ce trimestre.",
        DirectivePriority.HIGH,
    ),
    ("Notez précisément les prix annoncés par les concurrents.", DirectivePriority.MEDIUM),
    ("Proposez un rendez-vous de suivi à chaque client hésitant.", DirectivePriority.LOW),
]

TRAINING = [
    (
        "Argumentaire gamme bio",
        "La gamme bio est certifiée Agriculture Biologique (AB).\n\n"
        "Elle est cultivée sans pesticides de synthèse et tracée du champ au rayon. "
        "La marge distributeur est de 35%, supérieure de 8 points à la gamme classique.\n\n"
        "Les produits se conservent 12 mois à température ambiante avant ouverture, "
        "puis 3 semaines au réfrigérateur.",
    ),
    (
        "Politique tarifaire 2026",
        "Remise maximale autorisée : 15% pour les commandes de plus de 500 unités.\n\n"
        "En dessous de 500 unités, le plafond de remise est de 8%. "
        "Toute remise supérieure nécessite la validation écrite du manager.\n\n"
        "Les frais de livraison sont offerts à partir de 1000 euros de commande.",
    ),
]

# Closed debriefings: (commercial_key, days_ago, messages, extracted_data)
CONVERSATIONS = [
    (
        "sofia",
        1,
        [
            (MessageSender.AGENT, "Salut Sofia ! Comment s'est passé ton RDV chez Pharma-Plus ?"),
            (MessageSender.USER, "Plutôt bien, ils ont commandé 300 unités de la gamme bio !"),
            (MessageSender.AGENT, "Super ! Ils ont eu des hésitations sur quelque chose ?"),
            (MessageSender.USER, "Le prix surtout, ils trouvaient ça un peu cher au début."),
            (MessageSender.AGENT, "Noté. Un suivi à prévoir avec eux ?"),
            (
                MessageSender.USER,
                "Oui, je dois les rappeler la semaine prochaine pour la livraison.",
            ),
        ],
        {
            "sentiment": "positif",
            "client_name": "Pharma-Plus",
            "order_result": "commande",
            "order_trend": "hausse",
            "objections": ["prix élevé"],
            "competitors": [],
            "product_knowledge_gap": False,
            "knowledge_gap_detail": None,
            "follow_up_needed": True,
            "follow_up_date": None,
            "follow_up_note": "Rappeler la semaine prochaine pour la livraison",
        },
    ),
    (
        "sofia",
        3,
        [
            (MessageSender.AGENT, "Coucou Sofia ! Ta journée côté clients ?"),
            (MessageSender.USER, "Compliquée. Chez BioMarket ils n'ont pas commandé."),
            (MessageSender.AGENT, "Ah, ils ont dit pourquoi ?"),
            (MessageSender.USER, "Ils comparent avec NaturaPlus qui propose 10% moins cher."),
            (MessageSender.AGENT, "Tu as su répondre sur la différence de qualité ?"),
            (
                MessageSender.USER,
                "Pas trop en fait, je ne connaissais pas bien la conservation du produit.",
            ),
        ],
        {
            "sentiment": "négatif",
            "client_name": "BioMarket",
            "order_result": "refus",
            "order_trend": "baisse",
            "objections": ["prix concurrent plus bas"],
            "competitors": [
                {"name": "NaturaPlus", "price_mentioned": True, "price_detail": "-10%"}
            ],
            "product_knowledge_gap": True,
            "knowledge_gap_detail": "conservation du produit bio",
            "follow_up_needed": True,
            "follow_up_date": None,
            "follow_up_note": "Recontacter avec un argumentaire qualité",
        },
    ),
    (
        "karim",
        2,
        [
            (MessageSender.AGENT, "Salut Karim ! Comment ça s'est passé aujourd'hui ?"),
            (MessageSender.USER, "Bien ! Signature chez Grand Frais pour 800 unités."),
            (MessageSender.AGENT, "Excellent ! Ils ont parlé de concurrents ?"),
            (MessageSender.USER, "Non, ils étaient déjà convaincus par la certification bio."),
            (MessageSender.AGENT, "Parfait, un follow-up nécessaire ?"),
            (MessageSender.USER, "Non, tout est bouclé, livraison planifiée."),
        ],
        {
            "sentiment": "positif",
            "client_name": "Grand Frais",
            "order_result": "commande",
            "order_trend": "hausse",
            "objections": [],
            "competitors": [],
            "product_knowledge_gap": False,
            "knowledge_gap_detail": None,
            "follow_up_needed": False,
            "follow_up_date": None,
            "follow_up_note": None,
        },
    ),
    (
        "karim",
        5,
        [
            (MessageSender.AGENT, "Coucou Karim ! Bilan de ta journée ?"),
            (MessageSender.USER, "Mitigé. Chez SuperU ils hésitent encore."),
            (MessageSender.AGENT, "Sur quoi portent leurs hésitations ?"),
            (MessageSender.USER, "Le volume minimum de commande, ils trouvent ça élevé."),
            (MessageSender.AGENT, "Un concurrent dans la boucle ?"),
            (MessageSender.USER, "Oui, EcoDistrib leur propose des plus petits lots."),
        ],
        {
            "sentiment": "mitigé",
            "client_name": "SuperU",
            "order_result": "en_attente",
            "order_trend": "stable",
            "objections": ["volume minimum trop élevé"],
            "competitors": [
                {"name": "EcoDistrib", "price_mentioned": False, "price_detail": "petits lots"}
            ],
            "product_knowledge_gap": False,
            "knowledge_gap_detail": None,
            "follow_up_needed": True,
            "follow_up_date": None,
            "follow_up_note": "Proposer un palier de commande intermédiaire",
        },
    ),
]


async def _delete_demo() -> None:
    async with async_session() as db:
        result = await db.execute(select(Tenant).join(User).where(User.email == DIRECTION_EMAIL))
        tenant = result.scalar_one_or_none()
        if tenant is not None:
            await db.execute(delete(Tenant).where(Tenant.id == tenant.id))
            await db.commit()


async def _already_seeded() -> bool:
    async with async_session() as db:
        result = await db.execute(select(User).where(User.email == DIRECTION_EMAIL))
        return result.scalar_one_or_none() is not None


async def seed() -> None:
    password_hash = hash_password(DEMO_PASSWORD)

    async with async_session() as db:
        tenant = Tenant(name="Demo SalesLoop")
        db.add(tenant)
        await db.flush()

        users: dict[str, User] = {}
        # First pass: managers and direction (commercials need their manager id)
        for email, full_name, role, _ in USERS:
            if role != UserRole.COMMERCIAL:
                user = User(
                    tenant_id=tenant.id,
                    email=email,
                    full_name=full_name,
                    password_hash=password_hash,
                    role=role,
                )
                db.add(user)
                users[role.value] = user
        await db.flush()

        for email, full_name, role, manager_key in USERS:
            if role == UserRole.COMMERCIAL:
                manager = users[manager_key] if manager_key else None
                user = User(
                    tenant_id=tenant.id,
                    email=email,
                    full_name=full_name,
                    password_hash=password_hash,
                    role=role,
                    manager_id=manager.id if manager else None,
                )
                db.add(user)
                users[email.split("@")[0]] = user
        await db.flush()

        for content, priority in DIRECTIVES:
            db.add(
                Directive(
                    tenant_id=tenant.id,
                    created_by=users["manager"].id,
                    content=content,
                    priority=priority,
                )
            )

        now = datetime.now(UTC)
        for commercial_key, days_ago, messages, extracted in CONVERSATIONS:
            commercial = users[commercial_key]
            ended = now - timedelta(days=days_ago)
            conversation = Conversation(
                tenant_id=tenant.id,
                user_id=commercial.id,
                agent_type=AgentType.COLLECTOR,
                status=ConversationStatus.COMPLETED,
                extracted_data=extracted,
                started_at=ended - timedelta(minutes=5),
                ended_at=ended,
                total_tokens=420,
            )
            db.add(conversation)
            await db.flush()
            for offset, (sender, text) in enumerate(messages):
                db.add(
                    Message(
                        conversation_id=conversation.id,
                        sender=sender,
                        content=text,
                        created_at=ended - timedelta(minutes=5) + timedelta(seconds=offset * 30),
                    )
                )

        await db.commit()

    # Training content: embedded via the real provider if a key is configured
    embedder = OpenAICompatibleEmbeddingProvider()
    try:
        async with async_session() as db:
            result = await db.execute(select(User).where(User.email == DIRECTION_EMAIL))
            direction = result.scalar_one()
            for title, content in TRAINING:
                await training_service.create_training_content(
                    db, embedder, direction, TrainingContentCreate(title=title, content=content)
                )
    finally:
        await embedder.aclose()


async def main() -> None:
    fresh = "--fresh" in sys.argv
    if fresh:
        await _delete_demo()
    elif await _already_seeded():
        print("Le tenant de démo existe déjà. Utilise --fresh pour le recréer.")
        return

    await seed()
    print(f"Démo créée. Connexion : {DIRECTION_EMAIL} / {DEMO_PASSWORD}")
    print("Autres comptes (même mot de passe) : manager@, sofia@, karim@demo.salesloop.fr")


if __name__ == "__main__":
    asyncio.run(main())
