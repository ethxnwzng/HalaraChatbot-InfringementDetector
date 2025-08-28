

WORK_SYMBOL = 'chatgpt-reviews-analyze'
JSON_KEY_EXCEL_DATA = 'excel_data'
JSON_KEY_EXCEL_NAME = 'excel_name'
JSON_KEY_EXCEL_COLUMNS = 'excel_columns'
JSON_KEY_REVIEW_FORMAT = 'review_format'
JSON_KEY_ASK_PROMPT = 'ask_prompt'
JSON_KEY_MERGE_PROMPT = 'merge_prompt'
JSON_KEY_SYS_PROMPT = 'system_prompt'
JSON_KEY_AUTO_MERGE = 'auto_merge'
JSON_KEY_TEMPERATURE = 'temperature'
JSON_KEY_WORDS_BATCH = 'words_in_batch'


def get_db_map_reviews(excel_data):
    map_reviews = {}
    for each in excel_data:
        review_id, review_content = '', ''
        for k, v in each.items():
            v = str(v).strip()
            # todo 写死了格式！！
            if k == '#1':
                review_id = v
            elif k == '#2':
                review_content = v
        map_reviews[review_id] = review_content
    return map_reviews

