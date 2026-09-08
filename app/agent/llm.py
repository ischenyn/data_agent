from app.config.app_config import load_app_config
from langchain.chat_models import init_chat_model

app_config = load_app_config()

model_name = app_config.llm.model_name
api_key = app_config.llm.api_key

llm = init_chat_model(
    model=model_name,
    api_key=api_key,
    temperature=0,
)
