import os
import aiohttp
import logging
import json
import re
import random

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-4o-mini"

async def improve_transcript_band_openai(transcript: str) -> str:
    """
    Uses OpenAI GPT to improve a transcript by about 0.5 band score (IELTS style).
    """
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY not set in environment variables.")
        raise RuntimeError("OPENAI_API_KEY not set.")

    prompt = (
        "You are an expert IELTS examiner and English teacher. "
        "Given the following student transcript, improve it by about 0.5 band score. "
        "Focus on grammar, vocabulary, coherence, and naturalness, but keep the student's original meaning and ideas. "
        "Return only the improved version, not any explanation.\n\n"
        f"Student transcript: {transcript}\n\nImproved version:"
    )

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 512,
        "temperature": 0.7
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(OPENAI_API_URL, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    improved = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                    return improved
                else:
                    error_text = await response.text()
                    logger.error(f"OpenAI API error: {response.status}, {error_text}")
                    raise RuntimeError(f"OpenAI API error: {response.status}, {error_text}")
    except Exception as e:
        logger.error(f"OpenAI API error: {str(e)}")
        raise RuntimeError(f"OpenAI API error: {str(e)}")

async def get_blank_indices_openai(improved_transcript: str, improved_word_indices: list) -> list:
    """
    Use OpenAI to select about 25% of the words to blank out, excluding improved words and critical words.
    Ensures no adjacent words are blanked out and sentences remain comprehensible.
    Returns a list of indices (0-based) of words to blank.
    """
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY not set in environment variables.")
        logger.info("Using fallback method due to missing API key")
        return fallback_blank_indices(improved_transcript, improved_word_indices)

    # Split transcript into sentences for better distribution
    sentences = [s.strip() for s in improved_transcript.split('.') if s.strip()]
    total_sentences = len(sentences)
    
    prompt = (
        f"Given the following transcript, select about 25% of the words to blank out for a language challenge. "
        f"Important rules:\n"
        f"1. Do NOT blank out any of these improved words (by index): {improved_word_indices}\n"
        f"2. Do NOT blank out words that are adjacent to each other\n"
        f"3. Do NOT blank out critical words that would make the sentence incomprehensible\n"
        f"4. Prefer to blank out:\n"
        f"   - Adjectives\n"
        f"   - Adverbs\n"
        f"   - Non-essential descriptive words\n"
        f"5. Avoid blanking out:\n"
        f"   - Main verbs\n"
        f"   - Subject nouns\n"
        f"   - Key conjunctions\n"
        f"   - Question words\n"
        f"6. IMPORTANT: Distribute the blanks evenly throughout the entire text. "
        f"Do not cluster them at the beginning or end.\n"
        f"7. Try to have at least one blank in each sentence if possible.\n"
        f"Return ONLY a JSON array of the indices (0-based) of the words to blank. No explanation needed."
        f"\n\nTranscript: {improved_transcript}"
    )
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 256,
        "temperature": 0.2,
        "response_format": {"type": "json_object"}
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(OPENAI_API_URL, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    content = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                    logger.info(f"OpenAI API call successful. Response preview: {content[:100]}...")
                    
                    json_match = re.search(r'\[.*?\]', content, re.DOTALL)
                    if json_match:
                        try:
                            blank_indices = json.loads(json_match.group(0))
                            if isinstance(blank_indices, list):
                                # Validate that none of the improved words are blanked
                                blank_indices = [idx for idx in blank_indices if idx not in improved_word_indices]
                                # Ensure no adjacent words are blanked
                                blank_indices = remove_adjacent_indices(blank_indices)
                                # Ensure we don't exceed 25% of words
                                max_blanks = int(len(improved_transcript.split()) * 0.25)
                                if len(blank_indices) > max_blanks:
                                    # Sort by position to ensure even distribution
                                    blank_indices = sorted(blank_indices)
                                    # Take evenly spaced indices
                                    step = len(blank_indices) / max_blanks
                                    blank_indices = [blank_indices[int(i * step)] for i in range(max_blanks)]
                                if blank_indices:
                                    logger.info(f"Successfully using OpenAI response. Generated {len(blank_indices)} blanks")
                                    return blank_indices
                                else:
                                    logger.warning("OpenAI response resulted in no valid blank indices")
                        except json.JSONDecodeError as e:
                            logger.error(f"JSON parsing error from OpenAI response: {e}")
                    else:
                        logger.warning("No JSON array found in OpenAI response")
                else:
                    error_text = await response.text()
                    logger.error(f"OpenAI API error: {response.status}, {error_text}")
    except Exception as e:
        logger.error(f"Error in get_blank_indices_openai: {str(e)}")
    
    logger.warning("Falling back to algorithmic method due to OpenAI issues")
    return fallback_blank_indices(improved_transcript, improved_word_indices)

def remove_adjacent_indices(indices: list) -> list:
    """
    Remove indices that are adjacent to each other, keeping the first one in each pair.
    Also ensures we don't blank out too many words in a row.
    """
    if not indices:
        return []
    
    # Sort indices to ensure we process them in order
    sorted_indices = sorted(indices)
    result = [sorted_indices[0]]
    
    for i in range(1, len(sorted_indices)):
        # Only add if not adjacent to the last added index
        # and if we haven't already blanked 3 words in the last 5 positions
        if sorted_indices[i] - result[-1] > 1:
            # Check the last 5 positions for density of blanks
            recent_blanks = [idx for idx in result if sorted_indices[i] - idx <= 5]
            if len(recent_blanks) < 3:  # Don't allow more than 3 blanks in 5 consecutive words
                result.append(sorted_indices[i])
    
    return result

def fallback_blank_indices(improved_transcript: str, improved_word_indices: list) -> list:
    """
    Fallback method to generate blank indices if OpenAI API fails.
    Blanks approximately 25% of words at random, excluding improved words and adjacent words.
    Prioritizes blanking less critical words and ensures even distribution.
    """
    logger.info("Starting fallback blank generation method")
    words = improved_transcript.split()
    total_words = len(words)
    
    # Split into sentences for better distribution
    sentences = [s.strip() for s in improved_transcript.split('.') if s.strip()]
    total_sentences = len(sentences)
    
    # Get all valid indices (exclude improved words)
    valid_indices = [i for i in range(total_words) if i not in improved_word_indices]
    
    # Calculate how many words to blank (about 25% of eligible words)
    blank_count = int(len(valid_indices) * 0.25)
    
    if not valid_indices or blank_count <= 0:
        logger.warning("No valid indices for blanking in fallback method")
        return []
    
    # Create a scoring system for words (lower score = more likely to be blanked)
    word_scores = []
    for i, word in enumerate(words):
        if i in valid_indices:
            # Lower score means more likely to be blanked
            score = 1.0
            
            # Don't blank very short words (1-2 letters)
            if len(word) <= 2:
                score += 2.0
            
            # Don't blank words that look like main verbs (ends with -ing, -ed, etc.)
            if any(word.endswith(suffix) for suffix in ['ing', 'ed', 's', 'es']):
                score += 1.0
            
            # Don't blank question words
            if word.lower() in ['what', 'when', 'where', 'who', 'why', 'how', 'which']:
                score += 2.0
            
            # Don't blank common conjunctions
            if word.lower() in ['and', 'or', 'but', 'because', 'if', 'while', 'although']:
                score += 1.5
            
            word_scores.append((i, score))
    
    # Sort by score (lowest first)
    word_scores.sort(key=lambda x: x[1])
    
    # Calculate how many blanks per sentence (minimum 1 if possible)
    blanks_per_sentence = max(1, blank_count // total_sentences)
    
    # Distribute blanks across sentences
    selected_indices = []
    current_sentence = 0
    words_in_current_sentence = 0
    sentence_start = 0
    
    for i, (idx, _) in enumerate(word_scores):
        # Find which sentence this word belongs to
        while current_sentence < len(sentences) and idx >= sentence_start + len(sentences[current_sentence].split()):
            sentence_start += len(sentences[current_sentence].split())
            current_sentence += 1
            words_in_current_sentence = 0
        
        # If we haven't used up our quota for this sentence
        if words_in_current_sentence < blanks_per_sentence:
            selected_indices.append(idx)
            words_in_current_sentence += 1
        
        # If we have enough blanks, stop
        if len(selected_indices) >= blank_count:
            break
    
    # Remove adjacent indices
    final_indices = remove_adjacent_indices(sorted(selected_indices))
    logger.info(f"Fallback method generated {len(final_indices)} blanks")
    return final_indices 