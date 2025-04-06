import json
import os
import argparse

class ConfigHandler:
    """
    Handler for managing MUN analysis configuration files
    """
    
    def __init__(self, config_dir="configs"):
        """
        Initialize the config handler
        
        Args:
            config_dir (str): Directory to store configuration files
        """
        self.config_dir = config_dir
        os.makedirs(config_dir, exist_ok=True)
    
    def create_config(self, topic, country, committee, document_type="position_paper", output_format="all"):
        """
        Create a new configuration file
        
        Args:
            topic (str): The topic of the MUN session
            country (str): The country assignment
            committee (str): The committee name
            document_type (str): Type of document being analyzed
            output_format (str): Output format (text, visual, or all)
            
        Returns:
            str: Path to the created config file
        """
        config = {
            "topic": topic,
            "country": country,
            "committee": committee,
            "document_type": document_type,
            "output_format": output_format,
            "analysis_settings": {
                "perplexity_weight": 0.25,
                "burstiness_weight": 0.25,
                "keywords_weight": 0.3,
                "sentiment_weight": 0.2
            }
        }
        
        # Create a unique filename
        filename = f"{country.lower().replace(' ', '_')}_{committee.lower().replace(' ', '_')}.json"
        file_path = os.path.join(self.config_dir, filename)
        
        # Save the config
        with open(file_path, 'w') as f:
            json.dump(config, f, indent=4)
        
        print(f"Created configuration file: {file_path}")
        return file_path
    
    def load_config(self, file_path):
        """
        Load a configuration file
        
        Args:
            file_path (str): Path to the configuration file
            
        Returns:
            dict: Configuration data
        """
        try:
            with open(file_path, 'r') as f:
                config = json.load(f)
            return config
        except Exception as e:
            print(f"Error loading configuration: {e}")
            return None
    
    def list_configs(self):
        """
        List all available configuration files
        
        Returns:
            list: List of configuration files
        """
        if not os.path.exists(self.config_dir):
            return []
        
        return [f for f in os.listdir(self.config_dir) if f.endswith('.json')]

if __name__ == "__main__":
    # Command line interface for creating configuration files
    parser = argparse.ArgumentParser(description="Create a configuration file for MUN analysis")
    parser.add_argument("--topic", required=True, help="Topic of the MUN session")
    parser.add_argument("--country", required=True, help="Country assignment")
    parser.add_argument("--committee", required=True, help="Committee name")
    parser.add_argument("--document-type", default="position_paper", 
                        choices=["position_paper", "resolution", "speech", "policy_memo"],
                        help="Type of document being analyzed")
    parser.add_argument("--output-format", default="all", 
                        choices=["text", "visual", "all"],
                        help="Output format")
    
    args = parser.parse_args()
    
    handler = ConfigHandler()
    config_path = handler.create_config(
        args.topic, 
        args.country, 
        args.committee,
        args.document_type,
        args.output_format
    )
    
    print(f"Configuration file created at {config_path}")
