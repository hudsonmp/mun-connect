import streamlit as st
import os
import json
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from mun_delegate_analyzer import MUNDelegateAnalyzer
from config_handler import ConfigHandler
import tempfile
import boto3
import uuid
import logging
import time
import base64
from io import BytesIO
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional, Union, List, Tuple
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("mun-web-interface")

# Environment variables and constants
ENV_S3_BUCKET = os.environ.get("MUN_ANALYSIS_S3_BUCKET")
ENV_S3_REGION = os.environ.get("MUN_ANALYSIS_S3_REGION", "us-east-1")
ENV_TEST_MODE = os.environ.get("TEST_ENV", "false").lower() == "true"
ENV_STORAGE_MODE = os.environ.get("STORAGE_MODE", "local").lower()  # "local" or "s3"
ENV_AUTH_REQUIRED = os.environ.get("AUTH_REQUIRED", "false").lower() == "true"
ENV_COGNITO_USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID")
ENV_COGNITO_APP_CLIENT_ID = os.environ.get("COGNITO_APP_CLIENT_ID")
ENV_COGNITO_REGION = os.environ.get("COGNITO_REGION", ENV_S3_REGION)
ENV_CF_DOMAIN = os.environ.get("CLOUDFRONT_DOMAIN")
ENV_ALB_PATH_PREFIX = os.environ.get("ALB_PATH_PREFIX", "")
TEMP_DIR = tempfile.mkdtemp()

# Maximum retries for AWS operations
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

# Check if running in AWS environment
IS_AWS = any([
    os.environ.get("AWS_EXECUTION_ENV") is not None,
    os.environ.get("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI") is not None,
    os.environ.get("ECS_CONTAINER_METADATA_URI") is not None,
    os.environ.get("ELASTIC_BEANSTALK_ENVIRONMENT_ID") is not None
])

class S3Handler:
    """Handler for S3 operations"""
    
    def __init__(self, bucket_name: Optional[str] = None, region: str = "us-east-1"):
        """Initialize S3 handler"""
        self.bucket_name = bucket_name or ENV_S3_BUCKET
        self.region = region or ENV_S3_REGION
        
        if not self.bucket_name and not ENV_TEST_MODE:
            raise ValueError("S3 bucket name must be provided either directly or through MUN_ANALYSIS_S3_BUCKET environment variable")
        
        self.s3_client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize S3 client with retries"""
        # For test mode, use mock client
        if ENV_TEST_MODE:
            self.s3_client = MockS3Client()
            logger.info("Initialized mock S3 client for testing")
            return
            
        for attempt in range(MAX_RETRIES):
            try:
                self.s3_client = boto3.client('s3', region_name=self.region)
                # Verify IAM permissions by checking if we can list the bucket
                if self.bucket_name:
                    self.s3_client.head_bucket(Bucket=self.bucket_name)
                    logger.info(f"Successfully connected to S3 bucket: {self.bucket_name}")
                return
            except (ClientError, Exception) as e:
                if isinstance(e, ClientError) and e.response['Error']['Code'] == '403':
                    logger.error(f"Permission denied to access S3 bucket: {self.bucket_name}")
                    raise
                elif attempt < MAX_RETRIES - 1:
                    logger.warning(f"Failed to initialize S3 client (attempt {attempt+1}/{MAX_RETRIES}): {str(e)}")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error(f"Failed to initialize S3 client after {MAX_RETRIES} attempts: {str(e)}")
                    raise
    
    def upload_file(self, local_path: str, s3_key: str) -> str:
        """Upload a file from a local path to S3 and return the URL"""
        if ENV_TEST_MODE:
            logger.info(f"Mock uploading file to S3: {s3_key}")
            return f"s3://{self.bucket_name}/{s3_key}"
            
        for attempt in range(MAX_RETRIES):
            try:
                self.s3_client.upload_file(local_path, self.bucket_name, s3_key)
                url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
                
                # Use CloudFront URL if available
                if ENV_CF_DOMAIN:
                    url = f"https://{ENV_CF_DOMAIN}/{s3_key}"
                    
                return url
            except ClientError as e:
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Error uploading file to S3 (attempt {attempt+1}/{MAX_RETRIES}): {str(e)}")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error(f"Error uploading file to S3 after {MAX_RETRIES} attempts: {str(e)}")
                    raise
    
    def upload_fileobj(self, file_obj, s3_key: str, content_type: Optional[str] = None) -> str:
        """Upload a file object to S3 and return the URL"""
        if ENV_TEST_MODE:
            logger.info(f"Mock uploading file object to S3: {s3_key}")
            return f"s3://{self.bucket_name}/{s3_key}"
            
        for attempt in range(MAX_RETRIES):
            try:
                extra_args = {}
                if content_type:
                    extra_args['ContentType'] = content_type
                
                self.s3_client.upload_fileobj(file_obj, self.bucket_name, s3_key, ExtraArgs=extra_args)
                url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
                
                # Use CloudFront URL if available
                if ENV_CF_DOMAIN:
                    url = f"https://{ENV_CF_DOMAIN}/{s3_key}"
                    
                return url
            except ClientError as e:
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Error uploading file object to S3 (attempt {attempt+1}/{MAX_RETRIES}): {str(e)}")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error(f"Error uploading file object to S3 after {MAX_RETRIES} attempts: {str(e)}")
                    raise
    
    def download_fileobj(self, s3_key: str) -> BytesIO:
        """Download a file from S3 to a file-like object"""
        if ENV_TEST_MODE:
            # Create mock data for testing
            logger.info(f"Mock downloading file from S3: {s3_key}")
            mock_data = "This is mock data for testing purposes."
            return BytesIO(mock_data.encode('utf-8'))
            
        file_obj = BytesIO()
        for attempt in range(MAX_RETRIES):
            try:
                self.s3_client.download_fileobj(self.bucket_name, s3_key, file_obj)
                file_obj.seek(0)  # Reset to the beginning of the file
                return file_obj
            except ClientError as e:
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Error downloading file from S3 (attempt {attempt+1}/{MAX_RETRIES}): {str(e)}")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error(f"Error downloading file from S3 after {MAX_RETRIES} attempts: {str(e)}")
                    raise

class CognitoHandler:
    """Handler for AWS Cognito operations"""
    
    def __init__(self, user_pool_id: Optional[str] = None, app_client_id: Optional[str] = None, region: str = "us-east-1"):
        """Initialize Cognito handler"""
        self.user_pool_id = user_pool_id or ENV_COGNITO_USER_POOL_ID
        self.app_client_id = app_client_id or ENV_COGNITO_APP_CLIENT_ID
        self.region = region or ENV_COGNITO_REGION
        
        if not all([self.user_pool_id, self.app_client_id]) and not ENV_TEST_MODE and ENV_AUTH_REQUIRED:
            raise ValueError("Cognito user pool ID and app client ID must be provided for authentication")
        
        self.cognito_idp = None
        if not ENV_TEST_MODE and ENV_AUTH_REQUIRED:
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Cognito IDP client"""
        for attempt in range(MAX_RETRIES):
            try:
                self.cognito_idp = boto3.client('cognito-idp', region_name=self.region)
                logger.info("Successfully initialized Cognito IDP client")
                return
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Failed to initialize Cognito client (attempt {attempt+1}/{MAX_RETRIES}): {str(e)}")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error(f"Failed to initialize Cognito client after {MAX_RETRIES} attempts: {str(e)}")
                    raise
    
    def authenticate(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate user with Cognito"""
        if ENV_TEST_MODE:
            # Mock authentication for testing
            if username == "test" and password == "test":
                return {
                    "authenticated": True,
                    "user": {
                        "username": "test",
                        "email": "test@example.com",
                        "sub": "test-user-id"
                    }
                }
            else:
                raise Exception("Invalid credentials")
        
        try:
            response = self.cognito_idp.initiate_auth(
                ClientId=self.app_client_id,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': username,
                    'PASSWORD': password
                }
            )
            
            # Get user info
            access_token = response['AuthenticationResult']['AccessToken']
            user_info = self.cognito_idp.get_user(AccessToken=access_token)
            
            return {
                "authenticated": True,
                "tokens": response['AuthenticationResult'],
                "user": {
                    "username": user_info['Username'],
                    "attributes": {attr['Name']: attr['Value'] for attr in user_info['UserAttributes']}
                }
            }
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise

class MockS3Client:
    """Mock S3 client for testing"""
    
    def __init__(self):
        """Initialize mock S3 client"""
        self.mock_files = {}
    
    def head_bucket(self, Bucket):
        """Mock head_bucket method"""
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}
    
    def upload_file(self, Filename, Bucket, Key, ExtraArgs=None):
        """Mock upload_file method"""
        with open(Filename, 'rb') as f:
            self.mock_files[Key] = f.read()
        return True
    
    def upload_fileobj(self, Fileobj, Bucket, Key, ExtraArgs=None):
        """Mock upload_fileobj method"""
        self.mock_files[Key] = Fileobj.read()
        return True
    
    def download_fileobj(self, Bucket, Key, Fileobj):
        """Mock download_fileobj method"""
        if Key in self.mock_files:
            Fileobj.write(self.mock_files[Key])
        else:
            # Generate mock data
            mock_data = f"Mock data for {Key}"
            Fileobj.write(mock_data.encode('utf-8'))
        return True

def generate_test_data():
    """Generate test data for the application"""
    # Sample configuration
    config = {
        "topic": "Climate Change Mitigation",
        "country": "Sweden",
        "committee": "UNEP",
        "document_type": "position_paper",
        "output_format": "all",
        "analysis_settings": {
            "perplexity_weight": 0.25,
            "burstiness_weight": 0.25,
            "keywords_weight": 0.3,
            "sentiment_weight": 0.2
        }
    }
    
    # Sample delegate paper
    paper = """
    Sweden is committed to addressing climate change through ambitious mitigation strategies. 
    As a leader in renewable energy, Sweden has already achieved significant emissions reductions
    while maintaining economic growth. Our country aims to become one of the first fossil-free
    welfare states in the world. We have implemented a carbon tax since 1991, which has proven
    effective in reducing emissions while promoting innovation.

    Sweden recognizes the interconnected nature of climate challenges and advocates for a 
    comprehensive approach that includes all nations. We support the Paris Agreement framework
    and believe that developed countries must take the lead in emissions reductions while 
    supporting developing nations. Regional cooperation, particularly within the European Union
    and Nordic countries, has been central to our strategy.

    Sweden proposes strengthening international cooperation through increased climate financing,
    technology transfer, and capacity building. We advocate for a carbon pricing mechanism at the
    global level, similar to our successful national carbon tax. Additionally, we support enhanced
    transparency and accountability measures to ensure all parties meet their commitments under
    the Paris Agreement. Sweden stands ready to share best practices and technological solutions
    that have enabled our progress toward a fossil-free economy.
    """
    
    return config, paper

def main():
    # Configure Streamlit for AWS environment if needed
    if IS_AWS and ENV_ALB_PATH_PREFIX:
        # Set base path for ALB path-based routing
        st.set_page_config(
            page_title="MUN Delegate Analysis Tool",
            page_icon="📝",
            layout="wide",
            initial_sidebar_state="expanded",
            menu_items=None
        )
    else:
        st.set_page_config(
            page_title="MUN Delegate Analysis Tool",
            page_icon="📝",
            layout="wide"
        )
    
    # Display environment banner in test mode
    if ENV_TEST_MODE:
        st.warning("⚠️ Running in TEST MODE - S3 operations are mocked", icon="⚠️")
    
    # Initialize session state variables
    for key in ["authenticated", "user", "results", "delegate_text", "config", "temp_files"]:
        if key not in st.session_state:
            st.session_state[key] = None if key != "temp_files" else []
    
    # Authentication handling
    if ENV_AUTH_REQUIRED and not ENV_TEST_MODE:
        if not st.session_state.authenticated:
            show_login_page()
            return
    else:
        # Skip authentication in test mode or when not required
        st.session_state.authenticated = True
        if ENV_TEST_MODE and st.session_state.user is None:
            st.session_state.user = {
                "username": "test_user",
                "email": "test@example.com"
            }
    
    # Main application
    st.title("MUN Delegate Analysis Tool")
    st.write("Analyze how MUN delegates approach their country assignments and topics")
    
    # Display user info if authenticated
    if st.session_state.authenticated and st.session_state.user:
        st.sidebar.info(f"Logged in as: {st.session_state.user.get('username', 'User')}")
        if st.sidebar.button("Logout"):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.experimental_rerun()
    
    # Create sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        
        config_method = st.radio(
            "Configuration Method",
            ["Create New", "Upload Config File"]
        )
        
        if config_method == "Create New":
            # Get configuration values
            topic = st.text_input("Topic", "Climate Change Mitigation")
            country = st.text_input("Country", "Sweden")
            committee = st.text_input("Committee", "UNEP")
            
            document_type = st.selectbox(
                "Document Type", 
                ["Position Paper", "Resolution", "Speech", "Policy Memo"]
            )
            
            # Convert to internal format
            doc_type_mapping = {
                "Position Paper": "position_paper",
                "Resolution": "resolution",
                "Speech": "speech",
                "Policy Memo": "policy_memo"
            }
            
            # Create config dict
            st.session_state.config = {
                "topic": topic,
                "country": country,
                "committee": committee,
                "document_type": doc_type_mapping[document_type],
                "output_format": "all",
                "analysis_settings": {
                    "perplexity_weight": 0.25,
                    "burstiness_weight": 0.25,
                    "keywords_weight": 0.3,
                    "sentiment_weight": 0.2
                }
            }
            
            # Show advanced settings
            if st.checkbox("Show Advanced Settings"):
                st.session_state.config["analysis_settings"]["perplexity_weight"] = st.slider(
                    "Perplexity Weight", 0.0, 1.0, 0.25, 0.05
                )
                st.session_state.config["analysis_settings"]["burstiness_weight"] = st.slider(
                    "Burstiness Weight", 0.0, 1.0, 0.25, 0.05
                )
                st.session_state.config["analysis_settings"]["keywords_weight"] = st.slider(
                    "Keywords Weight", 0.0, 1.0, 0.3, 0.05
                )
                st.session_state.config["analysis_settings"]["sentiment_weight"] = st.slider(
                    "Sentiment Weight", 0.0, 1.0, 0.2, 0.05
                )
                
                # Normalize weights to sum to 1
                total = sum(st.session_state.config["analysis_settings"].values())
                for key in st.session_state.config["analysis_settings"]:
                    st.session_state.config["analysis_settings"][key] /= total
        
        else:  # Upload Config File
            uploaded_config = st.file_uploader("Upload Config File", type="json")
            
            if uploaded_config:
                # Load configuration
                try:
                    st.session_state.config = json.load(uploaded_config)
                    st.success("Configuration loaded successfully!")
                except Exception as e:
                    st.error(f"Error loading configuration: {e}")
    
        # Quick Load Test Data button (only in test mode)
        if ENV_TEST_MODE:
            if st.button("Load Test Data"):
                test_config, test_paper = generate_test_data()
                st.session_state.config = test_config
                st.session_state.delegate_text = test_paper
                st.success("Test data loaded successfully!")
                st.experimental_rerun()
    
    # Main content area
    st.header("Delegate Paper Analysis")
    
    # Input methods
    input_method = st.radio(
        "Input Method",
        ["Upload File", "Paste Text"]
    )
    
    if input_method == "Upload File":
        uploaded_file = st.file_uploader("Upload Delegate Paper", type=["txt", "pdf", "docx"])
        
        if uploaded_file:
            # Process the uploaded file based on environment
            if ENV_STORAGE_MODE == "s3" and not ENV_TEST_MODE and ENV_S3_BUCKET:
                try:
                    # Upload to S3 and get the URL
                    s3_handler = S3Handler()
                    file_id = str(uuid.uuid4())
                    file_key = f"uploads/{file_id}/{uploaded_file.name}"
                    
                    # Upload the file to S3
                    s3_uri = s3_handler.upload_fileobj(
                        uploaded_file,
                        file_key,
                        content_type="text/plain"
                    )
                    
                    # Store the S3 key for cleanup later
                    if "s3_keys" not in st.session_state:
                        st.session_state.s3_keys = []
                    st.session_state.s3_keys.append(file_key)
                    
                    # Download content for preview and processing
                    uploaded_file.seek(0)
                    st.session_state.delegate_text = uploaded_file.read().decode('utf-8', errors='ignore')
                    
                    # Keep track of the S3 URI for analysis
                    st.session_state.delegate_file_uri = f"s3://{ENV_S3_BUCKET}/{file_key}"
                    
                except Exception as e:
                    st.error(f"Error uploading file to S3: {str(e)}")
                    st.session_state.delegate_text = None
            else:
                # Local processing for test or non-AWS mode
                # Save to temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
                    temp_file.write(uploaded_file.read())
                    temp_path = temp_file.name
                    
                    # Add to session state for cleanup
                    if "temp_files" not in st.session_state:
                        st.session_state.temp_files = []
                    st.session_state.temp_files.append(temp_path)
                
                # Read content
                try:
                    with open(temp_path, "r", encoding="utf-8", errors="ignore") as f:
                        st.session_state.delegate_text = f.read()
                    
                    # Keep track of the file path for analysis
                    st.session_state.delegate_file_uri = temp_path
                    
                except Exception as e:
                    st.error(f"Error reading file: {str(e)}")
                    st.session_state.delegate_text = None
            
            # Preview
            if st.session_state.delegate_text:
                with st.expander("Preview Delegate Paper"):
                    preview_text = st.session_state.delegate_text[:500]
                    if len(st.session_state.delegate_text) > 500:
                        preview_text += "..."
                    st.text(preview_text)
    
    else:  # Paste Text
        st.session_state.delegate_text = st.text_area(
            "Paste Delegate Paper",
            height=300,
            help="Paste the delegate's position paper here"
        )
        
        # For pasted text, we need to save it to a temporary file or S3
        if st.session_state.delegate_text:
            if ENV_STORAGE_MODE == "s3" and not ENV_TEST_MODE and ENV_S3_BUCKET:
                try:
                    # Upload to S3
                    s3_handler = S3Handler()
                    file_id = str(uuid.uuid4())
                    file_key = f"uploads/{file_id}/pasted_text.txt"
                    
                    # Create BytesIO object and upload
                    text_bytes = BytesIO(st.session_state.delegate_text.encode('utf-8'))
                    s3_uri = s3_handler.upload_fileobj(
                        text_bytes,
                        file_key,
                        content_type="text/plain"
                    )
                    
                    # Store the S3 key for cleanup later
                    if "s3_keys" not in st.session_state:
                        st.session_state.s3_keys = []
                    st.session_state.s3_keys.append(file_key)
                    
                    # Keep track of the S3 URI for analysis
                    st.session_state.delegate_file_uri = f"s3://{ENV_S3_BUCKET}/{file_key}"
                    
                except Exception as e:
                    st.error(f"Error uploading text to S3: {str(e)}")
            else:
                # Save to temporary file for local processing
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
                        temp_file.write(st.session_state.delegate_text.encode('utf-8'))
                        temp_path = temp_file.name
                    
                    # Add to session state for cleanup
                    if "temp_files" not in st.session_state:
                        st.session_state.temp_files = []
                    st.session_state.temp_files.append(temp_path)
                    
                    # Keep track of the file path for analysis
                    st.session_state.delegate_file_uri = temp_path
                    
                except Exception as e:
                    st.error(f"Error saving text to temporary file: {str(e)}")
    
    # Analysis button
    if st.button("Analyze Paper") and st.session_state.delegate_text and st.session_state.config:
        # Prepare for analysis based on environment
        if ENV_STORAGE_MODE == "s3" and not ENV_TEST_MODE and ENV_S3_BUCKET:
            try:
                # Upload config to S3
                s3_handler = S3Handler()
                file_id = str(uuid.uuid4())
                config_key = f"configs/{file_id}/config.json"
                
                # Create BytesIO object and upload
                config_bytes = BytesIO(json.dumps(st.session_state.config).encode('utf-8'))
                s3_uri = s3_handler.upload_fileobj(
                    config_bytes,
                    config_key,
                    content_type="application/json"
                )
                
                # Store the S3 key for cleanup later
                if "s3_keys" not in st.session_state:
                    st.session_state.s3_keys = []
                st.session_state.s3_keys.append(config_key)
                
                # S3 path for config
                config_path = f"s3://{ENV_S3_BUCKET}/{config_key}"
                
                # S3 path for output
                output_id = str(uuid.uuid4())
                output_dir = f"s3://{ENV_S3_BUCKET}/results/{output_id}"
                
                # Run analysis with S3 paths
                with st.spinner("Analyzing paper..."):
                    analyzer = MUNDelegateAnalyzer(config_path)
                    st.session_state.results = analyzer.run_analysis(
                        st.session_state.delegate_file_uri, 
                        output_dir
                    )
                
            except Exception as e:
                st.error(f"Error during analysis with S3: {str(e)}")
                return
        else:
            # Local processing for test or non-AWS mode
            try:
                # Create temporary files
                with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as config_file:
                    json.dump(st.session_state.config, config_file)
                    config_path = config_file.name
                
                # Add to session state for cleanup
                if "temp_files" not in st.session_state:
                    st.session_state.temp_files = []
                st.session_state.temp_files.append(config_path)
                
                # Create temporary output directory
                output_dir = tempfile.mkdtemp()
                st.session_state.temp_files.append(output_dir)
                
                # Run analysis
                with st.spinner("Analyzing paper..."):
                    analyzer = MUNDelegateAnalyzer(config_path)
                    st.session_state.results = analyzer.run_analysis(
                        st.session_state.delegate_file_uri, 
                        output_dir
                    )
                
            except Exception as e:
                st.error(f"Error during analysis: {str(e)}")
                import traceback
                st.error(traceback.format_exc())
                return
        
        st.success("Analysis completed!")
    
    # Display results
    if st.session_state.results:
        st.header("Analysis Results")
        
        # Get sorted approaches
        approaches_sorted = sorted(
            st.session_state.results["similarity_scores"].keys(), 
            key=lambda x: st.session_state.results["similarity_scores"][x], 
            reverse=True
        )
        
        scores_sorted = [st.session_state.results["similarity_scores"][a] for a in approaches_sorted]
        labels_sorted = [' '.join(a.split('_')).title() for a in approaches_sorted]
        
        # Create two columns
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Approach Similarity Ranking")
            
            # Create dataframe for the table
            df = pd.DataFrame({
                "Approach": labels_sorted,
                "Similarity Score": scores_sorted
            })
            
            # Display as table
            st.dataframe(df, use_container_width=True)
            
            # Top approach explanation
            st.subheader("Primary Approach")
            top_approach = approaches_sorted[0]
            top_approach_name = ' '.join(top_approach.split('_')).title()
            
            approach_descriptions = {
                "positive_achievements": """
                    This delegate focuses on highlighting successful policies and initiatives related to the topic.
                    They emphasize strengths, progress, and positive developments in their country's approach.
                    This approach tends to be optimistic and solution-oriented, showcasing what has worked well.
                """,
                "regional_cooperation": """
                    This delegate emphasizes multilateral solutions and coordination with neighboring countries.
                    They focus on regional bodies, treaties, and collaborative initiatives.
                    This approach views problems as shared challenges requiring joint action across borders.
                """,
                "economic_focus": """
                    This delegate concentrates on financial implications and economic development.
                    They emphasize market-based approaches, trade considerations, and economic policies.
                    This approach views the topic primarily through an economic lens.
                """,
                "humanitarian_concern": """
                    This delegate centers on human rights and the welfare of affected populations.
                    They emphasize humanitarian needs, vulnerable groups, and ethical considerations.
                    This approach prioritizes human impact over political or economic factors.
                """,
                "diplomatic_neutral": """
                    This delegate takes a balanced stance that acknowledges different perspectives.
                    They avoid strong positions and focus on finding common ground.
                    This approach aims to be diplomatic and non-confrontational.
                """,
                "historical_context": """
                    This delegate references past events and how they shape current situations.
                    They provide historical background and emphasize the evolution of the issue.
                    This approach sees current challenges as part of a historical continuum.
                """,
                "sovereignty_emphasis": """
                    This delegate focuses on national sovereignty and respect for borders.
                    They emphasize non-interference principles and the right to self-determination.
                    This approach prioritizes state autonomy in decision-making.
                """,
                "legal_framework": """
                    This delegate centers on treaties, international law, and legal precedents.
                    They emphasize legal obligations, enforcement mechanisms, and rule of law.
                    This approach views solutions through a legal and regulatory lens.
                """
            }
            
            st.write(approach_descriptions[top_approach])
            
            # Download links for outputs (if files exist)
            if "output_files" in st.session_state.results:
                st.subheader("Download Results")
                output_files = st.session_state.results["output_files"]
                
                for file_type, file_uri in output_files.items():
                    # Create download link based on URI type
                    if file_uri.startswith("s3://"):
                        # For S3 URI, generate a pre-signed URL or use CloudFront
                        if ENV_CF_DOMAIN:
                            bucket_name, s3_key = file_uri.replace("s3://", "").split("/", 1)
                            download_url = f"https://{ENV_CF_DOMAIN}/{s3_key}"
                            st.markdown(f"[Download {file_type}]({download_url})")
                        else:
                            # Generate pre-signed URL
                            try:
                                s3_client = boto3.client('s3', region_name=ENV_S3_REGION)
                                bucket_name, s3_key = file_uri.replace("s3://", "").split("/", 1)
                                download_url = s3_client.generate_presigned_url(
                                    'get_object',
                                    Params={'Bucket': bucket_name, 'Key': s3_key},
                                    ExpiresIn=3600  # URL valid for 1 hour
                                )
                                st.markdown(f"[Download {file_type}]({download_url})")
                            except Exception as e:
                                st.error(f"Error generating download link: {str(e)}")
                    else:
                        # For local file, read and create a download link
                        try:
                            with open(file_uri, "rb") as f:
                                file_bytes = f.read()
                                b64 = base64.b64encode(file_bytes).decode()
                                
                                # Determine MIME type
                                mime_type = "text/plain"
                                if file_uri.endswith(".png"):
                                    mime_type = "image/png"
                                elif file_uri.endswith(".json"):
                                    mime_type = "application/json"
                                
                                href = f'<a href="data:{mime_type};base64,{b64}" download="{os.path.basename(file_uri)}">Download {file_type}</a>'
                                st.markdown(href, unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"Error creating download link: {str(e)}")
        
        with col2:
            st.subheader("Approach Fingerprint")
            
            # Create radar chart or load from output
            if "output_files" in st.session_state.results and "radar_chart" in st.session_state.results["output_files"]:
                # Try to display the pre-generated chart
                radar_uri = st.session_state.results["output_files"]["radar_chart"]
                
                if radar_uri.startswith("s3://"):
                    try:
                        # Download from S3
                        bucket_name, s3_key = radar_uri.replace("s3://", "").split("/", 1)
                        s3_client = boto3.client('s3', region_name=ENV_S3_REGION)
                        image_obj = BytesIO()
                        s3_client.download_fileobj(bucket_name, s3_key, image_obj)
                        image_obj.seek(0)
                        st.image(image_obj, use_column_width=True)
                    except Exception as e:
                        st.error(f"Error loading radar chart: {str(e)}")
                        # Fall back to generating chart
                        generate_radar_chart(approaches_sorted, scores_sorted, labels_sorted)
                else:
                    # Load from local file
                    try:
                        st.image(radar_uri, use_column_width=True)
                    except Exception as e:
                        st.error(f"Error loading radar chart: {str(e)}")
                        # Fall back to generating chart
                        generate_radar_chart(approaches_sorted, scores_sorted, labels_sorted)
            else:
                # Generate the radar chart
                generate_radar_chart(approaches_sorted, scores_sorted, labels_sorted)
            
            # Linguistic Features
            st.subheader("Linguistic Features")
            
            # Create metrics
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.metric(
                    "Perplexity", 
                    f"{st.session_state.results['delegate_analysis']['perplexity']:.2f}",
                    help="Higher values indicate more complex, unpredictable text"
                )
                st.metric(
                    "Word Count", 
                    st.session_state.results['delegate_analysis']['word_count']
                )
            
            with col_b:
                st.metric(
                    "Burstiness", 
                    f"{st.session_state.results['delegate_analysis']['burstiness']:.2f}",
                    help="Higher values indicate more varied sentence structure"
                )
                
                # Check if sentiment is in the new format
                if "sentiment" in st.session_state.results:
                    sentiment_value = st.session_state.results["sentiment"]["compound"]
                else:
                    sentiment_value = st.session_state.results["delegate_analysis"]["sentiment"]["compound"]
                    
                st.metric(
                    "Sentiment", 
                    f"{sentiment_value:.2f}",
                    help="Range from -1 (negative) to 1 (positive)"
                )
        
        # Keywords section
        st.subheader("Key Terms")
        keywords = st.session_state.results['delegate_analysis']['keywords']
        
        # Create columns for keywords
        keyword_cols = st.columns(5)
        for i, kw in enumerate(keywords[:15]):
            col_idx = i % 5
            keyword_cols[col_idx].markdown(f"• {kw}")
    
    # Clean up temporary files on app shutdown
    # Note: This doesn't work perfectly in Streamlit's current architecture, but helps in some cases
    cleanup_temp_files()

def show_login_page():
    """Display the login page for Cognito authentication"""
    st.title("MUN Delegate Analysis Tool - Login")
    
    # Login form
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Login")
        
        if submit_button:
            try:
                # Initialize Cognito handler
                cognito_handler = CognitoHandler()
                
                # Authenticate
                auth_result = cognito_handler.authenticate(username, password)
                
                # Store authentication result
                st.session_state.authenticated = True
                st.session_state.user = auth_result.get("user")
                
                # Redirect to main app
                st.experimental_rerun()
                
            except Exception as e:
                st.error(f"Authentication failed: {str(e)}")
    
    # Link to sign up page (should redirect to Cognito hosted UI or your custom sign-up page)
    if ENV_COGNITO_APP_CLIENT_ID and not ENV_TEST_MODE:
        cognito_domain = os.environ.get("COGNITO_DOMAIN")
        if cognito_domain:
            signup_url = f"https://{cognito_domain}.auth.{ENV_COGNITO_REGION}.amazoncognito.com/signup?client_id={ENV_COGNITO_APP_CLIENT_ID}&response_type=code&redirect_uri={st.experimental_get_query_params().get('redirect_uri', [''])[0]}"
            st.markdown(f"Don't have an account? [Sign up]({signup_url})")
    
    # Test mode bypass
    if ENV_TEST_MODE:
        if st.button("Login with Test Account"):
            st.session_state.authenticated = True
            st.session_state.user = {
                "username": "test_user",
                "email": "test@example.com"
            }
            st.experimental_rerun()

def generate_radar_chart(approaches, scores, labels):
    """Generate and display a radar chart"""
    try:
        # Create radar chart
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))
        
        # Number of variables
        N = len(labels)
        
        # Angle for each axis
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        angles += angles[:1]  # Close the loop
        
        # Add values for each angle (plus close the loop)
        values = scores
        values += values[:1]
        
        # Draw the plot
        ax.plot(angles, values, linewidth=2, linestyle='solid')
        ax.fill(angles, values, alpha=0.25)
        
        # Set labels
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(labels, size=10)
        
        # Draw axis lines for each angle and label
        ax.set_rlabel_position(0)
        ax.set_yticks([0.25, 0.5, 0.75])
        ax.set_yticklabels(["0.25", "0.5", "0.75"], color="grey", size=8)
        ax.set_ylim(0, 1)
        
        plt.tight_layout()
        
        # Display chart
        st.pyplot(fig)
    except Exception as e:
        st.error(f"Error generating radar chart: {str(e)}")

def cleanup_temp_files():
    """Clean up temporary files"""
    # Clean up local temp files
    if "temp_files" in st.session_state and st.session_state.temp_files:
        for temp_file in st.session_state.temp_files:
            try:
                if os.path.isfile(temp_file):
                    os.unlink(temp_file)
                elif os.path.isdir(temp_file):
                    import shutil
                    shutil.rmtree(temp_file)
            except Exception as e:
                logger.warning(f"Error cleaning up temporary file {temp_file}: {str(e)}")
    
    # Clean up S3 files in production if needed
    # Note: We might want to keep these for some time before cleanup
    # if "s3_keys" in st.session_state and st.session_state.s3_keys and ENV_STORAGE_MODE == "s3" and not ENV_TEST_MODE:
    #     try:
    #         s3_client = boto3.client('s3', region_name=ENV_S3_REGION)
    #         for s3_key in st.session_state.s3_keys:
    #             s3_client.delete_object(Bucket=ENV_S3_BUCKET, Key=s3_key)
    #     except Exception as e:
    #         logger.warning(f"Error cleaning up S3 files: {str(e)}")

if __name__ == "__main__":
    main()
