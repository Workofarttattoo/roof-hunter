import os
import csv
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# Configuration
# Try multiple possible paths for service account
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, 'credentials', 'service_account.json')

if not os.path.exists(SERVICE_ACCOUNT_FILE):
    # Fallback to .env path if exists
    env_path = os.getenv("GEE_SERVICE_ACCOUNT_KEY")
    if env_path and os.path.exists(env_path):
        SERVICE_ACCOUNT_FILE = env_path

SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']

def get_drive_service():
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        logger.error(f"Service account file not found at {SERVICE_ACCOUNT_FILE}")
        return None
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def create_folder_if_not_exists(folder_name):
    service = get_drive_service()
    if not service: return None
    
    query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])
    
    if not items:
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = service.files().create(body=file_metadata, fields='id').execute()
        logger.info(f"Created folder '{folder_name}' with ID: {folder.get('id')}")
        return folder.get('id')
    else:
        logger.info(f"Folder '{folder_name}' already exists with ID: {items[0]['id']}")
        return items[0]['id']

def upload_csv_to_sheets(csv_path, folder_id):
    service = get_drive_service()
    if not service: return None
    
    file_name = os.path.basename(csv_path)
    sheet_name = os.path.splitext(file_name)[0]
    
    # Check if file already exists in folder
    query = f"name = '{sheet_name}' and '{folder_id}' in parents and trashed = false"
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])
    
    file_metadata = {
        'name': sheet_name,
        'mimeType': 'application/vnd.google-apps.spreadsheet',
        'parents': [folder_id]
    }
    
    media = MediaFileUpload(csv_path, mimetype='text/csv', resumable=True)
    
    if items:
        # Update existing file
        file_id = items[0]['id']
        file = service.files().update(fileId=file_id, media_body=media).execute()
        logger.info(f"Updated existing Sheet '{sheet_name}' (ID: {file_id})")
        return file_id
    else:
        # Create new file
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        logger.info(f"Created new Sheet '{sheet_name}' in folder (ID: {file.get('id')})")
        return file.get('id')

def sync_all_manifests():
    folder_id = create_folder_if_not_exists("Hail_Leads")
    if not folder_id:
        logger.error("Could not find or create Hail_Leads folder.")
        return
    
    manifest_dir = os.path.join(BASE_DIR, 'leads_manifests')
    for f in os.listdir(manifest_dir):
        if f.endswith('.csv'):
            csv_path = os.path.join(manifest_dir, f)
            upload_csv_to_sheets(csv_path, folder_id)

if __name__ == "__main__":
    sync_all_manifests()
