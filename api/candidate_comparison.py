import os
import langsmith as ls
from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from datetime import datetime 

from utils.llm_config_loader import LoadLLMConfig
from utils.load_project_config import LoadProjectConfig

load_dotenv()

LLM_CFG = LoadLLMConfig()
PROJECT_CFG = LoadProjectConfig()

# MongoDB connection
MONGODB_URL = os.getenv("MONGODB_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME", "recruiit")

client = AsyncIOMotorClient(MONGODB_URL)
db = client[DATABASE_NAME]

class CandidateCompareRequest(BaseModel):
    candidateIds: List[str] = Field(..., description="Array of candidate ObjectIds to compare", min_items=2)
    userId: Optional[str] = Field(None, description="ObjectId of the authenticated user")  # Made optional
    # companyId: str = Field(..., description="ObjectId of the user's company")

class CandidateDetailObject(BaseModel):
    # Based on your actual DB schema
    candidateId: str
    id: Optional[int] = None  
    Name: Optional[str] = None
    Title: Optional[str] = None
    Headline: Optional[str] = None
    Summary: Optional[str] = None
    Industry: Optional[str] = None
    Location: Optional[str] = None
    Skills: List[Any] = []  
    Certifications: List[Any] = []
    Publications: List[Any] = []
    Education: List[Any] = []
    Experience: List[Any] = []
    Experience_in_days: Optional[int] = None
    Profile_url: Optional[str] = None

class CandidateCompareResponse(BaseModel):
    comparedCandidates: List[CandidateDetailObject] = Field(..., description="Array of detailed candidate objects for comparison")
    comparison_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata for comparison")

def validate_object_ids(ids: List[str]) -> List[ObjectId]:
    try:
        return [ObjectId(id_str) for id_str in ids]
    except Exception as e:
        raise ValueError(f"Invalid ObjectId format: {str(e)}")

# async def authenticate_and_authorize_user(user_id: str) -> bool:
#     try:
#         user_object_id = ObjectId(user_id)
#         # company_object_id = ObjectId(company_id)
        
#         user = await db.users.find_one({
#             "_id": user_object_id,
#             # "companyreference": company_object_id,  
#             "$or": [
#                 {"currentstatustext": {"$ne": "Deleted"}},
#                 {"currentstatustext": {"$exists": False}}
#             ]
#         })
        
#         return user is not None
#     except Exception:
#         return False

async def fetch_candidate_profiles(candidate_ids: List[ObjectId]) -> List[Dict]:
    """Fetch full candidate profiles from MongoDB"""
    try:
        candidates = await db.candidate.find({
            "_id": {"$in": candidate_ids}
        }).to_list(length=None)
        
        return candidates
    except Exception as e:
        raise ValueError(f"Error fetching candidate profiles: {str(e)}")

def format_candidate_for_comparison(candidate_doc: Dict) -> CandidateDetailObject:
    try:
        return CandidateDetailObject(
            candidateId=str(candidate_doc["_id"]),
            id=candidate_doc.get("id"),
            Name=candidate_doc.get("Name"),
            Title=candidate_doc.get("Title"),
            Headline=candidate_doc.get("Headline"),
            Summary=candidate_doc.get("Summary"),
            Industry=candidate_doc.get("Industry"),
            Location=candidate_doc.get("Location"),
            Skills=candidate_doc.get("Skills", []),
            Certifications=candidate_doc.get("Certifications", []),
            Publications=candidate_doc.get("Publications", []),
            Education=candidate_doc.get("Education", []),
            Experience=candidate_doc.get("Experience", []),
            Experience_in_days=candidate_doc.get("Experience in days"),  
            Profile_url=candidate_doc.get("Profile url")  
        )
    except Exception as e:
        raise ValueError(f"Error formatting candidate data: {str(e)}")

async def compare_candidates(input_data: CandidateCompareRequest) -> CandidateCompareResponse:
    with ls.tracing_context(project=PROJECT_CFG.langsmith_project_name, name="candidate_comparison"):
        try:
            # is_authorized = await authenticate_and_authorize_user(
            #     input_data.userId, 
            #     # input_data.companyId
            # )
            # if not is_authorized:
            #     raise ValueError("User not authorized to access candidate profiles")
            
            candidate_object_ids = validate_object_ids(input_data.candidateIds)
            
            if len(candidate_object_ids) < 2:
                raise ValueError("At least 2 candidates required for comparison")
            
            if len(candidate_object_ids) > 10: 
                raise ValueError("Maximum 10 candidates allowed for comparison")
            
            candidate_docs = await fetch_candidate_profiles(candidate_object_ids)
        
            found_ids = {str(doc["_id"]) for doc in candidate_docs}
            requested_ids = set(input_data.candidateIds)
            missing_ids = requested_ids - found_ids
            
            if missing_ids:
                raise ValueError(f"Candidates not found: {list(missing_ids)}")
            
            compared_candidates = []
            for candidate_doc in candidate_docs:
                formatted_candidate = format_candidate_for_comparison(candidate_doc)
                compared_candidates.append(formatted_candidate)
            
            # Generate comparison metadata
            comparison_metadata = {
                "total_candidates": len(compared_candidates),
                "comparison_timestamp": datetime.utcnow().isoformat(),
                "requested_by_user": input_data.userId or "anonymous",  # Handle optional userId
                # "company_id": input_data.companyId,
                "candidate_ids_order": input_data.candidateIds
            }
            
            # Create response
            response = CandidateCompareResponse(
                comparedCandidates=compared_candidates,
                comparison_metadata=comparison_metadata
            )
            
            print(f"Candidate Comparison Completed Successfully:")
            print(f"   - Candidates Compared: {len(compared_candidates)}")
            print(f"   - User ID: {input_data.userId or 'anonymous'}")
            # print(f"   - Company ID: {input_data.companyId}")
            print(f"   - Automatically traced in LangSmith!")
            
            return response
            
        except ValidationError as e:
            print(f"Validation Error: {str(e)}")
            raise ValueError(f"Input validation error: {str(e)}")
        except Exception as e:
            print(f"Comparison Error: {str(e)}")
            raise ValueError(f"Failed to compare candidates: {str(e)}")
