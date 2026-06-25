import json
import random
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import farm_data_definitions.enums as enums
import farm_data_definitions.event_metadata as meta
from farm_data_definitions import Event, EventType
from pydantic import BaseModel

DB_PATH = Path.home() / "nsf-data/dairy_farm.db"


class SimConfig(BaseModel):
    target_herd_size: int = 100
    sim_years: float = 10
    gestation_days: int = 280
    days_to_dry_off: int = 60
    voluntary_waiting_period: int = 50
    heifer_breeding_age: int = 400
    heat_cycle_days: int = 21
    conception_rate: float = 0.38
    daily_disease_prob: float = 0.002
    daily_base_cull_prob: float = 0.0008
    daily_abortion_prob: float = 0.0001  # For pregnancies between 42-260 days
    weaning_age: int = 60
    genome_test_age: int = 7
    dnb_age_threshold: int = 2920  # ~8 years
    herd_variation_p: float = 0.05
    milking_times: list[int] = [5, 13, 21]
    milking_session_duration: float = 1.5  # Hours to milk all cows
    feeding_duration: float = 0.5  # Time to provide feed to all cows


class SimCow:
    def __init__(
        self,
        age_days: int,
        is_milking: bool = False,
        days_in_milk: int = 0,
        days_pregnant: int = 0,
    ):
        self.id = str(uuid.uuid4())[:8]
        self.age_days = age_days
        self.is_milking = is_milking
        self.days_in_milk = days_in_milk
        self.days_pregnant = days_pregnant
        self.in_herd = True
        self.is_dnb = age_days >= SimConfig().dnb_age_threshold

    def create_event(
        self,
        dts: datetime,
        event_type: EventType,
        animal_id: str = "",
        metadata: dict = {},
    ) -> Event:
        event_id = uuid.uuid4()
        return Event(
            event_id=event_id,
            event_type=event_type,
            animal_id_source=animal_id or self.id,
            datetime=dts,
            metadata=metadata,
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
                self.create_event(current_date, EventType.GENOME_TEST, metadata=genome_meta)
            )
        elif self.age_days == config.weaning_age:
            events.append(self.create_event(current_date, EventType.WEANING))

        if not self.is_dnb and self.age_days >= config.dnb_age_threshold:
            self.is_dnb = True
            events.append(self.create_event(current_date, EventType.DNB_DECISION))

        # 2. Monthly Evaluations
        if self.age_days > 365 and self.age_days % 30 == 0:
            lameness_meta = meta.LamenessScoreMetadata(
                lameness_score=random.choices([0, 1, 2, 3, 4, 5], weights=[70, 15, 8, 4, 2, 1])[0],
                affected_leg=None,
                observation_context=None,
            ).model_dump()
            events.append(
                self.create_event(current_date, EventType.LAMENESS_SCORE, metadata=lameness_meta)
            )

        # 3. Probabilistic Health Events
        if random.random() < config.daily_disease_prob:
            events.append(self.create_event(current_date, EventType.DIAGNOSIS))
            events.append(self.create_event(current_date, EventType.TREATMENT))

        # 4. Reproduction Cycle
        if self.days_pregnant > 0:
            # Check for abortion (days 42 to 260)
            if 42 < self.days_pregnant < 260 and random.random() < config.daily_abortion_prob:
                self.days_pregnant = 0
                events.append(self.create_event(current_date, EventType.ABORTION))
            else:
                self.days_pregnant += 1

                if self.days_pregnant == (config.gestation_days - config.days_to_dry_off):
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
                        self.create_event(current_date, EventType.CALVING, metadata=calving_meta)
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
                    bull_name=random.choice(["SuperSire", "Crimson", "Renegade", "Doc"]),
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
                    self.create_event(current_date, EventType.BREEDING, metadata=breeding_meta)
                )

                if random.random() < config.conception_rate:
                    self.days_pregnant = 1
                    check_date = current_date + timedelta(days=35)
                    events.append(self.create_event(check_date, EventType.PREGNANCY_CHECK))

        # 5. High-Frequency Daily Events (Milking & Feeding)
        if self.is_milking:
            self.days_in_milk += 1

            milking_times = self._get_times(
                current_date, config.milking_times, config.milking_session_duration
            )

            for session_num, start_time in enumerate(milking_times, start=1):
                duration_mins = random.randint(5, 12)
                yield_kg = round(random.uniform(8.0, 18.0), 2)
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
                ).model_dump()
                events.append(
                    self.create_event(start_time, EventType.MILK_METER_YIELDS, metadata=milk_meta)
                )

            # Primary feeds 30 mins after milking
            feed_base_hours = [h + 0.5 for h in config.milking_times]

            feed_times = self._get_times(current_date, feed_base_hours, config.feeding_duration)

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
                    self.create_event(start_time, EventType.FEED_INTAKE, metadata=feed_meta)
                )

        else:
            # Feed Intake for dry cows / youngstock (2-3x day)
            feed_base_hours = [h + 0.5 for h in config.milking_times]

            feed_times = self._get_times(current_date, feed_base_hours, config.feeding_duration)

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
                    self.create_event(start_time, EventType.FEED_INTAKE, metadata=feed_meta)
                )

        return events, new_calves


class Farm:
    def __init__(self, conf: SimConfig, db_path: Path | str = DB_PATH):
        self.conf = conf
        self.cows = []
        self.db_conn = sqlite3.connect(db_path)
        self.setup_db()
        self.initialize_herd()

    def setup_db(self):
        cursor = self.db_conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS Events")
        cursor.executescript(
            """CREATE TABLE Events (
                event_id TEXT PRIMARY KEY,
                datetime TEXT NOT NULL,
                event_type TEXT NOT NULL,
                animal_id TEXT NOT NULL,
                metadata TEXT NOT NULL
            );
            """
        )
        self.db_conn.commit()

    def initialize_herd(self):
        for _ in range(self.conf.target_herd_size):
            age = random.randint(730, 2500)
            is_milking = random.choice([True, False])
            dim = random.randint(1, 305) if is_milking else 0
            dcc = random.randint(0, 200)
            self.cows.append(
                SimCow(
                    age_days=age,
                    is_milking=is_milking,
                    days_in_milk=dim,
                    days_pregnant=dcc,
                )
            )

    def write_events(self, events: list[Event]):
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
                    default=lambda o: o.isoformat() if isinstance(o, datetime) else str(o),
                ),
            )
            for ev in events
        ]
        cursor.executemany(
            "INSERT INTO Events (event_id, datetime, event_type, animal_id, metadata) VALUES (?, ?, ?, ?, ?)",
            formatted_events,
        )
        self.db_conn.commit()

    def run_simulation(self):
        current_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = current_date + timedelta(days=int(self.conf.sim_years * 365))
        date_i = 1

        print(f"Starting simulation from {current_date.date()} to {end_date.date()}...")

        while current_date < end_date:
            print(f"Day {date_i} / {int(self.conf.sim_years * 365)}", end="\r")
            daily_events = []

            # Process all active cows
            active_cows = [c for c in self.cows if c.in_herd]
            for cow in active_cows:
                c_events, new_calves = cow.process_day(self.conf, current_date)
                daily_events.extend(c_events)
                self.cows.extend(new_calves)

                # Base culling logic
                if random.random() < self.conf.daily_base_cull_prob:
                    cow.in_herd = False
                    daily_events.append(cow.create_event(current_date, EventType.EXIT))

            # Herd Size Orchestration
            current_size = len([c for c in self.cows if c.in_herd])

            if current_size < int(self.conf.target_herd_size * (1 - self.conf.herd_variation_p)):
                for _ in range(self.conf.target_herd_size - current_size):
                    new_cow = SimCow(
                        age_days=random.randint(730, 1000),
                        is_milking=True,
                        days_in_milk=10,
                    )
                    self.cows.append(new_cow)
                    purchase_meta = meta.HerdEntryMetadata(
                        entry_type=meta.HerdEntryType.PURCHASED,
                        entry_date=current_date.date(),
                        age_at_entry=new_cow.age_days,
                        source_farm=random.choice(["Green Acres", "Valley Farms", "Sunny Ridge"]),
                        purchase_price=round(random.uniform(1500.0, 2500.0), 2),
                        purchase_currency="USD",
                    ).model_dump()
                    daily_events.append(
                        new_cow.create_event(
                            current_date, EventType.HERD_ENTRY, metadata=purchase_meta
                        )
                    )

            elif current_size > int(self.conf.target_herd_size * (1 + self.conf.herd_variation_p)):
                excess = current_size - self.conf.target_herd_size
                # Cull priority: DNB cows first, then oldest
                active_cows.sort(key=lambda x: (not x.is_dnb, x.age_days), reverse=True)
                for cow in active_cows[:excess]:
                    cow.in_herd = False
                    daily_events.append(cow.create_event(current_date, EventType.EXIT))

            self.write_events(daily_events)
            current_date += timedelta(days=1)
            date_i += 1

        self.db_conn.commit()

        cursor = self.db_conn.cursor()
        cursor.execute("SELECT count(*) FROM Events")
        print(f"Simulation complete. Generated {cursor.fetchone()[0]:,} events.")


if __name__ == "__main__":
    Farm(SimConfig()).run_simulation()
