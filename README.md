# farm-data-definitions

Canonical farm data definitions used by the Bovi-Analytics Lab.

## Install

```bash
pip install -e .
```

## Quick Start

```python
from datetime import datetime, timezone
from uuid import uuid4

from farm_data_definitions import (
    AnimalGender,
    BirthMetadata,
    Cow,
    Event,
    EventType,
    Herd,
)

cow_id = uuid4()
herd_id = uuid4()

cow = Cow(
    animal_id=cow_id,
    herd_id=herd_id,
    gender=AnimalGender.FEMALE,
    birth_date=datetime(2020, 1, 1).date(),
)
herd = Herd(herd_id=herd_id)

# Direct model construction.
event = Event(
    event_id=uuid4(),
    event_type=EventType.BIRTH,
    animal_id=cow_id,
    timestamp=datetime.now(timezone.utc),
)

# Typed metadata payload + direct Event construction.
birth_metadata = BirthMetadata(calving_ease_type=None, parturition_birth_status_type=None)
birth_event = Event(
    event_id=uuid4(),
    event_type=EventType.BIRTH,
    animal_id=cow_id,
    timestamp=datetime.now(timezone.utc),
    metadata=birth_metadata.model_dump(exclude_none=False),
)
```

## Model Reference

- `Cow`: Animal identity, pedigree, and lifecycle record.
- `Herd`: Herd identity and location metadata.
- `Event`: Timeline event envelope with `event_type`, `timestamp`, and `metadata`.
- `Event metadata models`: Typed metadata contracts for constructing `Event.metadata` payloads.
- `Lactation`: Pending (not yet implemented/exported).

## Notes

- Canonical import path is `farm_data_definitions`.
- Data model field names are snake_case.
- `Lactation` is intentionally pending while requirements are finalized.
