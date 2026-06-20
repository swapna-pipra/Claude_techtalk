from flask import Flask, request, jsonify, send_from_directory
import requests
from requests.auth import HTTPBasicAuth
import os
import tempfile
import base64
import json

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

JIRA_URL   = os.environ.get("JIRA_URL",   "")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL", "")
JIRA_TOKEN = os.environ.get("JIRA_TOKEN", "")

AI_API_KEY = os.environ.get("AI_API_KEY", "")
AI_MODEL = os.environ.get("AI_MODEL", "gemini-2.5-flash")

if not AI_API_KEY:
    print("⚠️  WARNING: AI_API_KEY not set. Video analysis will be unavailable.")
else:
    print("✅ AI_API_KEY configured. Using Google Gemini for video analysis.")

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

AUTH    = HTTPBasicAuth(JIRA_EMAIL, JIRA_TOKEN)
HEADERS = {'Content-Type': 'application/json', 'Accept': 'application/json'}

ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'webm', 'mkv'}


class VideoProcessor:
    """Processes video files using Google Gemini API for analysis."""

    def __init__(self, api_key, model):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    def extract_frames(self, video_path, interval=2.0):
        """Extract frames from video at specified interval, resize, encode as base64 JPEG."""
        import cv2

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError("Cannot open video file. The file may be corrupt or use an unsupported codec.")

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30.0

        frame_interval = int(fps * interval)
        if frame_interval < 1:
            frame_interval = 1

        frames = []
        frame_count = 0
        max_frames = 15  # Limit for Gemini free tier

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % frame_interval == 0:
                # Resize to 512p max to reduce payload size
                height, width = frame.shape[:2]
                max_height = 512
                if height > max_height:
                    scale = max_height / height
                    new_width = int(width * scale)
                    frame = cv2.resize(frame, (new_width, max_height))

                # Encode as JPEG and convert to base64
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                frame_b64 = base64.b64encode(buffer).decode('utf-8')
                frames.append(frame_b64)

                if len(frames) >= max_frames:
                    break

            frame_count += 1

        cap.release()
        return frames

    def _call_gemini(self, parts, max_tokens=8192):
        """Call Google Gemini API with given content parts."""
        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": 0.2
            }
        }

        resp = requests.post(url, json=payload, timeout=120)

        if resp.status_code != 200:
            error_msg = resp.text[:500]
            raise RuntimeError(f"Gemini API error ({resp.status_code}): {error_msg}")

        data = resp.json()

        # Extract text from response
        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError("Gemini returned no candidates.")

        content = candidates[0].get("content", {})
        parts_resp = content.get("parts", [])
        if not parts_resp:
            raise RuntimeError("Gemini returned empty response.")

        text = parts_resp[0].get("text", "").strip()
        return text

    def analyze_workflow(self, frames):
        """Send frames to Gemini to identify user workflow steps."""
        selected_frames = frames[:10]  # Use up to 10 frames

        # Build parts: text prompt + inline images
        parts = [
            {
                "text": (
                    "You are a Senior QA Engineer analyzing application workflow screenshots. "
                    "Identify ALL user actions, inputs, and system responses visible in these sequential screenshots. "
                    "Return a JSON array of workflow steps. Each step should have: "
                    "step_number (int), action_type (text_input|button_click|navigation|system_response|other), "
                    "description (string, max 500 chars), ui_element (string or null). "
                    "Return ONLY the valid JSON array, no markdown formatting, no code fences, no explanations."
                )
            }
        ]

        for frame_b64 in selected_frames:
            parts.append({
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": frame_b64
                }
            })

        parts.append({
            "text": "Now analyze the screenshots above and return the JSON array of workflow steps."
        })

        content = self._call_gemini(parts, max_tokens=4096)

        # Strip markdown code fences if present
        if content.startswith("```"):
            lines = content.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)

        try:
            workflow_steps = json.loads(content)
        except json.JSONDecodeError:
            # Try to find JSON array in the response
            start = content.find("[")
            end = content.rfind("]")
            if start != -1 and end != -1:
                try:
                    workflow_steps = json.loads(content[start:end + 1])
                except json.JSONDecodeError:
                    workflow_steps = []
            else:
                workflow_steps = []

        return workflow_steps

    def generate_artifacts(self, workflow_steps):
        """Generate test artifacts from workflow steps using Gemini."""
        if not workflow_steps:
            return {
                "test_scenarios": [],
                "test_cases": [],
                "negative_cases": [],
                "edge_cases": [],
                "ui_ux_points": [],
                "message": "No testable workflows detected in the video."
            }

        prompt = (
            f"Based on these workflow steps:\n\n{json.dumps(workflow_steps, indent=2)}\n\n"
            "Generate comprehensive test artifacts in this exact JSON structure:\n"
            "{\n"
            '  "test_scenarios": [\n'
            '    {"title": "...", "steps": ["step1", "step2", ...], "expected_end_state": "..."}\n'
            "  ],\n"
            '  "test_cases": [\n'
            '    {"test_case_id": "TC-VID-001", "title": "...", "preconditions": "...", '
            '"steps": ["step1", "step2", ...], "expected_result": "...", "priority": "High|Medium|Low|Critical"}\n'
            "  ],\n"
            '  "negative_cases": [\n'
            '    {"test_case_id": "TC-VID-NNN", "title": "...", "preconditions": "...", '
            '"steps": ["step1", ...], "expected_result": "...", "priority": "..."}\n'
            "  ],\n"
            '  "edge_cases": [\n'
            '    {"category": "boundary_values|empty_inputs|max_lengths|concurrent_ops", '
            '"description": "...", "expected_behavior": "..."}\n'
            "  ],\n"
            '  "ui_ux_points": [\n'
            '    {"category": "alignment|responsive|accessibility|visual_consistency", "label": "..."}\n'
            "  ]\n"
            "}\n\n"
            "Rules:\n"
            "- Test case IDs must follow TC-VID-NNN format (sequential, starting at 001)\n"
            "- Continue numbering sequentially across test_cases and negative_cases\n"
            "- Priority must be exactly one of: Critical, High, Medium, Low\n"
            "- Generate at least 3 test scenarios, 5 test cases, 3 negative cases, 4 edge cases, and 5 UI/UX points\n"
            "- Be specific and detailed based on the observed workflow\n"
            "- Return ONLY the JSON object, no markdown, no code fences, no explanations"
        )

        parts = [{"text": prompt}]
        content = self._call_gemini(parts, max_tokens=8192)

        # Strip markdown code fences if present
        if content.startswith("```"):
            lines = content.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)

        try:
            artifacts = json.loads(content)
        except json.JSONDecodeError:
            # Try to find JSON object in the response
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1:
                try:
                    artifacts = json.loads(content[start:end + 1])
                except json.JSONDecodeError:
                    artifacts = {
                        "test_scenarios": [],
                        "test_cases": [],
                        "negative_cases": [],
                        "edge_cases": [],
                        "ui_ux_points": []
                    }
            else:
                artifacts = {
                    "test_scenarios": [],
                    "test_cases": [],
                    "negative_cases": [],
                    "edge_cases": [],
                    "ui_ux_points": []
                }

        # Ensure all keys exist
        for key in ["test_scenarios", "test_cases", "negative_cases", "edge_cases", "ui_ux_points"]:
            if key not in artifacts:
                artifacts[key] = []

        return artifacts

    def process(self, video_path):
        """Full pipeline: extract frames → analyze workflow → generate artifacts."""
        frames = self.extract_frames(video_path)

        if not frames:
            return {
                "success": True,
                "artifacts": {
                    "test_scenarios": [],
                    "test_cases": [],
                    "negative_cases": [],
                    "edge_cases": [],
                    "ui_ux_points": []
                },
                "summary": {
                    "test_scenarios": 0,
                    "test_cases": 0,
                    "negative_cases": 0,
                    "edge_cases": 0,
                    "ui_ux_points": 0
                },
                "message": "No frames could be extracted from the video."
            }

        workflow_steps = self.analyze_workflow(frames)
        artifacts = self.generate_artifacts(workflow_steps)

        # Remove the message key if present
        message = artifacts.pop("message", None)

        summary = {
            "test_scenarios": len(artifacts.get("test_scenarios", [])),
            "test_cases": len(artifacts.get("test_cases", [])),
            "negative_cases": len(artifacts.get("negative_cases", [])),
            "edge_cases": len(artifacts.get("edge_cases", [])),
            "ui_ux_points": len(artifacts.get("ui_ux_points", []))
        }

        result = {
            "success": True,
            "artifacts": artifacts,
            "summary": summary
        }

        if message:
            result["message"] = message

        return result


@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'index.html')


@app.route('/api/jira', methods=['POST'])
def jira_proxy():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request body'}), 400

        endpoint = data.get('endpoint', '').strip()
        if not endpoint:
            return jsonify({'error': 'Missing endpoint'}), 400

        url  = JIRA_URL.rstrip('/') + endpoint
        resp = requests.get(url, auth=AUTH, headers=HEADERS, timeout=30)

        try:
            return jsonify(resp.json()), resp.status_code
        except ValueError:
            return jsonify({'error': f'Non-JSON response from Jira (HTTP {resp.status_code}): {resp.text[:300]}'}), resp.status_code

    except requests.exceptions.ConnectionError:
        return jsonify({'error': 'Cannot connect to Jira. Check JIRA_URL and your network.'}), 503
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Jira request timed out.'}), 504
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate-testcases', methods=['POST'])
def generate_testcases():
    """Fetches Jira issue description and generates test cases using Gemini AI."""

    if not AI_API_KEY:
        return jsonify({'error': 'AI test case generation is unavailable. AI_API_KEY is not configured.'}), 503

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request body'}), 400

    issue_key = (data.get('issueKey') or '').strip().upper()
    if not issue_key:
        return jsonify({'error': 'Missing issueKey'}), 400

    # Fetch issue details from Jira (summary + description + acceptance criteria)
    try:
        url = JIRA_URL.rstrip('/') + f'/rest/api/3/issue/{issue_key}?fields=summary,description,issuetype,priority,labels'
        resp = requests.get(url, auth=AUTH, headers=HEADERS, timeout=30)

        if resp.status_code == 404:
            return jsonify({'error': f'Issue {issue_key} not found in Jira.'}), 404
        if resp.status_code != 200:
            return jsonify({'error': f'Jira error (HTTP {resp.status_code})'}), resp.status_code

        issue_data = resp.json()
    except requests.exceptions.ConnectionError:
        return jsonify({'error': 'Cannot connect to Jira.'}), 503
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Jira request timed out.'}), 504

    fields = issue_data.get('fields', {})
    summary = fields.get('summary', '')
    description_raw = fields.get('description', {})
    issue_type = fields.get('issuetype', {}).get('name', '')
    priority = fields.get('priority', {}).get('name', '')

    # Convert Atlassian Document Format (ADF) to plain text
    description = _adf_to_text(description_raw) if isinstance(description_raw, dict) else (description_raw or '')

    if not description and not summary:
        return jsonify({'error': f'Issue {issue_key} has no summary or description to analyze.'}), 400

    # Build prompt for Gemini
    story_context = f"Issue Key: {issue_key}\nType: {issue_type}\nPriority: {priority}\nSummary: {summary}\n\nDescription:\n{description}"

    prompt = (
        f"You are a Senior QA Engineer. Based on this Jira story/ticket, generate comprehensive test cases.\n\n"
        f"--- TICKET ---\n{story_context}\n--- END TICKET ---\n\n"
        "Generate test artifacts in this exact JSON structure:\n"
        "{\n"
        '  "test_scenarios": [\n'
        '    {"title": "...", "steps": ["step1", "step2", ...], "expected_end_state": "..."}\n'
        "  ],\n"
        '  "test_cases": [\n'
        '    {"test_case_id": "TC-001", "title": "...", "preconditions": "...", '
        '"steps": ["step1", "step2", ...], "expected_result": "...", "priority": "High|Medium|Low|Critical"}\n'
        "  ],\n"
        '  "negative_cases": [\n'
        '    {"test_case_id": "TC-NNN", "title": "...", "preconditions": "...", '
        '"steps": ["step1", ...], "expected_result": "...", "priority": "..."}\n'
        "  ],\n"
        '  "edge_cases": [\n'
        '    {"category": "boundary_values|empty_inputs|max_lengths|concurrent_ops", '
        '"description": "...", "expected_behavior": "..."}\n'
        "  ],\n"
        '  "ui_ux_points": [\n'
        '    {"category": "alignment|responsive|accessibility|visual_consistency", "label": "..."}\n'
        "  ]\n"
        "}\n\n"
        "Rules:\n"
        "- Test case IDs must follow TC-NNN format (sequential, starting at 001)\n"
        "- Continue numbering sequentially across test_cases and negative_cases\n"
        "- Priority must be exactly one of: Critical, High, Medium, Low\n"
        "- Generate at least 3 test scenarios, 5 test cases, 3 negative cases, 4 edge cases, and 5 UI/UX points\n"
        "- Be specific and detailed based on the ticket's requirements and acceptance criteria\n"
        "- Return ONLY the JSON object, no markdown, no code fences, no explanations"
    )

    # Call Gemini
    try:
        processor = VideoProcessor(AI_API_KEY, AI_MODEL)
        parts = [{"text": prompt}]
        content = processor._call_gemini(parts, max_tokens=8192)

        # Strip markdown code fences if present
        if content.startswith("```"):
            lines = content.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)

        try:
            artifacts = json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1:
                artifacts = json.loads(content[start:end + 1])
            else:
                artifacts = {"test_scenarios": [], "test_cases": [], "negative_cases": [], "edge_cases": [], "ui_ux_points": []}

        # Ensure all keys exist
        for key in ["test_scenarios", "test_cases", "negative_cases", "edge_cases", "ui_ux_points"]:
            if key not in artifacts:
                artifacts[key] = []

        summary_counts = {
            "test_scenarios": len(artifacts.get("test_scenarios", [])),
            "test_cases": len(artifacts.get("test_cases", [])),
            "negative_cases": len(artifacts.get("negative_cases", [])),
            "edge_cases": len(artifacts.get("edge_cases", [])),
            "ui_ux_points": len(artifacts.get("ui_ux_points", []))
        }

        return jsonify({
            "success": True,
            "issueKey": issue_key,
            "summary": summary,
            "artifacts": artifacts,
            "counts": summary_counts
        }), 200

    except Exception as e:
        return jsonify({'error': f'AI generation failed: {str(e)}'}), 500


def _adf_to_text(adf):
    """Convert Atlassian Document Format (ADF) JSON to plain text."""
    if not adf or not isinstance(adf, dict):
        return ''
    texts = []

    def walk(node):
        if isinstance(node, str):
            texts.append(node)
            return
        if isinstance(node, dict):
            if node.get('type') == 'text':
                texts.append(node.get('text', ''))
            elif node.get('type') == 'hardBreak':
                texts.append('\n')
            for child in node.get('content', []):
                walk(child)
        if isinstance(node, list):
            for item in node:
                walk(item)

    walk(adf)
    return '\n'.join(line for line in ''.join(texts).split('\n') if line.strip() or True)


@app.route('/api/analyze-video', methods=['POST'])
def analyze_video():
    """Accepts video upload, extracts frames, analyzes with Gemini AI, returns test artifacts."""

    # Check if AI is configured
    if not AI_API_KEY:
        return jsonify({'error': 'Video analysis is unavailable. AI_API_KEY is not configured. Get a free key at https://aistudio.google.com/apikey'}), 503

    # Validate file presence
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided. Please upload a video file.'}), 400

    file = request.files['video']
    if not file.filename:
        return jsonify({'error': 'No file selected.'}), 400

    # Validate file extension
    filename = file.filename
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        return jsonify({
            'error': f'Unsupported file format ".{ext}". Accepted formats: {", ".join(sorted(ALLOWED_VIDEO_EXTENSIONS))}'
        }), 400

    # Validate file size
    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)

    if file_size == 0:
        return jsonify({'error': 'The uploaded file is empty.'}), 400

    if file_size > 500 * 1024 * 1024:
        return jsonify({'error': 'File too large. Maximum size is 500 MB.'}), 413

    # Save to temp file and process
    tmp_path = None
    try:
        suffix = f'.{ext}'
        fd, tmp_path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        file.save(tmp_path)

        processor = VideoProcessor(AI_API_KEY, AI_MODEL)
        result = processor.process(tmp_path)
        result['filename'] = filename

        return jsonify(result), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Video analysis failed: {str(e)}'}), 500
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print("=" * 50)
    print("  Jira Issue Explorer + QA Test Case Generator")
    print(f"  http://localhost:{port}")
    print("  AI Provider: Google Gemini (free tier)")
    print("=" * 50)
    app.run(debug=False, port=port, host='127.0.0.1')
