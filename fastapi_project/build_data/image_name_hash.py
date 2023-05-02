import hashlib
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

import pymysql
from fastapi_project.app import models
import os

pymysql.install_as_MySQLdb()

app = FastAPI()
logger.add("logs/search_log_{time}", rotation="12:00")
templates = Jinja2Templates(directory="./templates/")

load_dotenv(dotenv_path="../secrets/.env")

AWS_ACCESS_KEY = os.environ.get("AWS_ES_ACCESS_KEY")
AWS_SECRET_KEY = os.environ.get("AWS_ES_SECRET_KEY")
AWS_REGION = os.environ.get("AWS_ES_REGION")
AWS_SERVICE = os.environ.get("AWS_ES_SERVICE")

DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST","localhost")
DB_PORT = os.getenv("DB_PORT", 3306)
DB_DATABASE = os.getenv("DB_DATABASE")

HOST = os.environ.get("ES_HOST")

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = f"mysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_DATABASE}"
engine = create_engine(DATABASE_URL, encoding="utf-8", pool_recycle=3600)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

s3_base_url = "https://jjmeme-bucket-2.s3.amazonaws.com/"
s3_new_url = "https://jjmeme-bucket-2.s3.amazonaws.com/hashed_name_image/"


def update_rdb_image_url(url):
    db = db_session()

    rdb_object = db.query(models.IMAGE).filter_by(image_url=url).first()
    if rdb_object:
        rdb_object.image_url = s3_new_url + new_key

    db.commit()
    db.close()

if __name__ == "__main__":
    key = "IMG_7080.JPG"
    ext = key.split(".")[-1]
    new_key = f"{hashlib.sha256(key.encode('utf-8')).hexdigest()}.{ext}"
    print(new_key)

    # s3_object_list = s3_lib.get_obj_list()
    # s3_object_list = list(filter(lambda x: 'hashed' not in x['Key'], s3_object_list))
    # print(len(s3_object_list))

    # last_index = 0
    # for idx, s3_object in enumerate(s3_object_list):
    #     if s3_object['Key'] == '무한도전_3035.jpg':
    #         last_index = idx
    #         break

    # print(last_index)
    # pbar = tqdm(s3_object_list[last_index:])
    # for s3_object in pbar:
    #     key = s3_object['Key']
    #     print(f"key = {key}")

        # ext = key.split(".")[-1]
        # new_key = f"{hashlib.sha256(key.encode('utf-8')).hexdigest()}.{ext}"
    #     s3_full_url = s3_base_url + key
    #     s3_full_url = s3_full_url.replace(" ", "%20")
    #     print(f"new_key = {new_key}")
    #     s3_lib.update_object_key(key, new_key)
    #     print("=== updated s3 ===")

    #     notion_object = notion_lib.search_by_url(s3_full_url)
    #     if notion_object:
    #         notion_lib.update_image_url(notion_object[0], s3_new_url + new_key)
    #         print("=== updated notion ===")
    #     else:
    #         print("=== no notion object ===")

    #     update_rdb_image_url(s3_full_url)
    #     print("=== updated rdb ===")
