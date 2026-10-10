---
name: api-rate-limiting
description: Add rate limiting to an HTTP API with token bucket or sliding window counters, return 429 with Retry-After, and handle limits as a client with backoff.
---

# API rate limiting

## Server side
Pick a key (API token, user, IP). A token bucket allows bursts and refills steadily; a
sliding window is stricter. Store counters in Redis so every instance shares them.

## Responses
Return `429 Too Many Requests` with a `Retry-After` header and the remaining quota in
response headers.

## Client side
Retry with exponential backoff and jitter, and respect `Retry-After` when present.
