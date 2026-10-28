# Student-05 Multi-Agent Feature: Screen Recording Guide

Approximate length: 2–3 minutes. Start the local Ollama service, Multi-Agent Server, Student-05 backend and frontend before recording. Keep the Multi-Agent Server terminal visible briefly so its local service is clear. The dashboard is served on port 8505 by default.

## Walkthrough and voice-over

| Screen action | Voice-over |
| --- | --- |
| Open the Student-05 dashboard and show its title and navigation. | “This is Student-05, the Travel Preparation and Compliance Microservice. I’m going to show how its shared local Multi-Agent Server reviews travel preparation evidence, then pauses for a human decision.” |
| Click **Multi-Agent Review**. Point out the mode selector, task and evidence fields. | “The review panel is part of the integrated Student-05 UI. The frontend sends the request through the Student-05 Flask API to the shared non-containerised server. The server supports workflow, testing report and cloud deployment report reviews.” |
| Leave **Multi-Agent Workflow Review** selected. Enter this in **Evidence or report**: `Student-05 stores travel documents, checks them against demonstration entry requirements, flags expiry and missing-document issues, and generates packing lists and pre-trip tasks. A traveller can review and accept AI suggestions before they are saved. The dashboard exposes the workflow through the integrated backend and frontend. Entry requirement data is demonstration data and must be verified with government sources.` Then click **Run Planner → Worker → Reviewer**. | “For this run, I’m asking the agents to review the travel preparation workflow. I’ve provided feature evidence and included the limitation that entry requirements are demonstration data.” |
| While the result loads, optionally show the local server terminal. Return to the completed result and point out each agent’s output. | “The Planner breaks down the review, the Worker assesses the supplied evidence, and the Reviewer checks the result. The service returns the three outputs to the dashboard and waits for a human decision.” |
| Read the result, optionally add a short note such as `Reviewed in the Student-05 dashboard demo.`, then click **Accept**, **Partially Accept**, or **Reject**. | “The human remains in the loop. After reviewing the agent outputs, I’m submitting [say the choice you made]. This records my decision for this workflow.” |
| Show the confirmation/result. Finish on the panel or dashboard. | “That completes a Student-05 workflow review through the shared Planner, Worker and Reviewer service, with a human decision submitted from the UI. The same panel can review testing reports and cloud deployment reports.” |

## Recording notes

- Use real service output in the recording; model responses and wait time can vary.
- Keep the service terminal free of secrets or unrelated personal information.
- If the request fails, check that Ollama and the Multi-Agent Server are running and that the Student-05 backend can reach `http://127.0.0.1:7010`.
- Workflow state in the UI server is held in memory and is cleared when that server restarts.
- Only say the human decision was accepted if the confirmation appears on screen. The service records the selected decision; it does not independently validate the underlying travel rules.
