from pprint import pprint
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from tqdm import tqdm
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO

import pymysql
from fastapi_project.app import models
import os
import imagehash
import requests

pymysql.install_as_MySQLdb()

load_dotenv(dotenv_path="../secrets/.env")

DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST","localhost")
DB_PORT = os.getenv("DB_PORT", 3306)
DB_DATABASE = os.getenv("DB_DATABASE")

DATABASE_URL = f"mysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_DATABASE}"
engine = create_engine(DATABASE_URL, encoding="utf-8", pool_recycle=3600)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

db = db_session()

def get_image_list():
    images = db.query(models.IMAGE).all()
    pbar = tqdm(images)
    for image in pbar:
        print(image)
        url = image.image_url
        response = requests.get(url)
        origin_image = Image.open(BytesIO(response.content))
        image.ahash = str(imagehash.average_hash(origin_image))
        image.dhash = str(imagehash.dhash(origin_image))
        image.phash = str(imagehash.phash_simple(origin_image))
        print(image.ahash, image.dhash, image.phash)

    db.commit()
    db.close()

if __name__ == "__main__":
    get_image_list()