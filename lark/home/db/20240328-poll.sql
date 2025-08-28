
CREATE TABLE IF NOT EXISTS `lark_poll` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT 'key',
    `poll_type` varchar(32) NOT NULL DEFAULT '' COMMENT 'symbol to specify',
    `lark_user` varchar(32) NOT NULL DEFAULT '' COMMENT 'lark user id',
    `repoll` tinyint(3) NOT NULL DEFAULT '0' COMMENT '是否可以重新poll, 0-no, 1-yes',

    `answer` json DEFAULT NULL COMMENT 'origin json detail',
    `result` json DEFAULT NULL COMMENT 'result json detail',

    `deleted` tinyint(3) NOT NULL DEFAULT '0' COMMENT '是否被删除, 0-no, 1-yes',
    `deleted_at` timestamp NOT NULL DEFAULT '1970-01-01 08:00:01' COMMENT '删除时间',
    `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',

    PRIMARY KEY (`id`),
    KEY `idx_poll_user` (`poll_type`, `lark_user`),
    KEY `idx_user` (`lark_user`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='问卷收集表';