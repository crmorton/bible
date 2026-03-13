# Production Cost Analysis & Scaling Strategy

This document outlines the expected costs and configuration for the Bible API at both the test and production scales.

## 1. Test Scale: 25,000 Requests / Day
This scale is designed to fit primarily within the Google Cloud Free Tier.

### Cloud Run Configuration
- **Region**: `us-central1` (Iowa) - *Best for Free Tier eligibility.*
- **Requests per month**: ~760,000
- **Execution time per request**: **10 ms** (Optimized by in-memory SQLite).
- **CPU/Memory**: 1 vCPU / 512 MiB
- **Concurrency**: 100 requests per instance.

### Estimated Monthly Egress (GCP Transfer Out)
- **Baseline**: **5 GB / month**
- **Calculation**: 760,000 requests × ~7 KB average HTML payload.
- **Note**: With Cloudflare enabled, this should drop significantly (potentially < 1 GB).

---

## 2. Production Scale: 10 Million Requests / Day
Scaling to handle 10 million requests per day (~300M per month) requires a multi-regional approach and aggressive edge caching.

### Multi-Regional Deployment
Deployment across 4 regions for global low latency:
- `us-central1` (Americas)
- `europe-west4` (EMEA)
- `asia-northeast1` (Asia)
- `australia-southeast1` (Oceania)

### Cost Mitigation via Cloudflare
Without Cloudflare, 300M requests generating 2.1 TB of egress would incur significant GCP costs.

| Strategy | GCP Direct Cost | With Cloudflare Caching |
| :--- | :--- | :--- |
| **Egress** | High (~$150 - $200+) | **Near Zero** (Served from Edge) |
| **Compute** | Sustained Scaling | **Minimal** (Instances spin down when cache hits) |

### Key Optimization Metrics
- **Cache Hit Ratio (Target)**: > 90%
- **Edge Latency**: < 50ms for 95% of users.
- **GCP Duty Cycle**: GCP only computes the "long tail" of unique verses and translations; popular passages (John 3:16, etc.) are purely handled by Cloudflare.

---

## 3. Recommended Calculator Inputs
When updating the [GCP Pricing Calculator](https://cloud.google.com/products/calculator), use these specific Bible API values:

1. **Execution Time**: `10 ms` (Our SQLite DB is loaded in RAM).
2. **Instance Size**: `1 vCPU` and `512 MiB` (Sufficient for Python/FastAPI/MiniRacer).
3. **Network Egress**: `5 GB` (Test) | `2.1 TB` (Production - *but actual costs will be slashed by Cloudflare*).
