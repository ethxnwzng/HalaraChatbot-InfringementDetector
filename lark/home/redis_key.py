

def lock_chatgpt_review_run(user_id):
    return 'lock:chatgpt:review:run:{}'.format(user_id)


def lock_chatgpt_review_merge(user_id):
    return 'lock:chatgpt:review:merge:{}'.format(user_id)

