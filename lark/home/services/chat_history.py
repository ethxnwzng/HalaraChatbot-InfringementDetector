from typing import Dict, List, Optional
from datetime import datetime, timedelta
from django.utils import timezone
from home.models import ChatMsg, ChatContext
import logging

logger = logging.getLogger(__name__)

class ChatHistoryService:
    """
    Service class for managing chat history and context in the mySQL database,
    specifically the chat_msg and chat_context tables in the common schema
    
    This class provides methods to:
    - Save chat messages (from bot and user)
    - Get chat history
    - Save and retrieve chat contexts
    """
    @staticmethod
    def save_message(msg_id: str, direction: str, msg_type: str, chat_type: str, 
                    chat_id: str, user_id: str, content: Dict, 
                    parent_id: str = '', root_id: str = '', chat_bot: str = 'idea_bot') -> ChatMsg:
        """Save a chat message using the existing ChatMsg model"""
        logger.info(f"[KIBANA] Saving message: chat_id={chat_id}, msg_id={msg_id}, user_id={user_id}, direction={direction}, msg_type={msg_type}, chat_type={chat_type}, parent_id={parent_id}, root_id={root_id}, content={content}, chat_bot={chat_bot}")
        return ChatMsg.objects.create(
            msg_id=msg_id,
            direction=direction,
            msg_type=msg_type,
            chat_type=chat_type,
            chat_id=chat_id,
            user_id=user_id,
            msg=content,
            msg_parent_id=parent_id,
            msg_root_id=root_id,
            at_bot=0,  # Default value
            open_id='',  # Can be updated if needed
            union_id='',  # Can be updated if needed
            deleted=0,
            dev_mode=0,
            chat_bot=chat_bot  # Use the provided chat_bot value
        )

    @staticmethod
    def get_chat_history(chat_id: str, limit: int = 10) -> List[ChatMsg]:
        """Get chat history for a specific chat"""
        logger.info(f"[KIBANA] Getting chat history: chat_id={chat_id}, limit={limit}")
        return ChatMsg.objects.filter(
            chat_id=chat_id,
            deleted=0
        ).order_by('-created_at')[:limit]

    @staticmethod
    def save_context(user_id: str, context_key: str, 
                    context_value: str, ttl_minutes: Optional[int] = None) -> ChatContext:
        """Save chat context with optional TTL"""
        logger.info(f"[KIBANA] Saving context: user_id={user_id}, context_key={context_key}, value={context_value}, ttl_minutes={ttl_minutes}")
        expires_at = None
        if ttl_minutes:
            expires_at = timezone.now() + timedelta(minutes=ttl_minutes)
        
        return ChatContext.objects.create(
            user_id=user_id,
            context_key=context_key,
            context_value=context_value,
            expires_at=expires_at
        )

    @staticmethod
    def get_context(user_id: str, context_key: str) -> Optional[ChatContext]:
        """Get chat context if it exists and hasn't expired"""
        logger.info(f"[KIBANA] Getting context: user_id={user_id}, context_key={context_key}")
        now = timezone.now()
        return ChatContext.objects.filter(
            user_id=user_id,
            context_key=context_key,
            expires_at__gt=now
        ).first() 