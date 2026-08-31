"""Cross-platform local entry point; run from any directory. Never prints secrets."""

import argparse
import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
os.environ.setdefault("UV_CACHE_DIR", str(ROOT / ".cache" / "uv"))


def run(*args: str, **kwargs):
    executable = shutil.which(args[0])
    if executable is None:
        raise SystemExit(f"Required command not found: {args[0]}")
    return subprocess.run([executable, *args[1:]], check=True, **kwargs)


def initialize(sqlite: bool):
    if not Path(".env").exists():
        content = Path(".env.example").read_text(encoding="utf-8")
        content = content.replace(
            "FENER_ADMIN_KEY=\n", f"FENER_ADMIN_KEY={secrets.token_urlsafe(36)}\n"
        )
        if sqlite:
            content = content.replace(
                "postgresql+psycopg://fener:fener_local@localhost:5432/fener",
                "sqlite:///.data/fener.db",
            )
        with Path(".env").open("x", encoding="utf-8") as file:
            file.write(content)
        if os.name != "nt":
            Path(".env").chmod(0o600)
    Path(".data").mkdir(exist_ok=True)
    run("uv", "sync", "--locked")
    run("pnpm", "install", "--frozen-lockfile")
    if "DATABASE_URL=postgresql" in Path(".env").read_text(encoding="utf-8"):
        run("docker", "compose", "up", "-d", "--wait", "db")
    run("uv", "run", "alembic", "upgrade", "head")
    print("Ready. Start services with: python scripts/manage.py dev")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "setup",
            "dev",
            "api",
            "web",
            "worker",
            "sync",
            "check",
            "schema",
            "backup",
            "export",
        ],
    )
    parser.add_argument(
        "--sqlite",
        action="store_true",
        help="Explicit lightweight fallback when creating a new .env",
    )
    parser.add_argument("--source", choices=["models_dev", "openrouter", "litellm", "llm_stats"])
    parser.add_argument("--docker", action="store_true", help="Use the Compose database for backup")
    args = parser.parse_args()
    commands = {
        "api": ["uv", "run", "uvicorn", "fener.api:app", "--host", "127.0.0.1", "--port", "8000"],
        "web": ["pnpm", "dev"],
        "worker": ["uv", "run", "fener", "worker"],
    }
    if args.command == "setup":
        initialize(args.sqlite)
    elif args.command in commands:
        run(*commands[args.command])
    elif args.command == "dev":
        processes = []
        try:
            for command in commands.values():
                executable = shutil.which(command[0])
                if not executable:
                    raise SystemExit(f"Required command not found: {command[0]}")
                processes.append(subprocess.Popen([executable, *command[1:]]))
            print("Fener: http://127.0.0.1:3000 · API: http://127.0.0.1:8000/docs")
            print("Worker enabled. Ctrl+C stops these services; no inference APIs are called.")
            while all(p.poll() is None for p in processes):
                try:
                    processes[0].wait(timeout=1)
                except subprocess.TimeoutExpired:
                    pass
        except KeyboardInterrupt:
            pass
        finally:
            for process in processes:
                if process.poll() is None:
                    process.terminate()
            for process in processes:
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
    elif args.command == "sync":
        run("uv", "run", "fener", "sync", *(["--source", args.source] if args.source else []))
    elif args.command == "check":
        for command in [
            ["uv", "run", "ruff", "check", "services", "tests", "scripts"],
            ["uv", "run", "ruff", "format", "--check", "services", "tests", "scripts"],
            ["uv", "run", "mypy"],
            ["uv", "run", "pytest", "-q"],
            ["pnpm", "typecheck"],
            ["pnpm", "lint"],
            ["pnpm", "test"],
            ["pnpm", "build"],
        ]:
            run(*command)
    elif args.command == "schema":
        run("uv", "run", "python", "scripts/schema.py")
        run(
            "node",
            "apps/web/node_modules/openapi-typescript/bin/cli.js",
            "docs/openapi.json",
            "-o",
            "apps/web/lib/api-schema.d.ts",
        )
        run(
            "node",
            "node_modules/prettier/bin/prettier.cjs",
            "--write",
            "docs/openapi.json",
            "apps/web/lib/api-schema.d.ts",
        )
    else:
        run(
            "uv",
            "run",
            "python",
            "scripts/data.py",
            args.command,
            *(["--docker"] if args.docker else []),
        )


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)
