"""UI module initialization."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Create main FastAPI app
app = FastAPI(title="Superteam Vietnam Admin UI")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routes after app creation to avoid circular imports
from .admin import app as admin_app

# Mount the admin app
app.mount("/admin", admin_app)

# Ensure required directories exist
def ensure_directories():
    """Create necessary directories if they don't exist."""
    try:
        directories = [
            "data/uploads",
            "data/knowledge_base",
            "data/models",
        ]
        for dir_path in directories:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            logger.info(f"Directory ensured: {dir_path}")
    except Exception as e:
        logger.error(f"Error creating directories: {e}")

# Initialize directories on import
ensure_directories()

__all__ = ['app']