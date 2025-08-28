alter table `chat_msg`
add column `chat_bot` varchar(32) NOT NULL DEFAULT 'lark_bot' COMMENT '所属飞书聊天机器人，比如：lark_bot, idea_bot';

CREATE TABLE IF NOT EXISTS `idea_material` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT 'key',
    `material_type` varchar(32) NOT NULL DEFAULT '' COMMENT 'text, picture, audio, video',
    `material_source` varchar(32) NOT NULL DEFAULT '' COMMENT 'source, e.g. douyin, xiaohongshu',
    `material_id` varchar(64) NOT NULL DEFAULT '' COMMENT 'material id in source naming',

    `page_url` varchar(512) NOT NULL DEFAULT '' COMMENT 'material page link',
    `caption` varchar(512) NOT NULL DEFAULT '' COMMENT '[title] caption text',
    `post_at` bigint(20) NOT NULL DEFAULT '0' COMMENT 'unix time in seconds',

    `play_count` int NOT NULL DEFAULT '0' COMMENT 'play',
    `like_count` int NOT NULL DEFAULT '0' COMMENT 'like',
    `comment_count` int NOT NULL DEFAULT '0' COMMENT 'comment',
    `collect_count` int NOT NULL DEFAULT '0' COMMENT 'collect',
    `share_count` int NOT NULL DEFAULT '0' COMMENT 'share',

    `material_url` varchar(512) NOT NULL DEFAULT '' COMMENT 's3 url',
    `cover_url` varchar(512) NOT NULL DEFAULT '' COMMENT 's3 cover url',
    `music_info` json DEFAULT NULL COMMENT 'music detail if has',

    `post_user_id` varchar(64) NOT NULL DEFAULT '' COMMENT 'material poster user-id',
    `post_user_name` varchar(64) NOT NULL DEFAULT '' COMMENT 'material poster user-name',
    `user_id_create` varchar(64) NOT NULL DEFAULT '' COMMENT 'global user_id',
    `user_id_update` varchar(64) NOT NULL DEFAULT '' COMMENT 'global user_id',

    `deleted` tinyint(3) NOT NULL DEFAULT '0' COMMENT '是否被删除, 0-no, 1-yes',
    `deleted_at` timestamp NOT NULL DEFAULT '1970-01-01 08:00:01' COMMENT '删除时间',
    `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',

    PRIMARY KEY (`id`),
    UNIQUE KEY `uniq_one` (`material_source`, `material_id`, `user_id_create`),
    KEY `idx_user` (`user_id_create`),
    KEY `idx_poster` (`post_user_id`),
    KEY `idx_source` (`material_source`),
    KEY `idx_time` (`post_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='idea素材表';

alter table `idea_material`
add column `detail` json DEFAULT NULL COMMENT '详细内容，比如{essay-小作文}';

