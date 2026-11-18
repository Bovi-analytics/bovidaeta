from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Herd(BaseModel):
    """
    Represents a herd: a group of cattle at the same geospatial location.

    One farm can therefore have multiple herds when cattle are housed at
    multiple locations. `herd_id` is mandatory.
    """

    model_config = ConfigDict(extra="forbid")

    herd_id: UUID = Field(
        description="UUID identifier for the herd.",
    )
    name: str | None = Field(
        default=None,
        description="Name of the herd as given by the farmer.",
    )
    source_id: int | None = Field(
        default=None,
        gt=0,
        description="Unique identifier for the data source",
    )
    data_provider_guid: str | None = Field(
        default=None,
        description="Globally unique identifier for the data provider.",
    )
    street: str | None = Field(
        default=None,
        description="Street name of herd location.",
    )
    number: str | None = Field(
        default=None,
        description="House number of herd location.",
    )
    registration_number: str | None = Field(
        default=None,
        description=(
            "Registration number of the herd as provided by the government "
            "(for example: UBN in the Netherlands)."
        ),
    )
    zip: str | None = Field(
        default=None,
        description="Zip code/postal code of herd location.",
    )
    city: str | None = Field(
        default=None,
        description="City name of herd location.",
    )
    state: str | None = Field(
        default=None,
        description="State name of herd location.",
    )
    country: str | None = Field(
        default=None,
        description="Country name of herd location.",
    )
    country_code: str | None = Field(
        default=None,
        min_length=2,
        max_length=2,
        description=(
            "Alpha-2 code of ISO 3166-1 for the country "
            "(https://en.wikipedia.org/wiki/ISO_3166-1)."
        ),
    )
    latitude: float | None = Field(
        default=None,
        ge=-90,
        le=90,
        description=(
            "A geographic coordinate that specifies the north-south position of "
            "the herd on the surface of the Earth."
        ),
    )
    longitude: float | None = Field(
        default=None,
        ge=-180,
        le=180,
        description=(
            "A geographic coordinate that specifies the east-west position of "
            "the herd on the surface of the Earth."
        ),
    )
    email: str | None = Field(
        default=None,
        description="Email address of the farmer.",
    )
    mobile_phone_number: str | None = Field(
        default=None,
        description="Mobile phone number of the farmer.",
    )
    telephone_number: str | None = Field(
        default=None,
        description="Telephone number of the farmer.",
    )

    @field_validator("country_code")
    @classmethod
    def normalize_country_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()
