import boto3
import os 
import pymysql
from app import models
import hashlib
from botocore.client import Config
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.sql import exists
from PIL import Image
from pprint import pprint
from tqdm import tqdm


pymysql.install_as_MySQLdb()

load_dotenv(dotenv_path="../secrets/.env")

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


def upload_image(image, image_name, prefix="hashed_name_image"):
    s3 = boto3.resource(
        's3',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
    )

    result = s3.Bucket("jjmeme-bucket-2").put_object(Key=f"{prefix}/{image_name}", Body=image, ContentType='image/jpg')    
    print(result)

    return result


def update_object_key(old_key, new_key):
    s3 = boto3.client(
        's3',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
    )

    s3.copy_object(Bucket=BUCKET_NAME, CopySource=f'{BUCKET_NAME}/{old_key}', Key=f"hashed_name_image/{new_key}")
    # s3.delete_object(Bucket=BUCKET_NAME, Key=old_key)
