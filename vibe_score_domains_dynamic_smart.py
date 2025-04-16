from sentence_transformers import SentenceTransformer, util
import torch
import sys
import os
import psutil
import csv

BAD_CONCEPTS = [
    "racist", "gross", "disease", "toxic", "ugly", "hate", "violence", "boring",
    "cringe", "annoying", "stupid", "offensive", "corporate", "soulless"
]

GOOD_CONCEPTS = [
    "creative", "fun", "clean", "fast", "modern", "friendly", "cool", "vibe",
    "brilliant", "playful", "fresh", "powerful", "aesthetic", "catchy", "original"
]

def estimate_batch_size(model, num_domains):
    ram_bytes = psutil.virtual_memory().available
    ram_gb = ram_bytes / (1024 ** 3)
    print(f"Detected {ram_gb:.2f} GB RAM.")
    if ram_gb < 1:
        return 64
    elif ram_gb < 2:
        return 128
    elif ram_gb < 4:
        return 256
    else:
        return min(1024, num_domains)

def load_domains(path):
    with open(path, "r") as f:
        return [line.strip() for line in f if line.strip()]

def write_outputs(scored, txt_path, csv_path):
    scored.sort(key=lambda x: x[1], reverse=True)
    with open(txt_path, "w") as f_txt, open(csv_path, "w", newline="") as f_csv:
        writer = csv.writer(f_csv)
        writer.writerow(["domain", "vibe_score"])
        for domain, score in scored:
            f_txt.write(f"{domain}\n")
            writer.writerow([domain, f"{score:.4f}"])

def main():
    if len(sys.argv) != 2:
        print("Usage: python vibe_score_domains_dynamic_smart.py filtered_available.txt")
        sys.exit(1)

    input_path = sys.argv[1]
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    txt_output = f"{base_name}_scored.txt"
    csv_output = f"{base_name}_scored.csv"

    print("Loading model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    print(f"Loading domains from {input_path}...")
    domains = load_domains(input_path)
    print(f"Loaded {len(domains)} domains.")

    batch_size = estimate_batch_size(model, len(domains))
    print(f"Starting batch size: {batch_size}")

    print("Embedding bad and good concepts...")
    bad_embeddings = model.encode(BAD_CONCEPTS, convert_to_tensor=True, normalize_embeddings=True)
    good_embeddings = model.encode(GOOD_CONCEPTS, convert_to_tensor=True, normalize_embeddings=True)

    print("Checking and scoring domains...")
    scored = []

    for i in range(0, len(domains), batch_size):
        batch = domains[i:i + batch_size]
        embeddings = model.encode(batch, convert_to_tensor=True, normalize_embeddings=True)

        for j, embedding in enumerate(embeddings):
            if len(bad_embeddings) > 0:
                bad_similarities = util.cos_sim(embedding, bad_embeddings)
                bad_score = bad_similarities.max().item()
            else:
                bad_score = 0.0

            if len(good_embeddings) > 0:
                good_similarities = util.cos_sim(embedding, good_embeddings)
                good_score = good_similarities.max().item()
            else:
                good_score = 0.0

            vibe_score = good_score - bad_score
            scored.append((batch[j], vibe_score))

    print(f"Writing results to {txt_output} and {csv_output}...")
    write_outputs(scored, txt_output, csv_output)
    print("Done.")

if __name__ == "__main__":
    main()
