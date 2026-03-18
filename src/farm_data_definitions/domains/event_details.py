from __future__ import annotations

"""
Typed detail payloads for timeline events.

This module describes timeline event metadata parameters that need extra
definition in the domain model.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .enums import (
    BreedingType,
    CalvingEaseType,
    DepartureReason,
    DepartureType,
    GenderSorting,
    ParturitionBirthStatusType,
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
    


__all__ = [
    "EventDetailModel",
    "BirthDetail",
    "BreedingDetail",
    "CalvingDetail",
    "ExitDetail",
    "MilkRecordingDetail",
    "MilkMeterYieldsDetail",
    "FeedIntakeDetail",
]
