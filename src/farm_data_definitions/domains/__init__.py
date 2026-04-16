"""Domain models for farm data definitions."""

from .cow import BreedPart, Cow
from .enums import (
    AnimalGender,
    Breed,
    BreedingType,
    CalvingEaseType,
    DepartureReason,
    DepartureType,
    EventType,
    GenderSorting,
    LamenessAffectedLeg,
    LamenessObservationContext,
    ParturitionBirthStatusType,
)
from .event import Event
from .event_metadata import (
    BirthMetadata,
    BodyConditionScoreMetadata,
    BodyWeightMetadata,
    BreedingMetadata,
    CalvingMetadata,
    EventMetadataModel,
    ExitMetadata,
    FeedIntakeMetadata,
    GenomeTestMetadata,
    LamenessScoreMetadata,
    MilkMeterYieldsMetadata,
    MilkRecordingMetadata,
)
from .herd import Herd

__all__ = [
    "AnimalGender",
    "BodyConditionScoreMetadata",
    "BodyWeightMetadata",
    "LamenessAffectedLeg",
    "LamenessObservationContext",
    "LamenessScoreMetadata",
    "Breed",
    "BreedPart",
    "BreedingType",
    "CalvingEaseType",
    "Cow",
    "DepartureReason",
    "DepartureType",
    "Event",
    "EventMetadataModel",
    "EventType",
    "GenderSorting",
    "Herd",
    "ParturitionBirthStatusType",
    "BirthMetadata",
    "BreedingMetadata",
    "CalvingMetadata",
    "ExitMetadata",
    "FeedIntakeMetadata",
    "GenomeTestMetadata",
    "MilkMeterYieldsMetadata",
    "MilkRecordingMetadata",
]
