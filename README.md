# farm-data-definitions
Canonical farm data definitions used by the Bovi-Analytics Lab.

## Install

```bash
pip install -e .
```

## Quick Start

```python
from datetime import datetime, timezone

from farm_data_definitions import (
    AnimalGender,
    BirthDetail,
    Cow,
    Event,
    EventType,
    Herd,
)

cow = Cow(animal_id=1, gender=AnimalGender.FEMALE, birth_date=datetime(2020, 1, 1).date())
herd = Herd(herd_identifier=1001)

# Direct model construction.
event = Event(
    event_id=1,
    event_type=EventType.BIRTH,
    animal_id=1,
    timestamp=datetime.now(timezone.utc),
)

# Typed detail payload + direct Event construction.
birth_detail = BirthDetail(calving_ease_type=None, parturition_birth_status_type=None)
birth_event = Event(
    event_id=2,
    event_type=EventType.BIRTH,
    animal_id=1,
    timestamp=datetime.now(timezone.utc),
    detail=birth_detail.model_dump(exclude_none=False),
)
```

## Model Reference

- `Cow`: Animal identity, pedigree, and lifecycle record.
- `Herd`: Herd identity, location, and cow membership context.
- `Event`: Timeline event envelope with `event_type`, `timestamp`, and `detail`.
- `Event detail models`: Typed detail contracts for constructing `Event.detail` payloads.
- `Lactation`: Pending (not yet implemented/exported).

## Notes

- Canonical import path is `farm_data_definitions`.
- Data model field names are snake_case.
- `Lactation` is intentionally pending while requirements are finalized.
