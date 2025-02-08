from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional, List
import logging
import os

# Enhanced logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # Base Paths
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    MODEL_DIR: Path = DATA_DIR / "models"
    
    # LLM Configuration
    MODEL_PATH: str = str(MODEL_DIR / "llama-2-7b-chat.Q4_K_M.gguf")
    CONTEXT_LENGTH: int = 4096
    GPU_LAYERS: int = 0
    THREADS: int = 4
    MAX_TOKENS: int = 2048
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/superteam.db"
    
    # Vector Store
    VECTOR_STORE_PATH: str = str(DATA_DIR / "vector_store")
    
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_ADMIN_IDS: str
    
    # Optional Twitter Configuration
    TWITTER_API_KEY: Optional[str] = None
    TWITTER_API_SECRET: Optional[str] = None
    TWITTER_ACCESS_TOKEN: Optional[str] = None
    TWITTER_ACCESS_SECRET: Optional[str] = None
    
    # Security
    SECRET_KEY: str
    ADMIN_PASSWORD: str

    def __init__(self, **kwargs):
        """Initialize settings with validation"""
        super().__init__(**kwargs)
        # Log initial values
        logger.info(f"Initializing settings from: {os.path.abspath('.env')}")
        logger.info(f"Initial TELEGRAM_ADMIN_IDS value: {self.TELEGRAM_ADMIN_IDS}")

    @property
    def admin_ids(self) -> List[str]:
        """Get list of admin IDs with enhanced validation and logging"""
        try:
            # Log raw value
            logger.info(f"Processing TELEGRAM_ADMIN_IDS: {self.TELEGRAM_ADMIN_IDS}")
            print(f"Debug - Raw admin IDs value: {self.TELEGRAM_ADMIN_IDS}")  # Direct debug print

            if not self.TELEGRAM_ADMIN_IDS:
                logger.warning("No admin IDs configured")
                return []

            # Clean and validate each ID
            admin_list = []
            for id_str in str(self.TELEGRAM_ADMIN_IDS).split(','):
                cleaned_id = id_str.strip()
                # Validate ID format
                if cleaned_id.isdigit():
                    admin_list.append(cleaned_id)
                    logger.info(f"Added valid admin ID: {cleaned_id}")
                else:
                    logger.warning(f"Skipped invalid admin ID: {cleaned_id}")

            if not admin_list:
                logger.warning("No valid admin IDs found after validation")
            else:
                logger.info(f"Final validated admin IDs: {admin_list}")

            return admin_list

        except Exception as e:
            logger.error(f"Error processing admin IDs: {e}", exc_info=True)
            return []

    def validate_paths(self):
        """Validate and create necessary directories"""
        try:
            # Create required directories if they don't exist
            self.DATA_DIR.mkdir(parents=True, exist_ok=True)
            self.MODEL_DIR.mkdir(parents=True, exist_ok=True)
            Path(self.VECTOR_STORE_PATH).mkdir(parents=True, exist_ok=True)
            
            # Log directory creation
            logger.info(f"Data directory: {self.DATA_DIR}")
            logger.info(f"Model directory: {self.MODEL_DIR}")
            logger.info(f"Vector store directory: {self.VECTOR_STORE_PATH}")
            
        except Exception as e:
            logger.error(f"Error creating directories: {e}")
            raise

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        case_sensitive = True
        extra = "ignore"

# Initialize settings with enhanced error handling
try:
    # Debug: Print current environment
    print(f"Current working directory: {os.getcwd()}")
    print(f"Looking for .env at: {os.path.abspath('.env')}")
    print(f"Current TELEGRAM_ADMIN_IDS env var: {os.getenv('TELEGRAM_ADMIN_IDS')}")
    
    # Initialize settings
    settings = Settings(_env_file='.env')
    
    # Validate directories
    settings.validate_paths()
    
    # Debug: Print final admin IDs
    print(f"Initialized admin IDs: {settings.admin_ids}")
    
except Exception as e:
    logger.error(f"Failed to initialize settings: {e}", exc_info=True)
    raise