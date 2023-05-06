from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import pymysql
from fastapi_project import models
import os

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


def move_tag(from_tag_name, to_tag_name, to_category_name):
    print(f"from: {from_tag_name} -> to: {to_tag_name}")
    db = db_session()

    from_tag = db.query(models.TAG).filter_by(name=from_tag_name).first()
    if not from_tag:
        print(f"Does not exists from_tag: {from_tag_name}")
        return
    from_category = db.query(models.CATEGORY).filter_by(category_id=from_tag.category_id).first()

    to_tag = db.query(models.TAG).filter_by(name=to_tag_name).first()
    to_category = db.query(models.CATEGORY).filter_by(name=to_category_name).first()
    if not to_tag:
        print(f"Create to_tag: {to_tag}")
        to_tag = models.TAG(name=to_tag_name, category_id=to_category.category_id)

    if not to_tag:
        print(f"Update Tag/ from: {from_tag_name} -> to: {to_tag_name}")
        from_tag.name = to_tag_name
        from_tag.category_id = to_category.category_id
    else:
        print(f"Move Tag/ from: {from_tag_name} -> to: {to_tag_name}")
        updated_cnt = db.query(models.MEME_TAG).filter_by(tag_id=from_tag.tag_id).update({"tag_id": to_tag.tag_id})
        print(f"Move count: {updated_cnt}")
        db.query(models.TAG).filter_by(name=from_tag_name).delete()

    db.commit()
    db.close()


if __name__ == "__main__":
    target_list_str = """
    - 귀여울때→귀여움
    - 기대할때→기대함
    - 기쁠때→기쁨
    - 답답할때→답답함
    - 부끄러울때→부끄러움
    - 속상할때→속상함
    - 외로울때→외로움
    - 아플때→아픔
    - 자상할때→자상함
    - 즐거울때→즐거움
    - 지칠때→지침
    - 피곤할때→피곤함
    - 피로할때→피로함
    - 화날때→화남
    - 슬플때→슬픔
    - 어색할때→어색함
    - 어이없을때→어이없음
    - 억울할떄→억울함
    - 의문스러울때→의문
    - 심심할때→심심함
    - 첫데이트준비할때→기대
    - 동아줄이라도잡고싶을때→간절함
    - 술로마음을적시고싶을때→씁쓸함
    """

    target_list = []
    target_list_str = target_list_str.replace("→", ",")
    for target_str in target_list_str.split("- ")[1:]:
        from_tag_name, to_tag_name = target_str.strip().split(",")
        target_list.append({
            "from_tag_name": from_tag_name,
            "to_tag_name": to_tag_name
        })

    for target in target_list[:10]:
        from_tag_name = target['from_tag_name']
        to_tag_name = target['to_tag_name']

        move_tag(from_tag_name, to_tag_name)
        print()
