from bovidaeta import EventType
from bovidaeta.event_metadata import (
    CalvingMetadata,
    LabMeasurementMetadata,
    SensorMeasurementMetadata,
)


def test_lab_measurement_metadata():
    meta = LabMeasurementMetadata(
        analyte="calcium", value=2.3, unit="mmol/L", sample_type="blood_serum"
    )
    assert meta.sample_type == "blood_serum"
    assert EventType.LAB_MEASUREMENT.value == "LabMeasurement"


def test_calving_metadata_extensions():
    meta = CalvingMetadata(calving_duration_hours=1.5, calf_removal="after_colostrum")
    assert meta.calf_removal == "after_colostrum"


def test_sensor_statistic_and_new_types():
    meta = SensorMeasurementMetadata(
        sensor_measurement_type="lying_bout_duration",
        value=60.0,
        unit="min",
        statistic="median",
    )
    assert meta.statistic == "median"
    SensorMeasurementMetadata(sensor_measurement_type="inactive_time", value=10.0)
