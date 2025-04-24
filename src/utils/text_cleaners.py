import re 
import pandas as pd
import logging
logging.basicConfig(level=logging.INFO) 
logger = logging.getLogger(__name__)



def clean_description(text):
    
    """Clean and standardize JIRA bug descriptions"""
    
    if pd.isna(text) or text is None:
        return ""
    
    text = str(text)
    
    # Replace Google Drive links and other markdown links with a placeholder
    text = re.sub(r'\[https:\/\/.*?\|.*?\]', '[LINK]', text)
    
    # Remove all other markdown-style links (like [text|url])
    text = re.sub(r'\[.*?\|.*?\]', '[LINK]', text)

    # Remove file/image attachments like !file.png!
    text = re.sub(r'!.*?!', '[FILE ATTACHMENT]', text)
    
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text)

    text.strip()

    logger.info(f"Cleaned description: {text}")

    
    return text.strip()