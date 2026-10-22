from locust import LoadTestShape


class StepLoadShape(LoadTestShape):
    """
    Step-up traffic ramp to simulate real-world traffic spikes and scaling behavior:
      - Stage 1 (Warmup): ramp to 30 users
      - Stage 2 (Medium load): ramp to 100 users
      - Stage 3 (Peak load): ramp to 250 users
      - Stage 4 (Sustained peak): maintain 250 users
    """
    stages = [
        {"duration": 20, "users": 30, "spawn_rate": 10},
        {"duration": 45, "users": 100, "spawn_rate": 20},
        {"duration": 80, "users": 250, "spawn_rate": 30},
        {"duration": 120, "users": 250, "spawn_rate": 20},
    ]

    def tick(self):
        run_time = self.get_run_time()
        for stage in self.stages:
            if run_time < stage["duration"]:
                return stage["users"], stage["spawn_rate"]
        return None
