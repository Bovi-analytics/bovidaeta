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
    ParturitionBirthStatusType,
)
from .event import Event
from .event_details import (
    BirthDetail,
    BreedingDetail,
    CalvingDetail,
    EventDetailModel,
    ExitDetail,
    FeedIntakeDetail,
    MilkMeterYieldsDetail,
    MilkRecordingDetail,
)
from .herd import Herd

__all__ = [
    "AnimalGender",
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
    "MilkMeterYieldsDetail",
    "MilkRecordingDetail",
]
