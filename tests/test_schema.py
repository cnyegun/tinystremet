from conftest import query, run


def test_migrations_create_expected_tables(migrated_db):
    tables = query(
        migrated_db,
        """
        select string_agg(tablename, ',' order by tablename)
        from pg_tables
        where schemaname = 'public'
        """,
    )
    assert tables == (
        "assemblies,assembly_parts,customers,jobs,locations,part_events,parts,statuses,users,workstations"
    )


def test_seed_inserts_statuses_and_workstations(migrated_db):
    status_count = query(migrated_db, "select count(*) from statuses")
    workstation_count = query(migrated_db, "select count(*) from workstations")

    assert status_count == "9"
    assert workstation_count == "5"


def test_part_code_is_unique(migrated_db):
    query(
        migrated_db,
        "insert into customers (customer_code, name) values ('CUST-1', 'Customer 1')",
    )
    query(
        migrated_db,
        "insert into jobs (job_code, customer_id, drawing_code) values ('JOB-1', 1, 'DWG-1')",
    )
    query(
        migrated_db,
        "insert into users (full_name, role) values ('Demo User', 'operator')",
    )
    query(
        migrated_db,
        """
        insert into parts (part_code, job_id, status_id, current_location_id, created_by, updated_by)
        values (
            'PART-001',
            1,
            (select id from statuses where code = 'created'),
            (select id from locations where location_code = 'ZONE_RAW'),
            1,
            1
        )
        """,
    )

    duplicate = run(
        [
            "psql",
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            """
            insert into parts (part_code, job_id, status_id)
            values ('PART-001', 1, (select id from statuses where code = 'created'))
            """,
        ],
        env=migrated_db["env"],
        check=False,
    )

    assert duplicate.returncode != 0
    assert "duplicate key value violates unique constraint" in duplicate.stderr


def test_multiple_parts_can_join_one_assembly(migrated_db):
    query(
        migrated_db,
        "insert into customers (customer_code, name) values ('CUST-1', 'Customer 1')",
    )
    query(
        migrated_db,
        "insert into jobs (job_code, customer_id, drawing_code) values ('JOB-1', 1, 'DWG-1')",
    )
    query(
        migrated_db,
        "insert into users (full_name, role) values ('Demo User', 'operator')",
    )
    query(
        migrated_db,
        """
        insert into parts (part_code, job_id, status_id, created_by, updated_by)
        values
            ('PART-001', 1, (select id from statuses where code = 'created'), 1, 1),
            ('PART-002', 1, (select id from statuses where code = 'created'), 1, 1)
        """,
    )
    query(
        migrated_db,
        """
        insert into assemblies (assembly_code, job_id, status_id, created_by, updated_by)
        values ('ASM-001', 1, (select id from statuses where code = 'assembled'), 1, 1)
        """,
    )
    query(
        migrated_db,
        """
        insert into assembly_parts (assembly_id, part_id, qty_used)
        values (1, 1, 1), (1, 2, 1)
        """,
    )

    joined_parts = query(
        migrated_db, "select count(*) from assembly_parts where assembly_id = 1"
    )
    assert joined_parts == "2"


def test_part_events_capture_history_with_json_metadata(migrated_db):
    query(
        migrated_db,
        "insert into customers (customer_code, name) values ('CUST-1', 'Customer 1')",
    )
    query(
        migrated_db,
        "insert into jobs (job_code, customer_id, drawing_code) values ('JOB-1', 1, 'DWG-1')",
    )
    query(
        migrated_db,
        "insert into users (full_name, role) values ('Demo User', 'operator')",
    )
    query(
        migrated_db,
        """
        insert into parts (part_code, job_id, status_id, current_location_id, created_by, updated_by)
        values (
            'PART-001',
            1,
            (select id from statuses where code = 'created'),
            (select id from locations where location_code = 'ZONE_RAW'),
            1,
            1
        )
        """,
    )
    query(
        migrated_db,
        """
        insert into part_events (
            part_id,
            event_type,
            from_status_id,
            to_status_id,
            from_location_id,
            to_location_id,
            workstation_id,
            user_id,
            metadata
        ) values (
            1,
            'moved',
            (select id from statuses where code = 'created'),
            (select id from statuses where code = 'in_process'),
            (select id from locations where location_code = 'ZONE_RAW'),
            (select id from locations where location_code = 'WS_BEND_01'),
            (select id from workstations where workstation_code = 'BEND_01'),
            1,
            '{"scan_source":"barcode"}'::jsonb
        )
        """,
    )

    metadata = query(
        migrated_db,
        "select metadata ->> 'scan_source' from part_events where part_id = 1",
    )
    assert metadata == "barcode"
