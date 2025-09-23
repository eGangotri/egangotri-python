import csv
import re
from docx import Document

def parse_catalog_entry(entry):
    # Skip empty entries
    if not entry.strip():
        return None
        
    # Split the entry into parts
    parts = entry.strip().split()
    
    # Initialize variables
    subject = []
    manuscript_id = None
    title = []
    language = None
    script = None
    material = None
    notes = []
    
    # Parse through parts
    i = 0
    while i < len(parts):
        # Look for manuscript ID (4 digits)
        if re.match(r'^\d{4}$', parts[i]):
            manuscript_id = parts[i]
            # Everything before this was subject
            subject = ' '.join(parts[:i])
            i += 1
            break
        i += 1
        
    if not manuscript_id:  # If no manuscript ID found, this might not be a valid entry
        return None
    
    # Continue parsing for title until we hit language marker
    while i < len(parts):
        if parts[i] in ['Skt.', 'Skt.-']:
            language = parts[i]
            i += 1
            break
        title.append(parts[i])
        i += 1
    
    # Parse script
    if i < len(parts) and parts[i] in ['Dng.', 'New.']:
        script = parts[i]
        i += 1
    
    # Parse material and remaining as notes
    while i < len(parts):
        if parts[i] == 'Paper,':
            material = 'Paper'
            notes = ' '.join(parts[i+1:])
            break
        i += 1
    
    return {
        'subject': subject,
        'manuscript_id': manuscript_id,
        'title': ' '.join(title),
        'language': language,
        'script': script,
        'material': material,
        'notes': notes
    }

def process_docx_file(input_file, output_file):
    entries = []
    
    # Read the Word document
    doc = Document(input_file)
    
    # Combine all paragraphs into a single text
    # We'll consider entries separated by empty paragraphs
    current_entry = []
    
    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if text:
            current_entry.append(text)
        elif current_entry:  # Empty paragraph and we have collected some text
            # Process the current entry
            entry_text = ' '.join(current_entry)
            result = parse_catalog_entry(entry_text)
            if result:
                entries.append(result)
            current_entry = []
    
    # Process the last entry if exists
    if current_entry:
        entry_text = ' '.join(current_entry)
        result = parse_catalog_entry(entry_text)
        if result:
            entries.append(result)
    
    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['subject', 'manuscript_id', 'title', 'language', 'script', 'material', 'notes'])
        writer.writeheader()
        writer.writerows(entries)
    
    return len(entries)

# Usage
input_file = "C:\\Users\\cheta\\Downloads\\ask_catalog.docx"
output_file = "catalog_output.csv"

try:
    print("Starting to process the Word document...")
    num_entries = process_docx_file(input_file, output_file)
    print(f"Successfully processed {num_entries} entries")
    print(f"Output saved to {output_file}")
except Exception as e:
    print(f"Error processing file: {str(e)}")