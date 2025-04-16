import asyncio
import aiodns
import itertools
import string
import os
import random
import socket

# --- Config ---
tld = ".com"
length = 5
resolvers = ["8.8.8.8", "1.1.1.1", "9.9.9.9", "8.8.4.4"]
concurrency = 500
timeout = 1
output_file = "available.txt"
progress_file = "progress.txt"
# ---------------

async def check_domain(domain, resolver):
    try:
        await resolver.gethostbyname(domain, socket.AF_INET)
        return (domain, False)  # Domain exists
    except aiodns.error.DNSError as e:
        # Only NXDOMAIN (code 4) counts as available
        if isinstance(e.args[0], int) and e.args[0] == 4:
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
            raise

async def file_writer(queue, filename):
    print("[file_writer] running")
    with open(filename, "a") as f:
        while True:
            item = await queue.get()
            f.write(item + "\n")
            f.flush()
            queue.task_done()

async def progress_writer(progress_queue):
    print("[progress_writer] running")
    last_saved = None
    while True:
        domain = await progress_queue.get()
        last_saved = domain
        progress_queue.task_done()
        if random.randint(1, 1000) == 1:
            with open(progress_file, "w") as f:
                f.write(last_saved)

async def main():
    domains = asyncio.Queue(maxsize=5000)
    available_queue = asyncio.Queue()
    progress_queue = asyncio.Queue()

    resume_from = None
    if os.path.exists(progress_file):
        with open(progress_file, "r") as f:
            resume_from = f.read().strip()
        print(f"[RESUME] Resuming from {resume_from}")

    resolver_pool = itertools.cycle([
        aiodns.DNSResolver(nameservers=[ip], timeout=timeout, tries=1)
        for ip in resolvers
    ])

    available_writer_task = asyncio.create_task(file_writer(available_queue, output_file))
    progress_writer_task = asyncio.create_task(progress_writer(progress_queue))

    tasks = []
    for _ in range(concurrency):
        task = asyncio.create_task(worker(domains, resolver_pool, available_queue, progress_queue))
        tasks.append(task)

    print(f"Spawned {len(tasks)} worker tasks")

    letters = string.ascii_lowercase
    started = False
    for combo in itertools.product(letters, repeat=length):
        domain = ''.join(combo) + tld
        if resume_from and not started:
            if domain == resume_from:
                print(f"[RESUME] Found resume point: {domain}")
                started = True
            else:
                continue
        await domains.put(domain)
        if domains.qsize() % 1000 == 0:
            print(f"Queued {domains.qsize()} domains")

    await domains.join()
    await available_queue.join()
    await progress_queue.join()

    for task in tasks:
        task.cancel()
    available_writer_task.cancel()
    progress_writer_task.cancel()

if __name__ == "__main__":
    asyncio.run(main())
