# Services Documentation

## IndexerService

The IndexerService manages document processing, embedding generation, and vector storage operations.

### Components

1. **Embedding Model**

   - Implementation: Ollama's nomic-embed-text model
   - Purpose: Converts text documents into vector embeddings
   - Configuration:
     - Model name: nomic-embed-text
     - Dimensions: 768

2. **Text Splitter**

   - Configuration:
     - Chunk size: 1000 characters
     - Overlap: 200 characters
     - Separators: ["\n\n", "\n", " ", ""]
   - Features:
     - Intelligent splitting based on content structure
     - Maintains context across chunks
     - Preserves document integrity

3. **Vector Store**
   - Implementation: ChromaDB
   - Features:
     - Persistent storage
     - Efficient vector search
     - Metadata support
   - Configuration:
     - Telemetry: Disabled
     - Storage path: ./data/chroma

### Key Methods

- `initialize()`

  - Purpose: Sets up all components for indexing
  - Returns: Boolean indicating success
  - Error handling: Logs failures and returns False

- `_setup_embedding_model()`

  - Purpose: Initializes Ollama embeddings
  - Configuration: Uses environment variables
  - Validation: Checks model availability

- `_setup_text_splitter()`

  - Purpose: Configures document splitting
  - Parameters: Customizable chunk size and overlap
  - Returns: Configured RecursiveCharacterTextSplitter

- `_setup_vector_store()`
  - Purpose: Initializes ChromaDB
  - Configuration: Sets up persistent storage
  - Error handling: Handles initialization failures

## WebsiteService

Handles website content processing and indexing operations.

### Features

- Comprehensive sitemap crawling
- URL validation and normalization
- Content extraction and processing
- Error handling and retry logic

### Key Methods

- `index_website(url: str)`

  - Purpose: Main entry point for website indexing
  - Parameters: Website URL
  - Returns: Processing status and statistics

- `_fetch_sitemap(url: str)`

  - Purpose: Retrieves and parses website sitemap
  - Returns: List of URLs to process
  - Error handling: Handles missing/invalid sitemaps

- `_process_url(url: str)`
  - Purpose: Processes individual webpage content
  - Features:
    - Content extraction
    - HTML cleaning
    - Metadata collection

### Error Handling

- Comprehensive error logging
- Network timeout handling
- Invalid URL detection
- Rate limiting consideration

## WikiService

Handles Azure DevOps wiki content retrieval and processing.

### Components

1. **WikiClient**

   - Purpose: Interacts with Azure DevOps Wiki REST API
   - Features:
     - Authentication handling
     - Page tree navigation
     - Content retrieval
     - Error management

2. **WikiPage Data Model**
   - Attributes:
     - page_path: Full path in repository
     - content: Markdown/text content
     - remote_url: External URL (optional)

### Key Methods

- `fetch_wiki_pages(organization, project, wiki_identifier)`

  - Purpose: Main entry point for wiki content retrieval
  - Parameters:
    - organization: Azure DevOps org name
    - project: Project name
    - wiki_identifier: Wiki repository ID
  - Returns: List of WikiPage objects or None
  - Authentication: Uses WIKI_ACCESS_TOKEN environment variable

- `_get_wiki_tree()`

  - Purpose: Retrieves complete wiki structure
  - Features:
    - Recursive page retrieval
    - Full tree traversal
    - Content inclusion

- `_flatten_pages(page)`
  - Purpose: Converts hierarchical wiki structure to flat list
  - Features:
    - Recursive processing
    - Content extraction
    - Metadata preservation

### Error Handling

- Custom WikiClientError exception
- Detailed error logging
- API request failure handling
- Authentication validation

### Integration Points

- Combines with IndexerService for content embedding
- Supports FastAPI routes for wiki processing
- Integrates with vector store for content storage

### Configuration

- API Version: 7.1
- Environment Variables:
  - WIKI_ACCESS_TOKEN: Required for authentication
- Logging: Detailed operation logging with multiple levels

### Performance Considerations

- Batch processing capabilities
- Efficient recursive traversal
- Content caching where appropriate
- Error recovery mechanisms

## DocumentService

Handles document file processing and indexing operations.

### Features

- Support for multiple document formats (PDF, DOCX)
- Automatic content extraction
- Document chunking and processing
- Vector store integration

### Supported File Types

1. **PDF Files**

   - Implementation: PyPDFLoader
   - Features:
     - Text extraction
     - Multi-page support
     - Metadata preservation

2. **Microsoft Word Documents**
   - Implementation: Docx2txtLoader
   - Features:
     - Text content extraction
     - Format preservation
     - Error handling

### Key Methods

- `process_document(file: UploadFile)`

  - Purpose: Main entry point for document processing
  - Parameters: Uploaded file object
  - Returns: Processing status and statistics
  - Features:
    - Async file handling
    - Temporary file management
    - Error handling

- `_create_document(file_path: str)`

  - Purpose: Creates document objects from files
  - Parameters: File path
  - Returns: List of Document objects
  - Features:
    - Format detection
    - Appropriate loader selection
    - Error validation

- `index_document(file_path: str)`
  - Purpose: Processes and indexes document content
  - Parameters: File path
  - Returns: Processing results with metrics
  - Features:
    - Document splitting
    - Vector store integration
    - Status tracking

### Error Handling

- Format validation
- File integrity checks
- Comprehensive error logging
- Clean temporary file management

## AgentService

Manages the integration between document retrieval and LLM-powered response generation using LangGraph.

### Components

1. **State Graph**

   - Implementation: LangGraph StateGraph
   - Purpose: Manages conversation flow and LLM interactions
   - Features:
     - Checkpointing with MemorySaver
     - Structured message handling
     - Async streaming support

2. **Language Model**
   - Implementation: Groq/Ollama integration
   - Models:
     - Primary: deepseek-r1-distill-llama-70b
     - Alternative: deepseek-r1:14b
   - Features:
     - Streaming response generation
     - Context-aware responses
     - State management

### Key Methods

- `stream_response(user_input: str)`

  - Purpose: Generates streaming responses to user questions
  - Features:
    - Async response generation
    - Document retrieval integration
    - SSE formatting
    - Error handling

- `_retrieve_docs(query: str)`
  - Purpose: Retrieves relevant documents for context
  - Features:
    - Vector similarity search
    - Configurable retrieval parameters
    - Document ranking

### Integration Points

- Combines with IndexerService for document retrieval
- Integrates with vector store for similarity search
- Supports streaming responses via FastAPI endpoints

### Error Handling

- Comprehensive error logging
- Runtime error detection
- State validation
- Stream integrity checks
