"""
Main entry point for document cross-reference analysis.
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional
from openai import OpenAI

from .toc_generator import generate_toc
from .header_ids import add_header_ids
from .section_tagger import tag_sections, parse_markdown_structure
from .cross_reference_analyzer import analyse_references, collect_all_refs


def analyze_document(document_path: str, api_key: str, output_dir: Optional[str] = None, max_passes: int = 3) -> Dict[str, Any]:
    """
    Complete end-to-end document analysis pipeline.
    
    Args:
        document_path: Path to the document to analyze
        api_key: OpenAI API key
        output_dir: Optional directory to save intermediate files
        max_passes: Number of passes to make at most with LLM.
    
    Returns:
        Dictionary containing all analysis results
    """
    # Setup
    doc_path = Path(document_path)
    if not doc_path.exists():
        raise FileNotFoundError(f"Document not found: {document_path}")
    
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
    else:
        output_path = doc_path.parent
    
    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)
    
    # Read document
    print(f"Reading document: {doc_path}")
    raw_text = doc_path.read_text(encoding="utf-8")
    
    # Step 1: Generate TOC
    print("\nStep 1: Generating Table of Contents")
    toc_md = generate_toc(raw_text, client, max_passes=max_passes)
    
    if output_dir:
        toc_path = output_path / f"{doc_path.stem}_toc.md"
        toc_path.write_text(toc_md, encoding="utf-8")
        print(f"Saved TOC to: {toc_path}")        
        
    # Step 2: Add IDs to TOC
    print("\nStep 2: Adding IDs to TOC")
    toc_ids, id_map = add_header_ids(toc_md)
    
    # Step 3: Tag sections in the text using the IDs
    print("\nStep 3: Tagging Sections")
    tagged_text = tag_sections(toc_ids, raw_text)

    # Save tagged text to output directory
    tagged_output_path = output_path / f"{doc_path.stem}_tagged.txt"
    with open(tagged_output_path, 'w', encoding='utf-8') as f:
        f.write(tagged_text)
    
    # Get smallest chunks
    smallest_chunks = get_smallest_chunks(tagged_text, toc_ids)
    
    # Save smallest chunks to output directory
    chunks_output_path = output_path / f"{doc_path.stem}_smallest_chunks.json"
    with open(chunks_output_path, 'w', encoding='utf-8') as f:
        json.dump(smallest_chunks, f, indent=2, ensure_ascii=False)

    # Step 4: Cross reference the text using the IDs as markers, organized by section depth (level)
    print("\nStep 4: Cross referencing")
    levels_info = analyse_references(toc_ids, tagged_text, client)

    # Step 5: 
    print("\nStep 5: Collecting results")
    all_refs = collect_all_refs(levels_info, tagged_text)
    if output_dir:
        refs_path = output_path / f"{doc_path.stem}_all_refs.json"
        with open(refs_path, "w", encoding="utf-8") as f:
            json.dump(all_refs, f, indent=2)
        print("Saved all_refs JSON to %s", refs_path)

    return {
        "toc_md": toc_md,
        "toc_ids": toc_ids,
        "id_map": id_map,
        "tagged_text": tagged_text,
        "levels_info": levels_info,
        "all_refs": all_refs,
        "smallest_chunks": smallest_chunks
    }

def get_smallest_chunks(tagged_text: str, toc_ids: str) -> Dict[str, str]:
    """
    Extract the smallest/deepest chunks from the document hierarchy.
    
    A chunk is considered "smallest" if it's at the deepest level before
    the hierarchy steps back up to a higher (lower-numbered) level.
    
    Args:
        tagged_text: The document text with section tags
        toc_ids: The TOC IDs
    
    Returns:
        Dict mapping section IDs to their text content
    """
    # Parse the TOC structure to get section hierarchy
    sections = parse_markdown_structure(toc_ids)
    
    if not sections:
        return {}
    
    # Sort sections by their line order in the TOC
    sections.sort(key=lambda x: x['line_index'])
    
    # Identify which sections are "smallest chunks"
    smallest_chunk_ids = []
    
    for i, section in enumerate(sections):
        current_level = section['level']
        
        # Check if this is a leaf node (deepest before stepping back up)
        is_smallest = True
        
        # Look at subsequent sections to see if any go deeper
        for j in range(i + 1, len(sections)):
            next_section = sections[j]
            next_level = next_section['level']
            
            # If we find a deeper level, this isn't a leaf
            if next_level > current_level:
                is_smallest = False
                break
            
            # If we hit the same or higher level, stop looking
            # (we've reached the end of this section's subsections)
            if next_level <= current_level:
                break
        
        if is_smallest:
            smallest_chunk_ids.append(section['id'])
    
    # Extract text content for each smallest chunk
    chunk_texts = {}
    
    for section_id in smallest_chunk_ids:
        # Find the section tags in the tagged text
        start_pattern = rf'\[START SECTION {re.escape(section_id)}:[^\]]*\]'
        end_pattern = rf'\[END SECTION {re.escape(section_id)}:[^\]]*\]'
        
        start_match = re.search(start_pattern, tagged_text)
        end_match = re.search(end_pattern, tagged_text)
        
        if start_match and end_match:
            start_pos = start_match.end()
            end_pos = end_match.start()
            
            if start_pos < end_pos:
                section_text = tagged_text[start_pos:end_pos].strip()
                chunk_texts[section_id] = section_text
            else:
                chunk_texts[section_id] = ""
        else:
            # If we can't find the tags, this section wasn't properly tagged
            chunk_texts[section_id] = ""
    
    return chunk_texts

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run cross‑reference analysis on a single document"
    )
    parser.add_argument("document_path", help="Path to your text or markdown file")
    parser.add_argument(
        "--api-key", "-k", required=True, 
        help="Your OpenAI API key"
    )
    parser.add_argument(
        "--output-dir", "-o", default=None,
        help="Where to write out intermediate files and JSON"
    )
    args = parser.parse_args()

    results = analyze_document(args.document_path, args.api_key, args.output_dir)
