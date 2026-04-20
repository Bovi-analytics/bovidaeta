from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from .enums import EventType


class Event(BaseModel):
    """
    A class to represent an event on the timeline of a cow.

    This model includes event identity fields plus event-specific metadata.
    """

    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    event_id: UUID | None = Field(
        default=None,
        description="UUID identifier of the event record.",
    )
    event_type: EventType = Field(
        description="Type of the event.",
    )
    animal_id: UUID | None = Field(
        default=None,
        description="UUID identifier of the animal this event belongs to.",
    )
    animal_id_source: str = Field(
        description="Identifier of the animal as per the source system.",
    )
    timestamp: AwareDatetime = Field(
        description="Mandatory date/time of the event.",
    )
    metadata: dict[str, Any] | None = Field(
        default_factory=dict,
        description=("Event metadata, unique for each event type."),
    )
