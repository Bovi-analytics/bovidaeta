"""Top-level public API for farm data definitions."""

from .cow import BreedPart, Cow
from .enums import (
    AnimalGender,
    Breed,
    BreedingType,
    CalvingEaseType,
    ConfirmationStatus,
    DepartureReason,
    DepartureType,
    DiagnosisMethod,
    DiagnosisSampleType,
    DiagnosisSeverity,
    DiagnosisStage,
    DiagnosticSource,
    DiseaseCode,
    EventType,
    GenderSorting,
    GenomicSampleSource,
    HerdEntryType,
    LamenessAffectedLeg,
    LamenessObservationContext,
    ParturitionBirthStatusType,
    RouteOfAdministration,
    SensorMeasurementType,
    TreatmentResponseStatus,
)
from .event import Event
from .event_metadata import (
    ALL_METADATA,
    BirthMetadata,
    BodyConditionScoreMetadata,
    BodyWeightKgMetadata,
    BreedingMetadata,
    CalvingMetadata,
    DiagnosisMetadata,
    DiagnosisSampleMetadata,
    DiseaseMetadata,
    EventMetadataModel,
    ExitMetadata,
    FeedIntakeMetadata,
    GenomeTestMetadata,
    HerdEntryMetadata,
    HerdMoveMetadata,
    LamenessScoreMetadata,
    MilkMeterYieldsMetadata,
    MilkRecordingMetadata,
    SensorMeasurementMetadata,
    TreatmentMetadata,
)
from .herd import Herd
from .io import DairyData

__version__ = "0.1.0"

__all__ = [
    "AnimalGender",
    "BirthMetadata",
    "BodyConditionScoreMetadata",
    "BodyWeightKgMetadata",
    "ConfirmationStatus",
    "DiagnosisMetadata",
    "DiagnosisSampleMetadata",
    "DiagnosisMethod",
    "DiagnosisSampleType",
    "DiagnosisSeverity",
    "DiagnosisStage",
    "DiagnosticSource",
    "DiseaseCode",
    "DiseaseMetadata",
    "LamenessAffectedLeg",
    "LamenessObservationContext",
    "LamenessScoreMetadata",
    "Breed",
    "BreedPart",
    "BreedingMetadata",
    "BreedingType",
    "CalvingMetadata",
    "CalvingEaseType",
    "Cow",
    "DepartureReason",
    "DepartureType",
    "Event",
    "EventMetadataModel",
    "EventType",
    "ExitMetadata",
    "FeedIntakeMetadata",
    "FarmData",
    "GenomeTestMetadata",
    "GenderSorting",
    "GenomicSampleSource",
    "Herd",
    "HerdEntryMetadata",
    "HerdEntryType",
    "HerdMoveMetadata",
    "MilkMeterYieldsMetadata",
    "MilkRecordingMetadata",
    "ParturitionBirthStatusType",
    "SensorMeasurementMetadata",
    "TreatmentMetadata",
    "RouteOfAdministration",
    "SensorMeasurementType",
    "TreatmentResponseStatus",
    "to_polars",
]


def __getattr__(name: str):
    """Expose `to_polars` lazily; it needs pyspark, the rest of the package does not."""
    if name == "to_polars":
        from .io import to_polars

        return to_polars
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
