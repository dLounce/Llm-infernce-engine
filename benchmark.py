import asyncio
import time
import httpx

async def send_request(client, prompt, max_tokens=50):
    start = time.time()
    response = await client.post(
        "http://127.0.0.1:8000/generate",
        json={"prompt": prompt, "max_tokens": max_tokens},
        timeout=60
    )
    latency = time.time() - start
    return latency

async def run_benchmark(num_requests=10, concurrency=1):
    prompts = [f"Tell me about topic {i}" for i in range(num_requests)]
    
    async with httpx.AsyncClient() as client:
        start = time.time()
        
        # Send requests with given concurrency
        semaphore = asyncio.Semaphore(concurrency)
        
        async def bounded_request(prompt):
            async with semaphore:
                return await send_request(client, prompt)
        
        latencies = await asyncio.gather(*[bounded_request(p) for p in prompts])
        
        total_time = time.time() - start
        rps = num_requests / total_time
        avg_latency = sum(latencies) / len(latencies)
        
        print(f"\n--- Benchmark Results ---")
        print(f"Requests: {num_requests}")
        print(f"Concurrency: {concurrency}")
        print(f"Total time: {total_time:.2f}s")
        print(f"Throughput: {rps:.2f} requests/sec")
        print(f"Avg latency: {avg_latency:.2f}s")
        print(f"Min latency: {min(latencies):.2f}s")
        print(f"Max latency: {max(latencies):.2f}s")

if __name__ == "__main__":
    asyncio.run(run_benchmark(num_requests=10, concurrency=4))