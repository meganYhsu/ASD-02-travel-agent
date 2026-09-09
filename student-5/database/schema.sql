PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS Documents (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	traveller_id TEXT NOT NULL,
	document_type TEXT NOT NULL CHECK (
		document_type IN (
			'Passport',
			'Visa',
			'Travel Permit',
			'Vaccination Certificate',
			'Other'
		)
	),
	document_number TEXT NOT NULL,
	issuing_country TEXT NOT NULL,
	nationality TEXT NOT NULL,
	issue_date TEXT NOT NULL,
	expiry_date TEXT NOT NULL,
	status TEXT NOT NULL CHECK (
		status IN ('valid', 'expiring', 'expired', 'revoked')
	),
	created_at TEXT NOT NULL,
	updated_at TEXT NOT NULL,
	UNIQUE (traveller_id, document_type, document_number),
	CHECK (date(expiry_date) >= date(issue_date))
);

CREATE INDEX IF NOT EXISTS idx_documents_traveller ON Documents (traveller_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON Documents (status);
CREATE INDEX IF NOT EXISTS idx_documents_expiry ON Documents (expiry_date);

CREATE TABLE IF NOT EXISTS EntryRequirements (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	destination_country TEXT NOT NULL,
	traveller_nationality TEXT NOT NULL,
	requirement_type TEXT NOT NULL CHECK (
		requirement_type IN (
			'Passport required',
			'Minimum passport validity',
			'Visa required',
			'Visa not required',
			'Vaccination required',
			'Travel permit required',
			'Other'
		)
	),
	document_type TEXT NOT NULL CHECK (
		document_type IN (
			'Passport',
			'Visa',
			'Travel Permit',
			'Vaccination Certificate',
			'Other'
		)
	),
	description TEXT NOT NULL,
	minimum_validity_days INTEGER NOT NULL DEFAULT 0 CHECK (minimum_validity_days >= 0),
	is_required INTEGER NOT NULL DEFAULT 1 CHECK (is_required IN (0, 1)),
	created_at TEXT NOT NULL,
	updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_entry_destination ON EntryRequirements (destination_country);
CREATE INDEX IF NOT EXISTS idx_entry_nationality ON EntryRequirements (traveller_nationality);
CREATE INDEX IF NOT EXISTS idx_entry_dest_nat ON EntryRequirements (destination_country, traveller_nationality);

CREATE TABLE IF NOT EXISTS PackingLists (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	trip_id TEXT NOT NULL,
	traveller_id TEXT NOT NULL,
	destination TEXT NOT NULL,
	start_date TEXT NOT NULL,
	end_date TEXT NOT NULL,
	climate TEXT NOT NULL,
	planned_activities TEXT NOT NULL,
	generated_by_ai INTEGER NOT NULL DEFAULT 0 CHECK (generated_by_ai IN (0, 1)),
	created_at TEXT NOT NULL,
	updated_at TEXT NOT NULL,
	CHECK (date(end_date) >= date(start_date))
);

CREATE INDEX IF NOT EXISTS idx_packing_trip ON PackingLists (trip_id);
CREATE INDEX IF NOT EXISTS idx_packing_traveller ON PackingLists (traveller_id);

CREATE TABLE IF NOT EXISTS ChecklistItems (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	packing_list_id INTEGER NOT NULL,
	item_name TEXT NOT NULL,
	category TEXT NOT NULL CHECK (
		category IN (
			'Clothing',
			'Toiletries',
			'Electronics',
			'Documents',
			'Medication / Health',
			'Activity Equipment',
			'Miscellaneous'
		)
	),
	quantity INTEGER NOT NULL CHECK (quantity > 0),
	is_completed INTEGER NOT NULL DEFAULT 0 CHECK (is_completed IN (0, 1)),
	completed_at TEXT,
	is_ai_generated INTEGER NOT NULL DEFAULT 0 CHECK (is_ai_generated IN (0, 1)),
	created_at TEXT NOT NULL,
	updated_at TEXT NOT NULL,
	FOREIGN KEY (packing_list_id) REFERENCES PackingLists (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_checklist_list ON ChecklistItems (packing_list_id);
CREATE INDEX IF NOT EXISTS idx_checklist_completed ON ChecklistItems (is_completed);

CREATE TABLE IF NOT EXISTS PreTripTasks (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	trip_id TEXT NOT NULL,
	traveller_id TEXT NOT NULL,
	task_name TEXT NOT NULL,
	description TEXT NOT NULL,
	due_date TEXT NOT NULL,
	priority TEXT NOT NULL CHECK (priority IN ('low', 'medium', 'high')),
	is_completed INTEGER NOT NULL DEFAULT 0 CHECK (is_completed IN (0, 1)),
	completed_at TEXT,
	is_ai_generated INTEGER NOT NULL DEFAULT 0 CHECK (is_ai_generated IN (0, 1)),
	created_at TEXT NOT NULL,
	updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tasks_trip ON PreTripTasks (trip_id);
CREATE INDEX IF NOT EXISTS idx_tasks_traveller ON PreTripTasks (traveller_id);
CREATE INDEX IF NOT EXISTS idx_tasks_completed ON PreTripTasks (is_completed);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON PreTripTasks (priority);
