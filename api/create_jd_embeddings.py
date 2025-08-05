import os
from dotenv import load_dotenv
from google import genai
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from google.genai import types
from pydantic import BaseModel, Field
from fastapi import HTTPException
import logging


load_dotenv()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
EMBEDDING_MODEL = "gemini-embedding-exp-03-07" # "models/text-embedding-004"

# print (f"Gemini API Key: {GEMINI_API_KEY}")

class JDEmbeddingRequest(BaseModel):
    jd_text: str = Field(..., description="Full job description text")

class JDEmbeddingResponse(BaseModel):
    embedding: list = Field(..., description="Vector embedding of JD")
    dimension: int = Field(..., description="Dimension of embedding")


def generate_jd_embedding(request: JDEmbeddingRequest) -> JDEmbeddingResponse:
    """Generate embedding for job description text"""
    try:
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-exp-03-07",
            google_api_key=GEMINI_API_KEY,
            )

        result = embeddings.embed_query(
            text= request.jd_text,
            task_type= "RETRIEVAL_QUERY", 
            output_dimensionality= 1536,
        )

        print(f"Generated embedding: {result}")
        
        logger.info(f"Generated embedding with {len(result)} dimensions")

        return JDEmbeddingResponse(
            embedding=result,
            dimension=len(result)
        )
        
    except Exception as e:
        error_msg = f"Embedding generation failed: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg) 


def main():
    # Example usage
    print("Starting JD embedding generation...")
    request = JDEmbeddingRequest(jd_text="Software Engineer with 5+ years experience in Python and cloud technologies.")
    response = generate_jd_embedding(request)
    print(response)

    print(f"Dimension: {response.dimension}")




if __name__ == "__main__":  
    main()



