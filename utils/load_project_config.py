import os
import yaml
from dotenv import load_dotenv
from pyprojroot import here

load_dotenv()

with open(here("configs/project_config.yml")) as cfg:
    app_config = yaml.load(cfg, Loader=yaml.FullLoader)

class LoadProjectConfig:
    def __init__(self) -> None:
        
        # Load LangSmith config
        os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
        os.environ["LANGCHAIN_TRACING_V2"] = app_config["langsmith"]["tracing"]
        os.environ["LANGCHAIN_PROJECT"] = app_config["langsmith"]["project_name"]

        # LangSmith attributes
        self.langsmith_tracing = app_config["langsmith"]["tracing"]
        self.langsmith_project_name = app_config["langsmith"]["project_name"]

        # # Database config
        # self.mongodb_uri = os.getenv("MONGODB_URI")
        # self.database_name = app_config["database"]["database_name"]
        # self.collection_name = app_config["database"]["collection_name"]

        # # Vector search config
        # self.vector_index_name = app_config["vector_search"]["index_name"]
        # self.vector_similarity_metric = app_config["vector_search"]["similarity_metric"]
        # self.vector_dimensions = int(app_config["vector_search"]["dimensions"])
