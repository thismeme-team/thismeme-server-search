from dotenv import load_dotenv, find_dotenv
from notion_client import Client
from PIL import Image
import requests
from io import BytesIO

import os
from pprint import pprint
from sqlalchemy import create_engine
from tqdm import tqdm

from google.cloud import vision
from konlpy.tag import Okt
from PIL import Image

import io
import re

# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./secrets/meme-369708-e4bd2f8056f2.json"
# client = vision.ImageAnnotatorClient()

load_dotenv(dotenv_path=find_dotenv(filename="secrets/.env"))

notion_secret_key = os.environ.get("NOTION_SECRET_KEY")
notion = Client(auth=notion_secret_key)

# print(notion)

databases = notion.search(filter={"property": "object", "value": "database"})
# pprint(databases)

database_id = databases['results'][0]['id']
databases = notion.databases.retrieve(database_id=database_id)
# pprint(databases)

def read():
    condition = []
    condition.append({'property': '밈 제목', 'title': {'is_not_empty' : True}})
    condition.append({'property': '밈 제목', 'title': {'does_not_contain': "#"}})
    condition.append({'property': '콘텐츠', 'multi_select': {'contains': "무한도전"}})
    # resp = notion.databases.query(database_id=database_id, filter={'or': condition})
    results = []
    cursor = None
    while True:
        resp = notion.databases.query(database_id=database_id, start_cursor=cursor, filter={'and': condition})
        results.extend(resp['results'])

        if not resp['has_more']:
            break
        cursor = resp['next_cursor']

    return results


def get_title_list():
    title_list = []
    cursor = None
    while True:
        resp = notion.databases.query(database_id=database_id, start_cursor=cursor)
        results = resp['results']
        for data in results:
            try:
                properites = data['properties']
                title = properites['밈 제목']['title'][0]['plain_text']
                title_list.append(title)
            except:
                continue

        if not resp['has_more']:
            break
        cursor = resp['next_cursor']
    return title_list


def update_title_from_image_caption():
    updated_count = 0
    cursor = None
    while True:
        resp = notion.databases.query(database_id=database_id, start_cursor=cursor)
        results = resp['results']
        for data in results:
            try:
                properites = data['properties']
                image_url = properites['URL']['url']
                title = properites['밈 제목']['title'][0]['plain_text'] if properites['밈 제목']['title'] else ""
                if not title:
                    continue

                if "무한도전_" not in title:
                    continue
    
                response = requests.get(image_url)
                img = Image.open(BytesIO(response.content))

                width, height = img.size
                left = 0
                right = width
                top = height / 2
                bottom = height * (95/100)
                _img = img.crop((left, top, right, bottom))
                
                buffer = io.BytesIO()
                _img.save(buffer, format="png")

                image = vision.Image(content=buffer.getvalue())
                # response = client.text_detection(image=image)

                try:
                    for ta in response.text_annotations:
                        max_x = -1
                        min_x = 10000
                        for v in ta.bounding_poly.vertices:
                            if v.x > max_x:
                                max_x = v.x
                            elif v.x < min_x:
                                min_x = v.x

                        diff = max_x - min_x
                        if diff > 300:
                            desc = ta.description
                            words = desc.split("\n")

                            result = []
                            for word in words:
                                hangul = re.compile(r'[^ .?!~\(\)ㄱ-ㅣ가-힣0-9+]')
                                hangul = hangul.sub('', word)
                                # hangul = spell_checker.check(hangul).as_dict()
                                hangul = hangul['checked']
                                if len(hangul) > 3 and not hangul.strip().replace(" ", "").isnumeric():
                                    result.append(hangul)

                            if result:
                                print(title, " ".join(result))
                                new_properties = properites
                                new_properties['밈 제목']['title'][0]['plain_text'] = f"#{' '.join(result)}"
                                new_properties['밈 제목']['title'][0]['text']['content'] = f"#{' '.join(result)}"
                                notion.pages.update(page_id=data['id'], properties=new_properties)
                                updated_count += 1
                except:
                    continue
                
            except Exception as e:
                print(e)
                print("Does Not Exists: Url value")
                continue

        if not resp['has_more']:
            break
        cursor = resp['next_cursor']

    print(updated_count)


def get_image_url_list():
    image_url_list = []
    cursor = None
    while True:
        resp = notion.databases.query(database_id=database_id, start_cursor=cursor)
        results = resp['results']
        for data in results:
            try:
                properites = data['properties']
                image_url = properites['URL']['url']
                image_url_list.append(image_url)
            except:
                print("Does Not Exists: Url value")
                continue

        if not resp['has_more']:
            break
        cursor = resp['next_cursor']
    return image_url_list


def create(name, ext, url):
    resp = notion.databases.query(database_id=database_id)
    results = resp['results']
    sample_page_id = results[-1]['id']

    sample_page = notion.pages.retrieve(page_id=sample_page_id)
    properties_new = sample_page['properties']

    target_key_list = ["밈 제목", "기존 태그", "URL"]
    keys = [key for key in properties_new.keys()]
    for key in keys:
        if key not in target_key_list:
            del properties_new[key]
    
    
    properties_new['밈 제목']['title'] = []
    properties_new['밈 제목']['title'].append({
        "plain_text": name,
        "text": {
            "content": name
        }
    })
    properties_new['기존 태그']['rich_text'] = []
    properties_new['기존 태그']['rich_text'].append({
        "text": {
            "content": ""
        }
    })
    properties_new["URL"]["url"] = url

    result = notion.pages.create(parent={'database_id': database_id}, properties=properties_new)

    page_id = result['id']
    blocks = notion.blocks.children.list(block_id=page_id)

    children_image = {
        "type": "image", 
        "image": {
            "external": {
                "url": url
            }
        }
    }
    children_blocks = [children_image]
    notion.blocks.children.append(block_id=page_id, children=children_blocks)


def retrieve_database():
    databases = notion.search(filter={"property": "object", "value": "database"})
    target_db = databases['results'][1]

    database_details = notion.databases.retrieve(database_id=target_db['id'])
    # pprint(database_details)

    return database_details


def move_tag():
    pass


def search_by_url(url):
    # pprint(notion.databases.query(database_id=database_id))
    condition = []
    condition.append({'property': 'URL', 'url': {'equals': url}})

    results = []
    cursor = None
    while True:
        resp = notion.databases.query(database_id=database_id, start_cursor=cursor, filter={'and': condition})
        results.extend(resp['results'])

        if not resp['has_more'] or results:
            break
        cursor = resp['next_cursor']

    return results


def update_image_url(data, url):
    properites = data['properties']
    page_id = data['id']
    new_properties = properites
    new_properties['URL']['url'] = url
    notion.pages.update(page_id=data['id'], properties=new_properties)

    children_image = {
        "type": "image", 
        "image": {
            "external": {
                "url": url
            }
        }
    }
    children_blocks = [children_image]
    notion.blocks.children.append(block_id=page_id, children=[])
    notion.blocks.children.append(block_id=page_id, children=children_blocks)


if __name__ == "__main__":
    # results = read()
    # print(len(results))
    # create("test22", ".jpg", "https://jjmeme-bucket-2.s3.amazonaws.com/(집에서)엄청바빠~할게많아.jpg")
    # print(len(get_title_list()))
    # pprint(databases['properties'].keys())
    # update_title_from_image_caption()
    # result = search_by_url('https://jjmeme-bucket-2.s3.amazonaws.com/무한도전_489.jpg')
    # print(result)
    # pass
    import pymysql
    pymysql.install_as_MySQLdb()
    DB_USERNAME = os.getenv("DB_USERNAME")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST = os.getenv("DB_HOST","localhost")
    DB_PORT = os.getenv("DB_PORT", 3306)
    DB_DATABASE = os.getenv("DB_DATABASE")
    from sqlalchemy.orm import scoped_session, sessionmaker
    import models
    DATABASE_URL = f"mysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_DATABASE}"
    engine = create_engine(DATABASE_URL, encoding="utf-8", pool_recycle=3600)
    db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

    notion_secret_key = os.environ.get("NOTION_SECRET_KEY")
    notion = Client(auth=notion_secret_key)
    databases = notion.search(filter={"property": "object", "value": "database"})
    pprint(databases['results'])
    database_id = databases['results'][0]['id']
    # databases = notion.databases.retrieve(database_id=database_id)
    pprint(databases)

    results = []
    cursor = None
    while True:
        print(cursor)
        resp = notion.databases.query(database_id=database_id, start_cursor=cursor)
        results.extend(resp['results'])

        if not resp['has_more']:
            break
        cursor = resp['next_cursor']

    print(len(results))
    current_category = None
    db = db_session()
    for result in results:
        if result['properties']['태그 카테고리']['title']:
            category = result['properties']['태그 카테고리']['title'][0]['plain_text'].strip()
            pprint(result)
            print(category)

            for relation in result['properties']['하위 항목']['relation']:
                page = notion.pages.retrieve(page_id=relation['id'])
                sub_category = page['properties']['2차 카테고리']['multi_select'][0]['name'].strip()
                tag = page['properties']['태그']['rich_text'][0]['text']['content'].strip()
                print(category, sub_category, tag)

                _category = db.query(models.MAIN_CATEGORY).filter_by(name=category)[0]
                _sub_category = db.query(models.CATEGORY).filter_by(name=sub_category)
                if not list(_sub_category):
                    _sub_category = models.CATEGORY(main_category_id=_category.main_category_id, name=sub_category)
                    db.add(_sub_category)
                    db.flush()
                    db.refresh(_sub_category)
                else:
                    _sub_category = _sub_category[0]

                _tag = db.query(models.TAG).filter_by(name=tag)
                if not list(_tag):
                    _tag = models.TAG(category_id=_sub_category.category_id, name=tag)
                    db.add(_tag)
                    db.flush()
                    db.refresh(_tag)
                else:
                    _tag = _tag[0]
                    _tag.category_id = _sub_category.category_id

            # break
            db.commit()
    db.close()