import subprocess
import pandas as pd
import time

INPUT_CSV = "filtered_available_scored.csv"
OUTPUT_CSV = "actually_available.csv"
TOP_N = 500
WHOIS_TIMEOUT = 5  # seconds

def is_unregistered(domain):
    try:
        result = subprocess.check_output(
            ["whois", "-h", "whois.verisign-grs.com", domain],
            stderr=subprocess.DEVNULL,
            timeout=WHOIS_TIMEOUT
        ).decode("utf-8", errors="ignore").lower()

        return "no match for" in result
    except subprocess.TimeoutExpired:
        print(f"[timeout] {domain}")
        return False
    except Exception as e:
        print(f"[error] {domain}: {e}")
        return False

def main():
    df = pd.read_csv(INPUT_CSV)
    df = df.sort_values(by="vibe_score", ascending=False).head(TOP_N)

    available = []

    print(f"Checking top {TOP_N} domains via WHOIS...")
    for domain in df["domain"]:
        print(f"→ {domain}...", end=" ", flush=True)
        if is_unregistered(domain):
            print("✅ available")
            available.append(domain)
        else:
            print("❌ registered")

        time.sleep(1.0)  # rate limiting

    print(f"\nWriting {len(available)} unregistered domains to {OUTPUT_CSV}")
    pd.DataFrame(available, columns=["domain"]).to_csv(OUTPUT_CSV, index=False)

if __name__ == "__main__":
    main()
