import argparse
import os
import sys
import json
import logging
import tempfile
import boto3
from botocore.exceptions import ClientError
from mun_delegate_analyzer import MUNDelegateAnalyzer
from config_handler import ConfigHandler
from typing import Dict, Any, Optional, Union, List, Tuple

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
ENV_S3_BUCKET = os.environ.get("MUN_ANALYSIS_S3_BUCKET")
ENV_S3_REGION = os.environ.get("MUN_ANALYSIS_S3_REGION", "us-east-1")
ENV_TEST_MODE = os.environ.get("TEST_ENV", "false").lower() == "true"
ENV_STORAGE_MODE = os.environ.get("STORAGE_MODE", "local").lower()  # "local" or "s3"

# Check if running in Lambda environment
IS_LAMBDA = os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None

class S3Handler:
    """Handler for S3 operations"""
    
    def __init__(self, bucket_name: Optional[str] = None, region: str = "us-east-1"):
        """Initialize S3 handler"""
        self.bucket_name = bucket_name or ENV_S3_BUCKET
        self.region = region or ENV_S3_REGION
        
        if not self.bucket_name:
            raise ValueError("S3 bucket name must be provided either directly or through MUN_ANALYSIS_S3_BUCKET environment variable")
        
        try:
            self.s3_client = boto3.client('s3', region_name=self.region)
            # Verify IAM permissions by checking if we can list the bucket
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Successfully connected to S3 bucket: {self.bucket_name}")
        except (ClientError, Exception) as e:
            if isinstance(e, ClientError) and e.response['Error']['Code'] == '403':
                logger.error(f"Permission denied to access S3 bucket: {self.bucket_name}")
            else:
                logger.error(f"Failed to initialize S3 client: {str(e)}")
            raise
    
    def download_file(self, s3_key: str, local_path: str) -> bool:
        """Download a file from S3 to a local path"""
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            self.s3_client.download_file(self.bucket_name, s3_key, local_path)
            return True
        except ClientError as e:
            logger.error(f"Error downloading file from S3: {str(e)}")
            return False
    
    def upload_file(self, local_path: str, s3_key: str) -> bool:
        """Upload a file from a local path to S3"""
        try:
            self.s3_client.upload_file(local_path, self.bucket_name, s3_key)
            return True
        except ClientError as e:
            logger.error(f"Error uploading file to S3: {str(e)}")
            return False
    
    def list_objects(self, prefix: str) -> List[str]:
        """List objects in S3 with the given prefix"""
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
            if 'Contents' in response:
                return [obj['Key'] for obj in response['Contents']]
            return []
        except ClientError as e:
            logger.error(f"Error listing objects in S3: {str(e)}")
            return []
    
    def object_exists(self, s3_key: str) -> bool:
        """Check if an object exists in S3"""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            logger.error(f"Error checking if object exists in S3: {str(e)}")
            raise

def generate_mock_event(command: str, **kwargs) -> Dict[str, Any]:
    """Generate a mock Lambda event for testing"""
    event = {
        "requestContext": {
            "http": {
                "method": "POST",
                "path": f"/api/{command}"
            }
        },
        "body": json.dumps(kwargs)
    }
    return event

def process_results(results: Dict[str, Any], output_dir: str, use_s3: bool = False) -> Dict[str, Any]:
    """Process analysis results and prepare response"""
    if not results:
        return {"success": False, "message": "Analysis failed"}
    
    # For S3, convert local paths to S3 URIs
    if use_s3 and ENV_S3_BUCKET:
        s3_output_prefix = f"results/{os.path.basename(output_dir)}/"
        output_uris = {}
        
        # Upload local results to S3 if needed
        if os.path.exists(output_dir):
            s3_handler = S3Handler()
            for root, _, files in os.walk(output_dir):
                for file in files:
                    local_path = os.path.join(root, file)
                    rel_path = os.path.relpath(local_path, output_dir)
                    s3_key = f"{s3_output_prefix}{rel_path}"
                    
                    if s3_handler.upload_file(local_path, s3_key):
                        output_uris[os.path.basename(file)] = f"s3://{ENV_S3_BUCKET}/{s3_key}"
            
            results["output_files"] = output_uris
            results["s3_prefix"] = f"s3://{ENV_S3_BUCKET}/{s3_output_prefix}"
    
    # Extract top approaches for cleaner response
    if "similarity_scores" in results:
        approaches_sorted = sorted(
            results["similarity_scores"].keys(), 
            key=lambda x: results["similarity_scores"][x], 
            reverse=True
        )
        
        top_approaches = []
        for i, approach in enumerate(approaches_sorted[:3], 1):
            score = results["similarity_scores"][approach]
            approach_name = ' '.join(approach.split('_')).title()
            top_approaches.append({
                "rank": i,
                "approach": approach_name,
                "score": round(score, 4)
            })
        
        results["top_approaches"] = top_approaches
    
    return {
        "success": True,
        "message": "Analysis completed successfully",
        "results": results
    }

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler function
    
    Args:
        event: Lambda event object
        context: Lambda context object
        
    Returns:
        dict: Response object
    """
    logger.info("Received event: %s", json.dumps(event))
    
    # Check for test mode
    is_test = ENV_TEST_MODE or event.get("isTest", False)
    use_s3 = not is_test and ENV_STORAGE_MODE == "s3"
    
    # Extract request information
    method = event.get("requestContext", {}).get("http", {}).get("method", "")
    path = event.get("requestContext", {}).get("http", {}).get("path", "")
    
    # Parse command from path or use default
    command = path.split("/")[-1] if path else "analyze"
    
    # Parse body
    body = {}
    if "body" in event:
        try:
            body = json.loads(event["body"])
        except (json.JSONDecodeError, TypeError):
            body = event.get("body", {}) if isinstance(event.get("body"), dict) else {}
    
    # Create temp directory for file operations if needed
    with tempfile.TemporaryDirectory() as temp_dir:
        # Setup config and output directories
        config_dir = os.path.join(temp_dir, "configs")
        output_dir = os.path.join(temp_dir, "results")
        os.makedirs(config_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        
        # Setup S3 handler if needed
        s3_handler = None
        if use_s3:
            try:
                s3_handler = S3Handler()
            except Exception as e:
                logger.error(f"Failed to initialize S3: {str(e)}")
                return {
                    "statusCode": 500,
                    "body": json.dumps({
                        "success": False, 
                        "message": f"S3 initialization error: {str(e)}"
                    })
                }
        
        # Create config handler with appropriate directory
        config_handler = ConfigHandler(config_dir=config_dir)
        
        # Handle different commands
        if command == "config":
            # Create configuration
            try:
                topic = body.get("topic")
                country = body.get("country")
                committee = body.get("committee")
                document_type = body.get("document_type", "position_paper")
                output_format = body.get("output_format", "all")
                
                if not all([topic, country, committee]):
                    return {
                        "statusCode": 400,
                        "body": json.dumps({
                            "success": False, 
                            "message": "Missing required parameters: topic, country, and committee are required"
                        })
                    }
                
                config_path = config_handler.create_config(
                    topic, country, committee, document_type, output_format
                )
                
                # Upload to S3 if using S3
                if use_s3 and s3_handler:
                    s3_key = f"configs/{os.path.basename(config_path)}"
                    s3_handler.upload_file(config_path, s3_key)
                    
                    return {
                        "statusCode": 200,
                        "body": json.dumps({
                            "success": True,
                            "message": f"Configuration created successfully",
                            "config_path": f"s3://{ENV_S3_BUCKET}/{s3_key}"
                        })
                    }
                
                return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "success": True,
                        "message": f"Configuration created successfully",
                        "config_path": config_path
                    })
                }
                
            except Exception as e:
                logger.error(f"Error creating configuration: {str(e)}")
                return {
                    "statusCode": 500,
                    "body": json.dumps({
                        "success": False,
                        "message": f"Error creating configuration: {str(e)}"
                    })
                }
                
        elif command == "list":
            # List available configurations
            try:
                if use_s3 and s3_handler:
                    configs = s3_handler.list_objects("configs/")
                    configs = [os.path.basename(c) for c in configs if c.endswith('.json')]
                else:
                    configs = config_handler.list_configs()
                
                return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "success": True,
                        "configs": configs
                    })
                }
            except Exception as e:
                logger.error(f"Error listing configurations: {str(e)}")
                return {
                    "statusCode": 500,
                    "body": json.dumps({
                        "success": False,
                        "message": f"Error listing configurations: {str(e)}"
                    })
                }
        
        elif command == "analyze":
            # Analyze delegate paper
            try:
                config_path = body.get("config")
                paper_path = body.get("paper")
                output_dir_name = body.get("output_dir", "results")
                
                if not config_path or not paper_path:
                    return {
                        "statusCode": 400,
                        "body": json.dumps({
                            "success": False,
                            "message": "Missing required parameters: config and paper are required"
                        })
                    }
                
                # Handle S3 paths
                local_config_path = config_path
                local_paper_path = paper_path
                
                # If using S3, download files to temp directory
                if use_s3 and s3_handler:
                    if config_path.startswith("s3://"):
                        s3_config_key = config_path.replace(f"s3://{ENV_S3_BUCKET}/", "")
                        local_config_path = os.path.join(config_dir, os.path.basename(s3_config_key))
                        s3_handler.download_file(s3_config_key, local_config_path)
                    
                    if paper_path.startswith("s3://"):
                        s3_paper_key = paper_path.replace(f"s3://{ENV_S3_BUCKET}/", "")
                        local_paper_path = os.path.join(temp_dir, os.path.basename(s3_paper_key))
                        s3_handler.download_file(s3_paper_key, local_paper_path)
                
                # Set up output directory
                analysis_output_dir = os.path.join(output_dir, output_dir_name)
                os.makedirs(analysis_output_dir, exist_ok=True)
                
                # Load configuration
                config = config_handler.load_config(local_config_path)
                if not config:
                    return {
                        "statusCode": 400,
                        "body": json.dumps({
                            "success": False,
                            "message": f"Failed to load configuration from {config_path}"
                        })
                    }
                
                # Create analyzer and run analysis
                analyzer = MUNDelegateAnalyzer(local_config_path)
                results = analyzer.run_analysis(local_paper_path, analysis_output_dir)
                
                # Process results
                response_data = process_results(results, analysis_output_dir, use_s3)
                
                return {
                    "statusCode": 200,
                    "body": json.dumps(response_data)
                }
                
            except Exception as e:
                logger.error(f"Error analyzing paper: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                return {
                    "statusCode": 500,
                    "body": json.dumps({
                        "success": False,
                        "message": f"Error analyzing paper: {str(e)}"
                    })
                }
        
        else:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "success": False,
                    "message": f"Unknown command: {command}"
                })
            }

def main():
    """
    Main entry point for the MUN Delegate Analysis Tool when running locally
    """
    parser = argparse.ArgumentParser(description="Analyze MUN delegate position papers")
    
    # Define command-line arguments
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Create config command
    config_parser = subparsers.add_parser("config", help="Create a new configuration")
    config_parser.add_argument("--topic", required=True, help="Topic of the MUN session")
    config_parser.add_argument("--country", required=True, help="Country assignment")
    config_parser.add_argument("--committee", required=True, help="Committee name")
    config_parser.add_argument("--document-type", default="position_paper", 
                        choices=["position_paper", "resolution", "speech", "policy_memo"],
                        help="Type of document being analyzed")
    config_parser.add_argument("--output-format", default="all", 
                        choices=["text", "visual", "all"],
                        help="Output format")
    
    # List configs command
    list_parser = subparsers.add_parser("list", help="List available configurations")
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a delegate paper")
    analyze_parser.add_argument("--config", required=True, help="Path to configuration file")
    analyze_parser.add_argument("--paper", required=True, help="Path to delegate paper")
    analyze_parser.add_argument("--output-dir", default="results", help="Directory to save results")
    
    # Interactive mode command
    interactive_parser = subparsers.add_parser("interactive", help="Run in interactive mode")
    
    # Testing command
    test_parser = subparsers.add_parser("test", help="Test Lambda function with mock event")
    test_parser.add_argument("--command", required=True, choices=["config", "list", "analyze"],
                         help="Command to test")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Create config handler
    config_handler = ConfigHandler()
    
    # Handle local test mode
    if args.command == "test":
        os.environ["TEST_ENV"] = "true"
        print(f"Testing Lambda function with mock event for command: {args.command}")
        
        # Generate mock event based on command
        mock_event = None
    if args.command == "config":
            mock_event = generate_mock_event(
                "config",
                topic="Climate Change",
                country="Sweden",
                committee="UN Environment Programme",
                document_type="position_paper"
            )
        elif args.command == "list":
            mock_event = generate_mock_event("list")
        elif args.command == "analyze":
            mock_event = generate_mock_event(
                "analyze",
                config="configs/sweden_un_environment_programme.json",
                paper="samples/sweden_climate_paper.txt",
                output_dir="test_results"
            )
        
        # Call lambda handler with mock event
        response = lambda_handler(mock_event, None)
        print(f"Lambda response: {json.dumps(response, indent=2)}")
        return
    
    # Handle interactive mode locally
    elif args.command == "interactive":
        run_interactive_mode(config_handler)
        return
    
    # Handle regular CLI commands
    elif args.command == "config":
        config_handler.create_config(
            args.topic,
            args.country,
            args.committee,
            args.document_type,
            args.output_format
        )
    
    elif args.command == "list":
        configs = config_handler.list_configs()
        if configs:
            print("\nAvailable configurations:")
            for i, config_file in enumerate(configs, 1):
                print(f"{i}. {config_file}")
            print()
        else:
            print("No configuration files found.")
    
    elif args.command == "analyze":
        # Load configuration
        config = config_handler.load_config(args.config)
        if not config:
            print(f"Failed to load configuration from {args.config}")
            return
        
        # Create analyzer
        analyzer = MUNDelegateAnalyzer(args.config)
        
        # Run analysis
        results = analyzer.run_analysis(args.paper, args.output_dir)
        
        if results:
            print("\nAnalysis completed successfully!")
            print(f"Results saved to {args.output_dir}")
            
            # Print top approaches
            print("\nTop approaches identified:")
            approaches_sorted = sorted(
                results["similarity_scores"].keys(), 
                key=lambda x: results["similarity_scores"][x], 
                reverse=True
            )
            
            for i, approach in enumerate(approaches_sorted[:3], 1):
                score = results["similarity_scores"][approach]
                approach_name = ' '.join(approach.split('_')).title()
                print(f"{i}. {approach_name}: {score:.4f}")
    
    else:
        parser.print_help()

def run_interactive_mode(config_handler):
    """
    Run the tool in interactive mode with a command-line interface
    
    Args:
        config_handler (ConfigHandler): Configuration handler instance
    """
    print("\n============================")
    print("MUN Delegate Analysis Tool")
    print("============================\n")
    
    print("This tool analyzes MUN position papers to determine the delegate's approach.")
    
    # Select or create configuration
    print("\nConfiguration:")
    print("1. Use existing configuration")
    print("2. Create new configuration")
    choice = input("Select an option (1-2): ")
    
    config_path = None
    
    if choice == "1":
        configs = config_handler.list_configs()
        if not configs:
            print("No configurations found. Creating a new one.")
            choice = "2"
        else:
            print("\nAvailable configurations:")
            for i, config_file in enumerate(configs, 1):
                print(f"{i}. {config_file}")
            
            idx = int(input("\nSelect a configuration number: ")) - 1
            if 0 <= idx < len(configs):
                config_path = os.path.join(config_handler.config_dir, configs[idx])
            else:
                print("Invalid selection. Creating a new configuration.")
                choice = "2"
    
    if choice == "2":
        topic = input("Enter topic: ")
        country = input("Enter country: ")
        committee = input("Enter committee: ")
        
        print("\nDocument types:")
        print("1. Position paper")
        print("2. Resolution")
        print("3. Speech")
        print("4. Policy memo")
        doc_choice = input("Select document type (1-4, default 1): ") or "1"
        
        doc_types = ["position_paper", "resolution", "speech", "policy_memo"]
        document_type = doc_types[int(doc_choice) - 1]
        
        config_path = config_handler.create_config(topic, country, committee, document_type)
    
    # Get delegate paper path
    paper_path = input("\nEnter path to delegate paper file: ")
    while not os.path.exists(paper_path):
        print("File not found.")
        paper_path = input("Enter path to delegate paper file: ")
    
    # Get output directory
    output_dir = input("Enter output directory (default: results): ") or "results"
    
    # Create analyzer and run analysis
    analyzer = MUNDelegateAnalyzer(config_path)
    results = analyzer.run_analysis(paper_path, output_dir)
    
    if results:
        print("\nAnalysis completed successfully!")
        print(f"Results saved to {output_dir}")
        
        # Print top approaches
        print("\nTop approaches identified:")
        approaches_sorted = sorted(
            results["similarity_scores"].keys(), 
            key=lambda x: results["similarity_scores"][x], 
            reverse=True
        )
        
        for i, approach in enumerate(approaches_sorted[:3], 1):
            score = results["similarity_scores"][approach]
            approach_name = ' '.join(approach.split('_')).title()
            print(f"{i}. {approach_name}: {score:.4f}")

if __name__ == "__main__":
    # Determine whether to use Lambda handler or CLI
    if IS_LAMBDA:
        # When running in Lambda, the handler is invoked by AWS
        pass
    else:
        # When running locally, invoke the main function
    main()