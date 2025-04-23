import bz2
import csv
import xml.etree.ElementTree as ET
import mwparserfromhell

bz2_path = 'enwikivoyage-latest-pages-articles.xml.bz2'
output_csv_path = 'us_articles_structured.csv'
NS = '{http://www.mediawiki.org/xml/export-0.11/}'

# Only match U.S. states to reduce false positives
us_keywords = {
    'alabama', 'alaska', 'arizona', 'arkansas', 'california', 'colorado',
    'connecticut', 'delaware', 'florida', 'georgia', 'hawaii', 'idaho',
    'illinois', 'indiana', 'iowa', 'kansas', 'kentucky', 'louisiana',
    'maine', 'maryland', 'massachusetts', 'michigan', 'minnesota',
    'mississippi', 'missouri', 'montana', 'nebraska', 'nevada',
    'new hampshire', 'new jersey', 'new mexico', 'new york',
    'north carolina', 'north dakota', 'ohio', 'oklahoma', 'oregon',
    'pennsylvania', 'rhode island', 'south carolina', 'south dakota',
    'tennessee', 'texas', 'utah', 'vermont', 'virginia', 'washington',
    'west virginia', 'wisconsin', 'wyoming',
}

# Target columns — one per article row
section_columns = [
    "Intro", "Understand", "Talk", "Get in", "Get around", "See", "Do", "Eat",
    "Drink", "Buy", "Sleep", "Stay safe", "Respect", "Connect", "Go next"
]

def normalize_heading(h):
    return h.strip().lower().title()

def is_us_article(text: str, title: str) -> bool:
    title_lower = title.lower()
    text_lower = text.lower()
    return any(state in title_lower or state in text_lower for state in us_keywords)

def extract_sections(wikitext: str):
    wikicode = mwparserfromhell.parse(wikitext)
    
    # Initialize sections dictionary
    section_data = {heading: "" for heading in section_columns}
    
    # Handle introduction (text before first heading)
    intro_text = ""
    nodes = wikicode.nodes
    for node in nodes:
        if isinstance(node, mwparserfromhell.nodes.heading.Heading):
            break
        intro_text += str(node)
    
    if intro_text.strip():
        parsed_intro = mwparserfromhell.parse(intro_text).strip_code().strip()
        section_data["Intro"] = parsed_intro
    
    # Extract all sections with their level
    current_section = None
    current_level = 0
    buffer = ""
    
    for node in nodes:
        if isinstance(node, mwparserfromhell.nodes.heading.Heading):
            # Save content from previous section
            if current_section and buffer:
                parsed_content = mwparserfromhell.parse(buffer).strip_code().strip()
                if parsed_content and current_section in section_data:
                    if section_data[current_section]:
                        section_data[current_section] += "\n\n" + parsed_content
                    else:
                        section_data[current_section] = parsed_content
            
            # Start new section
            heading_title = normalize_heading(str(node.title))
            level = node.level
            
            # Only reset for top-level headings
            if level == 2:  # MediaWiki uses == for top-level section headings
                current_section = heading_title
                current_level = level
                buffer = ""
            else:
                # For subsections, keep the content under the parent section
                # but add the subheading as part of the content
                if current_section:
                    buffer += f"\n{heading_title}\n"
        else:
            # Add content to current section
            if current_section:
                buffer += str(node)
    
    # Don't forget to process the last section
    if current_section and buffer:
        parsed_content = mwparserfromhell.parse(buffer).strip_code().strip()
        if parsed_content and current_section in section_data:
            if section_data[current_section]:
                section_data[current_section] += "\n\n" + parsed_content
            else:
                section_data[current_section] = parsed_content
    
    return section_data

# Progress tracking
total_pages = 0
us_matched = 0
saved_articles = 0
report_every = 500

with open(output_csv_path, mode='w', newline='', encoding='utf-8') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=["Title"] + section_columns)
    writer.writeheader()

    with bz2.open(bz2_path, 'rt', encoding='utf-8') as file:
        for event, elem in ET.iterparse(file, events=('end',)):
            if elem.tag == NS + 'page':
                total_pages += 1

                title_el = elem.find(NS + 'title')
                text_el = elem.find(f'.//{NS}text')

                if title_el is not None and text_el is not None:
                    title = title_el.text
                    text = text_el.text or ''

                    if text.strip().lower().startswith('#redirect'):
                        elem.clear()
                        continue

                    if not is_us_article(text, title):
                        elem.clear()
                        continue

                    us_matched += 1
                    section_data = extract_sections(text)

                    if any(section_data.values()):  # Only save if there's content
                        row = {"Title": title, **section_data}
                        writer.writerow(row)
                        saved_articles += 1

                elem.clear()

                if total_pages % report_every == 0:
                    print(f"📝 Scanned {total_pages} pages — {us_matched} US matches — {saved_articles} saved")

print(f"\n✅ Finished. Total pages: {total_pages}, US matches: {us_matched}, Articles saved: {saved_articles}")
