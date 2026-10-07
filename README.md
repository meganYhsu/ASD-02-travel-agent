Refer to Student-4's readme.md file for the instructions to run and dockerise complete application. As it might require a different way to set up.

credentials to log in the web app:
username:traveler
password:travel123

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

### 7. Test Student 4 RAG integration

Student 4 uses the shared RAG server to answer questions about saved itineraries. Before testing Student 4's RAG page, refresh the RAG corpus so the RAG server regenerates the latest Student 4 chunks from the Student 4 database.

Important: refresh RAG before testing Student 4's RAG integration. Student 4 itinerary data is now converted into a newer structured chunk format, including itinerary summary chunks, activity index chunks, individual activity chunks, and day schedule chunks. Refreshing RAG regenerates these Student 4 chunks and updates the vector store; without this step, the RAG server may still use old or stale Student 4 chunks.

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
