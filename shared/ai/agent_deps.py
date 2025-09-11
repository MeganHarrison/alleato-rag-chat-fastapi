"""Agent dependencies for RAG system."""

from shared.utils.db_utils import db_pool


class AgentDeps:
    """Dependencies for the RAG agent."""
    
    def __init__(self):
        self.db_pool = db_pool
        self.settings = None
        self.user_preferences = {}
        self.query_history = []
        self.openai_client = None
    
    async def initialize(self):
        """Initialize dependencies."""
        from shared.utils.config import load_settings
        import openai
        
        if not self.settings:
            self.settings = load_settings()
        
        # Initialize database pool with improved connection
        try:
            await self.db_pool.initialize()
            print("Database connection successful in agent deps")
        except Exception as db_error:
            print(f"Database initialization failed, will use API fallbacks: {db_error}")
            # Set db_pool to None to trigger fallback mode
            self.db_pool = None
        
        if not self.openai_client:
            self.openai_client = openai.AsyncOpenAI(
                api_key=self.settings.llm_api_key,
                base_url=self.settings.llm_base_url
            )
    
    async def get_embedding(self, text: str) -> list[float]:
        """Generate embedding for text using OpenAI."""
        if not self.openai_client:
            await self.initialize()
        
        response = await self.openai_client.embeddings.create(
            model=self.settings.embedding_model,
            input=text
        )
        return response.data[0].embedding