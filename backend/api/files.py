"""File upload API endpoints."""
import base64
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from pydantic import BaseModel

from ..services.drive_service import get_drive_service

router = APIRouter(prefix="/api/files", tags=["files"])

# Allowed file types
ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
ALLOWED_DOCUMENT_TYPES = {'application/pdf'}
ALLOWED_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_DOCUMENT_TYPES

# Max file size (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024


class FileResponse(BaseModel):
    id: str
    name: str
    mime_type: str
    size: Optional[int] = None
    web_view_link: Optional[str] = None
    web_content_link: Optional[str] = None


class FileListResponse(BaseModel):
    files: List[FileResponse]
    total_mb: float
    file_count: int


@router.post("/upload", response_model=FileResponse)
async def upload_file(
    file: UploadFile = File(...),
    subfolder: Optional[str] = Form(default="chat")
):
    """Upload a file to Google Drive.

    Args:
        file: The file to upload
        subfolder: 'chat' for chat attachments, 'todos' for task attachments
    """
    # Validate file type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{file.content_type}' not allowed. Allowed types: images (jpeg, png, gif, webp) and PDFs"
        )

    # Read file content
    content = await file.read()

    # Validate file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
        )

    # Upload to Drive
    try:
        drive = get_drive_service()
        result = drive.upload_file(
            file_content=content,
            filename=file.filename or "uploaded_file",
            mime_type=file.content_type,
            subfolder=subfolder
        )

        return FileResponse(
            id=result['id'],
            name=result['name'],
            mime_type=result['mimeType'],
            size=int(result.get('size', 0)) if result.get('size') else None,
            web_view_link=result.get('webViewLink'),
            web_content_link=result.get('webContentLink')
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@router.get("/list", response_model=FileListResponse)
async def list_files(subfolder: Optional[str] = None, limit: int = 50):
    """List files in the app's Google Drive folder."""
    try:
        drive = get_drive_service()
        files = drive.list_files(subfolder=subfolder, limit=limit)
        usage = drive.get_storage_usage()

        return FileListResponse(
            files=[
                FileResponse(
                    id=f['id'],
                    name=f['name'],
                    mime_type=f.get('mimeType', 'unknown'),
                    web_view_link=f.get('webViewLink')
                )
                for f in files
            ],
            total_mb=usage['total_mb'],
            file_count=usage['file_count']
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.get("/{file_id}")
async def get_file(file_id: str):
    """Get file info by ID."""
    try:
        drive = get_drive_service()
        info = drive.get_file_info(file_id)
        return FileResponse(
            id=info['id'],
            name=info['name'],
            mime_type=info.get('mimeType', 'unknown'),
            size=int(info.get('size', 0)) if info.get('size') else None,
            web_view_link=info.get('webViewLink'),
            web_content_link=info.get('webContentLink')
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found: {str(e)}")


@router.get("/{file_id}/download")
async def get_download_url(file_id: str):
    """Get a download URL for a file (makes it temporarily public for AI access)."""
    try:
        drive = get_drive_service()
        url = drive.get_download_url(file_id)
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found: {str(e)}")


@router.get("/{file_id}/content")
async def get_file_content(file_id: str):
    """Get file content as base64 (for sending to AI)."""
    try:
        drive = get_drive_service()
        content, mime_type = drive.download_file(file_id)

        # Return base64 encoded content
        b64_content = base64.b64encode(content).decode('utf-8')

        return {
            "content": b64_content,
            "mime_type": mime_type,
            "is_image": mime_type in ALLOWED_IMAGE_TYPES
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Failed to get file content: {str(e)}")


@router.delete("/{file_id}")
async def delete_file(file_id: str):
    """Delete a file from Google Drive."""
    try:
        drive = get_drive_service()
        drive.delete_file(file_id)
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Failed to delete file: {str(e)}")


@router.get("/storage/usage")
async def get_storage_usage():
    """Get storage usage statistics."""
    try:
        drive = get_drive_service()
        return drive.get_storage_usage()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get storage usage: {str(e)}")
