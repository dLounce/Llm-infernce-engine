from fastapi import FastAPI
from pydantic import BaseModel
import asyncio
from transformers import pipeline
# Load model once at startup
generator = pipeline("text-generation", model="distilgpt2")

app = FastAPI()

# Request schemapip3 install transformers torch
class InferenceRequest(BaseModel):
    prompt: str
    max_tokens: int = 256
    priority: int = 1

# In-memory queue
request_queue = asyncio.Queue()

# KV Cache Manager
class KVCacheManager:
    def __init__(self, total_slots=10):
        self.total_slots = total_slots
        self.free_slots = list(range(total_slots))  # [0,1,2,...,9]
        self.allocated = {}  # request_id -> list of slots

    def allocate(self, request_id, num_slots):
        if len(self.free_slots) < num_slots:
            return False  # Out of memory
        self.allocated[request_id] = [self.free_slots.pop() for _ in range(num_slots)]
        print(f"Allocated slots {self.allocated[request_id]} to request {request_id}")
        return True

    def free(self, request_id):
        if request_id in self.allocated:
            self.free_slots.extend(self.allocated.pop(request_id))
            print(f"Freed slots for request {request_id}. Free slots: {len(self.free_slots)}")

    def status(self):
        return {"total": self.total_slots, "free": len(self.free_slots), "allocated": len(self.allocated)}

kv_cache = KVCacheManager(total_slots=10)

# Metrics
from collections import deque
import time

class Metrics:
    def __init__(self):
        self.total_requests = 0
        self.total_batches = 0
        self.total_tokens = 0
        self.rejected_requests = 0
        self.batch_sizes = deque(maxlen=100)  # last 100 batches
        self.start_time = time.time()

    def record_request(self, tokens):
        self.total_requests += 1
        self.total_tokens += tokens

    def record_batch(self, size):
        self.total_batches += 1
        self.batch_sizes.append(size)

    def record_rejection(self):
        self.rejected_requests += 1

    def summary(self):
        uptime = time.time() - self.start_time
        avg_batch = sum(self.batch_sizes) / len(self.batch_sizes) if self.batch_sizes else 0
        return {
            "uptime_seconds": round(uptime, 2),
            "total_requests": self.total_requests,
            "rejected_requests": self.rejected_requests,
            "total_batches": self.total_batches,
            "avg_batch_size": round(avg_batch, 2),
            "total_tokens_processed": self.total_tokens,
            "cache_status": kv_cache.status()
        }

metrics = Metrics()
# Result store
result_store = {}
result_events = {}
async def batch_scheduler():
    batch = []
    batch_size = 4
    wait_time = 0.05

    while True:
        try:
            request = await asyncio.wait_for(request_queue.get(), timeout=wait_time)
            batch.append(request)

            while len(batch) < batch_size:
                try:
                    request = await asyncio.wait_for(request_queue.get(), timeout=0.01)
                    batch.append(request)
                except asyncio.TimeoutError:
                    break

            print(f"Dispatching batch of {len(batch)} requests")
            asyncio.create_task(mock_model_execute(batch))
            metrics.record_batch(len(batch))
            batch = []

        except asyncio.TimeoutError:
            continue
async def mock_model_execute(batch):
    loop = asyncio.get_event_loop()
    prompts = [r.prompt for _, r in batch]
    results = await loop.run_in_executor(
        None,
        lambda: generator(prompts, max_new_tokens=50, do_sample=True)
    )
    for i, (request_id, request) in enumerate(batch):
        generated_text = results[i][0]["generated_text"]
        print(f"Generated: {generated_text}")
        result_store[request_id] = generated_text
        if request_id in result_events:
            result_events[request_id].set()
        kv_cache.free(request_id)
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(batch_scheduler())
@app.post("/generate")
async def generate(request: InferenceRequest):
    request_id = id(request)
    slots_needed = request.max_tokens // 64
    slots_needed = max(1, slots_needed)

    if not kv_cache.allocate(request_id, slots_needed):
        metrics.record_rejection()
        return {"status": "rejected", "reason": "out of memory"}

    event = asyncio.Event()
    result_events[request_id] = event

    await request_queue.put((request_id, request))
    metrics.record_request(request.max_tokens)

    # Wait for result
    await event.wait()
    text = result_store.pop(request_id)
    result_events.pop(request_id)

    return {"status": "completed", "generated_text": text}

@app.get("/health")
async def health():
    return {"status": "ok", "queue_size": request_queue.qsize()}

@app.get("/metrics")
async def get_metrics():
    return metrics.summary()

from fastapi.responses import StreamingResponse

@app.post("/generate/stream")
async def generate_stream(request: InferenceRequest):
    request_id = id(request)
    slots_needed = max(1, request.max_tokens // 64)

    if not kv_cache.allocate(request_id, slots_needed):
        metrics.record_rejection()
        return {"status": "rejected", "reason": "out of memory"}

    async def token_generator():
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: generator(request.prompt, max_new_tokens=request.max_tokens, do_sample=True)
        )
        full_text = result[0]["generated_text"]
        for word in full_text.split():
            yield word + " "
            await asyncio.sleep(0.05)
        kv_cache.free(request_id)
        metrics.record_request(request.max_tokens)

    return StreamingResponse(token_generator(), media_type="text/plain")