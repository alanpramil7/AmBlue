# API Documentation

## Endpoints

### Health Check

```http
GET /check-health
```

Returns the current status and version of the service.

**Response**

```json
{
  "status": "Healthy",
  "version": "0.1"
}
```

### Process Website

```http
POST /website
```

Initiates asynchronous processing of a website's content.

**Request Body**

```json
{
  "url": "https://example.com"
}
```

**Response**

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Website processing started"
}
```

### Get Website Processing Status

```http
GET /website/{task_id}/status
```

Returns the current status of a website processing task.

**Response**

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "in_progress",
  "total_urls": 100,
  "processed_urls": ["https://example.com/page1", "https://example.com/page2"],
  "remaining_urls": ["https://example.com/page3"],
  "failed_urls": [],
  "current_url": "https://example.com/page3",
  "percent_complete": 66.67,
  "error": null
}
```

### Process Wiki

```http
POST /wiki
```

Initiates asynchronous processing of an Azure DevOps wiki.

**Request Body**

```json
{
  "organization": "cloudcadi",
  "project": "CloudCADI",
  "wikiIdentifier": "CloudCADI.wiki"
}
```

**Response**

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Wiki processing started"
}
```

### Get Wiki Processing Status

```http
GET /wiki/{task_id}/status
```

Returns the current status of a wiki processing task.

**Response**

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "in_progress",
  "total_pages": 50,
  "processed_pages": ["/Home", "/Getting-Started"],
  "remaining_pages": ["/API-Reference"],
  "failed_pages": [],
  "current_page": "/API-Reference",
  "percent_complete": 80.0,
  "error": null
}
```

### Process Document

```http
POST /document
```

Processes and indexes document files with support for multiple formats and concurrent processing.

**Request**

- Content-Type: multipart/form-data
- Body:
  - file: Document file (required)
  - metadata: Additional document metadata (optional)

**Supported File Types**

- PDF (.pdf)
- Microsoft Word (.docx)

**Processing Features**

- Concurrent processing (max 5 simultaneous)
- Automatic format detection
- Content chunking
- Vector embedding generation
- Progress tracking

**Success Response**

```json
{
  "status": "success",
  "message": "Document processed successfully",
  "file_name": "example.pdf",
  "chunks": 42
}
```

**Error Responses**

1. Invalid File Format
```json
{
  "error": "Invalid file format",
  "message": "Unsupported file format: txt. Supported formats are: pdf, docx",
  "code": "INVALID_FORMAT"
}
```

2. Processing Error
```json
{
  "error": "Processing failed",
  "message": "Failed to process document: detailed error message",
  "code": "PROCESSING_ERROR"
}
```

3. File Size Error
```json
{
  "error": "File too large",
  "message": "Document exceeds maximum allowed size",
  "code": "SIZE_LIMIT_EXCEEDED"
}
```

**Processing Pipeline**

1. File Upload
   - Format validation
   - Size verification
   - Temporary storage

2. Document Processing
   - Content extraction
   - Text normalization
   - Chunk generation

3. Indexing
   - Embedding generation
   - Vector storage
   - Metadata indexing

**Notes**

- Maximum file size: 10MB
- Processing timeout: 5 minutes
- Concurrent processing limit: 5 files
- Supported languages: All (UTF-8 encoding)

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request

```json
{
  "error": "Invalid request",
  "message": "Detailed error message"
}
```

### 404 Not Found

```json
{
  "error": "Not found",
  "message": "Resource not found"
}
```

### 500 Internal Server Error

```json
{
  "error": "Internal server error",
  "message": "An unexpected error occurred"
}
```

## Rate Limiting

All endpoints are subject to rate limiting:

- Maximum concurrent requests per client: 10
- Rate limit window: 1 minute
- Rate limit: 100 requests per minute

When rate limited, the API will respond with:

### 429 Too Many Requests

```json
{
  "error": "Rate limit exceeded",
  "message": "Too many requests, please try again in X seconds"
}
```

### Agent Response Generation

```http
POST /agent/query
```

Streams a response to a user query using RAG-based question answering.

**Request Body**

```json
{
  "query": "What are the key features of the system?",
  "user_id": "user-123"
}
```

**Response**

Streams chunks of text as Server-Sent Events (SSE):

```text
data: Based on the available documentation,
data: the system has several key features including:
data: 1. Website content processing with sitemap support
data: 2. Azure DevOps Wiki integration
data: 3. Document processing for PDF and DOCX files
...
```

**Features**

- Real-time response streaming
- Context-aware answers using RAG
- User session management
- Think-tag filtering
- Error recovery

### Health Check

```http
POST /agent
```

Generates a streaming response for a given question using the RAG agent.

**Request Body**

```json
{
  "question": "What is the capital of France?"
}
```

**Response**

- Content-Type: text/event-stream
- Streaming response with Server-Sent Events (SSE)

Example event:

```text
data: The capital of France is Paris.
```

## Error Responses

| Status Code | Description                               |
| ----------- | ----------------------------------------- |
| 400         | Bad Request - Invalid parameters          |
| 404         | Not Found                                 |
| 422         | Unprocessable Entity - Invalid URL format |
| 500         | Internal Server Error                     |
