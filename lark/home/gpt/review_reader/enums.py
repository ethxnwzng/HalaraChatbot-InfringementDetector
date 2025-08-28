from enum import Enum


class ArchiveType(Enum):
    UNKNOWN = 0
    MALL_REVIEWS = 1
    AD_REVIEWS = 2


class ExtractType(Enum):
    UNKNOWN = 0
    CONS = 1
    SCENARIO = 2
    PROS = 3
    COMMON = 4

    def name(self) -> str:
        if self == ExtractType.CONS:
            return 'cons'
        elif self == ExtractType.SCENARIO:
            return 'scenario'
        elif self == ExtractType.COMMON:
            return 'common'
        elif self == ExtractType.PROS:
            return 'pros'
        else:
            return 'unknown'

