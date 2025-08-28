import re
import traceback
import os
import uuid
import django
from datetime import datetime
from home.enums import MaterialType
from util import redis_util, s3_util
import pandas as pd
from typing import Dict, Optional, Tuple, List
import json
import tempfile
import time

os.environ['DJANGO_SETTINGS_MODULE'] = 'lark.settings'
django.setup()

from home.lark_client import bot
from home.config import constant
from home.idea_bot import client, spider, meta, openai_client, file_client
from home.idea_bot.enum import VideoSource, FileType
from home.message import LarkEvent
from home.models import ChatMsg, IdeaMaterial
from util.lark_util import Lark
from util.log_util import logger
from home.idea_bot.version import get_version_info, get_capabilities, CAPABILITIES
from home.idea_bot.chat_history import ChatHistoryService
from home.idea_bot.response_templates import (
    get_version_response, get_system_message, get_file_processing_response,
    get_error_response, get_image_analysis_response, get_analysis_system_message
)
from home.idea_bot.message_helpers import (
    save_user_message, save_bot_response, save_error_message
)


PT_LINK = re.compile(r'^.*(https?://[^ ,，?)\]]*).*$')

# ============================================================================
# MAIN EVENT HANDLERS
# ============================================================================

def tackle_event(lark_event: LarkEvent):
    """
    Main event handler for the idea_bot system that processes incoming Lark events and routes them to appropriate handlers. 
    This function serves as the primary entry point for all bot interactions, handling message deduplication, event validation, 
    and routing to specialized handlers based on message type (file vs text). It manages the complete event processing workflow 
    from reception to response. This is the top-level function that receives all incoming events from the Lark platform. It coordinates 
    the entire bot workflow by calling handle_file_message() for file uploads and handle_text_message() for text messages. It also 
    handles special cases like video link processing and ensures proper message saving and error handling throughout the process.

    params:
    - lark_event (LarkEvent): The complete event object from Lark containing message details, user information, and event metadata

    returns:
    Returns None after processing the event, with responses sent directly to the user through the Lark client
    """
    if not lark_event or (not lark_event.body_message and not lark_event.body_emoticon):
        return False
    #deduplicate
    event_id = lark_event.event_id
    if not redis_util.set_nx('idea:lock:event:{}'.format(event_id), ex=3600):
        #filter duplicate events
        return None
    #message
    if body := lark_event.body_message:
        chat_type = body.chat_type
        if chat_type != 'p2p':
            #todo idea_bot temporarily only supports single chat
            return None
            
        #get message details
        msg_id = body.message_id
        if ChatMsg.objects.filter(msg_id=msg_id, deleted=constant.NO_IN_DB).count() > 0:
            #filter duplicate messages
            return None
            
        text = body.text
        chat_id = body.chat_id
        user_id = body.user_id
        
        #store the message using chathistoryservice
        msg_receive = {'text': text}
        try:
            at_bot = meta.CHAT_BOT_NAME in body.ats
            if at_bot:
                at_bot = constant.YES_IN_DB
            else:
                at_bot = constant.NO_IN_DB
                
            #use chathistoryservice to save the message
            save_user_message(
                msg_id=msg_id,
                chat_id=chat_id,
                user_id=user_id,
                content=msg_receive,
                message_type=body.message_type,
                chat_type=chat_type,
                parent_id=body.parent_id,
                root_id=body.root_id
            )
            
            #also store in redis for quick access
            redis_util.set(f'chat:msg:{msg_id}', msg_receive, ex=3600)
            
        except Exception as e:
            logger.error(f'[idea chat write msg exception]: {traceback.format_exc()}')
            Lark(constant.LARK_CHAT_ID_zzm).send_rich_text('idea chat write exception', traceback.format_exc())
            return None
            
        #first try to handle special message types
        if body.message_type == 'file':
            response = handle_file_message(body, chat_id, user_id, msg_id)
            if response:
                client.reply(chat_id, user_id, response)
            return None
            
        #handle image/video uploads from the image/video button
        if body.message_type in ['image', 'video', 'post']:
            response = handle_image_video_message(body, chat_id, user_id, msg_id)
            if response:
                client.reply(chat_id, user_id, response)
            return None
            
        #handle copy-pasted images in text messages
        if body.message_type == 'text' and _contains_image_content(body.content):
            response = handle_copy_pasted_image(body, chat_id, user_id, msg_id)
            if response:
                client.reply(chat_id, user_id, response)
            return None
            
        #if no special handling was needed, treat it as a general chat message
        try:
            #use handle_text_message instead of handle_chat_message for better context and capability awareness
            response = handle_text_message(text, chat_id, user_id, msg_id)
            if response:
                client.reply(chat_id, user_id, response)
        except Exception as e:
            logger.error(f'Error handling chat message: {str(e)}')
            client.reply(chat_id, user_id, "I apologize, but I encountered an error. Please try again later.")
            
    return None

# ============================================================================
# MAIN MESSAGE HANDLERS
# ============================================================================

def handle_file_message(body, chat_id: str, user_id: str, msg_id: str) -> Optional[str]:
    """
    Main entry point for handling file uploads in the idea_bot system. 
    This function orchestrates the entire file processing workflow, from parsing incoming file messages 
    to routing them to appropriate handlers based on whether they are local files or Lark-uploaded files. 
    It serves as the primary dispatcher for all file-related operations and ensures proper error handling and logging 
    throughout the process. Called by tackle_event() when a file message is detected, this function delegates to specialized 
    helper functions (_handle_local_file, _handle_lark_file) based on the file source, and those 
    helpers further delegate to specific processors (_process_image_file, _process_regular_file) based on file type.

    params:
    - body: The raw message body object containing file metadata and content information
    - chat_id (str): Unique identifier for the chat session where the file was uploaded
    - user_id (str): Unique identifier for the user who uploaded the file
    - msg_id (str): Unique identifier for the specific message containing the file

    returns:
    Returns a string response to be sent back to the user, or None if processing fails
    """
    try:
        # Parse message content
        content = body.content
        logger.info(f'[handle_file_message] Received message content: {content}')
        
        if not isinstance(content, dict):
            try:
                content = json.loads(content)
                logger.info(f'[handle_file_message] Parsed JSON content: {content}')
            except:
                logger.error(f'[handle_file_message] Invalid content type and not JSON: {type(content)}')
                error_msg = get_error_response("Invalid file message format")
                save_error_message(msg_id, chat_id, user_id, error_msg, msg_id, msg_id)
                return error_msg
        
        # Extract file information
        file_key = content.get('file_key', '') or (content.get('file_info', {}) or {}).get('file_key', '')
        file_name = content.get('file_name', '')
        logger.info(f'[handle_file_message] Extracted file_key: {file_key}, file_name: {file_name}')
        
        # Handle local file
        if file_name and os.path.exists(file_name):
            return _handle_local_file(file_name, chat_id, user_id, msg_id)
        
        # Handle Lark file
        if not file_key:
            logger.error('[handle_file_message] No file_key found in message content')
            error_msg = get_error_response("No file key found in message")
            save_error_message(msg_id, chat_id, user_id, error_msg, msg_id, msg_id)
            return error_msg
            
        return _handle_lark_file(file_key, file_name, chat_id, user_id, msg_id)
            
    except Exception as e:
        logger.error(f'[handle_file_message] Unexpected error: {str(e)}')
        logger.error(f'[handle_file_message] Traceback: {traceback.format_exc()}')
        error_msg = get_error_response(f"Unexpected error processing file: {str(e)}")
        save_error_message(msg_id, chat_id, user_id, error_msg, msg_id, msg_id)
        return error_msg

def handle_image_video_message(body, chat_id: str, user_id: str, msg_id: str) -> Optional[str]:
    """
    Main entry point for handling image and video uploads from the Lark image/video button.
    This function handles the specific message formats that Lark sends when users upload
    images or videos through the dedicated image/video upload button, which is different
    from the general file upload functionality. It extracts image keys from the message
    content and routes them to the appropriate image processing functions.
    
    This function supports:
    - message_type: 'image' - Direct image uploads
    - message_type: 'video' - Direct video uploads (currently unsupported)
    - message_type: 'post' - Rich text posts containing images
    
    params:
    - body: The raw message body object containing image/video metadata and content
    - chat_id (str): Unique identifier for the chat session where the image/video was uploaded
    - user_id (str): Unique identifier for the user who uploaded the image/video
    - msg_id (str): Unique identifier for the specific message containing the image/video
    
    returns:
    Returns a string response to be sent back to the user, or None if processing fails
    """
    try:
        #parse message content
        content = body.content
        logger.info(f'[handle_image_video_message] Received message content: {content}')
        
        if not isinstance(content, dict):
            try:
                content = json.loads(content)
                logger.info(f'[handle_image_video_message] Parsed JSON content: {content}')
            except:
                logger.error(f'[handle_image_video_message] Invalid content type and not JSON: {type(content)}')
                error_msg = get_error_response("Invalid image/video message format")
                save_error_message(msg_id, chat_id, user_id, error_msg, msg_id, msg_id)
                return error_msg
        
        #extract image information based on message type
        image_key = None
        file_name = None
        
        if body.message_type == 'image':
            #direct image upload
            image_key = content.get('image_key', '')
            file_name = content.get('file_name', 'image.jpg')
            logger.info(f'[handle_image_video_message] Direct image upload - image_key: {image_key}')
            
        elif body.message_type == 'video':
            #direct video upload - currently unsupported
            logger.warning(f'[handle_image_video_message] Video uploads are not currently supported')
            error_msg = get_error_response("Video uploads are not currently supported. Please upload images only.")
            save_error_message(msg_id, chat_id, user_id, error_msg, msg_id, msg_id)
            return error_msg
            
        elif body.message_type == 'post':
            #rich text post containing images
            logger.info(f'[handle_image_video_message] Processing post message with content: {content}')
            
            #look for images in the post content
            post_content = content.get('content', [])
            if isinstance(post_content, list):
                for content_block in post_content:
                    if isinstance(content_block, list):
                        for item in content_block:
                            if isinstance(item, dict) and item.get('tag') == 'img':
                                image_key = item.get('image_key', '')
                                file_name = f"post_image_{int(time.time())}.jpg"
                                logger.info(f'[handle_image_video_message] Found image in post - image_key: {image_key}')
                                break
                        if image_key:
                            break
        
        #validate that we found an image
        if not image_key:
            logger.error(f'[handle_image_video_message] No image_key found in message content')
            error_msg = get_error_response("No image found in the message")
            save_error_message(msg_id, chat_id, user_id, error_msg, msg_id, msg_id)
            return error_msg
        
        #process the image using the existing lark file processing infrastructure
        logger.info(f'[handle_image_video_message] Processing image with key: {image_key}')
        return _handle_lark_file(image_key, file_name, chat_id, user_id, msg_id)
            
    except Exception as e:
        logger.error(f'[handle_image_video_message] Unexpected error: {str(e)}')
        logger.error(f'[handle_image_video_message] Traceback: {traceback.format_exc()}')
        error_msg = get_error_response(f"Unexpected error processing image/video: {str(e)}")
        save_error_message(msg_id, chat_id, user_id, error_msg, msg_id, msg_id)
        return error_msg

def handle_text_message(text: str, chat_id: str, user_id: str, msg_id: str = '') -> Optional[str]:
    """
    Main entry point for handling text messages in the idea_bot system. This function orchestrates the 
    complete text message processing workflow, including version queries, file context retrieval, chat context 
    management, and AI response generation. It maintains conversation context using Redis and provides intelligent 
    responses based on current file analysis context and chat history. Called by tackle_event() for all text messages, 
    this function is the primary coordinator for text-based interactions, managing both simple queries (like version requests) 
    and complex conversations with context awareness. It integrates with Redis for context persistence and OpenAI for 
    intelligent response generation, ensuring seamless user experience across multiple interactions.
    
    params:
    - text (str): The text content of the user's message
    - chat_id (str): Unique identifier for the chat session
    - user_id (str): Unique identifier for the user sending the message
    - msg_id (str, optional): Unique identifier for the message, used for saving to chat history
    
    returns:
    Returns a string response to be sent back to the user, or None if processing fails
    """
    try:
        #check for version query first
        if text.lower().strip() in ['version', 'v', 'ver']:
            return get_version_response()
        
        #check for clear command
        if text.lower().strip() == '/clear':
            #clear all context and tokens for this user
            redis_util.delete(f'file_context:{user_id}')
            redis_util.delete(f'full_file_context:{user_id}')
            redis_util.delete(f'chat_context:{chat_id}:{user_id}')
            redis_util.delete(f'chat_context:{chat_id}')
            redis_util.delete(f'chat_context_hash:{chat_id}')
            redis_util.hdel(f"user_preferences:{user_id}", "language")
            return "Chat history and file context cleared. How can I help you?"
        
        #check for analyze files command
        if text.lower().strip() in ['analyze these files', 'analyze files', 'ready for files', 'prepare for analysis']:
            return "I'm ready to analyze your files! Please upload the files you'd like me to analyze, and I'll provide detailed insights on the data."
        
        #check for large file analysis command
        if text.lower().strip() in ['analyze large file', 'chunked analysis', 'progressive analysis']:
            return "I can analyze large files in chunks to avoid token limits. Upload your large file and I'll analyze it progressively, providing insights on different sections of the data."
        
        #check for detailed analysis commands
        if text.lower().strip() in ['describe this image', 'describe image', 'detailed image analysis', 'show me the image details']:
            #check if there's recent image context and provide detailed analysis
            return handle_detailed_analysis_request(text, user_id, current_language, 'image')
        
        if text.lower().strip() in ['describe this file', 'describe file', 'detailed file analysis', 'show me the file details']:
            #check if there's recent file context and provide detailed analysis
            return handle_detailed_analysis_request(text, user_id, current_language, 'file')
        
        #detect language preference from user message
        language_preference = detect_language_preference(text)
        
        #update language preference in redis if detected
        if language_preference:
            redis_util.hset(f"user_preferences:{user_id}", "language", language_preference)
        
        #get current language preference
        current_language = redis_util.hget(f"user_preferences:{user_id}", "language")
        
        #get file context from redis
        file_context = redis_util.get(f'file_context:{user_id}')
        
        #ensure file_context is a dictionary if it exists
        if file_context and isinstance(file_context, str):
            try:
                file_context = json.loads(file_context)
            except json.JSONDecodeError:
                logger.warning(f'[handle_text_message] Invalid JSON in file_context for user {user_id}')
                file_context = None
        
        #check if this is a follow-up question about a recently uploaded file
        #look for analysis-related keywords in the user's message
        analysis_keywords = [
            'analyze', 'analysis', 'insights', 'describe', 'what', 'how', 'tell me about', 'show me',
            'explain', 'break down', 'summarize', 'overview', 'details', 'findings', 'results',
            'trends', 'patterns', 'statistics', 'data', 'information', 'report', 'summary'
        ]
        is_analysis_request = any(keyword in text.lower() for keyword in analysis_keywords)
        
        #also check for question patterns
        question_patterns = ['what is', 'what are', 'how is', 'how are', 'tell me', 'show me', 'give me']
        is_question = any(pattern in text.lower() for pattern in question_patterns)
        
        #if user is asking for analysis or asking a question and we have file context, treat it as a file analysis request
        if (is_analysis_request or is_question) and file_context:
            logger.info(f'[handle_text_message] Detected analysis/question request with file context, treating as file analysis')
            #use stored file context for analysis instead of conversation context
            analysis_messages = [
                get_system_message(file_context, current_language),
                {"role": "user", "content": f"Analyze this data and answer: {text}"}
            ]
            
            #get full file data for analysis if available
            full_file_context = get_full_file_context_from_redis(user_id)
            if full_file_context:
                analysis_system = get_analysis_system_message(full_file_context, current_language)
                analysis_messages[0] = analysis_system
            
            response = openai_client.chat_completion(analysis_messages)
            if response:
                return response
            else:
                logger.error(f'[handle_text_message] OpenAI returned None response for file analysis')
                return get_error_response("I encountered an error analyzing the file. Please try again.")
        
        #check if this is a large dataset that needs special handling
        is_large_dataset = False
        if file_context and isinstance(file_context, dict) and file_context.get('full_data_available'):
            processed_data = file_context.get('processed_data', {})
            if isinstance(processed_data, dict):
                rows = processed_data.get('rows', 0)
                is_large_dataset = rows > 50
        
        #get chat context from redis
        chat_context = _get_chat_context(chat_id, user_id)
        
        #prepare messages for openai
        messages = []
        
        #add system message with file context
        system_message = get_system_message(file_context, current_language)
        messages.append(system_message)
        
        #add chat history
        if chat_context:
            messages.extend(chat_context)
        
        #add current user message
        messages.append({"role": "user", "content": text})
        
        #for datasets with file context, use analysis path
        if file_context:
            #use stored file context for analysis instead of conversation context
            analysis_messages = [
                system_message,
                {"role": "user", "content": f"Analyze this data and answer: {text}"}
            ]
            
            #get full file data for analysis if available
            full_file_context = get_full_file_context_from_redis(user_id)
            if full_file_context:
                analysis_system = get_analysis_system_message(full_file_context, current_language)
                analysis_messages[0] = analysis_system
            
            response = openai_client.chat_completion(analysis_messages)
        else:
            #normal conversation flow
            response = openai_client.chat_completion(messages)
        
        if response:
            #update chat context in redis
            _update_chat_context(chat_id, user_id, messages)
            return response
        else:
            logger.error(f'[handle_text_message] OpenAI returned None response')
            return get_error_response("I encountered an error processing your message. Please try again.")
            
    except Exception as e:
        logger.error(f'[handle_text_message] Error: {str(e)}')
        logger.error(f'[handle_text_message] Traceback: {traceback.format_exc()}')
        logger.error(f'[handle_text_message] Text: {text}')
        logger.error(f'[handle_text_message] Chat ID: {chat_id}')
        logger.error(f'[handle_text_message] User ID: {user_id}')
        logger.error(f'[handle_text_message] File context: {file_context}')
        logger.error(f'[handle_text_message] Current language: {current_language}')
        return get_error_response("I encountered an error processing your message. Please try again.")

def detect_language_preference(text: str) -> Optional[str]:
    """
    Detect if user is requesting language preference change from their message text.
    This function analyzes the user's message to identify language preference requests
    and returns the appropriate language code. It supports both Chinese and English
    language preference detection using pattern matching.
    
    params:
    - text (str): The user's message text to analyze for language preferences
    
    returns:
    Returns "chinese", "english", or None if no language preference is detected
    """
    text_lower = text.lower()
    
    # Chinese language requests
    chinese_patterns = [
        "用中文", "中文回复", "请用中文", "用中文回答", "中文回答",
        "从现在起", "如果我用中文", "请用中文而不是英语",
        "用中文而不是英语回答", "用中文而不是英语"
    ]
    
    # English language requests  
    english_patterns = [
        "in english", "english please", "reply in english", "answer in english",
        "use english", "switch to english", "english response"
    ]
    
    for pattern in chinese_patterns:
        if pattern in text_lower:
            return "chinese"
    
    for pattern in english_patterns:
        if pattern in text_lower:
            return "english"
    
    return None

# ============================================================================
# FILE PROCESSING COORDINATORS
# ============================================================================

def _handle_local_file(file_name: str, chat_id: str, user_id: str, msg_id: str) -> Optional[str]:
    """
    Processes files that exist locally on the server filesystem. This function handles the complete workflow 
    for local file processing, including file reading, type detection, size validation, and routing to appropriate 
    processors based on file type (image vs regular files). It ensures proper error handling and logging for local 
    file operations. Called by handle_file_message() when a local file is detected, this function serves as the coordinator 
    for local file processing, delegating to _process_image_file() for images and _process_regular_file() for other file types. 
    It handles all the validation and setup logic before calling the specialized processors.

    params:
    - file_name (str): The path to the local file on the server filesystem
    - chat_id (str): Unique identifier for the chat session where the file was referenced
    - user_id (str): Unique identifier for the user who referenced the file
    - msg_id (str): Unique identifier for the message containing the file reference

    returns:
    Returns a string response describing the processing results, or None if processing fails
    """
    try:
        # Read the file
        with open(file_name, 'rb') as f:
            file_data = f.read()
            
        # Get file info
        file_size = len(file_data)
        file_type = FileType.from_extension(file_name)
        logger.info(f'[handle_file_message] File info - size: {file_size}, type: {file_type}')
        
        # Handle image files
        if file_type == FileType.IMAGE:
            return _process_image_file(file_data, file_name, chat_id, user_id, msg_id)
        
        # Check file size (20MB limit)
        if file_size > 20 * 1024 * 1024:
            logger.warning(f'[handle_file_message] File too large: {file_size} bytes')
            error_msg = get_error_response("File is too large. Maximum size is 20MB")
            save_error_message(msg_id, chat_id, user_id, error_msg, msg_id, msg_id)
            return error_msg
            
        # Check file type
        if file_type == FileType.UNKNOWN:
            logger.warning(f'[handle_file_message] Unsupported file type for file: {file_name}')
            error_msg = get_error_response("Unsupported file type. I can handle CSV, Excel, and PDF files")
            save_error_message(msg_id, chat_id, user_id, error_msg, msg_id, msg_id)
            return error_msg
            
        # Process non-image files
        return _process_regular_file(file_data, file_type, file_name, chat_id, user_id, msg_id)
                
    except Exception as e:
        logger.error(f'[handle_file_message] Error processing local file: {str(e)}')
        logger.error(f'[handle_file_message] Traceback: {traceback.format_exc()}')
        error_msg = get_error_response(f"Error processing local file: {str(e)}")
        save_error_message(msg_id, chat_id, user_id, error_msg, msg_id, msg_id)
        return error_msg

def _handle_lark_file(file_key: str, file_name: str, chat_id: str, user_id: str, msg_id: str) -> Optional[str]:
    """
    Processes files that were uploaded through the Lark platform and need to be downloaded before processing. This function 
    handles the complete workflow for Lark file processing, including file downloading, type detection, and routing to appropriate 
    processors based on file type. It manages the interaction with Lark's file API and ensures proper error handling for remote file 
    operations. Called by handle_file_message() when a Lark file is detected, this function serves as the coordinator for Lark file 
    processing, delegating to _process_lark_image_file() for images and _process_regular_file() for other file types. It handles the 
    file downloading and setup logic before calling the specialized processors.

    params:
    - file_key (str): The unique identifier for the file in Lark's system, used for downloading
    - file_name (str): The original filename of the uploaded file
    - chat_id (str): Unique identifier for the chat session where the file was uploaded
    - user_id (str): Unique identifier for the user who uploaded the file
    - msg_id (str): Unique identifier for the message containing the file upload

    returns:
    Returns a string response describing the processing results, or None if processing fails
    """
    try:
        logger.info(f'[handle_file_message] Getting file info for key: {file_key}')
        file_info, file_name = file_client.get_file_info(msg_id, file_key, file_name)
        file_data = file_info.content
        file_type = FileType.from_extension(file_name)
        
        # Handle image files
        if file_type == FileType.IMAGE:
            return _process_lark_image_file(file_data, file_key, file_name, chat_id, user_id, msg_id)
        
        # Process non-image files
        return _process_regular_file(file_data, file_type, file_name, chat_id, user_id, msg_id)
        
    except Exception as e:
        logger.error(f'[handle_file_message] Error processing Lark file: {str(e)}')
        logger.error(f'[handle_file_message] Traceback: {traceback.format_exc()}')
        error_msg = get_error_response(f"Error processing file: {str(e)}")
        save_error_message(msg_id, chat_id, user_id, error_msg, msg_id, msg_id)
        return error_msg

# ============================================================================
# FILE PROCESSORS
# ============================================================================

def _process_image_file(file_data: bytes, file_name: str, chat_id: str, user_id: str, msg_id: str) -> Optional[str]:
    """
    Processes image files using OpenAI's GPT-4 Vision API to provide detailed analysis and insights. This function handles the 
    complete image processing workflow for local files, including calling the vision API, formatting responses, and saving results 
    to chat history. It provides users with detailed descriptions and analysis of image content. Called by _handle_local_file() when 
    an image file is detected, this function is the specialized processor for image files, using the openai_client.process_image() 
    function to analyze image content. It works in parallel with _process_lark_image_file() which handles the same functionality for 
    Lark-uploaded images.

    params:
    - file_data (bytes): The raw binary data of the image file
    - file_name (str): The name of the image file being processed
    - chat_id (str): Unique identifier for the chat session where the image was uploaded
    - user_id (str): Unique identifier for the user who uploaded the image
    - msg_id (str): Unique identifier for the message containing the image

    returns:
    Returns a formatted string response containing the image analysis, or None if processing fails
    """
    logger.info(f'[handle_file_message] Starting image processing for local file: {file_name}')
    try:
        # Get current language preference
        current_language = redis_util.hget(f"user_preferences:{user_id}", "language")
        
        # Process image with GPT-4 Vision
        logger.info(f'[handle_file_message] Calling OpenAI Vision API for file: {file_name}')
        analysis = openai_client.process_image(file_data)
        logger.info(f'[handle_file_message] Successfully received analysis from OpenAI Vision API for file: {file_name}')
        
        # Create response
        response = get_image_analysis_response(analysis, current_language)
        
        # Save the analysis to chat history
        save_bot_response(msg_id, chat_id, user_id, response, msg_id, msg_id)
        return response

    except Exception as e:
        logger.error(f'[handle_file_message] Error processing local image file: {file_name}')
        logger.error(f'[handle_file_message] Error details: {str(e)}')
        logger.error(f'[handle_file_message] Traceback: {traceback.format_exc()}')
        error_msg = get_error_response(f"Error processing image: {str(e)}")
        save_error_message(msg_id, chat_id, user_id, error_msg, msg_id, msg_id)
        return error_msg

def _process_lark_image_file(file_data, file_key: str, file_name: str, chat_id: str, user_id: str, msg_id: str) -> Optional[str]:
    """
    Processes image files that were uploaded through Lark using OpenAI's GPT-4 Vision API. This function handles the complete image 
    processing workflow for Lark-uploaded files, including file content extraction, calling the vision API, formatting responses, and 
    saving results to chat history. It provides users with detailed descriptions and analysis of image content from Lark uploads. 
    Called by _handle_lark_file() when an image file is detected, this function is the specialized processor for Lark-uploaded image files, 
    using the openai_client.process_image() function to analyze image content. It works in parallel with _process_image_file() which handles 
    the same functionality for local image files.

    params:
    - file_data: The file data object from Lark, which may be bytes or require downloading
    - file_key (str): The unique identifier for the file in Lark's system, used for downloading if needed
    - file_name (str): The name of the image file being processed
    - chat_id (str): Unique identifier for the chat session where the image was uploaded
    - user_id (str): Unique identifier for the user who uploaded the image
    - msg_id (str): Unique identifier for the message containing the image

    returns:
    Returns a formatted string response containing the image analysis, or None if processing fails
    """
    logger.info(f'[handle_file_message] Starting image processing for Lark file: {file_name}')
    try:
        # Get current language preference
        current_language = redis_util.hget(f"user_preferences:{user_id}", "language")
        
        # Get image content
        logger.info(f'[handle_file_message] Getting image content for Lark file: {file_name}')
        logger.info(f'[handle_file_message] File data type: {type(file_data)}')
        logger.info(f'[handle_file_message] File data size: {len(file_data) if isinstance(file_data, bytes) else "not bytes"}')
        
        image_content = file_data if isinstance(file_data, bytes) else file_client.download_file(file_key)
        if not image_content:
            logger.error(f'[handle_file_message] Failed to get image content for Lark file: {file_name}')
            error_msg = get_error_response("Could not process image content")
            save_error_message(msg_id, chat_id, user_id, error_msg, msg_id, msg_id)
            return error_msg

        # Process image with GPT-4 Vision
        logger.info(f'[handle_file_message] Calling OpenAI Vision API for Lark file: {file_name}')
        analysis = openai_client.process_image(image_content)
        logger.info(f'[handle_file_message] Successfully received analysis from OpenAI Vision API for Lark file: {file_name}')
        logger.info(f'[handle_file_message] Analysis content: {analysis}')
        
        # Create response
        response = get_image_analysis_response(analysis, current_language)
        
        # Save the analysis to chat history
        save_bot_response(msg_id, chat_id, user_id, response, msg_id, msg_id)
        return response

    except Exception as e:
        logger.error(f'[handle_file_message] Error processing Lark image file: {file_name}')
        logger.error(f'[handle_file_message] Error details: {str(e)}')
        logger.error(f'[handle_file_message] Traceback: {traceback.format_exc()}')
        error_msg = get_error_response(f"Error processing image: {str(e)}")
        save_error_message(msg_id, chat_id, user_id, error_msg, msg_id, msg_id)
        return error_msg

def _process_regular_file(file_data: bytes, file_type: FileType, file_name: str, chat_id: str, user_id: str, msg_id: str) -> Optional[str]:
    """
    Processes non-image files (CSV, Excel, PDF) by extracting their content and storing the results for future analysis. This function handles 
    the complete workflow for regular file processing, including content extraction, data structure analysis, context storage in Redis, and response 
    generation. It prepares the file data for subsequent user queries and analysis. Called by both _handle_local_file() and _handle_lark_file() for 
    non-image files, this function is the specialized processor for regular files, using the process_file_content() function to extract and analyze file data. 
    It integrates with Redis for context persistence and provides intelligent responses based on file content analysis.
    
    params:
    - file_data (bytes): The raw binary data of the file to be processed
    - file_type (FileType): The enumerated type of the file (CSV, EXCEL, PDF, etc.)
    - file_name (str): The name of the file being processed
    - chat_id (str): Unique identifier for the chat session where the file was uploaded
    - user_id (str): Unique identifier for the user who uploaded the file
    - msg_id (str): Unique identifier for the message containing the file
    
    returns:
    Returns a string response describing the file processing results, or None if processing fails
    """
    try:
        #get current language preference
        current_language = redis_util.hget(f"user_preferences:{user_id}", "language")
        
        #process file content
        result = process_file_content(file_data, file_type, file_name)
        
        if result:
            #store file context in redis
            file_context = {
                'file_name': file_name,
                'file_type': file_type.name.lower(),
                'processed_data': result,
                'timestamp': time.time()
            }
            
            #check if this is a large dataset (>50 rows)
            is_large_dataset = False
            if result.get('type') == 'tabular':
                rows = result.get('rows', 0)
                is_large_dataset = rows > 50
                
                if is_large_dataset:
                    #for large datasets, store full data separately and only summary in conversation context
                    file_context['full_data_available'] = True
                    file_context['is_large_dataset'] = True
                    
                    #store full data for analysis
                    redis_util.setex(f'full_file_context:{user_id}', 3600, json.dumps(file_context))
                    
                    #create summary for conversation context
                    summary_context = {
                        'file_name': file_name,
                        'file_type': file_type.name.lower(),
                        'processed_data': {
                            'type': 'tabular',
                            'rows': rows,
                            'columns': result.get('columns', []),
                            'data': result.get('data', [])[:5]  #only first 5 rows
                        },
                        'timestamp': time.time(),
                        'is_summary': True
                    }
                    
                    #store summary in conversation context
                    redis_util.setex(f'file_context:{user_id}', 3600, json.dumps(summary_context))
                    
                    logger.info(f'[process_regular_file] Large dataset detected ({rows} rows), stored summary in conversation context')
                else:
                    #for small datasets, store full data in conversation context
                    redis_util.setex(f'file_context:{user_id}', 3600, json.dumps(file_context))
            else:
                #for non-tabular files, store normally
                redis_util.setex(f'file_context:{user_id}', 3600, json.dumps(file_context))
            
            #get response with language preference
            response = get_file_processing_response(file_type, file_name, result, current_language)
            
            #update chat context with the file processing response
            chat_context = _get_chat_context(chat_id, user_id)
            system_message = get_system_message(file_context, current_language)
            
            messages = [system_message]
            if chat_context:
                messages.extend(chat_context)
            messages.append({"role": "assistant", "content": response})
            
            _update_chat_context(chat_id, user_id, messages)
            
            return response
        else:
            return get_error_response("Could not process file content")
            
    except Exception as e:
        logger.error(f'[process_regular_file] Error: {str(e)}')
        return get_error_response("Could not process file content")

# ============================================================================
# CONTEXT MANAGEMENT
# ============================================================================

# Context storage configuration
USE_HASH_STORAGE = False  # Disabled - using string-based storage

def get_full_file_context_from_redis(user_id: str) -> Optional[dict]:
    """
    Get full file context from Redis for large dataset analysis.
    This function retrieves the complete file context that was stored separately
    for large datasets (>50 rows) to avoid overwhelming the conversation context.
    It's used when the user asks questions about large datasets that require
    access to the full dataset rather than just a summary.
    
    params:
    - user_id (str): Unique identifier for the user whose file context to retrieve
    
    returns:
    Returns the complete file context dictionary or None if not found
    """
    try:
        context_data = redis_util.get(f'full_file_context:{user_id}')
        if context_data:
            #redis_util.get() already deserializes JSON, so context_data should be a dict
            #but handle the case where it might be a string (backward compatibility)
            if isinstance(context_data, str):
                try:
                    return json.loads(context_data)
                except json.JSONDecodeError:
                    logger.warning(f'[get_full_file_context_from_redis] Invalid JSON in full_file_context for user {user_id}')
                    return None
            elif isinstance(context_data, dict):
                return context_data
            else:
                logger.warning(f'[get_full_file_context_from_redis] Unexpected type for full_file_context: {type(context_data)}')
                return None
        return None
    except Exception as e:
        logger.error(f'[get_full_file_context_from_redis] Error: {str(e)}')
        return None

def _get_chat_context(chat_id: str, user_id: str) -> List[Dict]:
    """
    Retrieves conversation context from Redis for maintaining coherent conversations. This function implements 
    a hierarchical context retrieval system, first trying to get user-specific context and falling back to chat-wide 
    context if needed. It ensures that conversations maintain continuity and context across multiple interactions. 
    Called by handle_text_message() to retrieve conversation history for context-aware responses, this function is part 
    of the context management system that works alongside _update_chat_context() to maintain the conversation state. It supports 
    the AI's ability to remember previous interactions and provide coherent responses.

    params:
    - chat_id (str): Unique identifier for the chat session
    - user_id (str): Unique identifier for the specific user within the chat

    returns:
    Returns a list of message dictionaries representing the conversation context, or an empty list if no context is found
    """
    try:
        # Try user-specific context first
        context_key = f"chat_context:{chat_id}:{user_id}"
        context = redis_util.get(context_key)
        
        if not context:
            # Fall back to chat-wide context
            chat_context_key = f"chat_context:{chat_id}"
            context = redis_util.get(chat_context_key)
            
        parsed_context = context if context else []
        
        return parsed_context if isinstance(parsed_context, list) else []
        
    except Exception as e:
        logger.error(f"Error getting chat context: {str(e)}")
        return []

def _update_chat_context(chat_id: str, user_id: str, messages: List[Dict]):
    """
    Updates conversation context in Redis to maintain conversation continuity. This function implements a dual-context 
    storage system, saving context both at the user-specific level and chat-wide level. It ensures that conversations 
    can be maintained across multiple users in the same chat while also preserving individual user context. Called by 
    handle_text_message() after generating a response to update the conversation context, this function works in conjunction 
    with _get_chat_context() to maintain the conversation state. It's part of the context management system that enables the 
    AI to remember and reference previous interactions.

    params:
    - chat_id (str): Unique identifier for the chat session
    - user_id (str): Unique identifier for the specific user within the chat
    - messages (List[Dict]): The complete conversation history including system message, context, and current interaction

    returns:
    No return value - updates Redis with the conversation context
    """
    try:
        # Save to both user-specific and chat-wide contexts
        context_key = f"chat_context:{chat_id}:{user_id}"
        chat_context_key = f"chat_context:{chat_id}"
        
        # Store the context with TTL (1 hour)
        result1 = redis_util.setex(context_key, 3600, messages)
        result2 = redis_util.setex(chat_context_key, 3600, messages)
        
        if not result1 or not result2:
            logger.error(f"[CONTEXT] Failed to store context: result1={result1}, result2={result2}")
        
    except Exception as e:
        logger.error(f"Error updating chat context: {str(e)}")

# ============================================================================
# IMAGE DETECTION HELPERS
# ============================================================================

def _contains_image_content(content) -> bool:
    """
    Detects if a message content contains embedded image data.
    This function checks for various ways that images can be embedded in messages,
    including copy-pasted images that come as text messages with image content.
    
    params:
    - content: The message content object from Lark
    
    returns:
    Returns True if the content contains image data, False otherwise
    """
    try:
        if not content:
            return False
            
        #if content is a string, try to parse it as json
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except:
                return False
        
        #check for direct image content
        if isinstance(content, dict):
            #check for image_key in content (actual image data)
            if content.get('image_key'):
                return True
                
            #check for content array with images (post format)
            content_array = content.get('content', [])
            if isinstance(content_array, list):
                for content_block in content_array:
                    if isinstance(content_block, list):
                        for item in content_block:
                            if isinstance(item, dict) and item.get('tag') == 'img':
                                return True
                                
            #check for file_info with image
            file_info = content.get('file_info', {})
            if file_info and file_info.get('file_key'):
                return True
                
            #check for embedded image data - only if type is explicitly 'image'
            #don't check for 'image' in text as that's too broad
            if content.get('type') == 'image':
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking for image content: {str(e)}")
        return False

def handle_copy_pasted_image(body, chat_id: str, user_id: str, msg_id: str) -> Optional[str]:
    """
    Handles copy-pasted images that come as text messages with embedded image content.
    This function extracts image data from text messages that contain embedded images,
    which happens when users copy and paste images directly into the chat.
    
    params:
    - body: The message body object containing the embedded image
    - chat_id (str): Unique identifier for the chat session
    - user_id (str): Unique identifier for the user who pasted the image
    - msg_id (str): Unique identifier for the message containing the image
    
    returns:
    Returns a string response describing the image analysis, or None if processing fails
    """
    try:
        logger.info(f'[handle_copy_pasted_image] Processing copy-pasted image from text message')
        
        # Parse message content
        content = body.content
        logger.info(f'[handle_copy_pasted_image] Received message content: {content}')
        
        if not isinstance(content, dict):
            try:
                content = json.loads(content)
                logger.info(f'[handle_copy_pasted_image] Parsed JSON content: {content}')
            except:
                logger.error(f'[handle_copy_pasted_image] Invalid content type and not JSON: {type(content)}')
                error_msg = get_error_response("Invalid image message format")
                save_error_message(msg_id, chat_id, user_id, error_msg, msg_id, msg_id)
                return error_msg
        
        # Extract image information
        image_key = None
        file_name = None
        
        # Try different ways to extract image data
        if content.get('image_key'):
            # Direct image key
            image_key = content.get('image_key')
            file_name = content.get('file_name', 'pasted_image.jpg')
            logger.info(f'[handle_copy_pasted_image] Found direct image_key: {image_key}')
            
        elif content.get('file_info', {}).get('file_key'):
            # File info structure
            file_info = content.get('file_info', {})
            image_key = file_info.get('file_key')
            file_name = file_info.get('file_name', 'pasted_image.jpg')
            logger.info(f'[handle_copy_pasted_image] Found image in file_info: {image_key}')
            
        elif content.get('content'):
            # Content array structure (like post messages)
            content_array = content.get('content', [])
            if isinstance(content_array, list):
                for content_block in content_array:
                    if isinstance(content_block, list):
                        for item in content_block:
                            if isinstance(item, dict) and item.get('tag') == 'img':
                                image_key = item.get('image_key')
                                file_name = f"pasted_image_{int(time.time())}.jpg"
                                logger.info(f'[handle_copy_pasted_image] Found image in content array: {image_key}')
                                break
                        if image_key:
                            break
        
        # Validate that we found an image
        if not image_key:
            logger.error(f'[handle_copy_pasted_image] No image_key found in copy-pasted content')
            error_msg = get_error_response("No image found in the pasted content")
            save_error_message(msg_id, chat_id, user_id, error_msg, msg_id, msg_id)
            return error_msg
        
        # Process the image using the existing Lark file processing infrastructure
        logger.info(f'[handle_copy_pasted_image] Processing copy-pasted image with key: {image_key}')
        return _handle_lark_file(image_key, file_name, chat_id, user_id, msg_id)
            
    except Exception as e:
        logger.error(f'[handle_copy_pasted_image] Unexpected error: {str(e)}')
        logger.error(f'[handle_copy_pasted_image] Traceback: {traceback.format_exc()}')
        error_msg = get_error_response(f"Unexpected error processing copy-pasted image: {str(e)}")
        save_error_message(msg_id, chat_id, user_id, error_msg, msg_id, msg_id)
        return error_msg

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def process_file_content(file_data: bytes, file_type: FileType, file_name: str) -> Optional[Dict]:
    """
    Low-level utility function that extracts and processes content from various file types (CSV, Excel, PDF). This function 
    handles the actual file parsing and content extraction, creating temporary files and using appropriate libraries to read 
    and analyze file content. It's the core utility that enables the bot to understand and work with different file formats. 
    Called by _process_regular_file() to perform the actual file content extraction, this function is a utility that focuses 
    solely on file parsing and content extraction, leaving higher-level concerns like context storage and response formatting 
    to the calling functions. It's the foundation that enables file analysis capabilities.

    params:
    - file_data (bytes): The raw binary data of the file to be processed
    - file_type (FileType): The enumerated type of the file (CSV, EXCEL, PDF, etc.)
    - file_name (str): The name of the file being processed (used for temporary file creation)

    returns:
    Returns a dictionary containing the processed file data and metadata, or None if processing fails
    """
    try:
        #create a temporary file to store the content
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_type.name.lower()}') as temp_file:
            temp_file.write(file_data)
            temp_path = temp_file.name
            
        try:
            #process different excel file types first, then get result
            if file_type == FileType.EXCEL:
                ext = file_name.split('.')[-1].lower()
                if ext in ['xlsx', 'xls']:
                    file_type_str = ext
                else:
                    logger.error(f"[process_file_content] File marked as Excel but has extension '{ext}': {file_name}")
                    file_type_str = 'xlsx'
            else:
                file_type_str = file_type.name.lower()
            
            result = openai_client.process_file(temp_path, file_type_str)
            
            #clean up the temporary file
            os.unlink(temp_path)
            
            if result.get('error'):
                logger.error(f'Error processing file content: {result["error"]}')
                return None
                
            return result
            
        finally:
            #ensure temp file is cleaned up even if processing fails
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
    except Exception as e:
        logger.error(f'Error in process_file_content: {str(e)}')
        return None

def handle_detailed_analysis_request(text: str, user_id: str, current_language: str, context_type: str) -> str:
    """
    Handles detailed analysis requests by checking if there's recent file or image context

    params:
    - text (str): The user's message text
    - user_id (str): Unique identifier for the user
    - current_language (str): Current language preference of the user
    - context_type (str): Type of context ('image' or 'file')

    returns:
    Returns a string response containing the detailed analysis or guidance
    """
    try:
        if context_type == 'file':
            # Check for file context
            file_context = redis_util.get(f'file_context:{user_id}')
            if file_context:
                try:
                    file_context = json.loads(file_context) if isinstance(file_context, str) else file_context
                    if file_context and isinstance(file_context, dict):
                        file_name = file_context.get('file_name', 'Unknown')
                        return f"I'll provide a detailed analysis of {file_name}. Please ask specific questions about what you'd like to know."
                except:
                    pass
            return "I'll provide a detailed analysis of the file. Please upload the file first, then ask for a detailed description."
        
        elif context_type == 'image':
            # For images, we don't currently store image context, so provide guidance
            return "I'll provide a detailed analysis of the image. Please upload the image first, then ask for a detailed description."
        
        else:
            return "I'm not sure what you'd like me to analyze. Please upload a file or image first."
        
    except Exception as e:
        logger.error(f'[handle_detailed_analysis_request] Error: {str(e)}')
        return "I encountered an error processing your request. Please try again."


