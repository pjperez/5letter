from sentence_transformers import SentenceTransformer, util
import numpy as np
import os
import psutil
import csv
import time

# --- Config ---
input_file = "filtered_available.txt"
output_file = "vibe_checked_and_ranked.txt"
csv_output_file = "vibe_checked_and_ranked.csv"

model_name = 'all-MiniLM-L6-v2'
bad_similarity_threshold = 0.7
good_similarity_threshold = 0.4
max_memory_usage_fraction = 0.5
# ----------------

bad_concepts = [
    # Insert full expanded bad word list here
]

good_concepts = [
    "smart", "bright", "happy", "brilliant", "creative", "fresh", "innovative", "energy", "growth", "trust",
    "strong", "bold", "agile", "friendly", "sunshine", "clean", "sharp", "future", "modern", "vision",
    "flow", "glow", "upbeat", "fast", "smooth", "shine", "pure", "hope", "dream", "success"
]

def load_domains(filename):
    with open(filename, "r") as f:
        return [line.strip() for line in f if line.strip()]

def estimate_initial_batch_size():
    mem = psutil.virtual_memory()
    total_gb = mem.total / (1024**3)
    print(f"Detected {total_gb:.2f} GB RAM.")
    approx_batch = int((total_gb * 1024) / 0.5 * max_memory_usage_fraction)
    return max(16, min(approx_batch, 256))

def memory_safe_batch_size(batch_size):
    mem = psutil.virtual_memory()
    used_fraction = mem.used / mem.total
    if used_fraction > max_memory_usage_fraction:
        batch_size = max(16, batch_size // 2)
        print(f"[WARN] High memory usage detected ({used_fraction:.2f}), reducing batch size to {batch_size}")
    return batch_size

def sort_output_file(filename):
    print(f"Sorting output file {filename} by score...")
    with open(filename, "r") as f:
        lines = f.readlines()

    scored_domains = []
    for line in lines:
        parts = line.strip().split()
        if len(parts) == 2:
            domain, score = parts
            scored_domains.append((domain, float(score)))

    scored_domains.sort(key=lambda x: x[1], reverse=True)

    with open(filename, "w") as f:
        for domain, score in scored_domains:
            f.write(f"{domain} {score:.4f}\n")

    print(f"Sorting complete.")
    return scored_domains

def save_as_csv(scored_domains, csv_filename):
    print(f"Saving CSV version to {csv_filename}...")
    with open(csv_filename, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Domain", "Score"])
        for domain, score in scored_domains:
            writer.writerow([domain, f"{score:.4f}"])
    print("CSV saved.")

def main():
    print("Loading model...")
    model = SentenceTransformer(model_name)

    print(f"Loading domains from {input_file}...")
    domains = load_domains(input_file)
    print(f"Loaded {len(domains)} domains.")

    batch_size = estimate_initial_batch_size()
    print(f"Starting batch size: {batch_size}")

    print("Embedding bad and good concepts...")
    bad_embeddings = model.encode(bad_concepts, normalize_embeddings=True)
    good_embeddings = model.encode(good_concepts, normalize_embeddings=True)

    good_domains = []

    print("Checking and scoring domains...")
    i = 0
    total = len(domains)
    while i < total:
        batch = domains[i:i+batch_size]
        names_only = [d.replace(".com", "") for d in batch]
        try:
            embeddings = model.encode(names_only, normalize_embeddings=True)
        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                batch_size = max(16, batch_size // 2)
                print(f"[ERROR] OOM detected, reducing batch size to {batch_size}")
                time.sleep(1)
                continue
            else:
                raise

        for domain, embedding in zip(batch, embeddings):
            bad_similarities = util.cos_sim(embedding, bad_embeddings)
            max_bad_similarity = np.max(bad_similarities.numpy())

            if max_bad_similarity > bad_similarity_threshold:
                print(f"Rejected: {domain} (bad vibe)")
                continue

            good_similarities = util.cos_sim(embedding, good_embeddings)
            max_good_similarity = np.max(good_similarities.numpy())

            score = float(max_good_similarity)
            good_domains.append((domain, score))

        i += batch_size
        batch_size = memory_safe_batch_size(batch_size)

    with open(output_file, "w") as f:
        for domain, score in good_domains:
            f.write(f"{domain} {score:.4f}\n")

    print(f"Done. Kept {len(good_domains)} good domains.")
    print(f"Saved scored list to {output_file}.")

    # Final sort and CSV save
    sorted_domains = sort_output_file(output_file)
    save_as_csv(sorted_domains, csv_output_file)

if __name__ == "__main__":
    main()