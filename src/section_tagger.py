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
    """Extract the starting text of a section from the markdown line."""
    # Handle both ASCII quotes (") and Unicode quotes ("")
    # Look for text between quotes, handling both types
    
    # Try Unicode quotes first (more specific)
    match = re.search(r'"([^"]+)"', line)
    if match:
        full_text = match.group(1)
        # Extract text before the ellipsis
        if '…' in full_text:
            start_text = full_text.split('…')[0].strip()
        elif '...' in full_text:
            start_text = full_text.split('...')[0].strip()
        else:
            # If no ellipsis, take first 100 chars
            start_text = full_text[:100]
        return start_text
    
    # Try ASCII quotes
    match = re.search(r'"([^"]+)"', line)
    if match:
        full_text = match.group(1)
        # Extract text before the ellipsis
        if '…' in full_text:
            start_text = full_text.split('…')[0].strip()
        elif '...' in full_text:
            start_text = full_text.split('...')[0].strip()
        else:
            # If no ellipsis, take first 100 chars
            start_text = full_text[:100]
        return start_text
    
    return ""


def create_search_pattern(text: str) -> str:
    """Create a regex pattern that matches text with flexible whitespace."""
    # Escape special regex characters
    escaped = re.escape(text)
    # Replace whitespace with flexible whitespace pattern
    # \s+ matches one or more whitespace characters (including newlines)
    pattern = re.sub(r'\\\s+', r'\\s+', escaped)
    return pattern


def fast_find_text(raw_text: str, search_text: str, start_pos: int = 0) -> Optional[int]:
    """
    Fast text search using regex with flexible whitespace matching.
    """
    if not search_text:
        return None
    
    # Try different search strategies in order of preference
    strategies = [
        # Strategy 1: Full text with flexible whitespace
        lambda: create_search_pattern(search_text),
        
        # Strategy 2: First 5 words
        lambda: r'\s+'.join(re.escape(word) for word in search_text.split()[:5]),
        
        # Strategy 3: First 3 words with very flexible spacing
        lambda: r'\s*'.join(re.escape(word) for word in search_text.split()[:3]),
        
        # Strategy 4: Key phrases (skip common words)
        lambda: r'.{0,50}'.join(re.escape(word) for word in 
                [w for w in search_text.split() if len(w) > 4][:3])
    ]
    
    for i, strategy_func in enumerate(strategies):
        try:
            pattern = strategy_func()
            if pattern:
                match = re.search(pattern, raw_text[start_pos:], re.IGNORECASE | re.DOTALL)
                if match:
                    return start_pos + match.start()
        except (re.error, IndexError):
            continue
    
    # Last resort: Look for any 2-3 distinctive words from the text
    words = [w for w in search_text.split() if len(w) > 3]
    if len(words) >= 2:
        # Try pairs of distinctive words
        for i in range(len(words) - 1):
            pattern = re.escape(words[i]) + r'.{0,100}' + re.escape(words[i+1])
            try:
                match = re.search(pattern, raw_text[start_pos:], re.IGNORECASE | re.DOTALL)
                if match:
                    return start_pos + match.start()
            except re.error:
                continue
    
    return None


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
        markdown_text: The markdown TOC with section headers and start text
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
        if not section['start_text']:
            continue
            
        # Start searching from beginning for each section to find its actual position
        pos = fast_find_text(raw_text, section['start_text'], 0)
        
        if pos is not None:
            section_positions[section['id']] = {
                'section': section,
                'start': pos,
                'end': None  # Will be determined later
            }
    
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
        end_tag = f" [END SECTION {pos['id']}]"
        result = result[:pos['end']] + end_tag + result[pos['end']:]
        
        # Insert start tag
        start_tag = f"[START SECTION {pos['id']}: {pos['title']}] "
        result = result[:pos['start']] + start_tag + result[pos['start']:]
    
    return result