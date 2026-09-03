const fs = require("fs");
const path = require("path");
const readline = require("readline/promises");

const dotenv = require("dotenv");
const db = require(path.join(__dirname, "..", "..", "database", "src", "database"));
const { getImplementationAdvice } = require("./implementationAgent");
const { getReview } = require("./reviewAgent");

const PACKAGE_ROOT = path.resolve(__dirname, "..");
const PROJECT_ROOT = path.resolve(PACKAGE_ROOT, "..");
const BACKEND_ROOT = PACKAGE_ROOT;
const FRONTEND_ROOT = path.join(PROJECT_ROOT, "frontend");

const DEFAULT_TASK =
    "Using only the validation evidence, identify the single highest-priority\n" +
    "verified problem and recommend one minimal code change to address it.\n" +
    "Do not recommend changes for anything that passed validation.";
const DEFAULT_DATABASE_BASE_URL = "http://127.0.0.1:5002";
const DEFAULT_BACKEND_BASE_URL = "http://127.0.0.1:5001";
const DEFAULT_LLM_BASE_URL = "http://localhost:11434/v1";

dotenv.config({
    path: path.resolve(BACKEND_ROOT, ".env")
});

const PLAN = {
    goal: "Validate the travel-agent stack with observe -> implement advice -> review -> human decision",
    db_plan: [
        "Check itinerary rows for required fields",
        "Check activity rows for required fields and foreign-key consistency",
        "Inspect a sample itinerary and sample activity set"
    ],
    backend_plan: [
        "Confirm backend route files export the expected handlers",
        "Confirm backend mount points match the route files",
        "Confirm feedback and itinerary update paths line up"
    ],
    frontend_plan: [
        "Confirm frontend fetch URLs match backend routes",
        "Confirm frontend payload keys match controller expectations"
    ]
};

const SOURCE_CONTRACTS = [
    {
        file: path.join(BACKEND_ROOT, "src/server.js"),
        snippets: [
            'require("./routes/citiesRoutes")',
            'require("./routes/getItineraryRoute")',
            'require("./routes/getFeedbackRoute")',
            'app.use("/api", cityRoutes)',
            'app.use("/api", itineraryRoutes)',
            'app.use("/api/update_itinerary_from_prompt", feedbackRoutes)'
        ]
    },
    {
        file: path.join(BACKEND_ROOT, "src/routes/citiesRoutes.js"),
        snippets: [
            'router.post("/cities"',
            "generateCitiesList",
            "module.exports = router"
        ]
    },
    {
        file: path.join(BACKEND_ROOT, "src/routes/getItineraryRoute.js"),
        snippets: [
            'router.post("/request_itineraries"',
            'router.post("/generate_complete_selected_itinerary"',
            'router.post("/update_itinerary_from_prompt"',
            "generateItineraryOptions",
            "generateCompleteItinerary",
            "updateItinerary",
            "module.exports = router"
        ]
    },
    {
        file: path.join(BACKEND_ROOT, "src/routes/getFeedbackRoute.js"),
        snippets: [
            'router.post("/", updateItineraryFromFeedback)',
            "module.exports = router"
        ]
    },
    {
        file: path.join(BACKEND_ROOT, "src/controllers/cityController.js"),
        snippets: [
            "function generateCitiesList",
            "generateCitiesList"
        ]
    },
    {
        file: path.join(BACKEND_ROOT, "src/controllers/itineraryController.js"),
        snippets: [
            "function generate_itineraries_options",
            "function build_complete_itinerary",
            "function updateItinerary",
            "generateItineraryOptions: generate_itineraries_options",
            "generateCompleteItinerary: build_complete_itinerary",
            "updateItinerary",
            "module.exports = {"
        ]
    },
    {
        file: path.join(BACKEND_ROOT, "src/controllers/getFeedbackController.js"),
        snippets: [
            "function updateItineraryFromFeedback",
            "updateItineraryFromFeedback"
        ]
    },
    {
        file: path.join(FRONTEND_ROOT, "src/pages/Travelling-Input-Form.tsx"),
        snippets: [
            'fetch("http://localhost:5001/api/cities"',
            "travelGroup",
            "travelStyle",
            "Requirements"
        ]
    },
    {
        file: path.join(FRONTEND_ROOT, "src/pages/itinerary_Options.tsx"),
        snippets: [
            'fetch("http://localhost:5001/api/request_itineraries"',
            "selectedItinerary",
            "travelPreference",
            "travelStyle"
        ]
    },
    {
        file: path.join(FRONTEND_ROOT, "src/pages/itinerary_Page.tsx"),
        snippets: [
            'fetch("http://localhost:5001/api/generate_complete_selected_itinerary"',
            'fetch("http://localhost:5001/api/update_itinerary_from_prompt"',
            "currentItinerary",
            "improvementPrompt",
            "selectedItinerary"
        ]
    }
];

const FRONTEND_PAYLOAD_CONTRACTS = [
    {
        file: path.join(FRONTEND_ROOT, "src/pages/Travelling-Input-Form.tsx"),
        objectName: "travelPreference",
        expectedKeys: [
            "destination",
            "startDate",
            "endDate",
            "budget",
            "travelGroup",
            "travelStyle",
            "Requirements"
        ]
    },
    {
        file: path.join(FRONTEND_ROOT, "src/pages/itinerary_Options.tsx"),
        objectName: "details",
        expectedKeys: [
            "destination",
            "startDate",
            "endDate",
            "cities",
            "budget",
            "group",
            "travelStyle",
            "travelPreference",
            "c"
        ]
    },
    {
        file: path.join(FRONTEND_ROOT, "src/pages/itinerary_Page.tsx"),
        objectName: "UserTravelValues",
        expectedKeys: [
            "destination",
            "startDate",
            "endDate",
            "cities",
            "budget",
            "group",
            "travelStyle",
            "travelPreference",
            "c",
            "selectedItinerary",
            "improvementPrompt"
        ]
    },
    {
        file: path.join(FRONTEND_ROOT, "src/pages/itinerary_Page.tsx"),
        objectName: "__inline_json_stringify__",
        expectedKeys: [
            "improvementPrompt",
            "currentItinerary",
            "destination",
            "startDate",
            "endDate",
            "cities",
            "budget",
            "group",
            "travelStyle",
            "travelPreference",
            "c",
            "selectedItinerary"
        ]
    }
];

function parseArgs(argv) {
    const args = {};

    for (let i = 0; i < argv.length; i += 1) {
        const token = argv[i];

        if (token === "--task" && argv[i + 1]) {
            args.task = argv[i + 1];
            i += 1;
            continue;
        }

        if (token === "--rounds" && argv[i + 1]) {
            args.rounds = Number(argv[i + 1]);
            i += 1;
            continue;
        }

        if (token === "--database-base-url" && argv[i + 1]) {
            args.databaseBaseUrl = argv[i + 1];
            i += 1;
            continue;
        }

        if (token === "--backend-base-url" && argv[i + 1]) {
            args.backendBaseUrl = argv[i + 1];
            i += 1;
            continue;
        }
    }

    return args;
}

function readTextIfExists(filePath) {
    try {
        return fs.readFileSync(filePath, "utf8");
    } catch {
        return null;
    }
}

function normalizeUrlPath(value) {
    const raw = String(value || "").trim();
    if (!raw) {
        return "";
    }

    try {
        if (/^https?:\/\//i.test(raw)) {
            return new URL(raw).pathname;
        }
    } catch {
        return raw;
    }

    return raw;
}

function extractFetchPaths(content) {
    if (!content) {
        return [];
    }

    const paths = [];
    const regex = /fetch\(\s*([`'"])(.*?)\1/g;
    let match;

    while ((match = regex.exec(content)) !== null) {
        paths.push(normalizeUrlPath(match[2]));
    }

    return paths;
}

function collectSnippetLines(content, snippet) {
    const directMatches = content
        .split(/\r?\n/)
        .map((line, index) => (line.includes(snippet) ? `${index + 1}: ${line.trim()}` : null))
        .filter(Boolean);

    if (directMatches.length > 0) {
        return directMatches;
    }

    const compactContent = content.replace(/\s+/g, "");
    const compactSnippet = snippet.replace(/\s+/g, "");

    if (compactContent.includes(compactSnippet)) {
        return [`matched across line breaks: ${snippet}`];
    }

    return [];
}

function inspectFile(filePath, snippets) {
    const content = readTextIfExists(filePath);
    const relPath = path.relative(PROJECT_ROOT, filePath);

    if (content === null) {
        return {
            file: relPath,
            exists: false,
            missingSnippets: snippets,
            matchedLines: [],
            fetchPaths: []
        };
    }

    const matchedLines = [];
    const missingSnippets = [];

    for (const snippet of snippets) {
        const lines = collectSnippetLines(content, snippet);
        if (lines.length > 0) {
            matchedLines.push(...lines.map((line) => `${relPath} | ${line}`));
        } else {
            missingSnippets.push(snippet);
        }
    }

    return {
        file: relPath,
        exists: true,
        missingSnippets,
        matchedLines,
        fetchPaths: extractFetchPaths(content)
    };
}

function extractObjectLiteralKeys(content, objectName) {
    if (!content || !objectName) {
        return [];
    }

    const pattern = objectName === "__inline_json_stringify__"
        ? /JSON\.stringify\(\s*\{([\s\S]*?)\}\s*\)/m
        : new RegExp(
            String.raw`(?:const|let|var)\s+${objectName}\s*=\s*\{([\s\S]*?)\n\s*\}`,
            "m"
        );
    const match = content.match(pattern);

    if (!match) {
        return [];
    }

    const objectBody = match[1];
    const keys = new Set();
    objectBody
        .split(",")
        .map((segment) => segment.trim())
        .forEach((segment) => {
            const keyMatch = segment.match(/^([A-Za-z_$][\w$]*)\s*(?::|$)/);
            if (keyMatch) {
                keys.add(keyMatch[1]);
            }
        });

    return Array.from(keys);
}

function inspectFrontendPayloadContracts() {
    return FRONTEND_PAYLOAD_CONTRACTS.map(({ file, objectName, expectedKeys }) => {
        const content = readTextIfExists(file);
        const relPath = path.relative(PROJECT_ROOT, file);
        const actualKeys = content ? extractObjectLiteralKeys(content, objectName) : [];
        const missingKeys = expectedKeys.filter((key) => !actualKeys.includes(key));
        const extraKeys = actualKeys.filter((key) => !expectedKeys.includes(key));

        return {
            file: relPath,
            objectName,
            exists: content !== null,
            expectedKeys,
            actualKeys,
            missingKeys,
            extraKeys
        };
    });
}

function isBlank(value) {
    return value === null || value === undefined || String(value).trim() === "";
}

function getSampleItinerary() {
    try {
        return db.prepare(`
            SELECT itinerary_id, destination, start_date, end_date, budget, travel_group, travel_style, requirements
            FROM itinerary
            ORDER BY itinerary_id
            LIMIT 1
        `).get();
    } catch {
        return null;
    }
}

function getSampleActivity(itineraryId) {
    if (!itineraryId) {
        return null;
    }

    try {
        return db.prepare(`
            SELECT activity_id, itinerary_id, day_no, date, location, time, cost, note
            FROM activity
            WHERE itinerary_id = ?
            ORDER BY activity_id
            LIMIT 1
        `).get(itineraryId);
    } catch {
        return null;
    }
}

function validateItineraryRow(row) {
    const errors = [];

    if (!row) {
        errors.push("no itinerary rows found");
        return errors;
    }

    if (isBlank(row.destination)) errors.push(`itinerary_id=${row.itinerary_id}: destination is required`);
    if (isBlank(row.start_date)) errors.push(`itinerary_id=${row.itinerary_id}: start_date is required`);
    if (isBlank(row.end_date)) errors.push(`itinerary_id=${row.itinerary_id}: end_date is required`);
    if (isBlank(row.budget)) errors.push(`itinerary_id=${row.itinerary_id}: budget is required`);
    if (isBlank(row.travel_style)) errors.push(`itinerary_id=${row.itinerary_id}: travel_style is required`);

    return errors;
}

function validateActivityRow(row) {
    const errors = [];

    if (!row) {
        errors.push("no activity rows found");
        return errors;
    }

    if (!Number.isInteger(row.itinerary_id)) errors.push(`activity_id=${row.activity_id}: itinerary_id must be an integer`);
    if (!Number.isInteger(row.day_no)) errors.push(`activity_id=${row.activity_id}: day_no must be an integer`);
    if (isBlank(row.date)) errors.push(`activity_id=${row.activity_id}: date is required`);
    if (isBlank(row.location)) errors.push(`activity_id=${row.activity_id}: location is required`);
    if (isBlank(row.time)) errors.push(`activity_id=${row.activity_id}: time is required`);

    return errors;
}

function observeDatabaseState() {
    const itineraryCount = db.prepare(`SELECT COUNT(*) AS count FROM itinerary`).get().count;
    const activityCount = db.prepare(`SELECT COUNT(*) AS count FROM activity`).get().count;
    const sampleItinerary = getSampleItinerary();
    const sampleActivity = sampleItinerary ? getSampleActivity(sampleItinerary.itinerary_id) : null;

    const allItineraries = db.prepare(`
        SELECT itinerary_id, destination, start_date, end_date, budget, travel_group, travel_style, requirements
        FROM itinerary
        ORDER BY itinerary_id
    `).all();

    const allActivities = db.prepare(`
        SELECT activity_id, itinerary_id, day_no, date, location, time, cost, note
        FROM activity
        ORDER BY activity_id
    `).all();

    const orphanActivities = db.prepare(`
        SELECT a.activity_id, a.itinerary_id
        FROM activity a
        LEFT JOIN itinerary i ON i.itinerary_id = a.itinerary_id
        WHERE i.itinerary_id IS NULL
    `).all();

    const issues = [
        ...allItineraries.flatMap(validateItineraryRow),
        ...allActivities.flatMap(validateActivityRow),
        ...orphanActivities.map((row) => `activity_id=${row.activity_id}: missing parent itinerary ${row.itinerary_id}`)
    ];

    return {
        ok: issues.length === 0,
        summary: itineraryCount === 0
            ? "No itineraries exist yet."
            : `${itineraryCount} itineraries and ${activityCount} activities found.`,
        itineraryCount,
        activityCount,
        sampleItinerary,
        sampleActivity,
        issues
    };
}

async function fetchWithTimeout(url, options = {}, timeoutMs = 5000) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);

    try {
        return await fetch(url, {
            ...options,
            signal: controller.signal
        });
    } finally {
        clearTimeout(timeout);
    }
}

async function checkEndpoint(label, method, url, body, expectedStatuses = []) {
    try {
        const response = await fetchWithTimeout(url, {
            method,
            headers: {
                "Content-Type": "application/json"
            },
            body: body === undefined ? undefined : JSON.stringify(body)
        });

        const text = await response.text();
        const pass = expectedStatuses.length > 0
            ? expectedStatuses.includes(response.status)
            : response.status < 500;

        return {
            label,
            ok: pass,
            status: response.status,
            expectedStatuses,
            contentOk: Boolean(text && text.trim()),
            bodyPreview: text.trim().slice(0, 220)
        };
    } catch (error) {
        return {
            label,
            ok: false,
            status: null,
            expectedStatuses,
            contentOk: false,
            error: error.message
        };
    }
}

async function observeLiveServices({ databaseBaseUrl, backendBaseUrl, sampleItinerary, sampleActivity }) {
    const itineraryId = sampleItinerary?.itinerary_id;

    const databaseChecks = [
        await checkEndpoint("database GET /health", "GET", `${databaseBaseUrl}/health`, undefined, [200]),
        ...(itineraryId
            ? [
                await checkEndpoint("database GET /api/itineraries/:id", "GET", `${databaseBaseUrl}/api/itineraries/${itineraryId}`, undefined, [200]),
                await checkEndpoint("database POST /api/itineraries validation", "POST", `${databaseBaseUrl}/api/itineraries`, {}, [400]),
                await checkEndpoint("database POST /api/itineraries/:id/activities validation", "POST", `${databaseBaseUrl}/api/itineraries/${itineraryId}/activities`, {}, [400])
            ]
            : [
                { label: "database GET /api/itineraries/:id", ok: false, status: null, contentOk: false, error: "skipped: no sample itinerary found" },
                { label: "database POST /api/itineraries validation", ok: false, status: null, contentOk: false, error: "skipped: no sample itinerary found" },
                { label: "database POST /api/itineraries/:id/activities validation", ok: false, status: null, contentOk: false, error: "skipped: no sample itinerary found" }
            ])
    ];

    const backendChecks = [
        await checkEndpoint("backend POST /api/cities", "POST", `${backendBaseUrl}/api/cities`, {}, [400]),
        await checkEndpoint("backend POST /api/request_itineraries", "POST", `${backendBaseUrl}/api/request_itineraries`, {}, [400]),
        await checkEndpoint("backend POST /api/generate_complete_selected_itinerary", "POST", `${backendBaseUrl}/api/generate_complete_selected_itinerary`, {}, [400]),
        await checkEndpoint("backend POST /api/update_itinerary_from_prompt", "POST", `${backendBaseUrl}/api/update_itinerary_from_prompt`, {}, [400])
    ];

    return {
        databaseChecks,
        backendChecks,
        sampleItineraryId: itineraryId || null,
        sampleActivityId: sampleActivity?.activity_id || null
    };
}

function buildSourceContracts() {
    return SOURCE_CONTRACTS.map(({ file, snippets }) => inspectFile(file, snippets));
}

function buildFrontendPayloadContracts() {
    return inspectFrontendPayloadContracts();
}

function findExpectedEndpointMismatches(observation) {
    const frontendFetches = observation.sourceContracts
        .flatMap((fileReport) => fileReport.fetchPaths)
        .filter(Boolean);

    const expected = [
        "/api/cities",
        "/api/request_itineraries",
        "/api/generate_complete_selected_itinerary",
        "/api/update_itinerary_from_prompt"
    ];

    return {
        missingFromFrontend: expected.filter((endpoint) => !frontendFetches.some((fetchPath) => fetchPath.includes(endpoint))),
        missingFromContracts: observation.sourceContracts.flatMap((fileReport) => fileReport.missingSnippets.map((snippet) => `${fileReport.file}: ${snippet}`))
    };
}

function isSkippedLiveCheck(check) {
    return typeof check.error === "string" && check.error.startsWith("skipped:");
}

function isConnectivityLiveCheckFailure(check) {
    return check.status === null && Boolean(check.error) && !isSkippedLiveCheck(check);
}

function buildVerifiedIssues(observation) {
    const issues = [];

    observation.db.issues.forEach((issue) => {
        issues.push(`DB: ${issue}`);
    });

    observation.mismatches.missingFromFrontend.forEach((endpoint) => {
        issues.push(`FRONTEND ENDPOINT: missing fetch for ${endpoint}`);
    });

    observation.mismatches.missingFromContracts.forEach((missing) => {
        issues.push(`SOURCE CONTRACT: missing ${missing}`);
    });

    observation.frontendPayloadContracts.forEach((report) => {
        report.missingKeys.forEach((key) => {
            issues.push(`FRONTEND PAYLOAD: ${report.file} ${report.objectName} missing key ${key}`);
        });
    });

    [
        ...observation.live.databaseChecks,
        ...observation.live.backendChecks
    ]
        .filter((check) => !check.ok && !isSkippedLiveCheck(check) && !isConnectivityLiveCheckFailure(check))
        .forEach((check) => {
            const status = check.status ?? "ERR";
            const expected = check.expectedStatuses?.length ? ` expected ${check.expectedStatuses.join("/")}` : "";
            const detail = check.error ? ` (${check.error})` : "";
            issues.push(`LIVE CHECK: ${check.label} -> ${status}${expected}${detail}`);
        });

    return issues;
}

function buildValidationBlockers(observation) {
    return [
        ...observation.live.databaseChecks,
        ...observation.live.backendChecks
    ]
        .filter((check) => !check.ok && isConnectivityLiveCheckFailure(check))
        .map((check) => `LIVE CHECK BLOCKED: ${check.label} (${check.error})`);
}

function buildAllowedRecommendationScope(observation) {
    const files = new Set([
        ...observation.sourceContracts.map((report) => report.file),
        ...observation.frontendPayloadContracts.map((report) => report.file)
    ]);
    const endpoints = new Set([
        "/api/cities",
        "/api/request_itineraries",
        "/api/generate_complete_selected_itinerary",
        "/api/update_itinerary_from_prompt",
        "/health"
    ]);

    observation.sourceContracts
        .flatMap((report) => report.fetchPaths)
        .filter(Boolean)
        .forEach((endpoint) => endpoints.add(endpoint));

    [
        ...observation.live.databaseChecks,
        ...observation.live.backendChecks
    ].forEach((check) => {
        const match = check.label.match(/\s(\/[A-Za-z0-9_/:.-]+)/);
        if (match) {
            endpoints.add(match[1]);
        }
    });

    return {
        files,
        endpoints
    };
}

function buildEvidenceText(observation) {
    const dbObservation = observation.db;
    const mismatches = observation.mismatches;
    const verifiedIssues = observation.verifiedIssues || buildVerifiedIssues(observation);
    const validationBlockers = observation.validationBlockers || buildValidationBlockers(observation);

    return [
        "VERIFIED ISSUES:",
        ...(verifiedIssues.length ? verifiedIssues : ["none"]),
        "",
        "VALIDATION BLOCKERS:",
        ...(validationBlockers.length ? validationBlockers : ["none"]),
        "",
        "ALLOWED FILES:",
        ...buildAllowedRecommendationScope(observation).files,
        "",
        "ALLOWED ENDPOINTS:",
        ...buildAllowedRecommendationScope(observation).endpoints,
        "",
        `DB SUMMARY: ${dbObservation.summary}`,
        `DB ISSUES: ${dbObservation.issues.length ? dbObservation.issues.join(" | ") : "none"}`,
        `SAMPLE ITINERARY: ${dbObservation.sampleItinerary ? JSON.stringify(dbObservation.sampleItinerary) : "none"}`,
        `SAMPLE ACTIVITY: ${dbObservation.sampleActivity ? JSON.stringify(dbObservation.sampleActivity) : "none"}`,
        "",
        "SOURCE CONTRACTS:",
        ...observation.sourceContracts.map((report) => {
            const header = `${report.file} :: ${report.exists ? "exists" : "missing"}`;
            const missing = report.missingSnippets.length ? `missing -> ${report.missingSnippets.join(" ; ")}` : "missing -> none";
            const matches = report.matchedLines.length ? report.matchedLines.join(" | ") : "matches -> none";
            return `${header}\n${missing}\n${matches}`;
        }),
        "",
        "FRONTEND PAYLOAD CONTRACTS:",
        ...observation.frontendPayloadContracts.map((report) => {
            const header = `${report.file} :: ${report.exists ? "exists" : "missing"}`;
            const expected = `expected -> ${report.expectedKeys.join(", ")}`;
            const actual = `actual -> ${report.actualKeys.length ? report.actualKeys.join(", ") : "none"}`;
            const missing = `missing -> ${report.missingKeys.length ? report.missingKeys.join(", ") : "none"}`;
            const extra = `extra -> ${report.extraKeys.length ? report.extraKeys.join(", ") : "none"}`;
            return `${header}\n${expected}\n${actual}\n${missing}\n${extra}`;
        }),
        "",
        "LIVE CHECKS:",
        ...observation.live.databaseChecks.map((check) => `${check.label} -> ${check.status ?? "ERR"} ${check.expectedStatuses?.length ? `expected ${check.expectedStatuses.join("/")}` : ""} ${check.error ? `(${check.error})` : ""} ${check.bodyPreview ? `| ${check.bodyPreview}` : ""}`),
        ...observation.live.backendChecks.map((check) => `${check.label} -> ${check.status ?? "ERR"} ${check.expectedStatuses?.length ? `expected ${check.expectedStatuses.join("/")}` : ""} ${check.error ? `(${check.error})` : ""} ${check.bodyPreview ? `| ${check.bodyPreview}` : ""}`),
        "",
        `MISSING FRONTEND ENDPOINTS: ${mismatches.missingFromFrontend.length ? mismatches.missingFromFrontend.join(", ") : "none"}`,
        `MISSING SOURCE CONTRACTS: ${mismatches.missingFromContracts.length ? mismatches.missingFromContracts.join(" | ") : "none"}`
    ].join("\n");
}

function buildNoIssueImplementation(observation) {
    const blockers = observation?.validationBlockers || [];

    return {
        content: JSON.stringify({
            observedProblem: "INSUFFICIENT EVIDENCE",
            evidence: ["VERIFIED ISSUES: none"],
            file: "",
            recommendedChange: "",
            confidence: "high",
            unknowns: blockers.length
                ? blockers
                : ["No verified validation failure was observed in database rows, source contracts, frontend payload contracts, or live service checks."]
        }, null, 4),
        error: ""
    };
}

function buildNoIssueReview(observation) {
    const blockers = observation?.validationBlockers || [];

    return {
        content: [
            "SUPPORTED",
            "",
            "Findings, ordered by severity:",
            "No verified issue was present in the validation evidence, so no code change should be recommended.",
            "",
            "Open questions or assumptions:",
            blockers.length
                ? `Validation blockers: ${blockers.join(" | ")}`
                : "Skipped sample itinerary checks are expected when the database has no itinerary rows.",
            "",
            "Short conclusion:",
            "Reject implementation changes until validation produces a concrete failure."
        ].join("\n"),
        error: ""
    };
}

function buildModelErrorReview(error) {
    return {
        content: [
            "INSUFFICIENT EVIDENCE",
            "",
            "Findings, ordered by severity:",
            `The implementation agent did not return a recommendation because the model call failed: ${error}`,
            "",
            "Open questions or assumptions:",
            "Confirm the configured Ollama/OpenAI-compatible endpoint is running before asking the model agents for advice.",
            "",
            "Short conclusion:",
            "No implementation advice can be accepted from this round."
        ].join("\n"),
        error: ""
    };
}

function buildUnsupportedRecommendationReview(implementation) {
    return {
        content: [
            "UNSUPPORTED",
            "",
            "Findings, ordered by severity:",
            "The implementation recommendation referenced files or endpoints outside the validation evidence.",
            implementation.content,
            "",
            "Open questions or assumptions:",
            "None.",
            "",
            "Short conclusion:",
            "Reject this recommendation and rerun after the validation evidence is concrete."
        ].join("\n"),
        error: ""
    };
}

function parseJsonObject(text) {
    try {
        return JSON.parse(text);
    } catch {
        const match = String(text || "").match(/\{[\s\S]*\}/);
        if (!match) {
            return null;
        }

        try {
            return JSON.parse(match[0]);
        } catch {
            return null;
        }
    }
}

function findUnsupportedRecommendationClaims(content, observation) {
    const parsed = parseJsonObject(content);
    const scope = buildAllowedRecommendationScope(observation);
    const issues = [];
    const text = String(content || "");

    if (parsed?.file && !scope.files.has(parsed.file)) {
        issues.push(`file "${parsed.file}" is not in the observed file set`);
    }

    const mentionedFiles = new Set(text.match(/[A-Za-z0-9_./-]+\.js\b/g) || []);
    mentionedFiles.forEach((file) => {
        if (!scope.files.has(file) && !Array.from(scope.files).some((allowed) => allowed.endsWith(`/${file}`))) {
            issues.push(`file "${file}" is not in the observed file set`);
        }
    });

    const mentionedEndpoints = new Set((text.match(/\/[A-Za-z0-9_/:.-]+/g) || [])
        .filter((endpoint) => !/\.(js|jsx|ts|tsx|json|txt)$/i.test(endpoint))
        .filter((endpoint) => !endpoint.includes("/src/"))
        .filter((endpoint) => !endpoint.includes("/backend/"))
        .filter((endpoint) => !endpoint.includes("/database/"))
        .filter((endpoint) => !endpoint.includes("/frontend/")));
    mentionedEndpoints.forEach((endpoint) => {
        const allowed = scope.endpoints.has(endpoint) || Array.from(scope.endpoints).some((known) => {
            if (!known.includes("/:")) {
                return false;
            }

            const pattern = new RegExp(`^${known.replace(/:[A-Za-z0-9_]+/g, "[^/]+")}$`);
            return pattern.test(endpoint);
        });

        if (!allowed) {
            issues.push(`endpoint "${endpoint}" is not in the observed endpoint set`);
        }
    });

    return [...new Set(issues)];
}

function sanitizeImplementationAdvice(implementation, observation) {
    if (!implementation.content) {
        return implementation;
    }

    const unsupportedClaims = findUnsupportedRecommendationClaims(implementation.content, observation);

    if (unsupportedClaims.length === 0) {
        return implementation;
    }

    return {
        content: JSON.stringify({
            observedProblem: "UNSUPPORTED MODEL OUTPUT",
            evidence: unsupportedClaims,
            file: "",
            recommendedChange: "",
            confidence: "low",
            unknowns: [
                "The model recommendation referenced files or endpoints outside the validation evidence."
            ]
        }, null, 4),
        error: implementation.error,
        unsupported: true
    };
}

async function humanReview({ observation, implementation, review, round }) {
    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout
    });

    try {
        console.log();
        console.log(`ROUND ${round} HUMAN REVIEW`);
        console.log();
        console.log("OBSERVATION SUMMARY");
        console.log(observation.db.summary);
        if (observation.db.issues.length > 0) {
            observation.db.issues.slice(0, 10).forEach((issue) => console.log(`- ${issue}`));
        }

        console.log();
        console.log("IMPLEMENTATION ADVICE");
        console.log(implementation.content || implementation.error || "No implementation advice returned.");

        console.log();
        console.log("REVIEW");
        console.log(review.content || review.error || "No review returned.");

        console.log();
        console.log("1 - Accept");
        console.log("2 - Partially Accept");
        console.log("3 - Reject");

        const selection = (await rl.question("Decision: ")).trim();
        const note = (await rl.question("Optional note: ")).trim();

        let decision = "Reject";
        if (selection === "1") {
            decision = "Accept";
        } else if (selection === "2") {
            decision = "Partially Accept";
        }

        return {
            decision,
            note
        };
    } finally {
        rl.close();
    }
}

async function observe({ databaseBaseUrl, backendBaseUrl }) {
    const dbObservation = observeDatabaseState();
    const sourceContracts = buildSourceContracts();
    const frontendPayloadContracts = buildFrontendPayloadContracts();
    const live = await observeLiveServices({
        databaseBaseUrl,
        backendBaseUrl,
        sampleItinerary: dbObservation.sampleItinerary,
        sampleActivity: dbObservation.sampleActivity
    });
    const mismatches = findExpectedEndpointMismatches({ sourceContracts });
    const partialObservation = {
        db: dbObservation,
        sourceContracts,
        frontendPayloadContracts,
        live,
        mismatches
    };
    const verifiedIssues = buildVerifiedIssues(partialObservation);
    const validationBlockers = buildValidationBlockers(partialObservation);

    return {
        ...partialObservation,
        verifiedIssues,
        validationBlockers,
        summary: dbObservation.summary
    };
}

function parseIntOrDefault(value, fallback) {
    const parsed = Number(value);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

async function main() {
    const args = parseArgs(process.argv.slice(2));
    const task = args.task || process.env.AGENT_TASK || DEFAULT_TASK;
    const maxRounds = parseIntOrDefault(args.rounds || process.env.AGENT_MAX_ROUNDS, 3);
    const databaseBaseUrl = args.databaseBaseUrl || process.env.DATABASE_BASE_URL || DEFAULT_DATABASE_BASE_URL;
    const backendBaseUrl = args.backendBaseUrl || process.env.BACKEND_BASE_URL || DEFAULT_BACKEND_BASE_URL;
    const llamaBaseUrl = process.env.OLLAMA_BASE_URL || process.env.LLAMA_BASE_URL || DEFAULT_LLM_BASE_URL;
    const qwenBaseUrl = process.env.OLLAMA_BASE_URL || process.env.QWEN_BASE_URL || DEFAULT_LLM_BASE_URL;
    const llamaModel = process.env.OLLAMA_MODEL || process.env.LLAMA_MODEL || "llama3.1";
    const qwenModel = process.env.OLLAMA_REVIEW_MODEL || process.env.QWEN_MODEL || "qwen2.5";

    console.log("=".repeat(60));
    console.log("TRAVEL AGENT LOOP");
    console.log("=".repeat(60));

    console.log();
    console.log("PLAN");
    console.log(JSON.stringify(PLAN, null, 2));

    let carryForward = "";

    for (let round = 1; round <= maxRounds; round += 1) {
        console.log();
        console.log(`ROUND ${round}`);
        console.log("OBSERVE");

        const observation = await observe({
            databaseBaseUrl,
            backendBaseUrl
        });

        const evidenceText = buildEvidenceText(observation);
        console.log(observation.summary);
        if (observation.verifiedIssues.length > 0) {
            console.log("Verified issues:");
            observation.verifiedIssues.slice(0, 10).forEach((issue) => console.log(`- ${issue}`));
        }
        if (observation.validationBlockers.length > 0) {
            console.log("Validation blockers:");
            observation.validationBlockers.slice(0, 10).forEach((blocker) => console.log(`- ${blocker}`));
        }
        if (observation.mismatches.missingFromFrontend.length > 0) {
            console.log(`Frontend endpoint gaps: ${observation.mismatches.missingFromFrontend.join(", ")}`);
        }

        console.log();
        console.log("IMPLEMENTATION AGENT");
        console.log(`Model: ${llamaModel}`);

        const implementation = observation.verifiedIssues.length === 0
            ? buildNoIssueImplementation(observation)
            : sanitizeImplementationAdvice(await getImplementationAdvice({
                task,
                validationEvidence: evidenceText,
                carryForward,
                modelConfig: { baseUrl: llamaBaseUrl, modelName: llamaModel }
            }), observation);

        console.log();
        console.log(implementation.content || implementation.error || "No implementation advice returned.");

        console.log();
        console.log("REVIEW AGENT");
        console.log(`Model: ${qwenModel}`);

        const review = observation.verifiedIssues.length === 0
            ? buildNoIssueReview(observation)
            : implementation.unsupported
                ? buildUnsupportedRecommendationReview(implementation)
                : implementation.error && !implementation.content
                    ? buildModelErrorReview(implementation.error)
                    : await getReview({
                task,
                implementationRecommendation: implementation.content || implementation.error || "No implementation advice returned.",
                validationEvidence: evidenceText,
                modelConfig: { baseUrl: qwenBaseUrl, modelName: qwenModel }
            });

        console.log();
        console.log(review.content || review.error || "No review returned.");

        const decision = await humanReview({
            observation,
            implementation,
            review,
            round
        });

        console.log();
        console.log(`Decision: ${decision.decision}`);

        if (decision.decision === "Accept") {
            console.log("LOOP COMPLETE");
            return;
        }

        if (decision.decision === "Partially Accept") {
            carryForward = [
                decision.note,
                review.content || review.error || ""
            ]
                .filter(Boolean)
                .join("\n");
            continue;
        }

        console.log("LOOP STOPPED");
        return;
    }

    console.log();
    console.log("Reached the maximum number of rounds without an accept decision.");
}

main().catch((error) => {
    console.error(error);
    process.exit(1);
});
