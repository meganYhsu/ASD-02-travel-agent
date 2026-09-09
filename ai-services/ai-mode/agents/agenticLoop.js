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


const STUDENT5_FRONTEND =
    process.env.STUDENT5_FRONTEND_URL ||
    "http://localhost:8505";

const STUDENT5_BACKEND =
    process.env.STUDENT5_BACKEND_URL ||
    "http://localhost:5505";

const STUDENT5_DATABASE =
    process.env.STUDENT5_DATABASE_URL ||
    "http://localhost:5405";






// const PLAN = {
//     goal:
//         "Validate the integrated Travel Agent application before release",
//
//     actions: [
//         "Check all student microservices are reachable",
//         "Check critical backend and database endpoints",
//         "Check frontend/backend integration",
//         "Check Docker Compose configuration",
//         "Check GitHub Actions workflows",
//         "Identify verified integration issues"
//     ]
// };

// function buildEvidenceText(observation) {
//
//     const students = [
//         observation.student1,
//         observation.student2,
//         observation.student3,
//         observation.student4,
//         observation.student5
//     ];
//
//     const lines = [
//         "INTEGRATED TRAVEL AGENT VALIDATION",
//         ""
//     ];
//
//     for (const student of students) {
//
//         let status;
//
//         if (student.skipped) {
//             status = "NOT CONFIGURED";
//         } else {
//             status = student.ok ? "PASS" : "FAIL";
//         }
//
//         lines.push(
//             `${student.student}: ${status}`
//         );
//
//         if (student.issues.length > 0) {
//             for (const issue of student.issues) {
//                 lines.push(`- ${issue}`);
//             }
//         }
//
//         lines.push("");
//     }
//
//     return lines.join("\n");
// }


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
       BUILD EVIDENCE FOR ONE STUDENT
    ========================================================= */

    // function buildStudentEvidenceText(
    //     observation
    // ) {
    //
    //     const lines = [
    //         "TRAVEL AGENT DEVELOPMENT VALIDATION",
    //         "",
    //         `Student: ${observation.student}`,
    //         `Component: ${observation.component}`,
    //         "",
    //         `Overall status: ${
    //             observation.ok
    //                 ? "PASS"
    //                 : observation.skipped
    //                     ? "NOT CONFIGURED"
    //                     : "FAIL"
    //         }`,
    //         ""
    //     ];
    //
    //
    //     for (
    //         const service of
    //     observation.services || []
    //         ) {
    //
    //         lines.push(
    //             `${service.name}: ${
    //                 service.ok
    //                     ? "PASS"
    //                     : "FAIL"
    //             }`
    //         );
    //
    //
    //         lines.push(
    //             `URL: ${service.url}`
    //         );
    //
    //
    //         if (
    //             service.status !== null &&
    //             service.status !== undefined
    //         ) {
    //             lines.push(
    //                 `HTTP status: ${service.status}`
    //             );
    //         }
    //
    //
    //         if (service.error) {
    //             lines.push(
    //                 `Error: ${service.error}`
    //             );
    //         }
    //
    //
    //         lines.push("");
    //     }
    //
    //
    //     if (
    //         observation.issues?.length > 0
    //     ) {
    //
    //         lines.push(
    //             "VERIFIED ISSUES:"
    //         );
    //
    //
    //         for (
    //             const issue of
    //             observation.issues
    //             ) {
    //             lines.push(
    //                 `- ${issue}`
    //             );
    //         }
    //
    //     } else {
    //
    //         lines.push(
    //             "VERIFIED ISSUES: none"
    //         );
    //     }
    //
    //
    //     return lines.join("\n");
    // }


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



// main().catch((error) => {
//
//     console.error(
//         "Shared agentic loop failed:",
//         error
//     );
//
//     process.exit(1);
// });

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




// async function checkService(
//     name,
//     url,
//     {
//         method = "GET",
//         body,
//         expectedStatuses = [200]
//     } = {}
// ) {
//     try {
//
//         const response = await fetch(url, {
//             method,
//
//             headers: {
//                 "Content-Type": "application/json"
//             },
//
//             body:
//                 body === undefined
//                     ? undefined
//                     : JSON.stringify(body),
//
//             signal: AbortSignal.timeout(5000)
//         });
//
//         return {
//             name,
//             url,
//             reachable: true,
//             status: response.status,
//
//             ok:
//                 expectedStatuses.includes(
//                     response.status
//                 )
//         };
//
//     } catch (error) {
//
//         return {
//             name,
//             url,
//             reachable: false,
//             status: null,
//             ok: false,
//             error: error.message
//         };
//     }
// }

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
            `${service.name} failed: ${
                service.error ||
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



async function observeStudent3() {

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

    const services = [
        frontend,
        categories,
        expenses,
        budget,
        dashboard
    ];

    const issues = services
        .filter(service => !service.ok)
        .map(service =>
            `${service.name} failed: ${
                service.error ||
                `HTTP ${service.status}`
            }`
        );

    return {
        student: "Student 3",
        component: "Budget & Expense Tracking",
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
            `${service.name} failed: ${
                service.error ||
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
    return {
        student: "Student 2",
        component: "Not configured yet",
        ok: false,
        skipped: true,
        services: [],
        issues: [
            "Validation not configured yet"
        ]
    };
}












