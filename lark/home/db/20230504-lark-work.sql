
CREATE TABLE IF NOT EXISTS `lark_user_workbench` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT 'key',
    `lark_user_id` varchar(64) NOT NULL DEFAULT '' COMMENT 'lark user',
    `work_symbol` varchar(32) NOT NULL DEFAULT '' COMMENT 'work symbol to specify',
    `detail` json DEFAULT NULL COMMENT 'workbench detail',

    `deleted` tinyint(3) NOT NULL DEFAULT '0' COMMENT '是否被删除, 0-no, 1-yes',
    `deleted_at` timestamp NOT NULL DEFAULT '1970-01-01 08:00:01' COMMENT '删除时间',
    `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',

    PRIMARY KEY (`id`),
    UNIQUE KEY `uniq_one` (`lark_user_id`, `work_symbol`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='飞书用户工作台表';

