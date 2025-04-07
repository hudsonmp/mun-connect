"""
Process and classify all papers in the papers directory.
This script will:
1. Convert PDFs to JSON
2. Classify each document as resolution, speech, or position paper
3. Detect multiple topics/papers within each document if applicable
"""

import os
import json
import argparse
from tqdm import tqdm
import sys

# Add the current directory to Python path to find the modules
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Import our modules
from pdf_json import save_pdf_as_json
from distilbert_document_type_classifier import DocumentTypeClassifier, DOCUMENT_TYPES
from distilbert_classifier import TopicClassifier

def classify_document(json_path, doc_classifier, topic_classifier=None):
    """
    Classify a document from its JSON file.
    
    Args:
        json_path (str): Path to the JSON file
        doc_classifier (DocumentTypeClassifier): Document type classifier
        topic_classifier (TopicClassifier, optional): Topic classifier for multi-topic docs
        
    Returns:
        dict: Classification results
    """
    try:
        # Load JSON
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        document_name = data.get('document_name', os.path.basename(json_path))
        
        # Check if document is multi-topic
        is_multi_topic = data.get('multi_topic', False)
        
        results = {
            "document_name": document_name,
            "multi_topic": is_multi_topic,
            "classifications": {}
        }
        
        if is_multi_topic:
            # Classify each topic segment
            content = data.get('content', {})
            
            for topic_name, text in content.items():
                doc_type, confidence = doc_classifier.predict(text, topic_name)
                
                results["classifications"][topic_name] = {
                    "document_type": doc_type,
                    "confidence": confidence
                }
        else:
            # Single topic document
            text = data.get('content', {}).get('main', '')
            doc_type, confidence = doc_classifier.predict(text, document_name)
            
            results["classifications"]["main"] = {
                "document_type": doc_type,
                "confidence": confidence
            }
            
            # If it's not explicitly multi-topic but topic_classifier is provided,
            # check if we should split it into multiple topics
            if topic_classifier and len(text.split()) > 300:  # Only try for longer documents
                try:
                    # Try to segment text into topics
                    segments = topic_classifier.segment_text(text)
                    
                    # If we found multiple topics, add them to the results
                    if len(segments) > 1:
                        results["detected_topics"] = {}
                        
                        for topic_id, segment_text in segments.items():
                            # Classify each detected segment
                            seg_doc_type, seg_confidence = doc_classifier.predict(segment_text)
                            
                            results["detected_topics"][topic_id] = {
                                "document_type": seg_doc_type,
                                "confidence": seg_confidence,
                                "preview": segment_text[:200] + "..." if len(segment_text) > 200 else segment_text
                            }
                except Exception as e:
                    print(f"Error detecting topics: {e}")
        
        # Update JSON with classification results
        data['classification'] = results
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        
        return results
    
    except Exception as e:
        print(f"Error classifying document {json_path}: {e}")
        return {"error": str(e)}

def process_and_classify_all(directory, output_dir=None, force_reprocess=False):
    """
    Process and classify all PDFs in a directory.
    
    Args:
        directory (str): Directory containing PDF files
        output_dir (str, optional): Directory to save processed JSON files
        force_reprocess (bool): Whether to reprocess already processed files
        
    Returns:
        dict: Overall classification statistics
    """
    if output_dir is None:
        output_dir = os.path.join(directory, "classified")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize classifiers
    doc_classifier_path = "./models/document-type-classifier"
    topic_classifier_path = "./models/topic-classifier"
    
    doc_classifier = DocumentTypeClassifier(doc_classifier_path if os.path.exists(doc_classifier_path) else None)
    
    topic_classifier = None
    if os.path.exists(topic_classifier_path):
        try:
            topic_classifier = TopicClassifier()
            topic_classifier.load_model(topic_classifier_path)
        except Exception as e:
            print(f"Warning: Could not load topic classifier: {e}")
    
    # Get all PDF files in the directory
    pdf_files = [f for f in os.listdir(directory) if f.lower().endswith('.pdf')]
    
    # Statistics to return
    stats = {
        "total_documents": len(pdf_files),
        "document_types": {doc_type: 0 for doc_type in DOCUMENT_TYPES.values()},
        "multi_topic_documents": 0,
        "errors": 0
    }
    
    for pdf_file in tqdm(pdf_files, desc="Processing and classifying PDFs"):
        pdf_path = os.path.join(directory, pdf_file)
        json_path = os.path.join(output_dir, os.path.splitext(pdf_file)[0] + '.json')
        
        try:
            # Process PDF to JSON if it doesn't exist or if we're forcing reprocessing
            if not os.path.exists(json_path) or force_reprocess:
                print(f"Converting {pdf_file} to JSON...")
                json_path = save_pdf_as_json(pdf_path, json_path)
            
            # Classify the document
            results = classify_document(json_path, doc_classifier, topic_classifier)
            
            # Update statistics
            if "error" in results:
                stats["errors"] += 1
                continue
                
            if results.get("multi_topic", False):
                stats["multi_topic_documents"] += 1
                
                # Count each topic's document type
                for _, classification in results.get("classifications", {}).items():
                    doc_type = classification.get("document_type")
                    if doc_type in stats["document_types"]:
                        stats["document_types"][doc_type] += 1
            else:
                # Count the main document type
                main_classification = results.get("classifications", {}).get("main", {})
                doc_type = main_classification.get("document_type")
                if doc_type in stats["document_types"]:
                    stats["document_types"][doc_type] += 1
            
        except Exception as e:
            print(f"Error processing {pdf_file}: {e}")
            stats["errors"] += 1
    
    return stats

def main():
    parser = argparse.ArgumentParser(description='Process and classify all papers')
    parser.add_argument('--data_dir', type=str, default='./models/context-analysis/papers',
                        help='Directory containing PDF files')
    parser.add_argument('--output_dir', type=str, help='Directory to save processed JSON files')
    parser.add_argument('--force', action='store_true', 
                        help='Force reprocessing of already processed files')
    args = parser.parse_args()
    
    if not os.path.exists(args.data_dir):
        print(f"Error: Directory {args.data_dir} does not exist")
        return
    
    # Process and classify all PDFs
    print(f"Processing and classifying all PDFs in {args.data_dir}...")
    stats = process_and_classify_all(
        args.data_dir, 
        args.output_dir,
        args.force
    )
    
    # Print statistics
    print("\n===== Classification Results =====")
    print(f"Total documents processed: {stats['total_documents']}")
    print(f"Documents with multiple topics: {stats['multi_topic_documents']}")
    print("\nDocument type distribution:")
    for doc_type, count in stats["document_types"].items():
        print(f"  {doc_type}: {count}")
    print(f"\nErrors: {stats['errors']}")

if __name__ == "__main__":
    main() 