import requests
import traceback
import json
from util.log_util import logger
from home.idea_bot import client, meta
from typing import Optional

def get_file_info(msg_id: str, file_key: str, file_name: str):
    """Get file information from Lark"""
    try:
        logger.info(f'[get_file_info] Starting to get file info for key: {file_key}')
        # Try the files endpoint first (more reliable)
        response = client.get_file_info_from_msg(msg_id, file_key)
        return response, file_name
        # Check if response is JSON or raw file content
        content_type = response.headers.get('Content-Type', '')
        if 'json' in content_type.lower():
            try:
                data = response.json()
                logger.info(f'[get_file_info] Parsed JSON response: {data}')
                
                if data.get('code') != 0:
                    logger.error(f'[get_file_info] API error: {data.get("msg")}')
                    return None
                    
                file_info = data.get('data', {})
            except Exception as e:
                logger.error(f'[get_file_info] Error parsing JSON: {str(e)}')
                return None
        else:
            # Response is raw file content, extract info from headers
            file_info = {}
            content_disposition = response.headers.get('Content-Disposition', '')
            inner_meta = response.headers.get('Inner_file_data_meta', '{}')
            
            try:
                meta_data = json.loads(inner_meta)
                file_info.update(meta_data)
            except:
                pass
                
            # Get filename from Content-Disposition
            if 'filename=' in content_disposition:
                file_info['name'] = content_disposition.split('filename=')[1].strip('"')
            elif 'filename*=' in content_disposition:
                file_info['name'] = content_disposition.split('filename*=')[1].split("'")[-1]
                
            # Get size and type
            file_info['size'] = int(response.headers.get('Content-Length', 0))
            file_info['type'] = response.headers.get('Content-Type', '')
            
        logger.info(f'[get_file_info] Extracted file info: {file_info}')
        
        # Try different field names based on API response
        name = file_info.get('FileName') or file_info.get('name', '')
        file_type = file_info.get('Mime') or file_info.get('type', '')
        size = file_info.get('FileSize') or file_info.get('size', 0)
        
        result = {
            'name': name,
            'type': file_type,
            'size': size
        }
        
        logger.info(f'[get_file_info] Returning result: {result}')
        return result
        
    except Exception as e:
        logger.error(f'[get_file_info] Error getting file info: {str(e)}')
        logger.error(f'[get_file_info] Traceback: {traceback.format_exc()}')
        return None

def download_file(file_key: str) -> Optional[bytes]:
    """Download a file from Lark using idea_bot's credentials"""
    try:
        # Get headers without content-type for file download
        headers = meta.get_headers(content_type=None)
        if headers is None:
            logger.error('Failed to get headers for file download')
            return None
            
        # Try the files endpoint first (more reliable)
        download_url = f'https://your-feishu-instance.com'
        logger.info(f'Downloading file with key: {file_key}')
        logger.info(f'Using URL: {download_url}')
        logger.info(f'Headers: {headers}')
        
        response = requests.get(download_url, headers=headers, stream=True)
        
        if not response.ok:
            # If files endpoint fails, try the messages endpoint
            logger.warning(f'Files endpoint failed with status {response.status_code}')
            download_url = f'https://your-feishu-instance.com'
            logger.info(f'Trying messages endpoint: {download_url}')
            
            # Get fresh token for retry
            headers = meta.get_headers(content_type=None)
            if headers is None:
                logger.error('Failed to get headers for retry')
                return None
                
            response = requests.get(download_url, headers=headers, stream=True)
        
        if not response.ok:
            logger.error(f'Failed to download file. Status code: {response.status_code}')
            logger.error(f'Response text: {response.text}')
            return None
            
        # Read the entire response content
        content = response.content
        
        logger.info(f'Successfully downloaded file content, size: {len(content)} bytes')
        return content
        
    except Exception as e:
        logger.error(f'Error downloading file: {str(e)}')
        logger.error(f'Traceback: {traceback.format_exc()}')
        return None

def get_file(file_key: str) -> dict:
    """Download a file from Lark using idea_bot's credentials"""
    try:
        # Get headers without content-type for file download
        headers = meta.get_headers(content_type=None)
        if headers is None:
            logger.error('Failed to get headers for file download')
            return None
            
        # Try the files endpoint first (more reliable)
        download_url = f'https://your-feishu-instance.com'
        logger.info(f'Downloading file with key: {file_key}')
        logger.info(f'Using URL: {download_url}')
        logger.info(f'Headers: {headers}')
        
        # Download the file
        response = requests.get(download_url, headers=headers, stream=True)
        
        if not response.ok:
            # If files endpoint fails, try the messages endpoint
            logger.warning(f'Files endpoint failed with status {response.status_code}')
            download_url = f'https://your-feishu-instance.com'
            logger.info(f'Trying messages endpoint: {download_url}')
            
            # Get fresh token for retry
            headers = meta.get_headers(content_type=None)
            if headers is None:
                logger.error('Failed to get headers for retry')
                return None
                
            response = requests.get(download_url, headers=headers, stream=True)
        
        if not response.ok:
            logger.error(f'Failed to download file. Status code: {response.status_code}')
            logger.error(f'Response text: {response.text}')
            return None
            
        # Get filename from Content-Disposition header if available
        content_disposition = response.headers.get('Content-Disposition', '')
        filename = 'downloaded_file'
        if 'filename=' in content_disposition:
            filename = content_disposition.split('filename=')[1].strip('"')
        elif 'filename*=' in content_disposition:
            filename = content_disposition.split('filename*=')[1].split("'")[-1]
        
        # Get content type
        content_type = response.headers.get('Content-Type', '')
        
        # Read the entire response content
        content = response.content
        
        logger.info(f'Successfully downloaded file: {filename} ({content_type})')
        logger.info(f'Content size: {len(content)} bytes')
        
        return {
            'content': content,
            'name': filename,
            'type': content_type
        }
        
    except Exception as e:
        logger.error(f'Error downloading file: {str(e)}')
        logger.error(f'Traceback: {traceback.format_exc()}')
        return None 