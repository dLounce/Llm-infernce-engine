from locust import HttpUser, task, between

class InferenceUser(HttpUser):
    wait_time = between(1, 3)  # wait 1-3 seconds between requests

    @task(3)
    def generate(self):
        self.client.post("/generate", json={
            "prompt": "Tell me something interesting",
            "max_tokens": 50
        }, timeout=60)

    @task(1)
    def stream(self):
        with self.client.post("/generate/stream", json={
            "prompt": "Once upon a time",
            "max_tokens": 30
        }, stream=True, catch_response=True, timeout=60) as response:
            response.success()

    @task(1)
    def health(self):
        self.client.get("/health")