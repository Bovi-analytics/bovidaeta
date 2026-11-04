"""
Enumerations used in the farm domain model.

This module describes parameters that need extra definition, including sex of
animal, breeding type, gender sorting, calving ease, birth status, departure
type/reason, breed codes, event types, genomic sample source, and lameness
assessment facets.
"""

from enum import Enum


class EventType(str, Enum):
    """
    Predefined and immutable timeline event types.

    - Birth: Cow was born.
    - Breeding: Animal shows heat and is inseminated.
    - BodyWeightKg: Body weight of the animal is measured (in kg).
    - Calving: Cow gives birth to a calf.
    - Exit: Cow was sold to another farm, died, or was culled.
    - DryOff: Animal is no longer milked until she calves.
    - Abortion: Cow loses pregnancy after placentation (>42 days) and before independent viability (260 days).
    - Heat: Animal shows signs of heat.
    - DNBdecision: Decision is made to not breed the animal.
    - MilkRecording: Milk yield as recorded by a milk recording organization.
    - MilkMeterYields: Milk production of a single milking measured by milk meter on milk robot or in a milk parlour.
    - AggregatedMilkMeterYields: Milk meter yields summed over a period (e.g. a day or a week), for sources that only report totals.
    - FeedIntake: Feed intake of concentrates per eating session.
    - Diagnosis: Animal is sick or diagnosed with an ailment.
    - Treatment: Cow is treated.
    - PregnancyCheck: Pregnancy check is performed, e.g., by ultrasound or blood test.
    - SensorMeasurement: Measurement of a trait by a sensor, e.g., rumination time or activity level.
    - BodyConditionScore: Body condition score of the animal measured.
    - LamenessScore: Locomotion or lameness score of the animal recorded.
    - GenomeTest: Genomic testing event for the animal.
    - HerdEntry: Animal enters the herd (born on farm or purchased from an external source).
    - HerdMove: Animal is moved from one location to another within the operation.
    - Weaning: The diet of the calf will no longer contain milk.
    """

    BIRTH = "Birth"
    BREEDING = "Breeding"
    BODY_WEIGHT_KG = "BodyWeightKg"
    CALVING = "Calving"
    EXIT = "Exit"
    DRY_OFF = "DryOff"
    ABORTION = "Abortion"
    HEAT = "Heat"
    DNB_DECISION = "DNBdecision"
    MILK_RECORDING = "MilkRecording"
    MILK_METER_YIELDS = "MilkMeterYields"
    AGGREGATED_MILK_METER_YIELDS = "AggregatedMilkMeterYields"
    FEED_INTAKE = "FeedIntake"
    DIAGNOSIS = "Diagnosis"
    TREATMENT = "Treatment"
    PREGNANCY_CHECK = "PregnancyCheck"
    SENSOR_MEASUREMENT = "SensorMeasurement"
    BODY_CONDITION_SCORE = "BodyConditionScore"
    LAMENESS_SCORE = "LamenessScore"
    GENOME_TEST = "GenomeTest"
    HERD_ENTRY = "HerdEntry"
    HERD_MOVE = "HerdMove"
    WEANING = "Weaning"


class AggregationPeriod(str, Enum):
    """
    Calendar unit an aggregated measurement covers. Combined with a length,
    e.g. 2 x day for every other day; a month is a calendar month.
    """

    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class SensorMeasurementType(str, Enum):
    """
    Type of sensor measurements.
    """

    EATING_TIME = "eating_time"
    RUMINATION_TIME = "rumination_time"
    LYING_TIME = "lying_time"
    STANDING_TIME = "standing_time"
    WALKING_TIME = "walking_time"
    LEG_ACTIVITY = "leg_activity"
    METHANE_OUTPUT = "methane_output"


class LamenessAffectedLeg(str, Enum):
    """
    Limb or side primarily affected, when a lameness score is leg-specific.

    Use `not_recorded` when the source gives a global locomotion score only,
    or when the affected limb was not identified.
    """

    LEFT_FORE = "left_fore"
    RIGHT_FORE = "right_fore"
    LEFT_HIND = "left_hind"
    RIGHT_HIND = "right_hind"
    BILATERAL = "bilateral"
    NOT_RECORDED = "not_recorded"


class LamenessObservationContext(str, Enum):
    """
    Where or how the locomotion assessment was performed.

    Fixed values keep analytics comparable across farms; use `unknown` when
    the source system does not specify.
    """

    PARLOR_EXIT = "parlor_exit"
    MILKING_ROBOT = "milking_robot"
    MILKING_PARLOUR = "milking_parlour"
    FEED_ALLEY = "feed_alley"
    WALKWAY = "walkway"
    FORCED_LOCOMOTION = "forced_locomotion"
    FREE_LOCOMOTION = "free_locomotion"
    HOLDING_PEN = "holding_pen"
    UNKNOWN = "unknown"


class GenomicSampleSource(str, Enum):
    """
    Tissue or DNA source used for genomic testing.

    Values follow CDCB accepted genotype SampleSheet `Sample_Source` values.
    """

    HAIR = "hair"
    BLOOD = "blood"
    SEMEN = "semen"
    TISSUE = "tissue"
    NASAL = "nasal"


class AnimalGender(str, Enum):
    """
    Sex of animal using species-independent English names.

    Includes neuter/cryptorchid variations as defined by ICAR:
    https://github.com/adewg/ICAR/blob/ADE-1/enums/icarAnimalGenderType.json
    """

    FEMALE = "female"
    FEMALE_NEUTER = "female_neuter"
    MALE = "male"
    MALE_CRYPTORCHID = "male_cryptorchid"
    UNKNOWN = "unknown"


class BreedingType(str, Enum):
    """Breeding type."""

    ARTIFICIAL_INSEMINATION = "artificial_insemination"
    DO_IT_YOURSELF = "do_it_yourself"
    NATURAL_SERVICE = "natural_service"
    WITH_BULL = "with_bull"
    EMBRYO_TRANSFER = "embryo_transfer"


class DiagnosisSampleType(str, Enum):
    """
    Type of samples that collected for diagnosis purpose.
    """

    MILK_INDIVIDUAL = "milk_individual"
    MILK_BULK_TANK = "milk_bulk_tank"
    BLOOD_SERUM = "blood_serum"
    BLOOD_WHOLE = "blood_whole"
    FECAL = "fecal"
    URINE = "urine"
    EAR_NOTCH = "ear_notch"
    HAIR = "hair"
    SWAB_NASAL = "swab_nasal"
    SWAB_VAGINAL = "swab_vaginal"
    TISSUE_NECROPSY = "tissue_necropsy"


class GenderSorting(str, Enum):
    """
    Type of sexing technology of the semen.

    Reference: https://www.sciencedirect.com/science/article/pii/S0093691X07001331
    """

    CONVENTIONAL = "conventional"
    FEMALE_SORTED = "female_sorted"
    MALE_SORTED = "male_sorted"
    UNKNOWN = "unknown"


class CalvingEaseType(str, Enum):
    """
    Calving ease.

    In the listed order, these correspond to INTERBEEF codes 1 to 5.
    Reference: https://github.com/adewg/ICAR/blob/ADE-1/enums/icarReproCalvingEaseType.json
    """

    EASY_UNASSISTED = "easy_unassisted"
    EASY_ASSISTED = "easy_assisted"
    DIFFICULT_EXTRA_ASSISTANCE = "difficult_extra_assistance"
    DIFFICULT_VETERINARY_CARE = "difficult_veterinary_care"
    CAESAREAN_OR_SURGERY = "caesarean_or_surgery"


class ParturitionBirthStatusType(str, Enum):
    """
    Widely used progeny birth statuses.

    Reference: https://github.com/adewg/ICAR/blob/ADE-1/enums/icarParturitionBirthStatusType.json
    """

    ALIVE = "alive"
    STILLBORN = "stillborn"
    ABORTED = "aborted"
    DIED_BEFORE_TAGGING_DATE = "died_before_tagging_date"
    DIED_AFTER_TAGGING_DATE = "died_after_tagging_date"
    SLAUGHTERED_AT_BIRTH = "slaughtered_at_birth"
    EUTHANISED_AT_BIRTH = "euthanised_at_birth"


class DepartureType(str, Enum):
    """
    Departure reasons based on Fetrow et al., 2006.

    Reference: http://dx.doi.org/10.3168/jds.S0022-0302(06)72257-3
    """

    DAIRY_SALE = "dairy_sale"
    SLAUGHTER = "slaughter"
    DEATH = "death"


class DepartureReason(str, Enum):
    """
    Departure cause.

    This was not specified in the previous ADE data dictionary.
    Reference: https://github.com/adewg/ICAR/blob/ADE-1/enums/icarDepartureReasonType.json
    """

    AGE = "age"
    SUPERFLUOUS = "superfluous"
    SLAUGHTER = "slaughter"
    SALE = "sale"
    NEWBORN = "newborn"
    LEG_OR_CLAW = "leg_or_claw"
    NUTRITION = "nutrition"
    PARTURITION = "parturition"
    MASTITIS = "mastitis"
    FERTILITY = "fertility"
    HEALTH = "health"
    PRODUCTION = "production"
    MILKING_ABILITY = "milking_ability"
    BAD_TYPE = "bad_type"
    BEHAVIOUR = "behaviour"
    OTHER = "other"
    UNKNOWN = "unknown"


class HerdEntryType(str, Enum):
    """
    Reason or mechanism by which an animal entered the herd.

    - born_on_farm: Animal was born on this farm. Complement to `Cow.born_on_farm`.
    - purchased: Animal was bought from an external source.
    - unknown: Entry reason is not recorded or not known.

    Note: intra-operation moves between herds or pens are represented as
    HerdMove events, not HerdEntry events.
    """

    BORN_ON_FARM = "born_on_farm"
    PURCHASED = "purchased"
    UNKNOWN = "unknown"


class Breed(str, Enum):
    """
    Breed codes used in cow breed composition, expressed as percentages.

    A cow can be, for example, 100% HOL (8/8), 50% HOL and 50% JER (4/8 + 4/8),
    or 50% HOL and 25% JER and 25% AAN.

    | Breed                      | BreedCode3 |
    | -------------------------- | ---------- |
    | Abondance                  | ABO        |
    | Angus                      | AAN        |
    | Aubrac                     | AUB        |
    | Ayrshire                   | RDC        |
    | Bazadais                   | BZD        |
    | Belgian Blue               | BBL        |
    | Blonde d'Aquitaine         | BAQ        |
    | Beef Shorthorn             | BSH        |
    | Beefmaster                 | BMA        |
    | Belgium Red & White        | BER        |
    | Braford                    | BFD        |
    | Brahman                    | BRM        |
    | Brangus                    | BRG        |
    | Brand Rood                 | BRR        |
    | British Frisian            | BRF        |
    | Brown Swiss                | BSW        |
    | Chianina                   | CIA        |
    | Charolais                  | CHA        |
    | Dairy Shorthorn            | MSH        |
    | Dutch Frisian              | DFR        |
    | Eringer                    | ERI        |
    | Meuse Rhine Yssel          | MRY        |
    | Dexter                     | DXT        |
    | Devon                      | DEV        |
    | Dikbil                     | DIK        |
    | Eastern Flanders White Red | BWR        |
    | European Red Dairy Breed   | RDC        |
    | Gascon                     | GAS        |
    | Glan Donnersberg           | GDB        |
    | Galloway                   | GLW        |
    | Guernsey                   | GUE        |
    | Gelbvieh                   | GVH        |
    | Groninger                  | GRO        |
    | Hereford                   | HER        |
    | Highland Cattle            | HLA        |
    | Hinterwalder               | HWD        |
    | Holstein                   | HOL        |
    | Holstein, Red and White    | RED        |
    | Jersey                     | JER        |
    | Kerry                      | KER        |
    | Dutch Belted-Lakenvelder   | DBE        |
    | Limousin                   | LIM        |
    | Lincoln Reds               | LIR        |
    | Longhorn                   | LON        |
    | Luing                      | LUI        |
    | Rouge des Pres             | RDP        |
    | Murray-Grey                | MGR        |
    | Montbeliard                | MON        |
    | Marchigiana                | MAR        |
    | Maremmana                  | MAE        |
    | Nellore                    | NEL        |
    | Normandy                   | NMD        |
    | Norwegian Red              | RDC        |
    | Parthenaise                | PAR        |
    | Polish White Backed        | PBG        |
    | Piedmont                   | PIE        |
    | Pinzgau                    | PIN        |
    | Polish Black and White     | PZB        |
    | Polish Red and White       | PZR        |
    | Red Angus                  | RAN        |
    | Romagnola                  | ROM        |
    | Salers                     | SAL        |
    | Santa Gertrudis            | SGE        |
    | South Devon                | SDE        |
    | Sussex                     | SUS        |
    | Simmental/Fleckvieh        | SIM        |
    | Speckle Park               | SPK        |
    | Stabiliser                 | STA        |
    | Swedish Red                | RDC        |
    | Sahiwal                    | SAH        |
    | Tarentaise                 | TAR        |
    | Tux                        | TUX        |
    | Tyrol Grey                 | TGR        |
    | Verbeter Roodbont          | VRB        |
    | Wagyu                      | WAG        |
    | Belgium Blue Mixte         | WBM        |
    | Welsh Black                | WBL        |
    | Western Flanders Meat      | BRV        |
    | West-Vlaams Rood           | BRD        |
    | Witrik                     | WRI        |

    Reference: https://interbull.org/ib/icarbreedcodes
    """

    AAN = "AAN"
    ABO = "ABO"
    AUB = "AUB"
    BAQ = "BAQ"
    BBL = "BBL"
    BER = "BER"
    BFD = "BFD"
    BMA = "BMA"
    BRD = "BRD"
    BRF = "BRF"
    BRG = "BRG"
    BRM = "BRM"
    BRR = "BRR"
    BRV = "BRV"
    BSH = "BSH"
    BSW = "BSW"
    BWR = "BWR"
    BZD = "BZD"
    CHA = "CHA"
    CIA = "CIA"
    DBE = "DBE"
    DEV = "DEV"
    DFR = "DFR"
    DIK = "DIK"
    DXT = "DXT"
    ERI = "ERI"
    GAS = "GAS"
    GDB = "GDB"
    GLW = "GLW"
    GRO = "GRO"
    GUE = "GUE"
    GVH = "GVH"
    HER = "HER"
    HLA = "HLA"
    HOL = "HOL"
    HWD = "HWD"
    JER = "JER"
    KER = "KER"
    LIM = "LIM"
    LIR = "LIR"
    LON = "LON"
    LUI = "LUI"
    MAE = "MAE"
    MAR = "MAR"
    MGR = "MGR"
    MON = "MON"
    MRY = "MRY"
    MSH = "MSH"
    NEL = "NEL"
    NMD = "NMD"
    PAR = "PAR"
    PBG = "PBG"
    PIE = "PIE"
    PIN = "PIN"
    PZB = "PZB"
    PZR = "PZR"
    RAN = "RAN"
    RDC = "RDC"
    RDP = "RDP"
    RED = "RED"
    ROM = "ROM"
    SAH = "SAH"
    SAL = "SAL"
    SDE = "SDE"
    SGE = "SGE"
    SIM = "SIM"
    SPK = "SPK"
    STA = "STA"
    SUS = "SUS"
    TAR = "TAR"
    TGR = "TGR"
    TUX = "TUX"
    VRB = "VRB"
    WAG = "WAG"
    WBL = "WBL"
    WBM = "WBM"
    WRI = "WRI"


class DiagnosisSeverity(str, Enum):
    """
    Clinical severity of a disease diagnosis.

    Reference: https://github.com/adewg/ICAR/blob/ADE-1/enums/icarDiagnosisSeverityType.json
    """

    LIGHT = "Light"
    MODERATE = "Moderate"
    SEVERE = "Severe"


class DiagnosisStage(str, Enum):
    """
    Stage of disease progression at time of diagnosis.

    Reference: https://github.com/adewg/ICAR/blob/ADE-1/enums/icarDiagnosisStageType.json
    """

    EARLY = "Early"
    ACUTE = "Acute"
    SUB_ACUTE = "SubAcute"
    CHRONIC = "Chronic"
    ACUTE_ON_CHRONIC = "AcuteOnChronic"
    END_STAGE = "EndStage"
    OTHER = "Other"


class DiseaseCode(str, Enum):
    """
    Common cattle disease codes used in diagnosis events.

    Covers the ~25 most clinically relevant conditions in dairy and beef herds.
    Less frequent or unclassified conditions should use OTH with a free-text
    description in DiseaseMetadata.disease_description.

    | Disease                               | Code |
    | ------------------------------------- | ---- |
    | Mastitis                              | MAS  |
    | Ketosis / Acetonaemia                 | KET  |
    | Milk Fever / Hypocalcaemia            | MFV  |
    | Left Displaced Abomasum               | LDA  |
    | Right Displaced Abomasum              | RDA  |
    | Retained Placenta                     | RTP  |
    | Metritis                              | MET  |
    | Endometritis                          | END  |
    | Ovarian Cyst                          | OVC  |
    | Digital Dermatitis                    | DDM  |
    | Foot Rot / Interdigital Phlegmon      | FTR  |
    | Sole Ulcer                            | SUL  |
    | White Line Disease                    | WLD  |
    | Bovine Respiratory Disease            | BRD  |
    | Bovine Viral Diarrhoea                | BVD  |
    | Infectious Bovine Rhinotracheitis     | IBR  |
    | Grass Tetany / Hypomagnesaemia        | MGT  |
    | Bloat                                 | BLT  |
    | Ruminal Acidosis                      | RAC  |
    | Traumatic Reticuloperitonitis         | TRP  |
    | Diarrhoea / Enteritis                 | DIA  |
    | Uterine Prolapse                      | UTP  |
    | Johne's Disease / Paratuberculosis    | JOH  |
    | Leptospirosis                         | LEP  |
    | Ringworm                              | RWM  |
    | Infectious Bovine Keratoconjunctivitis| IBK  |
    | Other                                 | OTH  |
    """

    MAS = "MAS"
    KET = "KET"
    MFV = "MFV"
    LDA = "LDA"
    RDA = "RDA"
    RTP = "RTP"
    MET = "MET"
    END = "END"
    OVC = "OVC"
    DDM = "DDM"
    FTR = "FTR"
    SUL = "SUL"
    WLD = "WLD"
    BRD = "BRD"
    BVD = "BVD"
    IBR = "IBR"
    MGT = "MGT"
    BLT = "BLT"
    RAC = "RAC"
    TRP = "TRP"
    DIA = "DIA"
    UTP = "UTP"
    JOH = "JOH"
    LEP = "LEP"
    RWM = "RWM"
    IBK = "IBK"
    OTH = "OTH"


class DiagnosisMethod(str, Enum):
    """Method used to identify a disease."""

    CLINICAL = "clinical"
    LABORATORY = "laboratory"
    SENSOR_BASED = "sensor_based"
    POST_MORTEM = "post_mortem"
    OTHER = "other"


class ConfirmationStatus(str, Enum):
    """Whether the diagnosis is still a suspicion or has been confirmed."""

    SUSPECTED = "suspected"
    CONFIRMED = "confirmed"


class DiagnosticSource(str, Enum):
    """Who or what made the diagnosis."""

    VETERINARIAN = "veterinarian"
    FARM_WORKER = "farm_worker"
    SENSOR = "sensor"
    LABORATORY = "laboratory"
    OTHER = "other"


class RouteOfAdministration(str, Enum):
    """
    Route by which a drug or treatment is administered.
    """

    INTRAMAMMARY = "intramammary"
    INTRAVENOUS = "intravenous"
    INTRAMUSCULAR = "intramuscular"
    SUBCUTANEOUS = "subcutaneous"
    ORAL = "oral"
    INTRAUTERINE = "intrauterine"
    TOPICAL = "topical"
    OTHER = "other"


class TreatmentResponseStatus(str, Enum):
    """Observed animal response at end of or after a treatment course."""

    IMPROVING = "improving"
    NO_CHANGE = "no_change"
    WORSENED = "worsened"
    RECOVERED = "recovered"
    DIED = "died"
