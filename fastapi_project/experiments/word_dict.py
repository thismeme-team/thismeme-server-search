from pprint import pprint
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from tqdm import tqdm
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO
from konlpy.tag import Okt

from fastapi_project.app import models
import pymysql
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
okt = Okt()


def get_all_rows_from_rdb_table(table):
    all_rows = db.query(table).all()
    db.close()
    return all_rows


def get_word_set_from_rows(rows):
    word_list = []
    for row in rows:
        word_list.extend([noun for noun in okt.nouns(okt.normalize(row.name)) if len(noun) > 1])
    return set(word_list)

def get_word_list_from_rdb():
    memes = get_all_rows_from_rdb_table(models.MEME)
    tags = get_all_rows_from_rdb_table(models.TAG)

    total_word_set = set()
    meme_word_set = get_word_set_from_rows(memes)
    tag_word_set = get_word_set_from_rows(tags)

    total_word_set = total_word_set.union(meme_word_set)
    total_word_set = total_word_set.union(tag_word_set)
    print(total_word_set)
    print(len(total_word_set))


if __name__ == "__main__":
    get_word_list_from_rdb()