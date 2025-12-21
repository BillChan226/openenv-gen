#!/usr/bin/env python3
"""Validate the {{ENV_NAME}} environment setup."""

import sys
import requests
import subprocess


def check_service(name: str, url: str, health_path: str = "/health") -> bool:
    """Check if a service is responding."""
    try:
        response = requests.get(f"{url}{health_path}", timeout=5)
        if response.ok:
            print(f"✓ {name} is running at {url}")
            return True
        print(f"✗ {name} returned status {response.status_code}")
        return False
    except requests.RequestException as e:
        print(f"✗ {name} not reachable: {e}")
        return False


def check_docker_containers() -> bool:
    """Check if Docker containers are running."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
        )
        containers = result.stdout.strip().split("\n")
        required = ["frontend", "backend", "database", "env_server"]

        all_running = True
        for container in required:
            found = any(container in c for c in containers)
            status = "✓" if found else "✗"
            print(f"{status} Container '{container}': {'running' if found else 'not found'}")
            if not found:
                all_running = False

        return all_running
    except Exception as e:
        print(f"✗ Docker check failed: {e}")
        return False


def main():
    print("=" * 50)
    print("{{ENV_NAME}} Environment Validation")
    print("=" * 50)
    print()

    print("Checking Docker containers...")
    docker_ok = check_docker_containers()
    print()

    print("Checking services...")
    services = [
        ("Frontend", "http://localhost:3000", "/"),
        ("Backend", "http://localhost:5000", "/api/health"),
        ("Environment Server", "http://localhost:8000", "/health"),
    ]

    all_ok = docker_ok
    for name, url, path in services:
        if not check_service(name, url, path):
            all_ok = False
    print()

    if all_ok:
        print("✓ All checks passed! Environment is ready.")
        sys.exit(0)
    else:
        print("✗ Some checks failed. Please fix the issues above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
