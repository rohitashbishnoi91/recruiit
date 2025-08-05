import re
import time
from typing import List, Dict, Any
from collections import Counter
import math

class TFIDFReranker:
    
    def __init__(self):
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
            'could', 'can', 'may', 'might', 'must', 'shall', 'this', 'that', 'these',
            'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her',
            'us', 'them', 'my', 'your', 'his', 'their', 'our', 'its'
        }
    
    def fast_tokenize(self, text: str) -> List[str]:
        """Ultra-fast tokenization without regex"""
        if not text:
            return []
        
        # Convert to lowercase and split
        tokens = text.lower().split()
        
        # Remove punctuation and filter stop words
        clean_tokens = []
        for token in tokens:
            # Remove punctuation from start and end
            clean_token = token.strip('.,!?;:"()[]{}')
            if clean_token and clean_token not in self.stop_words and len(clean_token) > 2:
                clean_tokens.append(clean_token)
        
        return clean_tokens
    
    def extract_jd_terms(self, jd_data: Dict[str, Any]) -> List[str]:
        """Extract and tokenize key JD terms for matching"""
        # Priority order - most important fields first
        key_fields = [
            ('skills_required', 3),  # 3x weight
            ('job_title', 2),        # 2x weight  
            ('key_responsibilities', 2),  # 2x weight
            ('keywords', 2),         # 2x weight
            ('qualifications', 1),   # 1x weight
            ('tags', 1)              # 1x weight
        ]
        
        weighted_terms = []
        
        for field, weight in key_fields:
            content = jd_data.get(field, '')
            
            if isinstance(content, list):
                content = ' '.join(content)
            
            if content:
                terms = self.fast_tokenize(content)
                # Add terms multiple times based on weight
                weighted_terms.extend(terms * weight)
        
        return weighted_terms
    
    def extract_candidate_terms(self, candidate: Dict[str, Any]) -> List[str]:
        """Extract candidate terms for matching - Updated for your transformed candidate structure"""
        candidate_text_parts = []
        
        # Updated field names to match your transformed candidate data
        fields_config = [
            ('title', 1),           # Current job title
            ('headline', 1),        # Professional headline
            ('description', 1),     # Profile description  
            ('core_skills', 2),     # Core skills (higher weight)
            ('matched_keywords', 3) # Matched keywords (highest weight)
        ]
        
        for field, weight in fields_config:
            value = candidate.get(field, '')
            
            if isinstance(value, list):
                # For lists like core_skills, matched_keywords
                text_content = ' '.join(value)
            elif isinstance(value, str):
                text_content = value
            else:
                continue
                
            if text_content:
                # Add weighted content
                for _ in range(weight):
                    candidate_text_parts.append(text_content)
        
        # Join and tokenize
        full_text = ' '.join(candidate_text_parts)
        return self.fast_tokenize(full_text)
    
    def calculate_experience_multiplier(self, candidate_years: float, jd_years_required: str) -> float:
        """Calculate experience-based multiplier for final ranking"""
        try:
            # Parse JD years requirement
            if not jd_years_required:
                return 1.0
            
            # Extract number from requirements like "2+"
            import re
            numbers = re.findall(r'\d+', jd_years_required)
            if not numbers:
                return 1.0
            
            required_years = float(numbers[0])  # Take first number as minimum
            
            # Calculate multiplier based on experience match
            if candidate_years >= required_years:
                # Bonus for meeting/exceeding requirements
                if candidate_years <= required_years * 1.5:
                    return 1.2  # Sweet spot: exactly what's needed
                elif candidate_years <= required_years * 2:
                    return 1.1  # Good: more experience than needed
                else:
                    return 1.05  # Might be overqualified, but still good
            else:
                # Penalty for insufficient experience
                experience_ratio = candidate_years / required_years
                if experience_ratio >= 0.8:
                    return 0.95  # Close to requirement
                elif experience_ratio >= 0.6:
                    return 0.9   # Somewhat below requirement
                else:
                    return 0.8   # Significantly below requirement
                    
        except Exception:
            return 1.0  # Default to no adjustment if parsing fails
    
    def calculate_enhanced_tfidf_score(self, candidate_terms: List[str], 
                                     jd_terms: List[str],
                                     experience_multiplier: float) -> float:
        """Calculate TF-IDF score with experience weighting"""
        if not candidate_terms or not jd_terms:
            return 0.0
        
        # Count term frequencies
        candidate_tf = Counter(candidate_terms)
        jd_tf = Counter(jd_terms)
        
        # Calculate TF-IDF score
        score = 0.0
        total_jd_terms = len(jd_terms)
        
        for term, jd_count in jd_tf.items():
            if term in candidate_tf:
                # Simple TF-IDF approximation
                tf_score = candidate_tf[term] / len(candidate_terms)
                idf_score = jd_count / total_jd_terms
                score += tf_score * idf_score
        
        # Apply experience multiplier
        final_score = score * experience_multiplier
        
        return final_score
    
    def rerank_candidates(self, candidates: List[Dict[str, Any]], 
                         jd_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fast re-ranking function with experience weighting - updated for your data structure
        """
        if not candidates or not jd_data:
            return candidates
        
        start_time = time.time()
        
        # Extract JD terms once
        jd_terms = self.extract_jd_terms(jd_data)
        jd_years_required = jd_data.get('years_of_experience', '')
        
        # Calculate enhanced TF-IDF scores for all candidates
        for candidate in candidates:
            candidate_terms = self.extract_candidate_terms(candidate)
            
            # Get candidate experience years (from your transformed data)
            candidate_years = candidate.get('experience_years', 0)
            
            # Calculate experience multiplier
            exp_multiplier = self.calculate_experience_multiplier(
                candidate_years, jd_years_required
            )
            
            # Calculate final TF-IDF score with experience weighting
            tfidf_score = self.calculate_enhanced_tfidf_score(
                candidate_terms, jd_terms, exp_multiplier
            )
            
            candidate['tfidf_rerank_score'] = tfidf_score
            candidate['experience_multiplier'] = exp_multiplier
        
        # Sort by TF-IDF score (descending)
        candidates.sort(key=lambda x: x.get('tfidf_rerank_score', 0), reverse=True)
        
        end_time = time.time()
        execution_time = (end_time - start_time) * 1000000  # Convert to microseconds
        
        print(f"TF-IDF re-ranking completed in {execution_time:.0f} microseconds")
        return candidates


# Global instance for reuse
_reranker = TFIDFReranker()

def fast_tfidf_rerank(candidates: List[Dict[str, Any]], 
                     jd_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Main re-ranking function to integrate into your pipeline
    """
    return _reranker.rerank_candidates(candidates, jd_data)


def apply_reranking_to_categories(relevant_candidates: List[Dict[str, Any]], 
                                similar_candidates: List[Dict[str, Any]], 
                                jd_data: Dict[str, Any]) -> tuple:
   
    # Re-rank relevant candidates (≥95%)
    if relevant_candidates:
        relevant_candidates = fast_tfidf_rerank(relevant_candidates, jd_data)
    
    # Re-rank similar candidates (≥65%)  
    if similar_candidates:
        similar_candidates = fast_tfidf_rerank(similar_candidates, jd_data)
    
    return relevant_candidates, similar_candidates
