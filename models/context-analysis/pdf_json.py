import os
import json
from pypdf import PdfReader
import re
import importlib.util
import sys
import fitz  # PyMuPDF

# Check if the classifier module is in the path
try:
    from models.context_analysis.distilbert_classifier import TopicClassifier
except ImportError:
    # If not, try to import it dynamically using the relative path
    classifier_path = os.path.join(os.path.dirname(__file__), "distilbert-classifier.py")
    if os.path.exists(classifier_path):
        spec = importlib.util.spec_from_file_location("distilbert_classifier", classifier_path)
        classifier_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(classifier_module)
        TopicClassifier = classifier_module.TopicClassifier
    else:
        print("Warning: Could not import TopicClassifier. Automatic segmentation will not be available.")
        TopicClassifier = None

def extract_text_with_formatting(pdf_path):
    """
    Extract text from PDF while preserving some formatting information.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        dict: Dictionary with text content and formatting information
    """
    # Open the PDF with PyMuPDF
    doc = fitz.open(pdf_path)
    
    result = {
        "pages": [],
        "full_text": "",
        "headers": [],
        "paragraphs": []
    }
    
    full_text = ""
    
    for page_num, page in enumerate(doc):
        # Extract text blocks with their formatting info
        blocks = page.get_text("dict")["blocks"]
        page_text = ""
        page_headers = []
        page_paragraphs = []
        
        for block in blocks:
            if "lines" in block:
                # Process text block
                for line in block["lines"]:
                    line_text = ""
                    line_size = 0
                    line_bold = False
                    
                    # Extract spans from the line
                    for span in line["spans"]:
                        span_text = span["text"]
                        span_size = span["size"]
                        span_font = span["font"]
                        
                        # Determine if text is bold
                        is_bold = "bold" in span_font.lower() or "heavy" in span_font.lower()
                        
                        # Update line properties
                        if span_size > line_size:
                            line_size = span_size
                        if is_bold:
                            line_bold = True
                            
                        line_text += span_text
                    
                    # Add line to page text
                    page_text += line_text + "\n"
                    
                    # Identify potential headers (larger, bold text or all caps)
                    is_header = (line_size > 11 and line_bold) or line_text.isupper() or len(line_text.strip()) < 50
                    
                    if is_header and line_text.strip():
                        page_headers.append({
                            "text": line_text.strip(),
                            "page": page_num + 1,
                            "size": line_size,
                            "bold": line_bold
                        })
                    else:
                        # Group lines into paragraphs
                        if line_text.strip():
                            if page_paragraphs and page_paragraphs[-1]["page"] == page_num + 1:
                                page_paragraphs[-1]["text"] += " " + line_text.strip()
                            else:
                                page_paragraphs.append({
                                    "text": line_text.strip(),
                                    "page": page_num + 1
                                })
        
        # Add page to the result
        result["pages"].append({
            "number": page_num + 1,
            "text": page_text
        })
        
        result["headers"].extend(page_headers)
        result["paragraphs"].extend(page_paragraphs)
        full_text += page_text
    
    # Update full text
    result["full_text"] = full_text
    
    doc.close()
    return result

def convert_pdf_to_json(pdf_path, multi_topic=False, manual_segmentation=False):
    """
    Convert a PDF file to JSON format.
    
    Args:
        pdf_path (str): Path to the PDF file
        multi_topic (bool): Whether the PDF contains multiple topics
        manual_segmentation (bool): Whether to manually segment the PDF
        
    Returns:
        str: JSON string containing the document name and text content
    """
    try:
        # Extract the document name from the path
        document_name = os.path.basename(pdf_path)
        
        # Extract text with formatting
        formatted_text = extract_text_with_formatting(pdf_path)
        
        # Read the PDF file using PyPDF as backup
        reader = PdfReader(pdf_path)
        
        # Extract text from all pages as a fallback
        backup_full_text = ""
        for page in reader.pages:
            backup_full_text += page.extract_text()
        
        # If formatted text extraction failed, use the backup
        if not formatted_text["full_text"]:
            formatted_text["full_text"] = backup_full_text
        
        result = {}
        
        if not multi_topic:
            # Single topic PDF - include formatting information
            result = {
                "document_name": document_name,
                "multi_topic": False,
                "content": {
                    "main": formatted_text["full_text"]
                },
                "formatting": {
                    "headers": formatted_text["headers"],
                    "paragraphs": formatted_text["paragraphs"],
                    "pages": formatted_text["pages"]
                }
            }
        else:
            # Multiple topics
            topic_segments = {}
            
            if manual_segmentation:
                # Get manual segmentation from user
                topic_segments = manually_segment_pdf(formatted_text["full_text"])
            else:
                # Use classifier to automatically segment
                topic_segments = automatically_segment_pdf(formatted_text["full_text"])
            
            # Match segments with formatting information
            segment_formatting = {}
            for topic_name, segment_text in topic_segments.items():
                segment_start = formatted_text["full_text"].find(segment_text)
                segment_end = segment_start + len(segment_text) if segment_start != -1 else -1
                
                # If segment found in the full text
                if segment_start != -1:
                    # Find headers within this segment
                    segment_headers = []
                    for header in formatted_text["headers"]:
                        header_pos = formatted_text["full_text"].find(header["text"])
                        if segment_start <= header_pos <= segment_end:
                            segment_headers.append(header)
                    
                    # Find paragraphs within this segment
                    segment_paragraphs = []
                    for paragraph in formatted_text["paragraphs"]:
                        para_pos = formatted_text["full_text"].find(paragraph["text"])
                        if segment_start <= para_pos <= segment_end:
                            segment_paragraphs.append(paragraph)
                    
                    segment_formatting[topic_name] = {
                        "headers": segment_headers,
                        "paragraphs": segment_paragraphs
                    }
            
            result = {
                "document_name": document_name,
                "multi_topic": True,
                "content": topic_segments,
                "formatting": segment_formatting
            }
        
        # Convert to JSON
        json_result = json.dumps(result, indent=4)
        
        return json_result
    
    except Exception as e:
        print(f"Error processing PDF: {e}")
        return json.dumps({"error": str(e)})

def manually_segment_pdf(text):
    """
    Ask the user to manually segment a PDF text into topics.
    
    Args:
        text (str): The full text of the PDF
        
    Returns:
        dict: Dictionary with topic names as keys and their content as values
    """
    print("\nPDF contains multiple topics. Let's segment it manually.")
    print("Look at the text and identify where different topics begin.")
    
    segments = {}
    num_topics = int(input("How many topics are in this PDF? "))
    
    # Display first few lines to help user identify segments
    preview_lines = 10
    print(f"\nPreview of first {preview_lines} lines:")
    for i, line in enumerate(text.split('\n')[:preview_lines]):
        print(f"{i+1}: {line}")
    
    print("\nFor each topic, you will provide a search term and a topic name.")
    print("We'll use the search term to find where the topic begins in the text.")
    
    current_position = 0
    for i in range(num_topics):
        topic_name = input(f"\nEnter a name for topic {i+1}: ")
        
        if i == 0:
            # First topic starts at the beginning
            start_pos = 0
        else:
            search_term = input(f"Enter a search term that marks the beginning of topic '{topic_name}': ")
            # Find the position of the search term after the current position
            start_pos = text.find(search_term, current_position)
            if start_pos == -1:
                print(f"Search term '{search_term}' not found. Using previous topic end as the start.")
                start_pos = current_position
            
        if i == num_topics - 1:
            # Last topic ends at the end of the document
            end_pos = len(text)
        else:
            next_topic_marker = input(f"Enter a search term that marks the END of topic '{topic_name}': ")
            end_pos = text.find(next_topic_marker, start_pos)
            if end_pos == -1:
                print(f"Search term '{next_topic_marker}' not found. Using the rest of the text.")
                end_pos = len(text)
        
        segments[topic_name] = text[start_pos:end_pos].strip()
        current_position = end_pos
    
    return segments

def automatically_segment_pdf(text):
    """
    Use the trained TopicClassifier to automatically segment a PDF text into topics.
    
    Args:
        text (str): The full text of the PDF
        
    Returns:
        dict: Dictionary with topic names as keys and their content as values
    """
    if TopicClassifier is None:
        print("Warning: TopicClassifier is not available. Falling back to manual segmentation.")
        return manually_segment_pdf(text)
    
    # Check if a trained model exists
    model_path = "./models/topic-classifier"
    if not os.path.exists(model_path):
        print("No trained model found. You need to train the model first.")
        print("For now, falling back to manual segmentation.")
        return manually_segment_pdf(text)
    
    try:
        # Initialize the classifier
        classifier = TopicClassifier()
        
        # Load the trained model
        classifier.load_model(model_path)
        
        # Segment the text
        segments = classifier.segment_text(text)
        
        # Ask user to provide meaningful names for the topics
        renamed_segments = {}
        print("\nAutomatic segmentation completed.")
        print(f"Found {len(segments)} topics in the document.")
        
        for topic_id, segment_text in segments.items():
            # Show preview of the segment
            preview = segment_text[:200] + "..." if len(segment_text) > 200 else segment_text
            print(f"\nPreview of {topic_id}:\n{preview}")
            
            # Ask for a meaningful name
            topic_name = input(f"Enter a meaningful name for this topic (or press Enter to keep '{topic_id}'): ")
            if not topic_name:
                topic_name = topic_id
                
            renamed_segments[topic_name] = segment_text
            
        return renamed_segments
    
    except Exception as e:
        print(f"Error in automatic segmentation: {e}")
        print("Falling back to manual segmentation.")
        return manually_segment_pdf(text)

def detect_multiple_topics(pdf_path):
    """
    Ask the user if the PDF contains multiple topics.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        bool: True if the PDF contains multiple topics, False otherwise
    """
    document_name = os.path.basename(pdf_path)
    response = input(f"\nDoes the PDF '{document_name}' contain multiple topics/papers? (y/n): ")
    return response.lower() in ["y", "yes"]

def save_pdf_as_json(pdf_path, output_path=None):
    """
    Convert a PDF to JSON and save it to a file.
    
    Args:
        pdf_path (str): Path to the PDF file
        output_path (str, optional): Path to save the JSON file. If None, 
                                     uses the PDF filename with .json extension.
    
    Returns:
        str: Path to the saved JSON file
    """
    # Generate output path if not provided
    if output_path is None:
        base_name = os.path.splitext(pdf_path)[0]
        output_path = f"{base_name}.json"
    
    # Ask user if PDF contains multiple topics
    multi_topic = detect_multiple_topics(pdf_path)
    
    # If multiple topics, ask if they want to segment manually
    manual_segmentation = False
    if multi_topic:
        seg_response = input("Would you like to segment the topics manually? (y/n): ")
        manual_segmentation = seg_response.lower() in ["y", "yes"]
    
    # Convert PDF to JSON
    json_content = convert_pdf_to_json(pdf_path, multi_topic, manual_segmentation)
    
    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(json_content)
    
    return output_path

# Example usage
if __name__ == "__main__":
    # Replace with your PDF path
    pdf_file = "example.pdf"
    json_file = save_pdf_as_json(pdf_file)
    print(f"PDF converted to JSON and saved as {json_file}")
