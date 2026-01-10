import argparse
import subprocess
import time
import shutil
import pandas as pd

DEFAULT_INPUT_CSV = "filtered_available_scored.csv"
DEFAULT_OUTPUT_CSV = "actually_available.csv"
DEFAULT_TOP_N = 500
DEFAULT_WHOIS_TIMEOUT = 5
DEFAULT_WHOIS_RATE_LIMIT = 1.0
DEFAULT_WHOIS_SERVER = "whois.verisign-grs.com"

def check_whois_available():
    return shutil.which("whois") is not None

def is_unregistered(domain, server, timeout):
    try:
        result = subprocess.check_output(
            ["whois", "-h", server, domain],
            stderr=subprocess.DEVNULL,
            timeout=timeout
        ).decode("utf-8", errors="ignore").lower()

        return "no match for" in result
    except subprocess.TimeoutExpired:
        print(f"[timeout] {domain}")
        return False
    except Exception as e:
        print(f"[error] {domain}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Check WHOIS availability of top N domains")
    parser.add_argument("--input", default=DEFAULT_INPUT_CSV, help="Input CSV with scored domains")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_CSV, help="Output CSV for available domains")
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N, help="Number of top domains to check")
    parser.add_argument("--whois-timeout", type=int, default=DEFAULT_WHOIS_TIMEOUT, help="WHOIS timeout in seconds")
    parser.add_argument("--whois-rate-limit", type=float, default=DEFAULT_WHOIS_RATE_LIMIT, help="Seconds to sleep between WHOIS queries")
    parser.add_argument("--whois-server", default=DEFAULT_WHOIS_SERVER, help="WHOIS server to use")
    args = parser.parse_args()

    if not check_whois_available():
        print("Error: 'whois' command not found. Please install whois package.")
        return

    try:
        df = pd.read_csv(args.input)
    except IOError as e:
        print(f"Error reading input CSV {args.input}: {e}")
        return
    except pd.errors.EmptyDataError:
        print(f"Error: Input file {args.input} is empty or invalid")
        return

    if "domain" not in df.columns or "vibe_score" not in df.columns:
        print("Error: Input CSV must contain 'domain' and 'vibe_score' columns")
        return

    df = df.sort_values(by="vibe_score", ascending=False).head(args.top_n)

    available = []

    print(f"Checking top {args.top_n} domains via WHOIS on {args.whois_server}...")
    for domain in df["domain"]:
        print(f"→ {domain}...", end=" ", flush=True)
        if is_unregistered(domain, args.whois_server, args.whois_timeout):
            print("✅ available")
            available.append(domain)
        else:
            print("❌ registered")

        if args.whois_rate_limit > 0:
            time.sleep(args.whois_rate_limit)

    try:
        pd.DataFrame(available, columns=["domain"]).to_csv(args.output, index=False)
        print(f"\nWriting {len(available)} unregistered domains to {args.output}")
    except IOError as e:
        print(f"Error writing output CSV {args.output}: {e}")

if __name__ == "__main__":
    main()
