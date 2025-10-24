# scripts/prepare_ner_dataset_final.py
import os
import json
import random
import logging
from typing import List, Dict, Any
from sklearn.model_selection import train_test_split
from collections import Counter

# pip install datasets
from datasets import DatasetDict, Dataset

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
RANDOM_SEED = 42
random.seed(RANDOM_SEED)

# ---------- CONFIG ----------
INPUT_FILE = "data/processed/bio_annotation_ready.jsonl"
OUTPUT_DIR = "data/processed/ner_final_splits"
TEST_SIZE = 0.2  # fraction for temp (val+test)
VAL_FRACTION_OF_TEMP = 0.5  # split temp into val/test equally

# Final ENTITY SCHEMA (update to match your annotated labels)
ENTITY_LABELS = [
    "ORG", "DATE", "FIN_VALUE", "REVENUE", "PROFIT", "FIN_TERM", "EVENT"
]

# Derived BIO tags
def create_label_maps(entity_labels: List[str]) -> Dict[str, int]:
    all_tags = ["O"]
    for tag in entity_labels:
        all_tags.append(f"B-{tag}")
        all_tags.append(f"I-{tag}")
    return {tag: i for i, tag in enumerate(all_tags)}

LABEL2ID = create_label_maps(ENTITY_LABELS)
ID2LABEL = {v: k for k, v in LABEL2ID.items()}

# ---------- UTIL ----------
def clean_record(record: Dict[str, Any]) -> Dict[str, Any] or None:
    """
    Validate token/label alignment, remove empty tokens, map labels to IDs.
    Returns {"tokens": [...], "ner_tags": [...], "has_entity": bool}
    """
    tokens = record.get("tokens", [])
    labels = record.get("labels", [])

    if not tokens or not labels or len(tokens) != len(labels):
        logging.warning("Skipping record due to token/label count mismatch.")
        return None

    new_tokens, new_labels = [], []
    for t, l in zip(tokens, labels):
        if not isinstance(t, str):
            continue
        tok = t.strip()
        lab = l.strip() if isinstance(l, str) else "O"
        if tok == "":
            continue
        new_tokens.append(tok)
        # normalize label: if label not in LABEL2ID, map to "O"
        if lab not in LABEL2ID:
            lab = "O"
        new_labels.append(lab)

    if not new_tokens:
        return None

    ner_tags = [LABEL2ID.get(l, 0) for l in new_labels]
    has_entity = any(l != "O" for l in new_labels)
    return {"tokens": new_tokens, "ner_tags": ner_tags, "has_entity": has_entity}

def load_and_clean(input_path: str):
    cleaned = []
    label_counter = Counter()
    total = 0
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                logging.warning("Skipping malformed JSON line.")
                continue
            cr = clean_record(rec)
            if cr:
                cleaned.append(cr)
                # count labels
                for idx in cr["ner_tags"]:
                    label_counter[ID2LABEL.get(idx, "O")] += 1
    logging.info(f"Loaded {total} raw records -> {len(cleaned)} cleaned records.")
    return cleaned, label_counter

def save_jsonl(records: List[Dict[str, Any]], path: str):
    with open(path, "w", encoding="utf-8") as outf:
        for r in records:
            json.dump(r, outf)
            outf.write("\n")

# ---------- MAIN ----------
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    logging.info("Loading and cleaning data...")
    cleaned_records, label_counter = load_and_clean(INPUT_FILE)

    logging.info("Label distribution (tag:count):")
    for tag, cnt in label_counter.most_common():
        logging.info(f"  {tag}: {cnt}")

    total = len(cleaned_records)
    if total == 0:
        logging.error("No cleaned records found. Aborting.")
        return

    # Quick check: proportion with entities
    with_entities = sum(1 for r in cleaned_records if r["has_entity"])
    logging.info(f"Records with >=1 entity: {with_entities} / {total} ({with_entities/total:.2%})")
    if with_entities / total < 0.01:
        logging.warning("Very few records contain entities (<1%). You should annotate more examples before training.")

    # Convert to minimal HF-friendly records: {"tokens": [...], "ner_tags": [...]}
    hf_records = [{"tokens": r["tokens"], "ner_tags": r["ner_tags"]} for r in cleaned_records]

    # Split: train / temp
    train, temp = train_test_split(hf_records, test_size=TEST_SIZE, random_state=RANDOM_SEED)
    val, test = train_test_split(temp, test_size=VAL_FRACTION_OF_TEMP, random_state=RANDOM_SEED)

    logging.info(f"Splits sizes -> train: {len(train)}, val: {len(val)}, test: {len(test)}")

    # Save JSONL splits for easy inspection & backup
    save_jsonl(train, os.path.join(OUTPUT_DIR, "train.jsonl"))
    save_jsonl(val, os.path.join(OUTPUT_DIR, "validation.jsonl"))
    save_jsonl(test, os.path.join(OUTPUT_DIR, "test.jsonl"))
    logging.info("Saved JSONL splits.")

    # Convert to HuggingFace DatasetDict and save_to_disk
    dataset_splits = DatasetDict({
        "train": Dataset.from_list(train),
        "validation": Dataset.from_list(val),
        "test": Dataset.from_list(test)
    })
    dataset_splits.save_to_disk(OUTPUT_DIR)
    logging.info(f"Saved DatasetDict to {OUTPUT_DIR}")

    # Save metadata
    metadata = {"id2label": ID2LABEL, "label2id": LABEL2ID, "entity_labels": ENTITY_LABELS}
    with open(os.path.join(OUTPUT_DIR, "metadata.json"), "w", encoding="utf-8") as mf:
        json.dump(metadata, mf, indent=2)

    logging.info("✅ Final NER dataset ready for training.")
    logging.info("Next: tokenization + alignment step with the model tokenizer (we can produce code for that too).")

if __name__ == "__main__":
    main()
