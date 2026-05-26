import yaml
import json
import pandas as pd
from pathlib import Path
from helper_functions import normalize_method

# ---------------------------
# Supercategory mapping
# Keys must exactly match top-level mapping keys below
# ---------------------------
supercategory_mapping = {
    "Morphology":     ["Derivation", "Inflection", "Word formation", "TAME"],
    "Morphosyntax":   ["Agreement", "Ergativity"],
    "Syntax":         ["Determiners", "Pronouns", "Argument Structure", "Adjuncts",
                       "Word order", "Passive", "Negation", "Ellipsis",
                       "Coordination", "Relative Clauses", "control&raising",
                       "Movement", "Island Effects", "Filler-Gap", "Topicalization",
                       "Comparison", "Classifiers", "Interrogatives",
                       "Copula", "Particles", "Coverbs", "Complex clauses"],
    "Syn-Sem Interface": ["NPIs", "Quantifiers"],
    "Semantics":      ["Binding"],
}


# ---------------------------
# Extract YAML frontmatter
# ---------------------------
def extract_frontmatter(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    out = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        out.append(line)
    return "\n".join(out)


# ---------------------------
# Citation builder
# ---------------------------
def make_cite(entry, filename=None):
    sc = entry.get("short_cite", "")
    if sc and sc.strip():
        return sc.strip()
    authors = entry.get("authors")
    year = entry.get("year")
    if isinstance(authors, list) and authors:
        last_names = [a.split(",")[0].strip() for a in authors]
        author_part = last_names[0] if len(last_names) == 1 else last_names[0] + " et al.,"
        return f"{author_part} ({year})" if year else author_part
    print(f"[WARNING] No valid citation info in: {filename}")
    return filename if filename else "Unknown"


# ---------------------------
# Phenomenon mapping
# Agreement is a nested dict — Case and DOM live inside it
# as sub-categories, so they collapse into the Agreement column.
# All other top-level keys are flat lists.
# ---------------------------
mapping = {
    "Agreement": {
        "DP-internal agreement": [
            "adjective-noun-aggrement",
            "adjective-noun-aggrement-possessive",
            "adjective-noun-agreement",
            "determiner-noun-agreement",
            "noun-adj-agreement",
            "attributive-agreement",
            "possessive-noun-agreement",
        ],
        "Subject-predicate agreement": [
            "subject-auxillary-agreement",
            "subject-predicate-agreement",
            # removed: subject-predicate-adjective-classifier-agreement
            # (lives in Classifiers — classifier phenomena take priority)
            "subject-verb-agreement",
            "predicate-agreement",

        ],
        "Object agreement": [
            "object-verb agreement",
            "indirect-object-auxillary-agreement",
            "Differential Object Marking"
        ],
        "Aspect-participle agreement": [
            "aspect-agreement",
            "Past participle agreements",
            "passive-participle-agreement",
            "unaccusative-participle-agreement",
            "predicative-attribute-agreement",
            "predicative-complement-agreement",
        ],
        "General-complex agreement": [
            "verb-agreement",
            "verbal-agreement",
            "person-number-agreement",
            "case-agreement",
            "noun-phrase-agreement",
            "nouns-cases", "subject-case", "dative-object"
        ],
        # Case and DOM intentionally nested here → collapse into Agreement column
    },

    "Derivation":      ["derivation", "morphology-derivation", "adjective-nominalization", "nominalization"],
    "Inflection":      ["morphology-number", "morphology-person", "numbers",
                        "word internal negation", "word-inflection",
                        "morphology-negation", "morphology-inflection"],
    "TAME":            ["verbal-conjugation", "morphology-tense", "aspect", "wug-test-past", "tense"],
    "Word formation":  ["noun compounds", "word-formation", "word-formatio", "compounding"],

    "Determiners":     ["determiners", "definiteness-effect"],
    "Pronouns":        ["pronouns"],
    "Classifiers":     ["classifier", "classifier-noun-agreement",
                        "subject-predicate-adjective-classifier-agreement"],  # owns this string

    "Ergativity":      ["ergativity", "split-ergativity-verb-prediction"],

    "Word order":      ["word-order", "scrambling", "order-of-adjectives", "order-of-adverbs",
                        "clause-structure&word-order", "NP-head-finality"],

    "Argument Structure": ["argument-structure"],
    "Adjuncts":        ["oblique", "adverbs&modifiers", "connectors (adverbial clause)", "verb-complement"],
    "Passive":         ["passive"],
    "Copula":          ["copula"],
    "Negation":        ["Standard negation", "negation"],

    "Comparison":      ["comparison", "adjectives-comparison"],
    "Interrogatives":  ["alternative-question", "question", "Question"],

    "Ellipsis":        ["Ellipsis", "gapping", "ellipsis"],
    "Coordination":    ["coordination"],
    "Relative Clauses": [
        "center-embedding (relative clause?)", "relative-clauses",
        "relative_clause-attachment", "participal-relatives",
        "center-embedding",           # deduplicated — was listed twice
    ],
    "Complex clauses": ["embedded-clauses"],
    "control&raising": ["control&raising", "control"],
    "Movement":        ["wh-fronting", "wh-movement"],
    "Island Effects":  ["island", "islands", "Addition island", "Island qu-", "SN island", "Subject island"],
    "Filler-Gap":      ["Filler-Gap", "filler-gap"],
    "Topicalization":  ["topicalization"],

    "Particles":       ["ba"],
    "Coverbs":         ["coverb"],
    "Quantifiers":     ["quantifiers"],
    "NPIs":            ["polarity-items", "NPI licensing", "NPI"],
    "Binding":         ["anaphor", "anaphor-agreement-gender", "anaphor-agreement-number",
                        "anaphoric-reference", "reflexives"],
}


# ---------------------------
# Build phen → category index
# Handles both flat lists and nested dicts (Agreement)
# ---------------------------
def build_phen_index(mapping):
    index = {}
    for cat, items in mapping.items():
        if isinstance(items, dict):
            # nested: iterate over sub-category lists
            for sub_items in items.values():
                for p in sub_items:
                    index[p] = cat   # all sub-phenomena map to the top-level category
        else:
            for p in items:
                index[p] = cat
    return index

phen_to_category = build_phen_index(mapping)


# ---------------------------
# Sanity check: every mapping key must appear in exactly one supercategory
# ---------------------------
all_super_cats = {cat for cats in supercategory_mapping.values() for cat in cats}
mapping_keys = set(mapping.keys())
orphaned = mapping_keys - all_super_cats
extra   = all_super_cats - mapping_keys
if orphaned:
    print(f"[WARNING] mapping keys not in any supercategory: {orphaned}")
if extra:
    print(f"[WARNING] supercategory references keys not in mapping: {extra}")


# ---------------------------
# Load files
# ---------------------------
folder = Path("/Users/argy/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian Vault/Projects/Survey/Survey")

records = []
categories = list(mapping.keys())

for file in sorted(folder.glob("*.md")):
    text = file.read_text()
    yml = extract_frontmatter(text)

    if not yml:
        print(f"SKIPPED (no frontmatter): {file.name}")
        continue

    try:
        entry = yaml.safe_load(yml)
    except Exception as e:
        print(f"YAML ERROR in {file.name}: {e}")
        continue

    citation    = make_cite(entry, filename=file.name)
    phenomena   = entry.get("phenomena", [])
    year        = entry.get("year")
    method      = normalize_method(entry.get("method"))
    languages   = entry.get("languages", [])
    eval_types  = normalize_method(entry.get("eval-type", []))
    num_examples = entry.get("example_number")

    row = {"Citation": citation}
    row.update({
        "Year":          year,
        "Method":        method,
        "Languages":     languages,
        "EvalType":      eval_types,
        "NumExamples":   num_examples,
        "IsMultilingual": len(languages) > 1,
    })
    for cat in categories:
        row[cat] = ""

    for ph in phenomena:
        cat = phen_to_category.get(ph)
        if cat:
            row[cat] = "check"
        # uncomment to debug unmatched phenomena:
        # else:
        #     print(f"[UNMATCHED] '{ph}' in {file.name}")

    records.append(row)


# ---------------------------
# Build and export
# ---------------------------
df = pd.DataFrame(records).set_index("Citation").sort_index()
print(df)
df.to_csv("/Users/argy/workspace/language-evaluationphenomena_table.csv")

# Export supercategory order as sidecar for the LaTeX formatter
with open("supercategory_mapping.json", "w") as f:
    json.dump(supercategory_mapping, f, indent=2)

print("\nWrote phenomena_table.csv and supercategory_mapping.json")