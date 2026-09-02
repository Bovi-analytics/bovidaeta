<img src="assets/badge.svg" alt="Logo" width="200">

# bovidaeta

Farm and cattle domain definitions created by the [Bovi-Analytics Lab](https://bovi-analytics.org/).

## Install

```bash
pip install -e .
```

Or add to a `uv` project with:

```bash
uv add /path/to/bovidaeta
```

After making local changes to the library, update the installation in a `uv` project with:

```bash
uv pip install /path/to/bovidaeta --reinstall
```

## Quick Start

```python
from datetime import datetime, timezone
from uuid import uuid4

from bovidaeta import (
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
    datetime=datetime.now(timezone.utc),
)

# Typed metadata payload + direct Event construction.
birth_metadata = BirthMetadata(calving_ease_type=None, parturition_birth_status_type=None)
birth_event = Event(
    event_id=uuid4(),
    event_type=EventType.BIRTH,
    animal_id=cow_id,
    datetime=datetime.now(timezone.utc),
    metadata=birth_metadata.model_dump(exclude_none=False),
)
```

## Model Reference

- `Cow`: Animal identity, pedigree, and lifecycle record.
- `Herd`: Herd identity and location metadata.
- `Event`: Timeline event envelope with `event_type`, `datetime`, and `metadata`.
- `Event metadata models`: Typed metadata contracts for constructing `Event.metadata` payloads.
- `Lactation`: Pending (not yet implemented/exported).
