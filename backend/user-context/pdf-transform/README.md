# PDF Transformation and Argumentation Analysis API

This service provides PDF processing capabilities and argumentation analysis through AWS Lambda functions. It extracts text from PDFs, analyzes document structure, identifies argumentative components, and detects patterns of reasoning.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Requirements](#requirements)
- [Deployment](#deployment)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Development](#development)

## Architecture Overview

This API is built using AWS Lambda with the following components:

- **PDF Processing**: Extract text and structure from PDFs
- **Argumentation Analysis**: Identify claims, premises, and relationships
- **S3 Integration**: Store documents and analysis results
- **CloudWatch Metrics**: Monitor performance and errors

The service uses transformer-based NLP models to analyze argumentative structures in documents, identifying argument components, relations, and reasoning patterns.

## Requirements

- Python 3.8+
- AWS CLI configured with appropriate permissions
- AWS Lambda access
- S3 bucket for document storage
- (Optional) AWS EFS for model caching

### Python Dependencies

```
boto3>=1.26.0
nltk>=3.8.1
torch>=2.0.0
transformers>=4.30.0
numpy>=1.24.0
reportlab>=3.6.12  # For testing only
```

## Deployment

### 1. Set Up AWS Resources

```bash
# Create S3 bucket
aws s3 mb s3://doc-processor-dev

# Create IAM role for Lambda (if not using existing role)
aws iam create-role --role-name lambda-pdf-transform \
  --assume-role-policy-document file://trust-policy.json

# Attach policies
aws iam attach-role-policy --role-name lambda-pdf-transform \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
aws iam attach-role-policy --role-name lambda-pdf-transform \
  --policy-arn arn:aws:iam::aws:policy/CloudWatchFullAccess
```

### 2. Package Lambda Function

```bash
# Create deployment package
pip install -r requirements.txt -t ./package
cp *.py ./package/
cd package
zip -r ../lambda_deployment.zip .
cd ..

# Deploy to Lambda
aws lambda create-function \
  --function-name pdf-transform \
  --zip-file fileb://lambda_deployment.zip \
  --handler lambda_function.lambda_handler \
  --runtime python3.8 \
  --role arn:aws:iam::ACCOUNT_ID:role/lambda-pdf-transform \
  --timeout 300 \
  --memory-size 2048
```

### 3. Configure Environment Variables

In the AWS Lambda console, set these environment variables:

- `S3_BUCKET`: Your S3 bucket name (e.g., `doc-processor-dev`)
- `LOG_LEVEL`: Logging level (`INFO`, `DEBUG`, `WARNING`, etc.)
- `USE_S3`: Whether to use S3 for storage (`true` or `false`)
- `TEST_ENV`: Whether to use test configuration (`true` or `false`)

### 4. (Optional) Set Up EFS for Model Caching

For improved performance on repeated invocations:

1. Create an EFS file system in the AWS console
2. Create access points for Lambda
3. Configure Lambda function to mount EFS
4. Set `EFS_MOUNT_PATH` environment variable

## API Reference

### PDF Processing API

#### Process a PDF Document

```json
POST /process
{
  "pdf_base64": "base64_encoded_pdf_data",
  "options": {
    "extract_structure": true,
    "extract_tables": true,
    "analyze_argumentation": true
  }
}
```

Response:

```json
{
  "success": true,
  "document_data": {
    "metadata": { ... },
    "content": { ... },
    "argumentation": { ... }
  },
  "processing_time_ms": 1234.56
}
```

#### Process Using S3

```json
POST /process
{
  "s3_key": "documents/example.pdf",
  "options": {
    "extract_structure": true,
    "analyze_argumentation": true
  }
}
```

Response:

```json
{
  "success": true,
  "s3_uri": "s3://doc-processor-dev/documents/example/analysis.json",
  "processing_time_ms": 1234.56
}
```

### Argumentation Analysis API

#### Analyze Document

```json
POST /analyze
{
  "document_data": {
    "metadata": { ... },
    "content": {
      "sentences": [ ... ],
      "paragraphs": [ ... ]
    }
  }
}
```

Response:

```json
{
  "success": true,
  "document_data": {
    "metadata": { ... },
    "content": { ... },
    "argumentation": {
      "components": [ ... ],
      "relations": [ ... ],
      "reasoning_patterns": [ ... ],
      "graph": { ... },
      "metrics": { ... }
    }
  },
  "processing_time_ms": 1234.56
}
```

## Testing

### Local Testing

Use the included `test_lambda.py` script to test the Lambda functions locally:

```bash
# Test PDF processing
python test_lambda.py --event-type process --pdf-path ./test_document.pdf

# Test argumentation analysis
python test_lambda.py --event-type analyze --use-flask

# Generate test PDF
python test_lambda.py --event-type generate
```

### Testing in Different Environments

The code supports two environments:

1. **Production**: Uses full models for accurate analysis
2. **Test**: Uses smaller models and mock pipelines for faster testing

Set the `TEST_ENV` environment variable to `true` to use test configuration:

```bash
export TEST_ENV=true
python test_lambda.py --event-type analyze
```

### Testing the Argumentation Analyzer

Use the command-line interface for testing the argumentation analyzer:

```bash
# Test with local file
python argumentation_analyzer.py --file ./document.json --test

# Test with S3 file
python argumentation_analyzer.py --s3 documents/example/document.json

# Custom output path
python argumentation_analyzer.py --file ./document.json --output ./results.json
```

## Development

### Project Structure

```
pdf-transform/
├── lambda_function.py       # Main Lambda entry point
├── pdf_processor.py         # PDF extraction functionality
├── argumentation_analyzer.py # Argumentation analysis
├── test_lambda.py           # Local testing utilities
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

### Adding New Models

To add new models for argumentation analysis:

1. Update the `MODEL_CONFIG` dictionary in `argumentation_analyzer.py`
2. Implement the analysis logic in the appropriate method
3. Update the metrics in the CloudWatch reporting

### Performance Considerations

- Memory usage is critical in Lambda environments
- Use batch processing for large documents
- Set appropriate timeout values (recommended: 5 minutes)
- Consider using provisioned concurrency for faster cold starts
- Use EFS for model caching to improve repeated invocations

---

## License

MIT

## Contact

For issues and support, please create an issue in the repository. 