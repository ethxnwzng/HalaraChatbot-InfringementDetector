from django.urls import path

from . import views, views_bu, cron, views_api, views_idea

urlpatterns = [
    path('', views.index, name='index'),
    path('page', views.index, name='index'),
    path('health/', views.health, name='health'),
    path('event', views.event, name='event'),
    path('approval/cs/submit', views_bu.cs_submit_approval, name='cs_submit_approval'),
    path('page/approval', views.approval_page, name='approval'),
    path('ajax-check-approval', views.ajax_check_approval, name='check-approval'),
    path('ajax-login', views.ajax_login, name='login'),
    path('approval/instance', views.approval_instance, name='approval-instance'),
    path('approval/cancel', views.cancel_approval, name='approval_cancel'),
    path('approval/check/pending', views.check_pending, name='approval_check_pending'),

    # login
    path('page/404', views.page_404, name='404'),
    path('callback/sso', views.sso_callback, name='sso'),

    # chatGPT
    path('page/chatgpt', views.chatgpt_index, name='chatgpt'),
    path('page/chatgpt/prompt', views.chatgpt_prompt, name='chatgpt-prompt'),
    path('page/chatgpt/prompt/manage', views.chatgpt_prompt_manage, name='chatgpt-prompt-manage'),
    path('page/chatgpt/prompt/manage/<str:prompt_type>', views.chatgpt_prompt_manage, name='chatgpt-prompt-manage'),
    path('api/chatgpt/ask', views_api.gpt_ask, name='chatgpt-ask'),
    path('api/chatgpt/tone/add', views_api.add_tone, name='chatgpt-tone-add'),
    path('api/chatgpt/prompt/del', views_api.del_prompt, name='chatgpt-prompt-del'),
    path('api/chatgpt/recipe/add', views_api.add_recipe, name='chatgpt-recipe-add'),
    path('page/chatgpt/review', views.page_chatgpt_review, name='chatgpt-review'),
    path('api/chatgpt/review/upload', views_api.chatgpt_review_upload, name='chatgpt-review-upload'),
    path('api/chatgpt/review/run', views_api.chatgpt_review_run, name='chatgpt-review-run'),
    path('api/chatgpt/review/merge', views_api.chatgpt_review_merge, name='chatgpt-review-merge'),
    path('api/chatgpt/review/manual/merge', views_api.chatgpt_manual_merge, name='chatgpt-review-manual-merge'),
    path('api/chatgpt/review/manual/trim', views_api.chatgpt_manual_trim, name='chatgpt-review-manual-trim'),
    path('api/chatgpt/gpt4/users', views_api.chatgpt_gpt4_users, name='chatgpt-gpt4-users'),

    # tools
    path('page/tool', views.tool, name='tool'),
    path('page/tool/speech2text', views.tool_speech2text, name='tool-speech2text'),
    path('api/tool/speech2text/receive', views_api.tool_speech2text_receive, name='tool-speech2text-receive'),

    # idea_bot
    path('event/idea', views_idea.event, name='event-idea'),
    path('webhook/idea_bot/', views_idea.event, name='webhook-idea-bot'),
    path('page/idea', views.page_idea_index, name='idea-index'),
    path('page/idea/list', views.page_idea_list, name='idea-list'),
    path('api/idea/del', views_idea.del_idea, name='idea-del'),
    path('api/idea/essay', views_idea.idea_essay, name='idea-essay'),

    # Obs bot
    path('event/obs', views_api.event_obs, name='event-obs'),

    # tools
    path('page/tool/words', views.page_tool_words),
    path('api/tool/words', views_api.tackle_words_split),
    path('page/tool/detect', views.page_tool_detect),
    path('api/tool/upload', views.upload_file),
    path('api/tool/detect', views_api.tackle_detect_face),
    path('page/poll/mbti', views.mbti),
    path('api/poll/mbti/cal', views.cal_mbti),
    path('api/excel/upload', views.handle_excel_file, name='handle_excel_file'),
    
    # crawler test endpoint
    path('test-crawler', views.test_crawler, name='test-crawler'),
]

# scheduler
cron.init()
