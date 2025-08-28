from enum import Enum


class ApprovalStatus(Enum):
    UNKNOWN = 0
    # 新创建
    PENDING = 1
    # 已通过
    APPROVED = 2
    # 已拒绝
    REJECTED = 3
    # 已撤销
    CANCELED = 4
    # 已删除
    DELETED = 5


class MaterialType(Enum):
    UNKNOWN = 0
    PICTURE = 1
    VIDEO = 2
    EXCEL = 3
    GIF = 4

