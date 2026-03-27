import importlib

import pytest
from httpx import ASGITransport, AsyncClient

from conftest import execute, query


def seed_basics(db):
    execute(
        db,
        """
        insert into customers (customer_code, name) values ('STREMET-001', 'Stremet Demo Customer');
        insert into jobs (job_code, customer_id, drawing_code, description)
        values ('JOB-1001', 1, 'DWG-ALPHA', 'Bracket family');
        insert into users (email, full_name, role)
        values ('operator1@stremet.test', 'Operator One', 'operator');
        """,
    )


@pytest.fixture
async def api_client(migrated_db, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", migrated_db["url"])
    module = importlib.import_module("app.main")
    module = importlib.reload(module)
    app = module.create_app()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, migrated_db


@pytest.mark.anyio
async def test_create_part_returns_created_record(api_client):
    client, db = api_client
    seed_basics(db)

    response = await client.post(
        "/parts",
        json={
            "part_code": "PART-1001",
            "job_code": "JOB-1001",
            "status_code": "created",
            "location_code": "ZONE_RAW",
            "created_by_email": "operator1@stremet.test",
            "notes": "Cut and waiting for bending",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["part_code"] == "PART-1001"
    assert payload["status_code"] == "created"
    assert payload["location_code"] == "ZONE_RAW"
    assert query(db, "select count(*) from parts where part_code = 'PART-1001'") == "1"


@pytest.mark.anyio
async def test_record_part_event_updates_current_state(api_client):
    client, db = api_client
    seed_basics(db)
    execute(
        db,
        """
        insert into parts (part_code, job_id, status_id, current_location_id, created_by, updated_by)
        values (
            'PART-2001',
            (select id from jobs where job_code = 'JOB-1001'),
            (select id from statuses where code = 'created'),
            (select id from locations where location_code = 'ZONE_RAW'),
            (select id from users where email = 'operator1@stremet.test'),
            (select id from users where email = 'operator1@stremet.test')
        );
        """,
    )

    response = await client.post(
        "/parts/PART-2001/events",
        json={
            "event_type": "moved",
            "to_status_code": "in_process",
            "to_location_code": "WS_BEND_01",
            "workstation_code": "BEND_01",
            "user_email": "operator1@stremet.test",
            "notes": "Started bending",
            "metadata": {"scan_source": "barcode"},
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["part_code"] == "PART-2001"
    assert payload["current_status_code"] == "in_process"
    assert payload["current_location_code"] == "WS_BEND_01"
    assert (
        query(
            db,
            "select count(*) from part_events where part_id = (select id from parts where part_code = 'PART-2001')",
        )
        == "1"
    )


@pytest.mark.anyio
async def test_create_assembly_links_multiple_parts(api_client):
    client, db = api_client
    seed_basics(db)
    execute(
        db,
        """
        insert into parts (part_code, job_id, status_id, created_by, updated_by)
        values
            ('PART-3001', (select id from jobs where job_code = 'JOB-1001'), (select id from statuses where code = 'created'), (select id from users where email = 'operator1@stremet.test'), (select id from users where email = 'operator1@stremet.test')),
            ('PART-3002', (select id from jobs where job_code = 'JOB-1001'), (select id from statuses where code = 'created'), (select id from users where email = 'operator1@stremet.test'), (select id from users where email = 'operator1@stremet.test'));
        """,
    )

    response = await client.post(
        "/assemblies",
        json={
            "assembly_code": "ASM-3001",
            "job_code": "JOB-1001",
            "status_code": "assembled",
            "location_code": "ZONE_ASSEMBLY",
            "created_by_email": "operator1@stremet.test",
            "part_codes": ["PART-3001", "PART-3002"],
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["assembly_code"] == "ASM-3001"
    assert payload["part_codes"] == ["PART-3001", "PART-3002"]
    assert (
        query(
            db,
            "select count(*) from assembly_parts where assembly_id = (select id from assemblies where assembly_code = 'ASM-3001')",
        )
        == "2"
    )


@pytest.mark.anyio
async def test_seed_demo_populates_realistic_records(api_client):
    client, db = api_client

    response = await client.post("/demo/seed")

    assert response.status_code == 201
    payload = response.json()
    assert payload["parts_created"] >= 4
    assert payload["assemblies_created"] >= 1
    assert query(db, "select count(*) from parts") == str(payload["parts_created"])
