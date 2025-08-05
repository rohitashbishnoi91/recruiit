from langchain_google_genai import GoogleGenerativeAIEmbeddings
from fastapi import HTTPException
import logging
import os
from pydantic import BaseModel
from typing import List

class JDEmbeddingRequest(BaseModel):
    jd_text: str

class JDEmbeddingResponse(BaseModel):
    embedding: List[float]
    dimension: int

logger = logging.getLogger(__name__)
GEMINI_API_KEY="AIzaSyBaYkOY_pT-mPTtsEy-MmdmqrkImtDKTds" 

def generate_embedding(request: JDEmbeddingRequest) -> JDEmbeddingResponse:
    try:
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-exp-03-07",
            google_api_key=GEMINI_API_KEY,
        )

        result = embeddings.embed_query(
            text=request.jd_text,
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=1536,
        )

        return JDEmbeddingResponse(embedding=result, dimension=len(result))

    except Exception as e:
        logger.error(f"Embedding generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))