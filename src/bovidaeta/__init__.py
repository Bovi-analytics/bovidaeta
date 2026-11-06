"""Top-level public API for bovidaeta."""

from .cow import BreedPart, Cow
from .enums import (
    AggregationPeriod,
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
    AggregatedMilkMeterYieldsMetadata,
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
from .lactation import (
    load_lactation_records,
    load_lactations,
    select_lactations,
)

__version__ = "0.1.3"

__all__ = [
    "ALL_METADATA",
    "AggregatedMilkMeterYieldsMetadata",
    "AggregationPeriod",
    "AnimalGender",
    "BirthMetadata",
    "BodyConditionScoreMetadata",
    "BodyWeightKgMetadata",
    "Breed",
    "BreedPart",
    "BreedingMetadata",
    "BreedingType",
    "CalvingEaseType",
    "CalvingMetadata",
    "ConfirmationStatus",
    "Cow",
    "DairyData",
    "DepartureReason",
    "DepartureType",
    "DiagnosisMetadata",
    "DiagnosisMethod",
    "DiagnosisSampleMetadata",
    "DiagnosisSampleType",
    "DiagnosisSeverity",
    "DiagnosisStage",
    "DiagnosticSource",
    "DiseaseCode",
    "DiseaseMetadata",
    "Event",
    "EventMetadataModel",
    "EventType",
    "ExitMetadata",
    "FeedIntakeMetadata",
    "GenderSorting",
    "GenomeTestMetadata",
    "GenomicSampleSource",
    "Herd",
    "HerdEntryMetadata",
    "HerdEntryType",
    "HerdMoveMetadata",
    "LamenessAffectedLeg",
    "LamenessObservationContext",
    "LamenessScoreMetadata",
    "MilkMeterYieldsMetadata",
    "MilkRecordingMetadata",
    "ParturitionBirthStatusType",
    "RouteOfAdministration",
    "SensorMeasurementMetadata",
    "SensorMeasurementType",
    "TreatmentMetadata",
    "TreatmentResponseStatus",
    "load_lactation_records",
    "load_lactations",
    "select_lactations",
    "to_polars",
]


def __getattr__(name: str):
    """Expose `to_polars` lazily; it needs pyspark, the rest of the package does not."""
    if name == "to_polars":
        from .io import to_polars

        return to_polars
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
