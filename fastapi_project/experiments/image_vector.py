import numpy as np
from keras.applications.inception_resnet_v2 import preprocess_input, InceptionResNetV2
from keras.models import Model
from keras_preprocessing import image
from opensearchpy import OpenSearch, RequestsHttpConnection
from dotenv import load_dotenv
from requests_aws4auth import AWS4Auth

import os

load_dotenv(dotenv_path="../secrets/.env")


AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_KEY")
AWS_REGION = os.environ.get("AWS_REGION")
AWS_SERVICE = os.environ.get("AWS_SERVICE")

HOST = os.environ.get("HOST")

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


def create_vectorized_index():
    index = "vector-test"
    body = {
        "mappings": {
            "properties": {
                "productInfo": {
                    "type": "text"
                },
                "vector": {
                    "type": "knn_vector",
                    "dimension": 1536
                }
            }
        }
    }

    es.indices.create(index, body=body)


def vectorize(filepath):
    model = InceptionResNetV2()
    layer_name = 'avg_pool'
    intermediate_layer_model = Model(inputs=model.input, outputs=model.get_layer(layer_name).output)

    img = image.load_img(filepath, target_size=(299, 299))
    x = image.img_to_array(img)
    x = np.expand_dims(x, axis=0)
    x = preprocess_input(x)
    intermediate_output = intermediate_layer_model.predict(x)
    return intermediate_output[0]


# print(vectorize("./crawling_images/crawling_images/20221210_13189_어몽어스 짤/001.jpg"))


def index_to_vector(info, vector):
    index = "vector-test"
    doc = {
        'productInfo': info,
        'vector': vector
    }

    response = es.index(index=index, body=doc)
    return response


def search_for_vector(vector):
    index = "vector-test"
    body = {
        "size": 20,
        "query": {
            "knn": {
                "vector": {
                    "vector": vector,
                    "k": 20
                }
            }
        }
    }

    response = es.search(index=index, body=body)

    return response['hits']['hits']


if __name__ == "__main__":
    # print(es.info())

    # print(create_vectorized_index())

    dir_path = "../tagged_images/"

    # list to store files
    images = []
    # Iterate directory
    for path in os.listdir(dir_path):
        # check if current path is a file
        if os.path.isfile(os.path.join(dir_path, path)):
            images.append(path)

    # for img in images:
    #     vector = vectorize(dir_path + img)
    #     print(img, vector)
    #     index_to_vector(img, vector)

    # vector = vectorize("./crawling_images/crawling_images/2022125_15556_루피 짤/106.jpg")
    # vector = vectorize("./crawling_images/crawling_images/2022125_14551_페페 짤/015.jpg")
    vector = vectorize("./똘페2.jpeg")
    # vector = vectorize("./crawling_images/crawling_images/20221210_13189_어몽어스 짤/018.jpg")
    result = search_for_vector(vector)

    for data in result:
        # print(data['_source']['productInfo'])
        print(data['_score'], data['_source']['productInfo'])
