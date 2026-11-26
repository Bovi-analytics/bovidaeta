"""Top-level public API for bovidaeta."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _version

from .cow import BreedPart, Cow
from .enums import (
    AggregationPeriod,
    AnimalGender,
    Breed,
    BreedingType,
    CalfRemovalTiming,
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
    SensorMeasurementStatistic,
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
    LabMeasurementMetadata,
    LamenessScoreMetadata,
    MilkMeterYieldsMetadata,
    MilkRecordingMetadata,
    SensorMeasurementMetadata,
    TreatmentMetadata,
)
from .herd import Herd
from .io import DairyData
from .lactation import (
    load_daily_milk_yields,
    load_lactation_records,
    load_lactations,
    select_lactations,
)
from .study import Study, StudyAnimal

try:
    __version__ = _version("bovidaeta")
except (
    PackageNotFoundError
):  # pragma: no cover - running from a source tree without installing
    __version__ = "0.0.0"

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
    "CalfRemovalTiming",
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
    "LabMeasurementMetadata",
    "LamenessAffectedLeg",
    "LamenessObservationContext",
    "LamenessScoreMetadata",
    "MilkMeterYieldsMetadata",
    "MilkRecordingMetadata",
    "ParturitionBirthStatusType",
    "RouteOfAdministration",
    "SensorMeasurementMetadata",
    "SensorMeasurementStatistic",
    "SensorMeasurementType",
    "Study",
    "StudyAnimal",
    "TreatmentMetadata",
    "TreatmentResponseStatus",
    "load_daily_milk_yields",
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
