# Background Guide Processor

This module provides functionality to process background guides for Model UN conferences, extract content, analyze and summarize text, and generate structured outputs for RAG (Retrieval Augmented Generation) applications.

## Features

- **File Processing**: Support for both PDF and plain text inputs
- **Text Extraction**: Convert PDF content to raw text using PyMuPDF
- **Text Preprocessing & Segmentation**: Clean and segment document into logical sections
- **Content Analysis & Summarization**: Summarize each segment and extract key insights
- **JSON Generation**: Generate structured JSON outputs for topics, committee info, citations, and research map
- **RAG Integration**: Create vector embeddings and index for retrieval-augmented generation
- **Custom Guide Generation**: Generate tailored background guides using OpenAI API with RAG

## Architecture

The system follows a modular architecture with several components:

1. **Text Extraction**: Extract and clean text from PDFs or text files
2. **Segmentation**: Divide documents into logical sections using rule-based and ML approaches
3. **Summarization**: Generate summaries for each section using local models or OpenAI API
4. **JSON Generation**: Create structured JSON outputs for various aspects of the document
5. **RAG**: Index document segments and retrieve relevant context for queries
6. **API**: Flask API endpoints for integrating with web applications

## Installation

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

2. Set up environment variables:

```
OPENAI_API_KEY=your_openai_api_key
AWS_MODEL_ENDPOINT=your_aws_endpoint  # Optional
```

## Usage

### As a Flask API

The module provides several API endpoints:

- **POST /api/background-guide/process**: Process a background guide file
- **POST /api/background-guide/generate-custom-guide**: Generate a custom guide based on a query
- **POST /api/background-guide/retrieve-context**: Retrieve relevant context for a query
- **POST /api/background-guide/extract-text**: Extract text from a file without full processing

### From Command Line

```bash
python main.py path/to/your/background_guide.pdf
```

Options:
- `--output-dir`, `-o`: Directory for output files (default: "output")
- `--use-openai`, `-u`: Use OpenAI for summarization (default: True)
- `--no-openai`: Don't use OpenAI for summarization
- `--use-aws`, `-a`: Use AWS hosted model for refinement (default: True)
- `--no-aws`: Don't use AWS hosted model for refinement
- `--query`, `-q`: Search query to test retrieval

### Programmatically

```python
from background_guide.processor import BackgroundGuideProcessor

# Initialize processor
processor = BackgroundGuideProcessor(
    use_openai_for_summary=True,
    use_aws_model=False,
    output_dir="output"
)

# Process a file
results = processor.process_file("path/to/background_guide.pdf")

# Search for relevant context
context = processor.retrieve_context_for_query("How does the committee handle voting procedures?")

# Generate a custom guide
custom_guide = processor.generate_custom_guide("Create a guide on the committee's stance on climate change")
```

## Generated Outputs

The processor creates several JSON files:

1. **Topic Files**: Separate files for each detected topic
2. **Committee Information**: Details on committee structure, rules, and debate flow
3. **Cited Sources**: Extracted references and citations
4. **Research Map**: Comprehensive outline of the document's structure with key insights

## Required Dependencies

- PyMuPDF: For PDF text extraction
- Transformers & Torch: For text segmentation and summarization
- SentenceTransformers: For generating text embeddings
- FAISS: For vector similarity search
- OpenAI: For enhanced summarization and RAG
- Flask: For API endpoints

## Notes

- The AWS Model integration is optional and can be disabled
- OpenAI API usage can be toggled on/off (local models will be used if disabled)
- CUDA will be used for models if available, otherwise CPU 