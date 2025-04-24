from utils.text_cleaners import clean_description

def format_query_string(summary: str, description: str) -> str:
    """
    Format the query string for the model.
    """
    cleaned_description = clean_description(description)
    query_string = f"Summary: {summary}\nDescription: {cleaned_description}"
    
    return query_string