import os
import openai
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai.api_key)

def call_gpt_summary(query):
    prompt = f"""
다음 질문에 대한 답변을 간단한 한 줄 요약을 작성하세요. 질문을 해결할 수 있는 답변이어야 합니다.[질문] {query}[요약 답변]""".strip()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=100
    )
    return response.choices[0].message.content.strip()

def search_similar_documents(query, model, index, documents, metadatas, top_k=3):
    query_embedding = model.encode([query])
    D, I = index.search(query_embedding, top_k)
    return [(documents[i], metadatas[i]) for i in I[0]]

def answer_query(query, meta):
    prompt = f""" 다음 민원 문서를 참고하여 질문에 대해 자세히 설명해주세요. [질문] {query} [민원 문서] {meta} [답변] """.strip()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "당신은 민원 정보를 잘 알려주는 공공서비스 상담 챗봇입니다."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1
    )
    return response.choices[0].message.content.strip()