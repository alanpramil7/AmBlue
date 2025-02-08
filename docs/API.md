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

Processes and indexes the content of a specified website.

**Request Body**

```json
{
  "url": "https://example.com"
}
```

**Response**

```json
{
  "status": "success",
  "message": "Website https://example.com has been processed"
}
```

### Process Wiki

```http
POST /wiki
```

Processes and indexes content from an Azure DevOps wiki.

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
  "status": "success",
  "total_documents_processed": 42
}
```

### Process Document

```http
POST /document
```

Processes and indexes document files (PDF, DOCX).

**Request**

- Content-Type: multipart/form-data
- Body:
  - file: Document file (PDF or DOCX)

**Response**

```json
{
  "message": "Document processed successfully",
  "file_name": "example.pdf",
  "chunks": 42
}
```

**Supported File Types**

- PDF (.pdf)
- Microsoft Word (.docx)

## Error Responses

| Status Code | Description                               |
| ----------- | ----------------------------------------- |
| 400         | Bad Request - Invalid parameters          |
| 404         | Not Found                                 |
| 422         | Unprocessable Entity - Invalid URL format |
| 500         | Internal Server Error                     |
