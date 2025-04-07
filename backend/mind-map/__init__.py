import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ensure the indices directory exists
indices_dir = Path(__file__).parent / "indices"
os.makedirs(indices_dir, exist_ok=True)

# Export the API blueprint
from .api import mind_map_blueprint

__all__ = ['mind_map_blueprint']

logger.info("Mind Map module initialized") 