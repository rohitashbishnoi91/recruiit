import os
import yaml
from dotenv import load_dotenv
from pyprojroot import here

load_dotenv()

class LoadLLMConfig:
    def __init__(self) -> None:
        with open(here("configs/llm_config.yml")) as cfg:
            app_config = yaml.load(cfg, Loader=yaml.FullLoader)

        os.environ['GEMINI_API_KEY'] = os.getenv("GEMINI_API_KEY")

        # Gemini LLM config
        self.gemini_llm_model = app_config["gemini_llm"]["model"]
        self.gemini_llm_temperature = float(app_config["gemini_llm"]["temperature"])
        self.gemini_llm_max_tokens = int(app_config["gemini_llm"]["max_tokens"])

      
        # Default provider
        self.default_provider = app_config["default_provider"]

        self.active_model = getattr(self, f"{self.default_provider}_model")
        self.active_temperature = getattr(self, f"{self.default_provider}_temperature")
        self.active_max_tokens = getattr(self, f"{self.default_provider}_max_tokens")
