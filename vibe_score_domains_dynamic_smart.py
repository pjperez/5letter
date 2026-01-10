from sentence_transformers import SentenceTransformer, util
import sys
import os
import psutil
import csv
import argparse

BAD_CONCEPTS = [
    "racist", "gross", "disease", "toxic", "ugly", "hate", "violence", "boring",
    "cringe", "annoying", "stupid", "offensive", "corporate", "soulless"
]

GOOD_CONCEPTS = [
    "creative", "fun", "clean", "fast", "modern", "friendly", "cool", "vibe",
    "brilliant", "playful", "fresh", "powerful", "aesthetic", "catchy", "original"
]

DEFAULT_MODEL = "all-MiniLM-L6-v2"
DEFAULT_MIN_RAM_GB_BATCHS = {
    0: 64,
    1: 64,
    2: 128,
    4: 256,
}

def estimate_batch_size(model, num_domains):
    ram_bytes = psutil.virtual_memory().available
    ram_gb = ram_bytes / (1024 ** 3)
    print(f"Detected {ram_gb:.2f} GB RAM.")

    for threshold, batch_size in sorted(DEFAULT_MIN_RAM_GB_BATCHS.items()):
        if ram_gb < threshold:
            return batch_size

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
    parser = argparse.ArgumentParser(description="Score domains by 'vibe' using sentence embeddings")
    parser.add_argument("input", help="Input file with domains")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Sentence transformer model to use")
    parser.add_argument("--output-txt", help="Output TXT file path (auto-generated if not specified)")
    parser.add_argument("--output-csv", help="Output CSV file path (auto-generated if not specified)")
    args = parser.parse_args()

    try:
        input_path = args.input
        base_name = os.path.splitext(os.path.basename(input_path))[0]

        if args.output_txt:
            txt_output = args.output_txt
        else:
            txt_output = f"{base_name}_scored.txt"

        if args.output_csv:
            csv_output = args.output_csv
        else:
            csv_output = f"{base_name}_scored.csv"

        print("Loading model...")
        model = SentenceTransformer(args.model)

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

            bad_similarities = util.cos_sim(embeddings, bad_embeddings)
            bad_scores = bad_similarities.max(dim=1).values

            good_similarities = util.cos_sim(embeddings, good_embeddings)
            good_scores = good_similarities.max(dim=1).values

            vibe_scores = good_scores - bad_scores

            for domain, score in zip(batch, vibe_scores):
                scored.append((domain, score.item()))

        print(f"Writing results to {txt_output} and {csv_output}...")
        write_outputs(scored, txt_output, csv_output)
        print("Done.")

    except IOError as e:
        print(f"Error reading/writing files: {e}")
        return
    except Exception as e:
        print(f"Error: {e}")
        return

if __name__ == "__main__":
    main()
