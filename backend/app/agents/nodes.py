"""LangGraph agent nodes for query processing."""

from app.models.schemas import Source
import re

from app.agents.state import AgentState
from app.core.logging import get_logger
from app.services.llm_service import get_llm_service
from app.services.redis_session_store import get_redis_session_store
from app.services.retrieval_service import get_retrieval_service

logger = get_logger(__name__)


async def query_analysis_node(state: AgentState) -> AgentState:
    """Analyze the user's query to understand intent and extract key information.

    Performs comprehensive query analysis:
    1. Loads conversation history from Redis session store
    2. Classifies query intent (code understanding, bug finding, architecture, etc.)
    3. Extracts key entities (file names, functions, classes)
    4. Identifies query focus areas
    5. Detects complex multi-part queries

    Args:
        state: Current agent state

    Returns:
        Updated state with session history loaded and query analysis metadata
    """
    logger.info(
        "query_analysis",
        query=state.query[:100],
        codebase_id=state.codebase_id,
        session_id=state.session_id,
    )

    # Initialize query analysis metadata
    query_analysis = {
        "intent": "unknown",
        "confidence": 0.0,
        "entities": {
            "files": [],
            "functions": [],
            "classes": [],
            "keywords": [],
        },
        "is_multi_part": False,
        "requires_context": False,
        "complexity": "simple",
    }

    # Load session history if session_id is provided
    if state.session_id:
        redis_store = get_redis_session_store()
        session = await redis_store.get_session(state.session_id)

        if session:
            # Load conversation history (last 10 turns = 20 messages max)
            history_messages = []
            async for msg in redis_store.get_messages(state.session_id, limit=20):
                # Format as Q: ... A: ... for LLM context
                if msg.role.value == "user":
                    history_messages.append({"role": "user", "content": msg.content})
                elif msg.role.value == "assistant":
                    history_messages.append({"role": "assistant", "content": msg.content})

            # Store in state for use in response_generation
            state.session_history = history_messages

            logger.info(
                "session_history_loaded",
                session_id=state.session_id,
                history_turns=len(history_messages) // 2,
            )
        else:
            logger.warning(
                "session_not_found",
                session_id=state.session_id,
                message="Session not found, proceeding without history",
            )

    # Analyze query to classify intent and extract entities
    query_lower = state.query.lower()

    # 1. Classify query intent
    intent_patterns = {
        "code_understanding": [
            "how does",
            "how do",
            "what is",
            "what does",
            "explain",
            "describe",
            "show me",
            "tell me about",
            "how work",
            "purpose",
            "functionality",
        ],
        "bug_finding": [
            "bug",
            "error",
            "issue",
            "problem",
            "wrong",
            "not working",
            "broken",
            "fix",
            "debug",
            "why failing",
            "doesn't work",
            "fail",
        ],
        "architecture": [
            "architecture",
            "design",
            "structure",
            "pattern",
            "component",
            "module",
            "package",
            "organization",
            "relationship",
            "flow",
        ],
        "implementation": [
            "implement",
            "add",
            "create",
            "write",
            "build",
            "develop",
            "how to",
            "example",
            "sample",
        ],
        "comparison": [
            "difference",
            "compare",
            "versus",
            "vs",
            "better",
            "worse",
            "instead of",
            "alternative",
        ],
        "location": [
            "where is",
            "find",
            "locate",
            "which file",
            "defined in",
            "implemented",
            "location",
        ],
        "documentation": ["document", "comment", "docstring", "readme", "usage"],
    }

    # Match intent patterns
    best_intent = "unknown"
    best_match_count = 0

    for intent, patterns in intent_patterns.items():
        match_count = sum(1 for pattern in patterns if pattern in query_lower)
        if match_count > best_match_count:
            best_match_count = match_count
            best_intent = intent

    if best_match_count > 0:
        query_analysis["intent"] = best_intent
        query_analysis["confidence"] = min(best_match_count * 0.3, 1.0)

    # 2. Extract file paths
    file_pattern = r'["\']?([a-zA-Z_./\\][a-zA-Z0-9_./\\]*\.(?:py|js|ts|tsx|java|go|rs|cpp|c|h|cs|php|rb|scala|kt|swift|dart))["\']?'
    files_found = re.findall(file_pattern, state.query, re.IGNORECASE)
    query_analysis["entities"]["files"] = list(set(files_found))

    # 3. Extract function names (common patterns)
    function_pattern = r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\("
    functions_found = re.findall(function_pattern, state.query)
    # Filter out common language keywords
    keyword_filter = {
        "if",
        "for",
        "while",
        "with",
        "def",
        "class",
        "import",
        "from",
        "return",
        "print",
    }
    query_analysis["entities"]["functions"] = [
        f for f in functions_found if f not in keyword_filter and len(f) > 2
    ]

    # 4. Extract class names (PascalCase)
    class_pattern = r"\b([A-Z][a-zA-Z0-9]*)\b"
    classes_found = re.findall(class_pattern, state.query)
    query_analysis["entities"]["classes"] = [
        c for c in classes_found if len(c) > 2 and c not in query_analysis["entities"]["files"]
    ]

    # 5. Extract key technical terms
    technical_terms = [
        "async",
        "await",
        "thread",
        "process",
        "database",
        "api",
        "endpoint",
        "middleware",
        "service",
        "controller",
        "model",
        "view",
        "router",
        "authentication",
        "authorization",
        "oauth",
        "jwt",
        "session",
        "cookie",
        "request",
        "response",
        "query",
        "mutation",
        "subscription",
        "graphql",
        "rest",
        "grpc",
        "websocket",
        "http",
        "https",
        "tcp",
        "udp",
        "docker",
        "kubernetes",
        "deployment",
        "container",
        "microservice",
        "monolith",
        "serverless",
        "function",
        "lambda",
        "queue",
        "stream",
        "cache",
        "redis",
        "memcached",
        "database",
        "sql",
        "nosql",
        "transaction",
        "lock",
        "semaphore",
        "race",
        "condition",
        "event",
    ]

    found_terms = [term for term in technical_terms if term in query_lower]
    query_analysis["entities"]["keywords"] = found_terms

    # 6. Detect multi-part queries
    multi_part_indicators = [" and ", " also ", " then ", " after ", " besides ", " plus "]
    query_analysis["is_multi_part"] = any(
        indicator in query_lower for indicator in multi_part_indicators
    )

    # 7. Detect if external context is needed
    context_indicators = ["outside", "external", "third-party", "library", "framework", "package"]
    query_analysis["requires_context"] = any(
        indicator in query_lower for indicator in context_indicators
    )

    # 8. Assess query complexity
    complexity_score = 0
    complexity_score += len(query_analysis["entities"]["files"]) * 2
    complexity_score += len(query_analysis["entities"]["functions"])
    complexity_score += len(query_analysis["entities"]["classes"])
    complexity_score += len(query_analysis["entities"]["keywords"])
    complexity_score += 10 if query_analysis["is_multi_part"] else 0
    complexity_score += 5 if query_analysis["requires_context"] else 0

    if complexity_score > 15:
        query_analysis["complexity"] = "complex"
    elif complexity_score > 7:
        query_analysis["complexity"] = "moderate"
    else:
        query_analysis["complexity"] = "simple"

    # Store analysis in state
    state.query_analysis = query_analysis

    # Log analysis results
    logger.info(
        "query_analysis_complete",
        intent=query_analysis["intent"],
        confidence=query_analysis["confidence"],
        files_found=len(query_analysis["entities"]["files"]),
        functions_found=len(query_analysis["entities"]["functions"]),
        classes_found=len(query_analysis["entities"]["classes"]),
        is_multi_part=query_analysis["is_multi_part"],
        complexity=query_analysis["complexity"],
    )

    state.step = "analyzed"
    return state


async def retrieval_node(state: AgentState) -> AgentState:
    """Retrieve relevant code chunks using vector search.

    Args:
        state: Current agent state

    Returns:
        Updated state with retrieved chunks
    """
    retrieval_service = get_retrieval_service()

    chunks, sources = await retrieval_service.retrieve_code(
        query=state.query,
        codebase_id=state.codebase_id,
        top_k=5,
    )

    state.retrieved_chunks = chunks
    state.sources = sources
    state.step = "retrieved"

    logger.info(
        "retrieval_complete",
        chunks_count=len(chunks),
        sources_count=len(sources),
    )

    return state


async def context_building_node(state: AgentState) -> AgentState:
    """Build formatted context from retrieved chunks.

    Args:
        state: Current agent state

    Returns:
        Updated state with formatted context
    """
    context_parts = []

    for chunk in state.retrieved_chunks:
        metadata = chunk["metadata"]
        context_parts.append(
            f"File: {metadata['file_path']} (Lines {metadata['line_start']}-{metadata['line_end']})\n"
            f"```{metadata['language']}\n"
            f"{chunk['content']}\n"
            f"```"
        )

    state.context = "\n\n".join(context_parts)
    state.step = "context_built"

    logger.info(
        "context_built",
        context_length=len(state.context),
    )

    return state


async def response_generation_node(state: AgentState) -> AgentState:
    """Generate response using Claude LLM.

    Args:
        state: Current agent state

    Returns:
        Updated state with generated response
    """
    llm_service = get_llm_service()

    response_parts = []
    async for chunk in llm_service.generate_response(
        query=state.query,
        context=state.context,
        session_history=state.session_history,
    ):
        response_parts.append(chunk)

    state.response = "".join(response_parts)
    state.step = "responded"

    logger.info(
        "response_generated",
        response_length=len(state.response),
        has_history=len(state.session_history) if state.session_history else 0,
    )

    return state


async def validation_node(state: AgentState) -> AgentState:
    """Validate the generated response and verify citations.

    Performs comprehensive validation:
    1. Verifies citations reference actual code chunks
    2. Detects potential hallucinations
    3. Checks response alignment with retrieved context
    4. Calculates quality score

    Args:
        state: Current agent state

    Returns:
        Updated state with validation results and quality metadata
    """
    validation_results = {
        "citations_verified": [],
        "citations_missing": [],
        "potential_hallucinations": [],
        "context_alignment_score": 0.0,
        "overall_quality_score": 0.0,
        "warnings": [],
    }

    # Skip validation if no response or sources
    if not state.response or not state.sources:
        logger.warning(
            "validation_skipped",
            has_response=bool(state.response),
            has_sources=len(state.sources) if state.sources else 0,
        )
        state.validation_results = validation_results
        state.step = "validated"
        return state

    # 1. Verify citations against retrieved chunks
    retrieved_files = set()
    retrieved_ranges = {}  # (file_path) -> [(line_start, line_end), ...]

    for chunk in state.retrieved_chunks:
        file_path = chunk["metadata"]["file_path"]
        line_start = chunk["metadata"]["line_start"]
        line_end = chunk["metadata"]["line_end"]

        retrieved_files.add(file_path)
        if file_path not in retrieved_ranges:
            retrieved_ranges[file_path] = []
        retrieved_ranges[file_path].append((line_start, line_end))

    # 2. Validate each citation
    for source in state.sources:
        file_path = source.file_path
        line_start = source.line_start
        line_end = source.line_end

        # Check if file exists in retrieved chunks
        if file_path not in retrieved_files:
            validation_results["citations_missing"].append(
                {"source": source, "reason": f"File '{file_path}' not found in retrieved context"}
            )
            validation_results["warnings"].append(
                f"Citation references unretrieved file: {file_path}"
            )
            continue

        # Check if line range overlaps with any retrieved chunk
        found = False
        for chunk_start, chunk_end in retrieved_ranges[file_path]:
            # Check for overlap or proximity (allow 5 line tolerance)
            if not (line_end < chunk_start - 5 or line_start > chunk_end + 5):
                found = True
                validation_results["citations_verified"].append(
                    {
                        "source": source.model_dump(),
                        "chunk_range": [chunk_start, chunk_end],
                    }
                )
                break

        if not found:
            validation_results["citations_missing"].append(
                {
                    "source": source.model_dump(),
                    "reason": f"Lines {line_start}-{line_end} not found in retrieved chunks for {file_path}",
                }
            )
            validation_results["warnings"].append(
                f"Citation line range {line_start}-{line_end} may not match retrieved content"
            )

    # 3. Detect potential hallucinations
    # Look for code patterns in response that might be fabricated
    code_block_pattern = r"```(\w+)?\n([\s\S]*?)```"
    code_blocks = re.findall(code_block_pattern, state.response)

    for lang, code in code_blocks:
        # Extract function/class definitions from code blocks
        function_pattern = r"(def|async def|class|function|const)\s+(\w+)"
        definitions = re.findall(function_pattern, code)

        for def_type, def_name in definitions:
            # Check if this definition is mentioned in retrieved context
            found_in_context = False
            for chunk in state.retrieved_chunks:
                content = chunk["content"]
                if def_name in content:
                    found_in_context = True
                    break

            if not found_in_context:
                validation_results["potential_hallucinations"].append(
                    {
                        "type": def_type,
                        "name": def_name,
                        "language": lang,
                    }
                )
                validation_results["warnings"].append(
                    f"Potential hallucination: {def_type} '{def_name}' not found in retrieved context"
                )

    # 4. Calculate context alignment score
    # Higher score = more of the response is grounded in retrieved context
    if state.context and state.response:
        # Simple heuristic: check overlap of key terms
        context_words = set(re.findall(r"\b\w+\b", state.context.lower()))
        response_words = set(re.findall(r"\b\w+\b", state.response.lower()))

        # Remove common words
        common_words = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "can",
            "to",
            "of",
            "in",
            "for",
            "on",
            "at",
            "by",
            "with",
            "from",
            "as",
            "or",
            "and",
            "not",
            "this",
            "that",
            "it",
            "its",
            "the",
            "you",
            "your",
            "we",
            "use",
            "using",
        }

        context_words -= common_words
        response_words -= common_words

        if response_words:
            overlap = len(context_words & response_words)
            alignment = min(overlap / len(response_words), 1.0)
            validation_results["context_alignment_score"] = round(alignment, 3)

    # 5. Calculate overall quality score
    # Score = 0.0 to 1.0 based on:
    # - Citation accuracy (40%)
    # - Context alignment (30%)
    # - Hallucination penalty (30%)
    total_citations = len(state.sources)
    verified_citations = len(validation_results["citations_verified"])
    citation_accuracy = verified_citations / total_citations if total_citations > 0 else 0.0

    hallucination_penalty = len(validation_results["potential_hallucinations"]) * 0.1

    overall_score = (
        citation_accuracy * 0.4
        + validation_results["context_alignment_score"] * 0.3
        + (1.0 - min(hallucination_penalty, 1.0)) * 0.3
    )

    validation_results["overall_quality_score"] = round(max(0.0, overall_score), 3)

    # 6. Log validation results
    logger.info(
        "validation_complete",
        total_citations=total_citations,
        verified_citations=verified_citations,
        missing_citations=len(validation_results["citations_missing"]),
        potential_hallucinations=len(validation_results["potential_hallucinations"]),
        context_alignment=validation_results["context_alignment_score"],
        overall_quality=validation_results["overall_quality_score"],
        warnings_count=len(validation_results["warnings"]),
    )

    # Add validation metadata to state
    state.validation_results = validation_results
    state.step = "validated"

    return state


async def error_handler_node(state: AgentState, error: Exception) -> AgentState:
    """Handle errors in the agent pipeline with intelligent categorization.

    Categorizes errors into:
    - User input errors (invalid queries, empty input)
    - Retrieval errors (codebase not found, no results)
    - LLM errors (rate limiting, service unavailable)
    - System errors (unexpected failures)

    Provides user-friendly messages and recovery suggestions.

    Args:
        state: Current agent state
        error: The error that occurred

    Returns:
        Updated state with categorized error information
    """
    error_type = "unknown"
    user_message = "An unexpected error occurred. Please try again."
    recovery_suggestion = None
    technical_details = None

    # Categorize error and provide appropriate messaging
    error_message = str(error).lower()

    # User input errors
    if "empty" in error_message or "not found" in error_message and "codebase" in error_message:
        error_type = "user_input"
        user_message = "Unable to find the specified codebase."
        recovery_suggestion = "Please check the codebase ID and try again."

    elif "invalid" in error_message and ("query" in error_message or "input" in error_message):
        error_type = "user_input"
        user_message = "Your query could not be processed."
        recovery_suggestion = "Please rephrase your question and try again."

    # Retrieval errors
    elif "retriev" in error_message or "vector" in error_message or "no results" in error_message:
        error_type = "retrieval"
        user_message = "No relevant code could be found for your query."
        recovery_suggestion = (
            "Try:\n"
            "- Using different keywords\n"
            "- Being more specific about what you're looking for\n"
            "- Checking if the code exists in this codebase"
        )

    elif "chroma" in error_message or "database" in error_message:
        error_type = "retrieval"
        user_message = "Unable to search the codebase."
        recovery_suggestion = "The search service may be unavailable. Please try again later."

    # LLM errors
    elif "rate limit" in error_message or "quota" in error_message or "429" in error_message:
        error_type = "rate_limit"
        user_message = "Too many requests. Please wait a moment before trying again."
        recovery_suggestion = "Rate limits help ensure fair usage for everyone."

    elif "anthropic" in error_message or "claude" in error_message or "llm" in error_message:
        error_type = "llm_service"
        user_message = "Unable to generate a response."
        recovery_suggestion = "The AI service may be unavailable. Please try again later."

    elif "timeout" in error_message:
        error_type = "timeout"
        user_message = "The request took too long to process."
        recovery_suggestion = "Try breaking your question into smaller parts."

    # Network/service errors
    elif "connection" in error_message or "network" in error_message:
        error_type = "network"
        user_message = "Network connection issue."
        recovery_suggestion = "Please check your connection and try again."

    elif (
        "unauthorized" in error_message
        or "authentication" in error_message
        or "401" in error_message
    ):
        error_type = "authentication"
        user_message = "Authentication failed."
        recovery_suggestion = "You may need to refresh your session."

    # System errors
    elif "memory" in error_message or "resource" in error_message:
        error_type = "resource"
        user_message = "System resources are temporarily unavailable."
        recovery_suggestion = "Please try again in a few moments."

    else:
        # Unknown error - provide generic message
        # Technical details logged but not exposed to user
        technical_details = str(error)

    # Sanitize user message (remove potential sensitive info)
    user_message = _sanitize_error_message(user_message)

    # Create error metadata
    error_metadata = {
        "error_type": error_type,
        "user_message": user_message,
        "recovery_suggestion": recovery_suggestion,
        "technical_details": technical_details,
        "step": state.step,
        "query_preview": state.query[:100] if state.query else None,
    }

    # Log comprehensive error information
    logger.error(
        "agent_error_handled",
        error_type=error_type,
        step=state.step,
        error=str(error),
        error_class=error.__class__.__name__,
        user_message=user_message,
        has_suggestion=recovery_suggestion is not None,
    )

    # Set error state
    state.error = user_message
    state.error_metadata = error_metadata
    state.step = "error"

    return state


def _sanitize_error_message(message: str) -> str:
    """Sanitize error messages to prevent information leakage.

    Removes potential sensitive information like:
    - File paths
    - Database connection strings
    - API keys or tokens
    - Internal URLs

    Args:
        message: Raw error message

    Returns:
        Sanitized error message safe for user display
    """
    # Remove file paths (Windows and Unix)
    message = re.sub(r"[A-Za-z]:\\[^;:\n\r]*", "[path]", message)
    message = re.sub(r"/[^;\s:\n\r]{20,}", "[path]", message)

    # Remove connection strings
    message = re.sub(r"://[^@\s]+@[^:\s]+", "://***:***@***", message)

    # Remove potential tokens/keys
    message = re.sub(r'key["\']?\s*[:=]\s*["\']?[^\s"\']{10,}["\']?', "key=***", message)
    message = re.sub(r'token["\']?\s*[:=]\s*["\']?[^\s"\']{10,}["\']?', "token=***", message)

    # Remove stack traces
    lines = message.split("\n")
    sanitized_lines = []
    for line in lines:
        # Skip lines that look like stack trace
        if line.strip().startswith("File ") or line.strip().startswith("at "):
            continue
        if "Traceback" in line:
            continue
        sanitized_lines.append(line)

    return "\n".join(sanitized_lines).strip()
