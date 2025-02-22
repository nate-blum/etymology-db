import csv
import bz2
import logging
import re
from multiprocessing import Pool
from datetime import datetime, timedelta
from pathlib import Path
from typing import Generator, List, Tuple

import mwparserfromhell as mwp
import requests
from lxml import etree
from mwparserfromhell.nodes.extras import Parameter
from mwparserfromhell.nodes.template import Template
from mwparserfromhell.nodes.text import Text
from mwparserfromhell.nodes.wikilink import Wikilink
from mwparserfromhell.wikicode import Wikicode

from elements import Etymology
from templates import parse_template

NAMESPACE = "{http://www.mediawiki.org/xml/export-0.10/}"

WIKI_FILENAME = "enwiktionary-20220820-pages-articles-multistream.xml.bz2"
WIKTIONARY_URL = f"http://dumps.wikimedia.your.org/enwiktionary/20220820/{WIKI_FILENAME}"

DOWNLOAD_PATH = Path("./").joinpath(WIKI_FILENAME)
OUTPUT_DIR = Path.cwd()
ETYMOLOGY_PATH = OUTPUT_DIR.joinpath("etymology_orig.csv")

def tag(s: str):
    return NAMESPACE + s

def download(url: str) -> None:
    """
    Downloads the file at the URL to `DOWNLOAD_PATH`
    """
    if DOWNLOAD_PATH.exists():
        logging.info("File already exists, skipping download.")
        return

    logging.info("Downloading {}".format(url))
    r = requests.get(url)
    with open(DOWNLOAD_PATH, 'wb') as f:
        f.write(r.content)
    logging.info("Downloaded {}".format(url))

def write_all():
    with open(ETYMOLOGY_PATH, "w") as f_out:
        writer = csv.writer(f_out)
        writer.writerow(Etymology.header())
        entries_parsed = 0
        time = datetime.now()
        for etys in Pool().imap_unordered(parse_wikitext, stream_terms()):
            if not etys:
                continue
            rows = [e.to_row() for e in etys]
            entries_parsed += len(rows)
            writer.writerows(rows)
            elapsed = (datetime.now() - time)
            if elapsed.total_seconds() > 1:
                elapsed -= timedelta(microseconds=elapsed.microseconds)
            print(f"Entries parsed: {entries_parsed} Time elapsed: {elapsed} "
                    f"Entries per second: {entries_parsed // elapsed.total_seconds()}{' ' * 10}", end="\r", flush=True)
        print("")


def stream_terms() -> Generator[Tuple[str, str], None, None]:
    with bz2.open(DOWNLOAD_PATH, "rb") as f_in:
        for event, elem in etree.iterparse(f_in, huge_tree=True):
            if "text" in elem.tag:
                page = elem.getparent().getparent()
                ns = page.find(tag("ns"))
                if ns is not None and ns.text == "0":
                    term = elem.getparent().getparent().find(tag("title")).text
                    yield term, elem.text
                page.clear()

def parse_wikitext(unparsed_data: Tuple[str, str]) -> List[Etymology]:
    term, unparsed_wikitext = unparsed_data
    wikitext = mwp.parse(unparsed_wikitext)
    parsed_etys = []
    for language_section in wikitext.get_sections(levels=[2]):
        lang = str(language_section.nodes[0].title)
        etymologies = language_section.get_sections(matches="Etymology", flat=True, include_headings=True)
        for e in etymologies:
            etym_idx = 0
            if type(e.nodes[0]) == mwp.nodes.Heading and any(char.isdigit() for char in str(e.nodes[0].title)):
                nums = re.findall(r'\b\d+\b', str(e.nodes[0].title))
                etym_idx = int(nums[0]) - 1 if len(nums) > 0 else 0

            clean_wikicode(e)
            for template in e.ifilter_templates(recursive=False):
                name = str(template.name)
                parsed = parse_template(name, term, lang, template, etym_idx)
                parsed_etys.extend([e for e in parsed if e.is_valid()])
    return [e for e in parsed_etys if e.is_valid()]


def clean_wikicode(wc: Wikicode):
    """
    Performs operations on each etymology section that get rid of extraneous nodes
    and create new templates based on natural-language parsing.
    """
    cleaner = lambda x: ((not isinstance(x, (Text, Wikilink, Template))) or
                         (isinstance(x, Text) and not bool(x.value.strip())))
    for node in wc.filter(recursive=False, matches=cleaner):
        wc.remove(node)

    merge_etyl_templates(wc)
    get_plus_combos(wc)
    get_comma_combos(wc)
    get_from_chains(wc)
    remove_links(wc)


def combine_template_chains(wc: Wikicode, new_template_name: str,
                            template_indices: List[int], text_indices: List[int]) -> None:
    """
    Helper function for combining templates that are linked via free text into
    a structured template hierarchy.
    """
    index_combos = []

    index_combo = []
    combine = False
    for i in template_indices:
        if (i+1 in text_indices) or (i-2 in index_combo and combine):
            index_combo.append(i)

        combine = i+1 in text_indices
        if not combine:
            if len(index_combo) > 1:
                index_combos.append(index_combo)
            index_combo = []

    if len(index_combo) > 1:
        index_combos.append(index_combo)

    combo_nodes = [[wc.nodes[i] for i in chain] for chain in index_combos]

    for combo in combo_nodes:
        params = [Parameter(str(i+1), t, showkey=False) for i, t in enumerate(combo)]
        new_template = Template(new_template_name, params=params)
        wc.insert_before(combo[0], new_template, recursive=False)
        for node in combo:
            wc.remove(node, recursive=False)


def merge_etyl_templates(wc: Wikicode) -> Wikicode:
    """
    Given a chunk of wikicode, finds instances where the deprecated `etyl` template is immediately followed by
    either a word in free text, a linked word, or a generic `mention`/`link`/`langname-mention` template.
    It replaces this pattern with a new `derived-parsed` template -- meaning the same thing as the `derived` template
    but namespaced to differentiate. For cases where the `mention` language is different from the `etyl` language,
    we use the former. The template is removed if we can't parse it effectively.
    """
    etyl_indices = [i for i, node in enumerate(wc.nodes)
                    if isinstance(node, Template) and node.name == "etyl" and i < len(wc.nodes) - 1]

    nodes_to_remove = []
    for i in etyl_indices:
        make_new_template = False
        etyl: Template = wc.nodes[i]
        related_language = etyl.params[0]
        if len(etyl.params) == 1:
            language = "en"
        else:
            language = etyl.params[1]
        node = wc.nodes[i+1]
        if isinstance(node, Text):
            val = re.split(",| |", node.value.strip())[0]
            if val:
                make_new_template = True
        elif isinstance(node, Wikilink):
            val = node.text or node.title
            val = re.split(",| |", val.strip())[0]
            if val:
                make_new_template = True
        elif isinstance(node, Template):
            if node.name in ("m", "mention", "m+", "langname-mention", "l", "link"):
                related_language = node.params[0]
                if len(node.params) > 1:
                    val = node.params[1].value
                    make_new_template = True
                    nodes_to_remove.append(node)

        if make_new_template:
            params = [Parameter(str(i+1), str(param), showkey=False)
                      for i, param in enumerate([language, related_language, val])]
            new_template = Template("derived-parsed", params=params)
            wc.replace(etyl, new_template, recursive=False)
        else:
            nodes_to_remove.append(etyl)

    for node in nodes_to_remove:
        wc.remove(node, recursive=False)
    return wc


def get_comma_combos(wc: Wikicode) -> None:
    """
    Given a chunk of wikicode, finds templates separated by the symbol ",", which indicates morphemes
    related to both each other and the original word. It combines them into a single nested template, `related-parsed`.
    """
    template_indices = [i for i, node in enumerate(wc.nodes) if isinstance(node, Template)]
    text_indices = [i for i, node in enumerate(wc.nodes) if isinstance(node, Text) and str(node).strip() == ","]

    combine_template_chains(wc, new_template_name="related-parsed", template_indices=template_indices,
                            text_indices=text_indices)


def get_plus_combos(wc: Wikicode) -> None:
    """
    Given a chunk of wikicode, finds templates separated by the symbol "+", which indicates multiple
    morphemes that affix to make a single etymological relation. It combines these templates into a single nested
    `affix-parsed` template -- meaning the same thing as the `affix` template, but namespaced to differentiate.
    """
    template_indices = [i for i, node in enumerate(wc.nodes) if isinstance(node, Template)]
    text_indices = [i for i, node in enumerate(wc.nodes) if isinstance(node, Text) and str(node).strip() == "+"]

    combine_template_chains(wc, new_template_name="affix-parsed", template_indices=template_indices,
                            text_indices=text_indices)


def get_from_chains(wc: Wikicode) -> None:
    """
    Given a chunk of wikicode, finds templates separated by either "from" or "<", indicating an ordered chain
    of inheritance. It combines these templates into a single nested `from-parsed` template.
    """
    is_inheritance_str = lambda x: str(x).strip() == "<" or re.sub("[^a-z]+", "", str(x).lower()) == "from"

    template_indices = [i for i, node in enumerate(wc.nodes) if isinstance(node, Template)]
    text_indices = [i for i, node in enumerate(wc.nodes)
                    if isinstance(node, Text) and is_inheritance_str(node)]

    combine_template_chains(wc, new_template_name="from-parsed", template_indices=template_indices,
                            text_indices=text_indices)


def remove_links(wc: Wikicode) -> None:
    """
    Given a chunk of wikicode, replaces all inner links with their text representation
    """
    for link in wc.filter_wikilinks():
        wc.replace(link, link.text)


def inherited(t: Template) -> Generator[List[str], None, None]:
    language = t.params[0]
    related_language = t.params[1]
    if len(t.params) > 2:
        related_word = t.params[2]
    else:
        related_word = None
    yield (language, related_language, related_word)


if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    # download(WIKTIONARY_URL)
    write_all()