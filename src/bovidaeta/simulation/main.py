"""Generate a plausible dummy farm database.

Produces the SQLite format described by `bovidaeta/schemas/sqlite.sql`, so
that `DairyData.from_sqlite` and `examples/sqlite_quickstart.py` can be run
without a real farm export. The simulation is heavily simplified and not
optimised for speed. We aim for biological plausibility where possible, but
results are only intended for testing, not serious analysis.
"""

import json
import math
import os
import random
import sqlite3
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from pydantic import BaseModel

import bovidaeta.event_metadata as meta
from bovidaeta import Event, EventType, enums
from bovidaeta.schemas import SQLITE_SCHEMA, read_schema

DATA_DIR = Path.home() / "nsf-data/"
DB_PATH = DATA_DIR / "dairy_farm.db"

def _uuid7() -> uuid.UUID:
    """A time-ordered UUID (RFC 9562 version 7) for event ids.

    Successive ids increase, so the AnimalEvents primary key grows at its end
    instead of at a random place for every insert: far less random I/O,
    which makes writing a large farm several times faster on slow or shared
    disks. The random part comes from os.urandom, so it doesn't consume the
    simulation's (seedable) `random` stream.
    """
    ms = time.time_ns() // 1_000_000
    rand = int.from_bytes(os.urandom(10), "big")  # 80 bits, 74 used
    value = (ms & ((1 << 48) - 1)) << 80
    value |= 0x7 << 76  # version
    value |= ((rand >> 62) & 0xFFF) << 64  # rand_a, 12 bits
    value |= 0b10 << 62  # variant
    value |= rand & ((1 << 62) - 1)  # rand_b, 62 bits
    return uuid.UUID(int=value)


# Farm numbers: the work number a farmer reads off the cow and types to ask about her, so a
# short 5-digit number (43905) rather than a UUID. Stored as `animal_farm_number`. Numbers
# start at 10000 so they all have the same length; 90,000 is plenty for one simulated farm.
NUMBER_MIN, NUMBER_MAX = 10_000, 99_999


class FarmNumbers:
    """Hands out unique, random 5-digit farm numbers for one farm."""

    def __init__(self):
        self.used: set[int] = set()

    def new(self) -> int:
        if len(self.used) > 0.9 * (NUMBER_MAX - NUMBER_MIN + 1):
            raise RuntimeError("ran out of farm numbers")
        while True:
            number = random.randint(NUMBER_MIN, NUMBER_MAX)
            if number not in self.used:
                self.used.add(number)
                return number


# Reset by each Farm, so farm numbers are unique within one farm database.
FARM_NUMBERS = FarmNumbers()


class SimConfig(BaseModel):
    target_herd_size: int = 200
    sim_years: float = 10
    sim_end_date: date | None = None
    gestation_days: int = 280
    days_to_dry_off: int = 60
    voluntary_waiting_period: int = 50
    heifer_breeding_age: int = 400
    heat_cycle_days: int = 21
    conception_rate: float = 0.38
    # Per-cow daily probability of a clinical case, before that cow's own
    # susceptibility multiplier is applied. Roughly 0.3 cases/cow/year at
    # the median.
    daily_disease_prob: float = 0.0008
    daily_base_cull_prob: float = 0.0008
    daily_abortion_prob: float = 0.0001  # For pregnancies between 42-260 days
    weaning_age: int = 60
    genome_test_age: int = 7
    dnb_age_threshold: int = 2920  # ~8 years
    herd_variation_p: float = 0.05
    milking_times: list[int] = [5, 13, 21]
    peak_yield_mean: float = 38.0
    peak_yield_sd: float = 6.0
    mastitis_recovery_days: int = 30
    mastitis_acute_yield_factor: float = 0.75
    mastitis_permanent_yield_loss: float = 0.04
    milking_session_duration: float = 1.5  # Hours to milk all cows
    feeding_duration: float = 0.5  # Time to provide feed to all cows


def _exit_metadata(cow: "SimCow", reason_hint: str) -> dict:
    """Departure metadata for a cull.

    `reason_hint` is how the herd logic decided: `"routine"` for the daily
    background cull, `"capacity"` when the herd is over target and the
    oldest and do-not-breed cows go first.
    """
    if reason_hint == "capacity":
        reason = (
            enums.DepartureReason.AGE
            if cow.is_dnb
            else enums.DepartureReason.SUPERFLUOUS
        )
    elif cow.mastitis_cases >= 3:
        reason = enums.DepartureReason.MASTITIS
    else:
        reason = random.choices(
            [
                enums.DepartureReason.FERTILITY,
                enums.DepartureReason.PRODUCTION,
                enums.DepartureReason.LEG_OR_CLAW,
                enums.DepartureReason.HEALTH,
            ],
            weights=[35, 30, 20, 15],
        )[0]

    departure_type = random.choices(
        [
            enums.DepartureType.SLAUGHTER,
            enums.DepartureType.DAIRY_SALE,
            enums.DepartureType.DEATH,
        ],
        weights=[75, 20, 5],
    )[0]
    return meta.ExitMetadata(
        departure_type=departure_type, departure_reason=reason
    ).model_dump()


def _split_yield(day_total: float, n_sessions: int) -> list[float]:
    """Divide a day's milk over its milking sessions, unevenly.

    Sessions are not equal in practice - the interval since the previous
    milking differs - so the split is jittered rather than exactly even,
    while still summing to the day's total.
    """
    weights = [random.uniform(0.8, 1.2) for _ in range(n_sessions)]
    total_weight = sum(weights)
    return [day_total * w / total_weight for w in weights]


DISEASE_DESCRIPTIONS = {
    enums.DiseaseCode.MAS: "Mastitis",
    enums.DiseaseCode.KET: "Ketosis",
    enums.DiseaseCode.RTP: "Retained placenta",
    enums.DiseaseCode.MFV: "Milk fever",
}

# Drug, route and milk withdrawal (days) per disease code.
TREATMENTS = {
    enums.DiseaseCode.MAS: (
        "Cephalexin intramammary",
        enums.RouteOfAdministration.INTRAMAMMARY,
        4,
    ),
    enums.DiseaseCode.KET: (
        "Propylene glycol",
        enums.RouteOfAdministration.ORAL,
        0,
    ),
    enums.DiseaseCode.RTP: (
        "Oxytetracycline",
        enums.RouteOfAdministration.INTRAUTERINE,
        5,
    ),
    enums.DiseaseCode.MFV: (
        "Calcium borogluconate",
        enums.RouteOfAdministration.INTRAVENOUS,
        2,
    ),
}


class SimCow:
    def __init__(
        self,
        age_days: int,
        herd_id: str = "",
        is_milking: bool = False,
        days_in_milk: int = 0,
        days_pregnant: int = 0,
        animal_farm_number: int | None = None,
        birth_date: str | None = None,
        born_on_farm: bool | None = None,
        exit_date: str | None = None,
    ):
        self.id = str(uuid.uuid4())
        self.herd_id = herd_id
        self.age_days = age_days
        self.is_milking = is_milking
        self.days_in_milk = days_in_milk
        self.days_pregnant = days_pregnant
        self.in_herd = True
        self.is_dnb = age_days >= SimConfig().dnb_age_threshold
        # The work number the tools look a cow up by; unique within the farm.
        self.animal_farm_number = animal_farm_number or FARM_NUMBERS.new()
        self.birth_date = birth_date
        self.born_on_farm = born_on_farm
        self.exit_date = exit_date

        self.disease_susceptibility = random.lognormvariate(0.0, 1.0)

        conf = SimConfig()
        self.peak_yield = max(
            12.0, random.gauss(conf.peak_yield_mean, conf.peak_yield_sd)
        )
        self.mastitis_recovery_left = 0  # days of acute yield depression left
        self.mastitis_cases = 0  # lifetime clinical cases, for permanent loss

        # Randomised static metadata (unrealistic values are fine for simulation)
        self.gender = random.choices(["female", "male"], weights=[95, 5])[0]
        self.animal_ear_tag = f"NL {random.randint(100_000_000, 999_999_999)}"
        self.animal_legal_id = self.animal_ear_tag  # mirrors EU convention
        # Breed: mostly pure HOL, occasionally crossed with JER or MRY
        self.breed = random.choices(
            [
                [{"breed_code": "HOL", "proportion": 1.0}],
                [
                    {"breed_code": "HOL", "proportion": 0.75},
                    {"breed_code": "JER", "proportion": 0.25},
                ],
                [
                    {"breed_code": "HOL", "proportion": 0.5},
                    {"breed_code": "MRY", "proportion": 0.5},
                ],
            ],
            weights=[80, 15, 5],
        )[0]

    def create_event(
        self,
        dts: datetime,
        event_type: EventType,
        animal_id: str = "",
        metadata: dict | None = None,
    ) -> Event:
        event_id = _uuid7()
        return Event(
            event_id=event_id,
            event_type=event_type,
            animal_id_source=animal_id or self.id,
            datetime=dts,
            metadata=metadata or {},
        )

    def _get_times(
        self,
        current_date: datetime,
        base_hours: list[int] | list[float],
        duration_all_cows: float,
    ):
        times = []
        for base_hour in base_hours:
            hour_variation = random.gauss(mu=base_hour, sigma=duration_all_cows / 2)
            hour_variation = max(0.0, min(23.99, hour_variation))
            h = int(hour_variation)
            m = int((hour_variation - h) * 60)
            times.append(current_date + timedelta(hours=h, minutes=m))
        times.sort()
        return times

    def daily_yield(self, config: SimConfig) -> float:
        """Expected total kg of milk today, across all milking sessions.

        A coarse stand-in for a lactation curve: yield climbs to a peak
        around 60 days in milk and then declines steadily, scaled by this
        cow's own potential and reduced by her mastitis history.
        """
        dim = max(1, self.days_in_milk)
        # Wood's-curve shape, divided by its own maximum (1.896, at ~67
        # days in milk) so the multiplier peaks at 1.0 and `peak_yield`
        # is correct.
        shape = (dim**0.2) * math.exp(-0.003 * dim) / 1.896
        yield_kg = self.peak_yield * shape

        if self.mastitis_recovery_left > 0:
            yield_kg *= config.mastitis_acute_yield_factor
        permanent_loss = min(
            0.25, self.mastitis_cases * config.mastitis_permanent_yield_loss
        )
        yield_kg *= 1.0 - permanent_loss

        return max(2.0, yield_kg * random.uniform(0.92, 1.08))

    def process_day(self, config: SimConfig, current_date: datetime):
        if not self.in_herd:
            return [], []

        events = []
        new_calves = []
        self.age_days += 1

        # 1. Lifetime Milestones
        if self.age_days == config.genome_test_age:
            genome_meta = meta.GenomeTestMetadata(
                provider=random.choice(["CDC Bovine", "Neogen", "Zoetis"]),
                test_name="CLARIFIDE Plus",
                sample_id=f"SMP-{uuid.uuid4().hex[:6].upper()}",
                result_uri=f"s3://dairy-farm-results/genomes/{self.id}.pdf",
            ).model_dump()
            events.append(
                self.create_event(
                    current_date, EventType.GENOME_TEST, metadata=genome_meta
                )
            )
        elif self.age_days == config.weaning_age:
            events.append(self.create_event(current_date, EventType.WEANING))

        if not self.is_dnb and self.age_days >= config.dnb_age_threshold:
            self.is_dnb = True
            events.append(self.create_event(current_date, EventType.DNB_DECISION))

        # 2. Monthly Evaluations
        if self.age_days > 365 and self.age_days % 30 == 0:
            lameness_meta = meta.LamenessScoreMetadata(
                lameness_score=random.choices(
                    [0, 1, 2, 3, 4, 5], weights=[70, 15, 8, 4, 2, 1]
                )[0],
                affected_leg=None,
                observation_context=None,
            ).model_dump()
            events.append(
                self.create_event(
                    current_date, EventType.LAMENESS_SCORE, metadata=lameness_meta
                )
            )

        # 3. Probabilistic Health Events
        if self.mastitis_recovery_left > 0:
            self.mastitis_recovery_left -= 1

        if random.random() < config.daily_disease_prob * self.disease_susceptibility:
            # Disease mix follows what the Israel export actually contains:
            # mastitis dominates, then ketosis, retained placenta and milk
            # fever. Codes come from the DiseaseCode enum.
            disease_code = random.choices(
                [
                    enums.DiseaseCode.MAS,
                    enums.DiseaseCode.KET,
                    enums.DiseaseCode.RTP,
                    enums.DiseaseCode.MFV,
                ],
                weights=[82, 11, 5, 2],
            )[0]

            if disease_code == enums.DiseaseCode.MAS:
                self.mastitis_cases += 1
                self.mastitis_recovery_left = config.mastitis_recovery_days

            severity = random.choices(
                [
                    enums.DiagnosisSeverity.LIGHT,
                    enums.DiagnosisSeverity.MODERATE,
                    enums.DiagnosisSeverity.SEVERE,
                ],
                weights=[55, 35, 10],
            )[0]

            diagnosis_meta = meta.DiagnosisMetadata(
                disease=meta.DiseaseMetadata(
                    disease_code=disease_code,
                    disease_description=DISEASE_DESCRIPTIONS[disease_code],
                    stage=enums.DiagnosisStage.ACUTE,
                ),
                severity=severity,
                diagnosis_method=random.choices(
                    [
                        enums.DiagnosisMethod.CLINICAL,
                        enums.DiagnosisMethod.SENSOR_BASED,
                        enums.DiagnosisMethod.LABORATORY,
                    ],
                    weights=[70, 20, 10],
                )[0],
                confirmation_status=enums.ConfirmationStatus.CONFIRMED,
                diagnostic_source=random.choices(
                    [
                        enums.DiagnosticSource.FARM_WORKER,
                        enums.DiagnosticSource.VETERINARIAN,
                        enums.DiagnosticSource.SENSOR,
                    ],
                    weights=[55, 30, 15],
                )[0],
            ).model_dump()
            events.append(
                self.create_event(
                    current_date, EventType.DIAGNOSIS, metadata=diagnosis_meta
                )
            )

            drug, route, milk_withdrawal = TREATMENTS[disease_code]
            treatment_meta = meta.TreatmentMetadata(
                disease_code=disease_code,
                drug_name=drug,
                dosage=round(random.uniform(5.0, 20.0), 1),
                dosage_unit="ml",
                route_of_administration=route,
                milk_withdrawal_days=milk_withdrawal,
                meat_withdrawal_days=milk_withdrawal + 7,
                response_status=random.choices(
                    [
                        enums.TreatmentResponseStatus.RECOVERED,
                        enums.TreatmentResponseStatus.IMPROVING,
                        enums.TreatmentResponseStatus.NO_CHANGE,
                    ],
                    weights=[75, 20, 5],
                )[0],
            ).model_dump()
            events.append(
                self.create_event(
                    current_date, EventType.TREATMENT, metadata=treatment_meta
                )
            )

        # 4. Reproduction Cycle
        if self.days_pregnant > 0:
            # Check for abortion (days 42 to 260)
            if (
                42 < self.days_pregnant < 260
                and random.random() < config.daily_abortion_prob
            ):
                self.days_pregnant = 0
                events.append(self.create_event(current_date, EventType.ABORTION))
            else:
                self.days_pregnant += 1

                if self.days_pregnant == (
                    config.gestation_days - config.days_to_dry_off
                ):
                    self.is_milking = False
                    events.append(self.create_event(current_date, EventType.DRY_OFF))

                elif self.days_pregnant >= config.gestation_days:
                    self.days_pregnant = 0
                    self.days_in_milk = 1
                    self.is_milking = True

                    calving_ease = random.choices(
                        [
                            meta.CalvingEaseType.EASY_UNASSISTED,
                            meta.CalvingEaseType.EASY_ASSISTED,
                            meta.CalvingEaseType.DIFFICULT_EXTRA_ASSISTANCE,
                            meta.CalvingEaseType.DIFFICULT_VETERINARY_CARE,
                            meta.CalvingEaseType.CAESAREAN_OR_SURGERY,
                        ],
                        weights=[70, 20, 7, 2, 1],
                    )[0]

                    calving_meta = meta.CalvingMetadata(
                        calving_ease_type=calving_ease,
                        parturition_birth_status_type=None,
                    ).model_dump()

                    events.append(
                        self.create_event(
                            current_date, EventType.CALVING, metadata=calving_meta
                        )
                    )

                    # 50% chance of a female calf entering the herd
                    if random.choice([True, False]):
                        new_calf = SimCow(age_days=0)
                        new_calves.append(new_calf)

                        birth_meta = meta.BirthMetadata(
                            calving_ease_type=calving_ease,  # Same as mother
                            parturition_birth_status_type=enums.ParturitionBirthStatusType.ALIVE,
                        ).model_dump()

                        events.append(
                            self.create_event(
                                current_date,
                                EventType.BIRTH,
                                new_calf.id,
                                metadata=birth_meta,
                            )
                        )
                        herd_entry_meta = meta.HerdEntryMetadata(
                            entry_type=enums.HerdEntryType.BORN_ON_FARM,
                            entry_date=current_date.date(),
                            age_at_entry=0,
                        ).model_dump()
                        events.append(
                            self.create_event(
                                current_date,
                                EventType.HERD_ENTRY,
                                new_calf.id,
                                metadata=herd_entry_meta,
                            )
                        )

        elif not self.is_dnb:
            is_eligible_heifer = (
                self.age_days >= config.heifer_breeding_age and self.days_in_milk == 0
            )
            is_eligible_cow = self.days_in_milk > config.voluntary_waiting_period

            if (
                is_eligible_heifer or is_eligible_cow
            ) and self.age_days % config.heat_cycle_days == 0:
                events.append(self.create_event(current_date, EventType.HEAT))
                breeding_meta = meta.BreedingMetadata(
                    bull_id=uuid.uuid4(),
                    bull_name=random.choice(
                        ["SuperSire", "Crimson", "Renegade", "Doc"]
                    ),
                    insemination_number=random.randint(1, 3),
                    breeding_type=enums.BreedingType.ARTIFICIAL_INSEMINATION,
                    gender_sorted=random.choices(
                        [
                            enums.GenderSorting.FEMALE_SORTED,
                            enums.GenderSorting.CONVENTIONAL,
                        ],
                        weights=[80, 20],
                    )[0],
                ).model_dump()
                events.append(
                    self.create_event(
                        current_date, EventType.BREEDING, metadata=breeding_meta
                    )
                )

                if random.random() < config.conception_rate:
                    self.days_pregnant = 1
                    check_date = current_date + timedelta(days=35)
                    events.append(
                        self.create_event(check_date, EventType.PREGNANCY_CHECK)
                    )

        # 5. High-Frequency Daily Events (Milking & Feeding)
        if self.is_milking:
            self.days_in_milk += 1

            milking_times = self._get_times(
                current_date, config.milking_times, config.milking_session_duration
            )

            # One MilkRecording per day summarising the whole day's yield,
            # alongside the per-session MilkMeterYields below.
            day_total = self.daily_yield(config)
            session_yields = _split_yield(day_total, len(milking_times))

            milk_recording_meta = meta.MilkRecordingMetadata(
                milking_yield=round(day_total, 2),
                fat_percentage=round(random.gauss(4.15, 0.45), 2),
                protein_percentage=round(random.gauss(3.45, 0.25), 2),
                lactose_percentage=round(random.gauss(4.60, 0.15), 2),
                scc=int(
                    random.lognormvariate(
                        13.8 if self.mastitis_recovery_left else 11.9, 0.6
                    )
                ),
            ).model_dump()
            events.append(
                self.create_event(
                    current_date, EventType.MILK_RECORDING, metadata=milk_recording_meta
                )
            )

            for session_num, start_time in enumerate(milking_times, start=1):
                duration_mins = random.randint(5, 12)
                yield_kg = round(session_yields[session_num - 1], 2)
                r_id = random.randint(1, 6)

                milk_meta = meta.MilkMeterYieldsMetadata(
                    milking_yield=yield_kg,
                    start_time=start_time,
                    end_time=start_time + timedelta(minutes=duration_mins),
                    robot_id=r_id,
                    robot_name=f"Astronaut {r_id}",
                    failure=random.random() < 0.01,
                    refusal=random.random() < 0.03,
                    milking_speed=round(yield_kg / duration_mins, 2),
                    body_weight=random.randint(550, 750),
                    milking_session=session_num,
                    milk_date=current_date.date(),
                ).model_dump()
                events.append(
                    self.create_event(
                        start_time, EventType.MILK_METER_YIELDS, metadata=milk_meta
                    )
                )

            # Primary feeds 30 mins after milking
            feed_base_hours = [h + 0.5 for h in config.milking_times]

            feed_times = self._get_times(
                current_date, feed_base_hours, config.feeding_duration
            )

            for session_num, start_time in enumerate(feed_times, start=1):
                duration_mins = random.randint(10, 30)
                prog_kg = round(random.uniform(1.5, 3.0), 2)

                feed_meta = meta.FeedIntakeMetadata(
                    product_id=101,
                    product_category="Concentrate",
                    feed_dry_matter_content_uni_id=1,
                    product_name="High Yield Pellets",
                    intake_programmed_kg=prog_kg,
                    intake_consumed_kg=round(prog_kg * random.uniform(0.8, 1.0), 2),
                    feed_intake_session=session_num,
                    start_time=start_time,
                    end_time=start_time + timedelta(minutes=duration_mins),
                ).model_dump()
                events.append(
                    self.create_event(
                        start_time, EventType.FEED_INTAKE, metadata=feed_meta
                    )
                )

        else:
            # Feed Intake for dry cows / youngstock (2-3x day)
            feed_base_hours = [h + 0.5 for h in config.milking_times]

            feed_times = self._get_times(
                current_date, feed_base_hours, config.feeding_duration
            )

            for session_num, start_time in enumerate(feed_times, start=1):
                duration_mins = random.randint(15, 40)
                prog_kg = round(random.uniform(2.0, 4.0), 2)

                feed_meta = meta.FeedIntakeMetadata(
                    product_id=202,
                    product_category="Dry Cow Mix",
                    feed_dry_matter_content_uni_id=1,
                    product_name="Maintenance Blend",
                    intake_programmed_kg=prog_kg,
                    intake_consumed_kg=round(prog_kg * random.uniform(0.9, 1.0), 2),
                    feed_intake_session=session_num,
                    start_time=start_time,
                    end_time=start_time + timedelta(minutes=duration_mins),
                ).model_dump()
                events.append(
                    self.create_event(
                        start_time, EventType.FEED_INTAKE, metadata=feed_meta
                    )
                )

        return events, new_calves


class Farm:
    def __init__(
        self, conf: SimConfig, db_path: Path | str = DB_PATH, overwrite: bool | None = None
    ):
        """`overwrite`: True to wipe an existing database, False to add to it, None to ask."""
        global FARM_NUMBERS
        FARM_NUMBERS = FarmNumbers()
        self.conf = conf
        self.herd_id = str(uuid.uuid4())
        self.source_id = random.randint(100_000, 999_999)
        self.country_code = "NL"
        self.cows = []
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_conn = sqlite3.connect(db_path)

        if overwrite is None:
            choice = input(
                f"Do you want to delete existing data in:\n- {db_path}\n\n"
                "Enter 'y' (yes) or 'n' (no) or 'c' (cancel): "
            )
        else:
            choice = "y" if overwrite else "n"
        self.sim_cancelled = False
        if "c" in choice:
            self.sim_cancelled = True
        elif "y" in choice:
            self.setup_db()

        if not self.sim_cancelled:
            self.initialize_herd()

    def setup_db(self):
        """(Re)create the tables from the bundled `schemas/sqlite.sql`."""
        cursor = self.db_conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS AnimalEvents")
        cursor.execute("DROP TABLE IF EXISTS Cows")
        cursor.execute("DROP TABLE IF EXISTS Herds")
        cursor.executescript(read_schema(SQLITE_SCHEMA))
        self.db_conn.commit()

    def write_herd(self):
        """Insert this farm's single Herds row.

        A farm database describes one herd, so this is one row. It is what
        `DairyData.load_herds()` reads, and what the SQLite -> Delta
        pipeline copies into the multi-farm `herds` table.
        """
        cursor = self.db_conn.cursor()
        cursor.execute(
            """
            INSERT INTO Herds (herd_id, source_id, country_code)
            VALUES (?, ?, ?)
            ON CONFLICT(herd_id) DO NOTHING
            """,
            (self.herd_id, self.source_id, self.country_code),
        )
        self.db_conn.commit()

    def write_cow(self, cow: "SimCow"):
        """Upsert a cow row. Called on entry to the sim and again on exit to set exit_date."""
        metadata = json.dumps(
            {
                "birth_date": cow.birth_date,
                "born_on_farm": cow.born_on_farm,
                "exit_date": cow.exit_date,
                "gender": cow.gender,
                "animal_farm_number": cow.animal_farm_number,
                "animal_ear_tag": cow.animal_ear_tag,
                "animal_legal_id": cow.animal_legal_id,
                "breed": cow.breed,
            }
        )
        cursor = self.db_conn.cursor()
        cursor.execute(
            """
            INSERT INTO Cows (animal_id, herd_id, sire_ear_tag, metadata)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(animal_id) DO UPDATE SET
                metadata = excluded.metadata
            """,
            (cow.id, cow.herd_id, None, metadata),
        )

    def _batch_write_cows(self, cows: list["SimCow"]):
        """Batch upsert of multiple cow rows — used on initialization and daily flush."""
        rows = [
            (
                cow.id,
                cow.herd_id,
                None,  # sire_ear_tag: the simulation has no sires
                json.dumps(
                    {
                        "birth_date": cow.birth_date,
                        "born_on_farm": cow.born_on_farm,
                        "exit_date": cow.exit_date,
                        "gender": cow.gender,
                        "animal_farm_number": cow.animal_farm_number,
                        "animal_ear_tag": cow.animal_ear_tag,
                        "animal_legal_id": cow.animal_legal_id,
                        "breed": cow.breed,
                    }
                ),
            )
            for cow in cows
        ]
        cursor = self.db_conn.cursor()
        cursor.executemany(
            """
            INSERT INTO Cows (animal_id, herd_id, sire_ear_tag, metadata)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(animal_id) DO UPDATE SET
                metadata = excluded.metadata
            """,
            rows,
        )
        self.db_conn.commit()

    def initialize_herd(self):
        self.write_herd()
        end_day = self.conf.sim_end_date or datetime.now(timezone.utc).date()
        start_day = end_day - timedelta(days=int(self.conf.sim_years * 365))
        for _ in range(self.conf.target_herd_size):
            age = random.randint(730, 2500)
            is_milking = random.choice([True, False])
            dim = random.randint(1, 305) if is_milking else 0
            dcc = random.randint(0, 200)
            cow = SimCow(
                age_days=age,
                herd_id=self.herd_id,
                is_milking=is_milking,
                days_in_milk=dim,
                days_pregnant=dcc,
                born_on_farm=False,  # pre-existing herd: origin unknown
                birth_date=(start_day - timedelta(days=age)).isoformat(),
            )
            self.cows.append(cow)
        self._batch_write_cows(self.cows)
        self.db_conn.commit()

    def write_events(self, events: list[Event]):
        # Some events are scheduled ahead (a pregnancy check weeks after breeding). The database
        # is history up to the end date, so nothing after it is written.
        end_day = self.conf.sim_end_date or datetime.now(timezone.utc).date()
        end = datetime(end_day.year, end_day.month, end_day.day, tzinfo=timezone.utc)
        events = [ev for ev in events if ev.datetime < end]
        if not events:
            return
        cursor = self.db_conn.cursor()
        formatted_events = [
            (
                str(ev.event_id),
                ev.datetime.isoformat(),
                ev.event_type,
                ev.animal_id_source,
                json.dumps(
                    ev.metadata,
                    default=lambda o: (
                        o.isoformat() if isinstance(o, datetime) else str(o)
                    ),
                ),
            )
            for ev in events
        ]
        cursor.executemany(
            "INSERT INTO AnimalEvents (event_id, datetime, event_type, animal_id, metadata) VALUES (?, ?, ?, ?, ?)",
            formatted_events,
        )

    def run_simulation(self):
        # Run backwards from the end date so the output is history rather
        # than a decade of the future: real farm data is historical, and
        # analyses filter on past years.
        end_day = self.conf.sim_end_date or datetime.now(timezone.utc).date()
        end_date = datetime(end_day.year, end_day.month, end_day.day, tzinfo=timezone.utc)
        current_date = end_date - timedelta(days=int(self.conf.sim_years * 365))
        date_i = 1

        print(f"Starting simulation from {current_date.date()} to {end_date.date()}...")

        while current_date < end_date:
            print(
                f"Day {date_i} / {int(self.conf.sim_years * 365)}", end="\r", flush=True
            )
            self.simulate_day(current_date)
            current_date += timedelta(days=1)
            date_i += 1

            if date_i % 30 == 0:
                self.db_conn.commit()

        self.db_conn.commit()

        cursor = self.db_conn.cursor()
        cursor.execute("SELECT count(*) FROM AnimalEvents")
        print(f"Simulation complete. Generated {cursor.fetchone()[0]:,} events.")

    def simulate_day(self, current_date: datetime):
        """Simulate one day of the farm and write its events (not committed)."""
        daily_events = []
        dirty_cows: list[SimCow] = []  # cows whose Cows row needs updating today

        # Process all active cows
        active_cows = [c for c in self.cows if c.in_herd]
        for cow in active_cows:
            c_events, new_calves = cow.process_day(self.conf, current_date)
            daily_events.extend(c_events)
            for calf in new_calves:
                calf.herd_id = self.herd_id
                calf.birth_date = current_date.date().isoformat()
                calf.born_on_farm = True
                dirty_cows.append(calf)
            self.cows.extend(new_calves)

            # Base culling logic
            if random.random() < self.conf.daily_base_cull_prob:
                cow.in_herd = False
                cow.exit_date = current_date.date().isoformat()
                dirty_cows.append(cow)
                daily_events.append(
                    cow.create_event(
                        current_date,
                        EventType.EXIT,
                        metadata=_exit_metadata(cow, "routine"),
                    )
                )

        # Herd Size Orchestration
        current_size = len([c for c in self.cows if c.in_herd])

        if current_size < int(
            self.conf.target_herd_size * (1 - self.conf.herd_variation_p)
        ):
            for _ in range(self.conf.target_herd_size - current_size):
                age = random.randint(730, 1000)
                new_cow = SimCow(
                    age_days=age,
                    herd_id=self.herd_id,
                    is_milking=True,
                    days_in_milk=10,
                    born_on_farm=False,
                    birth_date=(current_date.date() - timedelta(days=age)).isoformat(),
                )
                self.cows.append(new_cow)
                dirty_cows.append(new_cow)
                purchase_meta = meta.HerdEntryMetadata(
                    entry_type=meta.HerdEntryType.PURCHASED,
                    entry_date=current_date.date(),
                    age_at_entry=new_cow.age_days,
                    source_farm=random.choice(
                        ["Green Acres", "Valley Farms", "Sunny Ridge"]
                    ),
                    purchase_price=round(random.uniform(1500.0, 2500.0), 2),
                    purchase_currency="USD",
                ).model_dump()
                daily_events.append(
                    new_cow.create_event(
                        current_date, EventType.HERD_ENTRY, metadata=purchase_meta
                    )
                )

        elif current_size > int(
            self.conf.target_herd_size * (1 + self.conf.herd_variation_p)
        ):
            excess = current_size - self.conf.target_herd_size
            # Cull priority: DNB cows first, then oldest
            active_cows.sort(key=lambda x: (not x.is_dnb, x.age_days), reverse=True)
            for cow in active_cows[:excess]:
                cow.in_herd = False
                cow.exit_date = current_date.date().isoformat()
                dirty_cows.append(cow)
                daily_events.append(
                    cow.create_event(
                        current_date,
                        EventType.EXIT,
                        metadata=_exit_metadata(cow, "capacity"),
                    )
                )

        self.write_events(daily_events)
        if dirty_cows:
            self._batch_write_cows(dirty_cows)


if __name__ == "__main__":
    farm = Farm(SimConfig())
    if not farm.sim_cancelled:
        farm.run_simulation()
