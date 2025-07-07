# Comprehensive Debug Analysis for Smart-Meet Lite 500 Internal Server Error

## Context
We have a production system (Smart-Meet Lite) that successfully ingests meeting data using enhanced extraction but fails with HTTP 500 errors when querying the data. The system uses:
- FastAPI for REST API
- SQLite for structured data
- Qdrant for vector embeddings
- OpenRouter for LLM operations
- A sophisticated query engine (query_engine_v2.py)

## Error Symptoms
1. **Successful Operations:**
   - Meeting ingestion works perfectly (200 OK)
   - Enhanced extraction with OpenRouter structured output succeeds
   - Data is saved to both SQLite and Qdrant
   - Entity resolution and state tracking work correctly

2. **Failed Operations:**
   - ALL query endpoints return 500 Internal Server Error
   - Error messages vary:
     - `{"detail":"0"}` - suggests a string/number type issue
     - `{"detail":"Invalid format specifier ' \"Your comprehensive answer here\",\n    \"confidence\": 0.95\n' for object of type 'str'"}` - indicates string formatting error

3. **Test Results:**
   ```
   Query: What is the current status of Project Alpha?
   Response status: 500
   Response text: {"detail":"0"}
   
   Query: Show me the timeline of changes for API Migration
   Response status: 500
   Response text: {"detail":"Invalid format specifier..."}
   ```

## Key Files to Analyze

1. **src/api.py** (lines 404-435):
   - The query endpoint that's failing
   - Exception handling that produces the 500 error
   - How it calls the query engine

2. **src/query_engine_v2.py**:
   - The production query engine being used
   - Contains methods like `process_query`
   - Has JSON schema definitions with example outputs
   - Implements different query intents (status, timeline, blocker, etc.)

3. **src/models.py**:
   - QueryResult dataclass definition
   - Expected structure of query responses

## Investigation Tasks

### 1. Trace the Execution Flow
- Start at `/api/query` endpoint (api.py:404)
- Follow the call to `query_engine.process_query(request.query)`
- Identify which specific method in query_engine_v2.py is being called
- Find where the error is actually occurring

### 2. Analyze the Error Messages
- **"0" error**: This suggests somewhere in the code, an integer 0 is being passed to `str()` or used in a context expecting a string
- **"Invalid format specifier" error**: This indicates a Python string formatting issue, possibly:
  - Using % formatting with wrong arguments
  - Using .format() with mismatched placeholders
  - Using f-strings incorrectly
  - The error message shows JSON content being used as a format specifier

### 3. Check Data Type Mismatches
- Look for places where:
  - Numbers are expected but strings are provided
  - JSON strings are being used where objects are expected
  - Format strings are being constructed dynamically
  - Template strings contain user data

### 4. Examine the Query Result Construction
- How is QueryResult being created?
- Are all required fields being populated?
- Is there a mismatch between what the API expects and what the query engine returns?

### 5. Look for String Formatting Issues
Search for patterns like:
- `% confidence` or `% answer`
- Dynamic string construction with user input
- JSON schema examples being used as actual format strings
- Places where JSON examples might be mistaken for template strings

### 6. Check Async/Await Consistency
- Is `process_query` properly awaited?
- Are there any synchronous calls in async contexts?
- Database operations properly handled?

## Specific Hypotheses to Test

1. **JSON Schema Misuse**: The JSON schema examples (lines 571-573 in query_engine_v2.py) might be accidentally used as format strings
2. **Type Conversion Error**: The "0" error might come from a failed entity lookup returning 0 instead of None
3. **Missing Return Value**: The query engine might not be returning a proper QueryResult object
4. **Format String Injection**: User query text might be accidentally used in string formatting
5. **Confidence Score Type**: Confidence might be returned as string "0.95" instead of float 0.95

## Debug Strategy

1. **Add Logging**:
   - Log the exact input to `process_query`
   - Log the type and value of the result
   - Log any intermediate values in the query processing

2. **Check Return Types**:
   - Verify `process_query` returns a QueryResult object
   - Ensure all QueryResult fields are properly typed
   - Check if any fields are None when they shouldn't be

3. **String Format Analysis**:
   - Search for ALL string formatting operations in query_engine_v2.py
   - Look for places where JSON examples might be used as templates
   - Check if user input is ever used in format strings

4. **Error Propagation**:
   - The actual error might be wrapped multiple times
   - Check if the "0" is actually an error code being stringified
   - Look for exception handling that might mask the real error

## Required Information

To solve this issue, we need to find:
1. The exact line of code where the exception is raised
2. The actual values of variables at that point
3. Whether it's a type mismatch, formatting error, or logic bug
4. Why the error message varies between queries

## Next Steps

1. Add comprehensive logging to the query endpoint
2. Trace through a single query execution step by step
3. Identify the exact operation that fails
4. Fix the root cause (likely a string formatting or type conversion issue)
5. Add tests to prevent regression