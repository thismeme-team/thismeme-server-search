import asyncio
import hashlib
import io
from fastapi import FastAPI, Request, Body
from pydantic import BaseModel
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import FastAPI, status
from requests_aws4auth import AWS4Auth
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from opensearchpy import OpenSearch, RequestsHttpConnection
from typing import List
from collections import Counter
from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from tqdm import tqdm
from io import BytesIO
from pprint import pprint
from libs import s3_main_lib
from . import models
from discord.ext import commands
from discord.ui import Button, View

import discord
import imagehash
import pymysql
import os
import random
import requests
import datetime


pymysql.install_as_MySQLdb()

app = FastAPI()
logger.add("../logs/search_log_{time}", rotation="12:00")
templates = Jinja2Templates(directory="../app/app/templates/")

load_dotenv(dotenv_path="../app/secrets/.env")

# AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY")
# AWS_SECRET_KEY = os.environ.get("AWS_SECRET_KEY")
# AWS_REGION = os.environ.get("AWS_REGION")
# AWS_SERVICE = os.environ.get("AWS_SERVICE")

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

awsauth = AWS4Auth(
    AWS_ACCESS_KEY,
    AWS_SECRET_KEY,
    AWS_REGION,
    AWS_SERVICE,
)

es = OpenSearch(
    hosts=[{"host": HOST, "port": 443}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    timeout=30,
    max_retries=10,
    retry_on_timeout=True,
)

DATABASE_URL = f"mysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_DATABASE}"
engine = create_engine(DATABASE_URL, encoding="utf-8", pool_recycle=3600)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))


def get_db():
    db = db_session()
    try:
        yield db
    finally:
        db.close()

print(es.info())

class Image(BaseModel):
    imageId: int = Field(title="RDS id")
    imageUrl: str = Field(title="이미지 URL")
    imageWidth: int = Field(title="이미지 가로 길이")
    imageHeight: int = Field(title="이미지 세로 길이")


class ImageDto(BaseModel):
    images: List[Image] = Field(title="meme에 포함된 image들이 있는 리스트")
    count: int = Field(title="images에 들어있는 image의 개수")


class Meme(BaseModel):
    memeId: int = Field(title="RDS id")
    title: str = Field(title="제목")
    image: ImageDto = Field(title="image에 대한 정보")
    # tags: List[str] = Field(title="태그 목록")
    viewCount: int = Field(title="조회수")
    shareCount: int = Field(title="공유수")
    createdDate: str = Field(title="생성일")
    modifiedDate: str = Field(title="수정일")


class SearchDto(BaseModel):
    memes: List[Meme] = Field(title="meme들이 있는 리스트")
    count: int = Field(title="memes에 들어있는 meme의 개수")


def create_index(_index):
    resp = es.indices.create(
        index=_index,
        body={
            "settings": {
                "index": {
                    "analysis": {
                        "analyzer": {
                            "korean": {"type": "custom", "tokenizer": "seunjeon"},
                            "ngram_analyzer": {"tokenizer": "ngram_tokenizer"},
                        },
                        "tokenizer": {
                            "seunjeon": {
                                "type": "seunjeon_tokenizer",
                                "index_poses": [
                                    "UNK",
                                    "EP",
                                    "M",
                                    "N",
                                    "SL",
                                    "SH",
                                    "SN",
                                    "V",
                                    "VCP",
                                    "XP",
                                    "XS",
                                    "XR",
                                ],
                            },
                            "ngram_tokenizer": {
                                "type": "ngram",
                                "min_gram": "2",
                                "max_gram": "3",
                            },
                        },
                    },
                    "max_ngram_diff": "4",
                }
            },
            "mappings": {
                "properties": {
                    "name": {
                        "type": "text",
                        "analyzer": "korean",
                        "fields": {
                            "ngram": {"type": "text", "analyzer": "ngram_analyzer"}
                        },
                    },
                    "tags": {
                        "type": "text",
                        "analyzer": "korean",
                        "fields": {
                            "ngram": {"type": "text", "analyzer": "ngram_analyzer"}
                        },
                    },
                    "image_url": {"type": "text"},
                }
            },
        },
    )

    return resp


def delete_index(_index):
    es.indices.delete(index=_index)


def snake_to_camel(word):
    splited_word = word.split("_")
    if len(splited_word) >= 2:
        return splited_word[0] + ''.join(x.title() for x in splited_word[1:])
    return word


def sort_data(datas, sort):
    if not sort:
        return datas

    splited_sort = sort.split(",")
    if len(splited_sort) == 2:
        key, order = splited_sort
    else:
        key = splited_sort[0]
        order = "desc"
    return sorted(datas, key=lambda x: x[key], reverse=True if order == "desc" else False)


def clean_data(datas):
    converted_datas = []
    
    datas = [d["_source"] for d in datas]
    for data in datas:
        converted_data = {}
        for key in data.keys():
            # if key == "tags":
            #     continue
            if key == "images":
                converted_data["image"] = {"images": [], "count": 0}

                for image in data[key].split(","):
                    try:
                        image_id, image_url, image_width, image_height = image.split("||")
                        
                        converted_image = {}
                        converted_image["imageId"] = image_id
                        converted_image["imageUrl"] = image_url
                        converted_image["imageWidth"] = image_width
                        converted_image["imageHeight"] = image_height
                        converted_data["image"]["images"].append(converted_image)
                    except:
                        print(image)
                converted_data["image"]["count"] = len(converted_data["image"]["images"])
            else:
                converted_data[snake_to_camel(key)] = data[key]

        converted_datas.append(converted_data)
    return converted_datas


def get_search_sholud_query(keyword):
    should_query = [{"match": {"name": {"query": keyword, "operator": "and", "boost": 3}}},
                    {"match": {"tags": {"query": keyword, "operator": "and", "boost": 3}}},
                    {"match": {"name": {"query": keyword, "operator": "or"}}},
                    {"match": {"tags": {"query": keyword, "operator": "or"}}},
                    {"match_phrase": {"name.ngram": keyword}},
                    {"match_phrase": {"tags.ngram": keyword}},
                    {
                        "bool": {
                            "should": [
                                {"match": {"translator": "Constance Garnett"}},
                                {"match": {"translator": "Louise Maude"}},
                            ]
                        }
                    }]

    return should_query


@app.get("/search-page", response_class=HTMLResponse)
def search(request: Request):
    return templates.TemplateResponse("search.html", context={"request": request})


def get_word_count(data, target_tag):
    tags = []
    for d in data:
        tags.extend(d['tags'])
    counter_dict = Counter(tags)

    del counter_dict[target_tag]
    return counter_dict


@app.get("/recommend-tags")
def recommend_tags(tag: str):
    _index = "meme"

    doc = {
        "query": {
            "bool": {
                "should": [
                    {"match": {"tags": {"query": tag}}},
                    {
                        "bool": {
                            "should": [
                                {"match": {"translator": "Constance Garnett"}},
                                {"match": {"translator": "Louise Maude"}},
                            ]
                        }
                    },
                ]
            },
        }
    }

    res = es.search(index=_index, body=doc)
    # print(res['hits']['hits'])
    data = get_word_count(clean_data(res["hits"]["hits"]), tag)
    data = dict(sorted(data.items(), key=lambda item: item[1], reverse=True))
    result = {"data": data}
    return JSONResponse(content=result)


@app.get(
    path="/search",
    description="검색 API",
    status_code=status.HTTP_200_OK,
    response_model=SearchDto,
    responses={200: {"description": "200 응답 데이터는 data 키 안에 들어있음"}},
)
async def search(request: Request, keyword: str, offset: int = 0, limit: int = 30, sort: str = ""):
    logger.info(f"[{request.client.host}] keyword: {keyword}")

    _index = "meme"  # index name

    doc = {
        "query": {
            "bool": {
                "should": get_search_sholud_query(keyword),
                "minimum_should_match": 1,
                "filter": {
                    "exists" : {"field" : "images"}
                }
            }
        },
        "from": offset,
        "size": limit,
        "sort": [{"_score": "desc"}],
    }

    res = es.search(index=_index, body=doc)
    # print(res['hits']['hits'])
    memes = clean_data(res["hits"]["hits"])
    result = {"memes": sort_data(memes, sort), "count": len(memes)}
    return JSONResponse(content=result)


@app.get(
    path="/search/tag",
    description="태그 검색 API",
    status_code=status.HTTP_200_OK,
    response_model=SearchDto,
    responses={200: {"description": "200 응답 데이터는 data 키 안에 들어있음"}},
)
async def search_by_tag(request: Request, keyword: str, offset: int = 0, limit: int = 30, sort: str = ""):
    logger.info(f"[{request.client.host}] keyword: {keyword}")

    db = db_session()
    result = {"memes": [], "count": 0}
    if db.query(models.TAG).filter_by(name=keyword).first():
        _index = "meme"  # index name

        doc = {
            "query": {
                "bool": {
                    "should": [
                        # {"match": {"tags": {"query": keyword}}},
                        {"match_phrase": {"tags.ngram": keyword}},
                        {
                            "bool": {
                                "should": [
                                    {"match": {"translator": "Constance Garnett"}},
                                    {"match": {"translator": "Louise Maude"}},
                                ]
                            }
                        },
                    ],
                    "minimum_should_match": 1,
                    "filter": {
                        "exists" : {"field" : "images"}
                    }
                }
            },
            "from": offset,
            "size": limit,
            "sort": [{"_score": "desc"}],
        }

        res = es.search(index=_index, body=doc)
        memes = clean_data(res["hits"]["hits"])
        result = {"memes": sort_data(memes, sort), "count": len(memes)}

    db.close()
    return JSONResponse(content=result)


@app.get(
    path="/search/collection/{collection_id}",
    description="특정 보드 내의 밈 검색 API",
    status_code=status.HTTP_200_OK,
    response_model=SearchDto,
    responses={200: {"description": "200 응답 데이터는 data 키 안에 들어있음"}},
)
async def search_in_collection(request: Request, collection_id: int, keyword: str, offset: int = 0, limit: int = 30, sort: str = ""):
    db = db_session()
    result = []

    meme_collections = db.query(models.MEME_COLLECTION).filter_by(collection_id=collection_id)
    meme_ids = [str(meme_collection.meme_id) for meme_collection in meme_collections]
    logger.info(f"meme_ids = {meme_ids}")

    _index = "meme"  # index name

    doc = {
        "query": {
            "bool": {
                "should": get_search_sholud_query(keyword),
                "minimum_should_match": 1,
                "filter": [
                    {"terms": {
                        "meme_id": meme_ids
                    }},
                    {"exists" : {"field" : "images"}}
                ]
            }
        },
        "from": offset,
        "size": limit,
        "sort": [{"_score": "desc"}],
    }

    res = es.search(index=_index, body=doc)
    memes = clean_data(res["hits"]["hits"])
    result = {"memes": sort_data(memes, sort), "count": len(memes)}

    db.close()
    return JSONResponse(content=result)


@app.get(
    path="/search/user/{user_id}",
    description="@nickname이 찾는 그 밈 API",
    status_code=status.HTTP_200_OK,
    response_model=SearchDto,
    responses={200: {"description": "200 응답 데이터는 data 키 안에 들어있음"}},
)
async def search_by_nickname(request: Request, keywords: str, offset: int = 0, limit: int = 30, sort: str = ""):
    logger.info(f"[{request.client.host}] keywords: {keywords}")

    RANDOM_KEYWORD_NUM = 3
    keyword_list = keywords.split(",")
    if len(keyword_list) > RANDOM_KEYWORD_NUM:
        target_keywords = " ".join(random.shuffle(keyword_list)[:RANDOM_KEYWORD_NUM])
    else:
        target_keywords = " ".join(keyword_list)

    _sort = {"_score": "desc"}
    if not target_keywords.strip():
        _sort = {"view_count": "desc"}

    _index = "meme"  # index name

    doc = {
        "from": offset,
        "size": limit,
        "sort": [_sort],
    }

    if target_keywords.strip():
        _query = {
            "bool": {
                "should": get_search_sholud_query(target_keywords),
                "minimum_should_match": 1,
                "filter": [
                    {"exists" : {"field" : "images"}}
                ]
            }
        }
        doc['query'] = _query

    res = es.search(index=_index, body=doc)
    memes = clean_data(res["hits"]["hits"])
    result = {"memes": sort_data(memes, sort), "count": len(memes)}
    return JSONResponse(content=result)


@app.get(
    path="/search/image",
    description="동일 이미지 검색 API",
    status_code=status.HTTP_200_OK,
    # response_model=SearchDto,
    responses={200: {"description": "200 응답 데이터는 data 키 안에 들어있음"}},
)
async def search_same_image(request: Request, ahash: str, dhash: str, phash: str, offset: int = 0, limit: int = 30):
    _index = "image"  # index name

    doc = {
        "query": {
            "bool": {
                "must": [
                    {"match": {"ahash": {"query": ahash, "operator": "and"}}},
                    {"match": {"dhash": {"query": dhash, "operator": "and"}}},
                    {"match": {"phash": {"query": phash, "operator": "and"}}},
                ]
            }
        },
        "from": offset,
        "size": limit,
        "sort": {"_score": "desc"},
    }

    res = es.search(index=_index, body=doc)
    images = clean_data(res["hits"]["hits"])
    result = {"images": sort_data(images), "count": len(images)}
    return JSONResponse(content=result)


@app.get(path="/log-viewer")
async def log_viewer(request: Request):
    return templates.TemplateResponse("log_viewer.html", context={"request": request})


import zipfile
@app.get(path="/log")
async def get_logs(request: Request):
    logs = []

    dir_path = "../logs/"
    for path in os.listdir(dir_path):
        try:
            if ".zip" in path:
                with zipfile.ZipFile(path, mode="r") as arch:
                    name_list = arch.namelist()
                    for name in name_list:
                        logs.append(arch.read(name))
            else:
                with open(dir_path + path, "rt") as f:
                    lines = f.readlines()
                    for line in lines:
                        logs.append(line)
        except:
            continue

    return logs


def get_same_images():
    _index = "image"  # index name

    db = db_session()

    import PIL
    images = db.query(models.IMAGE).all()
    pbar = tqdm(images)
    for image in pbar:
        url = image.image_url
        print(url)
        response = requests.get(url)
        origin_image = PIL.Image.open(BytesIO(response.content))
        ahash = str(imagehash.average_hash(origin_image))
        dhash = str(imagehash.dhash(origin_image))
        phash = str(imagehash.phash_simple(origin_image))

        doc = {
            "query": {
                "bool": {
                    "must": [
                        {"match": {"ahash": {"query": ahash, "operator": "and"}}},
                        {"match": {"dhash": {"query": dhash, "operator": "and"}}},
                        {"match": {"phash": {"query": phash, "operator": "and"}}},
                    ]
                    # ,"must_not": {
                    #     "match": {
                    #         "image_url": url
                    #     }
                    # }
                }
            },
            "from": 0,
            "size": 100,
            "sort": {"_score": "desc"},
        }

        res = es.search(index=_index, body=doc)
        images = clean_data(res["hits"]["hits"])
        result = {"images": sort_data(images, None), "count": len(images)}
        if result['count'] > 1:
            pprint(result)
    
    db.close()


class Account(BaseModel):
    accountId: int = Field(title="RDS id")
    name: str = Field(title="제목")
    password: str = Field(title="비밀번호")
    email: str = Field(title="이메일")
    saveCount: int = Field(title="저장수")
    shareCount: int = Field(title="공유수")
    createdDate: str = Field(title="생성일")
    modifiedDate: str = Field(title="수정일")


@app.get(path="/db-viewer")
async def db_viewer(request: Request):
    return templates.TemplateResponse("db_viewer.html", context={"request": request})

from fastapi.encoders import jsonable_encoder
@app.get(
    path="/db-viewer/users",
    status_code=status.HTTP_200_OK,
    response_model=Account
)
async def db_viewer_users(request: Request):
    db = db_session()
    users = db.query(models.ACCOUNT).order_by("account_id").all()
    content = {
        "users": jsonable_encoder(users)
    }
    db.close()
    return JSONResponse(content=content)


@app.get(path="/manage/tag")
async def tag_manager(request: Request):
    db = db_session()
    main_categories = db.query(models.MAIN_CATEGORY).all()
    categories = db.query(models.CATEGORY).all()

    category_datas = {}
    for main_category in main_categories:
        category_datas[main_category] = {}
        sub_categories = db.query(models.CATEGORY).filter_by(main_category_id = main_category.main_category_id)
        for sub_category in sub_categories:
            category_datas[main_category][sub_category] = db.query(models.TAG).filter_by(category_id = sub_category.category_id)

    db.close()

    data = {
        'category_datas': category_datas,
        'main_categories': main_categories,
        'categories': categories,
    }
    return templates.TemplateResponse("tag_manager.html", context={"request": request, "data": data})


class Tag(BaseModel):
    tag_name: str
    category_id: int


import json

@app.put(
    path="/manage/tag/{tag_id}",
    status_code=status.HTTP_200_OK
)
async def change_tag(tag_id: str, request: Request):
    db = db_session()
    body = await request.body()
    body = json.loads(body)

    tag_name = body['tag_name']
    category_id = body['category_id']

    # 중복
    if db.query(models.TAG).filter_by(name=tag_name, category_id=category_id).first():
        content = {
            "result": "duplicate"
        }
        db.close()
        return JSONResponse(content=content)

    tag = db.query(models.TAG).filter_by(tag_id=tag_id).first()
    tag.name = tag_name
    tag.category_id = category_id

    db.commit()
    db.close()

    content = {
        "result": "ok"
    }
    return JSONResponse(content=content)


@app.get(path="/manage/upload")
async def upload_manager(request: Request):
    db = db_session()
    main_categories = db.query(models.MAIN_CATEGORY).all()
    categories = db.query(models.CATEGORY).all()
    tags = db.query(models.TAG).all()
    db.close()

    data = {
        'main_categories': main_categories,
        'categories': categories,
        'tags': tags
    }
    return templates.TemplateResponse("upload_manager.html", context={"request": request, "data": data})


@app.post(path="/manage/meme/upload")
async def upload_meme(request: Request):
    db = db_session()
    body = await request.form()

    image = body['image']
    name = body['name']
    description = body['description']
    main_category_id = body['mainCategoryId']
    category_id = body['subCategoryId']
    selected_tag_ids = body['selectedTagIds'].split(",")
    selected_tag_ids = list(filter(lambda x: len(x) > 0, selected_tag_ids))

    print(image, name, description, main_category_id, category_id, selected_tag_ids)
    image_name = image.filename
    image_bytes = await image.read()

    data_io = io.BytesIO(image_bytes)
    from PIL import Image
    img = Image.open(data_io)
    
    ext = image_name.split(".")[-1]
    img_name = f"{hashlib.sha256(image_name.encode('utf-8')).hexdigest()}.{ext}"
    response = s3_main_lib.upload_image(image_bytes, img_name)
    base_url = "https://jjmeme-bucket-2.s3.amazonaws.com/"
    full_url = f"{base_url}{response.key}"

    meme = models.MEME(name=name, description=description, created_date=datetime.datetime.now())
    db.add(meme)
    db.flush()
    db.refresh(meme)

    image = models.IMAGE(image_url=full_url, width=img.width, height=img.height, meme_id=meme.meme_id)
    db.add(image)
    for selected_tag_id in selected_tag_ids:
        selected_tag_id = int(selected_tag_id)
        tag = models.MEME_TAG(meme_id=meme.meme_id, tag_id=selected_tag_id)
        db.add(tag)
    
    db.commit()
    db.close()

    content = {
        "result": "ok"
    }
    return JSONResponse(content=content)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=">", intents=intents)

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")

@bot.event
async def on_guild_join(guild):
    guild = bot.get_guild(guild.id)
    target_channel = guild.text_channels[0]
    channels = sorted(guild.text_channels, key=lambda x: x.position)
    logger.info(f"Joined new Server/id: {guild.id}, name: {guild.name}")
    for channel in channels:
        if "moderator-only" not in channel.name:
            target_channel = channel
            break
    join_message = """
안녕하세요, thismeme 봇을 설치해주셔서 감사합니다

사용법)
1. 키워드 검색
    >밈 키워드
    ex) >밈 박명수

2. 결과로 나온 검색 결과 버튼 클릭
"""
    await target_channel.send(join_message)

@bot.command(aliases=['그밈', '그 밈', '밈'])
async def search_by_bot(ctx, *keyword):
    full_keyword = " ".join(keyword)
    logger.info(f"keyword: {full_keyword}")

    _index = "meme"

    doc = {
        "query": {
            "bool": {
                "should": get_search_sholud_query(full_keyword),
                "minimum_should_match": 1,
                "filter": {
                    "exists" : {"field" : "images"}
                }
            }
        },
        "from": 0,
        "size": 10,
        "sort": [{"_score": "desc"}],
    }

    res = es.search(index=_index, body=doc)
    datas = res["hits"]["hits"]

    if not datas:
        view = View()
        button = Button(label="밈 등록하러가기", url="https://app.thismeme.me")
        await ctx.send(embed=discord.Embed(title=f"'{keyword}' 에 해당하는 밈이 없어요 :( 등록하러 가실래요?"), view=view)
    else:
        view = View()
        for data in datas:
            button = Button(label=data['_source']['name'])
            async def make_callback(data):
                async def _callback(interaction):
                    await interaction.response.send_message(f"https://app.thismeme.me/memes/{data['_id']}")
                return _callback
            _callback = await make_callback(data)
            button.callback = _callback
            view.add_item(button)

        await ctx.send(embed=discord.Embed(title="밈 선택하기"), view=view)


async def run():
    await bot.start(DISCORD_TOKEN)


asyncio.create_task(run())


@app.get(path="/admin/meme/list")
async def admin_meme_list(request: Request):
    db = db_session()
    memes = db.query(models.MEME).all()
    db.close()

    data = {
        'memes': memes,
        'total_count': len(memes),
    }
    return templates.TemplateResponse("admin/meme/list.html", context={"request": request, "data": data})

@app.get(path="/admin/meme/detail/{meme_id}")
async def admin_meme_detail(request: Request, meme_id: str):
    db = db_session()
    meme, image = db.query(models.MEME, models.IMAGE, models.MEME_TAG, models.TAG).filter(models.MEME.meme_id == models.IMAGE.meme_id).filter_by(meme_id=meme_id)[0]
    db.close()

    data = {
        'meme': meme,
        'image': image
    }
    return templates.TemplateResponse("admin/meme/detail.html", context={"request": request, "data": data})