"""
TOC Generator Module
Generates table of contents from documents using OpenAI API.
"""

import re
from typing import Optional
from openai import OpenAI


def escape_markdown(text: str) -> str:
    """Escape characters that can break Markdown when we embed raw excerpts."""
    return re.sub(r"([*_~`\\[\\]()>#\-+={}|.!])", r"\\\1", text)


def first_pass_prompt(doc_txt: str) -> str:
    """Generate prompt for first pass TOC extraction."""
    HEADER_INFO = """Use markdown headers (#, ##, ###, ####, #####, ######) to reflect levels 1-6. After each header line, on the *next* line include a quoted snippet containing the first 12-15 words that follow the header, exactly as they appear in the document. This word sequence will be used to locate the section in the original document."""
    
    return f"""
Extract the top-level headings (level 1) from the document and present them in Markdown.

{HEADER_INFO}

EXAMPLE: If the document contains:
CHAPTER I
General provisions
(1) This Regulation lays down rules relating to the protection of natural persons...

Then output:
# CHAPTER I  
"General provisions This Regulation lays down rules relating to the protection of natural persons"

EXAMPLE: If the document contains:
Article 5    Principles relating to processing of personal data
1. Personal data shall be processed lawfully, fairly and in a transparent manner...

Then output:
# Article 5  
"Principles relating to processing of personal data Personal data shall be processed lawfully fairly and in"

CRITICAL: Look at every part of the document, from the beginning to the end, to try to find sections.
CRITICAL: Return entries in the exact document order.
CRITICAL: Use the exact words as they appear, don't skip or change anything.
CRITICAL: Do NOT copy the entire document - only extract section headers and their following words.

DOCUMENT:
{doc_txt}
"""


def next_pass_prompt(pass_number: int, current_toc_md: str, doc_txt: str) -> str:
    """Generate prompt for subsequent passes of TOC extraction."""
    HEADER_INFO = """Use markdown headers (#, ##, ###, ####, #####, ######) to reflect levels 1-6. After each header line, on the *next* line include a quoted snippet containing the first 12-15 words that follow the header, exactly as they appear in the document. This word sequence will be used to locate the section in the original document."""
    
    return f"""
Expand the current Table of Contents by adding ONE MORE level of sub-headings.

CURRENT TOC (Pass {pass_number-1}):
{current_toc_md}

{HEADER_INFO}

EXAMPLE: If current TOC is:
# Chapter 1
"Introduction This document establishes the rules for the protection of personal data processing within the European Union" 
## Section 1.1
"Overview This section provides the general framework for the implementation of data protection measures across all member states" 

and Section 1.1 contains "Article 1" and "Article 2", then output:

# Chapter 1
"Introduction This document establishes the rules for the protection of personal data processing within the European Union" 
## Section 1.1
"Overview This section provides the general framework for the implementation of data protection measures across all member states" 
### Article 1
"Definitions For the purposes of this regulation the following definitions shall apply to all processing activities undertaken" 
### Article 2
"Scope This article applies to the processing of personal data wholly or partly by automated means"

If a heading has no sub-headings, keep it unchanged. If *no* new sub-headings exist anywhere, return *exactly* the same Markdown.

CRITICAL:
1. Maintain exact document order.
2. Add an extra # to indicate one-level-higher sub-heading.
3. If no new sub-headings anywhere, return the same TOC as input.
4. Look at every part of the document, from the beginning to the end, to try to find sections and headings.
5. Use the exact words as they appear, don't skip or change anything.
6. Do NOT copy the entire document - only extract section headers and their following words.

DOCUMENT:
{doc_txt}
"""


def get_next_level_toc(doc_txt: str, current_toc: str, client: OpenAI, pass_number: int) -> Optional[str]:
    """Get the next level of TOC using OpenAI."""
    prompt = first_pass_prompt(doc_txt) if pass_number == 1 else next_pass_prompt(pass_number, current_toc, doc_txt)

    rsp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "You are a document analyzer. Create a concise table of contents with markdown headers and word snippets. Do NOT reproduce the entire document text - only extract section headers and their following 12-15 words."},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        max_tokens=32768,
    )
    return rsp.choices[0].message.content.strip()


def generate_toc(doc_txt: str, client: OpenAI, max_passes: int = 10) -> str:
    """Generate complete TOC for document."""
    toc_md = ""
    for p in range(1, max_passes + 1):
        print(f"\nPASS {p}")
        new_md = get_next_level_toc(doc_txt, toc_md, client, p)
        if not new_md or new_md == toc_md:
            print("No further expansion. Done.")
            break
        toc_md = new_md
        print(f"Completed pass {p}")
    return toc_md