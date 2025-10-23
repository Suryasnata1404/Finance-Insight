import os
import json
import random
import re
import nltk
from nltk.corpus import wordnet
from html import unescape
import logging

# ---------------- CONFIG ----------------
INPUT_FILE = "data/processed/merged_dataset.jsonl"
OUTPUT_FILE = "data/processed/augmented_dataset.jsonl"

# Fraction of records to augment (0.0 -> none, 1.0 -> all)
AUGMENT_RATIO = 0.05

# Per-token replacement/delete probabilities (applied only on chosen records)
REPLACE_PROB = 0.10
DELETE_PROB = 0.03

# Optional: set a seed for reproducibility (None for non-deterministic)
RANDOM_SEED = 42

# Setup logging
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

# ---------------- SETUP ----------------
# Download WordNet once if needed
try:
    _ = wordnet.synsets("finance")
except LookupError:
    nltk.download("wordnet")
    nltk.download("omw-1.4")

PROTECTED_FINANCIAL_TOKENS = {
    "₹", "$", "INR", "USD", "EUR", "₹", "%", "percent", "percentage",
    "EBITDA", "EBIT", "P/E", "PE", "EPS", "EPS(TTM)", "BSE", "NSE",
    "NASDAQ", "NYSE", "SENSEX", "NIFTY", "₹crore", "crore", "lakh",
    "million", "billion", "trillion"
    }

# Regex helpers
RE_NUMERIC = re.compile(r"\d")                     # any digit
RE_XML_TAG = re.compile(r"<[^>]+>")                # xml/html tags
RE_TOKEN = re.compile(r"\w+|[^\w\s]", re.UNICODE)  # words or punctuation

# ---------------- HELPERS ----------------
def is_numeric_token(token: str) -> bool:
    """Detect tokens that contain digits or typical numeric symbols."""
    if token is None:
        return False
    token = token.strip()
    # catch dates, numbers, amounts, percentages, hyphenated numbers etc.
    return bool(RE_NUMERIC.search(token)) or token in {"%", "$", "₹", "USD", "INR"}

def clean_html_like(text: str) -> str:
    """
    If text looks like XML/HTML (starts with <?xml or contains many tags),
    return a cleaned version with tags removed and HTML entities unescaped.
    Otherwise return original text.
    """
    if text.strip().lower().startswith("<?xml") or len(RE_XML_TAG.findall(text)) > 0:
        cleaned = RE_XML_TAG.sub(" ", text)        # remove tags
        cleaned = unescape(cleaned)               # unescape HTML entities
        # collapse whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned
    return text

def get_synonym(word: str) -> str:
    """
    Return a random synonym from WordNet if available, otherwise return the original word.
    Filters out numeric-looking synonyms, very short synonyms and multi-word lemmas with punctuation.
    """
    # protect tokens that look financial or numeric
    if word.upper() in (t.upper() for t in PROTECTED_FINANCIAL_TOKENS):
        return word

    syns = set()
    try:
        for syn in wordnet.synsets(word):
            for lemma in syn.lemmas():
                cand = lemma.name().replace("_", " ")
                # filter: avoid numerics, punctuation-only, very short tokens
                if not re.search(r"\d", cand) and re.match(r"^[A-Za-z\- ]+$", cand) and len(cand) >= 3:
                    if cand.lower() != word.lower():
                        syns.add(cand)
    except Exception:
        return word

    if not syns:
        return word
    # prefer single-word synonyms
    single_word_syns = [s for s in syns if " " not in s]
    pool = single_word_syns or list(syns)
    return random.choice(pool)

def tokenize_preserve(text: str):
    """
    Tokenize into a list of tokens while preserving punctuation tokens.
    Returns list of tokens.
    """
    return RE_TOKEN.findall(text)

def detokenize(tokens: list) -> str:
    """
    Rebuild string from tokens without inserting spaces before punctuation.
    Simple heuristic: punctuation tokens (non-word) are attached to previous token.
    """
    out = ""
    for tok in tokens:
        if re.match(r"^[^\w\s]+$", tok):  # punctuation only
            out = out.rstrip() + tok + " "
        else:
            out += tok + " "
    return out.strip()

def augment_text(text: str, replace_prob=REPLACE_PROB, delete_prob=DELETE_PROB) -> str:
    """
    Augment text by synonym replacement and random deletion with protections:
    - Numeric tokens and protected financial tokens are never changed.
    - XML/HTML is cleaned before augmentation (we operate on visible text).
    """
    # Work on cleaned visible text if XML/HTML present
    text_for_aug = clean_html_like(text)

    tokens = tokenize_preserve(text_for_aug)
    augmented = []

    for tok in tokens:
        # Protect numeric and financial tokens
        if is_numeric_token(tok) or tok in PROTECTED_FINANCIAL_TOKENS:
            augmented.append(tok)
            continue

        # do not attempt synonyms for single-char punctuation etc.
        if re.match(r"^[^\w\s]+$", tok):
            augmented.append(tok)
            continue

        # Random deletion
        if random.random() < delete_prob:
            continue

        # Synonym replacement
        if random.random() < replace_prob:
            try:
                new_tok = get_synonym(tok)
            except Exception:
                new_tok = tok
            augmented.append(new_tok)
        else:
            augmented.append(tok)

    return detokenize(augmented)

# ---------------- MAIN ----------------
def run_augmentation(input_path=INPUT_FILE, output_path=OUTPUT_FILE, augment_ratio=AUGMENT_RATIO):
    if not os.path.exists(input_path):
        logging.error(f"Input file not found: {input_path}")
        return

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    total, saved = 0, 0
    skipped_xml = 0
    try:
        with open(input_path, "r", encoding="utf-8") as infile, open(output_path, "w", encoding="utf-8") as outfile:
            for line in infile:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    logging.warning("Skipping invalid JSON record.")
                    continue

                text = record.get("text", "").strip()
                if not text:
                    continue

                total += 1

                # Always write the original record as-is
                outfile.write(json.dumps(record) + "\n")
                saved += 1

                # Decide whether to augment this record
                if augment_ratio <= 0 or random.random() >= augment_ratio:
                    continue

                # If the text is giant (very long), avoid heavy augmentation — do a light pass instead
                if len(text) > 200000:
                    # perform a light augmentation by only doing small synonym swaps on the first 5k chars
                    preview = text[:5000]
                    aug_preview = augment_text(preview, replace_prob=0.05, delete_prob=0.01)
                    aug_text = aug_preview + text[5000:]
                else:
                    aug_text = augment_text(text)

                aug_record = {
                    "text": aug_text,
                    "source_file": record.get("source_file", ""),
                    "augmentation_type": "synonym_replace_delete_controlled"
                }
                outfile.write(json.dumps(aug_record) + "\n")
                saved += 1

    except Exception as e:
        logging.exception(f"Unexpected error during augmentation: {e}")

    logging.info("✅ Augmentation done.")
    logging.info(f"   Original records processed: {total}")
    logging.info(f"   Total saved (original + augmented): {saved}")
    logging.info(f"   Skipped heavy-xml records: {skipped_xml}")
    logging.info(f"   Output → {output_path}")

if __name__ == "__main__":
    run_augmentation()