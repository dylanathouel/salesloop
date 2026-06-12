"""Closed-value enums shared across models, schemas and services.

Stored as plain VARCHAR in the database (native_enum=False) with a CHECK
constraint, so the DB stays portable and values readable.
"""

import enum

from sqlalchemy import Enum as SAEnum


class UserRole(str, enum.Enum):
    COMMERCIAL = "commercial"
    MANAGER = "manager"
    DIRECTION = "direction"


class TenantPlan(str, enum.Enum):
    TRIAL = "trial"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class AgentType(str, enum.Enum):
    COLLECTOR = "collector"
    TRAINER = "trainer"


class ConversationStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class MessageSender(str, enum.Enum):
    USER = "user"
    AGENT = "agent"


class ReportPeriodType(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class DirectivePriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DirectiveStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


def db_enum(enum_cls: type[enum.Enum], name: str) -> SAEnum:
    """Map a Python enum to a VARCHAR column (values, not member names)."""
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        validate_strings=True,
        values_callable=lambda e: [m.value for m in e],
    )
