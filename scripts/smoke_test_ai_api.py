#!/usr/bin/env python3
"""Call a running PURE AI service with one deterministic synthetic window."""

from __future__ import annotations

import argparse
import json
import math
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    return parser.parse_args()


def request_json(url: str, payload: dict | None = None) -> dict:
    encoded = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=encoded,
        headers={"Content-Type": "application/json"},
        method="GET" if payload is None else "POST",
    )
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    args = parse_arguments()
    base_url = args.base_url.rstrip("/")
    time_values = [index / 30.0 for index in range(300)]
    waveform = [
        math.sin(2.0 * math.pi * 1.2 * value)
        + 0.12 * math.sin(2.0 * math.pi * 2.4 * value)
        for value in time_values
    ]
    try:
        health = request_json(f"{base_url}/health")
        prediction = request_json(
            f"{base_url}/v1/signal-quality",
            {
                "device_id": "pure-smoke-test",
                "sampling_rate_hz": 30,
                "ppg": waveform,
                "candidate_bpm": 72,
            },
        )
    except (HTTPError, URLError) as error:
        print(f"PURE AI API smoke test failed: {error}")
        return 1

    print(json.dumps({"health": health, "prediction": prediction}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
