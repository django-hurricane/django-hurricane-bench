import os
import re
from locust import LoadTestShape


def parse_duration_seconds(duration_str: str) -> int:
    """Parses durations like '45s', '2m', '90' into integer seconds."""
    if not duration_str:
        return 45
    duration_str = str(duration_str).strip().lower()
    match = re.match(r"^(\d+)(s|m|h)?$", duration_str)
    if not match:
        try:
            return int(float(duration_str))
        except ValueError:
            return 45
    val, unit = match.groups()
    val = int(val)
    if unit == "m":
        return val * 60
    elif unit == "h":
        return val * 3600
    return val


class StepLoadShape(LoadTestShape):
    """
    Step-up traffic ramp to simulate real-world traffic spikes and scaling behavior.
    Dynamically computes 4 stages based on BENCH_DURATION and BENCH_USERS:
      - Stage 1 (Initial Ramp): 20% of duration, ramp to ~25% max users
      - Stage 2 (Medium Load): 45% of duration, ramp to ~60% max users
      - Stage 3 (Peak Ramp): 75% of duration, ramp to 100% max users
      - Stage 4 (Sustained Peak): remaining duration to 100%, maintain 100% max users
    """

    def __init__(self):
        super().__init__()
        total_duration = parse_duration_seconds(os.environ.get("BENCH_DURATION", "45s"))
        peak_users = int(os.environ.get("BENCH_USERS", "150"))
        spawn_rate = int(os.environ.get("BENCH_SPAWN_RATE", "25"))

        d1 = max(5, int(total_duration * 0.20))
        d2 = max(d1 + 5, int(total_duration * 0.45))
        d3 = max(d2 + 5, int(total_duration * 0.75))
        d4 = total_duration

        u1 = max(1, int(peak_users * 0.25))
        u2 = max(u1 + 1, int(peak_users * 0.60))
        u3 = peak_users
        u4 = peak_users

        r1 = max(1, spawn_rate // 2)
        r2 = spawn_rate
        r3 = spawn_rate
        r4 = max(1, spawn_rate // 2)

        self.stages = [
            {"duration": d1, "users": u1, "spawn_rate": r1},
            {"duration": d2, "users": u2, "spawn_rate": r2},
            {"duration": d3, "users": u3, "spawn_rate": r3},
            {"duration": d4, "users": u4, "spawn_rate": r4},
        ]

    def tick(self):
        run_time = self.get_run_time()
        for stage in self.stages:
            if run_time < stage["duration"]:
                return stage["users"], stage["spawn_rate"]
        return None
