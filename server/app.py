"""HTTP entrypoint: same FastAPI app as `email_env.server`, port 7860 (HF Spaces default)."""

import argparse

import uvicorn

from email_env.server import app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=7860)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
