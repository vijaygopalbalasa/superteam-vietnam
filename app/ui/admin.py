from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Form
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import secrets
import logging
from ..core.config import settings
from ..core.rag import RAGSystem

app = FastAPI()
security = HTTPBasic()
templates = Jinja2Templates(directory="app/ui/templates")

# Initialize RAG system
rag_system = RAGSystem()

# Set up logging
logger = logging.getLogger(__name__)

def get_current_admin(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify admin credentials"""
    correct_username = "admin"
    correct_password = settings.ADMIN_PASSWORD
    
    is_correct_username = secrets.compare_digest(credentials.username.encode("utf8"), correct_username.encode("utf8"))
    is_correct_password = secrets.compare_digest(credentials.password.encode("utf8"), correct_password.encode("utf8"))
    
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

@app.get("/", response_class=HTMLResponse)
async def admin_panel(admin: str = Depends(get_current_admin)):
    """Admin panel homepage"""
    return templates.TemplateResponse(
        "admin.html",
        {"request": {}, "title": "Superteam Vietnam Admin Panel"}
    )

@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(...),
    admin: str = Depends(get_current_admin)
):
    """Handle document uploads"""
    try:
        # Create uploads directory if it doesn't exist
        upload_dir = Path("data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file
        file_path = upload_dir / file.filename
        content = await file.read()
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Process with RAG system
        with open(file_path, "r", encoding="utf-8") as f:
            text_content = f.read()
        
        metadata = {
            "title": title,
            "description": description,
            "filename": file.filename,
            "uploaded_by": admin
        }
        
        success = await rag_system.add_document(text_content, metadata)
        
        if success:
            return {"message": "Document uploaded and processed successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to process document")
            
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents")
async def list_documents(admin: str = Depends(get_current_admin)):
    """List all uploaded documents"""
    try:
        documents = []
        upload_dir = Path("data/uploads")
        if upload_dir.exists():
            for file_path in upload_dir.glob("*.*"):
                documents.append({
                    "filename": file_path.name,
                    "size": file_path.stat().st_size,
                    "modified": file_path.stat().st_mtime
                })
        return {"documents": documents}
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))