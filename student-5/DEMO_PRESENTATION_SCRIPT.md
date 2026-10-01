# Student-5 Feature Demonstration Script

## Before starting

Open the application at:

```text
http://127.0.0.1:8505/
```

Have the database, backend, and frontend services running. The default demo values use traveller `traveller-001`, trip `trip-001`, destination `Japan`, and nationality `Australian`.

## Opening

"This is the Student-5 travel preparation application. It helps a traveller check their travel documents, review destination entry requirements, identify compliance issues, create packing and pre-trip checklists, and monitor progress before departure.

The application is divided into five main areas: Documents, Compliance, Entry Requirements, Packing, and Pre-Trip Tasks. The final tab brings these activities together in a Plan, Act, Observe, and Adapt workflow."

## 1. Documents

Click the **Documents** tab.

"I will start with travel documents. The application stores important document information such as the document type, issuing country, nationality, issue date, and expiry date.

The existing records are displayed in a table. Document numbers are masked, so sensitive information is not shown in full. The status also highlights whether a document is valid, expiring, or expired.

I can add a new document using this form. After submitting it, the document appears in the table and its status is calculated from the expiry date. Documents can also be deleted when they are no longer needed."

## 2. Entry requirements

Click the **Entry Requirements** tab.

"Next, I can review the demonstration entry requirements for a destination and traveller nationality. I can filter the list by destination and nationality.

These requirements are stored as structured records, including the requirement type, document type, description, minimum validity period, and whether the requirement is mandatory.

This release uses demonstration data only. Official government sources must always be checked before real travel."

## 3. Compliance check

Click the **Compliance** tab.

"The compliance feature compares the traveller's documents with the selected destination requirements.

I will use the default trip details: Japan, Australian nationality, and the departure and return dates shown here. When I click the compliance button, the application checks for missing, expired, or soon-to-expire documents and returns recommended actions.

The result is based on the stored data, and the AI explanation is kept separate from the deterministic compliance result. This makes the result easier to review and helps prevent unsupported requirements from being invented."

## 4. Packing and AI checklist generation

Click the **Packing** tab.

"The Packing section can generate a personalised checklist using the destination, trip dates, climate, and planned activities.

For this example, the planned activities are hiking and a business meeting. The generated results include packing items, quantities, categories, pre-trip tasks, due dates, priorities, and a reason for each recommendation.

The suggestions are shown for review first. They are not saved automatically. This gives the traveller the opportunity to reject or change recommendations before accepting them."

If Ollama is running, click **Generate Packing & Pre-Trip Checklist**.

"The AI has now produced suggestions based on the trip details. I can review the reason for each item and then choose to save the approved checklist."

If Ollama is not running, say:

"The AI generation endpoint is available, but this demonstration environment does not currently have the local Ollama model running. The rest of the application remains available, including stored packing lists, task tracking, and compliance alerts."

## 5. Saved packing lists

Scroll to **Saved packing lists** in the Packing tab.

"Once a checklist is accepted, it appears in the saved packing lists section. Each item has a category, quantity, and source indicator showing whether it was AI-generated or added manually.

I can mark items as complete using the checkboxes or add a custom item. The progress count updates as items are completed."

## 6. Pre-trip tasks

Click the **Pre-Trip Tasks** tab.

"Pre-trip tasks are tracked separately from packing items. I can add a task, description, due date, and priority.

Tasks can be marked complete or deleted, and the application displays the overall completed-versus-total progress. This helps the traveller see what still needs to be done before departure."

## 7. Agentic workflow

Click **Plan - Act - Observe - Adapt**.

"The final section combines the features into an agentic preparation workflow.

Plan uses the trip details, documents, and entry requirements to identify compliance issues and produce recommendations.

Act represents the traveller reviewing suggestions, saving approved checklists, updating documents, and completing tasks.

Observe monitors document expiry, missing documents, packing progress, task progress, and the number of days until departure.

Adapt recommends the next action when something changes, such as rerunning the compliance check after a document is updated or regenerating the checklist when the trip details change.

This is more than a static checklist because the displayed status is calculated from the current travel data and progress."

## Closing

"To summarise, this application provides one workflow for preparing a trip. It protects document numbers in the interface, compares documents against demonstration entry requirements, identifies compliance alerts, generates explainable AI suggestions, requires review before saving AI output, and tracks both packing and pre-trip progress.

The user interface runs on port 8505. The backend API runs on port 5505, and the database API runs on port 5405. Port 5405 is intended to return JSON data; the application screen is the one currently being demonstrated at port 8505."

## Optional command-line proof

From the repository root, the read-only command-line demo can also be run:

```bash
python student-5/demo_features.py
```

To include the Ollama-backed features:

```bash
python student-5/demo_features.py --ai
```
