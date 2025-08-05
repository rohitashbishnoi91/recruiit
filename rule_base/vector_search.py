import os
import pymongo
from bson import ObjectId
import asyncio
from scipy.stats import percentileofscore
from pydantic import BaseModel, Field
from typing import Dict, Any, List

# Import all scoring components
from rule_base.core.skills import final_skills_score
from core.experience import final_experience_score
from core.job_title import final_title_score
from core.education import final_education_score
from core.premier_education import final_premier_education_score
from core.location import final_location_score
from core.seniority import final_seniority_score
from core.soft_skills import final_soft_skills_score

from rerank_algo import apply_reranking_to_categories
from contact_out.search import parse_user_query, normalize_filters, process_candidates

class CandidateSearchRequest(BaseModel):
    jd_id: str = Field(..., description="MongoDB ObjectId of the job description")
    query: str = Field(..., description="User query keywords")
    debug: bool = Field(default=False, description="Enable debug logging")

######################## LOADING JD DATA ########################

def load_jd_data(jd_id, collection):

    jd_doc = collection.find_one({"_id": ObjectId(jd_id)})
    
    if not jd_doc:
        print(f"JD document with ID {jd_id} not found")
        return None, None
    
    # Extract jdVector
    jd_vector = jd_doc.get("jdVector")
    if not jd_vector:
        print("jdVector not found in document")
        return None, None
    
    qualifications = [
        "Bachelor's degree in Computer Science, Software Engineering, or a related field.",
        "Minimum of 2+ years of professional experience.",
        "Strong problem-solving and analytical skills.",
        "Excellent communication and teamwork abilities."
    ]

    jd_data = {
        "job_title": jd_doc.get('title', ''),
        "tags": jd_doc.get('keywords', [])[:6],  # First 6 keywords as tags
        "years_of_experience": jd_doc.get('years_of_experience', ''),
        "about_the_role": jd_doc.get('description', ''),
        "job_type_workplace_location": jd_doc.get('location', ''),
        "key_responsibilities": jd_doc.get('keyResponsibilities', []),
        "skills_required": jd_doc.get('skillsRequired', []),
        
        # "qualifications": jd_doc.get('qualifications', []),
        "qualifications": qualifications,

        "what_we_offer": jd_doc.get('whatWeOffer', []),
        "keywords": jd_doc.get('keywords', [])
    }
    
    return jd_vector, jd_data




######################## VECTOR SEARCH ########################

def vector_search(jd_vector, client):

    # define pipeline
    pipeline = [
    {
        '$vectorSearch': {
        "exact": False,
        'index': 'vector_index_user', 
        'path': 'embedding', 
        'queryVector': jd_vector, 
        'numCandidates': 3000, 
        'limit': 150
        }
    }, {
        '$project': {
        '_id': 1,
        'Name': 1,
        'Title': 1,

        # Core Characteristics Data (70% weight)
        'Headline': 1,
        'Location': 1,
        'Skills': 1,               
        'Certifications': 1,
        'Education': 1,
        'Experience': 1,
        'Experience in days': 1,
        'Profile url': 1,        
        'score': {
            '$meta': 'vectorSearchScore'
        }
        }
    }
    ]

    # run pipeline
    # result = client["candidates"]["users"].aggregate(pipeline)
    result = list(client["candidates"]["users"].aggregate(pipeline))

    return result
 

######################## ASYNC CORE COMPONENTS  ########################

async def calculate_skills_score_async(candidates_core, jd_data):
    
    jd_skills_req = jd_data.get('skills_required', [])
    return final_skills_score(candidates_core, jd_skills_req, debug=False)


async def calculate_experience_score_async(candidates_core, jd_data):
    return final_experience_score(candidates_core, jd_data, debug=False)

async def calculate_title_score_async(candidates_core, jd_data):
    return final_title_score(candidates_core, jd_data, debug=False)

async def calculate_education_score_async(candidates_core, jd_data):
    return final_education_score(candidates_core, jd_data, debug=False)

async def calculate_premier_education_score_async(candidates_core, jd_data):
    return final_premier_education_score(candidates_core, debug=False)

async def calculate_location_score_async(candidates_core, jd_data):
    return final_location_score(candidates_core, jd_data, debug=False)

async def calculate_seniority_score_async(candidates_core, jd_data):
    return final_seniority_score(candidates_core, jd_data, debug=False)

async def calculate_soft_skills_score_async(candidates_core, jd_data):
    return final_soft_skills_score(candidates_core, jd_data, debug=False)


######################## CORE SCORE ########################

async def calculate_core_scores(candidates_core, jd_data):
    print("Calculating core scores...")


    # Create copies for parallel processing
    candidates_copies = [[dict(candidate) for candidate in candidates_core] for _ in range(8)]

    results = await asyncio.gather(
        calculate_skills_score_async(candidates_copies[0], jd_data),
        calculate_experience_score_async(candidates_copies[1], jd_data),
        calculate_title_score_async(candidates_copies[2], jd_data),
        calculate_education_score_async(candidates_copies[3], jd_data),
        calculate_premier_education_score_async(candidates_copies[4], jd_data),
        calculate_location_score_async(candidates_copies[5], jd_data),
        calculate_seniority_score_async(candidates_copies[6], jd_data),
        calculate_soft_skills_score_async(candidates_copies[7], jd_data)
    )
    


    # Merge scores back to original candidates
    for i, candidate in enumerate(candidates_core):
        candidate['skill_weighted_score'] = results[0][i].get('skill_weighted_score', 0)
        candidate['experience_weighted_score'] = results[1][i].get('experience_weighted_score', 0)
        candidate['title_weighted_score'] = results[2][i].get('title_weighted_score', 0)
        candidate['education_weighted_score'] = results[3][i].get('education_weighted_score', 0)
        candidate['premier_education_weighted_score'] = results[4][i].get('premier_education_weighted_score', 0)
        candidate['location_weighted_score'] = results[5][i].get('location_weighted_score', 0)
        candidate['seniority_weighted_score'] = results[6][i].get('seniority_weighted_score', 0)
        candidate['soft_skills_weighted_score'] = results[7][i].get('soft_skills_weighted_score', 0)


        
        # Calculate total core score
        candidate['total_core_score'] = (
            candidate['skill_weighted_score'] +                    # 35 points
            candidate['experience_weighted_score'] +               # 25 points
            candidate['title_weighted_score'] +                    # 10 points
            candidate['education_weighted_score'] +                # 10 points
            candidate['premier_education_weighted_score'] +        # 5 points
            candidate['location_weighted_score'] +                 # 5 points
            candidate['seniority_weighted_score'] +                # 5 points
            candidate['soft_skills_weighted_score']                # 5 points
        )
    
    print("Core scoring completed!")
    return candidates_core




######################## BONUS SCORE ########################

async def calculate_bonus_scores(candidates_core, jd_data):
    print("Calculating bonus scores...")

    # For now, just add default bonus scores to all candidates
    for candidate in candidates_core:
        candidate['bonus_score'] = 0  # Default 0 bonus points for now
    
    print("Bonus scoring completed!")
    return candidates_core  





######################## FINAL SCORE ########################

def apply_final_percentile_score(candidates):
    """Apply percentile ranking to final scores for relative comparison"""
    final_scores = [c.get('final_score', 0) for c in candidates]
    
    # Debug: Print the scores array
    # print(f"Debug - Final Scores Array: {sorted(final_scores, reverse=True)}")
    # print(f"Debug - Min Score: {min(final_scores)}, Max Score: {max(final_scores)}")
    
    for candidate in candidates:
        score = candidate.get('final_score', 0)
        percentile = percentileofscore(final_scores, score, kind='weak')
        candidate['final_percentile_score'] = percentile
        
        # Debug: Print each calculation
        # print(f"Debug - {candidate.get('Name', 'Unknown')}: Score {score:.2f} → Percentile {percentile:.1f}%")
    
    return candidates




async def calculate_final_scores(cosine_cand, jd_data):
    print("Calculating final scores...")
    
    # Create copies for parallel processing
    candidates_core = [dict(candidate) for candidate in cosine_cand]
    candidates_bonus = [dict(candidate) for candidate in cosine_cand]

    weighted_core_score = calculate_core_scores(candidates_core, jd_data)
    weighted_bonus_score = calculate_bonus_scores(candidates_bonus, jd_data)

    core_results, bonus_results = await asyncio.gather(weighted_core_score, weighted_bonus_score)

    # Calculate final score for each candidate
    for i, candidate in enumerate(cosine_cand):
        # Get core and bonus scores from results
        core_score = core_results[i].get('total_core_score', 0)
        bonus_score = bonus_results[i].get('bonus_score', 0)
        
        # Calculate weighted final score
        weighted_core = (core_score / 100) * 70
        weighted_bonus = (bonus_score / 50) * 30
        final_score = weighted_core + weighted_bonus
        
        # Add scores to original candidate
        candidate['total_core_score'] = core_score
        candidate['bonus_score'] = bonus_score
        candidate['final_score'] = final_score
        candidate['vector_score'] = candidate.get('score', 0)

    print("Final scoring completed!")
    return cosine_cand


######################## HELPER FUNCTION - Core Skills ########################


def build_relevant_core_skills(candidate, jd_keywords=None, matched_keywords=None):
    """
    Build core skills list prioritizing relevance to JD
    Returns up to 6 skills ordered by relevance - only JD-based matching
    """
    all_candidate_skills = candidate.get('Skills', [])
    
    if not all_candidate_skills:
        return []
    
    if not jd_keywords:
        # If no JD keywords, return first 6 skills as fallback
        return all_candidate_skills[:6]
    
    # Convert to sets for easier comparison
    candidate_skills_lower = {skill.lower().strip(): skill for skill in all_candidate_skills}
    jd_keywords_lower = [kw.lower().strip() for kw in jd_keywords] if jd_keywords else []
    
    relevant_skills = []
    used_skills_lower = set()
    
    # Priority 1: Exact matches (already in matched_keywords)
    if matched_keywords:
        for matched_skill in matched_keywords:
            matched_lower = matched_skill.lower().strip()
            # Find original candidate skill that matches
            for candidate_skill_lower, original_skill in candidate_skills_lower.items():
                if candidate_skill_lower == matched_lower and matched_lower not in used_skills_lower:
                    relevant_skills.append(original_skill)
                    used_skills_lower.add(matched_lower)
                    break
    
    # Priority 2: Partial matches with JD keywords
    if len(relevant_skills) < 6:
        for jd_keyword in jd_keywords_lower:
            if len(relevant_skills) >= 6:
                break
                
            for candidate_skill_lower, original_skill in candidate_skills_lower.items():
                if candidate_skill_lower not in used_skills_lower:
                    # Check if JD keyword is contained in candidate skill or vice versa
                    if (jd_keyword in candidate_skill_lower or 
                        candidate_skill_lower in jd_keyword or
                        any(word in candidate_skill_lower for word in jd_keyword.split() if len(word) > 3)):
                        
                        relevant_skills.append(original_skill)
                        used_skills_lower.add(candidate_skill_lower)
                        break
    
    # Priority 3: Remaining candidate skills (if still need more)
    if len(relevant_skills) < 6:
        for original_skill in all_candidate_skills:
            if len(relevant_skills) >= 6:
                break
                
            skill_lower = original_skill.lower().strip()
            if skill_lower not in used_skills_lower:
                relevant_skills.append(original_skill)
                used_skills_lower.add(skill_lower)
    
    return relevant_skills[:6]



######################## TRANSFORM CANDIDATES ########################

def transform_candidate_for_response(candidate, jd_keywords=None):
    
    # Calculate years of experience
    experience_years = round(candidate.get('Experience in days', 0) / 365, 1) if candidate.get('Experience in days') else 0
    
    # Get highest education degree
    education_degrees = candidate.get('Education', [])
    highest_degree = ""
    if education_degrees:
        highest_degree = education_degrees[0].get('degree', '') or education_degrees[0].get('fieldOfStudy', '')
        if not highest_degree and len(education_degrees) > 0:
            highest_degree = "Degree"
    
    # Extract matched keywords (intersection between JD keywords and candidate skills)
    matched_keywords = []
    if jd_keywords:
        candidate_skills = set([skill.lower().strip() for skill in candidate.get('Skills', [])])
        jd_keywords_lower = set([kw.lower().strip() for kw in jd_keywords])
        
        # Find exact matches
        matches = candidate_skills.intersection(jd_keywords_lower)
        
        # Convert back to original case from JD keywords for display
        matched_keywords = []
        for match in matches:
            # Find the original keyword from JD that matches
            for original_kw in jd_keywords:
                if original_kw.lower().strip() == match:
                    matched_keywords.append(original_kw)
                    break
        
        # Limit to 4-5 for UI display
        matched_keywords = matched_keywords[:5]
    
    # Core skills (limit to top 7 for UI)
    # core_skills = candidate.get('Skills', [])[:7]
    core_skills = build_relevant_core_skills(candidate, jd_keywords, matched_keywords)
    
    # Create description from headline
    description = candidate.get('Headline', '')
    if not description and candidate.get('Summary'):
        description = candidate.get('Summary', '')
    
    base_response = {
        # Basic Info
        "id": str(candidate.get('_id', '')),
        "name": candidate.get('Name', 'N/A'),
        "title": candidate.get('Title', ''),
        "location": candidate.get('Location', ''),
        "profile_url": candidate.get('Profile url', ''),
        
        # Experience & Education
        "experience_years": experience_years,
        "highest_degree": highest_degree,
        
        # Scoring & Matching (only percentile)
        "percentile_score": round(candidate.get('final_percentile_score', 0), 2),
        "tfidf_rerank_score": round(candidate.get('tfidf_rerank_score', 0), 4),
        
        # Skills & Keywords - matched keywords are the ones that appear in both JD and candidate
        "matched_keywords": matched_keywords,  # These are for highlighting
        "core_skills": core_skills,
        
        # Description
        "description": description,
        "headline": candidate.get('Headline', '')
    }

    return base_response


######################## API CALLING FUNCTION ########################


async def search_candidates_by_jd(jd_id, user_query, client, debug=False):

    # Response structure
    response = {
        "status": "success",
        "data": {
            "relevant_candidates": [],
            "similar_candidates": [],
            "search_metadata": {},
        },
        "errors": []
    }

    try:
        
        # 1. Get MongoDB client
        if debug:
            print("Starting internal candidate search...")

        db = client['Recruiit']
        collection = db['jobdescriptions']

        # Load JD data
        print("Loading JD data...")
        jd_vector, jd_data = load_jd_data(jd_id, collection)

        # print("JD Data:", jd_data)
        if not jd_vector or not jd_data:
            print("Could not load JD data")
            response["status"] = "error"
            response["errors"].append("Could not load JD data")
            return response

        # 2. Perform internal vector search
        try:
            if debug:
                print("Performing vector search...")
            
            cosine_cand = vector_search(jd_vector, client)
            
            if not cosine_cand:
                response["status"] = "success"
                response["data"]["search_metadata"] = {
                    "total_candidates_found": 0,
                    "message": "No candidates found matching the JD"
                }
                return response
                
        except Exception as e:
            response["status"] = "error"
            response["errors"].append(f"Vector search failed: {str(e)}")
            return response


        # 5. Calculate final scores
        try:
            if debug:
                print("Calculating Internal Cand final scores...")

            internal_candidates = await calculate_final_scores(cosine_cand, jd_data)
            internal_candidates = apply_final_percentile_score(internal_candidates)

        except Exception as e:
            response["status"] = "error"
            response["errors"].append(f"Scoring calculation failed: {str(e)}")
            return response

        # 6. Sort candidates by final score
        try:
            internal_candidates.sort(key=lambda x: x.get('final_score', 0), reverse=True)
        
        except Exception as e:
            if debug:
                print(f"Warning: Sorting failed: {e}")

        # 7. Transform all candidates to simplified format
        try:
            # Get JD keywords directly from JD data
            jd_keywords = jd_data.get('keywords', [])
            
            if debug:
                print(f"JD Keywords for matching: {jd_keywords[:10]}...")  # Show first 10
            
            # Transform all candidates once
            transformed_internal_cand = [
                transform_candidate_for_response(candidate, jd_keywords) 
                for candidate in internal_candidates
            ]
            
        except Exception as e:
            if debug:
                print(f"Warning: Candidate transformation failed: {e}")
            # Fallback to original format
            transformed_internal_cand = internal_candidates



        # 8. Categorize results based on LLD requirements
        internal_rel_cand = []
        internal_sim_cand = []

        
        
        for candidate in transformed_internal_cand:
            candidate['source'] = 'internal' 
            percentile_score = candidate.get('percentile_score', 0)
            if percentile_score >= 95:  # Top 5% - Relevant candidates
                internal_rel_cand.append(candidate)
            elif percentile_score >= 65:  # Top 35% - Similar candidates  
                internal_sim_cand.append(candidate)

        if debug:
            print(f"Internal results: {len(internal_rel_cand)} relevant, {len(internal_sim_cand)} similar")

        # 8.1 CHECK: Do we need ContactOut fallback?
        external_rel_cand = []
        external_sim_cand = []

        if len(internal_rel_cand) < 10:
            if debug:
                print(f"Insufficient relevant candidates ({len(internal_rel_cand)}), activating ContactOut fallback...")

            try:
                # 4.1 Fetch and store external candidates
                raw_filters = parse_user_query(user_query)
                filters = normalize_filters(raw_filters)
                process_candidates(filters=filters, limit=5, jd_id=jd_id, query=user_query)

                if debug:
                    print("External candidates fetched and stored successfully.")

                # 4.2 Retrieve stored external candidates for this JD
                external_db = client['external_candidates_testing']
                external_collection = external_db['candidates']
                
                external_candidates = list(external_collection.find({
                    "search_context.jd_ids": jd_id,
                    "embedding": {"$exists": True, "$ne": None}
                }))

                if debug:
                    print(f"Retrieved {len(external_candidates)} external candidates for processing")

                # 4.3 Process external candidates through same pipeline
                if external_candidates:
                    # Calculate scores for external candidates
                    external_scored = await calculate_final_scores(external_candidates, jd_data)
                    external_scored = apply_final_percentile_score(external_scored)
                    external_scored.sort(key=lambda x: x.get('final_score', 0), reverse=True)

                    # Transform external candidates
                    transformed_external = [
                        transform_candidate_for_response(candidate, jd_keywords) 
                        for candidate in external_scored
                    ]
                    
                    # Categorize external results and add source tag
                    for candidate in transformed_external:
                        candidate['source'] = 'external'  # Tag as external
                        percentile_score = candidate.get('percentile_score', 0)
                        if percentile_score >= 95:
                            external_rel_cand.append(candidate)
                        elif percentile_score >= 65:
                            external_sim_cand.append(candidate)

                    if debug:
                        print(f"External results: {len(external_rel_cand)} relevant, {len(external_sim_cand)} similar")

            except Exception as e:
                if debug:
                    print(f"ContactOut fallback failed: {e}")
                response["errors"].append(f"ContactOut fallback failed: {str(e)}")

        # 5. Merge internal and external results
        relevant_candidates = internal_rel_cand + external_rel_cand
        similar_candidates = internal_sim_cand + external_sim_cand

        # Sort merged results by percentile score
        relevant_candidates.sort(key=lambda x: x.get('percentile_score', 0), reverse=True)
        similar_candidates.sort(key=lambda x: x.get('percentile_score', 0), reverse=True)

        if debug:
            print(f"Merged results: {len(relevant_candidates)} relevant, {len(similar_candidates)} similar")
            print(f"  Internal: {len(internal_rel_cand)} rel + {len(internal_sim_cand)} sim")
            print(f"  External: {len(external_rel_cand)} rel + {len(external_sim_cand)} sim")


        # 9. NEW: Apply TF-IDF re-ranking within each category
        try:
            if debug:
                print("Applying TF-IDF re-ranking...")
            
            relevant_candidates, similar_candidates = apply_reranking_to_categories(
                relevant_candidates, similar_candidates, jd_data
            )
            
            if debug:
                print(f"Re-ranking completed. Relevant: {len(relevant_candidates)}, Similar: {len(similar_candidates)}")
                
        except Exception as e:
            if debug:
                print(f"Warning: TF-IDF re-ranking failed: {e}")
        
        
        # 10. Build final response
        response["data"] = {
            "relevant_candidates": relevant_candidates,
            "similar_candidates": similar_candidates,
            "search_metadata": {
                "total_candidates_found": len(transformed_internal_cand),  # More accurate than len(candidates)
                "relevant_count": len(relevant_candidates),
                "similar_count": len(similar_candidates),
                "jd_id": jd_id,
                "search_sources": ["internal", "external"] if external_rel_cand + external_sim_cand else ["internal"]
            },
        }

        if debug:
            print(f"Search completed. Total: {len(internal_candidates)}, Relevant: {len(relevant_candidates)}, Similar: {len(similar_candidates)}")

        return response

    except Exception as e:
        response["status"] = "error"
        response["errors"].append(f"Unexpected error: {str(e)}")
        if debug:
            import traceback
            traceback.print_exc()
        return response



######################## MAIN FUNCTION - TESTING ########################

async def main():
    
    jd_id = "6859529091ffb44cbf3acd10"
    
    try:
        # Call the main search function
        result = await search_candidates_by_jd(jd_id, debug=False)
        print(f"Search Result : {result}")


        # # Handle the response
        # if result["status"] == "success":
        #     relevant_candidates = result["data"]["relevant_candidates"]
        #     similar_candidates = result["data"]["similar_candidates"]
        #     metadata = result["data"]["search_metadata"]
            
        #     print(f"\n=== SEARCH RESULTS ===")
        #     print(f"Total candidates found: {metadata['total_candidates_found']}")
        #     print(f"Relevant candidates (>=80): {metadata['relevant_count']}")
        #     print(f"Similar candidates (>=50): {metadata['similar_count']}")


        #     # Display all relevant candidates
        #     if relevant_candidates:
        #         print(f"\n=== ALL RELEVANT CANDIDATES ===")
        #         for i, candidate in enumerate(relevant_candidates, 1):  # All relevant
        #             print(f"{i}. {candidate.get('Name', 'N/A')} - Percentile: {candidate.get('final_percentile_score', 0):.2f}")

        #     # Display all similar candidates
        #     if similar_candidates:
        #         print(f"\n=== ALL SIMILAR CANDIDATES ===")
        #         for i, candidate in enumerate(similar_candidates, 1):  # All similar
        #             print(f"{i}. {candidate.get('Name', 'N/A')} - Percentile: {candidate.get('final_percentile_score', 0):.2f}")

        # else:
        #     print("Search failed!")
        #     print("Errors:", result["errors"])
        

    except Exception as e:
        print(f"Error in scoring process: {e}")
        import traceback
        traceback.print_exc()


   


# if __name__ == "__main__":
#     asyncio.run(main())

