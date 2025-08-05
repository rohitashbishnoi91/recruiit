from pydantic import BaseModel
from typing import List

class JDEmbeddingRequest(BaseModel):
    jd_text: str

class JDEmbeddingResponse(BaseModel):
    embedding: List[float]
    dimension: int