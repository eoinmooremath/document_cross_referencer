"""
Section Tagger Module
Tags sections in raw text based on markdown structure.
"""

import re
from typing import List, Dict, Optional


def get_header_level(line: str) -> int:
    """Get the header level from a markdown line."""
    match = re.match(r'^(#+)\s', line)
    return len(match.group(1)) if match else 0


def extract_header_id(line: str) -> str:
    """Extract the header ID from a markdown header line."""
    match = re.search(r'\{#([^}]+)\}', line)
    return match.group(1) if match else ""


def extract_header_text(line: str) -> str:
    """Extract the header text without markdown symbols and ID."""
    text = re.sub(r'^#+\s+', '', line)
    text = re.sub(r'\s*\{#[^}]+\}$', '', text)
    return text.strip()


def extract_section_start_text(line: str) -> str:
    """Extract the word sequence that follows a section header."""
    # Handle both ASCII quotes (") and Unicode quotes ("")
    # Look for text between quotes, handling both types
    
    # Try Unicode quotes first (more specific)
    match = re.search(r'"([^"]+)"', line)
    if match:
        return match.group(1).strip()
    
    # Try ASCII quotes
    match = re.search(r'"([^"]+)"', line)
    if match:
        return match.group(1).strip()
    
    return ""


def normalize_text_for_word_matching(text: str) -> str:
    """Normalize text for word-by-word matching by removing formatting but keeping all words."""
    # Convert to lowercase
    text = text.lower()
    
    # Remove all punctuation, numbers, and special characters
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # Replace multiple whitespace with single spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Return the normalized text with all words preserved
    return text.strip()


def find_word_sequence(raw_text: str, search_words: str, start_pos: int = 0) -> Optional[int]:
    """Find a sequence of words in the raw text, ignoring formatting and punctuation."""
    if not search_words:
        return None
    
    # Normalize the search words
    normalized_search = normalize_text_for_word_matching(search_words)
    search_word_list = normalized_search.split()
    
    if len(search_word_list) < 5:  # Need at least 5 words for reliable matching with longer sequences
        return None
    
    # Try exact matching first
    exact_pos = find_word_sequence_exact(raw_text, search_word_list, start_pos)
    if exact_pos is not None:
        return exact_pos
    
    # If exact matching fails, try fuzzy matching
    return find_word_sequence_fuzzy(raw_text, search_word_list, start_pos)


def find_word_sequence_exact(raw_text: str, search_word_list: List[str], start_pos: int = 0) -> Optional[int]:
    """Find exact word sequence match."""
    # Normalize the raw text in chunks to avoid memory issues with very large documents
    chunk_size = 5000  # Process 5000 characters at a time
    overlap = 500      # Overlap to catch sequences that span chunks
    
    pos = start_pos
    while pos < len(raw_text):
        # Get chunk with overlap
        chunk_end = min(pos + chunk_size, len(raw_text))
        chunk = raw_text[pos:chunk_end + overlap]
        
        # Normalize the chunk
        normalized_chunk = normalize_text_for_word_matching(chunk)
        chunk_words = normalized_chunk.split()
        
        # Look for the word sequence in this chunk
        for i in range(len(chunk_words) - len(search_word_list) + 1):
            # Check if we have a match starting at position i
            match = True
            for j, search_word in enumerate(search_word_list):
                if i + j >= len(chunk_words) or chunk_words[i + j] != search_word:
                    match = False
                    break
            
            if match:
                # Found the sequence! Now find the position in the original text
                return estimate_position_in_original(raw_text, pos, chunk, chunk_words, i)
        
        # Move to next chunk
        pos += chunk_size
        if pos >= len(raw_text):
            break
    
    return None


def find_word_sequence_fuzzy(raw_text: str, search_word_list: List[str], start_pos: int = 0) -> Optional[int]:
    """Find fuzzy word sequence match - allows for some words to be different."""
    chunk_size = 5000
    overlap = 500
    min_match_ratio = 0.8  # Require at least 80% of words to match
    
    pos = start_pos
    best_match = None
    best_score = 0
    
    while pos < len(raw_text):
        chunk_end = min(pos + chunk_size, len(raw_text))
        chunk = raw_text[pos:chunk_end + overlap]
        
        normalized_chunk = normalize_text_for_word_matching(chunk)
        chunk_words = normalized_chunk.split()
        
        # Look for fuzzy matches in this chunk
        for i in range(len(chunk_words) - len(search_word_list) + 1):
            # Count how many words match in sequence
            matches = 0
            for j, search_word in enumerate(search_word_list):
                if i + j < len(chunk_words) and chunk_words[i + j] == search_word:
                    matches += 1
            
            match_ratio = matches / len(search_word_list)
            
            # If this is a good enough match and better than what we've found
            if match_ratio >= min_match_ratio and match_ratio > best_score:
                best_score = match_ratio
                best_match = estimate_position_in_original(raw_text, pos, chunk, chunk_words, i)
        
        pos += chunk_size
        if pos >= len(raw_text):
            break
    
    return best_match


def estimate_position_in_original(raw_text: str, chunk_start: int, chunk: str, chunk_words: List[str], word_index: int) -> int:
    """Estimate the position in the original text based on word position in normalized chunk."""
    if word_index == 0:
        return chunk_start
    
    # Get the words before our match
    words_before = chunk_words[:word_index]
    words_before_text = ' '.join(words_before)
    
    # Estimate position in original chunk
    if words_before_text:
        # Look for a substring that contains these words
        chunk_lower = chunk.lower()
        estimated_pos = 0
        for word in words_before:
            word_pos = chunk_lower.find(word, estimated_pos)
            if word_pos >= 0:
                estimated_pos = word_pos + len(word)
        
        return chunk_start + estimated_pos
    else:
        return chunk_start


def find_header_directly(raw_text: str, header_text: str, start_pos: int = 0) -> Optional[int]:
    """Try to find a header directly by looking for its exact text in header-like contexts only."""
    if not header_text:
        return None
    
    # Try different variations of the header
    header_variations = [
        header_text,
        header_text.upper(),
        header_text.lower(),
        header_text.title(),
    ]
    
    for variation in header_variations:
        escaped_header = re.escape(variation)
        
        # Strategy 1: Header at start of line (most reliable)
        pattern = r'(?:^|\n)\s*' + escaped_header + r'(?:\s*$|\s+[A-Z]|\s*\n)'
        try:
            match = re.search(pattern, raw_text[start_pos:], re.IGNORECASE | re.MULTILINE)
            if match:
                # Return position of the actual header text
                match_text = match.group()
                header_pos_in_match = match_text.lower().find(variation.lower())
                if header_pos_in_match >= 0:
                    return start_pos + match.start() + header_pos_in_match
        except re.error:
            continue
        
        # Strategy 2: Header with typical context patterns
        header_context_patterns = [
            # Header followed by a number (like "Article 5", "Section 1.1")
            r'(?:^|\n)\s*' + escaped_header + r'\s+[0-9]+(?:\.[0-9]+)*(?:\s|$|\n)',
            # Header followed by a colon or dash (like "CHAPTER II:")
            r'(?:^|\n)\s*' + escaped_header + r'\s*[:\-]',
            # Header in all caps at start of line (like "CHAPTER II")
            r'(?:^|\n)\s*' + escaped_header.upper() + r'(?:\s*$|\s*\n)',
        ]
        
        for context_pattern in header_context_patterns:
            try:
                match = re.search(context_pattern, raw_text[start_pos:], re.IGNORECASE | re.MULTILINE)
                if match:
                    # Find where the actual header text starts within the match
                    match_text = match.group()
                    header_pos_in_match = match_text.lower().find(variation.lower())
                    if header_pos_in_match >= 0:
                        return start_pos + match.start() + header_pos_in_match
            except re.error:
                continue
    
    return None


def find_header_position_from_sequence(raw_text: str, header_text: str, sequence_pos: int) -> Optional[int]:
    """
    Given the position of a word sequence, find where the actual header starts.
    The sequence represents content that comes AFTER the header.
    """
    if sequence_pos <= 0:
        return None
    
    # Look backwards from the sequence position to find the header
    # We'll search in a reasonable window before the sequence
    search_start = max(0, sequence_pos - 200)  # Smaller window for word-based approach
    search_text = raw_text[search_start:sequence_pos]
    
    # Try to find the header text in this window
    header_variations = [
        header_text,
        header_text.upper(),
        header_text.lower(),
        header_text.title(),
    ]
    
    for variation in header_variations:
        # Look for the header, preferring positions closer to the sequence
        pos = search_text.rfind(variation)  # rfind = rightmost occurrence
        if pos >= 0:
            return search_start + pos
    
    # If we can't find the exact header text, return the sequence position
    # This is a fallback - the tag will be placed at the content start
    return sequence_pos


def parse_markdown_structure(markdown_text: str) -> List[Dict]:
    """Parse markdown to extract section structure with hierarchy."""
    lines = markdown_text.split('\n')
    sections = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        level = get_header_level(line)
        if level == 0:
            continue
            
        header_id = extract_header_id(line)
        header_text = extract_header_text(line)
        start_text = extract_section_start_text(line)
        
        # Get the next line which should contain the quoted text
        if i + 1 < len(lines) and not start_text:
            next_line = lines[i + 1].strip()
            start_text = extract_section_start_text(next_line)
        
        if header_id:  # Only require header_id
            sections.append({
                'id': header_id,
                'level': level,
                'title': header_text,
                'start_text': start_text,
                'line_index': i
            })
    
    return sections


def tag_sections(markdown_text: str, raw_text: str) -> str:
    """
    Tag sections in raw text based on markdown structure.
    
    Args:
        markdown_text: The markdown TOC with section headers and word sequences
        raw_text: The full document text to be tagged
    
    Returns:
        The raw text with section tags inserted
    """
    # Parse markdown structure
    sections = parse_markdown_structure(markdown_text)
    if not sections:
        return raw_text
    
    # Sort sections by their appearance order
    sections.sort(key=lambda x: x['line_index'])
    
    # First pass: Find all section positions
    section_positions = {}
    
    for i, section in enumerate(sections):
        header_pos = None
        sequence_pos = None
        
        # Strategy 1: Use the word sequence to find the section
        if section['start_text']:
            sequence_pos = find_word_sequence(raw_text, section['start_text'], 0)
            if sequence_pos is not None:
                # The sequence represents content AFTER the header
                # So we need to find where the header actually starts
                header_pos = find_header_position_from_sequence(raw_text, section['title'], sequence_pos)
        
        # Strategy 2: If word sequence search fails, try to find the header directly
        if header_pos is None and section['title']:
            header_pos = find_header_directly(raw_text, section['title'], 0)
        
        # Strategy 3: Try finding the section ID if it appears in text (last resort)
        if header_pos is None and section['id']:
            id_pattern = r'\b' + re.escape(section['id']) + r'\b'
            try:
                match = re.search(id_pattern, raw_text, re.IGNORECASE)
                if match:
                    header_pos = match.start()
            except re.error:
                pass
        
        if header_pos is not None:
            section_positions[section['id']] = {
                'section': section,
                'start': header_pos,
                'sequence_pos': sequence_pos,  # Keep track of both positions
                'end': None  # Will be determined later
            }
        else:
            print(f"Warning: Could not find section {section['id']} ({section['title']}) in document")
            # Debug info
            if section['start_text']:
                print(f"  Searched for words: {repr(section['start_text'])}")
    
    # Sort all found positions by their start position
    sorted_positions = sorted(section_positions.items(), key=lambda x: x[1]['start'])
    
    # Second pass: Determine end positions based on hierarchy
    tagged_positions = []
    
    for i, (sec_id, pos_info) in enumerate(sorted_positions):
        section = pos_info['section']
        start_pos = pos_info['start']
        
        # Find where this section ends
        # Look through all subsequent sections in document order
        end_pos = len(raw_text)  # Default to end of document
        
        for j in range(i + 1, len(sorted_positions)):
            next_id, next_pos_info = sorted_positions[j]
            next_section = next_pos_info['section']
            next_start = next_pos_info['start']
            
            # If the next section is at the same level or higher (lower number), this is our end
            if next_section['level'] <= section['level']:
                end_pos = next_start
                break
        
        tagged_positions.append({
            'id': section['id'],
            'title': section['title'],
            'level': section['level'],
            'start': start_pos,
            'end': end_pos
        })
    
    # Sort positions by start position (in reverse for insertion)
    tagged_positions.sort(key=lambda x: x['start'], reverse=True)
    
    # Insert tags into the text
    result = raw_text
    for pos in tagged_positions:
        # Insert end tag
        end_tag = f" [END SECTION {pos['id']}: {pos['title']}]"
        result = result[:pos['end']] + end_tag + result[pos['end']:]
        
        # Insert start tag
        start_tag = f"[START SECTION {pos['id']}: {pos['title']}] "
        result = result[:pos['start']] + start_tag + result[pos['start']:]
    
    return result