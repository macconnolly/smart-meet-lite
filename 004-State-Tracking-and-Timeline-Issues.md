# 004: State Tracking and Timeline Query Failures

## Problem
After implementing entity resolution and performing a clean reset, comprehensive testing revealed critical failures in state tracking and timeline functionality:
- Only 16 state transitions recorded across 4 meetings (should be 100+)
- Timeline queries return 500 errors or empty results
- State changes mentioned in transcripts not captured as transitions
- Complex queries fall back to generic responses with 0.20 confidence

## Root Cause
The `_process_state_changes()` method in processor.py creates entity states but fails to detect changes between meetings. The state comparison logic appears flawed, preventing transition records from being created when states change.

## Evidence
```
Test Results:
- 102 entity states created ✓
- 16 state transitions created ✗ (should be many more)
- Timeline query: "How did API optimization project progress?" → 500 error
- Blocker query: "What blockers did we encounter?" → Generic response (0.20 confidence)
```

## Impact
- No historical tracking of project progress
- Unable to answer "how did X change over time" questions
- Missing critical business intelligence about blockers and resolutions
- Timeline features completely non-functional

## Solution Approach
1. Fix state comparison logic in `_process_state_changes()`
2. Add comprehensive logging to understand comparison failures
3. Implement state inference from context ("now in progress", "blocked")
4. Create proper test cases for state transitions
5. Improve query intent classification for timeline/blocker queries

## Status
- Created comprehensive backlog in FINDINGS_AND_BACKLOG.md
- Identified specific code changes needed
- All test scripts moved to examples/ folder
- Ready to implement Priority 1 fixes