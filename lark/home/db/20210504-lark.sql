/**
 * lark approval persistence
 */

CREATE TABLE IF NOT EXISTS `lark_approval_instance` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
    `approval_code` varchar(64) NOT NULL DEFAULT '' COMMENT '审批定义code',
    `instance_code` varchar(64) NOT NULL DEFAULT '' COMMENT '审批实例code',
    `approval_name` varchar(64) NOT NULL DEFAULT '' COMMENT '审批定义名称',

    `submitter` varchar(64) NOT NULL DEFAULT '' COMMENT '提交人飞书open-id',
    `submit_time` timestamp NOT NULL DEFAULT '1970-01-01 08:00:01' COMMENT '审批提交时间',
    `detail` json DEFAULT NULL COMMENT '业务详细信息，因类型而异',
    `approval_status` smallint NOT NULL DEFAULT '0' COMMENT '审批状态，详见enum/ApprovalStatus',
    `approval_time` timestamp NOT NULL DEFAULT '1970-01-01 08:00:01' COMMENT '审批结果时间',

    `deleted` tinyint(3) NOT NULL DEFAULT '0' COMMENT '是否被删除, 0-no, 1-yes',
    `deleted_at` timestamp NOT NULL DEFAULT '1970-01-01 08:00:01' COMMENT '删除时间',
    `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',

    PRIMARY KEY (`id`),
    UNIQUE KEY `uniq_instance` (`instance_code`),
    KEY `idx_approval` (`approval_code`),
    KEY `idx_submitter` (`submitter`),
    KEY `idx_subtime` (`submit_time`),
    KEY `idx_status` (`approval_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='飞书审批实例表';

