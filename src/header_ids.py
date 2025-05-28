"""
Header IDs Module
Adds unique identifiers to markdown headers.
"""

import re
from typing import Tuple, Dict, Any


HEADER_RE = re.compile(r'^(#{1,6})\s*(.+?)(?:\s*\{#([^}]+)\})?\s*$')


def add_header_ids(toc_md: str) -> Tuple[str, Dict[str, Dict[str, Any]]]:
    """
    Add {#hN} anchors to Markdown headers and return updated markdown and id map.
    
    Args:
        toc_md: Markdown text with headers
        
    Returns:
        Tuple of (updated_markdown, id_map)
        where id_map is {header_id: {"title": str, "level": int}}
    """
    lines = toc_md.splitlines()
    out_lines, id_map = [], {}
    next_id = 1

    for line in lines:
        m = HEADER_RE.match(line)
        if m:
            hashes, title, anchor = m.groups()
            level = len(hashes)

            if not anchor:  # need a new id
                anchor = f"h{next_id}"
                next_id += 1
                line = f"{hashes} {title} {{#{anchor}}}"

            id_map[anchor] = {"title": title.strip(), "level": level}

        out_lines.append(line)

    return "\n".join(out_lines) + "\n", id_map