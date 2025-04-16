import asyncio
import aiodns
import itertools
import string
import os
import random

# --- Config ---
tld = ".com"
length = 5
resolvers = ["8.8.8.8", "1.1.1.1", "9.9.9.9", "8.8.4.4"]
concurrency = 10000
timeout = 1
output_file = "available.txt"
progress_file = "progress.txt"
# ---------------

async def check_domain(domain, resolver):
    try:
        await resolver.gethostbyname(domain, socket.AF_INET)
        return (domain, False)
    except aiodns.error.DNSError:
        return (domain, True)
    except Exception:
        return (domain, False)

async def worker(domains, resolver_pool, available_queue, progress_queue):
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
            print(f"Error checking domain: {e}")

async def file_writer(queue, filename):
    with open(filename, "a") as f:
        while True:
            item = await queue.get()
            f.write(item + "\n")
            f.flush()
            queue.task_done()

async def progress_writer(progress_queue):
    last_saved = None
    while True:
        domain = await progress_queue.get()
        last_saved = domain
        progress_queue.task_done()

        if random.randint(1, 1000) == 1:
            with open(progress_file, "w") as f:
                f.write(last_saved)

async def main():
    domains = asyncio.Queue()
    available_queue = asyncio.Queue()
    progress_queue = asyncio.Queue()

    resume_from = None
    if os.path.exists(progress_file):
        with open(progress_file, "r") as f:
            resume_from = f.read().strip()
        print(f"Resuming from {resume_from}")

    letters = string.ascii_lowercase
    started = False
    for combo in itertools.product(letters, repeat=length):
        domain = ''.join(combo) + tld
        if resume_from and not started:
            if domain == resume_from:
                started = True
            else:
                continue
        await domains.put(domain)

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

    await domains.join()
    await available_queue.join()
    await progress_queue.join()

    for task in tasks:
        task.cancel()
    available_writer_task.cancel()
    progress_writer_task.cancel()

if __name__ == "__main__":
    asyncio.run(main())
