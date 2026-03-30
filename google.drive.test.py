from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
import pickle
import os

# Scopes requis
SCOPES = ['https://www.googleapis.com/auth/drive']

# Fichier JSON téléchargé depuis Google Cloud Console
CLIENT_SECRET_FILE = 'credentials/client_secret_362977680971-ed92ddj1o7ebe0ud01j53umbf8epquoh.apps.googleusercontent.com.json'
TOKEN_PICKLE = 'token.pickle'

# ID du dossier où uploader les fichiers
FOLDER_ID = '1wgDlVORrBR-LKC5gMwGzQZL3HdC0tDwE'

# Authentification
creds = None
if os.path.exists(TOKEN_PICKLE):
    with open(TOKEN_PICKLE, 'rb') as token:
        creds = pickle.load(token)
if not creds or not creds.valid:
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
    creds = flow.run_local_server(port=0)
    with open(TOKEN_PICKLE, 'wb') as token:
        pickle.dump(creds, token)

service = build('drive', 'v3', credentials=creds)

# Upload du fichier dans le dossier spécifique
media = MediaIoBaseUpload(io.BytesIO(b'test content'), mimetype='text/plain')
file = service.files().create(
    body={
        'name': 'test.txt',
        'parents': [FOLDER_ID]  # <-- Ici tu spécifies le dossier
    },
    media_body=media,
    fields='id'
).execute()

file_id = file.get('id')
print(f"✅ Upload réussi ! ID : {file_id}")

# Rendre le fichier public
service.permissions().create(
    fileId=file_id,
    body={'type': 'anyone', 'role': 'reader'}
).execute()
print(f"✅ Fichier public : https://drive.google.com/uc?export=view&id={file_id}")