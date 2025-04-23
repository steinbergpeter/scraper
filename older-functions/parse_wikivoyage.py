import xml.etree.ElementTree as ET
import csv
import re

# Define the sections to extract
SECTIONS = ["Understand", "Talk", "Get in", "Get around", "See", "Do", "Eat",
            "Drink", "Buy", "Sleep", "Stay safe", "Respect", "Connect", "Go next"]

def extract_sections(text):
    # Regular expression to find section headings
    section_regex = re.compile(r'==\s*(.+?)\s*==')
    sections = {}
    last_pos = 0
    last_section = "Intro"
    for match in section_regex.finditer(text):
        section_title = match.group(1).strip()
        start = match.start()
        content = text[last_pos:start].strip()
        if last_section in sections:
            sections[last_section] += "\n" + content
        else:
            sections[last_section] = content
        last_section = section_title
        last_pos = match.end()
    # Capture the content after the last section
    content = text[last_pos:].strip()
    if last_section in sections:
        sections[last_section] += "\n" + content
    else:
        sections[last_section] = content
    return sections

def parse_wikivoyage_dump(xml_file, output_csv):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    ns = {'ns': 'http://www.mediawiki.org/xml/export-0.10/'}

    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ["Title", "Intro"] + SECTIONS
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        count = 0
        for page in root.findall('.//ns:page', ns):
            title = page.find('ns:title', ns).text
            revision = page.find('ns:revision', ns)
            if revision is None:
                continue
            text_elem = revision.find('ns:text', ns)
            if text_elem is None or text_elem.text is None:
                continue
            text = text_elem.text

            sections = extract_sections(text)

            # Filter out articles that don't have any of the desired sections
            if not any(sec in sections for sec in SECTIONS):
                continue

            row = {"Title": title}
            for sec in ["Intro"] + SECTIONS:
                row[sec] = sections.get(sec, "")
            writer.writerow(row)

            count += 1
            if count % 100 == 0:
                print(f"Processed {count} articles...")

    print(f"Finished processing. Total articles written: {count}")
