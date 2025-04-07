"""
Check if processed JSON files have document types and add them if missing.
This script analyzes the content of each JSON file and assigns a document type
(resolution, speech, or position_paper) based on characteristics of the text.
"""

import os
import json
import re
from tqdm import tqdm

def analyze_document_type(content, document_name):
    """
    Analyze content to determine document type.
    
    Args:
        content (str): Document content
        document_name (str): Name of the document
        
    Returns:
        str: Document type (resolution, speech, or position_paper)
    """
    content_lower = content.lower()
    filename_lower = document_name.lower()
    
    # Check filename for clues
    if any(word in filename_lower for word in ['resolution', 'ecosoc crisis']):
        return 'resolution'
    
    if any(word in filename_lower for word in ['speech', 'speeches']):
        return 'speech'
    
    if any(word in filename_lower for word in ['position paper', 'position_paper']):
        return 'position_paper'
    
    # Look for resolution patterns
    if re.search(r'(\d+\.\s+[A-Z])|(\n\s*\d+\.\s+)', content) and re.search(r'(The General Assembly|The Security Council)', content):
        return 'resolution'
    
    # Look for speech patterns
    if re.search(r'(thank you|distinguished delegates|mr\. president|madam chair)', content_lower):
        return 'speech'
        
    # Look for position paper patterns 
    if re.search(r'(delegation|country)[:\s]+(of\s+)?[A-Z]', content):
        return 'position_paper'
    
    # If still uncertain, make a best guess based on structure
    if "section" in content_lower and not re.search(r'(\d+\.\s+[A-Z])', content):
        return 'position_paper'
    
    # Default to position paper if nothing else matches
    return 'position_paper'

def process_directory(directory_path):
    """
    Process all JSON files in a directory, adding document types if missing.
    
    Args:
        directory_path (str): Path to directory containing JSON files
        
    Returns:
        dict: Statistics on processed files
    """
    # Count statistics
    stats = {
        'total': 0,
        'already_had_type': 0,
        'added_type': 0,
        'types': {
            'resolution': 0,
            'speech': 0,
            'position_paper': 0
        }
    }
    
    # Get all JSON files
    json_files = [f for f in os.listdir(directory_path) if f.lower().endswith('.json')]
    stats['total'] = len(json_files)
    
    print(f"Processing {len(json_files)} JSON files...")
    
    for json_file in tqdm(json_files):
        file_path = os.path.join(directory_path, json_file)
        
        try:
            # Load JSON
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check if document_type exists
            if 'document_type' in data and data['document_type']:
                stats['already_had_type'] += 1
                doc_type = data['document_type']
            else:
                # Get the main content
                content = data.get('content', {}).get('main', '')
                document_name = data.get('document_name', json_file)
                
                # Determine document type
                doc_type = analyze_document_type(content, document_name)
                
                # Add to data
                data['document_type'] = doc_type
                
                # Save updated JSON
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4)
                
                stats['added_type'] += 1
            
            # Track type statistics
            if doc_type in stats['types']:
                stats['types'][doc_type] += 1
            
        except Exception as e:
            print(f"Error processing {json_file}: {e}")
    
    return stats

def main():
    # Directory containing processed JSON files
    processed_dir = './papers/processed'
    
    # Process the directory
    stats = process_directory(processed_dir)
    
    # Print statistics
    print("\nDocument Type Statistics:")
    print(f"Total files processed: {stats['total']}")
    print(f"Files that already had a document_type: {stats['already_had_type']}")
    print(f"Files where document_type was added: {stats['added_type']}")
    print("\nDocument type distribution:")
    for doc_type, count in stats['types'].items():
        print(f"{doc_type}: {count} files ({count/stats['total']*100:.1f}%)")

if __name__ == "__main__":
    main() 