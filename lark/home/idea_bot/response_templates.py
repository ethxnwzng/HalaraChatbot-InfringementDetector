from home.idea_bot.version import get_version_info, get_capabilities, CAPABILITIES
import json
import logging

logger = logging.getLogger(__name__)

def get_version_response():
    """Get the version and capabilities response"""
    capabilities = CAPABILITIES['file_handling']
    business_capabilities = CAPABILITIES['business_support']
    return f"""I am {get_version_info()}.
            
My capabilities include:
📄 File handling up to {capabilities['max_size']}
📊 Supported formats: {', '.join(capabilities['supported_types'])}
🖼️ Image analysis with GPT-4 Vision
💾 {CAPABILITIES['chat']['features'][1]}
🔍 {capabilities['features'][1]}
💬 {CAPABILITIES['chat']['features'][0]}
🧠 {CAPABILITIES['chat']['features'][3]}
🔄 {CAPABILITIES['chat']['features'][2]}
🌐 Multilingual support (Chinese/English)
🏢 Professional workplace communication

Business Support Features:
📊 Product data analysis and insights
💰 Sales performance and trend analysis
👥 Customer behavior and preference analysis
📦 Inventory management and optimization
📢 Marketing content and campaign analysis
✅ Quality control and product review
🎯 Competitive analysis and market research
🛒 E-commerce optimization support
👗 Fashion industry expertise

I'm specifically designed to support Halara employees in their daily work tasks!"""

def get_intelligent_data_sample(data, max_rows=50):
    """
    Get an intelligent sample of data that preserves statistical properties.
    For large datasets, this samples from the beginning, middle, and end to maintain data distribution.
    
    params:
    - data (list): The full dataset
    - max_rows (int): Maximum number of rows to include
    
    returns:
    Returns a sampled dataset that preserves data distribution
    """
    if len(data) <= max_rows:
        return data
    
    # For large datasets, sample strategically
    sample_size = max_rows // 3  # Divide into thirds
    
    # Get beginning, middle, and end samples
    beginning = data[:sample_size]
    middle_start = len(data) // 2 - sample_size // 2
    middle = data[middle_start:middle_start + sample_size]
    end = data[-sample_size:]
    
    # Combine samples
    sampled_data = beginning + middle + end
    
    # Ensure we don't exceed max_rows
    if len(sampled_data) > max_rows:
        sampled_data = sampled_data[:max_rows]
    
    return sampled_data

def get_system_message(file_context=None, language_preference=None):
    """
    Get the system message with optional file context and language preference.
    
    params:
    - file_context (dict, optional): Context information about uploaded files
    - language_preference (str, optional): User's preferred language ("chinese" or "english")
    
    returns:
    Returns a dictionary with role "system" and formatted content for OpenAI API
    """
    logger.info(f'[get_system_message] Called with file_context type: {type(file_context)}')
    logger.info(f'[get_system_message] Language preference: {language_preference}')
    
    base_message = "You are idea_bot, an AI assistant for Halara employees. Be helpful, professional, and concise."
    
    # Add language preference instruction
    if language_preference == "chinese":
        base_message += " Respond in Chinese (简体中文)."
    elif language_preference == "english":
        base_message += " Respond in English."

    if file_context:
        logger.info(f'[get_system_message] Processing file_context: {type(file_context)}')
        #ensure file_context is a dictionary
        if isinstance(file_context, str):
            try:
                file_context = json.loads(file_context)
                logger.info(f'[get_system_message] Parsed file_context from string: {type(file_context)}')
            except json.JSONDecodeError:
                logger.warning(f'[get_system_message] Invalid JSON in file_context')
                file_context = None
        
        if file_context and isinstance(file_context, dict):
            logger.info(f'[get_system_message] File context is valid dict, processing...')
            file_name = file_context.get('file_name', 'Unknown')
            file_type = file_context.get('file_type', 'Unknown')
            processed_data = file_context.get('processed_data', {})
            logger.info(f'[get_system_message] File: {file_name}, Type: {file_type}')
            logger.info(f'[get_system_message] Processed data type: {type(processed_data)}')
            
            #ensure processed_data is a dictionary
            if isinstance(processed_data, str):
                try:
                    processed_data = json.loads(processed_data)
                    logger.info(f'[get_system_message] Parsed processed_data from string: {type(processed_data)}')
                except json.JSONDecodeError:
                    logger.warning(f'[get_system_message] Invalid JSON in processed_data')
                    processed_data = {}
            
            # Format the file data properly for the AI
            if processed_data and isinstance(processed_data, dict) and processed_data.get('type') == 'tabular':
                logger.info(f'[get_system_message] Processing tabular data')
                rows = processed_data.get('rows', 0)
                columns = processed_data.get('columns', [])
                data = processed_data.get('data', [])
                logger.info(f'[get_system_message] Tabular data: {rows} rows, {len(columns)} columns, {len(data)} data entries')
                
                # Create a data summary with actual data for analysis
                data_summary = f"""

File: {file_name} ({file_type})
Rows: {rows}, Columns: {len(columns)}
Columns: {', '.join(columns)}

Data:
"""
                # Include data for analysis (this is needed for real insights)
                logger.info(f'[get_system_message] Adding {len(data)} data rows to context')
                
                # Smart sampling for large datasets to prevent token issues
                max_rows_to_include = 50  # Limit to prevent token overflow
                if len(data) > max_rows_to_include:
                    # Use intelligent sampling to preserve data distribution
                    data_to_include = get_intelligent_data_sample(data, max_rows_to_include)
                    logger.info(f'[get_system_message] Large dataset detected ({len(data)} rows), intelligently sampled {len(data_to_include)} rows for analysis')
                else:
                    data_to_include = data
                
                for i, row in enumerate(data_to_include):
                    # Format row as a readable string with column names
                    if isinstance(row, dict):
                        row_parts = []
                        for col in columns:
                            value = row.get(col, '')
                            row_parts.append(f"{col}: {value}")
                        row_str = f"{i+1}: {' | '.join(row_parts)}\n"
                    else:
                        row_str = f"{i+1}: {row}\n"
                    
                    data_summary += row_str
                    # Log first few rows for debugging
                    if i < 3:
                        logger.info(f'[get_system_message] Row {i+1}: {row}')
                
                # Add note if data was sampled
                if len(data) > max_rows_to_include:
                    data_summary += f"\nNote: Showing sample of {len(data_to_include)} rows from {len(data)} total rows for analysis.\n"
                
                logger.info(f'[get_system_message] Final data_summary length: {len(data_summary)} characters')
                base_message += data_summary
                
            elif processed_data and isinstance(processed_data, dict) and processed_data.get('type') == 'text':
                text_content = processed_data.get('data', '')
                # Truncate long text content
                if len(text_content) > 1000:
                    text_content = text_content[:1000] + "... (truncated)"
                
                base_message += f"""

File: {file_name} ({file_type})
Content: {text_content}"""
            
            else:
                # Fallback for other file types
                base_message += f"""

File: {file_name} ({file_type})
Data available for analysis"""

    return {"role": "system", "content": base_message}

def get_analysis_system_message(file_context, language_preference=None):
    """
    Get system message specifically for large dataset analysis.
    
    params:
    - file_context (dict): Complete file context with full dataset information
    - language_preference (str, optional): User's preferred language ("chinese" or "english")
    
    returns:
    Returns a dictionary with role "system" and analysis-focused content for OpenAI API
    """
    base_message = "You are idea_bot, a data analyst for Halara. Provide clear, actionable insights from the data."
    
    # Add language preference instruction
    if language_preference == "chinese":
        base_message += " Respond in Chinese (简体中文)."
    elif language_preference == "english":
        base_message += " Respond in English."

    if file_context:
        #ensure file_context is a dictionary
        if isinstance(file_context, str):
            try:
                file_context = json.loads(file_context)
            except json.JSONDecodeError:
                logger.warning(f'[get_analysis_system_message] Invalid JSON in file_context')
                file_context = None
        
        if file_context and isinstance(file_context, dict):
            file_name = file_context.get('file_name', 'Unknown')
            file_type = file_context.get('file_type', 'Unknown')
            processed_data = file_context.get('processed_data', {})
            
            #ensure processed_data is a dictionary
            if isinstance(processed_data, str):
                try:
                    processed_data = json.loads(processed_data)
                except json.JSONDecodeError:
                    logger.warning(f'[get_analysis_system_message] Invalid JSON in processed_data')
                    processed_data = {}
            
            if processed_data and isinstance(processed_data, dict) and processed_data.get('type') == 'tabular':
                rows = processed_data.get('rows', 0)
                columns = processed_data.get('columns', [])
                data = processed_data.get('data', [])
                
                # Include data for analysis
                data_summary = f"""

File: {file_name} ({file_type})
Rows: {rows}, Columns: {len(columns)}
Columns: {', '.join(columns)}

Data:
"""
                # Include all data for analysis
                for i, row in enumerate(data):
                    # Format row as a readable string with column names
                    if isinstance(row, dict):
                        row_parts = []
                        for col in columns:
                            value = row.get(col, '')
                            row_parts.append(f"{col}: {value}")
                        row_str = f"{i+1}: {' | '.join(row_parts)}\n"
                    else:
                        row_str = f"{i+1}: {row}\n"
                    
                    data_summary += row_str
                
                base_message += data_summary

    return {"role": "system", "content": base_message}

def get_file_processing_response(file_type, file_name, result, language_preference=None):
    """Get response for file processing results with language support"""
    if language_preference == "chinese":
        return f"我已经分析了您的文件：{file_name}，可以回答任何相关问题。"
    else:
        return f"I have analyzed your file: {file_name} and am ready to answer any questions regarding it."

def get_error_response(error_msg, include_version=True):
    """Get standardized error response"""
    if include_version:
        return f"{error_msg} ({get_version_info()})"
    return error_msg

def get_image_analysis_response(analysis, language_preference=None):
    """Get response for image analysis with language support"""
    if language_preference == "chinese":
        return f"我已经分析了这张图片（{get_version_info()}），可以回答任何相关问题。"
    else:
        return f"I've analyzed the image ({get_version_info()}) and am ready to answer any questions about it." 