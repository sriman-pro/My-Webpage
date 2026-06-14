#!/usr/bin/env python
# coding: utf-8

# Reads a single .bib file (mypublist.bib) and generates one Markdown file
# per entry in ../_publications/. Handles article, inproceedings, incollection,
# misc, and any other type by detecting which venue field is present.

from pybtex.database.input import bibtex
import pybtex.database.input.bibtex
from time import strptime
import html
import os
import re

BIB_FILE = "../mypublist.bib"

html_escape_table = {"&": "&amp;", '"': "&quot;", "'": "&apos;"}

def html_escape(text):
    return "".join(html_escape_table.get(c, c) for c in text)

def get_category(entry_type):
    if entry_type in ("article",):
        return "manuscripts"
    if entry_type in ("inproceedings", "conference"):
        return "conferences"
    if entry_type in ("incollection",):
        return "books"
    if entry_type == "misc":
        return "conferences"
    return "manuscripts"

def get_venue(entry_type, fields):
    """Return (venue_pretext, venue_value) based on entry type and available fields."""
    if entry_type in ("article",):
        return "", fields.get("journal", "")
    if entry_type in ("inproceedings", "conference"):
        return "In the proceedings of ", fields.get("booktitle", "")
    if entry_type in ("incollection",):
        return "In ", fields.get("booktitle", "")
    if entry_type == "misc":
        return "", fields.get("howpublished", fields.get("note", ""))
    # fallback: try journal then booktitle
    if "journal" in fields:
        return "", fields["journal"]
    if "booktitle" in fields:
        return "In ", fields["booktitle"]
    return "", fields.get("publisher", "")

import pybtex.errors
pybtex.errors.set_strict_mode(False)

parser = bibtex.Parser()
bibdata = parser.parse_file(BIB_FILE)

os.makedirs("../_publications", exist_ok=True)

for bib_id in bibdata.entries:
    entry = bibdata.entries[bib_id]
    b = entry.fields
    entry_type = entry.type.lower()

    pub_year = "1900"
    pub_month = "01"
    pub_day = "01"

    try:
        pub_year = str(b["year"])

        if "month" in b:
            m = b["month"].strip()
            if m.isdigit():
                pub_month = m.zfill(2)
            else:
                try:
                    pub_month = "{:02d}".format(strptime(m[:3], '%b').tm_mon)
                except ValueError:
                    pass

        if "day" in b:
            pub_day = str(b["day"])

        pub_date = f"{pub_year}-{pub_month}-{pub_day}"

        raw_title = b["title"].replace("{", "").replace("}", "").replace("\\", "")
        clean_title = raw_title.replace(" ", "-")
        url_slug = re.sub(r"\[.*?\]|[^a-zA-Z0-9_-]", "", clean_title).replace("--", "-")[:100]

        md_filename = f"{pub_date}-{url_slug}.md".replace("--", "-")
        html_filename = f"{pub_date}-{url_slug}".replace("--", "-")

        # Build citation string
        citation = ""
        for author in entry.persons.get("author", []):
            first = author.first_names[0] if author.first_names else ""
            last = author.last_names[0] if author.last_names else ""
            citation += f" {first} {last},"

        citation += f' "{html_escape(raw_title)}."'

        venue_pretext, venue_val = get_venue(entry_type, b)
        venue_val = venue_val.replace("{", "").replace("}", "").replace("\\", "")
        venue = venue_pretext + venue_val
        citation += f" {html_escape(venue)}, {pub_year}."

        # Build markdown
        md = f'---\ntitle: "{html_escape(raw_title)}"\n'
        md += "collection: publications\n"
        md += f"category: {get_category(entry_type)}\n"
        md += f"permalink: /publication/{html_filename}\n"

        note = b.get("note", "")
        if len(note) > 5:
            md += f"excerpt: '{html_escape(note)}'\n"

        md += f"date: {pub_date}\n"
        md += f"venue: '{html_escape(venue)}'\n"

        url = b.get("url", "")
        if len(url) > 5:
            md += f"paperurl: '{url}'\n"

        md += f"citation: '{html_escape(citation)}'\n"
        md += "---\n"

        if note and len(note) > 5:
            md += html_escape(note) + "\n"

        if url and len(url) > 5:
            md += f'\n[Access paper here]({url}){{:target="_blank"}}\n'
        else:
            md += f"\nUse [Google Scholar](https://scholar.google.com/scholar?q={html.escape(clean_title.replace('-', '+'))}){{:target=\"_blank\"}} for full citation\n"

        out_path = os.path.join("../_publications", os.path.basename(md_filename))
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(md)

        print(f'OK  {bib_id}: "{raw_title[:70]}{"..." if len(raw_title) > 70 else ""}"')

    except KeyError as e:
        print(f'WARN missing field {e} in entry {bib_id}: "{b.get("title", "???")[:40]}"')
        continue
