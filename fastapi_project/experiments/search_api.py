from fastapi import FastAPI, status
import tweepy
from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import os
from opensearchpy import OpenSearch
from typing import List


load_dotenv()


app = FastAPI()
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_KEY")
AWS_REGION = os.environ.get("AWS_REGION")
AWS_SERVICE = os.environ.get("AWS_SERVICE")

HOST = os.environ.get("HOST")

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

print(es.info())


class Meme(BaseModel):
    timestamp: str = Field(title="생성일")
    id: int = Field(title="RDS id")
    title: str = Field(title="제목")
    description: str = Field(title="설명")
    image_url: str = Field(title="이미지 URL")
    tags: List[str] = Field(title="태그 목록")


class SearchDto(BaseModel):
    id: str = Field(title="index id", description="_id")
    index: str = Field(title="index name", description="_index")
    type: str = Field(title="index type", description="_type")
    score: float = Field(title="검색 결과 점수", description="_score")
    source: Meme = Field(title="밈 데이터", description="_source")


def create_index(_index):
    resp = es.indices.create(
        index=_index,
        body={
            "settings": {
                "index": {
                    "analysis": {
                        "analyzer": {
                            "korean": {"type": "custom", "tokenizer": "seunjeon"}
                        },
                        "tokenizer": {"seunjeon": {"type": "seunjeon_tokenizer"}},
                    }
                }
            },
            "mappings": {
                "properties": {
                    "description": {"type": "text", "analyzer": "korean"},
                    "title": {"type": "text", "analyzer": "korean"},
                    "tags": {"type": "text", "analyzer": "korean"},
                    "image_url": {"type": "text"},
                }
            },
        },
    )

    return resp


def clean_data(data):
    for d in data:
        print("???", d)
        # if not d['_source']['tags']:
        #     d['_source']['tags'] = []
        # else:
        #     d['_source']['tags'] = d['_source']['tags'].split(",")

    return data


@app.get(
    path="/search",
    description="검색 API",
    status_code=status.HTTP_200_OK,
    response_model=SearchDto,
    responses={200: {"description": "200 응답 데이터는 data 키 안에 들어있음"}},
)
async def search(keyword: str, offset: int = 0, limit: int = 10):
    _index = "mm"  # index name

    doc = {
        "query": {
            "bool": {
                "should": [
                    {"match": {"title": {"query": keyword, "boost": 1}}},
                    {"match": {"description": {"query": keyword, "boost": 3}}},
                    {"match": {"tags": {"query": keyword, "boost": 100}}},
                    {
                        "bool": {
                            "should": [
                                {"match": {"translator": "Constance Garnett"}},
                                {"match": {"translator": "Louise Maude"}},
                            ]
                        }
                    },
                ]
            }
        },
        # "from": offset,
        # "size": limit,
        "sort": [{"_score": "desc"}],
    }

    res = es.search(index=_index, body=doc)
    # print(res['hits']['hits'])
    result = {"data": clean_data(res["hits"]["hits"])}
    return JSONResponse(content=result)
