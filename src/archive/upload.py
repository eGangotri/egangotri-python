from internetarchive import upload
import os
import random
import re
from string import ascii_letters
from tqdm import tqdm
from .utils import add_to_upload_cycle

# Configure your credentials
# https://archive.org/account/s3.php


def bulk_upload(identifier, files, config,metadata=None):
    """Upload multiple files to Archive.org with progress tracking"""
    if metadata is None:
        return None
    
    # Show progress bar for the upload
    print(f"Uploading {len(files)} files to {identifier}...")
    response = upload(
        identifier,
        files=files,
        metadata=metadata,
        config={
            's3': {
                'access': config['s3']['access'],
                'secret': config['s3']['secret']
            }
        }
    )
    return response

def bulk_upload_pdfs(directory_path, metadata_set_one, config, accepted_extensions=['.pdf']):
    """Upload all PDF files from a directory to Archive.org
    
    Args:
        directory_path (str): Path to directory containing PDFs
        accepted_extensions (list): List of accepted file extensions (default: ['.pdf'])
    
    Returns:
        list: List of dictionaries containing upload results with structure:
            {
                'file': str,
                'item_id': str,
                'title': str,
                'creator': str,
                'url': str,
                'success': bool,
                'error': str (optional)
            }
    """
    results = []
    
          
    if not os.path.exists(directory_path):
        print(f"Directory not found: {directory_path}")
        return results
        
    for file in os.listdir(directory_path):
        if any(file.lower().endswith(ext.lower()) for ext in accepted_extensions):
            try:
                full_path = os.path.join(directory_path, file)
                # Generate unique ID for each file
                item_id = generate_item_id(file)
                # Get metadata from filename
                metadata = get_metadata_from_filename(file, metadata_set_one)
                
                print(f"Processing {file}...")
                print(f"Title: {metadata['title']}")
                print(f"Creator: {metadata['creator']}")
            
                result0 = bulk_upload(item_id, [full_path], config, metadata)

                upload_result = {
                    'file': file,
                    'item_id': item_id,
                    'title': metadata['title'],
                    'creator': metadata['creator'],
                    'url': f"https://archive.org/details/{item_id}",
                    'success': bool(result0)
                }
                
                if result0:
                    print("Upload successful")
                    print(f"View your upload: {upload_result['url']}\n")
                else:
                    upload_result['error'] = "Upload failed"
                    print("Upload failed\n")
                    
                results.append(upload_result)
                
            except Exception as e:
                error_msg = str(e)
                print(f"Error processing {file}: {error_msg}\n")
                results.append({
                    'file': file,
                    'success': False,
                    'error': error_msg
                })
    
    return results

def generate_item_id(filename):
    """Generate a valid item_id from filename with specific rules:
    - Starts with 4 random letters
    - Followed by filename without extension
    - Replace spaces with dashes
    - Only allow alphanumeric, dash, underscore
    - Max length 99 chars
    """
    # Generate 4 random letters
    prefix = ''.join(random.choice(ascii_letters) for _ in range(4))
    
    # Get filename without extension and convert to lowercase
    name = os.path.splitext(filename)[0].lower()
    
    # Replace spaces with dashes and remove any other non-allowed chars
    name = name.replace(' ', '-')
    name = re.sub(r'[^a-z0-9-_]', '', name)
    
    # Combine and truncate to 99 chars if needed
    item_id = f"{prefix}-{name}"
    if len(item_id) > 99:
        item_id = item_id[:99]
    
    return item_id

def get_metadata_from_filename(filename, metadata_set_one):
    """Extract title and creator from filename"""
    # Remove extension
    name_without_ext = os.path.splitext(filename)[0]
    
    # Get creator from text after last dash, or use default
    if '-' in name_without_ext:
        title = name_without_ext
        creator = name_without_ext.split('-')[-1].strip()
    else:
        title = name_without_ext
        creator = metadata_set_one.get("creator", "")
    
    return {
        'title': title,
        'creator': creator,
        'subject': metadata_set_one.get("subject", ""),
        'description': f'{metadata_set_one.get("description", "")} {filename}',
        'mediatype': 'texts'
    }
