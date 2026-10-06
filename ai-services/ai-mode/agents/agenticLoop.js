const {
    getImplementationAdvice
} = require("./implementationAgent");

const {
    getReview
} = require("./reviewAgent");

const {
    recordReview
} = require("./reviewRecorder");

const {
    checkService,
    buildStudentEvidenceText
} = require("./validation");

const readline = require("readline/promises");




// =====================
// Student 2 URLs
// =====================

const STUDENT2_FRONTEND =
    process.env.STUDENT2_FRONTEND_URL ||
    "http://localhost:3002";

const STUDENT2_BACKEND =
    process.env.STUDENT2_BACKEND_URL ||
    "http://localhost:5002";

const STUDENT2_DATABASE =
    process.env.STUDENT2_DATABASE_URL ||
    "http://localhost:6002";



// =====================
// Student 4 URLs
// =====================

const STUDENT4_FRONTEND =
    process.env.STUDENT4_FRONTEND_URL ||
    "http://localhost:3004";

const STUDENT4_BACKEND =
    process.env.STUDENT4_BACKEND_URL ||
    "http://localhost:5004";

const STUDENT4_DATABASE =
    process.env.STUDENT4_DATABASE_URL ||
    "http://localhost:6004";


// =====================
// Student 3 URLs
// =====================

const STUDENT3_FRONTEND =
    process.env.STUDENT3_FRONTEND_URL ||
    "http://localhost:3003";

const STUDENT3_BACKEND =
    process.env.STUDENT3_BACKEND_URL ||
    "http://localhost:5003";

const STUDENT3_DATABASE =
    process.env.STUDENT3_DATABASE_URL ||
    "http://localhost:6003";


// =====================
// Student 5 URLs
// =====================

const STUDENT5_FRONTEND =
    process.env.STUDENT5_FRONTEND_URL ||
    "http://localhost:8505";

const STUDENT5_BACKEND =
    process.env.STUDENT5_BACKEND_URL ||
    "http://localhost:5505";

const STUDENT5_DATABASE =
    process.env.STUDENT5_DATABASE_URL ||
    "http://localhost:5405";

// =====================
// Release 1 - shared local MCP and RAG servers
// Both run on the host and are not defined in docker-compose.yml.
// =====================

const MCP_SERVER =
    process.env.MCP_SERVER_URL ||
    "http://localhost:7004";

const RAG_SERVER =
    process.env.RAG_SERVER_URL ||
    "http://localhost:7001";

const RAG_CALLER =
    process.env.RAG_CALLER ||
    "student-3-budget";

const RAG_TIMEOUT_MS =
    Number(
        process.env.RAG_TIMEOUT_MS ||
        300000
    );

const MCP_ENABLED =
    (process.env.MCP_ENABLED || "true")
        .toLowerCase() !== "false";

const RAG_ENABLED =
    (process.env.RAG_ENABLED || "true")
        .toLowerCase() !== "false";




async function main() {


    const PLAN = {
        goal:
            "Use the shared Development Agentic AI Loop to validate a student's Travel Agent microservice before release.",

        actions: [
            "Observe the selected student's frontend, backend and database",
            "Collect verified validation evidence",
            "Run the shared Implementation Agent",
            "Run the shared Review Agent",
            "Require human review",
            "Record the review evidence",
            "Repeat when partially accepted"
        ]
    };


    /* =========================================================
       COMMAND-LINE INPUT
    ========================================================= */

    function parseArgs(argv) {

        const args = {
            student:
                process.env.AGENT_STUDENT ||
                "student-4",

            task:
                process.env.AGENT_TASK ||
                "",

            rounds:
                Number(
                    process.env.AGENT_MAX_ROUNDS ||
                    3
                )
        };


        for (
            let i = 0;
            i < argv.length;
            i += 1
        ) {

            if (
                argv[i] === "--student" &&
                argv[i + 1]
            ) {
                args.student = argv[i + 1];
                i += 1;
                continue;
            }


            if (
                argv[i] === "--task" &&
                argv[i + 1]
            ) {
                args.task = argv[i + 1];
                i += 1;
                continue;
            }


            if (
                argv[i] === "--rounds" &&
                argv[i + 1]
            ) {
                args.rounds =
                    Number(argv[i + 1]);

                i += 1;
            }
        }


        return args;
    }


    /* =========================================================
       SELECT THE CORRECT STUDENT OBSERVER
    ========================================================= */

    async function observeStudent(student) {

        switch (student) {

            case "student-1":
                return observeStudent1();

            case "student-2":
                return observeStudent2();

            case "student-3":
                return observeStudent3();

            case "student-4":
                return observeStudent4();

            case "student-5":
                return observeStudent5();

            default:
                throw new Error(
                    `Unknown student: ${student}`
                );
        }
    }



    /* =========================================================
       MAIN SHARED LOOP
    ========================================================= */

    // async function main() {

    const args =
        parseArgs(
            process.argv.slice(2)
        );


    const student =
        args.student;


    const task =
        args.task ||
        `Validate ${student}'s Travel Agent microservice and identify verified development or integration issues.`;


    const maxRounds =
        args.rounds;


    let carryForward = "";


    console.log(
        "=".repeat(60)
    );

    console.log(
        "SHARED DEVELOPMENT AGENTIC AI LOOP"
    );

    console.log(
        "=".repeat(60)
    );


    console.log(
        `\nStudent: ${student}`
    );

    console.log(
        `Task: ${task}`
    );


    console.log("\nPLAN");

    console.log(
        JSON.stringify(
            PLAN,
            null,
            2
        )
    );


    for (
        let round = 1;
        round <= maxRounds;
        round += 1
    ) {

        console.log(
            `\n${"=".repeat(60)}`
        );

        console.log(
            `ROUND ${round}`
        );

        console.log(
            "=".repeat(60)
        );


        /* =====================
           ACT
        ===================== */

        console.log("\nACT");

        console.log(
            `Validate ${student}'s development implementation.`
        );


        /* =====================
           OBSERVE
        ===================== */

        console.log("\nOBSERVE");


        const observation =
            await observeStudent(
                student
            );


        const evidenceText =
            buildStudentEvidenceText(
                observation
            );


        console.log(
            evidenceText
        );


        /* =====================
           ADAPT
        ===================== */

        console.log("\nADAPT");


        /* ---------------------
           IMPLEMENTATION AGENT
        --------------------- */

        console.log(
            "\nIMPLEMENTATION AGENT"
        );


        const implementation =
            await getImplementationAdvice({

                student,

                task,

                validationEvidence:
                    evidenceText,

                carryForward
            });


        console.log(
            implementation.content ||
            implementation.error
        );


        if (implementation.error) {

            throw new Error(
                `Implementation Agent failed: ${implementation.error}`
            );
        }


        /* ---------------------
           REVIEW AGENT
        --------------------- */

        console.log(
            "\nREVIEW AGENT"
        );


        const review =
            await getReview({

                student,

                task,

                implementationRecommendation:
                    implementation.content,

                validationEvidence:
                    evidenceText,

                carryForward
            });


        console.log(
            review.content ||
            review.error
        );


        if (review.error) {

            throw new Error(
                `Review Agent failed: ${review.error}`
            );
        }


        /* ---------------------
           HUMAN REVIEW
        --------------------- */

        const decision =
            await humanReview({

                observation,

                implementation,

                review,

                round
            });


        /* ---------------------
           RECORD EVIDENCE
        --------------------- */

        await recordReview({

            student,

            round,

            task,

            observation,

            validationEvidence:
                evidenceText,

            implementationRecommendation:
                implementation.content,

            review:
                review.content,

            humanDecision:
                decision.decision,

            humanNote:
                decision.note,

            carryForward,

            timestamp:
                new Date().toISOString()
        });


        /* =====================
           LOOP DECISION
        ===================== */

        if (
            decision.decision ===
            "Accept"
        ) {

            console.log(
                "\nRecommendation accepted."
            );

            console.log(
                "LOOP COMPLETE"
            );

            return;
        }


        if (
            decision.decision ===
            "Partially Accept"
        ) {

            carryForward = [

                decision.note,

                review.content

            ]
                .filter(Boolean)
                .join("\n");


            console.log(
                "\nPartially accepted."
            );

            console.log(
                "Feedback will be carried into the next round."
            );


            continue;
        }


        console.log(
            "\nRecommendation rejected."
        );

        console.log(
            "LOOP STOPPED"
        );

        return;
    }


    console.log(
        "\nMaximum number of rounds reached."
    );
}


/* =========================================================
   RUN
========================================================= */

main().catch(
    (error) => {

        console.error(
            "Shared agentic loop failed:",
            error
        );

        process.exit(1);
    }
);




async function observeIntegratedApplication() {

    const [
        student1,
        student2,
        student3,
        student4,
        student5
    ] = await Promise.all([
        observeStudent1(),
        observeStudent2(),
        observeStudent3(),
        observeStudent4(),
        observeStudent5()
    ]);

    return {
        student1,
        student2,
        student3,
        student4,
        student5
    };
}

async function humanReview({
    observation,
    implementation,
    review,
    round
}) {
    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout
    });

    try {
        console.log(`\nROUND ${round} HUMAN REVIEW`);

        console.log("\n1 - Accept");
        console.log("2 - Partially Accept");
        console.log("3 - Reject");

        const selection =
            (await rl.question("Decision: ")).trim();

        const note =
            (await rl.question("Optional note: ")).trim();

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




async function observeStudent4() {

    const frontend =
        await checkService(
            "Student 4 Frontend",
            STUDENT4_FRONTEND,
            {
                expectedStatuses: [200]
            }
        );

    const backend =
        await checkService(
            "Student 4 Backend - Cities",
            `${STUDENT4_BACKEND}/api/cities`,
            {
                method: "POST",

                body: {
                    destination: "Australia"
                },

                expectedStatuses: [200]
            }
        );

    const database =
        await checkService(
            "Student 4 Database",
            `${STUDENT4_DATABASE}/health`,
            {
                expectedStatuses: [200]
            }
        );

    const services = [
        frontend,
        backend,
        database
    ];

    const issues = services
        .filter(service => !service.ok)
        .map(service =>
            `${service.name} failed: ${service.error ||
            `HTTP ${service.status}`
            }`
        );

    return {
        student: "Student 4",
        component: "Plan Itinerary",
        ok: issues.length === 0,
        services,
        issues
    };
}

/* =========================================================
   RELEASE 1 VALIDATION HELPER

   checkService() in validation.js reports reachability only.
   The MCP and RAG requirements also need the response body
   asserted - a registered tool list, citations, a confidence
   category, an insufficient-context response. This helper adds
   that assertion while returning the same service shape, so
   buildStudentEvidenceText() needs no change.
========================================================= */

async function checkContract(
    name,
    url,
    {
        method = "GET",
        body = null,
        expectedStatuses = [200],
        timeoutMs = 20000,
        assert = null
    } = {}
) {

    const controller = new AbortController();

    const timer = setTimeout(
        () => controller.abort(),
        timeoutMs
    );

    try {
        const response = await fetch(url, {
            method,

            headers: body
                ? { "Content-Type": "application/json" }
                : undefined,

            body: body
                ? JSON.stringify(body)
                : undefined,

            signal: controller.signal
        });

        const text = await response.text();

        let payload = null;

        try {
            payload = JSON.parse(text);
        } catch (error) {
            payload = null;
        }

        const statusOk =
            expectedStatuses.includes(response.status);

        let assertOk = true;
        let detail = `HTTP ${response.status}`;

        if (assert) {

            const outcome =
                assert(payload, text);

            assertOk = outcome.ok;

            detail =
                `HTTP ${response.status}, ${outcome.detail}`;
        }

        const ok = statusOk && assertOk;

        return {
            name,
            url,
            ok,
            status: response.status,
            detail,
            error: ok
                ? null
                : `contract not satisfied (${detail})`
        };

    } catch (error) {

        const timedOut =
            error.name === "AbortError";

        return {
            name,
            url,
            ok: false,
            status: 0,

            detail: timedOut
                ? `timed out after ${timeoutMs} ms`
                : `request failed: ${error.message}`,

            error: timedOut
                ? `timed out after ${timeoutMs} ms`
                : error.message
        };
    } finally {
        clearTimeout(timer);
    }
}


function skipped(name, flag) {
    return {
        name,
        url: "not called",
        ok: true,
        status: 0,
        detail: `skipped (${flag}=false)`,
        error: null
    };
}


// RELEASE 1 - SHARED MCP SERVER (Student 3)

async function observeStudent3Mcp() {

    if (!MCP_ENABLED) {
        return [
            skipped(
                "Student 3 MCP - shared server",
                "MCP_ENABLED"
            )
        ];
    }

    const PERMITTED = [
        "total_activity_count",
        "total_activities_count_a_day",
        "get_trip_activities_desc"
    ];

    const registry =
        await checkContract(
            "Student 3 MCP - registered tools",
            `${MCP_SERVER}/mcp/tools`,
            {
                assert: (payload) => {

                    const names =
                        (payload && payload.tools) || [];

                    const present =
                        PERMITTED.filter(
                            tool => names.includes(tool)
                        );

                    return {
                        ok:
                            names.length > 0 &&
                            present.length === PERMITTED.length,

                        detail:
                            `registered=${names.length}, ` +
                            `permitted_present=` +
                            `${present.length}/${PERMITTED.length}`
                    };
                }
            }
        );

    const activityCount =
        await checkContract(
            "Student 3 MCP - tool total_activity_count",
            `${MCP_SERVER}/mcp/tool`,
            {
                method: "POST",

                body: {
                    tool_name: "total_activity_count",
                    arguments: { itinerary_id: 3 }
                },

                assert: (payload) => {

                    const result =
                        payload && payload.result;

                    return {
                        ok: Boolean(
                            payload &&
                            payload.ok &&
                            result
                        ),

                        detail:
                            `ok=${payload && payload.ok}, ` +
                            `activities=` +
                            `${result && result.total_no_of_activities}`
                    };
                }
            }
        );

    const activityDesc =
        await checkContract(
            "Student 3 MCP - tool get_trip_activities_desc",
            `${MCP_SERVER}/mcp/tool`,
            {
                method: "POST",

                body: {
                    tool_name: "get_trip_activities_desc",
                    arguments: { itinerary_id: 3 }
                },

                assert: (payload) => {

                    const list =
                        (payload &&
                            payload.result &&
                            payload.result.activity_description) || [];

                    return {
                        ok: Boolean(payload && payload.ok),
                        detail:
                            `ok=${payload && payload.ok}, ` +
                            `descriptions=${list.length}`
                    };
                }
            }
        );

    const unregistered =
        await checkContract(
            "Student 3 MCP - unregistered tool refused by server",
            `${MCP_SERVER}/mcp/tool`,
            {
                method: "POST",

                body: {
                    tool_name: "not_a_registered_tool",
                    arguments: {}
                },

                expectedStatuses: [400, 403, 404, 500],

                assert: (payload) => ({
                    ok: Boolean(
                        payload &&
                        payload.ok === false &&
                        payload.error
                    ),
                    detail:
                        `error_returned=` +
                        `${Boolean(payload && payload.error)}`
                })
            }
        );

    const boundary =
        await checkContract(
            "Student 3 MCP - registered tool outside boundary refused by backend",
            `${STUDENT3_BACKEND}/mcp/get_travel_requirements`,
            {
                method: "POST",
                body: { trip_id: 1 },
                expectedStatuses: [403],

                assert: (payload, text) => ({
                    ok: /outside the Budget/i.test(text),
                    detail:
                        "refused with HTTP 403 before contacting the server"
                })
            }
        );

    const throughBackend =
        await checkContract(
            "Student 3 MCP - permitted tool through backend",
            `${STUDENT3_BACKEND}/mcp/total_activity_count`,
            {
                method: "POST",
                body: { trip_id: 1 },

                assert: (payload, text) => ({
                    ok: /MCP tool result/i.test(text),
                    detail:
                        `result rendered=${/MCP tool result/i.test(text)}`
                })
            }
        );

    return [
        registry,
        activityCount,
        activityDesc,
        unregistered,
        boundary,
        throughBackend
    ];
}


//  RELEASE 1 - SHARED RAG SERVER (Student 3)

async function observeStudent3Rag() {

    if (!RAG_ENABLED) {
        return [
            skipped(
                "Student 3 RAG - shared server",
                "RAG_ENABLED"
            )
        ];
    }

    const groundedQuery =
        "What expenses are recorded for trip 1?";

    const unrelatedQuery =
        "zzzqqq xylophone submarine telegraph";

    const health =
        await checkContract(
            "Student 3 RAG - shared server health",
            `${RAG_SERVER}/health`,
            { timeoutMs: 10000 }
        );

    const retrieval =
        await checkContract(
            "Student 3 RAG - context retrieved",
            `${RAG_SERVER}/rag/retrieve`,
            {
                method: "POST",

                body: {
                    query: groundedQuery,
                    k: 5,
                    caller: RAG_CALLER
                },

                timeoutMs: 60000,

                assert: (payload) => {

                    const results =
                        (payload && payload.results) || [];

                    const mode =
                        (payload && payload.retrieval_mode) ||
                        "unknown";

                    return {
                        ok: results.length > 0,
                        detail:
                            `retrieved=${results.length}, mode=${mode}` +
                            (results.length
                                ? `, top=${results[0].source_id}`
                                : "")
                    };
                }
            }
        );

    const grounded =
        await checkContract(
            "Student 3 RAG - grounded answer with citations",
            `${RAG_SERVER}/rag/answer`,
            {
                method: "POST",

                body: {
                    query: groundedQuery,
                    k: 5,
                    caller: RAG_CALLER
                },

                timeoutMs: RAG_TIMEOUT_MS,

                assert: (payload) => {

                    const citations =
                        (payload && payload.citations) || [];

                    const answer =
                        ((payload && payload.answer) || "").trim();

                    const confidence =
                        payload && payload.confidence_category;

                    const isGrounded =
                        citations.length > 0 &&
                        answer.toLowerCase() !==
                        "insufficient evidence.";

                    return {
                        ok: isGrounded && Boolean(confidence),
                        detail:
                            `citations=${citations.length}, ` +
                            `confidence=${confidence}, ` +
                            `grounded=${isGrounded}`
                    };
                }
            }
        );

    const insufficient =
        await checkContract(
            "Student 3 RAG - insufficient-context response",
            `${RAG_SERVER}/rag/answer`,
            {
                method: "POST",

                body: {
                    query: unrelatedQuery,
                    k: 5,
                    caller: RAG_CALLER
                },

                timeoutMs: RAG_TIMEOUT_MS,

                assert: (payload) => {

                    const citations =
                        (payload && payload.citations) || [];

                    const answer =
                        ((payload && payload.answer) || "")
                            .trim()
                            .toLowerCase();

                    const refused =
                        answer === "insufficient evidence." ||
                        citations.length === 0;

                    return {
                        ok: refused,
                        detail: `insufficient_context=${refused}`
                    };
                }
            }
        );

    const renderedGrounded =
        await checkContract(
            "Student 3 RAG - backend renders citations",
            `${STUDENT3_BACKEND}/rag/query`,
            {
                method: "POST",
                body: { question: groundedQuery },
                timeoutMs: RAG_TIMEOUT_MS,

                assert: (payload, text) => ({
                    ok: /citations/i.test(text),
                    detail: `citations shown=${/citations/i.test(text)}`
                })
            }
        );

    const renderedRefusal =
        await checkContract(
            "Student 3 RAG - backend renders insufficient context",
            `${STUDENT3_BACKEND}/rag/query`,
            {
                method: "POST",
                body: { question: unrelatedQuery },
                timeoutMs: RAG_TIMEOUT_MS,

                assert: (payload, text) => ({
                    ok: /insufficient context/i.test(text),
                    detail:
                        `refusal shown=` +
                        `${/insufficient context/i.test(text)}`
                })
            }
        );

    return [
        health,
        retrieval,
        grounded,
        insufficient,
        renderedGrounded,
        renderedRefusal
    ];
}
// Release 1 - validation modes for the Student 3 observer.
// main() is shared and stays unchanged. Its parseArgs() skips flags it
// does not know, so --mode reaches this observer through process.argv.
//   base  Release 0 checks only
//   mcp   Release 0 checks + shared MCP server checks
//   rag   Release 0 checks + shared RAG server checks
//   all   both (default)

function student3ValidationMode() {

    const modes = ["base", "mcp", "rag", "all"];

    const argv = process.argv.slice(2);

    const index = argv.indexOf("--mode");

    const mode =
        index >= 0 && argv[index + 1]
            ? argv[index + 1]
            : (process.env.AGENT_MODE || "all");

    if (!modes.includes(mode)) {
        throw new Error(
            `Unknown mode: ${mode}. Use one of: ${modes.join(", ")}`
        );
    }

    return mode;
}


async function observeStudent3() {

    const mode =
        student3ValidationMode();

    console.log(
        `  Student 3 validation mode: ${mode}`
    );

    const frontend =
        await checkService(
            "Student 3 Frontend",
            STUDENT3_FRONTEND,
            {
                expectedStatuses: [200]
            }
        );

    const categories =
        await checkService(
            "Student 3 Categories",
            `${STUDENT3_DATABASE}/categories`,
            {
                expectedStatuses: [200]
            }
        );

    const expenses =
        await checkService(
            "Student 3 Expenses",
            `${STUDENT3_DATABASE}/expenses?trip_id=1`,
            {
                expectedStatuses: [200]
            }
        );

    const budget =
        await checkService(
            "Student 3 Budget",
            `${STUDENT3_DATABASE}/budgets/1`,
            {
                expectedStatuses: [200]
            }
        );

    const dashboard =
        await checkService(
            "Student 3 Dashboard",
            `${STUDENT3_BACKEND}/dashboard/1`,
            {
                expectedStatuses: [200]
            }
        );

    const configuration =
        await checkContract(
            "Student 3 Release 1 configuration",
            `${STUDENT3_BACKEND}/health`,
            {
                assert: (payload) => ({
                    ok: Boolean(
                        payload &&
                        payload.mcp_server &&
                        payload.rag_server
                    ),

                    detail:
                        `mcp=${payload && payload.mcp_server}, ` +
                        `rag=${payload && payload.rag_server}, ` +
                        `permitted_tools=${(payload &&
                            payload.allowed_mcp_tools || []).length}`
                })
            }
        );

    const mcpServices =
        mode === "mcp" || mode === "all"
            ? await observeStudent3Mcp()
            : [];

    const ragServices =
        mode === "rag" || mode === "all"
            ? await observeStudent3Rag()
            : [];

    const services = [
        frontend,
        categories,
        expenses,
        budget,
        dashboard,
        configuration,
        ...mcpServices,
        ...ragServices
    ];

    for (const service of services) {
        if (service.detail) {
            console.log(
                `  ${service.name} -> ${service.detail}`
            );
        }
    }

    const issues = services
        .filter(service => !service.ok)
        .map(service =>
            `${service.name} failed: ${service.error ||
            `HTTP ${service.status}`
            }`
        );

    return {
        student: "Student 3",
        component: `Budget & Expense Tracking (validation mode: ${mode})`,
        ok: issues.length === 0,
        services,
        issues
    };
}


async function observeStudent5() {

    const frontend =
        await checkService(
            "Student 5 Frontend",
            STUDENT5_FRONTEND,
            {
                expectedStatuses: [200]
            }
        );

    const backendHealth =
        await checkService(
            "Student 5 Backend Health",
            `${STUDENT5_BACKEND}/health`,
            {
                expectedStatuses: [200]
            }
        );

    const databaseHealth =
        await checkService(
            "Student 5 Database Health",
            `${STUDENT5_DATABASE}/health`,
            {
                expectedStatuses: [200]
            }
        );

    const documents =
        await checkService(
            "Student 5 Documents",
            `${STUDENT5_BACKEND}/api/documents`,
            {
                expectedStatuses: [200]
            }
        );

    const requirements =
        await checkService(
            "Student 5 Entry Requirements",
            `${STUDENT5_BACKEND}/api/entry-requirements`,
            {
                expectedStatuses: [200]
            }
        );

    const packingLists =
        await checkService(
            "Student 5 Packing Lists",
            `${STUDENT5_BACKEND}/api/packing-lists`,
            {
                expectedStatuses: [200]
            }
        );

    const tasks =
        await checkService(
            "Student 5 Pre-trip Tasks",
            `${STUDENT5_BACKEND}/api/pre-trip-tasks`,
            {
                expectedStatuses: [200]
            }
        );

    const agenticStatus =
        await checkService(
            "Student 5 Agentic Status",
            `${STUDENT5_BACKEND}/api/agentic/status`,
            {
                expectedStatuses: [200]
            }
        );

    const services = [
        frontend,
        backendHealth,
        databaseHealth,
        documents,
        requirements,
        packingLists,
        tasks,
        agenticStatus
    ];

    const issues = services
        .filter(service => !service.ok)
        .map(service =>
            `${service.name} failed: ${service.error ||
            `HTTP ${service.status}`
            }`
        );

    return {
        student: "Student 5",
        component: "Pre-trip Preparation",
        ok: issues.length === 0,
        services,
        issues
    };
}


async function observeStudent1() {
    return {
        student: "Student 1",
        component: "Not configured yet",
        ok: false,
        skipped: true,
        services: [],
        issues: [
            "Validation not configured yet"
        ]
    };
}

async function observeStudent2() {

    const frontend =
        await checkService(
            "Student 2 Frontend - Itinerary",
            `${STUDENT2_FRONTEND}/itinerary`,
            {
                expectedStatuses: [200]
            }
        );

    const backend =
        await checkService(
            "Student 2 Backend - Itineraries",
            `${STUDENT2_BACKEND}/itineraries`,
            {
                expectedStatuses: [200]
            }
        );

    const database =
        await checkService(
            "Student 2 Database - Itineraries",
            `${STUDENT2_DATABASE}/itineraries`,
            {
                expectedStatuses: [200]
            }
        );

    const services = [
        frontend,
        backend,
        database
    ];

    const issues = services
        .filter(service => !service.ok)
        .map(service =>
            `${service.name} failed: ${service.error ||
            `HTTP ${service.status}`
            }`
        );

    return {
        student: "Student 2",
        component: "Booking & Itinerary Management",
        ok: issues.length === 0,
        services,
        issues
    };
}












