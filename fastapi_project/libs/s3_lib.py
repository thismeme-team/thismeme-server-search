import boto3
import os 
import pymysql
import hashlib
from dotenv import find_dotenv, load_dotenv
from pprint import pprint
from tqdm import tqdm
from .notion_lib import get_image_url_list



pymysql.install_as_MySQLdb()

load_dotenv(dotenv_path=find_dotenv(filename="secrets/.env"))

AWS_ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.environ.get('AWS_SECRET_KEY')
AWS_REGION = os.environ.get('AWS_REGION')
BUCKET_NAME = os.environ.get('BUCKET_NAME')


def get_obj_list():
    s3 = boto3.client(
        's3',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
    )

    paginator = s3.get_paginator('list_objects_v2')
    response_iterator = paginator.paginate(
        Bucket=BUCKET_NAME
    )

    results = []
    for page in response_iterator:
        for content in page['Contents']:
            results.append(content)

    return results


def get_obj_url_list():
    s3 = boto3.client(
        's3',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
    )

    paginator = s3.get_paginator('list_objects_v2')
    response_iterator = paginator.paginate(
        Bucket=BUCKET_NAME
    )

    base_url = "https://jjmeme-bucket-2.s3.amazonaws.com/"
    results = []
    for page in response_iterator:
        for content in page['Contents']:
            results.append(base_url + content['Key'])
            print(content['Key'])

    return results


def get_obj_url_list_only_key():
    s3 = boto3.client(
        's3',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
    )

    obj_list = s3.list_objects(Bucket=BUCKET_NAME)
    contents_list = obj_list['Contents']

    return [content['Key'] for content in contents_list]


def upload_image(image, image_name):
    s3 = boto3.resource(
        's3',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
    )

    result = s3.Bucket("jjmeme-bucket-2").put_object(Key=f"hashed_name_image/{image_name}", Body=image, ContentType='image/jpg')    
    print(result)


def upload_image_gd():
    s3 = boto3.resource(
        's3',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
    )
    
    dir_path = "../google_drive_images/"

    # list to store files
    images = []
    # Iterate directory
    for path in os.listdir(dir_path):
        # check if current path is a file
        if os.path.isfile(os.path.join(dir_path, path)):
            images.append(path)

    uploaded_keys = get_obj_url_list_only_key()
    pbar = tqdm(list(filter(lambda x: x not in uploaded_keys, images)))
    for image_name in pbar:
        print(image_name)
        image = open(dir_path + image_name, 'rb')
        result = s3.Bucket("jjmeme-bucket-2").put_object(Key=image_name, Body=image, ContentType='image/jpg')
        print(result)

    pbar.close()


def s3_clean_from_notion():
    notion_image_url_list = get_image_url_list()
    s3_image_url_list = get_obj_url_list()

    notion_image_url_list = list(map(lambda x: x.replace("%20", " "), notion_image_url_list))

    diff_list = list(set(s3_image_url_list) - set(notion_image_url_list))
    print(diff_list)
    print(f"notion: {len(notion_image_url_list)}, s3: {len(s3_image_url_list)}, diff: {len(diff_list)}")
    print(f"notion: {len(set(notion_image_url_list))}, s3: {len(set(s3_image_url_list))}, diff: {len(diff_list)}")

    s3 = boto3.client(
        's3',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
    )

    base_url = "https://jjmeme-bucket-2.s3.amazonaws.com/"
    pbar = tqdm(diff_list)
    for diff_obj in pbar:
        file_name = diff_obj.replace(base_url, "")
        response = s3.delete_object(Bucket=BUCKET_NAME, Key=file_name)
        pprint(response)
    pbar.close()


def update_object_key(old_key, new_key):
    s3 = boto3.client(
        's3',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
    )

    s3.copy_object(Bucket=BUCKET_NAME, CopySource=f'{BUCKET_NAME}/{old_key}', Key=f"hashed_name_image/{new_key}")
    # s3.delete_object(Bucket=BUCKET_NAME, Key=old_key)


if __name__ == "__main__":
    # obj_url_list = get_obj_url_list()
    # upload_image_gd()
    # s3_clean_from_notion()
    result = get_obj_list()
    print(result[0])
    key = result[0]['Key']
    ext = key.split(".")[-1]
    new_key = f"{hashlib.sha256(key.encode('utf-8')).hexdigest()}.{ext}"
    update_object_key(key, new_key)
