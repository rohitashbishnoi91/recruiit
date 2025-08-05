import os
import langsmith as ls
from pydantic import BaseModel, Field, ValidationError
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import JsonOutputParser
 
from utils.llm_config_loader import LoadLLMConfig

load_dotenv()

LLM_CFG = LoadLLMConfig()

llm = ChatGoogleGenerativeAI(
    model=LLM_CFG.active_model,
    google_api_key=os.getenv("GEMINI_API_KEY"),
    temperature=LLM_CFG.active_temperature,
    max_output_tokens=LLM_CFG.active_max_tokens,
    # convert_system_message_to_human=True   
)

class ParagraphInput(BaseModel):
    prompt: str = Field(..., description="User-provided job description prompt in a single paragraph")

class JobDescriptionSection(BaseModel):
    job_title: str
    tags: list[str]
    years_of_experience: str
    about_the_role: str
    job_type_workplace_location: str
    key_responsibilities: list[str]    # Detailed responsibilities (what they'll do)
    skills_required: list[str]         # Technical skills + experience levels
    qualifications: list[str]          # Education, soft skills, broader requirements
    what_we_offer: list[str] 
    keywords: list[str]  

class JDResponse(BaseModel):
    full_description: JobDescriptionSection = Field(..., description="The full generated job description as a structured object")

def get_system_prompt():
    return """You are an expert HR professional specializing in creating comprehensive and detailed industry-standard job descriptions.
Your task is to generate a structured, comprehensive job description based on the provided keywords.
Follow these guidelines:

1. Use clear, professional language appropriate for the specified industry
2. Structure the JD with the following sections:
   - Job Title: Clear, specific title
   - About the Role: A detailed paragraph introducing the role and its importance to the company
   - Job Type, Workplace Type, Location: A single string stating job type, workplace type, and location (e.g., "Full time, On site, Gurugram")
   - Key Responsibilities: A DETAILED list of strings (at least 4-5 items), starting with a strong action verb (e.g., "Design", "Implement", "Collaborate")
   - Skills Required: list of 5-7 technical skills requirements (under 10 words each) 
   - Qualifications: list of 4-6 education, experience, and soft skill requirements
   - What We Offer: list of 4-6 compelling benefits and opportunities

3. For Keyword Tags (Extracted Keywords - automatically extract from JD content):
   - Extract the job title as the first keyword
   - Extract all technical skills mentioned in Skills Required section
   - Extract experience requirements (e.g., "5+ years experience")
   - Extract work preferences (e.g., "remote work", "startup environment") 
   - Extract key technologies, frameworks, and tools mentioned
   - Extract education requirements if specific
   - These should be SHORT, TAG-LIKE keywords extracted directly from the generated content
   - Tags: EXACTLY 5-6 short tags only (experience level, primary tech, domain)
   - Generate 10-15 extracted keywords that would be useful for search and filtering


4. For Key Responsibilities:
   - Include specific technical responsibilities relevant to the role
   - Include collaboration aspects with other teams
   - Include quality assurance responsibilities
   - Include optimization and performance improvement duties
   - Be very specific and comprehensive, providing 1 line per responsibility

5. For Skills Required (IMPORTANT - follow this exact format):
   - Use colon-separated format: "Category: skill1, skill2, skill3"
   - Examples:
     * "Frontend Technologies: React, Redux, Context API, React Router"
     * "Programming Languages: TypeScript, JavaScript, Python"
     * "Testing Frameworks: Jest, React Testing Library, Cypress"
     * "Version Control: Git, GitHub, GitLab"
   - Each line should have a clear category followed by colon and space, then comma-separated skills
   - Generate 5-7 categorized skill requirements

6. For Qualifications (separate from technical skills):
   - Educational requirements only
   - Experience levels (e.g., "5+ years experience")
   - Soft skills and abilities
   - Communication and collaboration skills


7. For What We Offer:
   - Competitive compensation and benefits
   - Professional development opportunities
   - Work environment and culture benefits
   - Career growth prospects
   - Specific perks relevant to the industry/role

8. For Keywords generation:
   - Include technical skills and programming languages mentioned in the role
   - Add relevant tools, frameworks, and platforms commonly used
   - Include soft skills essential for the position
   - Add industry-specific terminology and methodologies
   - Include experience-level indicators (e.g., "Senior", "Mid-level", "Junior")
   - Add related job titles and role variations
   - Include domain-specific terms and certifications
   - Consider both explicit and implicit skills needed for the role

9. Aim for a comprehensive, professional JD similar to what a major tech company would produce
10. IMPORTANT: If location is not explicitly mentioned by the user, you MUST leave it completely blank by writing only "Full-time, On-site" without specifying any city. DO NOT default to San Francisco, New York, or any other location.

Return your response as a JSON object with the following structure:
{{
    "job_title": "string",
    "tags": ["string"],
    "years_of_experience": "string",  # e.g., "5+"
    "about_the_role": "string",
    "job_type_workplace_location": "string",
    "key_responsibilities": ["string"],
    "skills_required": ["string"]
    "qualifications": ["string"]
    "what_we_offer": ["string"]
    "keywords": ["string"]
}}"""

def create_user_prompt_template():
    return """Create a detailed job description based on the following prompt:

Prompt: {user_input}

Make this extremely comprehensive and detailed. 

The key_responsibilities should contain at least 4-5 detailed items, each with specific duties, starting with action verbs. 

IMPORTANT for skills_required: Format each skill requirement using the colon-separated format:
- "Category: skill1, skill2, skill3"
- Examples: "Frontend Frameworks: React, Vue.js, Angular", "Backend Technologies: Node.js, Python, Java"
- Generate 5-7 categorized skill requirements in this exact format

For the qualifications section, include 6-7 detailed items describing educational requirements, experience levels, and soft skills.


The requirements should contain at least 6-7 detailed items describing technical proficiencies and experience levels.
For the keywords field, generate EXACTLY 20 highly relevant keywords that include:
- Technical skills and programming languages
- Tools, frameworks, and platforms
- Soft skills and competencies
- Industry terminology and methodologies
- Experience level indicators
- Related job titles and variations
- Domain-specific terms and certifications
- Both explicit and implicit skills needed

The keywords should be tailored to the specific role and experience level mentioned in the prompt.

- If no location is specified in the prompt, set job_type_workplace_location to only include the job type and workplace type (e.g., "Full-time, On-site") WITHOUT any city or location.

The output should resemble a professional JD from a major company, with specific technical details rather than generic statements.
"""

prompt_template = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(get_system_prompt()),
    HumanMessagePromptTemplate.from_template(create_user_prompt_template())
])

json_parser = JsonOutputParser(pydantic_object=JobDescriptionSection)

jd_generation_chain = prompt_template | llm | json_parser

async def generate_jd(input_data: ParagraphInput) -> JDResponse:
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
