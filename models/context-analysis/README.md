# Document Classification System

This system processes PDF files, particularly UN committee documents, and classifies them as:
- Resolutions
- Speeches
- Position Papers

It can also detect when a PDF contains multiple topics or separate documents and segment them accordingly.

## Requirements

Install the required packages:

```bash
pip install -r requirements.txt
```

## Components

- **PDF to JSON Converter (`pdf_json.py`)**: Converts PDFs to JSON while preserving formatting
- **Document Type Classifier (`distilbert_document_type_classifier.py`)**: Classifies documents as resolution, speech, or position paper
- **Topic Classifier (`distilbert_classifier.py`)**: Detects and segments multiple topics within a document
- **Training Scripts**:
  - `train_document_type_classifier.py`: Train the document type classifier
  - `train_topic_classifier.py`: Train the topic classifier
- **Processing Script (`classify_all_papers.py`)**: Process and classify all papers in a directory

## Usage Instructions

### 1. Train the Document Type Classifier

To train the document type classifier with your PDF documents:

```bash
python train_document_type_classifier.py --data_dir ./models/context-analysis/papers --use_example_data
```

Options:
- `--data_dir`: Directory containing your PDF files
- `--output_dir`: Directory to save processed JSON files (optional)
- `--epochs`: Number of training epochs (default: 3)
- `--manual_labeling`: Manually label all documents (otherwise tries to auto-detect)
- `--use_example_data`: Use example data for training (recommended for initial training)

### 2. Train the Topic Classifier (for multi-topic detection)

To train the topic classifier:

```bash
python train_topic_classifier.py --data_dir ./models/context-analysis/papers/processed --use_example_data
```

Options:
- `--data_dir`: Directory containing segmented JSON files
- `--epochs`: Number of training epochs (default: 3)
- `--use_example_data`: Use example data for training (recommended for initial training)

### 3. Process and Classify All Papers

To process and classify all papers in a directory:

```bash
python classify_all_papers.py --data_dir ./models/context-analysis/papers --output_dir ./models/context-analysis/papers/classified
```

Options:
- `--data_dir`: Directory containing PDF files
- `--output_dir`: Directory to save processed JSON files (optional)
- `--force`: Force reprocessing of already processed files

## How It Works

1. **Document Type Classification**:
   - First tries to detect document type from the document name
   - Uses text structure analysis (looking for patterns like numbered clauses, first-person pronouns, etc.)
   - Falls back to the trained DistilBERT model for classification

2. **Topic Segmentation**:
   - Detects if a document contains multiple topics or separate papers
   - Segments the document based on content changes
   - Classifies each segment separately

3. **Formatting Preservation**:
   - The system preserves document formatting like headers, bold text, and paragraphs
   - This helps improve classification accuracy

## Example Output

After processing, each document will have a JSON file with:
- Document text content
- Formatting information (headers, paragraphs)
- Classification results (document type, confidence score)
- Multiple topic segments if detected

## Notes

- Initial model training will be based on example data
- As you process more documents, the classification accuracy will improve
- You can re-train the models periodically with more data
- If the automatic classification is incorrect, you can manually label documents

For more detailed information, see the documentation in each module. 