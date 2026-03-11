# Module 4: AI Supply Chain

## Overview

An ML model registry and inference pipeline that stores, distributes, and executes machine learning models. The registry accepts model uploads with no signature verification. The pipeline runner downloads models and deserializes them using Python's `pickle.load` — which executes arbitrary code during deserialization. This simulates the real-world AI supply chain where models are shared via registries (Hugging Face, private S3 buckets, internal model stores) and loaded by training/inference pipelines.

MinIO provides S3-compatible object storage as a secondary model hosting path, simulating cloud storage buckets that may be misconfigured or compromised.

## Services

| Service | Port | Role |
|---|---|---|
| **model-registry** | :8007 | Model storage — upload/download/list models, no signing |
| **pipeline-runner** | :8008 | Inference pipeline — downloads and loads models with pickle |
| **minio** | :9000 (API) / :9001 (console) | S3-compatible storage — secondary model hosting |

## How It Works

### Model Registry
A simple REST API for uploading and downloading `.pkl` model files. Stores models on disk with optional JSON metadata. No signature verification, no checksum enforcement, no authentication.

### Pipeline Runner
Accepts a model name and registry URL, downloads the model, and loads it with `pickle.load`. The caller can override the registry URL — pointing it at an attacker-controlled server.

Also supports loading models from MinIO S3 via `/run-from-s3`.

### MinIO
Standard S3-compatible object storage with default credentials. Models uploaded here can be fetched by the pipeline runner. In real attacks, compromised S3 buckets are a common vector for swapping legitimate models with poisoned ones.

## Attack Surface

### Pickle Deserialization RCE
The primary vulnerability. Python's `pickle.load` on untrusted data is equivalent to arbitrary code execution. A malicious pickle object can define a `__reduce__` method that calls `os.system()` (or any function) during deserialization — before the model is even used for inference.

**Attack flow:**
1. Create a malicious pickle payload (see `generate_poisoned.py`)
2. Upload it to the registry via `/models/upload`
3. Trigger the pipeline to load it via `POST /run`
4. Code executes on the pipeline-runner container during deserialization

- Pipeline endpoint: `POST /run`
- Payload: `{"model_name": "backdoor-model"}`
- `pickle.load` fires the payload on deserialization

### No Model Signature Verification
The registry stores models with no cryptographic signatures. An attacker can:
- Replace a legitimate model with a poisoned one
- Upload a new model with a trusted-looking name
- Modify model metadata to appear legitimate

### Registry Redirect
The pipeline runner accepts a `registry_url` parameter from the caller. An attacker can point it at an attacker-controlled server to serve a malicious model, even if the legitimate registry is clean.

- Payload: `{"model_name": "trusted-model", "registry_url": "http://192.168.19.128:9999"}`

### Path Traversal on Model Names
The model name is used directly in the file path. A name like `../../etc/backdoor` writes outside the models directory.

### S3 Misconfiguration (MinIO)
MinIO runs with default credentials (`minioadmin`/`minioadmin`). Models stored here can be read, modified, or replaced by anyone with the credentials.

- Console: `http://192.168.19.1:9001`
- API: `http://192.168.19.1:9000`
- Credentials: `minioadmin` / `minioadmin`

## Key Endpoints

### Model Registry (:8007)
| Method | Path | Description |
|---|---|---|
| POST | `/models/upload` | Upload a model (no signing) |
| GET | `/models/{name}` | Download a model |
| GET | `/models/{name}/metadata` | Get model metadata |
| GET | `/models` | List all models |
| GET | `/health` | Health check |

### Pipeline Runner (:8008)
| Method | Path | Description |
|---|---|---|
| POST | `/run` | Load model from registry and run inference (pickle RCE) |
| POST | `/run-from-s3` | Load model from MinIO S3 (same pickle vuln) |
| GET | `/health` | Health check |

### MinIO
| URL | Description |
|---|---|
| `http://192.168.19.1:9001` | Web console (minioadmin/minioadmin) |
| `http://192.168.19.1:9000` | S3 API |

## OSAI+ Topics
- Pickle deserialization attacks
- ML model poisoning
- Model registry security
- Supply chain integrity (signatures, checksums)
- S3 bucket misconfiguration
- Model provenance and trust
