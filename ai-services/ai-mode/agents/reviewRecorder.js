const fs = require("fs");
const path = require("path");

const REVIEW_DIR =
    path.resolve(__dirname, "../reviews");


function safeTimestamp(timestamp) {
    return timestamp
        .replaceAll(":", "-")
        .replaceAll(".", "-");
}


async function recordReview({
                                student,
                                round,
                                task,
                                observation,
                                validationEvidence,
                                implementationRecommendation,
                                review,
                                humanDecision,
                                humanNote = "",
                                carryForward = "",
                                timestamp = new Date().toISOString()
                            }) {

    if (!student) {
        throw new Error(
            "Cannot record review: student is required."
        );
    }


    const studentReviewDir =
        path.join(
            REVIEW_DIR,
            student
        );


    /*
     * Create the student's review folder
     * automatically if it does not exist.
     */
    fs.mkdirSync(
        studentReviewDir,
        {
            recursive: true
        }
    );


    const reviewRecord = {

        student,

        round,

        timestamp,

        task,

        observation,

        validationEvidence,

        implementationAgent: {
            recommendation:
            implementationRecommendation
        },

        reviewAgent: {
            review
        },

        humanReview: {
            decision:
            humanDecision,

            note:
            humanNote
        },

        carryForward
    };


    const filename =
        `review-${safeTimestamp(timestamp)}-round-${round}.json`;


    const filePath =
        path.join(
            studentReviewDir,
            filename
        );


    fs.writeFileSync(
        filePath,
        JSON.stringify(
            reviewRecord,
            null,
            2
        ),
        "utf8"
    );


    console.log(
        `Review evidence saved: ${filePath}`
    );


    return {
        filePath,
        reviewRecord
    };
}


module.exports = {
    recordReview
};