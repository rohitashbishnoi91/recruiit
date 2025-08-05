import re

def extract_skills_from_requirements(skills_required):
    all_skills = []
    
    pattern = r'(?<=:\s)(.*)'
    
    for requirement in skills_required:
        match = re.search(pattern, requirement)
        if match:
            skills_text = match.group(1).strip()
            
            skills = [skill.strip() for skill in skills_text.split(',')]
            all_skills.extend(skills)
    
    return all_skills

# Example usage with your JD format
skills_required = [
    "Programming Languages: Python, SQL",
    "Web Frameworks: Flask, FastAPI, Django (Optional)",
    "Databases: PostgreSQL, MySQL, MongoDB (Optional)",
    "API Development: RESTful APIs, API Design, Swagger/OpenAPI",
    "Version Control: Git, GitHub, GitLab",
    "Data Structures & Algorithms: DSA fundamentals, algorithm design, complexity analysis",
    "Testing: Unit Testing, Integration Testing, Test-Driven Development (TDD)"
]

extracted_skills = extract_skills_from_requirements(skills_required)
print(extracted_skills)
