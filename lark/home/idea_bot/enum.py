from enum import Enum


class VideoSource(Enum):
    UNKNOWN = 0
    DOUYIN = 1
    XIAOHONGSHU = 2
    TIKTOK = 3
    JVLING = 4
    TAOBAO = 5
    FACBOOK = 6

    def name(self):
        if self == VideoSource.UNKNOWN:
            return '未知'
        elif self == VideoSource.DOUYIN:
            return '抖音'
        elif self == VideoSource.XIAOHONGSHU:
            return '小红书'
        elif self == VideoSource.TIKTOK:
            return 'Tiktok'
        elif self == VideoSource.JVLING:
            return '巨量'
        elif self == VideoSource.TAOBAO:
            return '淘宝'
        elif self == VideoSource.FACBOOK:
            return '脸书'

    def db_name(self):
        if self == VideoSource.UNKNOWN:
            return ''
        elif self == VideoSource.DOUYIN:
            return 'douyin'
        elif self == VideoSource.XIAOHONGSHU:
            return 'xiaohongshu'
        elif self == VideoSource.TIKTOK:
            return 'tiktok'
        elif self == VideoSource.JVLING:
            return 'jvliang'
        elif self == VideoSource.TAOBAO:
            return 'taobao'
        elif self == VideoSource.FACBOOK:
            return 'facebook'


class FileType(Enum):
    UNKNOWN = 0
    EXCEL = 1
    CSV = 2
    PDF = 3
    IMAGE = 4
    VIDEO = 5
    
    @classmethod
    def from_extension(cls, filename: str) -> 'FileType':
        """Get FileType from file extension"""
        if not filename:
            return cls.UNKNOWN
            
        ext = filename.lower().split('.')[-1]
        if ext in ['xlsx', 'xls']:
            return cls.EXCEL
        elif ext == 'csv':
            return cls.CSV
        elif ext == 'pdf':
            return cls.PDF
        elif ext in ['jpg', 'jpeg', 'png', 'gif']:
            return cls.IMAGE
        elif ext in ['mp4', 'mov', 'avi']:
            return cls.VIDEO
        return cls.UNKNOWN