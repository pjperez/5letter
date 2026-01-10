import argparse
from domain_utils import is_pronounceable

DEFAULT_TLD = ".com"
DEFAULT_INPUT_FILE = "available.txt"
DEFAULT_OUTPUT_FILE = "filtered_available.txt"

def main():
    parser = argparse.ArgumentParser(description="Filter domains by pronounceability")
    parser.add_argument("--input", default=DEFAULT_INPUT_FILE, help="Input file with domains")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_FILE, help="Output file for filtered domains")
    parser.add_argument("--tld", default=DEFAULT_TLD, help="Top-level domain (default: .com)")
    args = parser.parse_args()

    try:
        with open(args.input, "r") as infile:
            domains = [line.strip() for line in infile if line.strip()]
    except IOError as e:
        print(f"Error reading input file {args.input}: {e}")
        return

    total = len(domains)
    kept = 0

    try:
        with open(args.output, "w") as outfile:
            for domain in domains:
                if is_pronounceable(domain, args.tld):
                    outfile.write(domain + "\n")
                    kept += 1
    except IOError as e:
        print(f"Error writing output file {args.output}: {e}")
        return

    print(f"Processed {total} domains.")
    print(f"Kept {kept} pronounceable domains.")
    print(f"Filtered results written to: {args.output}")

if __name__ == "__main__":
    main()
