import matplotlib.pyplot as plt
import json

# Results
results = {
    "static_batching": {
        "total_time": 14.99,
        "throughput": 0.67,
        "avg_latency": 14.99
    },
    "continuous_batching": {
        "total_time": 14.35,
        "throughput": 0.70,
        "avg_latency": 5.40
    }
}

# Save results
with open("results.json", "w") as f:
    json.dump(results, f, indent=2)

# Plot
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))

modes = ["Static Batching", "Continuous Batching"]
throughputs = [results["static_batching"]["throughput"], results["continuous_batching"]["throughput"]]
latencies = [results["static_batching"]["avg_latency"], results["continuous_batching"]["avg_latency"]]

# Throughput chart
ax1.bar(modes, throughputs, color=["#ff6b6b", "#51cf66"])
ax1.set_title("Throughput (req/sec)")
ax1.set_ylabel("Requests per second")
for i, v in enumerate(throughputs):
    ax1.text(i, v + 0.01, f"{v:.2f}", ha="center", fontweight="bold")

# Latency chart
ax2.bar(modes, latencies, color=["#ff6b6b", "#51cf66"])
ax2.set_title("Avg Latency (seconds)")
ax2.set_ylabel("Seconds")
for i, v in enumerate(latencies):
    ax2.text(i, v + 0.1, f"{v:.2f}s", ha="center", fontweight="bold")

plt.suptitle("Static vs Continuous Batching — distilgpt2 on CPU", fontweight="bold")
plt.tight_layout()
plt.savefig("benchmark_results.png", dpi=150)
print("Chart saved as benchmark_results.png")