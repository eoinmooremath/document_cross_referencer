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


def escape_for_fstring(text: str) -> str:
    """Escape text safely for f-string inclusion without making it unreadable."""
    # Replace triple quotes that could break f-strings
    text = text.replace('"""', '"" "')
    text = text.replace("'''", "'' '")
    return text


def first_pass_prompt(doc_txt: str) -> tuple[str, str]:
    """Generate prompt for first pass TOC extraction. Returns (instructions, document)."""
    HEADER_INFO = """Use markdown headers (#, ##, ###, ####, #####, ######) to reflect levels 1-6. After each header line, on the *next* line include a quoted snippet containing EXACTLY 12-15 words that follow the header, exactly as they appear in the document. This word sequence will be used to locate the section in the original document."""
    
    instructions = f"""
Extract the top-level headings (level 1) from the following document and present them in Markdown.

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

CRITICAL RULES:
1. Look for any text that appears to be a structural heading or section title
2. Each quoted snippet must be EXACTLY 12-15 words, no more, no less
3. Return entries in the exact document order
4. Use the exact words as they appear, don't skip or change anything
5. Do NOT copy large blocks of text - only extract section headers with their brief following text
"""
    
    safe_doc = escape_for_fstring(doc_txt)
    return instructions, safe_doc


def next_pass_prompt(pass_number: int, current_toc_md: str, doc_txt: str) -> tuple[str, str]:
    """Generate prompt for subsequent passes of TOC extraction. Returns (instructions, document)."""
    HEADER_INFO = """Use markdown headers (#, ##, ###, ####, #####, ######) to reflect levels 1-6. After each header line, on the *next* line include a quoted snippet containing EXACTLY 12-15 words that follow the header, exactly as they appear in the document. This word sequence will be used to locate the section in the original document."""
    
    instructions = f"""
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

CRITICAL RULES:
1. Look for any text that appears to be a structural heading or section title
2. Each quoted snippet must be EXACTLY 12-15 words, no more, no less
3. Maintain exact document order
4. Add an extra # to indicate one-level-higher sub-heading
5. If no new sub-headings anywhere, return the same TOC as input
6. Use the exact words as they appear, don't skip or change anything
7. Do NOT copy large blocks of text - only extract section headers with their brief following text
"""
    
    safe_doc = escape_for_fstring(doc_txt)
    return instructions, safe_doc


def get_next_level_toc(doc_txt: str, current_toc: str, client: OpenAI, pass_number: int) -> Optional[str]:
    """Get the next level of TOC using OpenAI."""
    if pass_number == 1:
        instructions, document = first_pass_prompt(doc_txt)
    else:
        instructions, document = next_pass_prompt(pass_number, current_toc, doc_txt)

    rsp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "You are a document analyzer. Create a concise table of contents with markdown headers and EXACTLY 12-15 word snippets. Do NOT reproduce large blocks of text. Extract any structural headings or section titles you identify in the document."},
            {"role": "user", "content": instructions},
            {"role": "user", "content": document},
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