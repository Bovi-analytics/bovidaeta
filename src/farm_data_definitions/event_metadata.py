from __future__ import annotations

"""
Typed metadata payloads for timeline events.

This module describes timeline event metadata parameters that need extra
definition in the domain model.
"""


from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .enums import (
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
    GenderSorting,
    HerdEntryType,
    LamenessAffectedLeg,
    LamenessObservationContext,
    ParturitionBirthStatusType,
    RouteOfAdministration,
    SensorMeasurementType,
    TreatmentFrequency,
    TreatmentResponseStatus,
)


class EventMetadataModel(BaseModel):
    """Base class representing timeline event metadata."""

    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class HerdEntryMetadata(EventMetadataModel):
    """
    Herd entry event metadata.

    Records how and when an animal joined the herd. For animals born on farm,
    this event coexists with a BIRTH event on the same timeline — the BIRTH
    event carries biological details (calving ease, birth status) while this
    event records herd membership.
    """

    entry_type: HerdEntryType = Field(
        description=(
            "The mechanism by which the animal entered the herd "
            "(born on farm, purchased, or unknown)."
        ),
    )
    entry_date: date = Field(
        description=(
            "Date the animal officially entered the herd, format YYYY-MM-DD. "
            "For born-on-farm animals this is typically the birth date."
        ),
    )
    age_at_entry: int | None = Field(
        default=None,
        ge=0,
        description=(
            "Age of the animal at the time of herd entry, expressed in days. "
            "Zero for animals born on farm."
        ),
    )
    source_farm: str | None = Field(
        default=None,
        description=(
            "Name or identifier of the farm or operation from which the animal "
            "originated. Applies to purchased animals; free text."
        ),
    )
    purchase_price: float | None = Field(
        default=None,
        ge=0,
        description=(
            "Price paid per animal at the time of purchase. For lot purchases, "
            "record the per-head price (total lot price divided by number of animals). "
            "Applies to purchased animals only."
        ),
    )
    purchase_currency: str | None = Field(
        default=None,
        description=(
            "ISO 4217 currency code for the purchase price (e.g. 'USD', 'EUR', 'GBP'). "
            "Applies to purchased animals only."
        ),
    )


class HerdMoveMetadata(EventMetadataModel):
    """
    Herd move event metadata.

    Records the reassignment of an already-registered animal from one location
    to another. Use this event whenever an animal that exists in the system
    changes pen, group, pasture, or physical site — including moves to and from
    off-farm facilities such as heifer raisers. In that case the animal retains
    its identity and pen/location assignment in the system; no new HerdEntry is
    needed when it returns.

    Contrast with HerdEntry, which is only recorded once — when the animal is
    first registered in the system (born on farm or purchased from an external
    source).

    For group moves, all animals share the same `group_move_id` on their
    individual timelines.
    """

    location_from: str = Field(
        description=(
            "Location the animal is moving from. Use the pen ID for pen-to-pen moves "
            "(e.g. '42'), a descriptive name for pastures (e.g. 'North Pasture'), "
            "or a facility name for off-farm locations (e.g. 'Heifer Raiser - Smith Farm'). "
            "Free text; use consistent naming within your operation."
        ),
    )
    location_to: str = Field(
        description=(
            "Location the animal is moving to. Use the pen ID for pen-to-pen moves "
            "(e.g. '42'), a descriptive name for pastures (e.g. 'North Pasture'), "
            "or a facility name for off-farm locations (e.g. 'Heifer Raiser - Smith Farm'). "
            "Free text; use consistent naming within your operation."
        ),
    )
    group_move_id: int | None = Field(
        default=None,
        gt=0,
        description=(
            "Optional identifier linking all animals moved together in the same "
            "group move. Each animal still has its own HERD_MOVE event."
        ),
    )
    notes: str | None = Field(
        default=None,
        description=(
            "Optional free-text context for the move (e.g. routine production group "
            "rotation, heifer-raiser assignment). Health and treatment reasons are "
            "better captured via Diagnosis and Treatment events on the same timeline."
        ),
    )


class BirthMetadata(EventMetadataModel):
    """Birth event metadata."""

    calving_ease_type: CalvingEaseType | None = Field(
        default=None,
        description="Ease of being born of this cow, based on ICAR enum.",
    )
    parturition_birth_status_type: ParturitionBirthStatusType | None = Field(
        default=None,
        description="The way this calf was born, based on ICAR enum.",
    )


class BreedingMetadata(EventMetadataModel):
    """Breeding event metadata."""

    bull_id: UUID | None = Field(
        default=None,
        description="UUID identifier of the bull used for breeding.",
    )
    bull_ear_tag: str | None = Field(
        default=None,
        description="Ear tag number of the bull.",
    )
    bull_name: str | None = Field(
        default=None,
        description="Official name of the bull.",
    )
    bull_number: int | None = Field(
        default=None,
        gt=0,
        description=(
            "Number of the bull from the breeding organization or, when the bull is "
            "at the farm, the farm number of the bull."
        ),
    )
    insemination_number: int | None = Field(
        default=None,
        ge=1,
        description="Insemination attempt number.",
    )
    breeding_type: BreedingType | None = Field(
        default=None,
        description="Breeding type based on ICAR enums.",
    )
    gender_sorted: GenderSorting | None = Field(
        default=None,
        description="Description of gender-sorted semen, based on ICAR enums.",
    )


class CalvingMetadata(EventMetadataModel):
    """Calving event metadata."""

    calving_ease_type: CalvingEaseType | None = Field(
        default=None,
        description="Ease of the birthing process, based on ICAR enum.",
    )
    parturition_birth_status_type: ParturitionBirthStatusType | None = Field(
        default=None,
        description="The way a calf was born, based on ICAR enum.",
    )


class DiagnosisSampleMetadata(EventMetadataModel):
    """Diagnosis sample collecting event metadata."""

    sample_id: int | str | None = Field(
        default=None,
        description="Unique identifier or barcode of the collected sample.",
    )
    diagnosis_sample_type: DiagnosisSampleType | None = Field(
        default=None,
        description="The biological material collected (e.g., milk, blood, fecal).",
    )
    diagnostic_target: str | None = Field(
        default=None,
        description="The pathogen or condition being tested for, e.g., 'Mastitis' or 'Ketosis'.",
    )
    collection_method: str | None = Field(
        default=None,
        description="The tool or process used, e.g., 'Sterile Strip' or 'Vacutainer'.",
    )
    technician_id: int | str | None = Field(
        default=None,
        description="Identifier of the person (Vet or Farm Staff) who collected the sample.",
    )
    is_pooled: bool = Field(
        default=False,
        description="True if the sample contains material from multiple cows (e.g. bulk tank or pen pool).",
    )


class ExitMetadata(EventMetadataModel):
    """Exit event metadata."""

    departure_type: DepartureType | None = Field(
        default=None,
        description="Enumeration for exit reason based on Fetrow et al., 2006.",
    )
    departure_reason: DepartureReason | None = Field(
        default=None,
        description="Reason for exit of the cow, based on ICAR enum.",
    )


class MilkRecordingMetadata(EventMetadataModel):
    """Milk recording event metadata."""

    lactose_percentage: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Percentage of lactose in milk, between 0 and 100.",
    )
    fat_percentage: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Percentage of fat in milk, between 0 and 100.",
    )
    protein_percentage: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Percentage of protein in milk, between 0 and 100.",
    )
    scc: int | None = Field(
        default=None,
        ge=0,
        description="Somatic Cell Count, an indicator of udder health. cells/ml raw milk",
    )
    milking_yield: float | None = Field(
        default=None,
        ge=0,
        description="Total daily milk yield in kilograms (or liters).",
    )


class MilkMeterYieldsMetadata(EventMetadataModel):
    """
    Milk meter yields event metadata.

    Represents milk production of a single milking session measured by a milk
    meter on a milk robot or in a milk parlour.
    """

    milking_yield: float | None = Field(
        default=None,
        ge=0,
        description="Amount of milk produced during the session, measured in kg (or liters).",
    )
    start_time: datetime | None = Field(
        default=None,
        description="Start time of milking session (format: YYYY-MM-DD HH:MM:SS).",
    )
    end_time: datetime | None = Field(
        default=None,
        description="End time of milking session (format: YYYY-MM-DD HH:MM:SS).",
    )
    robot_id: int | None = Field(
        default=None,
        gt=0,
        description="ID of the robot as attributed at the farm (for example: 5).",
    )
    robot_name: str | None = Field(
        default=None,
        description='Name of the robot (for example: "Astronaut 102").',
    )
    failure: bool | None = Field(
        default=None,
        description="Indicates if the robot encountered an error during the session (true/false).",
    )
    refusal: bool | None = Field(
        default=None,
        description="Indicates if the cow refused milking or interrupted the system (true/false).",
    )
    milking_speed: float | None = Field(
        default=None,
        ge=0,
        description="Average speed of milking during the session (kg/min).",
    )
    body_weight: int | None = Field(
        default=None,
        ge=0,
        description="Body weight of the animal measured during the session, in kg.",
    )
    milking_session: int | None = Field(
        default=None,
        ge=1,
        description="Session number of milking on that day (1 for first session, 2 for second, etc.).",
    )


class BodyWeightKgMetadata(EventMetadataModel):
    """
    Body weight event metadata.

    Represents the body weight of an animal measured during a session.
    """

    body_weight_kg: int | None = Field(
        default=None,
        ge=0,
        description="Body weight of the animal measured, in kg.",
    )


class BodyConditionScoreMetadata(EventMetadataModel):
    """
    Body condition score event metadata.

    Represents the body condition score (BCS) of an animal.
    """

    body_condition_score: float | None = Field(
        default=None,
        ge=1,
        le=5,
        description="Body condition score (BCS) of the animal on a 1-5 scale.",
    )


class LamenessScoreMetadata(EventMetadataModel):
    """
    Lameness score event metadata.

    Represents a locomotion or lameness assessment. Scoring schemes vary by
    protocol (for example 0-3 or 1-5); the numeric value is stored as recorded.
    """

    lameness_score: int | None = Field(
        default=None,
        ge=0,
        le=5,
        description=(
            "Lameness or locomotion score as recorded (typical scales include "
            "0-3 or 1-5 depending on the assessment protocol)."
        ),
    )
    affected_leg: LamenessAffectedLeg | None = Field(
        default=None,
        description=(
            "Primarily affected limb when recorded; `not_recorded` when the score "
            "is not tied to a single leg or the limb was not specified."
        ),
    )
    observation_context: LamenessObservationContext | None = Field(
        default=None,
        description="Where or how the animal was observed for this assessment.",
    )


class GenomeTestMetadata(EventMetadataModel):
    """
    Genome test event metadata.

    Represents a genomic test performed for an animal. The actual result payload
    can be stored externally and referenced here.
    """

    provider: str | None = Field(
        default=None,
        description='Testing provider or lab (for example: "CDC Bovine", "Neogen").',
    )
    test_name: str | None = Field(
        default=None,
        description='Test or panel name (for example: "CLARIFIDE Plus").',
    )
    sample_id: str | None = Field(
        default=None,
        description="Identifier of the biological sample used for the test (if provided).",
    )
    result_uri: str | None = Field(
        default=None,
        description="URI/location of the genomic test result file (if stored externally).",
    )


class FeedIntakeMetadata(EventMetadataModel):
    """
    Feed intake event metadata.

    Represents feed consumption of concentrates per eating session.
    """

    product_id: int | None = Field(
        default=None,
        gt=0,
        description="ID of the feed product assigned by the farm.",
    )
    product_category: str | None = Field(
        default=None,
        description='Category of feed (for example: "Concentrate").',
    )
    feed_dry_matter_content_uni_id: int | None = Field(
        default=None,
        gt=0,
        description="ID for the dry matter content unit (for example: 1).",
    )
    product_name: str | None = Field(
        default=None,
        description='Name of the feed product (for example: "VS 2 RB eiwit").',
    )
    intake_programmed_kg: float | None = Field(
        default=None,
        ge=0,
        description="Maximum intake allowed for that day or visit, in kg (for example: 1.1).",
    )
    intake_consumed_kg: float | None = Field(
        default=None,
        ge=0,
        description="Actual intake consumed for that day or visit, in kg (for example: 0.56).",
    )
    feed_intake_session: int | None = Field(
        default=None,
        ge=1,
        description="Session number for eating on that day (for example: 1 for first session, 2 for second).",
    )
    start_time: datetime | None = Field(
        default=None,
        description="Start time of feeding session (format: YYYY-MM-DD HH:MM:SS).",
    )
    end_time: datetime | None = Field(
        default=None,
        description="End time of feeding session (format: YYYY-MM-DD HH:MM:SS).",
    )


class SensorMeasurementMetadata(EventMetadataModel):
    """Sensor measurement event metadata."""

    sensor_measurement_type: SensorMeasurementType = Field(
        description="Type of sensor measurement.",
    )
    sensor_name: str | None = Field(
        default=None,
        description="Name of the sensor (e.g., 'CowManager', 'SCR Heatime').",
    )
    sensor_version: str | None = Field(
        default=None,
        description="Version of the sensor or software (e.g., 'v2.1').",
    )
    value: float = Field(
        ge=0,
        description="Measured value. For durations (minutes) or steps depending on measurement type.",
    )
    unit: str | None = Field(
        default=None,
        description="Optional unit of measurement, e.g., 'min', 'steps'.",
    )
    start_time: datetime | None = Field(
        default=None,
        description="Start of measurement interval (if applicable).",
    )
    end_time: datetime | None = Field(
        default=None,
        description="End of measurement interval (if applicable).",
    )


class DiseaseMetadata(EventMetadataModel):
    """
    Disease metadata — describes the condition itself.

    Nested inside DiagnosisMetadata. Captures the clinical characterisation of
    what the animal has, independent of how or when it was detected.
    """

    disease_code: DiseaseCode | None = Field(
        default=None,
        description=(
            "Standardised disease code. Use OTH when the condition is not in the "
            "DiseaseCode enum and provide free-text in disease_description."
        ),
    )
    disease_description: str | None = Field(
        default=None,
        description=(
            "Free-text description of the condition. Required when disease_code is OTH; "
            'optional extra detail otherwise (e.g. "Left front quarter mastitis, right displacement of the abomasum ").'
        ),
    )
    stage: DiagnosisStage | None = Field(
        default=None,
        description=(
            "Stage of disease progression at time of diagnosis. "
            "Reference: https://github.com/adewg/ICAR/blob/ADE-1/enums/icarDiagnosisStageType.json"
        ),
    )


class DiagnosisMetadata(EventMetadataModel):
    """
    Diagnosis event metadata — describes the act of identifying a condition.

    Captures who detected the disease, how, how certain they are, and what
    follow-up is needed. The disease itself is described in the nested
    `disease` field.
    """

    disease: DiseaseMetadata | None = Field(
        default=None,
        description="Nested model describing the disease or condition that was diagnosed.",
    )
    severity: DiagnosisSeverity | None = Field(
        default=None,
        description=(
            "Clinical severity at time of diagnosis. "
            "Reference: https://github.com/adewg/ICAR/blob/ADE-1/enums/icarDiagnosisSeverityType.json"
        ),
    )
    diagnosis_method: DiagnosisMethod | None = Field(
        default=None,
        description='Method used to identify the condition (e.g. "clinical", "laboratory").',
    )
    confirmation_status: ConfirmationStatus | None = Field(
        default=None,
        description="Whether this is a suspected or confirmed diagnosis.",
    )
    diagnostic_source: DiagnosticSource | None = Field(
        default=None,
        description="Who or what made the diagnosis (vet, farm worker, sensor, lab).",
    )
    notes: str | None = Field(
        default=None,
        description="Additional free-text clinical notes from the diagnosing party.",
    )


class TreatmentMetadata(EventMetadataModel):
    """
    Treatment event metadata — describes a single drug application or intervention.

    One Treatment event = one application. When a course requires multiple
    applications, each gets its own event linked via treatment_course_id.
    """

    # --- Link back to the condition being treated ---
    disease_code: DiseaseCode | None = Field(
        default=None,
        description=(
            "Disease code of the condition being treated. Allows linking to a "
            "Diagnosis event without a strict foreign key."
        ),
    )

    # --- Course tracking ---
    treatment_course_id: int | None = Field(
        default=None,
        gt=0,
        description=(
            "Shared identifier grouping all Treatment events in the same course, "
            "assigned by the source system."
        ),
    )
    application_number: int | None = Field(
        default=None,
        ge=1,
        description="Sequence of this application within its course (1 = first, 2 = second, …).",
    )
    total_applications: int | None = Field(
        default=None,
        ge=1,
        description="Total number of applications planned for the full treatment course.",
    )
    frequency: TreatmentFrequency | None = Field(
        default=None,
        description="How often the drug is applied within the course.",
    )

    # --- Drug ---
    drug_id: int | None = Field(
        default=None,
        gt=0,
        description="Identifier of the drug as registered in the farm or veterinary system.",
    )
    drug_name: str | None = Field(
        default=None,
        description='Commercial or generic name of the drug (e.g. "Penicillin G", "Metacam").',
    )
    dosage: float | None = Field(
        default=None,
        ge=0,
        description="Amount of drug administered in this single application.",
    )
    dosage_unit: str | None = Field(
        default=None,
        description='Unit for the dosage field (e.g. "ml", "g", "tablet").',
    )
    route_of_administration: RouteOfAdministration | None = Field(
        default=None,
        description="Route by which the drug was administered.",
    )

    # --- Timing ---
    treatment_start_time: datetime | None = Field(
        default=None,
        description="Date/time this specific application started.",
    )
    treatment_end_time: datetime | None = Field(
        default=None,
        description="Date/time this specific application ended.",
    )
    course_end_date: date | None = Field(
        default=None,
        description="Calendar date the full treatment course is expected to end (format: YYYY-MM-DD).",
    )

    # --- Regulatory ---
    milk_withdrawal_days: int | None = Field(
        default=None,
        ge=0,
        description=(
            "Days milk must be withheld after the last application of the course."
        ),
    )
    meat_withdrawal_days: int | None = Field(
        default=None,
        ge=0,
        description=(
            "Days before this animal may enter the food chain after the last application."
        ),
    )
    prescription_id: str | None = Field(
        default=None,
        description=(
            "Veterinary prescription reference number. Required in many jurisdictions "
            "for prescription-only medicines."
        ),
    )

    # --- Operator & outcome ---
    operator_id: int | None = Field(
        default=None,
        gt=0,
        description="Numeric identifier of the person who administered the treatment.",
    )
    treated_by: str | None = Field(
        default=None,
        description=(
            "Name or role of the person who administered the treatment "
            '(e.g. "vet", "farm_worker_id:42"). Complements operator_id.'
        ),
    )
    response_status: TreatmentResponseStatus | None = Field(
        default=None,
        description="Observed animal response recorded at end of or after the course.",
    )
    notes: str | None = Field(
        default=None,
        description="Additional free-text notes on the treatment.",
    )


__all__ = [
    "EventMetadataModel",
    "HerdEntryMetadata",
    "HerdMoveMetadata",
    "BirthMetadata",
    "BreedingMetadata",
    "CalvingMetadata",
    "BodyWeightKgMetadata",
    "BodyConditionScoreMetadata",
    "LamenessScoreMetadata",
    "GenomeTestMetadata",
    "ExitMetadata",
    "MilkRecordingMetadata",
    "MilkMeterYieldsMetadata",
    "FeedIntakeMetadata",
    "DiagnosisSampleMetadata",
    "SensorMeasurementMetadata",
    "DiseaseMetadata",
    "DiagnosisMetadata",
    "TreatmentMetadata",
]

ALL_METADATA = [globals()[name] for name in __all__]
