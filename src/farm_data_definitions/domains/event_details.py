from __future__ import annotations

"""
Typed detail payloads for timeline events.

This module describes timeline event metadata parameters that need extra
definition in the domain model.
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from .enums import (
    BreedingType,
    CalvingEaseType,
    ConfirmationStatus,
    DepartureReason,
    DepartureType,
    DiagnosisMethod,
    DiagnosisSeverity,
    DiagnosisStage,
    DiagnosticSource,
    DiseaseCode,
    GenderSorting,
    ParturitionBirthStatusType,
    RouteOfAdministration,
    TreatmentFrequency,
    TreatmentResponseStatus,
)


class EventDetailModel(BaseModel):
    """Base class representing timeline event metadata."""

    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class BirthDetail(EventDetailModel):
    """Birth event metadata."""

    calving_ease_type: CalvingEaseType | None = Field(
        default=None,
        description="Ease of being born of this cow, based on ICAR enum.",
    )
    parturition_birth_status_type: ParturitionBirthStatusType | None = Field(
        default=None,
        description="The way this calf was born, based on ICAR enum.",
    )


class BreedingDetail(EventDetailModel):
    """Breeding event metadata."""

    bull_identifier: int | None = Field(
        default=None,
        gt=0,
        description="Identifier of the bull used for breeding, unique number within the system.",
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


class CalvingDetail(EventDetailModel):
    """Calving event metadata."""

    calving_ease_type: CalvingEaseType | None = Field(
        default=None,
        description="Ease of the birthing process, based on ICAR enum.",
    )
    parturition_birth_status_type: ParturitionBirthStatusType | None = Field(
        default=None,
        description="The way a calf was born, based on ICAR enum.",
    )


class ExitDetail(EventDetailModel):
    """Exit event metadata."""

    departure_type: DepartureType | None = Field(
        default=None,
        description="Enumeration for exit reason based on Fetrow et al., 2006.",
    )
    departure_reason: DepartureReason | None = Field(
        default=None,
        description="Reason for exit of the cow, based on ICAR enum.",
    )


class MilkRecordingDetail(EventDetailModel):
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


class MilkMeterYieldsDetail(EventDetailModel):
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


class FeedIntakeDetail(EventDetailModel):
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


class DiseaseDetail(EventDetailModel):
    """
    Disease metadata — describes the condition itself.

    Nested inside DiagnosisDetail. Captures the clinical characterisation of
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
            'optional extra detail otherwise (e.g. "Left front quarter mastitis").'
        ),
    )
    stage: DiagnosisStage | None = Field(
        default=None,
        description=(
            "Stage of disease progression at time of diagnosis. "
            "Reference: https://github.com/adewg/ICAR/blob/ADE-1/enums/icarDiagnosisStageType.json"
        ),
    )
    affected_system: str | None = Field(
        default=None,
        description=(
            'Body system primarily affected (e.g. "udder", "metabolic", '
            '"reproductive", "respiratory", "locomotion").'
        ),
    )
    body_part: str | None = Field(
        default=None,
        description=(
            'Specific anatomical location (e.g. "left front quarter", '
            '"right hind hoof", "uterus").'
        ),
    )
    laterality: str | None = Field(
        default=None,
        description=(
            'Side of the body affected when relevant '
            '(e.g. "left", "right", "bilateral", "LFQ" for left front quarter).'
        ),
    )
    onset_time: datetime | None = Field(
        default=None,
        description=(
            "Estimated date/time when the condition first started. "
            "May be earlier than detection_time in DiagnosisDetail."
        ),
    )
    recurrence: bool | None = Field(
        default=None,
        description=(
            "True if this is a recurring episode of the same condition in this "
            "lactation; False if it is the first occurrence."
        ),
    )


class DiagnosisDetail(EventDetailModel):
    """
    Diagnosis event metadata — describes the act of identifying a condition.

    Captures who detected the disease, how, how certain they are, and what
    follow-up is needed. The disease itself is described in the nested
    `disease` field.
    """

    disease: DiseaseDetail | None = Field(
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
    diagnosed_by: str | None = Field(
        default=None,
        description=(
            "Name or identifier of the specific person who made the diagnosis. "
            'Complements diagnostic_source (e.g. "Dr. Smith", "farm_worker_id:42").'
        ),
    )
    detection_time: datetime | None = Field(
        default=None,
        description=(
            "Exact date/time the condition was detected. May differ from the event "
            "timestamp if there was a recording delay."
        ),
    )
    follow_up_date: date | None = Field(
        default=None,
        description="Recommended calendar date for a follow-up check (format: YYYY-MM-DD).",
    )
    notes: str | None = Field(
        default=None,
        description="Additional free-text clinical notes from the diagnosing party.",
    )


class TreatmentDetail(EventDetailModel):
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
            'Name or role of the person who administered the treatment '
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
    "EventDetailModel",
    "BirthDetail",
    "BreedingDetail",
    "CalvingDetail",
    "ExitDetail",
    "MilkRecordingDetail",
    "MilkMeterYieldsDetail",
    "FeedIntakeDetail",
    "DiseaseDetail",
    "DiagnosisDetail",
    "TreatmentDetail",
]
