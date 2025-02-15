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
  "url": "https://example.com",
  "max_concurrent_requests": 10
}
```

**Response**

```json
{
  "status": "started",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
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
  "wikiIdentifier": "CloudCADI.wiki",
  "max_concurrent_requests": 10
}
```

**Response**

```json
{
  "status": "started",
  "task_id": "cloudcadi_cloudcadi_cloudcadi.wiki",
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

Processes and indexes document files with support for multiple formats.

**Request**

- Content-Type: multipart/form-data
- Body:
  - file: Document file (required)

**Supported File Types**

- PDF (.pdf)
- Microsoft Word (.docx)

**Success Response**

```json
{
  "status": "success",
  "message": "Document processed successfully",
  "file_name": "example.pdf",
  "chunks": 42
}
```

### Generate Agent Response

```http
POST /agent
```

Generates a streaming response for a given question using the agent.

**Request Body**

```json
{
  "question": "What is the capital of France?",
  "user_id": "user123"
}
```

**Response**

Server-Sent Events (SSE) stream with the agent's response. Each event contains a chunk of the response.

Example event:
```
data: This is a part of the response...

data: Here is another part of the response...
```

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

### 422 Unprocessable Entity

```json
{
  "error": "Validation error",
  "message": "Invalid data format"
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
- Maximum requests per window: 100

## Authentication

Authentication is required for all endpoints except the health check. API keys should be provided in the Authorization header:

```http
Authorization: Bearer <api_key>
```
