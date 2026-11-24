from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Study(BaseModel):
    """
    A research study whose data is stored next to (or instead of) farm data.

    Studies can be grouped in a `project` (for example all studies of GEMS).
    Events recorded by a study carry its `study_id`; which animals took part
    is recorded with `StudyAnimal`. Farm data has no studies.
    """

    model_config = ConfigDict(extra="forbid")

    study_id: UUID = Field(
        description="UUID identifier of the study.",
    )
    project: str | None = Field(
        default=None,
        description='Project the study belongs to, for example "GEMS".',
    )
    name: str | None = Field(
        default=None,
        description="Short name of the study.",
    )
    description: str | None = Field(
        default=None,
        description="What the study investigated.",
    )
    start_date: date | None = Field(
        default=None,
        description="First day of the study.",
    )
    end_date: date | None = Field(
        default=None,
        description="Last day of the study.",
    )
    doi_or_protocol_url: str | None = Field(
        default=None,
        description="DOI of the publication, or a URL of the study protocol.",
    )
    open_data: bool = Field(
        default=False,
        description="Whether the study's data may be included in open-source exports.",
    )
    license: str | None = Field(
        default=None,
        description='License the data is shared under, for example "CC-BY-4.0".',
    )
    credit_required: bool | None = Field(
        default=None,
        description="Whether the study's contributors ask for authorship credit.",
    )
    contributors: str | None = Field(
        default=None,
        description="Names and/or ORCIDs of the contributors, or a citation string.",
    )

    @model_validator(mode="after")
    def _end_after_start(self) -> Study:
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError(
                f"end_date ({self.end_date}) is before start_date ({self.start_date})"
            )
        return self


class StudyAnimal(BaseModel):
    """
    An animal that took part in a study.

    An animal keeps one `animal_id` across studies, so it can take part in
    more than one: one `StudyAnimal` per (study, animal) pair.
    """

    model_config = ConfigDict(extra="forbid")

    study_id: UUID = Field(
        description="UUID identifier of the study.",
    )
    animal_id: UUID = Field(
        description="UUID identifier of the animal.",
    )
    study_group: str | None = Field(
        default=None,
        description="Group the animal was in within the study, for example a treatment arm.",
    )
