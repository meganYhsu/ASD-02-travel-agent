const fs = require("fs");
const path = require("path");
const readline = require("readline/promises");

const { getImplementationAdvice } = require("./implementationAgent");
const { getReview } = require("./reviewAgent");


// Human review
async function askHumanDecision(rl) {
    console.log("\nADAPT - Human Review");
    console.log("1. Accept");
    console.log("2. Partially Accept");
    console.log("3. Reject");

    const choice = await rl.question("Select 1, 2 or 3: ");
    const note = await rl.question("Human review note: ");

    if (choice === "1") {
        return {
            decision: "Accept",
            note
        };
    }

    if (choice === "2") {
        return {
            decision: "Partially Accept",
            note
        };
    }

    return {
        decision: "Reject",
        note
    };
}


// Read one section from request.txt
function readSection(text, sectionName) {
    const lines = text.split(/\r?\n/);

    let collecting = false;
    const result = [];

    for (const line of lines) {

        if (line.trim() === `${sectionName}:`) {
            collecting = true;
            continue;
        }

        if (
            collecting &&
            /^[A-Za-z ]+:$/.test(line.trim())
        ) {
            break;
        }

        if (collecting && line.trim()) {
            result.push(line.trim());
        }
    }

    return result;
}


// Read request.txt
function loadRequest(student) {

    const promptDir = path.join(
        __dirname,
        "prompts",
        `student-${student}`
    );

    const requestFile = path.join(
        promptDir,
        "request.txt"
    );

    if (!fs.existsSync(requestFile)) {
        throw new Error(
            `request.txt not found: ${requestFile}`
        );
    }

    const requestText = fs.readFileSync(
        requestFile,
        "utf8"
    );

    const feature = readSection(
        requestText,
        "Feature"
    ).join(" ");

    const objective = readSection(
        requestText,
        "Review objective"
    ).join(" ");

    const codeFiles = readSection(
        requestText,
        "Code files"
    );

    const reviewFocus = readSection(
        requestText,
        "Review focus"
    );


    if (codeFiles.length === 0) {
        throw new Error(
            "No code files were found in request.txt"
        );
    }


    return {
        promptDir,
        requestFile,
        requestText,
        feature,
        objective,
        codeFiles,
        reviewFocus
    };
}


// Read all code files and create evidence
function buildEvidence(codeFiles) {

    let evidence = "";

    const projectRoot = path.resolve(
        __dirname,
        "..",
        ".."
    );


    for (const file of codeFiles) {

        const cleanFile = file.replace(
            /^[-*]\s*/,
            ""
        );

        const filePath = path.resolve(
            projectRoot,
            cleanFile
        );


        if (!fs.existsSync(filePath)) {

            console.log(
                `Warning: file not found -> ${cleanFile}`
            );

            continue;
        }


        const fileContent = fs.readFileSync(
            filePath,
            "utf8"
        );

        console.log(
            `Loaded: ${cleanFile} (${fileContent.length} characters)`
        );


        evidence +=
            `\n===== FILE: ${cleanFile} =====\n\n`;

        evidence += fileContent;

        evidence +=
            "\n\n====================================\n";
    }


    if (!evidence.trim()) {
        throw new Error(
            "No source code evidence could be loaded."
        );
    }


    return evidence;
}


// Save review record
function saveRecord(
    student,
    feature,
    task,
    codeFiles,
    records
) {

    const outputDir = path.join(
        __dirname,
        "review-records"
    );

    if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(
            outputDir,
            { recursive: true }
        );
    }


    let output = "";

    output +=
        "Development Agentic AI Review Record\n";

    output +=
        "===================================\n";

    output += `Student: ${student}\n`;
    output += `Feature: ${feature}\n\n`;

    output +=
        "Workflow: Plan -> Act -> Observe -> Adapt\n\n";


    output += "Reviewed code files:\n";

    for (const file of codeFiles) {
        output += `- ${file}\n`;
    }

    output += "\n";


    for (const record of records) {

        output +=
            `Cycle ${record.cycle}\n`;

        output +=
            "-----------------------------------\n\n";


        output += "PLAN\n";
        output += `${task}\n\n`;


        output +=
            "ACT - Implementation Agent\n";

        output +=
            `${record.implementation}\n\n`;


        output +=
            "OBSERVE - Review Agent\n";

        output +=
            `${record.review}\n\n`;


        output +=
            "ADAPT - Human Decision\n";

        output +=
            `Decision: ${record.decision}\n`;

        output +=
            `Human Note: ${record.note || "None"}\n\n`;
    }


    const filename =
        `student-${student}-review-record.txt`;

    const outputPath = path.join(
        outputDir,
        filename
    );


    fs.writeFileSync(
        outputPath,
        output,
        "utf8"
    );


    return outputPath;
}


// Shared agentic loop
async function main() {

    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout
    });


    console.log(
        "\nTravel Agent Development Agentic Loop\n"
    );


    const student =
        await rl.question("Student number: ");


    // ==========================================
    // PLAN
    // ==========================================

    const request = loadRequest(
        student.trim()
    );


    const evidence =
        buildEvidence(
            request.codeFiles
        );


    const task = `
Review objective:
${request.objective}

Review focus:
${request.reviewFocus.join("\n")}
`.trim();


    console.log("\nPLAN");

    console.log(
        `Student: ${student}`
    );

    console.log(
        `Feature: ${request.feature}`
    );

    console.log(
        `Review objective: ${request.objective}`
    );


    console.log("\nReview focus:");

    for (const focus of request.reviewFocus) {
        console.log(focus);
    }


    console.log("\nCode files:");

    for (const file of request.codeFiles) {
        console.log(file);
    }


    let carryForward = "";
    let cycle = 1;

    const records = [];


    while (true) {

        console.log(
            `\n--- Cycle ${cycle} ---`
        );


        // ==========================================
        // ACT
        // ==========================================

        console.log(
            "\nACT - Implementation Agent"
        );


        const implementation =
            await getImplementationAdvice({
                task,
                evidence,
                carryForward,
                promptDir: request.promptDir
            });


        if (implementation.error) {

            console.log(
                "Implementation Agent error: " +
                implementation.error
            );

            break;
        }


        console.log(
            implementation.content
        );


        // ==========================================
        // OBSERVE
        // ==========================================

        console.log(
            "\nOBSERVE - Review Agent"
        );


        const review =
            await getReview({
                task,

                implementationRecommendation:
                    implementation.content,

                evidence,

                promptDir:
                    request.promptDir
            });


        if (review.error) {

            console.log(
                "Review Agent error: " +
                review.error
            );

            break;
        }


        console.log(
            review.content
        );


        // ==========================================
        // ADAPT
        // ==========================================

        const human =
            await askHumanDecision(rl);


        records.push({
            cycle,
            implementation:
                implementation.content,
            review:
                review.content,
            decision:
                human.decision,
            note:
                human.note
        });


        if (
            human.decision === "Accept"
        ) {
            break;
        }


        if (
            human.decision === "Reject"
        ) {
            break;
        }


        carryForward =
            human.note;


        console.log(
            "\nAdaptation feedback will be carried to the next cycle."
        );


        cycle++;
    }


    if (records.length > 0) {

        const savedFile =
            saveRecord(
                student,
                request.feature,
                task,
                request.codeFiles,
                records
            );


        console.log(
            "\nReview record saved: " +
            savedFile
        );
    }


    rl.close();
}


// Run loop
main().catch(error => {
    console.error(
        "Agentic loop failed:",
        error
    );
});