# Document Analysis Pipeline for Delegate Profile Generation

This project implements a comprehensive document analysis pipeline to process delegate position papers and speeches, analyzing both writing style (linguistic patterns) and argumentative reasoning structures. The pipeline focuses on **how** delegates write and reason rather than the specific content of their documents.

## Overview

The pipeline extracts, processes, and analyzes PDF documents through several stages:
1. **PDF Text Extraction** - Extracts text while preserving document structure
2. **Metadata Extraction** - Identifies document metadata like committee, country, topics
3. **BERT-Friendly Formatting** - Prepares text for transformer-based analysis
4. **Linguistic Style Analysis** - Analyzes writing style features
5. **Argumentation Analysis** - Identifies argument components and relationships
6. **Profile Generation** - Creates a comprehensive delegate profile

## Key Features

- Converts PDF documents to structured text with PyMuPDF and PyMuPDF4LLM
- Extracts metadata using pattern recognition and named entity recognition
- Segments text appropriately for BERT models with controlled overlapping
- Identifies argumentative components (claims, premises) and their relationships
- Detects reasoning patterns (deductive, inductive, abductive, analogical)
- Analyzes linguistic style features for stylometric profiling
- Generates comprehensive delegate profiles based on multiple documents
- Provides a RESTful API for document processing

## Installation

### Prerequisites

- Python 3.8+
- PyTorch
- Transformers (HuggingFace)
- PyMuPDF
- Flask

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/delegate-analysis.git
cd delegate-analysis

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download required NLTK resources
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('averaged_perceptron_tagger')"

# Download SpaCy model
python -m spacy download en_core_web_sm
```

## Usage

### Command Line Interface

Process a single document:

```bash
python document_processing_pipeline.py path/to/document.pdf --document-type position_paper
```

Process multiple documents and generate a delegate profile:

```bash
python document_processing_pipeline.py path/to/doc1.pdf path/to/doc2.pdf --profile --output-dir ./output
```

### API

Start the API server:

```bash
python api.py
```

Process a document via API:

```bash
curl -X POST -F "file=@path/to/document.pdf" -F "document_type=position_paper" http://localhost:5000/process
```

## API Endpoints

- `POST /process` - Process a single document
- `POST /process-batch` - Process multiple documents
- `GET /download/<filename>` - Download a processed file
- `GET /health` - Check API health

## Modules

1. **pdf_processor.py** - Extracts text from PDF documents
2. **metadata_extractor.py** - Extracts metadata from document content
3. **bert_formatter.py** - Formats document data for BERT processing
4. **linguistic_features.py** - Extracts linguistic style features
5. **argumentation_analyzer.py** - Analyzes argumentation structure
6. **document_processing_pipeline.py** - Coordinates the entire pipeline
7. **config.py** - Configuration settings
8. **api.py** - Flask API for document processing

## HuggingFace Models Used

The pipeline utilizes the following HuggingFace models:

1. **BERT Base Uncased** - For text embeddings and general NLP tasks
2. **DistilRoBERTa for Argument Component Detection** - For identifying argument components
3. **BERT for Argument Relation Classification** - For identifying relationships between arguments
4. **DistilBERT Fine-tuned on MNLI** - For reasoning pattern classification

## Customization

You can customize the pipeline by modifying the settings in `config.py`:

- Change the models used for different analysis components
- Enable/disable various processing options
- Configure API settings

## License

MIT License

## Citation

If you use this pipeline in your research, please cite:

```
@software{delegate_analysis_pipeline,
  author = {Your Name},
  title = {Document Analysis Pipeline for Delegate Profile Generation},
  year = {2025},
  url = {https://github.com/yourusername/delegate-analysis}
}
```
