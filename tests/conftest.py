import os
import shutil
import socket
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
DB_DIR = ROOT / "db"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def run(command, *, env=None, check=True, capture_output=True):
    kwargs = {"text": True, "env": env, "check": check}
    if capture_output:
        kwargs["capture_output"] = True
    else:
        kwargs["stdout"] = subprocess.DEVNULL
        kwargs["stderr"] = subprocess.DEVNULL
    return subprocess.run(command, **kwargs)


@pytest.fixture(scope="session")
def postgres_cluster():
    if (
        not shutil.which("initdb")
        or not shutil.which("pg_ctl")
        or not shutil.which("psql")
    ):
        pytest.skip("PostgreSQL command line tools are required for tests")

    temp_dir = Path(tempfile.mkdtemp(prefix="stremet_pg_"))
    data_dir = temp_dir / "data"
    socket_dir = temp_dir / "socket"
    log_file = temp_dir / "postgres.log"
    socket_dir.mkdir()
    port = _free_port()

    initdb = run(["initdb", "-D", str(data_dir), "-A", "trust", "-U", "postgres"])
    assert initdb.returncode == 0, initdb.stderr

    start = run(
        [
            "pg_ctl",
            "-D",
            str(data_dir),
            "-l",
            str(log_file),
            "-o",
            f"-F -k {socket_dir} -p {port}",
            "-w",
            "start",
        ],
        capture_output=False,
    )
    assert start.returncode == 0

    env = os.environ.copy()
    env.update(
        {
            "PGHOST": str(socket_dir),
            "PGPORT": str(port),
            "PGUSER": "postgres",
            "PGDATABASE": "postgres",
        }
    )

    deadline = time.time() + 10
    while True:
        probe = run(["psql", "-At", "-c", "select 1"], env=env, check=False)
        if probe.returncode == 0 and probe.stdout.strip() == "1":
            break
        if time.time() > deadline:
            raise AssertionError(f"Postgres did not start in time: {probe.stderr}")
        time.sleep(0.2)

    try:
        yield env, data_dir, socket_dir, port
    finally:
        run(
            ["pg_ctl", "-D", str(data_dir), "-m", "fast", "stop"],
            check=False,
            capture_output=False,
        )
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def migrated_db(postgres_cluster):
    env, _, socket_dir, port = postgres_cluster
    db_name = f"test_{uuid.uuid4().hex[:8]}"

    createdb = run(["createdb", db_name], env=env)
    assert createdb.returncode == 0, createdb.stderr

    db_env = env.copy()
    db_env["PGDATABASE"] = db_name

    migration = run(
        ["psql", "-v", "ON_ERROR_STOP=1", "-f", str(DB_DIR / "001_init.sql")],
        env=db_env,
    )
    assert migration.returncode == 0, migration.stderr

    seed = run(
        [
            "psql",
            "-v",
            "ON_ERROR_STOP=1",
            "-f",
            str(DB_DIR / "002_seed_reference_data.sql"),
        ],
        env=db_env,
    )
    assert seed.returncode == 0, seed.stderr

    db_url = f"postgresql://postgres@/{db_name}?host={socket_dir}&port={port}"

    try:
        yield {"env": db_env, "name": db_name, "url": db_url}
    finally:
        admin_env = env.copy()
        admin_env["PGDATABASE"] = "postgres"
        run(["dropdb", "--if-exists", db_name], env=admin_env, check=False)


def query(db, sql: str) -> str:
    result = run(["psql", "-At", "-c", sql], env=db["env"])
    return result.stdout.strip()


def execute(db, sql: str) -> None:
    run(["psql", "-v", "ON_ERROR_STOP=1", "-c", sql], env=db["env"])
