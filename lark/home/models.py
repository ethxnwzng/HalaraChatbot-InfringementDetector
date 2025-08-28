from django.db import models


class LarkApprovalInstance(models.Model):
    id = models.BigAutoField(primary_key=True)
    approval_code = models.CharField(max_length=64)
    instance_code = models.CharField(unique=True, max_length=64)
    approval_name = models.CharField(max_length=64)
    submitter = models.CharField(max_length=64)
    submit_time = models.DateTimeField()
    detail = models.JSONField(blank=True, null=True)
    approval_status = models.SmallIntegerField()
    approval_time = models.DateTimeField()
    deleted = models.IntegerField()
    # deleted_at = models.DateTimeField()
    # created_at = models.DateTimeField()
    # updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'lark_approval_instance'


class ChatMsg(models.Model):
    id = models.BigAutoField(primary_key=True)
    msg_id = models.CharField(unique=True, max_length=64)
    direction = models.CharField(max_length=16)
    msg_type = models.CharField(max_length=16)
    chat_type = models.CharField(max_length=16)
    chat_id = models.CharField(max_length=64)
    at_bot = models.IntegerField()
    user_id = models.CharField(max_length=64)
    open_id = models.CharField(max_length=64)
    union_id = models.CharField(max_length=64)
    msg_parent_id = models.CharField(max_length=64)
    msg_root_id = models.CharField(max_length=64)
    msg = models.JSONField(blank=True, null=True)
    deleted = models.IntegerField()
    dev_mode = models.IntegerField()
    chat_bot = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'chat_msg'
        indexes = [
            models.Index(fields=['user_id'], name='idx_user_id'),
            models.Index(fields=['chat_id'], name='idx_chat_id'),
            models.Index(fields=['msg_parent_id'], name='idx_msg_parent_id'),
            models.Index(fields=['msg_root_id'], name='idx_msg_root_id'),
            models.Index(fields=['created_at'], name='idx_created_at')
        ]

#builds on ChatMsg class which handles basic message storage
#ChatContext used in chat_history.py to manage conversation contexts
class ChatContext(models.Model):
    """Manages conversation contexts and history for the chat system.
    
    This model extends the basic message storage provided by ChatMsg to handle:
    - Conversation context tracking
    - Context expiration
    - User-specific context storage
    
    Indexes are optimized for:
    - Quick lookups by user_id and context_key
    - Efficient expiration checks
    """
    id = models.BigAutoField(primary_key=True)
    user_id = models.CharField(max_length=64, db_index=True,
                             help_text="Lark user ID for context ownership")
    context_key = models.CharField(max_length=64, db_index=True,
                                 help_text="Unique identifier for the context type")
    context_value = models.JSONField(blank=True, null=True,
                                   help_text="Stored context data in JSON format")
    created_at = models.DateTimeField(auto_now_add=True,
                                    help_text="When this context was first created")
    updated_at = models.DateTimeField(auto_now=True,
                                    help_text="Last time this context was modified")
    expires_at = models.DateTimeField(null=True, db_index=True,
                                    help_text="When this context should expire")

    class Meta:
        managed = False
        db_table = 'chat_context'
        indexes = [
            models.Index(fields=['user_id', 'context_key'], name='ctx_user_key_idx'),
            models.Index(fields=['expires_at'], name='ctx_expiry_idx')
        ]
        unique_together = (('user_id', 'context_key'),)  # Prevent duplicate contexts

    def __str__(self):
        """String representation for debugging and admin interface"""
        return f"ChatContext(user={self.user_id}, key={self.context_key})"

    def is_expired(self):
        """Check if the context has expired"""
        from django.utils import timezone
        return self.expires_at and self.expires_at < timezone.now()

    def extend_expiry(self, minutes=60):
        """Extend the context expiration time"""
        from django.utils import timezone
        self.expires_at = timezone.now() + timezone.timedelta(minutes=minutes)
        self.save(update_fields=['expires_at', 'updated_at'])

class AigcPrompt(models.Model):
    id = models.BigAutoField(primary_key=True)
    prompt_type = models.CharField(max_length=32)
    scope_type = models.CharField(max_length=32)
    scope_id = models.CharField(max_length=64)
    title = models.CharField(max_length=64)
    prompt_topic = models.CharField(max_length=64)
    detail = models.JSONField(blank=True, null=True)
    user_id_create = models.CharField(max_length=64)
    user_id_update = models.CharField(max_length=64)
    deleted = models.IntegerField()
    # deleted_at = models.DateTimeField()
    # created_at = models.DateTimeField()
    # updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'aigc_prompt'
        unique_together = (('prompt_type', 'scope_type', 'scope_id', 'title'),)


class ChatTone(models.Model):
    id = models.BigAutoField(primary_key=True)
    tone_type = models.CharField(max_length=32)
    chat_id = models.CharField(max_length=64)
    prompt_id = models.BigIntegerField()
    user_id_create = models.CharField(max_length=64)
    user_id_update = models.CharField(max_length=64)
    deleted = models.IntegerField()
    # deleted_at = models.DateTimeField()
    # created_at = models.DateTimeField()
    # updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'chat_tone'
        unique_together = (('tone_type', 'chat_id'),)


class IdeaMaterial(models.Model):
    id = models.BigAutoField(primary_key=True)
    material_type = models.CharField(max_length=32)
    material_source = models.CharField(max_length=32)
    material_id = models.CharField(max_length=64)
    page_url = models.CharField(max_length=512)
    caption = models.CharField(max_length=512)
    post_at = models.BigIntegerField()
    play_count = models.IntegerField()
    like_count = models.IntegerField()
    comment_count = models.IntegerField()
    collect_count = models.IntegerField()
    share_count = models.IntegerField()
    material_url = models.CharField(max_length=512)
    cover_url = models.CharField(max_length=512)
    music_info = models.JSONField(blank=True, null=True)
    post_user_id = models.CharField(max_length=64)
    post_user_name = models.CharField(max_length=64)
    user_id_create = models.CharField(max_length=64)
    user_id_update = models.CharField(max_length=64)
    deleted = models.IntegerField()
    # deleted_at = models.DateTimeField()
    # created_at = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)
    detail = models.JSONField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'idea_material'
        unique_together = (('material_source', 'material_id', 'user_id_create'),)


class LarkUserWorkbench(models.Model):
    id = models.BigAutoField(primary_key=True)
    lark_user_id = models.CharField(max_length=64)
    work_symbol = models.CharField(max_length=32)
    detail = models.JSONField(blank=True, null=True)
    # deleted = models.IntegerField()
    # deleted_at = models.DateTimeField()
    # created_at = models.DateTimeField()
    # updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'lark_user_workbench'
        unique_together = (('lark_user_id', 'work_symbol'),)


class ObserverArchive(models.Model):
    id = models.BigAutoField(primary_key=True)
    archive_type = models.SmallIntegerField()
    archive_name = models.CharField(max_length=64)
    record_count = models.IntegerField()
    origin_url = models.CharField(max_length=256)
    origin_info = models.JSONField(blank=True, null=True)
    process_info = models.JSONField(blank=True, null=True)
    # deleted = models.IntegerField()
    # deleted_at = models.DateTimeField()
    # created_at = models.DateTimeField()
    # updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'observer_archive'
        unique_together = (('archive_type', 'archive_name', 'record_count'),)


class LarkPoll(models.Model):
    id = models.BigAutoField(primary_key=True)
    poll_type = models.CharField(max_length=32)
    lark_user = models.CharField(max_length=32)
    repoll = models.IntegerField()
    answer = models.JSONField(blank=True, null=True)
    result = models.JSONField(blank=True, null=True)
    # deleted = models.IntegerField()
    # deleted_at = models.DateTimeField()
    # created_at = models.DateTimeField()
    # updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'lark_poll'



