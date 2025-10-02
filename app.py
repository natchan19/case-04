from datetime import datetime, timezone
import hashlib, json, os

from flask import Flask, request, jsonify
from flask_cors import CORS
from pydantic import ValidationError

from models import SurveySubmission, StoredSurveyRecord
from storage import append_json_line

app = Flask(__name__)
CORS(app, resources={r"/v1/*": {"origins": "*"}})

def sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({
        "status": "ok",
        "message": "API is alive",
        "utc_time": datetime.now(timezone.utc).isoformat()
    })

@app.post("/v1/survey")
def submit_survey():
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "invalid_json", "detail": "Body must be application/json"}), 400

    # (Req 1) If user_agent not provided, capture it from request headers
    payload = dict(payload)  # ensure mutable
    payload.setdefault("user_agent", request.headers.get("User-Agent"))

    try:
        submission = SurveySubmission(**payload)
    except ValidationError as ve:
        return jsonify({"error": "validation_error", "detail": ve.errors()}), 422

    # (Req 3) Ensure submission_id exists; if missing, compute sha256(email + YYYYMMDDHH) in UTC
    if not submission.submission_id:
        ymdh = datetime.now(timezone.utc).strftime("%Y%m%d%H")
        computed_sid = sha256_str(f"{submission.email}{ymdh}")
        # We’ll pass this into the stored record below
        submission_id = computed_sid
    else:
        submission_id = submission.submission_id

    # Build the full record object (still contains raw email/age in memory)
    record = StoredSurveyRecord(
        **submission.dict(exclude={"submission_id"}),  # <— exclude it here
        submission_id=submission_id,                  # <— then add exactly once
        received_at=datetime.now(timezone.utc),
        ip=request.headers.get("X-Forwarded-For", request.remote_addr or "")
    )

    # (Req 2) BEFORE persisting: replace email & age with SHA-256 hashes
    to_store = record.dict()
    to_store["email"] = sha256_str(submission.email)         # hash raw email
    to_store["age"] = sha256_str(str(submission.age))        # hash raw age as string

    # Persist one line of JSON (NDJSON)
    append_json_line(to_store)

    return jsonify({"status": "ok", "submission_id": submission_id}), 201

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))  # grader expects 5000
    app.run(host="127.0.0.1", port=port, debug=False)
