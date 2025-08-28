
CREATE TABLE IF NOT EXISTS `chat_msg` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT 'key',
    `msg_id` varchar(64) NOT NULL DEFAULT '' COMMENT 'lark open_message_id, like: om_***',
    `direction` varchar(16) NOT NULL DEFAULT '' COMMENT 'like: receive, send, chat_gpt',
    `msg_type` varchar(16) NOT NULL DEFAULT '' COMMENT 'like: text, image',
    `chat_type` varchar(16) NOT NULL DEFAULT '' COMMENT 'like: private, group',
    `chat_id` varchar(64) NOT NULL DEFAULT '' COMMENT 'lark open_chat_id, like: oc_***',
    `at_bot` tinyint(3) NOT NULL DEFAULT '0' COMMENT 'if @bot, 0-no, 1-yes',

    `user_id` varchar(64) NOT NULL DEFAULT '' COMMENT 'global user_id',
    `open_id` varchar(64) NOT NULL DEFAULT '' COMMENT 'open user_id, like: ou_***',
    `union_id` varchar(64) NOT NULL DEFAULT '' COMMENT 'union user_id, like: on_***',
    `msg_parent_id` varchar(64) NOT NULL DEFAULT '' COMMENT 'message parent, lark open_message_id, like: om_***',
    `msg_root_id` varchar(64) NOT NULL DEFAULT '' COMMENT 'message root, lark open_message_id, like: om_***',
    `msg` json DEFAULT NULL COMMENT 'msg json struct, like {text, user_agent, image_url}',

    `deleted` tinyint(3) NOT NULL DEFAULT '0' COMMENT '是否被删除, 0-no, 1-yes',
    `deleted_at` timestamp NOT NULL DEFAULT '1970-01-01 08:00:01' COMMENT '删除时间',
    `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',

    PRIMARY KEY (`id`),
    UNIQUE KEY `uniq_msg` (`msg_id`),
    KEY `idx_chat` (`chat_id`),
    KEY `idx_user` (`user_id`),
    KEY `idx_create` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='飞书对话消息表';

