import os.path
import io
import gdown

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from PIL import Image
from tqdm import tqdm

from pprint import pprint

def get_creds():
    # If modifying these scopes, delete the file token.json.
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    """Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('../token.json'):
        creds = Credentials.from_authorized_user_file('../token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                '../secrets/client_secret_290545402134-8bi7u6v4nrnqkdptto6rcm97irg7b2to.apps.googleusercontent.com.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('../token.json', 'w') as token:
            token.write(creds.to_json())

    return creds

service = build('drive', 'v3', credentials=get_creds())

def get_root_folder(root_folder_name):
    folder = None
    page_token = None
    while True:
        # pylint: disable=maybe-no-member
        response = service.files().list(q="mimeType='application/vnd.google-apps.folder'",
                                        spaces='drive',
                                        fields='nextPageToken, '
                                                'files(id, name)',
                                        pageToken=page_token).execute()
        for file in response.get('files', []):
            # Process change
            if file.get("name") == root_folder_name:
                print(F'Found file: {file.get("name")}, {file.get("id")}')
                folder = file
        page_token = response.get('nextPageToken', None)
        if page_token is None:
            break
    
    return folder


def get_folders(target_folders, root_folder):
    folders = []
    page_token = None
    while True:
        # pylint: disable=maybe-no-member
        response = service.files().list(q=f"parents = '{root_folder['id']}'").execute()
        for file in response.get('files', []):
            # Process change
            if file.get("name") in target_folders:
                print(F'Found file: {file.get("name")}, {file.get("id")}')
                folders.append(file)
        page_token = response.get('nextPageToken', None)
        if page_token is None:
            break

    return folders


def get_files(target_folder_names):
    try:
        root_folder = get_root_folder("crawling_images")
        target_folders = get_folders(target_folder_names, root_folder)
    
        files = []

        for target_folder in target_folders:
            __page_token = None
            while True:
                response = service.files().list(q=f"parents = '{target_folder['id']}'",
                                                spaces='drive',
                                                fields='nextPageToken, '
                                                        'files',
                                                pageToken=__page_token).execute()
                _files = [{"target_folder": target_folder, "file": file} for file in response.get('files')]
                files.extend(_files)
                __page_token = response.get('nextPageToken', None)
                if __page_token is None:
                    break

        for _file in files:
            file = _file['file']
            print(file["id"], file["name"], file["webContentLink"])

        return files

    except HttpError as error:
        # TODO(developer) - Handle errors from drive API.
        print(f'An error occurred: {error}')


def download_file(real_file_id):
    try:
        file_id = real_file_id

        # pylint: disable=maybe-no-member
        request = service.files().get_media(fileId=file_id)
        file = io.BytesIO()
        downloader = MediaIoBaseDownload(file, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print(F'Download {int(status.progress() * 100)}.')

    except HttpError as error:
        print(F'An error occurred: {error}')
        file = None

    return file.getvalue()


def download_from_google_drvie(files):
    pbar = tqdm(files)

    base_dir = "../google_drive_images/"
    for _file in pbar:
        file = _file['file']
        target_folder_name = _file['target_folder']['name']
        try:
            file_id = file['id']
            if not os.path.exists(base_dir + file['name']):
                result = download_file(real_file_id=file_id)
                img = Image.open(io.BytesIO(result))
                print(img.width)
                if img.width <= 200 or '#' in file['name']:
                    print("Too small image OR prev image")
                    continue
                img.save(base_dir + target_folder_name + "_" + file['name'])
        except:
            continue

    pbar.close()

    
if __name__ == '__main__':
    target_folder_names = ["추가 조사한 무한도전 짤"]
    files = get_files(target_folder_names)
    # pprint(files)
    download_from_google_drvie(files)

    # notion_lib.create(None)
    # for file in files[:1]:
    #     print(file["name"], file["webContentLink"])
    #     notion_lib.create(file)

    # from PIL import Image
    # import requests
    # from io import BytesIO

    # response = requests.get("https://drive.google.com/file/d/1STBY9Zffmv18N_Gw3GcQexZB4DziXv_p/view?usp=share_link")
    # print(response.content)
    # img = Image.open(BytesIO(response.content))
