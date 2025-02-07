from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional, List
import logging
import os
from huggingface_hub import hf_hub_download

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # Base Paths
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    MODEL_DIR: Path = DATA_DIR / "models"
    
    # Hugging Face Model Settings
    MODEL_ID: str = "TheBloke/Llama-2-7B-Chat-GGUF"
    MODEL_FILENAME: str = "llama-2-7b-chat.Q4_K_M.gguf"
    
    # LLM Configuration
    CONTEXT_LENGTH: int = 4096
    GPU_LAYERS: int = 0
    THREADS: int = 4
    MAX_TOKENS: int = 2048
    
    @property
    def MODEL_PATH(self) -> str:
        """Get or download the model file"""
        model_path = self.MODEL_DIR / self.MODEL_FILENAME
        if not model_path.exists():
            logger.info(f"Downloading model from Hugging Face: {self.MODEL_ID}")
            model_path = Path(hf_hub_download(
                repo_id=self.MODEL_ID,
                filename=self.MODEL_FILENAME,
                local_dir=self.MODEL_DIR,
                local_dir_use_symlinks=False
            ))
        return str(model_path)
    
    # Rest of your settings...
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/superteam.db"
    VECTOR_STORE_PATH: str = str(DATA_DIR / "vector_store")
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_ADMIN_IDS: str
    SECRET_KEY: str
    ADMIN_PASSWORD: str

    @property
    def admin_ids(self) -> List[str]:
        """Get list of admin IDs with proper logging and validation"""
        try:
            logger.info(f"Loading admin IDs from config: {self.TELEGRAM_ADMIN_IDS}")
            
            if not self.TELEGRAM_ADMIN_IDS:
                logger.warning("No admin IDs configured")
                return []
                
            # Split and clean admin IDs
            admin_list = [str(id.strip()) for id in self.TELEGRAM_ADMIN_IDS.split(",") 
                         if id.strip().isdigit()]
            
            logger.info(f"Parsed admin IDs: {admin_list}")
            
            if not admin_list:
                logger.warning("No valid admin IDs found after parsing")
            
            return admin_list
            
        except Exception as e:
            logger.error(f"Error parsing admin IDs: {e}")
            return []

    def validate_paths(self):
        """Validate and create necessary directories"""
        try:
            self.DATA_DIR.mkdir(parents=True, exist_ok=True)
            self.MODEL_DIR.mkdir(parents=True, exist_ok=True)
            Path(self.VECTOR_STORE_PATH).mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Data directory: {self.DATA_DIR}")
            logger.info(f"Model directory: {self.MODEL_DIR}")
            logger.info(f"Vector store directory: {self.VECTOR_STORE_PATH}")
            
        except Exception as e:
            logger.error(f"Error creating directories: {e}")
            raise

    class Config:
        env_file = ".env"
        case_sensitive = True

# Initialize settings
settings = Settings()

# Validate directories on import
try:
    settings.validate_paths()
except Exception as e:
    logger.error(f"Failed to initialize settings: {e}")
    raise