from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .enums import AnimalGender, Breed


class BreedPart(BaseModel):
    """
    A class to represent the breed composition of a cow.

    Breed is expressed as percentages, often in eighths. A cow can be, for
    example, 100% HOL (8/8), 50% HOL and 50% JER (4/8 + 4/8), or 50% HOL and
    25% JER and 25% AAN.

    Reference: https://interbull.org/ib/icarbreedcodes.
    """

    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    breed_code: Breed = Field(
        description='The name/code of the breed (for example: "HOL", "JER", or "AAN").',
    )
    proportion: float = Field(
        ge=0,
        le=1,
        description=(
            "The proportion of this breed in the cow (for example: 1.0 for 100% HOL, "
            "0.5 or 4/8 for 50% HOL)."
        ),
    )

    def __str__(self) -> str:
        return f"{self.breed_code} {int(self.proportion * 100)}%"


class Cow(BaseModel):
    """
    A class to represent a cow.

    Specify at least `animal_id`, `herd_id`, and `gender`
    when creating a new cow.

    """

    model_config = ConfigDict(extra="forbid")

    animal_id: UUID = Field(
        description=(
            "UUID identifier for the animal record. This identifier is "
            "linked to `herd_id` and remains stable over time."
        ),
    )
    herd_id: UUID = Field(
        description="UUID identifier of the herd this cow belongs to.",
    )

    gender: AnimalGender = Field(
        description=(
            "The animal's gender (male/female), based on ICAR enumeration for sex of "
            "animal using species-independent English names, including "
            "neuter/cryptorchid variations."
        ),
    )
    birth_date: date | None = Field(
        default=None,
        description=(
            "Day the animal was born as recorded by the farmer, format YYYY-MM-DD, "
            "if available add time. Empty when the source does not hold it."
        ),
    )
    exit_date: date | None = Field(
        description=("Day the animal left the herd."),
    )
    animal_ear_tag: str | None = Field(
        default=None,
        description=(
            "The animal's ear tag number, which is official and unique in most (but "
            "not all) countries. In Europe, every cow receives a unique official ear "
            "tag linked to that animal for life (for example EG 911/2004 and "
            "EG1760/2000)."
        ),
    )
    animal_farm_name: str | None = Field(
        default=None,
        description="The animal's name most commonly used on the farm (barn name).",
    )
    animal_farm_number: int | None = Field(
        default=None,
        gt=0,
        description=(
            "The animal's number most commonly used on the farm (work number), for "
            "example on a collar or burn mark; it can be reused over time on the farm."
        ),
    )
    genetic_dam_ear_tag: str | None = Field(
        default=None,
        description="The animal's dam ear tag number.",
    )
    genetic_dam_id: UUID | None = Field(
        default=None,
        description="UUID identifier of the animal's dam.",
    )
    sire_ear_tag: str | None = Field(
        default=None,
        description="The animal's sire ear tag number.",
    )
    sire_id: UUID | None = Field(
        default=None,
        description="UUID identifier of the animal's sire.",
    )
    animal_legal_id: str | None = Field(
        default=None,
        description="In EU countries, this is typically the same as the animal ear tag.",
    )
    animal_isorfid_starting_manufacturer: str | None = Field(
        default=None,
        description="ISO RFID tag starting with manufacturer code.",
    )
    animal_isorfid_starting_country_code: str | None = Field(
        default=None,
        description=(
            "ISO RFID tag starting with country code "
            "(https://en.wikipedia.org/wiki/ISO_11784_%26_11785)."
        ),
    )
    animal_herd_book_name: str | None = Field(
        default=None,
        description="A name given to the animal by an official herd book.",
    )
    animal_usda: str | None = Field(
        default=None,
        description=(
            "A number used by the US Department of Agriculture for animal "
            "identification "
            "(https://www.aphis.usda.gov/aphis/ourfocus/animalhealth/nvap/"
            "NVAP-Reference-Guide/Animal-Identification/Animal-Identification)."
        ),
    )
    animal_dhia: str | None = Field(
        default=None,
        description="A number used by the US DHIA (http://www.dhia.org).",
    )
    recipient_dam_id: UUID | None = Field(
        default=None,
        description=(
            "UUID identifier of the animal's surrogate dam; only applies when the "
            "cow was born using assisted reproductive technologies such as in vitro "
            "embryo production or embryo transfer."
        ),
    )
    breed: list[BreedPart] = Field(
        default=[BreedPart(breed_code=Breed.HOL, proportion=0.99)],
        description=(
            "The animal's breed expressed as a list of `BreedPart`. When unknown, "
            "the default is 99% HOL."
        ),
    )
    born_on_farm: bool | None = Field(
        default=None,
        description="Boolean indicating if the animal was born on the herd linked to the herd identifier.",
    )
