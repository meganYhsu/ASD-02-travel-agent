-- Deterministic demonstration data for Release 0 (student-2: Traveler Preferences).
-- Every table is seeded with at least ten (10) records per the project specification.

INSERT OR IGNORE INTO Travelers (
	id, full_name, username, email, home_location, travel_style, created_at, updated_at
) VALUES
(1,  'Aiko Tanaka',      'aiko.t',      'aiko.tanaka@example.com',      'Sydney, Australia',      'Mid-range', '2026-01-05T09:00:00Z', '2026-01-05T09:00:00Z'),
(2,  'Ben Okafor',       'ben.okafor',  'ben.okafor@example.com',       'Melbourne, Australia',   'Budget',    '2026-01-05T09:10:00Z', '2026-01-05T09:10:00Z'),
(3,  'Clara Mendes',     'clara.m',     'clara.mendes@example.com',     'Brisbane, Australia',    'Luxury',    '2026-01-06T10:00:00Z', '2026-01-06T10:00:00Z'),
(4,  'Daniel Kim',       'dan.kim',     'daniel.kim@example.com',       'Perth, Australia',       'Mid-range', '2026-01-06T10:30:00Z', '2026-01-06T10:30:00Z'),
(5,  'Elena Rossi',      'elena.r',     'elena.rossi@example.com',      'Adelaide, Australia',    'Luxury',    '2026-01-07T08:15:00Z', '2026-01-07T08:15:00Z'),
(6,  'Farid Rahman',     'farid.r',     'farid.rahman@example.com',     'Canberra, Australia',    'Budget',    '2026-01-07T11:45:00Z', '2026-01-07T11:45:00Z'),
(7,  'Grace Nguyen',     'grace.n',     'grace.nguyen@example.com',     'Hobart, Australia',      'Mid-range', '2026-01-08T09:20:00Z', '2026-01-08T09:20:00Z'),
(8,  'Hugo Laurent',     'hugo.l',      'hugo.laurent@example.com',     'Darwin, Australia',      'Budget',    '2026-01-08T14:05:00Z', '2026-01-08T14:05:00Z'),
(9,  'Isla Fraser',      'isla.f',      'isla.fraser@example.com',      'Auckland, New Zealand',  'Mid-range', '2026-01-09T09:00:00Z', '2026-01-09T09:00:00Z'),
(10, 'Jonas Weber',      'jonas.w',     'jonas.weber@example.com',      'Wellington, New Zealand','Luxury',    '2026-01-09T16:40:00Z', '2026-01-09T16:40:00Z'),
(11, 'Keira Adams',      'keira.a',     'keira.adams@example.com',      'Gold Coast, Australia',  'Mid-range', '2026-01-10T10:10:00Z', '2026-01-10T10:10:00Z'),
(12, 'Liam Murphy',      'liam.m',      'liam.murphy@example.com',      'Newcastle, Australia',   'Budget',    '2026-01-10T13:25:00Z', '2026-01-10T13:25:00Z');

INSERT OR IGNORE INTO Preferences (
	id, traveler_id, budget_min, budget_max, currency, pace, preferred_trip_length_days, created_at, updated_at
) VALUES
(1,  1,  2000.00,  4500.00, 'AUD', 'balanced', 10, '2026-01-05T09:05:00Z', '2026-01-05T09:05:00Z'),
(2,  2,   800.00,  1800.00, 'AUD', 'packed',    7, '2026-01-05T09:15:00Z', '2026-01-05T09:15:00Z'),
(3,  3,  8000.00, 15000.00, 'AUD', 'relaxed',  14, '2026-01-06T10:05:00Z', '2026-01-06T10:05:00Z'),
(4,  4,  2500.00,  5000.00, 'AUD', 'balanced', 12, '2026-01-06T10:35:00Z', '2026-01-06T10:35:00Z'),
(5,  5,  9000.00, 18000.00, 'AUD', 'relaxed',  21, '2026-01-07T08:20:00Z', '2026-01-07T08:20:00Z'),
(6,  6,   600.00,  1500.00, 'AUD', 'packed',    5, '2026-01-07T11:50:00Z', '2026-01-07T11:50:00Z'),
(7,  7,  3000.00,  6000.00, 'AUD', 'balanced',  9, '2026-01-08T09:25:00Z', '2026-01-08T09:25:00Z'),
(8,  8,   700.00,  1600.00, 'AUD', 'packed',    6, '2026-01-08T14:10:00Z', '2026-01-08T14:10:00Z'),
(9,  9,  2200.00,  4800.00, 'NZD', 'balanced', 11, '2026-01-09T09:05:00Z', '2026-01-09T09:05:00Z'),
(10, 10, 10000.00, 20000.00,'NZD', 'relaxed',  18, '2026-01-09T16:45:00Z', '2026-01-09T16:45:00Z'),
(11, 11, 2800.00,  5500.00, 'AUD', 'balanced', 10, '2026-01-10T10:15:00Z', '2026-01-10T10:15:00Z'),
(12, 12,  900.00,  2000.00, 'AUD', 'packed',    8, '2026-01-10T13:30:00Z', '2026-01-10T13:30:00Z');

INSERT OR IGNORE INTO Interests (
	id, traveler_id, interest_category, priority, created_at, updated_at
) VALUES
(1,  1,  'Food & Dining',      'high',   '2026-01-05T09:06:00Z', '2026-01-05T09:06:00Z'),
(2,  1,  'History & Culture',  'medium', '2026-01-05T09:06:30Z', '2026-01-05T09:06:30Z'),
(3,  1,  'Photography',        'low',    '2026-01-05T09:07:00Z', '2026-01-05T09:07:00Z'),
(4,  2,  'Adventure Sports',   'high',   '2026-01-05T09:16:00Z', '2026-01-05T09:16:00Z'),
(5,  2,  'Nature & Outdoors',  'high',   '2026-01-05T09:16:30Z', '2026-01-05T09:16:30Z'),
(6,  3,  'Wellness & Spa',     'high',   '2026-01-06T10:06:00Z', '2026-01-06T10:06:00Z'),
(7,  3,  'Art & Museums',      'medium', '2026-01-06T10:06:30Z', '2026-01-06T10:06:30Z'),
(8,  3,  'Food & Dining',      'high',   '2026-01-06T10:07:00Z', '2026-01-06T10:07:00Z'),
(9,  4,  'Architecture',       'medium', '2026-01-06T10:36:00Z', '2026-01-06T10:36:00Z'),
(10, 4,  'Local Experiences',  'high',   '2026-01-06T10:36:30Z', '2026-01-06T10:36:30Z'),
(11, 5,  'Beaches',            'high',   '2026-01-07T08:21:00Z', '2026-01-07T08:21:00Z'),
(12, 5,  'Wellness & Spa',     'high',   '2026-01-07T08:21:30Z', '2026-01-07T08:21:30Z'),
(13, 6,  'Nightlife',          'medium', '2026-01-07T11:51:00Z', '2026-01-07T11:51:00Z'),
(14, 6,  'Shopping',           'low',    '2026-01-07T11:51:30Z', '2026-01-07T11:51:30Z'),
(15, 7,  'Nature & Outdoors',  'high',   '2026-01-08T09:26:00Z', '2026-01-08T09:26:00Z'),
(16, 7,  'Photography',        'medium', '2026-01-08T09:26:30Z', '2026-01-08T09:26:30Z'),
(17, 8,  'Adventure Sports',   'high',   '2026-01-08T14:11:00Z', '2026-01-08T14:11:00Z'),
(18, 8,  'Beaches',            'medium', '2026-01-08T14:11:30Z', '2026-01-08T14:11:30Z'),
(19, 9,  'History & Culture',  'high',   '2026-01-09T09:06:00Z', '2026-01-09T09:06:00Z'),
(20, 9,  'Art & Museums',      'medium', '2026-01-09T09:06:30Z', '2026-01-09T09:06:30Z'),
(21, 10, 'Food & Dining',      'high',   '2026-01-09T16:46:00Z', '2026-01-09T16:46:00Z'),
(22, 10, 'Architecture',       'medium', '2026-01-09T16:46:30Z', '2026-01-09T16:46:30Z'),
(23, 11, 'Local Experiences',  'high',   '2026-01-10T10:16:00Z', '2026-01-10T10:16:00Z'),
(24, 11, 'Shopping',           'medium', '2026-01-10T10:16:30Z', '2026-01-10T10:16:30Z'),
(25, 12, 'Nightlife',          'high',   '2026-01-10T13:31:00Z', '2026-01-10T13:31:00Z'),
(26, 12, 'Nature & Outdoors',  'medium', '2026-01-10T13:31:30Z', '2026-01-10T13:31:30Z');

INSERT OR IGNORE INTO AccessibilityNeeds (
	id, traveler_id, requirement, dietary_restriction, notes, created_at, updated_at
) VALUES
(1,  1,  'None',                  'Vegetarian',        'Prefers vegetarian set menus where available.',      '2026-01-05T09:08:00Z', '2026-01-05T09:08:00Z'),
(2,  2,  'None',                  'None',              NULL,                                                 '2026-01-05T09:17:00Z', '2026-01-05T09:17:00Z'),
(3,  3,  'Step-free access',      'Gluten-free',       'Requires step-free hotel entry and lifts.',          '2026-01-06T10:08:00Z', '2026-01-06T10:08:00Z'),
(4,  4,  'None',                  'Halal',             'Halal dining required for all main meals.',          '2026-01-06T10:37:00Z', '2026-01-06T10:37:00Z'),
(5,  5,  'Limited walking',       'None',              'Maximum 2 km walking per activity block.',           '2026-01-07T08:22:00Z', '2026-01-07T08:22:00Z'),
(6,  6,  'None',                  'Vegan',             'Fully plant-based diet.',                            '2026-01-07T11:52:00Z', '2026-01-07T11:52:00Z'),
(7,  7,  'Hearing assistance',    'None',              'Requires captioned tours where offered.',            '2026-01-08T09:27:00Z', '2026-01-08T09:27:00Z'),
(8,  8,  'None',                  'Nut allergy',       'Severe peanut and tree-nut allergy, carries EpiPen.','2026-01-08T14:12:00Z', '2026-01-08T14:12:00Z'),
(9,  9,  'Wheelchair accessible', 'None',              'Manual wheelchair, needs accessible transfers.',     '2026-01-09T09:07:00Z', '2026-01-09T09:07:00Z'),
(10, 10, 'Accessible bathroom',   'Dairy-free',        'Lactose intolerant, needs accessible bathroom.',     '2026-01-09T16:47:00Z', '2026-01-09T16:47:00Z'),
(11, 11, 'None',                  'Shellfish allergy', 'Avoids all shellfish and cross-contamination.',      '2026-01-10T10:17:00Z', '2026-01-10T10:17:00Z'),
(12, 12, 'Visual assistance',     'None',              'Large-print itineraries preferred.',                 '2026-01-10T13:32:00Z', '2026-01-10T13:32:00Z');
