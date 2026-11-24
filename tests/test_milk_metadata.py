"""Milk quality (fat, protein, lactose, SCC) belongs to milk recordings only."""

import pytest
from pydantic import ValidationError

from bovidaeta import (
    AggregatedMilkMeterYieldsMetadata,
    AggregationPeriod,
    MilkMeterYieldsMetadata,
    MilkRecordingMetadata,
)

QUALITY = {
    "lactose_percentage": 4.7,
    "fat_percentage": 4.1,
    "protein_percentage": 3.4,
    "scc": 120_000,
}


def test_milk_recording_has_quality_fields():
    assert MilkRecordingMetadata(milking_yield=30.0, **QUALITY).scc == 120_000


@pytest.mark.parametrize("field", QUALITY)
def test_milk_meter_events_reject_quality_fields(field):
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        MilkMeterYieldsMetadata(milking_yield=15.0, **{field: QUALITY[field]})
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        AggregatedMilkMeterYieldsMetadata(
            aggregation_period=AggregationPeriod.DAY,
            milking_yield=30.0,
            **{field: QUALITY[field]},
        )
