import os

from env.openenv_adapter import app  # noqa: F401


def _env(name: str, default: str) -> str:
    v = os.getenv(name)
    return v if v is not None and str(v).strip() != "" else default


# Exposed for convenience when running `python -m env.server.main`
HOST = _env("OPENENV_HOST", "0.0.0.0")
PORT = int(_env("OPENENV_PORT", "9100"))


def main() -> None:
    """Run the OpenEnv adapter via uvicorn.

    Note: In production/docker, prefer:
        uvicorn env.server.main:app --host 0.0.0.0 --port 9100
    """

    import uvicorn

    uvicorn.run("env.server.main:app", host=HOST, port=PORT, reload=False)


if __name__ == "__main__":
    main()
