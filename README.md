# 5-Letter Domain Finder and Vibe Checker

This project helps you find available 5-letter `.com` domains, filter them for pronounceability, and rank them by "positive vibe" using deep semantic vector analysis.

It is designed to be **fast**, **scalable**, **resilient**, and **fully automatable**.

Please note domains not resolving may still be unavailable.

---

## Project Structure

| File | Purpose |
|:---|:---|
| `check_domains_async.py` | Asynchronously scan for available 5-letter domains using DNS lookups with thousands of parallel tasks. Saves progress to allow resuming. |
| `filter_domains.py` | Simple linguistic filter: keeps domains that are pronounceable based on consonant/vowel patterns (e.g., no 3 consonants or vowels in a row). |
| `vibe_score_domains_dynamic_smart.py` | Vibe check domains using vector embeddings. Dynamically adjusts batch size based on available system memory. Scores good domains and outputs both `.txt` and `.csv` formats. |

---

## Technical Workflow

### 1. **Find Available Domains (`check_domains_async.py`)**

- Generates **all 5-letter** combinations (`a` to `z`) for `.com` domains.
- **Asynchronous DNS lookup** using `aiodns` for high speed (up to 10,000 concurrent checks).
- **Round-robin resolvers** (Google, Cloudflare, Quad9) prevent overloading one DNS server.
- **Timeouts** are short (1 second) for efficiency.
- **Progress tracking**: Saves the last domain checked every ~1000 checks to `progress.txt` so you can **resume** if interrupted.
- **Result**: Writes **only available domains** to `available.txt`.

### 2. **Filter Pronounceable Domains (`filter_domains.py`)**

- Applies simple linguistic rules to domain names:
  - Rejects domains with **3+ consonants** in a row.
  - Rejects domains with **3+ vowels** in a row.
  - Requires at least **one vowel**.
  - Preferably starts **consonant + vowel**.
- **Result**: Outputs a cleaner list into `filtered_available.txt`, removing ugly/awkward names.

### 3. **Vibe Check and Score Domains (`vibe_score_domains_dynamic_smart.py`)**

- **Vectorizes** each domain name using `sentence-transformers` (`MiniLM-L6-v2` model).
- Compares embeddings against:
  - A **bad word list** (e.g., "fail", "lame", "ugly", etc.) — domains close to bad concepts are rejected.
  - A **good word list** (e.g., "smart", "happy", "clean", etc.) — domains close to good concepts are scored higher.
- **Dynamic batching** based on:
  - **RAM detection**: starts with a large batch if lots of memory available.
  - **Live adjustment**: reduces batch size if memory usage exceeds 50% or if an out-of-memory error occurs.
- **Sorting**: After vibe check, domains are sorted from **highest** to **lowest** positive vibe score.
- **Outputs**:
  - `vibe_checked_and_ranked.txt` — text file, domain + score
  - `vibe_checked_and_ranked.csv` — CSV file, ready for Excel/Sheets.

---

## Requirements

Install dependencies first:

```bash
pip install aiodns sentence-transformers psutil
```

(If you want, you can add `aiofiles` and `asyncio` for further optimization, but not strictly required.)

---

## How to Run

1. **Find Available Domains**:

```bash
python check_domains_async.py
```

- Will output: `available.txt`

2. **Filter Pronounceable Domains**:

```bash
python filter_domains.py
```

- Will output: `filtered_available.txt`

3. **Vibe Check and Score Domains**:

```bash
python vibe_score_domains_dynamic_smart.py
```

- Will output:
  - `vibe_checked_and_ranked.txt` (text)
  - `vibe_checked_and_ranked.csv` (csv)

---

## Example Outputs

(These domains are made up)

**TXT Output** (best domains first):

```
navio.com 0.7335
monla.com 0.7218
brilo.com 0.7092
...
```

**CSV Output** (Excel/Sheets ready):

| Domain | Score |
|:---|:---|
| navio.com | 0.7335 |
| monla.com | 0.7218 |
| brilo.com | 0.7092 |

---

## Design Principles

- **Concurrency**: Uses asyncio and thousands of tasks to scan DNS very quickly.
- **Fault Tolerance**: Auto-resume scanning if interrupted (no rechecking from scratch).
- **Scalability**: Dynamic memory usage adapts automatically to small or large machines.
- **Semantics**: Real vector similarity instead of basic substring matching — truly checks "vibe" and branding quality.
- **Separation of Stages**: Each script handles a clean step (find → filter → vibe score), making debugging and re-running easier.

---

**Happy hunting for your 5-letter golden domain!**
