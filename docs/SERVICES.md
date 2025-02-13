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

Handles website content processing and indexing operations with asynchronous task tracking.

### Features

- Asynchronous website processing with task tracking
- Comprehensive sitemap crawling
- URL validation and normalization
- Content extraction and processing
- Concurrent request handling with rate limiting
- Real-time progress monitoring

### Components

1. **TaskStore**
   - Purpose: Manages processing task states and progress
   - Features:
     - Task status tracking (PENDING, IN_PROGRESS, COMPLETED, FAILED)
     - Progress monitoring with percentage completion
     - Failed URL tracking
     - Concurrent access handling with locks

2. **ProcessingStatus**
   - Tracks:
     - Total URLs to process
     - Processed URLs list
     - Remaining URLs queue
     - Failed URLs list
     - Current URL being processed
     - Completion percentage
     - Error information

### Key Methods

- `process_website(url: str)`

  - Purpose: Main entry point for website processing
  - Returns: Task ID for status tracking
  - Features:
    - Asynchronous processing
    - Progress monitoring
    - Error handling

- `_process_website_task(url: str, task_id: str)`

  - Purpose: Background task for website processing
  - Features:
    - Sitemap parsing
    - Concurrent URL processing
    - Status updates
    - Error handling

- `_fetch_sitemap(base_url: str)`

  - Purpose: Retrieves and parses website sitemap
  - Returns: List of URLs to process
  - Features:
    - XML sitemap parsing
    - URL validation
    - Error handling for missing/invalid sitemaps

- `_process_url(url: str, task_id: str)`
  - Purpose: Processes individual webpage content
  - Features:
    - Content extraction with WebBaseLoader
    - Rate limiting with semaphore
    - Status updates
    - Error handling and logging

### Error Handling

- Comprehensive error logging with context
- Network timeout handling (configurable)
- Invalid URL detection and reporting
- Rate limiting with configurable concurrent requests
- Task-level error tracking
- Automatic retry logic for transient failures

### Configuration

- `max_concurrent_requests`: Controls concurrent URL processing (default: 10)
- `connection_timeout`: Network timeout in seconds (default: 30)
- Configurable through service initialization

## WikiService

Manages Azure DevOps Wiki content processing with asynchronous task tracking and caching.

### Features

- Asynchronous wiki processing with task tracking
- Concurrent page processing with rate limiting
- Content caching for improved performance
- Real-time progress monitoring
- Hierarchical page structure handling

### Components

1. **WikiClient**
   - Purpose: Handles Azure DevOps Wiki API interactions
   - Features:
     - Connection pooling with aiohttp
     - Rate limiting with semaphore
     - TTL-based caching (1-hour cache)
     - Authentication handling
     - Concurrent request management

2. **TaskStore**
   - Purpose: Manages processing task states
   - Features:
     - Task status tracking (PENDING, IN_PROGRESS, COMPLETED, FAILED)
     - Progress monitoring
     - Failed pages tracking
     - Concurrent access handling

3. **WikiPage**
   - Purpose: Represents wiki page content and metadata
   - Properties:
     - Page path
     - Content
     - Remote URL

### Key Methods

- `process_wiki(organization: str, project: str, wiki_identifier: str)`

  - Purpose: Main entry point for wiki processing
  - Returns: Task ID for status tracking
  - Features:
    - Asynchronous processing
    - Progress monitoring
    - Error handling

- `_process_wiki_pages(task_id: str, organization: str, project: str, wiki_identifier: str)`

  - Purpose: Background task for wiki processing
  - Features:
    - Page tree traversal
    - Concurrent page processing
    - Status updates
    - Error handling

- `fetch_wiki_pages(organization: str, project: str, wiki_identifier: str)`
  - Purpose: Retrieves all wiki pages concurrently
  - Features:
    - Resource management
    - Concurrent processing
    - Error handling

### Error Handling

- Custom WikiClientError for API-related errors
- Network timeout handling
- Rate limit handling
- Task-level error tracking
- Automatic retry logic
- Comprehensive error logging

### Caching

- TTL-based caching (1-hour expiry)
- Cache size limit: 100 items
- Cached items:
  - Page content
  - Wiki tree structure

### Configuration

- `max_concurrent_requests`: Controls concurrent page processing (default: 10)
- `connection_timeout`: Network timeout in seconds (default: 30)
- API version: 7.1
- Cache TTL: 3600 seconds (1 hour)

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

Handles asynchronous document processing and indexing operations with support for multiple file formats.

### Features

1. **Concurrent Processing**
   - Semaphore-based concurrency control (max 5 concurrent)
   - Async file operations
   - Thread pool for CPU-intensive tasks
   - Resource management

2. **Document Processing Pipeline**
   - File validation and type detection
   - Temporary file management
   - Document loading and parsing
   - Content chunking
   - Vector embedding and storage

3. **Supported Formats**
   - PDF (.pdf) using PyPDFLoader
   - Microsoft Word (.docx) using Docx2txtLoader
   - Extensible loader architecture

### Key Methods

- `process_document(content: bytes, file_name: str, content_type: str)`

  - Purpose: Main entry point for document processing
  - Features:
    - File validation
    - Temporary storage management
    - Concurrent processing
    - Progress tracking
    - Resource cleanup

- `_create_document(file_path: str)`

  - Purpose: Document loading and parsing
  - Features:
    - Format detection
    - Loader selection
    - Thread pool execution
    - Error handling

### Error Handling

1. **Input Validation**
   - File format verification
   - Content type checking
   - File name validation
   - Size limit enforcement

2. **Processing Errors**
   - Loader failures
   - Resource exhaustion
   - Indexing errors
   - Cleanup failures

3. **Recovery Mechanisms**
   - Temporary file cleanup
   - Resource release
   - Error logging
   - Client notification

### Performance Features

1. **Concurrency**
   - Async I/O operations
   - Semaphore-based limits
   - Thread pool utilization
   - Resource pooling

2. **Resource Management**
   - Temporary file cleanup
   - Memory optimization
   - Connection pooling
   - Thread management

3. **Monitoring**
   - Progress tracking
   - Error logging
   - Performance metrics
   - Resource usage

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

Provides RAG-based question answering capabilities using LangGraph and LLM integration.

### Components

1. **LLM Integration**
   - Implementation: Groq LLM (deepseek-r1-distill-llama-70b)
   - Purpose: Natural language response generation
   - Features:
     - Streaming response capability
     - Context-aware responses
     - Think-tag processing

2. **LangGraph Integration**
   - Purpose: Manages conversation state and flow
   - Features:
     - State management with checkpointing
     - Message history tracking
     - Async streaming support

3. **Document Retrieval**
   - Purpose: Fetches relevant context for queries
   - Features:
     - Similarity-based search
     - Configurable retrieval count (k=3)
     - Document content aggregation

### Key Methods

- `stream_response(user_input: str, user_id: str)`

  - Purpose: Main entry point for question answering
  - Features:
    - Asynchronous response streaming
    - Context retrieval and integration
    - System prompt management
    - Think-tag filtering

- `_retrieve_docs(query: str)`

  - Purpose: Retrieves relevant documents for context
  - Features:
    - Vector similarity search
    - Configurable result count
    - Error handling for uninitialized stores

### State Management

1. **Conversation State**
   - Message history tracking
   - System prompt integration
   - Context management

2. **Graph State**
   - Checkpoint management with MemorySaver
   - Thread-based configuration
   - Message streaming control

### Error Handling

- Vector store initialization checks
- LLM response error handling
- Context integration validation
- Streaming error management

### Performance Features

- Async/await for non-blocking operations
- Efficient context retrieval (top-k)
- Streaming response for better UX
- Thread-based state isolation

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
