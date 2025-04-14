import re

input_file = "available.txt"
output_file = "filtered_available.txt"

def is_pronounceable(domain):
    name = domain.replace(".com", "")

    if re.search(r"[bcdfghjklmnpqrstvwxyz]{3}", name):
        return False
    if re.search(r"[aeiou]{3}", name):
        return False
    if not re.search(r"[aeiou]", name):
        return False
    if not re.match(r"[bcdfghjklmnpqrstvwxyz][aeiou]", name):
        return False

    return True

def main():
    total = 0
    kept = 0

    with open(input_file, "r") as infile, open(output_file, "w") as outfile:
        for line in infile:
            domain = line.strip()
            if domain:
                total += 1
                if is_pronounceable(domain):
                    outfile.write(domain + "\n")
                    kept += 1

    print(f"Processed {total} domains.")
    print(f"Kept {kept} pronounceable domains.")
    print(f"Filtered results written to: {output_file}")

if __name__ == "__main__":
    main()