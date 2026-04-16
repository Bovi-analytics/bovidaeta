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
from .event_details import (
    BirthDetail,
    BreedingDetail,
    CalvingDetail,
    BodyConditionScoreDetail,
    BodyWeightDetail,
    EventDetailModel,
    ExitDetail,
    FeedIntakeDetail,
    GenomeTestDetail,
    LamenessScoreDetail,
    MilkMeterYieldsDetail,
    MilkRecordingDetail,
)
from .herd import Herd

__all__ = [
    "AnimalGender",
    "BodyConditionScoreDetail",
    "BodyWeightDetail",
    "LamenessAffectedLeg",
    "LamenessObservationContext",
    "LamenessScoreDetail",
    "Breed",
    "BreedPart",
    "BreedingType",
    "CalvingEaseType",
    "Cow",
    "DepartureReason",
    "DepartureType",
    "Event",
    "EventDetailModel",
    "EventType",
    "GenderSorting",
    "Herd",
    "ParturitionBirthStatusType",
    "BirthDetail",
    "BreedingDetail",
    "CalvingDetail",
    "ExitDetail",
    "FeedIntakeDetail",
    "GenomeTestDetail",
    "MilkMeterYieldsDetail",
    "MilkRecordingDetail",
]
