import csv
import requests
import time
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)

def convert_text(text: str, nativize: bool = False) -> str:
    """
    Convert text from IAST to RomanColloquial using Aksharamukha API
    """
    if not text:
        return ""
        
    # Clean the text by removing square brackets and their contents
    text = text.replace('[', '').replace(']', '')
        
    url = "https://www.aksharamukha.com/api/convert"
    body = {
        "source": "IAST",
        "target": "RomanColloquial",
        "text": text,
        "nativize": nativize,
    }
    
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=body, timeout=30)
            response.raise_for_status()
            return response.json().get('text', '')
        except requests.RequestException as e:
            if attempt < max_retries - 1:
                logging.warning("Attempt %d failed for text '%s': %s. Retrying...", 
                              attempt + 1, text, e)
                time.sleep(retry_delay)
            else:
                logging.error("All attempts failed for text '%s': %s", text, e)
                return text  # Return original text after all retries fail

def process_csv(input_file: Path) -> None:
    """
    Process the catalog CSV file and add transliterated columns
    """
    output_file = input_file.parent / f"{input_file.stem}_transliterated{input_file.suffix}"
    
    try:
        # Read all rows from input CSV
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fieldnames = reader.fieldnames + ['subject-without-diacritics', 'title-without-diacritics']
        
        # Process each row
        total_rows = len(rows)
        for i, row in enumerate(rows, 1):
            logging.info("Processing row %d of %d...", i, total_rows)
            
            # Convert subject and title
            row['subject-without-diacritics'] = convert_text(row['subject'])
            row['title-without-diacritics'] = convert_text(row['title'])
            
            # Add small delay to avoid overwhelming the API
            time.sleep(0.5)
        
        # Write output CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
            
        logging.info("Processing complete! Output saved to: %s", output_file)
        
    except (IOError, csv.Error) as e:
        logging.error("Error processing CSV file: %s", e)

def main() -> None:
    """Main entry point for the script"""
    csv_path = Path("catalog_output.csv")
    process_csv(csv_path)

if __name__ == "__main__":
    main()
