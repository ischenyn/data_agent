from huggingface_hub import InferenceClient, AsyncInferenceClient

from app.config.app_config import EmbeddingConfig, app_config


class LocalEmbeddingClient:
    """
    直接对接自建的 embedding 服务(如 TEI),
    绕过 HuggingFaceEndpointEmbeddings 对 model 必须是仓库名而非 URL 的限制。
    """

    def __init__(self, base_url: str):
        self.client = InferenceClient(model=base_url)
        self.async_client = AsyncInferenceClient(model=base_url)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        texts = [t.replace("\n", " ") for t in texts]
        return self.client.feature_extraction(text=texts).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        texts = [t.replace("\n", " ") for t in texts]
        result = await self.async_client.feature_extraction(text=texts)
        return result.tolist()

    async def aembed_query(self, text: str) -> list[float]:
        return (await self.aembed_documents([text]))[0]


class EmbeddingClientManager:
    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self.client: LocalEmbeddingClient | None = None

    def init(self):
        self.client = LocalEmbeddingClient(f"http://{self.config.host}:{self.config.port}")


embedding_client_manager = EmbeddingClientManager(app_config.embedding)
