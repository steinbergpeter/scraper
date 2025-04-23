import bz2
import xml.etree.ElementTree as ET

bz2_path = 'enwikivoyage-latest-pages-articles.xml.bz2'
NS = '{http://www.mediawiki.org/xml/export-0.11/}'  # Expected namespace

page_count = 0

with bz2.open(bz2_path, 'rt', encoding='utf-8') as file:
    for event, elem in ET.iterparse(file, events=('end',)):
        print(f"TAG: {elem.tag}")  # Print actual tag name to confirm namespace
        if 'page' in elem.tag:
            print("\n🎯 Found a page element!\n")
            print(ET.tostring(elem, encoding='unicode')[:1000])  # Print first 1000 chars
            break
