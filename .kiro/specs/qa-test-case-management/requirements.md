# Requirements Document

## Introduction

The QA Test Case Management feature extends the existing Jira Issue Explorer application with two integrated modules in a unified UI: (1) ID-Based Test Case Lookup that retrieves and displays detailed test case information for a given Jira issue, and (2) Video-Based Test Case Generation that analyzes uploaded workflow videos to automatically generate comprehensive test artifacts including test scenarios, detailed test cases, negative test cases, edge cases, and UI/UX validation points.

## Glossary

- **Flask_Backend**: The Python Flask server (server.py) that handles API routing, file uploads, and business logic for the application
- **Unified_UI**: The single-page HTML/Bootstrap interface combining both modules via tabbed navigation
- **ID_Lookup_Module**: The module responsible for accepting a Jira issue ID and displaying related test case details
- **Video_Analysis_Module**: The module responsible for processing uploaded video files and generating test artifacts
- **Test_Artifact**: A structured output from video analysis, including Test Scenarios, Detailed Test Cases, Negative Test Cases, Edge Cases, and UI/UX Validation Points
- **Video_Processor**: The backend component that analyzes uploaded video files using AI to extract workflow steps and generate test artifacts
- **Jira_API**: The Atlassian Jira REST API (v3) used to fetch issue details and related test cases
- **Test_Case_Table**: A structured table format containing Test Case ID, Title, Preconditions, Steps, Expected Result, and Priority columns

## Requirements

### Requirement 1: Unified Tabbed Navigation

**User Story:** As a QA Engineer, I want both test case modules available in a single interface with tab navigation, so that I can switch between ID lookup and video-based generation without leaving the page.

#### Acceptance Criteria

1. THE Unified_UI SHALL provide a primary navigation with two tabs labeled "ID-Based Lookup" and "Video Analysis", positioned below the application navbar and above the module content area
2. WHEN a user selects the "ID-Based Lookup" tab, THE Unified_UI SHALL display the ID_Lookup_Module interface and hide the Video_Analysis_Module interface
3. WHEN a user selects the "Video Analysis" tab, THE Unified_UI SHALL display the Video_Analysis_Module interface and hide the ID_Lookup_Module interface
4. THE Unified_UI SHALL preserve the existing Jira Issue Explorer styling using Bootstrap 5 and the existing CSS custom properties for colors and layout
5. THE Unified_UI SHALL default to the "ID-Based Lookup" tab as active on initial page load
6. WHEN a user switches between tabs, THE Unified_UI SHALL preserve any user-entered data and state within each module so that returning to a previously visited tab restores its prior state
7. THE Unified_UI SHALL visually distinguish the active tab from the inactive tab by applying the Bootstrap active navigation styling to the selected tab

### Requirement 2: ID-Based Test Case Lookup

**User Story:** As a QA Engineer, I want to enter a Jira issue ID and see all related test case details, so that I can quickly review existing test coverage for any issue.

#### Acceptance Criteria

1. WHEN a user enters a Jira issue ID matching the format `PROJECT-NUMBER` (one or more uppercase letters, a hyphen, and one or more digits) and submits, THE ID_Lookup_Module SHALL send a request to the Flask_Backend to fetch issue details from the Jira_API
2. WHEN the Jira_API returns issue data, THE ID_Lookup_Module SHALL display the issue summary, type, status, priority, and assignee in the issue header section
3. WHEN the Jira_API returns issue data, THE ID_Lookup_Module SHALL display all child issues, subtasks, linked issues, and test cases in categorized tabs with a count badge on each tab indicating the number of items
4. WHEN the fetched issue has related test case issues (issues whose type name contains "Test"), THE ID_Lookup_Module SHALL display test case details including summary, status, priority, and assignee in a Test_Case_Table format
5. IF the Jira_API returns an error response, THEN THE ID_Lookup_Module SHALL display an error message indicating the cause of the failure returned by the Jira_API
6. IF the user submits an empty or whitespace-only issue ID, THEN THE ID_Lookup_Module SHALL not send a request to the Flask_Backend and SHALL keep the input focused for correction
7. IF the user submits an issue ID that does not match the format `PROJECT-NUMBER`, THEN THE ID_Lookup_Module SHALL display a validation message indicating the expected format
8. WHILE the Flask_Backend is fetching data from the Jira_API, THE ID_Lookup_Module SHALL display a loading indicator and disable the search button until the response is received or a timeout of 30 seconds is reached
9. IF the Flask_Backend does not respond within 30 seconds, THEN THE ID_Lookup_Module SHALL hide the loading indicator and display an error message indicating the request timed out

### Requirement 3: Video File Upload

**User Story:** As a QA Engineer, I want to upload a video recording of an application workflow, so that the system can analyze it and generate test cases automatically.

#### Acceptance Criteria

1. THE Video_Analysis_Module SHALL provide a file upload control that accepts video files in MP4, WebM, and AVI formats
2. WHEN a user selects a video file, THE Video_Analysis_Module SHALL validate that the file type is an accepted video format (MP4, WebM, or AVI) and that the file size is greater than 0 bytes
3. IF a user selects a file that is not an accepted video format, THEN THE Video_Analysis_Module SHALL display an error message specifying the accepted formats (MP4, WebM, AVI)
4. WHEN a user submits a valid video file, THE Video_Analysis_Module SHALL upload the file to the Flask_Backend via a multipart form POST request
5. THE Video_Analysis_Module SHALL enforce a minimum file size of 1 byte and a maximum file size of 100 MB for uploaded videos
6. IF a user submits a video file exceeding 100 MB or a file with 0 bytes, THEN THE Video_Analysis_Module SHALL display an error message indicating the applicable file size constraint
7. WHILE the video file is uploading, THE Video_Analysis_Module SHALL display a determinate progress indicator showing the upload percentage (0–100%)
8. WHEN the video file upload completes successfully, THE Video_Analysis_Module SHALL display a success confirmation message and the filename of the uploaded video
9. IF the video file upload fails due to a network error or server error, THEN THE Video_Analysis_Module SHALL display an error message indicating that the upload failed and SHALL allow the user to retry the upload without re-selecting the file

### Requirement 4: Video Workflow Analysis

**User Story:** As a QA Engineer, I want the system to analyze my uploaded video and identify all user actions, inputs, and system responses, so that I can get a complete breakdown of the workflow.

#### Acceptance Criteria

1. WHEN the Flask_Backend receives a valid video file, THE Video_Processor SHALL extract frames from the video at a configurable interval with a default of 1 frame per second and an allowed range of 0.5 to 5 seconds
2. WHEN frames are extracted, THE Video_Processor SHALL analyze each frame sequence to identify user actions, text inputs, button clicks, navigation events, and system responses
3. WHEN analysis is complete, THE Video_Processor SHALL produce a structured list of workflow steps in chronological order containing no more than 200 steps
4. THE Video_Processor SHALL include for each workflow step: step number, action type (one of: text input, button click, navigation event, system response, or other user action), description (up to 500 characters), and any visible UI element involved
5. IF the Video_Processor fails to analyze the video, THEN THE Flask_Backend SHALL return an error response to the Video_Analysis_Module indicating the specific failure reason
6. WHILE the Video_Processor is analyzing the video, THE Video_Analysis_Module SHALL display a processing status indicator with a message indicating that video analysis is in progress
7. IF the Video_Processor does not complete analysis within 120 seconds, THEN THE Flask_Backend SHALL terminate the processing and return a timeout error response to the Video_Analysis_Module

### Requirement 5: Test Artifact Generation

**User Story:** As a QA Engineer, I want the system to generate comprehensive test artifacts from the analyzed workflow, so that I have ready-to-use test documentation.

#### Acceptance Criteria

1. WHEN workflow analysis is complete and at least one workflow step has been identified, THE Video_Processor SHALL generate at least one Test Scenario per distinct workflow path, where each scenario includes a title, a sequence of workflow steps, and the expected end-state
2. WHEN workflow analysis is complete, THE Video_Processor SHALL generate Test Cases in a Test_Case_Table format with columns: Test Case ID, Title, Preconditions, Steps (numbered sequential actions), Expected Result, and Priority, producing at least one test case per identified workflow step
3. WHEN workflow analysis is complete, THE Video_Processor SHALL generate Negative Test Cases covering at least one test case per workflow step for each applicable category: invalid inputs, unauthorized actions, and error conditions
4. WHEN workflow analysis is complete, THE Video_Processor SHALL generate Edge Cases covering at least one test case per workflow step for each applicable category: boundary values, empty inputs, maximum lengths, and concurrent operation scenarios
5. WHEN workflow analysis is complete, THE Video_Processor SHALL generate UI/UX Validation Points covering at least one validation point per identified UI element for each applicable category: element alignment, responsive behavior, accessibility attributes, and visual consistency against the source video frames
6. THE Video_Processor SHALL assign a priority to each generated test case using exactly one of the values Critical, High, Medium, or Low, where Critical applies to workflow steps that block all subsequent steps, High applies to steps on the main workflow path, Medium applies to alternative paths, and Low applies to cosmetic or non-functional observations
7. THE Video_Processor SHALL generate unique Test Case IDs following the pattern TC-VID-{sequential_number} where sequential_number is a zero-padded 3-digit integer starting at 001 and incrementing by 1 for each test case within a single generation run
8. IF workflow analysis completes and identifies zero workflow steps, THEN THE Video_Processor SHALL return an empty artifact set accompanied by a message indicating that no testable workflows were detected in the video

### Requirement 6: Test Artifact Display

**User Story:** As a QA Engineer, I want the generated test artifacts displayed in organized, readable sections, so that I can review and use them immediately.

#### Acceptance Criteria

1. WHEN test artifacts are generated, THE Video_Analysis_Module SHALL display results in collapsible sections in the following fixed order: Test Scenarios, Detailed Test Cases, Negative Test Cases, Edge Cases, and UI/UX Validation Points, with all sections expanded by default
2. IF a category contains zero generated artifacts, THEN THE Video_Analysis_Module SHALL display that section with a message indicating no items were generated for that category
3. THE Video_Analysis_Module SHALL render Detailed Test Cases in a table with columns in left-to-right order: Test Case ID, Title, Preconditions, Steps, Expected Result, and Priority, displaying up to 200 test cases per category
4. THE Video_Analysis_Module SHALL render Negative Test Cases in a table with the same column structure and column order as Detailed Test Cases
5. THE Video_Analysis_Module SHALL render Edge Cases as a list grouped by category label, where each item displays a description (maximum 500 characters) and its expected behavior (maximum 500 characters)
6. THE Video_Analysis_Module SHALL render UI/UX Validation Points as a checklist where each item displays a label and a pass/fail indicator defaulting to an unset state until explicitly marked by the user
7. WHEN test artifacts are generated, THE Video_Analysis_Module SHALL display a count summary above the collapsible sections showing the number of artifacts generated in each of the five categories as numeric values

### Requirement 7: Flask Backend Video Upload Endpoint

**User Story:** As a developer, I want a dedicated API endpoint for video uploads, so that the frontend can submit video files for processing.

#### Acceptance Criteria

1. THE Flask_Backend SHALL expose a POST endpoint at /api/analyze-video that accepts multipart form data with a video file in a form field named "video", with a maximum file size of 500 MB
2. WHEN the /api/analyze-video endpoint receives a video file that has an accepted format (mp4, avi, mov, webm, mkv) and does not exceed the maximum file size, THE Flask_Backend SHALL save the file to a temporary directory for processing
3. WHEN processing of the uploaded video file is complete and the response has been sent to the client, THE Flask_Backend SHALL delete the temporary video file from the server within 60 seconds
4. IF the /api/analyze-video endpoint receives a request without a "video" form field or with an empty file attachment, THEN THE Flask_Backend SHALL return a 400 status with a JSON response containing an error message indicating that a video file is required
5. IF the /api/analyze-video endpoint receives a file with an extension not in the accepted formats list (mp4, avi, mov, webm, mkv), THEN THE Flask_Backend SHALL return a 400 status with a JSON response containing an error message that lists the accepted formats
6. WHEN processing completes successfully, THE Flask_Backend SHALL return a 200 status with a JSON response containing categorized test artifacts including at minimum: test scenarios, test steps, and expected results
7. IF the uploaded video file exceeds the maximum file size of 500 MB, THEN THE Flask_Backend SHALL return a 413 status with a JSON response containing an error message indicating the maximum allowed file size

### Requirement 8: AI Integration for Video Analysis

**User Story:** As a developer, I want the video analysis to use an AI service for intelligent workflow interpretation, so that the generated test cases are accurate and comprehensive.

#### Acceptance Criteria

1. THE Video_Processor SHALL use an AI API (configurable via environment variables) to analyze extracted video frames
2. THE Video_Processor SHALL send frames with a structured prompt instructing the AI to identify user actions, inputs, navigation, and system responses
3. THE Video_Processor SHALL send a follow-up prompt to generate test artifacts from the identified workflow steps
4. THE Flask_Backend SHALL load the AI API key from an environment variable named AI_API_KEY
5. THE Flask_Backend SHALL load the AI model identifier from an environment variable named AI_MODEL with a default value of "gpt-4o"
6. IF the AI API returns an error or does not respond within 60 seconds, THEN THE Video_Processor SHALL return a descriptive error to the Flask_Backend indicating the analysis failure reason
7. IF AI_API_KEY is not set or empty when a video analysis request is received, THEN THE Flask_Backend SHALL return a 503 status with a JSON error message indicating that video analysis is unavailable due to missing AI configuration

### Requirement 9: Environment Configuration

**User Story:** As a developer, I want all external service credentials managed via environment variables, so that sensitive data is not hardcoded in the application.

#### Acceptance Criteria

1. THE Flask_Backend SHALL load JIRA_URL, JIRA_EMAIL, and JIRA_TOKEN from environment variables at startup for Jira_API connectivity, where JIRA_URL SHALL default to the configured Jira instance URL if not provided, and JIRA_EMAIL and JIRA_TOKEN SHALL default to empty strings if not provided
2. THE Flask_Backend SHALL load AI_API_KEY and AI_MODEL from environment variables at startup for AI service connectivity
3. IF a required environment variable for AI service (AI_API_KEY or AI_MODEL) is missing or empty at startup, THEN THE Flask_Backend SHALL log a warning message to standard output indicating the Video_Analysis_Module will be unavailable
4. THE Flask_Backend SHALL use python-dotenv to load environment variables from a .env file located in the application root directory when the file is present, where real environment variables already set in the OS take precedence over values defined in the .env file
5. IF JIRA_EMAIL or JIRA_TOKEN is empty or missing at startup, THEN THE Flask_Backend SHALL still start successfully but SHALL return an error response when Jira_API requests are attempted with missing credentials
