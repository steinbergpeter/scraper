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
    sections = wikicode.get_sections(flat=True, include_lead=True)

    section_data = {heading: "" for heading in section_columns}

    for i, section in enumerate(sections):
        # First block without heading → Intro
        if i == 0 and not section.filter_headings():
            section_data["Intro"] = section.strip_code().strip()
            continue

        headings = section.filter_headings()
        if not headings:
            continue

        heading = normalize_heading(headings[0].title.strip())
        if heading in section_data:
            content = section.strip_code().strip()
            if section_data[heading]:
                section_data[heading] += "\n\n" + content
            else:
                section_data[heading] = content

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
