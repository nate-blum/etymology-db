import csv
import uuid, base64
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional, Tuple, Dict

LANG_CODE_PATH = Path.cwd().joinpath("wiktionary_codes.csv")

@dataclass(frozen=True)
class Etymology:
    lang: str
    term: str
    reltype: str
    related_lang: Optional[str]
    related_term: Optional[str]
    definition_num: int
    position: int = 0
    group_tag: str = None
    parent_tag: str = None
    parent_position: int = None

    @classmethod
    def with_parent(cls, child: "Etymology", parent: "Etymology", position: int = 0):
        return cls(lang=child.lang, term=child.term, reltype=child.reltype, related_lang=child.related_lang,
                   related_term=child.related_term, definition_num=child.definition_num, position=child.position, group_tag=child.group_tag,
                   parent_tag=parent.group_tag, parent_position=position)

    @property
    def related_lang_full(self):
        return lang_dict().get(self.related_lang, self.related_lang)

    def is_valid(self) -> bool:
        # May include more conditions in the future
        return self.related_term not in ("", "-")

    def to_row(self) -> Tuple[str, str, str, str, Optional[str], Optional[str], Optional[str], int, Optional[str],
                              Optional[str], Optional[int]]:
        return (self.lang, self.term, self.reltype, self.related_lang_full, 
               self.related_term, self.definition_num, self.position, self.group_tag, self.parent_tag, self.parent_position)
    
    @staticmethod
    def generate_root_tag() -> str:
        uuid_id = uuid.uuid4()
        return base64.urlsafe_b64encode(uuid_id.bytes).decode("ascii").rstrip("=")

    @staticmethod
    def header() -> Tuple[str, ...]:
        return ("lang", "term", "reltype", "related_lang",
             "related_term", "definition_num", "position", "group_tag", "parent_tag", "parent_position")

@lru_cache(maxsize=1)
def lang_dict() -> Dict[str, str]:
    with open(LANG_CODE_PATH, 'r') as f_in:
        reader = csv.reader(f_in)
        next(reader)
        return {row[0]: row[1] for row in reader}
