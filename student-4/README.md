## Student 4 - Testing Instructions

Student 4's Plan Itinerary component uses the Groq API to generate itineraries.

The Groq API key is not committed to GitHub for security reasons.

### Student 4 environment setup

Create the Student 4 backend environment file:

cp student-4/backend/.env.example student-4/backend/.env

Then add the required API key to:

student-4/backend/.env



### 1. Configure the Groq API key

The `.env` file is not included in the repository because it contains a private API key.

From the project root, create the Student 4 backend `.env` file by running:

```bash
cp student-4/backend/.env.example student-4/backend/.env
```

Then open:

```text
student-4/backend/.env
```

and replace the placeholder with your own Groq API key:

```env
GROQ_API_KEY=your_actual_groq_api_key
```

A valid Groq API key is required for itinerary generation.

Do not commit the `.env` file.

To generate a Groq API key:
open https://groq.com/
navigate to Start Building Option (or simply opem, https://console.groq.com/home?utm_source=website&utm_medium=outbound_link&utm_campaign=dev_console_click&_gl=1*1n4q29l*_gcl_au*Nzk5NTIyNTk5LjE3ODcyNzMyMTM.*_ga*Nzc0MDk5NDk3LjE3Nzg3NTE4MDU.*_ga_4TD0X2GEZG*czE3ODg4MzYyNzAkbzE0JGcwJHQxNzg4ODM2MjcwJGo2MCRsMCRoMA..)
You will be able to generate the API key.




### 2. Start the application

From the project root:

```bash
docker compose up -d --build
```

### 3. Start the local RAG and MCP servers

Student 4's RAG assistant and MCP integration depend on two local services that are not started by the Student 4 Docker Compose application:

- RAG server on port `7001`
- MCP server on port `7004`

Start both services before testing the Student 4 RAG page or MCP integration page.

In a new terminal, start the RAG server from the project root:

```bash
cd rag-server
python3 rag_http_server.py
```

The RAG server should be available at:

```text
http://127.0.0.1:7001
```

In another terminal, start the MCP server from the project root:

```bash
cd ai-services/mcp-server
python3 http_server.py
```

The MCP server should be available at:

```text
http://127.0.0.1:7004
```

To confirm the MCP server is running:

```bash
curl -s http://127.0.0.1:7004/mcp/tools
```

### 4. Open the application

Shared application:

```text
http://localhost:8080
```

Student 4 directly:

```text
http://localhost:3004
```

### 5. Test the Plan Itinerary component

1. Open the Plan Itinerary page.
2. Enter destination and travel preferences.
3. Select cities.
4. Generate itinerary options.
5. Select an itinerary.
6. Review/refine the itinerary.
7. Save the itinerary.

### 6. Test the Development Agentic AI Loop

From the project root:

```bash
node ai-services/ai-mode/agents/agenticLoop.js \
  --student student-4 \
  --task "Validate Student 4 Plan Itinerary microservice"
```

### 7. Test Student 4 RAG integration

Student 4 uses the shared RAG server to answer questions about saved itineraries. Before testing Student 4's RAG page, refresh the RAG corpus so the RAG server regenerates the latest Student 4 chunks from the Student 4 database.

Make sure the RAG server is running on port `7001`, then run:

```bash
curl -X POST http://127.0.0.1:7001/rag/refresh \
  -H "Content-Type: application/json" \
  -d '{}'
```

This rebuilds `rag-server/corpus/corpus.jsonl` and refreshes the Chroma vector store. It is required after saving, deleting, or changing Student 4 itineraries; otherwise, the RAG server may answer using stale Student 4 chunks.

To test retrieval directly:

```bash
curl -X POST http://127.0.0.1:7001/rag/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "In itinerary ID 3, what activities is the user doing?",
    "k": 5
  }'
```

To test the generated RAG answer:

```bash
curl -X POST http://127.0.0.1:7001/rag/answer \
  -H "Content-Type: application/json" \
  -d '{
    "query": "In itinerary ID 3, what activities is the user doing?",
    "k": 5
  }'
```
