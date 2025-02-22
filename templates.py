import logging
from multiprocessing import Manager
from enum import Enum
from typing import Callable, List

from mwparserfromhell.nodes.template import Template

from elements import Etymology

# unparsed_templates = Manager().dict()

class RelType(Enum):
    Inherited = "inherited_from"
    Derived = "derived_from"
    Borrowed = "borrowed_from"
    LearnedBorrowing = "learned_borrowing_from"
    SemiLearnedBorrowing = "semi_learned_borrowing_from"
    OrthographicBorrowing = "orthographic_borrowing_from"
    UnadaptedBorrowing = "unadapted_borrowing_from"
    Root = "has_root"
    Affix = "has_affix"
    Prefix = "has_prefix"
    PrefixRoot = "has_prefix_with_root"
    Suffix = "has_suffix"
    SuffixRoot = "has_prefix_with_root"
    Confix = "has_confix"
    Compound = "compound_of"
    Blend = "blend_of"
    Abbreviation = "abbreviation_of"
    Initialism = "initialism_of"
    Clipping = "clipping_of"
    BackForm = "back-formation_from"
    Doublet = "doublet_with"
    Onomatopoeia = "is_onomatopoeic"
    Calque = "calque_of"
    SemanticLoan = "semantic_loan_of"
    NamedAfter = "named_after"
    PhonoSemanticMatching = "phono-semantic_matching_of"
    Mention = "etymologically_related_to"
    Cognate = "cognate_of"
    GroupAffix = "group_affix_root"
    GroupMention = "group_related_root"
    GroupDerived = "group_derived_root"


def parse_template(template_name: str, term: str, lang: str, template: Template, i: int) -> List[Etymology]:
    parser_func = get_template_parser(template_name.strip())
    if not parser_func:
        # counter = unparsed_templates.get(template_name, 0)
        # unparsed_templates[template_name] = counter + 1
        # logging.debug(f"Unrecognized template name `{template_name}` (term: {term}, lang: {lang})")
        return []
    try:
        result = parser_func(term, lang, template, i)
    except Exception:
        logging.warning(f"Error while parsing:\nTerm: {term}\nLanguage: {lang}\n"
                      f"Wikicode: {template}\n", exc_info=True)
        return []
    return [result] if isinstance(result, Etymology) else result


def get_template_parser(template_name: str) -> Callable[[str, str, Template, int], Etymology]:
    default_func = lambda x, y, z, a: []
    parse_dict = {
        "inherited": inherited,
        "inh": inherited,
        "derived": derived,
        "der": derived,
        "borrowed": borrowed,
        "bor": borrowed,
        "learned borrowing": learned_borrowing,
        "learned_borrowing": learned_borrowing,
        "lbor": learned_borrowing,
        "orthographic borrowing": orthographic_borrowing,
        "obor": orthographic_borrowing,
        "slbor": semi_learned_borrowing,
        "unadapted borrowing": unadapted_borrowing,
        "ubor": unadapted_borrowing,
        "PIE root": pie_root,
        "root": root,
        "affix": affix,
        "af": affix,
        "prefix": prefix,
        "pre": prefix,
        "confix": confix,
        "suffix": suffix,
        "suf": suffix,
        "compound": compound,
        "com": compound,
        "blend": blend,
        "clipping": clipping,
        "clipping of": clipping,
        "back_form": back_form,
        "back-form": back_form,
        "back-formation": back_form,
        "doublet": doublet,
        "onomatopoeic": onomatopoeic,
        "onom": onomatopoeic,
        "calque": calque,
        "cal": calque,
        "semantic loan": semantic_loan,
        "named-after": named_after,
        "phono-semantifc matching": phono_semantic_matching,
        "psm": phono_semantic_matching,
        "mention": mention,
        "m": mention,
        "cognate": cognate,
        "cog": cognate,
        "noncognate": non_cognate,
        "noncog": non_cognate,
        "ncog": non_cognate,
        "langname-mention": mention,
        "m+": mention,
        "link": mention,
        "l": mention,
        "derived-parsed": derived_parsed,
        "affix-parsed": affix_parsed,
        "from-parsed": from_parsed,
        "related-parsed": related_parsed,
        "abbreviation of": abbreviation,
        "initialism of": initialism,
        # Templates not related to etymology
        # Wikipedia link
        "w": default_func,
        "wikipedia": default_func,
        # Derived category, shortens chains that exist elsewhere
        "dercat": default_func,
        # Unrelated metadata
        "rel-top": default_func,
        "rel-bottom": default_func,
        "small": default_func,
        "section link": default_func,
        "CE": default_func,
        "C.E.": default_func,
        "B.C.E.": default_func,
        "gloss": default_func,
        "glossary": default_func,
        # Unknown/low-information
        "unk": default_func,
        "unknown": default_func,
        "etystub": default_func,
        "nonlemma": default_func,
        "rfe": default_func,
        "IPAchar": default_func,
        "ja-l": default_func,
        "ja-r": default_func,
        "ja-kanjitab": default_func,
        # Qualifiers/extras to ignore for now
        "sense": default_func,
        "senseid": default_func,
        "senseid-close": default_func,
        "defdate": default_func,
        "qualifier": default_func,
        "nb...": default_func,
        "rfv-etym": default_func,
        "inflection of": default_func
    }
    return parse_dict.get(template_name)


def derived(term: str, lang: str, template: Template, i: int):
    """
    This template is a "catch-all" that is used when neither {{inherited}} nor {{borrowed}} is applicable.

    Params: (lang, source lang, source word)
    """
    p = [param for param in template.params if not param.showkey]
    if len(p) < 3:
        return []
    return Etymology(
        term=term,
        lang=lang,
        reltype=RelType.Derived.value,
        related_lang=str(p[1]),
        related_term=str(p[2]),
        definition_num=i
    )


def borrowed(term: str, lang: str, template: Template, i: int):
    """
    This template is for loanwords that were borrowed during the time the borrowing language was spoken.

    Params: (lang, source lang, source word)
    """
    p = [param for param in template.params if not param.showkey]
    if len(p) < 3:
        return []
    return Etymology(
        term=term,
        lang=lang,
        reltype=RelType.Borrowed.value,
        related_lang=str(p[1]),
        related_term=str(p[2]),
        definition_num=i
    )


def learned_borrowing(term: str, lang: str, template: Template, i: int):
    """
    This template is intended specifically for learned borrowings, those that were intentionally taken into a language
    from another not through normal means of language contact.

    Params: (lang, source lang, source word)
    """
    p = [param for param in template.params if not param.showkey]
    if len(p) < 3:
        return []
    return Etymology(
        term=term,
        lang=lang,
        reltype=RelType.LearnedBorrowing.value,
        related_lang=str(p[1]),
        related_term=str(p[2]),
        definition_num=i
    )


def semi_learned_borrowing(term: str, lang: str, template: Template, i: int):
    """
    This template is intended specifically for semi-learned borrowings,
    which are borrowings that have been partly reshaped by later sound change or analogy with inherited terms

    Params: (lang, source lang, source word)
    """
    p = [param for param in template.params if not param.showkey]
    if len(p) < 3:
        return []
    return Etymology(
        term=term,
        lang=lang,
        reltype=RelType.SemiLearnedBorrowing.value,
        related_lang=str(p[1]),
        related_term=str(p[2]),
        definition_num=i
    )


def unadapted_borrowing(term: str, lang: str, template: Template, i: int):
    """
    This template is intended for loanwords that have not been conformed to the morpho-syntactic,
    phonological and/or phonotactical rules of the target language.

    Params: (lang, source lang, source word)
    """
    p = [param for param in template.params if not param.showkey]
    if len(p) < 3:
        return []
    return Etymology(
        term=term,
        lang=lang,
        reltype=RelType.UnadaptedBorrowing.value,
        related_lang=str(p[1]),
        related_term=str(p[2]),
        definition_num=i
    )


def orthographic_borrowing(term: str, lang: str, template: Template, i: int):
    """
    This template is intended specifically for loans from language A into language B, which are loaned only in its
    script form and not pronunciation and often become new words which are phonetically quite dissimilar.

    Params: (lang, source lang, source word)
    """
    p = [param for param in template.params if not param.showkey]
    if len(p) < 3:
        return []
    return Etymology(
        term=term,
        lang=lang,
        reltype=RelType.OrthographicBorrowing.value,
        related_lang=str(p[1]),
        related_term=str(p[2]),
        definition_num=i
    )


def inherited(term: str, lang: str, template: Template, i: int):
    """
    This template is intended for terms that have an unbroken chain of inheritance from the source term in question.

    Params: (lang, source lang, source word)
    """
    p = [param for param in template.params if not param.showkey]
    if len(p) < 3:
        return []
    return Etymology(
        term=term,
        lang=lang,
        reltype=RelType.Inherited.value,
        related_lang=str(p[1]),
        related_term=str(p[2]),
        definition_num=i
    )


def root(term: str, lang: str, template: Template, i: int):
    """
    Root language derivation, a generalization of the deprecated pie root

    Params: (lang, PIE root 1, PIE root n...)
    """
    p = [param for param in template.params if not param.showkey]
    etys = []
    for j, root in enumerate(p[2:]):
        etys.append(
            Etymology(
                term=term,
                lang=lang,
                reltype=RelType.Root.value,
                related_lang=str(p[1]),
                related_term=str(root),
                position=j,
                definition_num=i
            ))
    return etys


def pie_root(term: str, lang: str, template: Template, i: int):
    """
    This template adds entries to a subcategory of Category:Terms derived from Proto-Indo-European roots.

    Params: (lang, PIE root 1, PIE root n...)
    """
    p = [param for param in template.params if not param.showkey]
    etys = []
    for j, root in enumerate(p[1:]):
        etys.append(
            Etymology(
                term=term,
                lang=lang,
                reltype=RelType.Root.value,
                related_lang="ine-pro",
                related_term=str(root),
                position=j,
                definition_num=i
            ))
    return etys


def affix(term: str, lang: str, template: Template, i: int):
    """
    This template shows the parts (morphemes) that make up a word.

    Params: (lang, word part 1, word part n....)
    """
    p = [param for param in template.params if not param.showkey]
    etys = []
    for j, root in enumerate(p[1:]):
        etys.append(
            Etymology(
                term=term,
                lang=lang,
                reltype=RelType.Affix.value,
                related_lang=str(p[0]),
                related_term=str(root),
                position=j,
                definition_num=i
            ))
    return etys


def prefix(term: str, lang: str, template: Template, i: int):
    """
    This template shows the parts (morphemes) that make up a word.

    Params: (lang, prefix, root)
    """
    p = [param for param in template.params if not param.showkey]
    pre = Etymology(
        term=term,
        lang=lang,
        reltype=RelType.Prefix.value,
        related_lang=str(p[0]),
        related_term=str(p[1]),
        definition_num=i
    )
    if len(p) > 2 and str(p[2]):
        root = Etymology(
            term=term,
            lang=lang,
            reltype=RelType.PrefixRoot.value,
            related_lang=str(p[0]),
            related_term=str(p[2]),
            definition_num=i
        )
        return [pre, root]
    else:
        return pre


def confix(term: str, lang: str, template: Template, i: int):
    """
    For use in the Etymology sections of words which consist of only a prefix and a suffix, or which were formed by
    simultaneous application of a prefix and a suffix to some other element(s).

    Params: (lang, prefix, confix root 1, confix root n..., suffix)
    """
    p = [param for param in template.params if not param.showkey]
    etys = []
    etys.append(
        Etymology(
            term=term,
            lang=lang,
            reltype=RelType.Confix.value,
            related_lang=str(p[0]),
            related_term=str(p[1]),
            position=0,
            definition_num=i
        ))

    for j, root in enumerate(p[2:-1]):
        etys.append(
            Etymology(
                term=term,
                lang=lang,
                reltype=RelType.Confix.value,
                related_lang=str(p[0]),
                related_term=str(root),
                position=j+1,
                definition_num=i
            ))

    etys.append(
        Etymology(
            term=term,
            lang=lang,
            reltype=RelType.Confix.value,
            related_lang=str(p[0]),
            related_term=str(p[-1]),
            position=len(p)-2,
            definition_num=i
        ))
    return etys


def suffix(term: str, lang: str, template: Template, i: int):
    """
    This template shows the parts (morphemes) that make up a word.

    Params: (lang, root, suffix)
    """
    p = [param for param in template.params if not param.showkey]
    if len(str(p)) < 3:
        return []
    suf = Etymology(
        term=term,
        lang=lang,
        reltype=RelType.Suffix.value,
        related_lang=str(p[0]),
        related_term=str(p[2]),
        definition_num=i
    )
    root = Etymology(
        term=term,
        lang=lang,
        reltype=RelType.SuffixRoot.value,
        related_lang=str(p[0]),
        related_term=str(p[1]),
        definition_num=i
    )
    return [root, suf]


def compound(term: str, lang: str, template: Template, i: int):
    """
    This template is used in the etymology section to display etymologies for compound words: words that are made up of
    multiple parts.

    Params: (source lang, word part 1, word part n...)
    """
    p = [param for param in template.params if not param.showkey]
    etys = []
    for j, root in enumerate(p[1:]):
        etys.append(
            Etymology(
                term=term,
                lang=lang,
                reltype=RelType.Compound.value,
                related_lang=str(p[0]),
                related_term=str(root),
                position=j,
                definition_num=i
            ))
    return etys


def blend(term: str, lang: str, template: Template, i: int):
    """
    A word or name that combines two words, typically starting with the start of one word and ending with the end of
    another, such as smog (from smoke and fog) or Wiktionary (from wiki and dictionary). Many blends are portmanteaus.

    Params: (lang, word part 1, word part n...)
    """
    p = [param for param in template.params if not param.showkey]
    etys = []
    for j, root in enumerate(p[1:]):
        etys.append(
            Etymology(
                term=term,
                lang=lang,
                reltype=RelType.Blend.value,
                related_lang=str(p[0]),
                related_term=str(root),
                position=j,
                definition_num=i
            ))
    return etys


def clipping(term: str, lang: str, template: Template, i: int):
    """
    A shortening of a word, without changing meaning or part of speech.

    Params: (lang, source word)
    """
    p = [param for param in template.params if not param.showkey]
    if len(p) < 2:
        return []
    return Etymology(
        term=term,
        lang=lang,
        reltype=RelType.Clipping.value,
        related_lang=str(p[0]),
        related_term=str(p[1]),
        definition_num=i
    )


def abbreviation(term: str, lang: str, template: Template, i: int):
    """
    Abbreviations of another word. Differs from clipping in that
    abbreviations are based on written shortenings instead of spoken ones.

    Params: (lang, source word)
    """
    p = [param for param in template.params if not param.showkey]
    if len(p) < 2:
        return []
    return Etymology(
        term=term,
        lang=lang,
        reltype=RelType.Abbreviation.value,
        related_lang=str(p[0]),
        related_term=str(p[1]),
        definition_num=i
    )


def initialism(term: str, lang: str, template: Template, i: int):
    """
    Initialisms of another word/phrase

    Params: (lang, source word)
    """
    p = [param for param in template.params if not param.showkey]
    if len(p) < 2:
        return []
    return Etymology(
        term=term,
        lang=lang,
        reltype=RelType.Initialism.value,
        related_lang=str(p[0]),
        related_term=str(p[1]),
        definition_num=i
    )


def back_form(term: str, lang: str, template: Template, i: int):
    """
    A term formed by removing an apparent or real prefix or suffix from an older term; for example, the noun pea arose
    because the final /z/ sound in pease sounded like a plural suffix. Similarly, the verb edit is a back-formation from
    the earlier noun editor. Not to be confused with clipping, which just shortens a word without changing meaning or
    part of speech.

    Params: (lang, source word)
    """
    p = [param for param in template.params if not param.showkey]
    if len(p) < 2:
        return []
    return Etymology(
        term=term,
        lang=lang,
        reltype=RelType.BackForm.value,
        related_lang=str(p[0]),
        related_term=str(p[1]),
        definition_num=i
    )


def doublet(term: str, lang: str, template: Template, i: int):
    """
    In etymology, two or more words in the same language are called doublets or etymological twins or twinlings
    (or possibly triplets, and so forth) when they have different phonological forms but the same etymological root.

    Params: (lang, word part 1, word part n...)
    """
    p = [param for param in template.params if not param.showkey]
    etys = []
    for j, doub in enumerate(p[1:]):
        etys.append(
            Etymology(
                term=term,
                lang=lang,
                reltype=RelType.Doublet.value,
                related_lang=str(p[0]),
                related_term=str(doub),
                position=j,
                definition_num=i
            ))
    return etys


def onomatopoeic(term: str, lang: str, template: Template, i: int):
    """
    This templates indicates that a word is an onomatopoeia.

    Params: (lang)
    """
    p = [param for param in template.params if not param.showkey]
    return Etymology(
        term=term,
        lang=lang,
        reltype=RelType.Onomatopoeia.value,
        related_lang=str(p[0]),
        related_term=term,
        definition_num=i
    )


def calque(term: str, lang: str, template: Template, i: int):
    """
    In linguistics, a calque or loan translation is a word or phrase borrowed from another language by literal,
    word-for-word or root-for-root translation.

    Params: (lang, source lang, source word)
    """
    p = [param for param in template.params if not param.showkey]
    if len(p) < 3:
        return []
    return Etymology(
        term=term,
        lang=lang,
        reltype=RelType.Calque.value,
        related_lang=str(p[1]),
        related_term=str(p[2]),
        definition_num=i
    )


def semantic_loan(term: str, lang: str, template: Template, i: int):
    """
    Semantic borrowing is a special case of calque or loan-translation, in which the word in the borrowing
    language already existed and simply had a new meaning added to it.

    Params: (lang, source lang, source word)
    """
    p = [param for param in template.params if not param.showkey]
    if len(p) < 3:
        return []
    return Etymology(
        term=term,
        lang=lang,
        reltype=RelType.SemanticLoan.value,
        related_lang=str(p[1]),
        related_term=str(p[2]),
        definition_num=i
    )


def named_after(term: str, lang: str, template: Template, i: int):
    """
    Use this template in an etymology section of eponyms.

    Params: (lang, person's name)
    """
    p = [param for param in template.params if not param.showkey]
    if len(p) < 2:
        return []
    return Etymology(
        term=term,
        lang=lang,
        reltype=RelType.NamedAfter.value,
        related_lang=str(p[0]),
        related_term=str(p[1]),
        definition_num=i
    )


def phono_semantic_matching(term: str, lang: str, template: Template, i: int):
    """
    Phono-semantic matching (PSM) is the incorporation of a word into one language from another, often creating
    a neologism, where the word's non-native quality is hidden by replacing it with phonetically and semantically
    similar words or roots from the adopting language. Thus, the approximate sound and meaning of the original
    expression in the source language are preserved, though the new expression (the PSM) in the target language may
    sound native.

    Params: (lang, source lang, source word)
    """
    p = [param for param in template.params if not param.showkey]
    if len(p) < 3:
        return []
    return Etymology(
        term=term,
        lang=lang,
        reltype=RelType.PhonoSemanticMatching.value,
        related_lang=str(p[1]),
        related_term=str(p[2]),
        definition_num=i
    )


def mention(term: str, lang: str, template: Template, i: int):
    """
    Use this template when a particular term is mentioned within running English text.

    Params: (source lang, source word)
    """
    p = [param for param in template.params if not param.showkey]
    if len(p) < 2:
        return []
    return Etymology(
        term=term,
        lang=lang,
        reltype=RelType.Mention.value,
        related_lang=str(p[0]),
        related_term=str(p[1]),
        definition_num=i
    )


def cognate(term: str, lang: str, template: Template, i: int):
    """
    This template is used to indicate cognacy with terms in other languages that are not ancestors of the given term
    (hence none of {{inherited}}, {{borrowed}}, and {{derived}} are applicable).
    There is no consensus whether its use for etymologically related but borrowed terms is appropriate.

    Params: (source lang, source word)
    """
    p = [param for param in template.params if not param.showkey]
    if len(p) < 2:
        return []
    return Etymology(
        term=term,
        lang=lang,
        reltype=RelType.Cognate.value,
        related_lang=str(p[0]),
        related_term=str(p[1]),
        definition_num=i
    )


def non_cognate(term: str, lang: str, template: Template, i: int):
    """
    This template is used to format terms in other languages that are mentioned in etymology sections
    but are not cognate with the page's term.

    Params: (source lang, source word)
    """
    p = [param for param in template.params if not param.showkey]
    if len(p) < 2:
        return []
    return Etymology(
        term=term,
        lang=lang,
        reltype=RelType.Mention.value,
        related_lang=str(p[0]),
        related_term=str(p[1]),
        definition_num=i
    )


def derived_parsed(term: str, lang: str, template: Template, i: int):
    """
    Same as derived, but a custom solution that automatically parses etyl templates in which the word is located
    outside of the template.

    Params: (lang, source lang, source word)
    """
    p = [param for param in template.params if not param.showkey]
    return Etymology(
        term=term,
        lang=lang,
        reltype=RelType.Derived.value,
        related_lang=str(p[1]),
        related_term=str(p[2]),
        definition_num=i
    )


def unnest_template(term: str, lang: str, template: Template, reltype: RelType, i: int):
    """
    Builds etymologies out of nested templates, assigning the immediate parent to a given child
    in cases of deeply nested templates.
    """
    parent_index = 0
    parent_ety = Etymology(
        term=term,
        lang=lang,
        reltype=reltype.value,
        related_lang=None,
        related_term=None,
        definition_num=i
    )
    etys = [parent_ety]
    for p in template.params:
        for child_template in p.value.filter_templates(recursive=False):
            child_etys = parse_template(str(child_template.name), term, lang, child_template, i)
            for child_ety in child_etys:
                if child_ety.parent_tag:
                    # This means the template was at least doubly nested and a parent has already been assigned
                    # further up the stack
                    etys.append(child_ety)
                else:
                    parented_ety = Etymology.with_parent(child=child_ety, parent=parent_ety, position=parent_index)
                    etys.append(parented_ety)
            parent_index += 1
    return etys


def affix_parsed(term: str, lang: str, template: Template, i: int):
    """
    Same as affix, but a custom solution that parses plain text to find strings of "+" - separated terms.

    Child templates are extracted and linked hierarchically.
    Params: (Template 1, template n...)
    """
    return unnest_template(term=term, lang=lang, template=template, reltype=RelType.GroupAffix, i=i)


def from_parsed(term: str, lang: str, template: Template, i: int):
    """
    Custom solution that finds chains of derivation.

    Child templates are extracted and linked hierarchically.
    Params: (Template 1, template n...)
    """
    return unnest_template(term=term, lang=lang, template=template, reltype=RelType.GroupDerived, i=i)


def related_parsed(term: str, lang: str, template: Template, i: int):
    """
    Custom solution to find morphemes related to both each other and the original word.

    Child templates are extracted and linked hierarchically.
    Params: (Template 1, template n...)
    """
    return unnest_template(term=term, lang=lang, template=template, reltype=RelType.GroupMention, i=i)

