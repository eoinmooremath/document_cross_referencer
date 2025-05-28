# src/main.py
"""
Main entry point for document cross-reference analysis.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional
from openai import OpenAI

from .toc_generator import generate_toc
from .header_ids import add_header_ids
from .section_tagger import tag_sections
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
    # pretty‑print just the cross‑refs to stdout:
    print(json.dumps(results["all_refs"], indent=2))
