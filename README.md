# LLM Inference Engine

A production-inspired LLM inference engine built from scratch in Python, implementing core concepts used in systems like vLLM.

## Architecture

## Components

### 1. API Layer (FastAPI)
- POST `/generate` — accepts prompt, returns generated text
- GET `/health` — queue status
- GET `/metrics` — system observability

### 2. Batch Scheduler
- Continuous batching — collects requests for 50ms before dispatching
- Fills up to batch size of 4 before dispatching
- Non-blocking async design

### 3. KV Cache Manager
- Fixed memory pool of 10 slots
- Allocates slots per request based on token count
- Rejects requests when memory is full
- Frees slots immediately after completion

### 4. Model Execution
- Runs distilgpt2 via HuggingFace Transformers
- Non-blocking execution using asyncio thread executor
- Results returned directly to caller via async events

### 5. Observability
- Tracks uptime, total requests, rejections, batch sizes, tokens processed
- Live cache status

## Key Design Decisions

| Decision | Choice | Reason |
|---|---|---|
| Batching | Continuous | Better throughput than static batching |
| Queue | asyncio.Queue | Zero-dependency, sufficient for single-node |
| Model execution | Thread executor | Prevents blocking the async event loop |
| Result delivery | asyncio.Event | Efficient async wait without polling |

## How to Run

```bash
pip install fastapi uvicorn transformers torch
uvicorn server:app
```

## Example

```bash
curl -X POST http://127.0.0.1:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Once upon a time", "max_tokens": 50}'
```

## What I Learned
- Why continuous batching outperforms static batching
- How KV cache memory management works and why fragmentation matters
- Why prefill and decode phases have different compute profiles
- How vLLM's PagedAttention solves memory fragmentation
                        