"""Google Drive service for file storage."""
import os
import io
import json
import base64
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from google.auth.transport.requests import Request

from ..config import get_settings

settings = get_settings()

# Folder name in Google Drive for storing app files
APP_FOLDER_NAME = "PlannerAI_Files"


class DriveService:
    """Service for Google Drive file operations."""

    def __init__(self):
        self._service = None
        self._folder_id: Optional[str] = None

    @property
    def service(self):
        """Lazy-load Google Drive service."""
        if self._service is None:
            self._service = self._authenticate()
        return self._service

    def _authenticate(self):
        """Authenticate with Google Drive API using same credentials as Calendar."""
        creds = None

        # Check for base64-encoded credentials from environment (for cloud deployment)
        if settings.GOOGLE_TOKEN_JSON:
            try:
                token_data = base64.b64decode(settings.GOOGLE_TOKEN_JSON).decode('utf-8')
                token_dict = json.loads(token_data)
                creds = Credentials.from_authorized_user_info(token_dict, settings.GOOGLE_SCOPES)
            except Exception as e:
                raise RuntimeError(f"Failed to load token from GOOGLE_TOKEN_JSON: {e}")
        else:
            # Fallback to file-based auth for local development
            token_path = str(settings.TOKEN_PATH)

            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, settings.GOOGLE_SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            elif not settings.GOOGLE_TOKEN_JSON:
                # Only try OAuth flow for local development
                creds_path = str(settings.CREDENTIALS_PATH)
                if not os.path.exists(creds_path):
                    raise RuntimeError(
                        f"Missing credentials.json at {creds_path}. "
                        "Download from Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, settings.GOOGLE_SCOPES)
                creds = flow.run_local_server(port=0)

                with open(str(settings.TOKEN_PATH), "w", encoding="utf-8") as f:
                    f.write(creds.to_json())

        return build("drive", "v3", credentials=creds)

    def _get_or_create_app_folder(self) -> str:
        """Get or create the app's folder in Google Drive."""
        if self._folder_id:
            return self._folder_id

        # Search for existing folder
        query = f"name='{APP_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = self.service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()

        files = results.get('files', [])

        if files:
            self._folder_id = files[0]['id']
        else:
            # Create the folder
            folder_metadata = {
                'name': APP_FOLDER_NAME,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            self._folder_id = folder.get('id')

        return self._folder_id

    def upload_file(
        self,
        file_content: bytes,
        filename: str,
        mime_type: str,
        subfolder: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upload a file to Google Drive.

        Args:
            file_content: The file bytes
            filename: Name for the file
            mime_type: MIME type (e.g., 'image/jpeg')
            subfolder: Optional subfolder within app folder ('chat' or 'todos')

        Returns:
            Dict with file id, name, and webViewLink
        """
        parent_id = self._get_or_create_app_folder()

        # Create subfolder if specified
        if subfolder:
            parent_id = self._get_or_create_subfolder(parent_id, subfolder)

        # Upload the file
        file_metadata = {
            'name': filename,
            'parents': [parent_id]
        }

        media = MediaIoBaseUpload(
            io.BytesIO(file_content),
            mimetype=mime_type,
            resumable=True
        )

        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink, webContentLink, mimeType, size'
        ).execute()

        return {
            'id': file.get('id'),
            'name': file.get('name'),
            'webViewLink': file.get('webViewLink'),
            'webContentLink': file.get('webContentLink'),
            'mimeType': file.get('mimeType'),
            'size': file.get('size')
        }

    def _get_or_create_subfolder(self, parent_id: str, folder_name: str) -> str:
        """Get or create a subfolder within a parent folder."""
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
        results = self.service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()

        files = results.get('files', [])

        if files:
            return files[0]['id']
        else:
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id]
            }
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            return folder.get('id')

    def download_file(self, file_id: str) -> Tuple[bytes, str]:
        """Download a file from Google Drive.

        Returns:
            Tuple of (file_content, mime_type)
        """
        # Get file metadata first
        file_meta = self.service.files().get(
            fileId=file_id,
            fields='mimeType, name'
        ).execute()

        mime_type = file_meta.get('mimeType', 'application/octet-stream')

        # Download the file
        request = self.service.files().get_media(fileId=file_id)
        file_buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(file_buffer, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        file_buffer.seek(0)
        return file_buffer.read(), mime_type

    def get_file_info(self, file_id: str) -> Dict[str, Any]:
        """Get file metadata."""
        file = self.service.files().get(
            fileId=file_id,
            fields='id, name, webViewLink, webContentLink, mimeType, size, createdTime'
        ).execute()
        return file

    def delete_file(self, file_id: str) -> None:
        """Delete a file from Google Drive."""
        self.service.files().delete(fileId=file_id).execute()

    def list_files(self, subfolder: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """List files in the app folder or a subfolder."""
        parent_id = self._get_or_create_app_folder()

        if subfolder:
            parent_id = self._get_or_create_subfolder(parent_id, subfolder)

        query = f"'{parent_id}' in parents and trashed=false and mimeType!='application/vnd.google-apps.folder'"

        results = self.service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name, mimeType, size, createdTime, webViewLink)',
            orderBy='createdTime desc',
            pageSize=limit
        ).execute()

        return results.get('files', [])

    def get_download_url(self, file_id: str) -> str:
        """Get a direct download URL for a file (for images to send to AI)."""
        # Make the file viewable by anyone with the link temporarily
        # This is needed for OpenAI to access the image
        try:
            self.service.permissions().create(
                fileId=file_id,
                body={'type': 'anyone', 'role': 'reader'},
                fields='id'
            ).execute()
        except Exception:
            pass  # Permission might already exist

        file = self.service.files().get(
            fileId=file_id,
            fields='webContentLink'
        ).execute()

        return file.get('webContentLink', '')

    def get_storage_usage(self) -> Dict[str, Any]:
        """Get storage usage info for the app folder."""
        parent_id = self._get_or_create_app_folder()

        # List all files recursively
        total_size = 0
        file_count = 0

        def count_folder(folder_id):
            nonlocal total_size, file_count

            query = f"'{folder_id}' in parents and trashed=false"
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, mimeType, size)'
            ).execute()

            for f in results.get('files', []):
                if f.get('mimeType') == 'application/vnd.google-apps.folder':
                    count_folder(f['id'])
                else:
                    file_count += 1
                    total_size += int(f.get('size', 0))

        count_folder(parent_id)

        return {
            'total_bytes': total_size,
            'total_mb': round(total_size / (1024 * 1024), 2),
            'file_count': file_count
        }


# Singleton instance
_drive_service: Optional[DriveService] = None


def get_drive_service() -> DriveService:
    """Get the singleton DriveService instance."""
    global _drive_service
    if _drive_service is None:
        _drive_service = DriveService()
    return _drive_service
