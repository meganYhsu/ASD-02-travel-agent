async function checkService(
    name,
    url,
    {
        method = "GET",
        body,
        expectedStatuses = [200],
        timeout = 5000
    } = {}
) {

    try {

        const response =
            await fetch(
                url,
                {
                    method,

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        body === undefined
                            ? undefined
                            : JSON.stringify(body),

                    signal:
                        AbortSignal.timeout(
                            timeout
                        )
                }
            );


        return {

            name,

            url,

            reachable: true,

            status:
            response.status,

            ok:
                expectedStatuses.includes(
                    response.status
                ),

            error: ""
        };


    } catch (error) {

        return {

            name,

            url,

            reachable: false,

            status: null,

            ok: false,

            error:
                error instanceof Error
                    ? error.message
                    : String(error)
        };
    }
}



function buildStudentEvidenceText(
    observation
) {

    const lines = [

        "TRAVEL AGENT DEVELOPMENT VALIDATION",

        "",

        `Student: ${observation.student}`,

        `Component: ${observation.component}`,

        "",

        `Overall status: ${
            observation.ok
                ? "PASS"
                : observation.skipped
                    ? "NOT CONFIGURED"
                    : "FAIL"
        }`,

        ""
    ];


    for (
        const service of
    observation.services || []
        ) {

        lines.push(
            `${service.name}: ${
                service.ok
                    ? "PASS"
                    : "FAIL"
            }`
        );


        lines.push(
            `URL: ${service.url}`
        );


        if (
            service.status !== null &&
            service.status !== undefined
        ) {

            lines.push(
                `HTTP status: ${service.status}`
            );
        }


        if (service.error) {

            lines.push(
                `Error: ${service.error}`
            );
        }


        lines.push("");
    }


    if (
        observation.issues &&
        observation.issues.length > 0
    ) {

        lines.push(
            "VERIFIED ISSUES:"
        );


        for (
            const issue of
            observation.issues
            ) {

            lines.push(
                `- ${issue}`
            );
        }

    } else {

        lines.push(
            "VERIFIED ISSUES: none"
        );
    }


    return lines.join("\n");
}



module.exports = {
    checkService,
    buildStudentEvidenceText
};