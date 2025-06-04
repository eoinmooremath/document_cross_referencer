"""
Cross Reference Analyzer Module
Analyzes documents to find cross-references between sections.
"""

import re
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI


HEADER_RE = re.compile(r'^(#{1,6})\s*(.+?)\s*\{#([^}]+)\}\s*$', re.MULTILINE)
START_RE = re.compile(r'\[START SECTION ([^:]+): ([^\]]+)\]')
END_RE = re.compile(r'\[END SECTION ([^:]+): ([^\]]+)\]')


def parse_toc_md(md: str) -> Dict[str, Dict[str, Any]]:
    """Parse TOC markdown to extract header info."""
    return {m.group(3): {"title": m.group(2).strip(), "level": len(m.group(1))}
            for m in HEADER_RE.finditer(md)}


def parse_tagged_text(txt: str) -> List[Dict[str, str]]:
    """Parse tagged text to extract sections."""
    out, pos = [], 0
    while (m := START_RE.search(txt, pos)):
        hid = m.group(1)
        mend = END_RE.search(txt, m.end())
        if not mend or mend.group(1) != hid:
            raise ValueError(f"Unmatched tags for {hid}")
        out.append({"id": hid, "text": txt[m.end(): mend.start()].strip()})
        pos = mend.end()
    return out


def build_cross_ref_prompt(markdown_table: str, wrapped_text: str) -> str:
    """Build prompt for GPT to find all cross-references."""
    return f"""Analyze this legal document to find ALL cross-references between sections.

The document has:
1. A table of contents in Markdown format with section titles and {{#id}} anchors
2. The full document text where each section is wrapped with [START SECTION id] and [END SECTION id] tags

Your task: Go through EVERY section and find ALL references to other sections. Look for any text that refers to another part of the document.

Common reference patterns include:
- Direct section/article references: "Section 2.01", "Article III", "Schedule 1.01(b)"
- References with context: "as defined in...", "pursuant to...", "set forth in...", "in accordance with...", "under...", "as provided in...", "subject to...", "as described in...", "the provisions of...", "requirements of...", "conditions in..."
- Any other way one section mentions another section

Return a JSON object listing every reference found:
{{"refs": [
   {{"from": "h1", "to": ["h22", "h35"]}},
   {{"from": "h22", "to": ["h1", "h44", "h67"]}},
   {{"from": "h35", "to": ["h22"]}}
]}}

Where "from" is the section ID containing the reference, and "to" is a list of section IDs it references.

Important: 
- Check EVERY section, even if it seems to have no references
- Include ALL references found, don't skip any
- Use the exact section IDs from the tags (h1, h22, etc.)
- Match references to the correct section IDs using the table of contents

--- MARKDOWN TABLE OF CONTENTS ---
{markdown_table}
--- END MARKDOWN TABLE OF CONTENTS ---

--- TAGGED DOCUMENT ---
{wrapped_text}
--- END TAGGED DOCUMENT ---"""


def extract_section_text(section_id: str, tagged_text: str) -> str:
    """Extract clean text for a specific section from the tagged document."""
    # Pattern for [START SECTION h1: ARTICLE I] format
    start_pattern = f'\\[START SECTION {re.escape(section_id)}: [^\\]]+\\]'
    end_pattern = f'\\[END SECTION {re.escape(section_id)}: [^\\]]+\\]'
    
    start_match = re.search(start_pattern, tagged_text, re.IGNORECASE)
    end_match = re.search(end_pattern, tagged_text, re.IGNORECASE)
    
    if not start_match or not end_match or end_match.start() <= start_match.end():
        return ""
    
    # Extract text between the tags
    raw_text = tagged_text[start_match.end():end_match.start()]
    
    # Remove all nested section tags
    return re.sub(r'\[(?:START|END)\s+SECTION\s+[^\]]+\]', '', raw_text, flags=re.IGNORECASE).strip()


def analyse_references(toc_md_text: str, tagged_text: str, client: OpenAI) -> List[Dict]:
    """
    Analyze document to find all cross-references.
    
    Args:
        toc_md_text: Markdown TOC with header IDs
        tagged_text: Document text with section tags
        client: OpenAI client instance
        
    Returns:
        List of dictionaries grouped by level containing section info and references
    """
    toc_map = parse_toc_md(toc_md_text)    
    prompt = build_cross_ref_prompt(toc_md_text, tagged_text)
    
    rsp = client.chat.completions.create(
        model="gpt-4.1-mini",  
        messages=[
            {"role": "system", "content": "Return only the JSON specified."},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        max_tokens=32000,
        response_format={"type": "json_object"},
    )
    refs_json = json.loads(rsp.choices[0].message.content)
    
    # Build complete section info with all sections from TOC
    all_sections = {}
    
    # First, add all sections from TOC
    for section_id, info in toc_map.items():
        all_sections[section_id] = {
            "section_title": info["title"],
            "section_id": section_id,
            "references": [],
            "text": extract_section_text(section_id, tagged_text),
            "level": info["level"]
        }
    
    # Then, add references from GPT results
    for ref in refs_json.get("refs", []):
        from_id = ref["from"]
        to_ids = ref["to"]
        if from_id in all_sections:
            all_sections[from_id]["references"] = to_ids
    
    # Group by level
    level_map: Dict[int, List] = {}
    for section_id, section_data in all_sections.items():
        level = section_data["level"]
        level_map.setdefault(level, []).append({
            "section_title": section_data["section_title"],
            "section_id": section_data["section_id"],
            "references": section_data["references"],
            "text": section_data["text"]
        })
    
    return [{"level": lvl, "chunks": chunks} for lvl, chunks in sorted(level_map.items())]


def collect_refs_texts(section_id: str, structured: List[Dict], tagged_text: str = None) -> List[str]:
    """Collect the text of all sections referenced by the given section."""
    # Find which sections this section references
    referenced_ids = []
    for lvl in structured:
        for c in lvl["chunks"]:
            if c["section_id"] == section_id:
                referenced_ids = c["references"]
                break
        if referenced_ids:
            break
    
    if not referenced_ids:
        return []
    
    # If tagged_text is provided, extract fresh text for each referenced section
    if tagged_text:
        return [extract_section_text(ref_id, tagged_text) for ref_id in referenced_ids]
    
    # Otherwise, use the text from the structured data
    id_to_text = {c["section_id"]: c["text"] for lvl in structured for c in lvl["chunks"]}
    return [id_to_text[r] for r in referenced_ids if r in id_to_text]

def collect_all_refs(
    structured: List[Dict],
    tagged_text: Optional[str] = None
) -> Dict[str, List[str]]:
    result = {}
    for lvl in structured:
        for c in lvl["chunks"]:
            result[c["section_id"]] = collect_refs_texts(
                c["section_id"], structured, tagged_text
            )
    return result

