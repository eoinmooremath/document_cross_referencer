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
    HEADER_INFO = "Use markdown headers (#, ##, ###, ####, #####, ######) to reflect levels 1-6. After each header line, on the *next* line include a quoted snippet: the first 50 characters of that section … then the last 50 characters, separated by an ellipsis (…).*No other text or keys.* Do not confuse enumerated or unenumerated lists for sections. Do not create a new header for lists or list items."
    
    escaped = escape_markdown(doc_txt)
    return f"""
Extract the top-level headings (level 1) from the document and present them in Markdown.

{HEADER_INFO}

EXAMPLE: If the document contains an Introduction, Conclusion, Chapter 1, and Chapter 2 as the top level sections, then output
# Introduction  
"This is the beginn…" … "…end of Introduction"  
# Chapter 1  
"This is the beginn…" … "…end of Chapter 1"  
# Chapter 2  
"This is the beginn…" … "…end of Chapter 2"  
# Conclusion  
"This is the beginn…" … "…end of Conclusion"  

CRITICAL: Look at every part of the document, from the beginning to the end, to try to find sections.
CRITICAL: Return entries in the exact document order.

DOCUMENT:
{escaped}
"""


def next_pass_prompt(pass_number: int, current_toc_md: str, doc_txt: str) -> str:
    """Generate prompt for subsequent passes of TOC extraction."""
    HEADER_INFO = "Use markdown headers (#, ##, ###, ####, #####, ######) to reflect levels 1-6. After each header line, on the *next* line include a quoted snippet: the first 50 characters of that section … then the last 50 characters, separated by an ellipsis (…).*No other text or keys.* Do not confuse enumerated or unenumerated lists for sections. Do not create a new header for lists or list items."
    
    escaped = escape_markdown(doc_txt)
    return f"""
Expand the current Table of Contents by adding ONE MORE level of sub-headings.

CURRENT TOC (Pass {pass_number-1}):
{current_toc_md}

{HEADER_INFO}

EXAMPLE: If current TOC is:
# Chapter 1
"This is the beginn…" … "…end of Chapter 1" 
## Section 1.1
"This is the beginn…" … "…end of Section 1.1" 
# Chapter 2
"This is the beginn…" … "…end of Chapter 2" 
## Section 2.1 
"This is the beginn…" … "…end of Section 2.2" 
## Section 2.2
"This is the beginn…" … "…end of Section 2.2" 

and Section 1.1 contains "Article 1" and "Article 2", and Section 2.1 contains "Article 3", then output:

# Chapter 1
"This is the beginn…" … "…end of Chapter 1" 
## Section 1.1
"This is the beginn…" … "…end of Section 1.1" 
### Article 1
"This is the beginn…" … "…end of Article 1" 
### Article 2
"This is the beginn…" … "…end of Article 2"
# Chapter 2
"This is the beginn…" … "…end of Chapter 2" 
## Section 2.1 
"This is the beginn…" … "…end of Section 2.2" 
### Article 3
"This is the beginn…" … "…end of Article 3"
## Section 2.2
"This is the beginn…" … "…end of Section 2.2" 


If a heading has no sub-headings, keep it unchanged. If *no* new sub-headings exist anywhere, return *exactly* the same Markdown.

CRITICAL:
1. Maintain exact document order.
2. Add an extra # to indicate one-level-higheer sub-heading.
3. If no new sub-headings anywhere, return the same TOC as input.
4. Look at every part of the document, from the beginning to the end, to try to find sections and headings.

DOCUMENT:
{escaped}
"""


def get_next_level_toc(doc_txt: str, current_toc: str, client: OpenAI, pass_number: int) -> Optional[str]:
    """Get the next level of TOC using OpenAI."""
    prompt = first_pass_prompt(doc_txt) if pass_number == 1 else next_pass_prompt(pass_number, current_toc, doc_txt)

    rsp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "Return a Markdown TOC using # headers plus snippets as instructed."},
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