
CREATE TABLE IF NOT EXISTS `observer_archive` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT 'key',
    `archive_type` smallint NOT NULL DEFAULT '0' COMMENT '详见gpt/review_reader/enums/ArchiveType',
    `archive_name` varchar(64) NOT NULL DEFAULT '' COMMENT 'symbol to specify',
    `record_count` int NOT NULL DEFAULT '0' COMMENT 'e.g. number of reviews',

    `origin_url` varchar(256) NOT NULL DEFAULT '' COMMENT 'original material url',
    `origin_info` json DEFAULT NULL COMMENT 'origin json detail',
    `process_info` json DEFAULT NULL COMMENT 'processed info detail',

    `deleted` tinyint(3) NOT NULL DEFAULT '0' COMMENT '是否被删除, 0-no, 1-yes',
    `deleted_at` timestamp NOT NULL DEFAULT '1970-01-01 08:00:01' COMMENT '删除时间',
    `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',

    PRIMARY KEY (`id`),
    UNIQUE KEY `uniq_one` (`archive_type`, `archive_name`, `record_count`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='评论分析项目的数据存档';

