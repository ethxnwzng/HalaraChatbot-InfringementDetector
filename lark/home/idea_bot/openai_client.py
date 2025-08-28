import os
from typing import List, Dict, Optional, Any
from openai import OpenAI
from datetime import datetime
import tiktoken
import json
from util.log_util import logger
from home.gpt import meta as gpt_meta
import traceback
import base64

CHAT_CONTEXT_TTL = 3600  # 1 hour cache TTL

def get_openai_client():
    """
    Initialize OpenAI client with better error handling. This function creates and configures an OpenAI 
    client instance using the API key from the gpt_meta configuration. It provides centralized error handling 
    for client initialization and ensures the API key is properly set before creating the client. This is the 
    primary function for obtaining a configured OpenAI client instance that can be used throughout the application 
    for API calls.

    returns:
    Returns an initialized OpenAI client instance, or None if initialization fails
    """
    try:
        api_key = gpt_meta.OPEN_AI_KEY_AIGC
        if not api_key:
            logger.error("OpenAI API key is not set")
            return None
        return OpenAI(api_key=api_key)
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {str(e)}")
        return None

# Initialize OpenAI client
client = get_openai_client()

def num_tokens_from_messages(messages: List[Dict], model: str = "gpt-3.5-turbo") -> int:
    """
    Return the number of tokens used by a list of messages. This function calculates the token count for 
    a conversation by analyzing each message's content and structure according to OpenAI's tokenization rules. 
    It accounts for message formatting overhead, role indicators, and content encoding to provide accurate token 
    estimates. This is essential for managing conversation length and avoiding token limits when working with OpenAI's 
    API. The function uses tiktoken library for accurate token counting based on the specified model.

    params:
    - messages (List[Dict]): List of message dictionaries containing role and content
    - model (str, optional): The OpenAI model to use for tokenization, defaults to "gpt-3.5-turbo"

    returns:
    Returns the total number of tokens used by the message list, or 0 if an error occurs
    """
    #no need to store every image or file (keep file key or token and fetch if needed)
    #fetch file from file token only when it is needed from the user
    try:
        encoding = tiktoken.encoding_for_model(model)
        num_tokens = 0
        for message in messages:
            num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
            for key, value in message.items():
                num_tokens += len(encoding.encode(str(value)))
                if key == "name":  # if there's a name, the role is omitted
                    num_tokens += -1  # role is always required and always 1 token
        num_tokens += 2  # every reply is primed with <im_start>assistant
        return num_tokens
    except Exception as e:
        logger.error(f"Error counting tokens: {str(e)}")
        return 0

def summarize_conversation(messages: List[Dict], model: str = "gpt-3.5-turbo") -> Dict[str, Any]:
    """
    Summarize a conversation to reduce token count while preserving context. This function creates a concise 
    summary of recent conversation history to manage token limits while maintaining important context. It preserves 
    the original system message and uses OpenAI to generate a summary of the last 10 messages, focusing on key information, 
    decisions, and file analysis context. The summarized context includes the original system message, the generated summary, 
    and a continuation message to maintain conversation flow. This is essential for long conversations that might exceed token limits.

    params:
    - messages (List[Dict]): The complete conversation history to be summarized
    - model (str, optional): The OpenAI model to use for summarization, defaults to "gpt-3.5-turbo"

    returns:
    Returns a list of message dictionaries containing the summarized conversation context, or falls back to the last 5 messages if summarization fails
    """
    try:
        # Keep the system message if it exists
        system_msg = next((msg for msg in messages if msg['role'] == 'system'), None)
        
        summary_prompt = {
            "role": "system",
            "content": """Please provide a concise summary of this conversation that preserves:
1. The current context (especially file analysis context if present)
2. Key information exchanged
3. Important decisions or conclusions
4. Any relevant file data being discussed

Format the summary to clearly distinguish between context and conversation."""
        }
        
        # Use last 10 messages for summary
        recent_messages = messages[-10:]
        
        response = client.chat.completions.create(
            model=model,
            messages=[summary_prompt] + recent_messages,
            temperature=0.7,
            max_tokens=500
        )
        
        summary = response.choices[0].message.content
        
        # Create new summarized context
        summarized_context = []
        if system_msg:
            summarized_context.append(system_msg)  # Preserve original system message
            
        summarized_context.extend([
            {"role": "system", "content": f"Previous conversation summary: {summary}"},
            {"role": "assistant", "content": "I'll continue helping you with your questions, taking into account our previous discussion."}
        ])
        
        return summarized_context
        
    except Exception as e:
        logger.error(f"Error summarizing conversation: {str(e)}")
        return messages[-5:]  # Fall back to just keeping last 5 messages

def process_file(file_path: str, file_type: str, query: str = None) -> Dict[str, Any]:
    """
    Process different types of files using appropriate methods. This function handles the extraction and 
    analysis of various file formats including CSV, Excel, and PDF files. It uses appropriate libraries (pandas 
    for tabular data, PyPDF2 for PDFs) to read and parse file content, returning structured data that can be used 
    for further analysis. For tabular files, it returns column information, row count, and data preview. For PDF 
    files, it extracts text content. This function serves as the foundation for file analysis capabilities in the bot.

    params:
    - file_path (str): The path to the file to be processed
    - file_type (str): The type of file (csv, xlsx, xls, pdf)
    - query (str, optional): Optional query parameter for future use

    returns:
    Returns a dictionary containing processed file data and metadata, or an error dictionary if processing fails
    """
    try:
        if file_type.lower() in ['csv', 'xlsx', 'xls']:
            import pandas as pd
            df = pd.read_csv(file_path) if file_type.lower() == 'csv' else pd.read_excel(file_path)
            return {
                'type': 'tabular',
                'data': df.to_dict('records'),
                'columns': list(df.columns),
                'rows': len(df)
            }
        elif file_type.lower() == 'pdf':
            from PyPDF2 import PdfReader
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return {
                'type': 'text',
                'data': text
            }
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
            
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        return {'error': str(e)}

def chat_completion(messages: List[Dict[str, str]]) -> Optional[str]:
    """
    Get a chat completion from OpenAI with enhanced file analysis capabilities. This function sends 
    a conversation to OpenAI's GPT-4 model and retrieves a response. It uses optimized parameters for 
    analysis tasks including temperature, max tokens, and other completion settings. The function provides 
    comprehensive error handling and logging for API interactions, ensuring reliable communication with OpenAI's 
    services. It's the primary interface for getting AI-generated responses to user queries and file analysis requests.

    params:
    - messages (List[Dict[str, str]]): List of message dictionaries containing the conversation history

    returns:
    Returns the AI-generated response as a string, or None if an error occurs
    """
    if not client:
        logger.error("[chat_completion] OpenAI client not initialized")
        return None
        
    try:
        # Calculate message tokens to determine appropriate max_tokens
        message_tokens = num_tokens_from_messages(messages, "gpt-4")
        max_completion_tokens = max(100, 8192 - message_tokens - 100)  # Leave 100 tokens buffer
        
        completion = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            max_tokens=max_completion_tokens,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        
        return completion.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Error in chat_completion: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def process_excel_query(df_info: Dict, query: str) -> str:
    """
    Process a query about Excel/CSV data using OpenAI. This function creates a specialized system 
    message that includes dataset information (rows, columns, and preview data) and sends it along 
    with the user's query to OpenAI for analysis. It provides the AI with context about the data structure 
    and sample content, enabling more accurate and relevant responses to data-related questions. The
    function uses GPT-4 for enhanced analytical capabilities and returns a clear, concise answer to the 
    user's query about the dataset.

    params:
    - df_info (Dict): Dictionary containing dataset information including rows, columns, and preview data
    - query (str): The user's question about the dataset

    returns:
    Returns a string containing the AI-generated analysis or answer to the query, or an error message if processing fails
    """
    try:
        # Create a system message that explains the data
        system_msg = f"""You are analyzing a dataset with {df_info['rows']} rows and the following columns:
{', '.join(df_info['columns'])}

Here's a preview of the first few rows:
{json.dumps(df_info['preview'], indent=2)}

Please provide a clear and concise answer to the user's query about this data."""

        # Create the messages array
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": query}
        ]

        # Get completion from OpenAI
        completion = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )

        return completion.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"Error processing Excel query: {str(e)}")
        return f"I encountered an error analyzing the data: {str(e)}"

def test_vision_model_access():
    """
    Test if we have access to the vision model. This function verifies that the OpenAI API key 
    has the necessary permissions to access GPT-4 Vision models. It attempts to list available 
    models and specifically retrieve information about the vision model to confirm access. This is 
    useful for debugging vision-related issues and ensuring the bot can process images. The function 
    provides detailed logging of available models and any access errors encountered during the test.

    params:
    None

    returns:
    Returns True if vision model access is confirmed, False otherwise
    """
    try:
        # Try to list available models
        models = client.models.list()
        logger.info(f'[test_vision_model_access] Available models: {[model.id for model in models.data]}')
        
        # Try to get specific model info
        try:
            model_info = client.models.retrieve("gpt-4-vision-preview")
            logger.info(f'[test_vision_model_access] Vision model info: {model_info}')
            return True
        except Exception as e:
            logger.error(f'[test_vision_model_access] Error accessing vision model: {str(e)}')
            return False
            
    except Exception as e:
        logger.error(f'[test_vision_model_access] Error listing models: {str(e)}')
        return False

def process_image(image_content: bytes, prompt: str = "Analyze this image and provide insights:") -> str:
    """
    Process an image using GPT-4 Vision. This function handles the complete image analysis workflow using OpenAI's GPT-4 Vision API. It validates image size limits, converts the image to base64 format for API transmission, and creates the appropriate message structure for vision analysis. The function uses the gpt-4.1 model for enhanced visual understanding and provides comprehensive logging throughout the process. It returns detailed analysis and insights about the image content, enabling the bot to understand and describe visual information.

    params:
    - image_content (bytes): The raw binary data of the image to be analyzed
    - prompt (str, optional): Custom prompt for image analysis, defaults to a general analysis prompt

    returns:
    Returns a string containing the AI-generated analysis of the image, or an error message if processing fails
    """
    try:
        logger.info(f'[process_image] Starting image processing with prompt: {prompt}')
        logger.info(f'[process_image] Image content size: {len(image_content)} bytes')
        logger.info(f'[process_image] First few bytes of image: {image_content[:100]}') 
        #check image size 
        if len(image_content) > 20 * 1024 * 1024:
            logger.error(f'[process_image] Image too large: {len(image_content)} bytes')
            return "Sorry, the image is too large. Maximum size is 20MB."
        
        #convert image to base64
        image_base64 = base64.b64encode(image_content).decode('utf-8')
        logger.info(f'[process_image] Successfully encoded image to base64')
        logger.info(f'[process_image] First 100 chars of base64: {image_base64[:100]}') 
        
        #create messages array with image
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }
        ]
        logger.info(f'[process_image] Created messages array with image')
        logger.info(f'[process_image] Message structure: {json.dumps(messages, indent=2)}')  # Log full message structure

        #get completion from OpenAI
        logger.info(f'[process_image] Attempting to call OpenAI API with model: gpt-4.1')
        completion = client.chat.completions.create(
            model="gpt-4.1",
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )
        logger.info(f'[process_image] Successfully received response from OpenAI API')
        logger.info(f'[process_image] Raw API response: {completion.choices[0].message.content}')  # Log raw response

        return completion.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f'[process_image] Error processing image: {str(e)}')
        logger.error(f'[process_image] Traceback: {traceback.format_exc()}')
        return "Sorry, I couldn't process the image at this time." 