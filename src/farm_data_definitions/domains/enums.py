"""
Enumerations used in the farm domain model.

This module describes parameters that need extra definition, including sex of
animal, breeding type, gender sorting, calving ease, birth status, departure
type/reason, breed codes, and event types.
"""

from enum import Enum

class EventType(str, Enum):
    """
    Predefined and immutable timeline event types.

    - Birth: Cow was born.
    - Breeding: Animal shows heat and is inseminated.
    - Calving: Cow gives birth to a calf.
    - Exit: Cow was sold to another farm, died, or was culled.
    - DryOff: Animal is no longer milked until she calves.
    - Abortion: Cow loses pregnancy after placentation (>42 days) and before
      independent viability (260 days).
    - Heat: Animal shows signs of heat.
    - DNBdecision: Decision is made to not breed the animal.
    - MilkRecording: Milk yield as recorded by a milk recording organization.
    - MilkMeterYields: Milk production of a single milking measured by milk
      meter on milk robot or in a milk parlour.
    - FeedIntake: Feed intake of concentrates per eating session.
    - Diagnosis: Animal is sick or diagnosed with an ailment.
    - Treatment: Cow is treated.
    - Weaning: the diet of the calf will no longer contain milk
    """

    BIRTH = "Birth"
    BREEDING = "Breeding"
    CALVING = "Calving"
    EXIT = "Exit"
    DRY_OFF = "DryOff"
    ABORTION = "Abortion"
    HEAT = "Heat"
    DNB_DECISION = "DNBdecision"
    MILK_RECORDING = "MilkRecording"
    MILK_METER_YIELDS = "MilkMeterYields"
    FEED_INTAKE = "FeedIntake"
    DIAGNOSIS = "Diagnosis"
    TREATMENT = "Treatment"
    WEANING = "Weaning"

class WeightObservationMethodType(str, Enum):
    """
    Method by which the weight is observed.

    Includes loadcell (loadbars), girth (tape), assessed (visually),
    walk-over weighing, prediction, imaging (camera/IR),
    front end weight correlated to whole body, group average.

    Based on ICAR enum:
    https://github.com/adewg/ICAR/blob/ADE-1/enums/icarWeightMethodType.json
    """

    LOAD_CELL = "load_cell"
    GIRTH = "girth"
    ASSESSED = "assessed"
    WALK_OVER = "walk_over"
    PREDICTED = "predicted"
    IMAGED = "imaged"
    FRONT_END_CORRELATED = "front_end_correlated"
    GROUP_AVERAGE = "group_average"

class WeaningMethod(str, Enum):
    """
    The protocol that was used to wean the calf. 
    Abrupt = going from the highest milk consumption straight to zero kg milk per day
    Gradual = step down approach where the milk consumption is reduced over a couple of days
    Fenceline = only relevant for cow/calf management systems;
        the calf is seperated by a barrier from it's mom but there is still contact possible.
    """

    ABRUPT = 'abrupt'
    GRADUAL = 'gradual'
    FENCELINE = 'fence_line'
    

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


