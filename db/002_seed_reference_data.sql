BEGIN;

INSERT INTO statuses (code, name, sort_order)
VALUES
    ('created', 'Created', 10),
    ('queued', 'Queued', 20),
    ('in_process', 'In Process', 30),
    ('waiting_next_step', 'Waiting Next Step', 40),
    ('stored', 'Stored', 50),
    ('assembled', 'Assembled', 60),
    ('packed', 'Packed', 70),
    ('shipped', 'Shipped', 80),
    ('blocked', 'Blocked', 90)
ON CONFLICT (code) DO NOTHING;

INSERT INTO locations (location_code, name, location_type, parent_location_id)
VALUES
    ('FACILITY_MAIN', 'Main Factory', 'facility', NULL),
    ('ZONE_RAW', 'Raw Material Area', 'zone', (SELECT id FROM locations WHERE location_code = 'FACILITY_MAIN')),
    ('ZONE_LASER_Q', 'Laser Queue', 'zone', (SELECT id FROM locations WHERE location_code = 'FACILITY_MAIN')),
    ('WS_BEND_01', 'Bending Station 1', 'workstation_area', (SELECT id FROM locations WHERE location_code = 'FACILITY_MAIN')),
    ('WS_BEND_02', 'Bending Station 2', 'workstation_area', (SELECT id FROM locations WHERE location_code = 'FACILITY_MAIN')),
    ('WS_WELD_A', 'Welding Cell A', 'workstation_area', (SELECT id FROM locations WHERE location_code = 'FACILITY_MAIN')),
    ('ZONE_ASSEMBLY', 'Assembly Area', 'zone', (SELECT id FROM locations WHERE location_code = 'FACILITY_MAIN')),
    ('ZONE_PACK', 'Packaging Area', 'zone', (SELECT id FROM locations WHERE location_code = 'FACILITY_MAIN')),
    ('RACK_FIN_A1', 'Finished Goods Rack A1', 'rack', (SELECT id FROM locations WHERE location_code = 'FACILITY_MAIN'))
ON CONFLICT (location_code) DO NOTHING;

INSERT INTO workstations (workstation_code, name, location_id, process_step)
VALUES
    ('LASER_01', 'Laser Station 1', (SELECT id FROM locations WHERE location_code = 'ZONE_LASER_Q'), 'cutting'),
    ('BEND_01', 'Bending Station 1', (SELECT id FROM locations WHERE location_code = 'WS_BEND_01'), 'bending'),
    ('BEND_02', 'Bending Station 2', (SELECT id FROM locations WHERE location_code = 'WS_BEND_02'), 'bending'),
    ('WELD_A', 'Welding Cell A', (SELECT id FROM locations WHERE location_code = 'WS_WELD_A'), 'welding'),
    ('PACK_01', 'Packing Station 1', (SELECT id FROM locations WHERE location_code = 'ZONE_PACK'), 'packaging')
ON CONFLICT (workstation_code) DO NOTHING;

COMMIT;
