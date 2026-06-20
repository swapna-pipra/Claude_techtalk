from flask import Flask, request, jsonify, send_from_directory
import requests
from requests.auth import HTTPBasicAuth
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

JIRA_URL   = os.environ.get("JIRA_URL",   "https://pipra-solutions.atlassian.net")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL", "")
JIRA_TOKEN = os.environ.get("JIRA_TOKEN", "")

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

AUTH    = HTTPBasicAuth(JIRA_EMAIL, JIRA_TOKEN)
HEADERS = {'Content-Type': 'application/json', 'Accept': 'application/json'}


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


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print("=" * 50)
    print("  Jira Issue Explorer")
    print(f"  http://localhost:{port}")
    print("=" * 50)
    app.run(debug=False, port=port, host='127.0.0.1')
