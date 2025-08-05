import os
from typing import List
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import langsmith as ls

class KeywordSuggestionRequest(BaseModel):
    user_input: str = Field(..., description="User's initial keywords input")

class JDSectionSuggestions(BaseModel):
    skills_required: List[str] = Field(description="Suggested skills based on experience levels", default_factory=list)

class KeywordSuggestionResponse(BaseModel):
    suggestions: JDSectionSuggestions
    total_suggestions: int

class KeywordSuggestionService:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=os.getenv("GEMINI_API_KEY"),
            temperature=0.1,
            max_output_tokens=600
        )
        self.suggestion_chain = self._create_suggestion_chain()

    def _create_suggestion_chain(self):
        system_prompt = """You are a recruitment expert helping users create job descriptions. Analyze the input and suggest 5-7 keywords across the skills_required section:

        1. skills_required: Most relevant Technical skills (short, tag-like, e.g., "Python", "AWS"). Do NOT include generic fields like 'Machine Learning' or 'Deep Learning' as standalone skills.

        Rules:
        - Only suggest keywords NOT in the user's input
        - Prioritize the most important suggestions first
        - Skills should be concise, role-specific keywords, not sentences
        - Be specific to the apparent role type"""

        user_prompt = """Current Input: "{user_input}"

        Suggest missing keywords for the skills_required section in JD generation:
        - Required Skills (4-5, short, tag-like, e.g., "Python", "AWS"). Only include specific programming languages, frameworks, libraries, or platforms

        Format response as JSON with lists for only skills_required section."""

        prompt_template = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", user_prompt)
        ])

        json_parser = JsonOutputParser(pydantic_object=JDSectionSuggestions)
        return prompt_template | self.llm | json_parser

    async def get_suggestions(self, request: KeywordSuggestionRequest) -> KeywordSuggestionResponse:
        with ls.tracing_context(project="keyword_suggestions"):
            try:
                # Get raw suggestions as dict
                suggestions_dict = await self.suggestion_chain.ainvoke({
                    "user_input": request.user_input
                })

                # Convert to Pydantic model
                suggestions = JDSectionSuggestions(**suggestions_dict)

                return KeywordSuggestionResponse(
                    suggestions=suggestions,
                    total_suggestions=sum(len(getattr(suggestions, field)) for field in suggestions.__fields__)
                )

            except Exception as e:
                raise ValueError(f"Keyword suggestion failed: {str(e)}")

keyword_service = KeywordSuggestionService()
