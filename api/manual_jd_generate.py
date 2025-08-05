import os
import langsmith as ls
from pydantic import BaseModel, Field, ValidationError
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from utils.llm_config_loader import LoadLLMConfig

# Load environment variables
load_dotenv()

LLM_CFG = LoadLLMConfig()

# Setup the LLM instance with appropriate configurations
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=os.getenv("GEMINI_API_KEY"),
    temperature=LLM_CFG.active_temperature,
    max_output_tokens=1500,
)

# Define the input schema
class ParagraphInput(BaseModel):
    prompt: str = Field(..., description="User-provided job description prompt in a single paragraph")

# Define the structure of the Job Description
class JobDescriptionSection(BaseModel):
    job_title: str
    tags: list[str]
    years_of_experience: str
    about_the_role: str
    job_type_workplace_location: str
    key_responsibilities: list[str]  # Detailed responsibilities
    skills_required: list[str]  # Technical skills + experience levels
    qualifications: list[str]  # Education, soft skills, broader requirements
    what_we_offer: list[str]
    keywords: list[str]  # Extracted keywords

# Define the response schema
class JDResponse(BaseModel):
    full_description: JobDescriptionSection = Field(..., description="The full generated job description as a structured object")

# Optimized System Prompt for LLM
def get_system_prompt():
    return """You are an HR expert tasked with generating structured, professional job descriptions based on provided keywords.
    
Please generate a detailed job description in the following format:

- **Job Title**: Clear, concise title of the role.
- **About the Role**: Short paragraph describing the role and its significance.
- **Job Type & Workplace Location**: A single string (e.g., "Full-time, On-site").
- **Key Responsibilities**: At least 4-5 responsibilities starting with action verbs (e.g., "Design", "Collaborate").
- **Skills Required**: Categorized by type, formatted as:
    - "Category: skill1, skill2, skill3" (e.g., "Programming Languages: Python, SQL")
- **Qualifications**: List of required education, experience, and soft skills (e.g., "Bachelor's degree", "2+ years experience").
- **What We Offer**: List of benefits and career opportunities.
- **Keywords**: Relevant technical skills, tools, frameworks, and soft skills (e.g., "Python", "REST APIs").

The **Skills Required** section should have 5-7 categories with short, comma-separated skills under each category.

**Output Format**: Return the job description in the following JSON structure:
{{
    "job_title": "string",
    "tags": ["string"],
    "years_of_experience": "string",
    "about_the_role": "string",
    "job_type_workplace_location": "string",
    "key_responsibilities": ["string"],
    "skills_required": ["string"],
    "qualifications": ["string"],
    "what_we_offer": ["string"],
    "keywords": ["string"]
}}
"""


# Optimized User Prompt Template
def create_user_prompt_template():
    return """Create a detailed job description based on the following prompt:

Prompt: {user_input}

- **Job Title**: Clear and concise title.
- **Key Responsibilities**: At least 4-5 points, starting with action verbs.
- **Skills Required**: Use a colon-separated format like "Category: skill1, skill2, skill3". Ensure you categorize the skills.
- **Qualifications**: Include educational requirements, experience, and soft skills.
- **Keywords**: Extract relevant technical and soft skills (e.g., "Python", "Django", "Communication").

Return the job description as a structured JSON object with the following fields:
- job_title, tags, years_of_experience, about_the_role, job_type_workplace_location, 
  key_responsibilities, skills_required, qualifications, what_we_offer, keywords
"""


# Define the chain that connects the prompt to the LLM
prompt_template = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(get_system_prompt()),
    HumanMessagePromptTemplate.from_template(create_user_prompt_template())
])

# Define the output parser
json_parser = JsonOutputParser(pydantic_object=JobDescriptionSection)

# Define the chain with the LLM model
jd_generation_chain = prompt_template | llm | json_parser

# Function to generate the job description
async def manual_generate_jd(input_data: ParagraphInput) -> JDResponse:
    with ls.tracing_context(project="jd_generate"):
        try:
            result = await jd_generation_chain.ainvoke({
                "user_input": input_data.prompt
            })
            
            jd_response = JDResponse(full_description=result)
            
            print(f"JD Generated Successfully with LangChain:")
            print(f"   - Model: {LLM_CFG.active_model}")
            print(f"   - Automatically traced in LangSmith!")
            
            return jd_response
            
        except ValidationError as e:
            print(f"Validation Error: {str(e)}")
            raise ValueError(f"Input validation error: {str(e)}")
        except Exception as e:
            print(f"Generation Error: {str(e)}")
            raise ValueError(f"Failed to generate job description: {str(e)}")
