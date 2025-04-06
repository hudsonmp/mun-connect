# Multi-Document Generator for AWS Lambda

This module provides UN document generation capabilities (position papers, speeches, and resolutions) optimized for deployment on AWS Lambda.

## AWS Architecture

The generator uses the following AWS services:

- **Lambda**: For executing the document generation
- **S3**: For storing delegate profiles and generated documents
- **EFS**: For caching model weights and tokenizers
- **CloudWatch**: For logging and monitoring
- **IAM**: For security permissions

## Features

- Generates multiple document types (position papers, speeches, resolutions)
- Mimics a delegate's writing style
- Optimized for AWS Lambda with proper resource handling
- Supports separate model initialization to reduce cold start times
- Includes test mode with smaller models for development
- Provides local testing capabilities with mock fixtures

## AWS Lambda Optimization

This generator is optimized for Lambda in several ways:

1. **Separate Initialization**: Model loading occurs during Lambda container initialization rather than invocation
2. **EFS Integration**: Model weights are cached on EFS for faster loading
3. **S3 Operations**: File I/O replaced with S3 operations for persistence
4. **Memory Management**: Optimized for efficient memory usage in the Lambda environment
5. **Error Handling**: Comprehensive error handling with CloudWatch logging

## Deployment

### Prerequisites

- [Serverless Framework](https://www.serverless.com/)
- AWS CLI configured with appropriate permissions
- An EFS access point configured for Lambda
- S3 buckets for documents and profiles

### Installation

1. Install dependencies:

```bash
npm install -g serverless
npm install
pip install -r requirements.txt
```

2. Update the serverless.yml file with your EFS and VPC configuration:

```yaml
custom:
  efsAccessPoint:
    dev: <your-dev-efs-access-point-arn>
    test: <your-test-efs-access-point-arn>
    prod: <your-prod-efs-access-point-arn>
  
  vpc:
    dev:
      securityGroupId: <your-dev-security-group-id>
      subnetIds:
        - <your-dev-subnet-id>
    test:
      securityGroupId: <your-test-security-group-id>
      subnetIds:
        - <your-test-subnet-id>
    prod:
      securityGroupId: <your-prod-security-group-id>
      subnetIds:
        - <your-prod-subnet-id>
```

3. Deploy:

```bash
serverless deploy --stage dev
```

## Usage

### Lambda API

The Lambda function accepts the following event structure:

```json
{
  "delegate_profile": "<profile-data-or-s3-key>",
  "document_type": "position_paper|speech|resolution",
  "topic": "Optional topic override",
  "committee": "Optional committee override",
  "country": "Optional country override",
  "additional_params": {},
  "profile_s3_bucket": "If delegate_profile is an S3 key",
  "output_s3_bucket": "Bucket for output",
  "model_name": "Optional model override",
  "use_gpu": false,
  "max_length": 2048,
  "temperature": 0.7,
  "top_p": 0.9,
  "seed": 42,
  "test_mode": false
}
```

### Local Testing

Test AWS permissions:

```bash
python multi_document_generator.py test-aws --bucket your-bucket-name
```

Test with fixtures (no model loading):

```bash
python multi_document_generator.py test-fixtures --output-bucket your-bucket --type position_paper
```

Generate a document:

```bash
python multi_document_generator.py generate --profile path/to/profile.json --output-bucket your-bucket --type position_paper --test-mode
```

## Testing Environment

For testing without loading large models:

1. Set the `test_mode` parameter to `true`
2. Use the `test-fixtures` command for testing with mock data
3. The Lambda environment includes a `generate-test` endpoint that uses smaller models

## Security

- S3 permissions are verified before operations
- Full CloudWatch logging for monitoring and debugging
- Proper error handling with appropriate HTTP response codes

## Resource Requirements

- Lambda: 10GB memory, 15-minute timeout
- EFS: At least 10GB storage for model weights
- S3: Storage for input profiles and output documents

## Multi-Document Generator API

This API generates different types of UN documents (position papers, speeches, and resolutions) that mimic a delegate's style. It can be deployed as either a Flask application or an AWS Lambda function accessible through API Gateway.

## Features

- Generate position papers, speeches, and resolutions
- Support for custom delegate profiles
- Style mimicking based on linguistic patterns
- Local and AWS deployment options
- Comprehensive testing suite

## Setup

### Local Development

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Configure environment variables:

```bash
# Optional: create a .env file
cp example.env .env
```

3. Run the development server:

```bash
python multi_document_api.py
```

The server will be available at `http://localhost:5001`.

### AWS Deployment

1. Install Serverless Framework:

```bash
npm install -g serverless
```

2. Install plugins:

```bash
npm install --save-dev serverless-python-requirements serverless-dotenv-plugin
```

3. Deploy to AWS:

```bash
# Deploy to dev stage
serverless deploy

# Deploy to production stage
serverless deploy --stage prod

# Deploy with X-Ray tracing enabled
serverless deploy --xray true
```

## Configuration

### Environment Variables

- `DOCUMENT_GENERATOR_S3_BUCKET`: S3 bucket name for storing generated documents
- `DOCUMENT_GENERATOR_S3_REGION`: AWS region for S3 bucket (default: 'us-east-1')
- `USE_S3`: Set to 'true' to use S3 for storage, 'false' for local storage
- `TEST_ENV`: Set to 'true' for testing mode
- `XRAY_ENABLED`: Set to 'true' to enable AWS X-Ray tracing

### config.py

The `config.py` file contains configuration for:

- Generator options (model name, output directory, etc.)
- API settings (host, port, upload folder, etc.)

## API Endpoints

### Generate Document

```
POST /generate
```

Generates a document based on a delegate profile uploaded as a file.

**Request:**
- Form data with profile file and document parameters

**Response:**
- JSON with generation results and output file path/URL

### Generate Document from Data

```
POST /generate-from-data
```

Generates a document from JSON data.

**Request:**
- JSON with profile data and document parameters

**Response:**
- JSON with generation results and output file path/URL

### Download Document

```
GET /download/{filename}
```

Downloads a generated document.

**Response:**
- File for download or redirect to S3 presigned URL

### Compare Documents

```
POST /compare
```

Compares an original document with a generated one.

**Request:**
- JSON with paths to original and generated documents

**Response:**
- JSON with comparison results

### Document Types

```
GET /document-types
```

Returns available document types and their parameters.

**Response:**
- JSON with document type descriptions and parameters

### Health Check

```
GET /health
```

Checks API health.

**Response:**
- JSON with health status

## Testing

Run the tests:

```bash
python -m unittest multi_document_api_tests.py
```

## AWS Integration

This application supports:

- Deployment as AWS Lambda function
- API Gateway integration
- S3 storage for files
- X-Ray tracing
- IAM roles for S3 access

## Example Usage

### Generate a position paper

```bash
# Using curl with local server
curl -X POST \
  http://localhost:5001/generate-from-data \
  -H 'Content-Type: application/json' \
  -d '{
    "document_type": "position_paper",
    "topic": "Nuclear Disarmament",
    "committee": "Security Council",
    "country": "United States",
    "profile": {
      "delegateProfile": {
        "metadata": {
          "committees": ["Security Council"],
          "topics": ["Nuclear Disarmament"],
          "roles": ["United States"]
        },
        "country": "United States",
        "committee": "Security Council"
      }
    }
  }'
```

## License

[MIT License](LICENSE) 