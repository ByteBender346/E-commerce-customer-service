from langchain.chat_models import init_chat_model

from dianshang.conf.config import settings

llm = init_chat_model(
    model=settings.llm_model,
    model_provider="openai",
    api_key=settings.llm_api_key,
    base_url=settings.llm_base_url,
    temperature=0,
)

if __name__ == '__main__':
    for chunk in llm.stream("你是电商客服助手，请用一句话介绍你能为用户提供哪些服务。"):
        print(chunk.text, end="", flush=True)
