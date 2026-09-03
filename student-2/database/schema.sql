PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS Travelers (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	full_name TEXT NOT NULL,
	username TEXT NOT NULL UNIQUE,
	email TEXT NOT NULL UNIQUE,
	home_location TEXT NOT NULL,
	travel_style TEXT NOT NULL CHECK (
		travel_style IN ('Budget', 'Mid-range', 'Luxury')
	),
	created_at TEXT NOT NULL,
	updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_travelers_email ON Travelers (email);
CREATE INDEX IF NOT EXISTS idx_travelers_style ON Travelers (travel_style);

CREATE TABLE IF NOT EXISTS Preferences (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	traveler_id INTEGER NOT NULL REFERENCES Travelers (id) ON DELETE CASCADE,
	budget_min REAL NOT NULL CHECK (budget_min >= 0),
	budget_max REAL NOT NULL CHECK (budget_max >= 0),
	currency TEXT NOT NULL DEFAULT 'AUD',
	pace TEXT NOT NULL CHECK (pace IN ('relaxed', 'balanced', 'packed')),
	preferred_trip_length_days INTEGER CHECK (
		preferred_trip_length_days IS NULL OR preferred_trip_length_days > 0
	),
	created_at TEXT NOT NULL,
	updated_at TEXT NOT NULL,
	UNIQUE (traveler_id),
	CHECK (budget_max >= budget_min)
);

CREATE INDEX IF NOT EXISTS idx_preferences_traveler ON Preferences (traveler_id);

CREATE TABLE IF NOT EXISTS Interests (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	traveler_id INTEGER NOT NULL REFERENCES Travelers (id) ON DELETE CASCADE,
	interest_category TEXT NOT NULL CHECK (
		interest_category IN (
			'Food & Dining',
			'History & Culture',
			'Nature & Outdoors',
			'Art & Museums',
			'Nightlife',
			'Shopping',
			'Adventure Sports',
			'Beaches',
			'Architecture',
			'Local Experiences',
			'Wellness & Spa',
			'Photography'
		)
	),
	priority TEXT NOT NULL DEFAULT 'medium' CHECK (
		priority IN ('low', 'medium', 'high')
	),
	created_at TEXT NOT NULL,
	updated_at TEXT NOT NULL,
	UNIQUE (traveler_id, interest_category)
);

CREATE INDEX IF NOT EXISTS idx_interests_traveler ON Interests (traveler_id);
CREATE INDEX IF NOT EXISTS idx_interests_category ON Interests (interest_category);

CREATE TABLE IF NOT EXISTS AccessibilityNeeds (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	traveler_id INTEGER NOT NULL REFERENCES Travelers (id) ON DELETE CASCADE,
	requirement TEXT NOT NULL CHECK (
		requirement IN (
			'None',
			'Step-free access',
			'Wheelchair accessible',
			'Limited walking',
			'Visual assistance',
			'Hearing assistance',
			'Service animal',
			'Accessible bathroom',
			'Elevator required',
			'Other'
		)
	),
	dietary_restriction TEXT NOT NULL CHECK (
		dietary_restriction IN (
			'None',
			'Vegetarian',
			'Vegan',
			'Halal',
			'Kosher',
			'Gluten-free',
			'Nut allergy',
			'Dairy-free',
			'Shellfish allergy',
			'Other'
		)
	),
	notes TEXT,
	created_at TEXT NOT NULL,
	updated_at TEXT NOT NULL,
	UNIQUE (traveler_id, requirement, dietary_restriction)
);

CREATE INDEX IF NOT EXISTS idx_accessibility_traveler ON AccessibilityNeeds (traveler_id);
