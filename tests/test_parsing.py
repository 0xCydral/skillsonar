from skillsonar.index import parse_frontmatter, split_frontmatter, stem, tokenize


def test_plain_fields():
    text = "---\nname: pdf-tool\ndescription: Fill forms.\n---\n# Body\n"
    assert parse_frontmatter(text) == {"name": "pdf-tool", "description": "Fill forms."}


def test_quoted_values_lose_their_quotes():
    text = '---\nname: "quoted"\ndescription: \'single\'\n---\n'
    assert parse_frontmatter(text) == {"name": "quoted", "description": "single"}


def test_literal_block_scalar():
    text = "---\nname: a\ndescription: |\n  first line\n  second line\nother: x\n---\n"
    assert parse_frontmatter(text)["description"] == "first line second line"


def test_folded_block_scalar_stops_at_next_key():
    text = "---\ndescription: >-\n  folded text\n  continues\nname: after\n---\n"
    fields = parse_frontmatter(text)
    assert fields["description"] == "folded text continues"
    assert fields["name"] == "after"


def test_indented_key_is_not_top_level():
    text = "---\nname: real\nmetadata:\n  name: nested\n---\n"
    assert parse_frontmatter(text)["name"] == "real"


def test_when_to_use_is_read():
    text = "---\nname: a\nwhen_to_use: After an outage.\n---\n"
    assert parse_frontmatter(text)["when_to_use"] == "After an outage."


def test_crlf_line_endings():
    text = "---\r\nname: win\r\ndescription: |\r\n  windows file\r\n---\r\nbody"
    assert parse_frontmatter(text) == {"name": "win", "description": "windows file"}


def test_no_frontmatter_is_all_body():
    assert split_frontmatter("# Just a heading") == ("", "# Just a heading")
    assert parse_frontmatter("# Just a heading") == {}


def test_stem_is_consistent_on_both_sides():
    assert stem("restarting") == stem("restarts") == stem("restart")
    assert stem("indexes") == stem("indexed")
    assert stem("pod") == "pod"


def test_stem_leaves_short_words_alone():
    assert stem("bus") == "bus"
    assert stem("uses") == "uses"


def test_tokenize_drops_stopwords_and_short_tokens():
    assert tokenize("the pod is up") == {"pod"}


def test_tokenize_splits_camel_case():
    assert tokenize("CrashLoopBackOff") == {"crash", "loop", "back", "off"}


def test_contractions_do_not_become_rare_tokens():
    # "doesn't" used to split into "doesn", a rare token that matched any skill saying "doesn't".
    assert tokenize("it doesn't work") == {"work"}
    assert tokenize("it doesn\u2019t work") == {"work"}
