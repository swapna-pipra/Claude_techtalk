# Implementation Plan: QA Test Case Management

## Overview

Extend the existing Jira Issue Explorer with two modules in a tabbed UI: ID-Based Lookup (refactoring existing search) and Video Analysis (new backend pipeline with OpenCV frame extraction and OpenAI GPT-4o analysis). Implementation uses Python/Flask backend and Bootstrap 5 frontend with no database.

## Tasks

- [x] 1. Update dependencies and environment configuration
  - [x] 1.1 Add opencv-python and openai to requirements.txt
    - Add `opencv-python` and `openai` packages to requirements.txt
    - _Requirements: 9.2_
  - [x] 1.2 Update server.py to load AI environment variables
    - Load AI_API_KEY and AI_MODEL (default "gpt-4o") from environment variables at startup
    - Log warning if AI_API_KEY is missing or empty
    - _Requirements: 8.4, 8.5, 9.2, 9.3_

- [x] 2. Implement unified tabbed UI navigation
  - [x] 2.1 Restructure index.html with primary tab navigation
    - Add two primary tabs ("ID-Based Lookup" and "Video Analysis") below the navbar
    - Move existing search/results into ID-Based Lookup tab content area
    - Create empty Video Analysis tab content area
    - Default to ID-Based Lookup tab active on load
    - Apply Bootstrap nav-tabs styling with active state
    - _Requirements: 1.1, 1.2, 1.3, 1.5, 1.7_
  - [x] 2.2 Implement tab switching with state preservation
    - Switch visible module on tab click, hide the other
    - Preserve entered data and displayed results when switching tabs
    - _Requirements: 1.2, 1.3, 1.6_
  - [ ]* 2.3 Write property test for tab state preservation
    - **Property 4: Tab state preservation round-trip**
    - **Validates: Requirement 1.6**

- [x] 3. Enhance ID-Based Lookup module with validation
  - [x] 3.1 Add input validation for issue ID format
    - Validate format matches `PROJECT-NUMBER` pattern (`/^[A-Z]+-\d+$/`)
    - Reject empty/whitespace-only input without sending request
    - Display validation message for invalid formats
    - _Requirements: 2.1, 2.6, 2.7_
  - [x] 3.2 Add loading indicator and timeout handling
    - Show spinner and disable search button during fetch
    - Implement 30-second timeout with error display
    - _Requirements: 2.8, 2.9_
  - [ ]* 3.3 Write property test for issue ID validation
    - **Property 9: Issue ID validation**
    - **Validates: Requirements 2.6, 2.7**

- [x] 4. Implement Video Analysis Module frontend
  - [x] 4.1 Create video file upload UI
    - Add file input accepting MP4, WebM, AVI formats
    - Add upload button and file info display area
    - _Requirements: 3.1_
  - [x] 4.2 Implement client-side file validation
    - Validate file extension (mp4, webm, avi)
    - Validate file size (min 1 byte, max 100 MB)
    - Display appropriate error messages for invalid files
    - _Requirements: 3.2, 3.3, 3.5, 3.6_
  - [x] 4.3 Implement video upload with progress tracking
    - Use XMLHttpRequest for upload progress events
    - Display determinate progress bar (0-100%)
    - Show success confirmation with filename on completion
    - Handle network errors with retry capability (preserve file reference)
    - _Requirements: 3.4, 3.7, 3.8, 3.9_
  - [x] 4.4 Implement processing status indicator
    - Show "Video analysis in progress" message during backend processing
    - _Requirements: 4.6_
  - [ ]* 4.5 Write property test for file validation
    - **Property 1: File validation consistency**
    - **Validates: Requirements 3.2, 3.3, 3.5, 3.6**

- [x] 5. Checkpoint - Verify frontend modules
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement Flask video upload endpoint
  - [x] 6.1 Create /api/analyze-video POST endpoint with validation
    - Accept multipart form data with "video" field
    - Configure MAX_CONTENT_LENGTH to 500 MB
    - Validate file presence, extension (mp4, avi, mov, webm, mkv), and size
    - Return 400 for missing/empty file or invalid format
    - Return 413 for oversized files
    - Save valid files to temp directory with random names
    - _Requirements: 7.1, 7.2, 7.4, 7.5, 7.7_
  - [x] 6.2 Implement temp file cleanup
    - Delete temp file in finally block after processing (success or failure)
    - Ensure cleanup happens before response is sent
    - _Requirements: 7.3_
  - [x] 6.3 Add AI configuration check
    - Return 503 if AI_API_KEY is not set when video analysis is requested
    - _Requirements: 8.7_
  - [ ]* 6.4 Write property test for error response structure
    - **Property 10: Error response structure**
    - **Validates: Requirements 7.4, 7.5, 7.7, 8.6, 8.7**
  - [ ]* 6.5 Write property test for temp file cleanup
    - **Property 3: Temp file cleanup guarantee**
    - **Validates: Requirement 7.3**

- [x] 7. Implement frame extraction module
  - [x] 7.1 Create extract_frames function using OpenCV
    - Open video with cv2.VideoCapture
    - Extract frames at configurable interval (default 1fps, range 0.5-5s)
    - Encode frames as base64 JPEG strings
    - Cap at 30 frames maximum for API cost control
    - Handle corrupt/unreadable videos with descriptive error
    - Release cv2 resources in finally block
    - _Requirements: 4.1_
  - [ ]* 7.2 Write unit tests for frame extraction
    - Test with a short sample video file
    - Test error handling for corrupt files
    - Test frame count capping behavior
    - _Requirements: 4.1_

- [x] 8. Implement AI analysis module
  - [x] 8.1 Create analyze_workflow function
    - Construct OpenAI API messages with base64 frames as image_url content
    - Send structured prompt for workflow step identification
    - Parse response into list of WorkflowStep dicts
    - Implement 60-second timeout per API call
    - Handle API errors with descriptive messages
    - _Requirements: 4.2, 4.3, 4.4, 8.1, 8.2, 8.6_
  - [x] 8.2 Create generate_test_artifacts function
    - Send workflow steps with test artifact generation prompt
    - Parse response into categorized artifact structure (scenarios, cases, negative, edge, ui_ux)
    - Generate sequential TC-VID-NNN IDs
    - Assign priority values (Critical/High/Medium/Low)
    - Handle empty workflow steps (return empty artifacts with message)
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 8.3_
  - [x] 8.3 Wire analysis pipeline into endpoint
    - Call extract_frames → analyze_workflow → generate_test_artifacts
    - Implement 120-second total processing timeout
    - Return structured JSON with all artifact categories and count summary
    - Return 200 on success with categorized artifacts
    - _Requirements: 4.7, 7.6_
  - [ ]* 8.4 Write property test for test case ID generation
    - **Property 2: Test case ID sequential uniqueness**
    - **Validates: Requirement 5.7**
  - [ ]* 8.5 Write property test for priority assignment
    - **Property 5: Priority assignment correctness**
    - **Validates: Requirement 5.6**
  - [ ]* 8.6 Write property test for workflow step bounds
    - **Property 6: Workflow step structure and bounds**
    - **Validates: Requirements 4.3, 4.4**

- [x] 9. Checkpoint - Verify backend pipeline
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Implement test artifact display
  - [x] 10.1 Render artifact count summary
    - Display numeric counts for all 5 categories above the sections
    - _Requirements: 6.7_
  - [x] 10.2 Render collapsible artifact sections
    - Display sections in fixed order: Test Scenarios, Detailed Test Cases, Negative Test Cases, Edge Cases, UI/UX Validation Points
    - All sections expanded by default
    - Show "no items generated" message for empty categories
    - _Requirements: 6.1, 6.2_
  - [x] 10.3 Render test case tables
    - Detailed Test Cases table: ID, Title, Preconditions, Steps, Expected Result, Priority
    - Negative Test Cases table: same column structure
    - Support up to 200 rows per table
    - _Requirements: 6.3, 6.4_
  - [x] 10.4 Render edge cases and UI/UX points
    - Edge Cases: grouped list by category with description and expected behavior
    - UI/UX Validation Points: checklist with label and pass/fail indicator (default unset)
    - _Requirements: 6.5, 6.6_
  - [ ]* 10.5 Write property test for artifact count accuracy
    - **Property 11: Artifact count summary accuracy**
    - **Validates: Requirement 6.7**
  - [ ]* 10.6 Write property test for non-empty workflow artifact generation
    - **Property 7: Non-empty workflow produces all artifact categories**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5**

- [x] 11. Final checkpoint - Full integration verification
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- The project uses Python for backend (Flask + OpenCV + OpenAI) and vanilla JavaScript for frontend
- No database is needed — all processing is request-scoped and in-memory
