alter table chat_msg
add column `dev_mode` tinyint(3) NOT NULL DEFAULT '0' COMMENT '是否开发模式的消息, 0-no, 1-yes';

CREATE TABLE IF NOT EXISTS `aigc_prompt` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT 'key',
    `prompt_type` varchar(32) NOT NULL DEFAULT '' COMMENT 'chatgpt-system, chatgpt-user',
    `scope_type` varchar(32) NOT NULL DEFAULT '' COMMENT 'use in which scope, like: lark-chat, lark-user, public, lark-group',
    `scope_id` varchar(64) NOT NULL DEFAULT '' COMMENT 'like: lark_user_id, 若为空则公共可用',
    `title` varchar(64) NOT NULL DEFAULT '' COMMENT 'prompt title',
    `prompt_topic` varchar(64) NOT NULL DEFAULT '' COMMENT 'prompt topic for category',

    `detail` json DEFAULT NULL COMMENT 'prompt, like {text}',
    `user_id_create` varchar(64) NOT NULL DEFAULT '' COMMENT 'global user_id',
    `user_id_update` varchar(64) NOT NULL DEFAULT '' COMMENT 'global user_id',

    `deleted` tinyint(3) NOT NULL DEFAULT '0' COMMENT '是否被删除, 0-no, 1-yes',
    `deleted_at` timestamp NOT NULL DEFAULT '1970-01-01 08:00:01' COMMENT '删除时间',
    `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',

    PRIMARY KEY (`id`),
    UNIQUE KEY `uniq_one` (`prompt_type`, `scope_type`, `scope_id`, `title`),
    KEY `idx_scope` (`scope_type`, `scope_id`),
    KEY `idx_topic` (`prompt_topic`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='aigc-prompt汇总表';

INSERT INTO `aigc_prompt`(id, prompt_type, scope_type, scope_id, title, prompt_topic, detail, user_id_create, user_id_update) VALUES (1,'chatgpt-system','public','','default','','{\"text\": \"You are an intelligent AI assistant.\"}','dac53d12','dac53d12'),(2,'chatgpt-system','public','','ads copywriting in 3s','','{\"text\": \"As a marketing copywriting robot for women\'s clothing products, your task is to create short, native, and attractive descriptions of the products that showcase their unique features in a dramatic way. Your response should be concise and written in a TikTok tone that captures attention quickly.\\n\\nPlease note that you should avoid using an advertising or sales tone in your responses. Instead, focus on highlighting the product\'s benefits and qualities in a creative and engaging manner, without coming across as too pushy or promotional.\\n\\nYour descriptions should be short enough to be read by humans within 3 seconds, while still conveying all the necessary information about the product. \\n\\nFollowing statements are the good examples you should learn from:\\n\\n1. \\\"My newfound love for jeans makes my butt look so good!\\\"\\n2. \\\"This dress gives you \\\"that hot girl summer\\\" look without making you feel sticky!\\\"\\n3. \\\"Why r these the best and most inexpensive joggers I own\\\"\\n4. \\\"Why does this pair of joggers turn out to be my favourite purchase ever\\\"\\n5. \\\"I\'m going to be sad if anyone misses out on these Leg-contouring Leggings\\\" \\n6. \\\"Run, that dress that went viral is back in stock and it\'s on sale now!\\\"\"}','dac53d12','dac53d12');



CREATE TABLE IF NOT EXISTS `chat_tone` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT 'key',
    `tone_type` varchar(32) NOT NULL DEFAULT '' COMMENT 'like: chatgpt-system',
    `chat_id` varchar(64) NOT NULL DEFAULT '' COMMENT 'lark open_chat_id, like: oc_***',
    `prompt_id` bigint(20) NOT NULL DEFAULT '0' COMMENT 'aigc_prompt table id',

    `user_id_create` varchar(64) NOT NULL DEFAULT '' COMMENT 'global user_id',
    `user_id_update` varchar(64) NOT NULL DEFAULT '' COMMENT 'global user_id',

    `deleted` tinyint(3) NOT NULL DEFAULT '0' COMMENT '是否被删除, 0-no, 1-yes',
    `deleted_at` timestamp NOT NULL DEFAULT '1970-01-01 08:00:01' COMMENT '删除时间',
    `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',

    PRIMARY KEY (`id`),
    UNIQUE KEY `uniq_one` (`tone_type`, `chat_id`),
    KEY `idx_prompt` (`prompt_id`),
    KEY `idx_chat` (`chat_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='飞书对话tone映射表';

