import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field 
from contextlib import asynccontextmanager
import pymongo
import json

from api.jd_generate import ParagraphInput, JDResponse, generate_jd
from api.suggest_keyword import KeywordSuggestionRequest, KeywordSuggestionResponse, keyword_service
from api.candidate_comparison import CandidateCompareRequest, CandidateCompareResponse, compare_candidates
from api.create_jd_embeddings import generate_jd_embedding, JDEmbeddingRequest,JDEmbeddingResponse
from api.manual_jd_generate import ParagraphInput, manual_generate_jd, JDResponse

from rule_base.vector_search import search_candidates_by_jd, CandidateSearchRequest

from contact_out.search import parse_user_query, normalize_filters, process_candidates


from utils.llm_config_loader import LoadLLMConfig
from utils.load_project_config import LoadProjectConfig

load_dotenv()

LLM_CFG = LoadLLMConfig()
PROJECT_CFG = LoadProjectConfig()

mongodb_client = None       # Global MongoDB client variable

router = APIRouter()

class ContactOutSearchRequest(BaseModel):
    query: str
    limit: int = 2
    jd_id: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    global mongodb_client
    try: 
        print("🚀 RecruiiT API Starting...")
        print(f"✅ LangSmith Tracing: {PROJECT_CFG.langsmith_tracing}")
        print(f"✅ LangSmith Project: {PROJECT_CFG.langsmith_project_name}")
        print(f"✅ Active LLM Model: {LLM_CFG.active_model}")
        print(f"✅ LLM Temperature: {LLM_CFG.active_temperature}")
        print("🎯 API Ready at http://0.0.0.0:8010")


        # Connect to MongoDB once
        mongodb_uri = os.getenv("MONGODB_URI") or "mongodb+srv://parmarkrrish2643:kIcue54sGLtVh8uE@cluster0.ksou84b.mongodb.net/Recruiit?retryWrites=true&w=majority&appName=Cluster0"
        
        mongodb_client = pymongo.MongoClient(
            mongodb_uri,
            maxPoolSize=50,         # Maximum connections in pool
            minPoolSize=10,         # Minimum connections to maintain
            maxIdleTimeMS=30000,    # Close connections after 30s idle
            serverSelectionTimeoutMS=5000,  # 5s timeout for server selection
            connectTimeoutMS=10000,          # 10s connection timeout
            retryWrites=True
        )
        
        # Test the connection
        mongodb_client.admin.command('ping')
        print("✅ MongoDB connection pool established successfully")
        print("🎯 API Ready at http://0.0.0.0:8010")
    

    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        mongodb_client = None

    yield

    # Shutdown: Close MongoDB connection
    if mongodb_client:
        mongodb_client.close()
        print("🔌 MongoDB connection closed")



app = FastAPI(
    title="Resume and Job Description Processing API",
    version="1.0.0",
    lifespan=lifespan,
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_mongodb_client():
    """Dependency to get the MongoDB client"""
    if not mongodb_client:
        raise HTTPException(status_code=500, detail="MongoDB connection not available")
    return mongodb_client


# JD Generation endpoint 
@app.post("/generate-jd", response_model=JDResponse)
async def generate_job_description(input_data: ParagraphInput):
    try:
        return await generate_jd(input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating job description: {str(e)}")


# JD Matching endpoint
# @app.post("/match-resume")
# async def match_resume(jd_request: JDRequest):
#     try:
#         return await match_resume_logic(jd_request)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error matching resume: {str(e)}")


@app.post("/suggest-keywords", response_model=KeywordSuggestionResponse)
async def suggest_keywords(request: KeywordSuggestionRequest):
    """Suggest missing keywords before JD generation"""
    try:
        return await keyword_service.get_suggestions(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/candidates-compare", response_model=CandidateCompareResponse)
async def compare_candidates_endpoint(input_data: CandidateCompareRequest):
    try:
        return await compare_candidates(input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error comparing candidates: {str(e)}")

@app.post("/jd-embedding", response_model=JDEmbeddingResponse)
async def generate_jd_embedding_endpoint(input_data: JDEmbeddingRequest):
    try:
        return generate_jd_embedding(input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating JD embedding: {str(e)}") 


@app.post("/fetch-candidates")
async def search_candidates_endpoint(request: CandidateSearchRequest):
    """Search and rank candidates based on job description requirements"""
    try:
        client = get_mongodb_client()

        result = await search_candidates_by_jd(
            jd_id=request.jd_id,
            user_query= request.query,
            client=client,  
            debug=request.debug
        )
    
        return result 
    

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-manual-jd", response_model=JDResponse)
async def generate_manual_job_description(input_data: ParagraphInput):
    try:
        jd_response = await manual_generate_jd(input_data)
        return jd_response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating manual job description: {str(e)}")



# @app.post("/fetch-external-candidates")
# def fetch_external_candidates(req: ContactOutSearchRequest):
#     try:
#         raw_filters = parse_user_query(req.query)
#         filters = normalize_filters(raw_filters)
#         print("\n🧩 Final Filters Used:", json.dumps(filters, indent=2))
#         process_candidates(filters=filters, limit=req.limit, jd_id=req.jd_id, query=req.query)
#         return {"message": "✅ External candidates fetched and stored successfully."}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error fetching candidates: {str(e)}")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
