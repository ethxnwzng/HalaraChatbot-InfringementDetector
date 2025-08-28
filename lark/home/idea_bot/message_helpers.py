from home.idea_bot.chat_history import ChatHistoryService
from util.log_util import logger

def save_user_message(msg_id: str, chat_id: str, user_id: str, content: dict, 
                     message_type: str = 'text', chat_type: str = 'p2p', 
                     parent_id: str = '', root_id: str = ''):
    """Save user message to chat history"""
    try:
        ChatHistoryService.save_message(
            msg_id=msg_id,
            direction='receive',
            msg_type=message_type,
            chat_type=chat_type,
            chat_id=chat_id,
            user_id=user_id,
            content=content,
            parent_id=parent_id,
            root_id=root_id
        )
        return True
    except Exception as e:
        logger.error(f'Error saving user message: {str(e)}')
        return False

def save_bot_response(msg_id: str, chat_id: str, user_id: str, response: str, 
                     parent_id: str = '', root_id: str = ''):
    """Save bot response to chat history"""
    try:
        ChatHistoryService.save_message(
            msg_id=f"{msg_id}_response",
            direction='send',
            msg_type='text',
            chat_type='p2p',
            chat_id=chat_id,
            user_id=user_id,
            content={'text': response},
            parent_id=parent_id,
            root_id=root_id
        )
        return True
    except Exception as e:
        logger.error(f'Error saving bot response: {str(e)}')
        return False

def save_error_message(msg_id: str, chat_id: str, user_id: str, error_msg: str, 
                      parent_id: str = '', root_id: str = ''):
    """Save error message to chat history"""
    try:
        ChatHistoryService.save_message(
            msg_id=f"{msg_id}_error",
            direction='send',
            msg_type='text',
            chat_type='p2p',
            chat_id=chat_id,
            user_id=user_id,
            content={'text': error_msg},
            parent_id=parent_id,
            root_id=root_id
        )
        return True
    except Exception as e:
        logger.error(f'Error saving error message: {str(e)}')
        return False 