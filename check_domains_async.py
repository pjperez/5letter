import asyncio
import aiodns
import itertools
import string
import os
import random
import socket
import argparse
import shutil
from domain_utils import is_pronounceable

DEFAULT_TLD = ".com"
DEFAULT_LENGTH = 5
DEFAULT_RESOLVERS = ["8.8.8.8", "1.1.1.1", "9.9.9.9", "8.8.4.4"]
DEFAULT_CONCURRENCY = 500
DEFAULT_TIMEOUT = 1
DEFAULT_OUTPUT_FILE = "available.txt"
DEFAULT_PROGRESS_FILE = "progress.txt"
DEFAULT_DOMAIN_QUEUE_SIZE = 5000
DEFAULT_RESUME_SKIP_THRESHOLD = 100

NXDOMAIN_CODE = 4

async def check_domain(domain, resolver):
    try:
        await resolver.gethostbyname(domain, socket.AF_INET)
        return (domain, False)
    except aiodns.error.DNSError as e:
        if len(e.args) > 0 and isinstance(e.args[0], int) and e.args[0] == NXDOMAIN_CODE:
            return (domain, True)
        return (domain, False)
    except Exception:
        return (domain, False)

async def worker(domains, resolver_pool, available_queue, progress_queue):
    print("[worker] started")
    while True:
        try:
            domain = await domains.get()
            resolver = next(resolver_pool)
            result = await check_domain(domain, resolver)
            if result[1]:
                print(f"AVAILABLE: {result[0]}")
                await available_queue.put(result[0])
            await progress_queue.put(domain)
            domains.task_done()
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[worker error] {e}")

async def file_writer(queue, filename, append_mode):
    print(f"[file_writer] running to {filename}")
    mode = "a" if append_mode else "w"
    with open(filename, mode) as f:
        while True:
            item = await queue.get()
            f.write(item + "\n")
            f.flush()
            queue.task_done()

async def progress_writer(progress_queue, progress_file, resume_threshold):
    print("[progress_writer] running")
    last_saved = None
    counter = 0
    while True:
        domain = await progress_queue.get()
        last_saved = domain
        counter += 1
        progress_queue.task_done()
        if counter % resume_threshold == 0:
            with open(progress_file, "w") as f:
                f.write(last_saved)

async def main():
    parser = argparse.ArgumentParser(description="Check domain availability")
    parser.add_argument("--tld", default=DEFAULT_TLD, help="Top-level domain (default: .com)")
    parser.add_argument("--length", type=int, default=DEFAULT_LENGTH, help="Domain name length (default: 5)")
    parser.add_argument("--resolvers", nargs="+", default=DEFAULT_RESOLVERS, help="DNS resolvers")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY, help="Number of concurrent workers")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="DNS query timeout in seconds")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_FILE, help="Output file for available domains")
    parser.add_argument("--progress", default=DEFAULT_PROGRESS_FILE, help="Progress file for resuming")
    parser.add_argument("--append", action="store_true", help="Append to output file instead of overwriting")
    parser.add_argument("--no-resume", action="store_true", help="Ignore progress file and start fresh")
    parser.add_argument("--resume-skip-threshold", type=int, default=DEFAULT_RESUME_SKIP_THRESHOLD, help="Save progress every N domains")
    args = parser.parse_args()

    domains = asyncio.Queue(maxsize=DEFAULT_DOMAIN_QUEUE_SIZE)
    available_queue = asyncio.Queue()
    progress_queue = asyncio.Queue()

    resume_from = None
    if not args.no_resume and os.path.exists(args.progress):
        try:
            with open(args.progress, "r") as f:
                resume_from = f.read().strip()
            print(f"[RESUME] Resuming from {resume_from}")
        except IOError as e:
            print(f"[WARNING] Could not read progress file: {e}")

    resolver_pool = itertools.cycle([
        aiodns.DNSResolver(nameservers=[ip], timeout=args.timeout, tries=1)
        for ip in args.resolvers
    ])

    available_writer_task = asyncio.create_task(file_writer(available_queue, args.output, args.append))
    progress_writer_task = asyncio.create_task(progress_writer(progress_queue, args.progress, args.resume_skip_threshold))

    tasks = []
    for _ in range(args.concurrency):
        task = asyncio.create_task(worker(domains, resolver_pool, available_queue, progress_queue))
        tasks.append(task)

    print(f"Spawned {len(tasks)} worker tasks")

    letters = string.ascii_lowercase
    started = False
    filtered_count = 0
    skipped_count = 0
    queued_count = 0
    for combo in itertools.product(letters, repeat=args.length):
        domain = ''.join(combo) + args.tld

        if resume_from and not started:
            if domain == resume_from:
                print(f"[RESUME] Found resume point: {domain}")
                started = True
            else:
                skipped_count += 1
                continue

        if not is_pronounceable(domain, args.tld):
            filtered_count += 1
            continue

        await domains.put(domain)
        queued_count += 1
        if queued_count % 1000 == 0:
            print(f"Queued {queued_count} domains")

    await domains.join()
    await available_queue.join()
    await progress_queue.join()

    print(f"Filtered out {filtered_count} domains due to pronounceability rules")
    print(f"Skipped {skipped_count} domains during resume")

    for task in tasks:
        task.cancel()
    available_writer_task.cancel()
    progress_writer_task.cancel()

    await asyncio.gather(*tasks, available_writer_task, progress_writer_task, return_exceptions=True)

    print("Cleaning up progress file...")
    try:
        os.remove(args.progress)
    except IOError as e:
        print(f"[WARNING] Could not remove progress file: {e}")

if __name__ == "__main__":
    asyncio.run(main())
