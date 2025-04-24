from jira import JIRA
import csv
import logging
import requests
from requests.auth import HTTPBasicAuth
import os
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import time
import random

load_dotenv()
# Jira credentials (replace with your actual values)
JIRA_SERVER = os.getenv('JIRA_SERVER')
JIRA_EMAIL = os.getenv('JIRA_EMAIL')
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')
DAYS_BACK = int(os.getenv("DAYS_BACK", "60"))  # Default to 60 days
TEAM_WHITELIST = os.getenv("TEAM_WHITELIST", "")
print(f"TEAM_WHITELIST: {TEAM_WHITELIST}")

N_DAYS_AGO = (datetime.utcnow() - timedelta(days=DAYS_BACK)).strftime('%Y-%m-%d')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# JQL query to fetch both Bug and Transient Bug issue types
JQL = JQL = f'issuetype in ("Bug", "Transient Bug") AND created >= "{N_DAYS_AGO}"'

# API endpoint for searching issues
SEARCH_URL = f'{JIRA_SERVER}/rest/api/2/search'

# Headers for the request
HEADERS = {
    'Accept': 'application/json'
}

# Base parameters for the request.
# We request 'customfield_14600' which is used for "Fixed By", 
# and the 'description' field for the full ticket body.
BASE_PARAMS = {
    'jql': JQL,
    'fields': 'key,summary,reporter,assignee,status,created,updated,description,customfield_14600,issuetype'
}

# Rate limiting parameters
MAX_RETRIES = 5
BASE_RETRY_DELAY = 10  # seconds
MAX_WORKERS = 5  # Reduced from 10 to avoid overwhelming the API

def extract_text_only(content):
    """
    Extracts only 'text' type nodes from ADF content blocks.
    Ignores all other node types.
    """
    texts = []
    if isinstance(content, list):
        for item in content:
            texts.extend(extract_text_only(item))
    elif isinstance(content, dict):
        node_type = content.get('type')
        if node_type == 'text':  # Only process 'text' nodes
            texts.append(content.get('text', ''))
        elif 'content' in content:  # Recursively process nested content
            texts.extend(extract_text_only(content['content']))
    return texts

def extract_description_text(description):
    """
    Extracts plain text from a Jira description, handling both string and JSON formats.
    """
    if not description:
        return ""
    if isinstance(description, str):
        return description.strip()
    if isinstance(description, dict):
        extracted_text = '\n'.join(extract_text_only(description.get('content', []))).strip()
        return extracted_text
    logger.warning(f"Unexpected description format: {type(description)}")
    return ""

def fetch_issues_batch(start_at, batch_size):
    """
    Fetches a batch of issues starting at 'start_at' with 'batch_size' results.
    Includes retry logic for rate limits.
    Returns a tuple of (issues, total_count).
    """
    params = BASE_PARAMS.copy()
    params['startAt'] = start_at
    params['maxResults'] = batch_size
    
    for retry in range(MAX_RETRIES):
        try:
            response = requests.get(
                SEARCH_URL,
                headers=HEADERS,
                params=params,
                auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
            )
            
            # Check for rate limiting response
            if response.status_code == 429:
                # Get retry-after header if available, or use exponential backoff
                retry_after = int(response.headers.get('Retry-After', BASE_RETRY_DELAY * (2 ** retry)))
                logger.warning(f"Rate limit hit at {start_at}. Retrying after {retry_after} seconds (attempt {retry+1}/{MAX_RETRIES})")
                time.sleep(retry_after)
                continue
            
            response.raise_for_status()
            data = response.json()
            issues = data.get('issues', [])
            total = data.get('total', 0)
            
            # Add a small delay between requests even on success to be nice to the API
            time.sleep(random.uniform(0.5, 1.5))
            
            return issues, total
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:  # Too Many Requests
                # This should be handled above, but just in case
                retry_after = int(response.headers.get('Retry-After', BASE_RETRY_DELAY * (2 ** retry)))
                logger.warning(f"Rate limit hit at {start_at}. Retrying after {retry_after} seconds (attempt {retry+1}/{MAX_RETRIES})")
                time.sleep(retry_after)
            else:
                logger.error(f"HTTP error at {start_at}: {e}")
                if retry < MAX_RETRIES - 1:
                    wait_time = BASE_RETRY_DELAY * (2 ** retry)
                    logger.info(f"Retrying in {wait_time} seconds... (attempt {retry+1}/{MAX_RETRIES})")
                    time.sleep(wait_time)
                else:
                    raise
        except Exception as e:
            logger.error(f"Error fetching batch at {start_at}: {e}")
            if retry < MAX_RETRIES - 1:
                wait_time = BASE_RETRY_DELAY * (2 ** retry)
                logger.info(f"Retrying in {wait_time} seconds... (attempt {retry+1}/{MAX_RETRIES})")
                time.sleep(wait_time)
            else:
                raise
    
    # If we got here, all retries failed
    raise Exception(f"Failed to fetch batch at {start_at} after {MAX_RETRIES} retries")

def write_issues_to_csv(csv_writer, issues):
    """
    Writes the list of issues to CSV using the given csv_writer.
    Skips issues where the Fixed By field is 'unassigned'.
    """
    for issue in issues:
        fields = issue['fields']
        # Use customfield_14600 for Fixed By.
        fixed_by_field = fields.get('customfield_14600')
        # fixed_by = (fixed_by_field.get('value') 
        #             if fixed_by_field and fixed_by_field.get('value') and fixed_by_field.get('value').lower() != "unassigned"
        #             else "unassigned")
        # # Skip issues with Fixed By as unassigned
        # if fixed_by.lower() == "unassigned":
        #     continue
        fixed_by = (fixed_by_field.get('value') 
                    if fixed_by_field and fixed_by_field.get('value') and fixed_by_field.get('value').lower() != "unassigned"
                    else "unassigned")

        # Skip if unassigned or not in the whitelisted teams
        if fixed_by.lower() == "unassigned" or (TEAM_WHITELIST and fixed_by.lower() not in TEAM_WHITELIST):
            continue
            
        # Get issue type
        issue_type = fields.get('issuetype', {}).get('name', 'Unknown')

        description = extract_description_text(fields.get('description'))
        
        # Sanitize fields for CSV
        summary = fields.get('summary', '').replace('"', '""').replace('\n', ' ').replace('\r', '')
        description = description.replace('"', '""').replace('\n', ' ').replace('\r', '')
        
        csv_writer.writerow([
            issue['key'],
            summary,
            fields.get('reporter', {}).get('displayName', 'Unknown'),
            fields.get('assignee', {}).get('displayName', 'Unassigned'),
            fields.get('status', {}).get('name'),
            fields.get('created'),
            fields.get('updated'),
            fixed_by,
            description,
            issue_type
        ])

def save_progress(all_batches, output_file):
    """
    Save the current progress to avoid losing data in case of failure
    """
    # Flatten the list of batches into a single list of issues
    all_issues = [issue for batch in all_batches for issue in batch]
    
    # Write to a temporary file first to avoid corrupting the main output
    temp_file = f"{output_file}.temp"
    with open(temp_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        # Write CSV header with Issue Type added
        writer.writerow([
            'Issue Key', 'Summary', 'Reporter', 'Assignee', 'Status',
            'Created', 'Updated', 'Fixed By', 'Description', 'Issue Type'
        ])
        write_issues_to_csv(writer, all_issues)
    
    # Rename the temp file to the actual output file
    if os.path.exists(output_file):
        os.remove(output_file)
    os.rename(temp_file, output_file)
    
    return len(all_issues)

def main():
    output_file = '/home/sourjyamukherjee/Projects/jira_router/src/data/issues.csv'
    batch_size = 50  # Reduced batch size to avoid overwhelming the API
    
    try:
        # First call to determine the total count
        first_batch, total = fetch_issues_batch(0, batch_size)
        logger.info(f"Total issues to fetch: {total}")
        
        # List to hold all batches of issues
        all_batches = [first_batch]
        
        # Save initial batch to have something in case of failure
        save_progress(all_batches, output_file)
        
        # Prepare the list of start indices for the remaining batches
        start_indices = list(range(batch_size, total, batch_size))
        total_batches = len(start_indices) + 1
        
        # Use ThreadPoolExecutor to fetch batches concurrently, but with fewer workers
        completed = 1
        failed_indices = []
        
        # Process in smaller chunks to save progress periodically
        chunk_size = 50  # Number of batches to process before saving
        for chunk_start in range(0, len(start_indices), chunk_size):
            chunk_end = min(chunk_start + chunk_size, len(start_indices))
            current_indices = start_indices[chunk_start:chunk_end]
            
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                future_to_start = {
                    executor.submit(fetch_issues_batch, start, batch_size): start 
                    for start in current_indices
                }
                for future in as_completed(future_to_start):
                    start = future_to_start[future]
                    try:
                        issues, _ = future.result()
                        all_batches.append(issues)
                        completed += 1
                        logger.info(f"Fetched batch starting at {start}, progress: {completed}/{total_batches} ({completed/total_batches:.1%})")
                    except Exception as e:
                        logger.error(f"Error fetching batch starting at {start}: {e}")
                        failed_indices.append(start)
            
            # Save progress after each chunk
            issues_saved = save_progress(all_batches, output_file)
            logger.info(f"Progress saved: {issues_saved} issues written to {output_file}")
        
        # Retry failed batches
        if failed_indices:
            logger.info(f"Retrying {len(failed_indices)} failed batches...")
            retry_count = 0
            while failed_indices and retry_count < 3:
                retry_count += 1
                still_failed = []
                
                for start in failed_indices:
                    try:
                        logger.info(f"Retrying batch at {start} (attempt {retry_count})")
                        # Add a longer delay before retry
                        time.sleep(BASE_RETRY_DELAY)
                        issues, _ = fetch_issues_batch(start, batch_size)
                        all_batches.append(issues)
                        logger.info(f"Successfully retried batch at {start}")
                    except Exception as e:
                        logger.error(f"Retry failed for batch at {start}: {e}")
                        still_failed.append(start)
                
                failed_indices = still_failed
                
                # Save progress after retries
                issues_saved = save_progress(all_batches, output_file)
                logger.info(f"Progress after retries: {issues_saved} issues written to {output_file}")
        
        # Final stats
        with open(output_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            rows = list(reader)
        
        final_count = len(rows)
        bug_count = sum(1 for row in rows if row[9] == 'Bug')
        transient_bug_count = sum(1 for row in rows if row[9] == 'Transient Bug')
        
        logger.info(f"Final statistics:")
        logger.info(f"  Total issues: {final_count}")
        logger.info(f"  Bug issues: {bug_count}")
        logger.info(f"  Transient Bug issues: {transient_bug_count}")
        
        if failed_indices:
            logger.warning(f"Some batches could not be fetched after multiple retries: {failed_indices}")
        
        print(f"Successfully wrote {final_count} issues to {output_file}")
        
    except Exception as e:
        logger.error(f"An error occurred during execution: {e}")
        raise

if __name__ == '__main__':
    main()