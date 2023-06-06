import os
from dotenv import load_dotenv, find_dotenv
import openai
from retry import retry 


load_dotenv(find_dotenv("secrets/.env"))

openai.api_key = os.getenv("OPENAI_API_KEY")

@retry(Exception, tries=5, delay=2, backoff=2, max_delay=120)
def get_openai_categorizing(categories, tag):
    PROMPT = """
    You are a helpful tagging and categorizing assistant. 
    We had {categories} categories. 
    Please recommend me which category the tag for {tag} belongs to. 
    Don't add anything else, just say the word that corresponds to the category name.
    """

    PROMPT = PROMPT.format(categories=categories, tag=tag)

    completion = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    temperature=0.0,
    messages=[
            {"role": "system", "content": PROMPT},
        ]
    )

    response = completion.choices[0].message.content
    return response


@retry(Exception, tries=5, delay=2, backoff=2, max_delay=120)
def get_openai_mbti_categorizing_by_name(name, tags):
    print(name, tags)
    PROMPT = """
너는 MBTI 전문가야
아래의 규칙에 따라 "{name}, {tags}" 를 분류해줘

내향 (I) vs 외향 (E): 사람들이 에너지를 어디서 얻는지를 나타냅니다. 내향형은 내부 세계에서 에너지를 얻으며, 외향형은 외부 세계에서 에너지를 얻습니다.
감각 (S) vs 직관 (N): 사람들이 정보를 수집하는 주된 방식을 나타냅니다. 감각형은 현재의 실제 데이터와 사실에 주로 초점을 맞추며, 직관형은 패턴과 가능성에 주로 초점을 맞춥니다.
사고 (T) vs 감정 (F): 사람들이 결정을 내리고 정보를 처리하는 방식을 나타냅니다. 사고형은 논리와 분석을 중시하며, 감정형은 감정과 가치에 중점을 둡니다.
판단 (J) vs 인식 (P): 사람들이 세상과 대응하는 방식을 나타냅니다. 판단형은 계획적이고 조직적으로 행동하며, 인식형은 유연하고 적응적으로 행동합니다.

최종 분류 결과만 얘기해줘
최종 분류 결과 앞 뒤에 아무 말도 하지마
"""

    PROMPT = PROMPT.format(name=name, tags=tags)

    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        temperature=0.0,
        messages=[
                {"role": "system", "content": PROMPT},
            ],
        request_timeout=60,
    )

    response = completion.choices[0].message.content
    print(response)
    return response
