from flask import Flask, render_template, request, jsonify
import requests
import PyPDF2
from io import BytesIO

app = Flask(__name__)

API_KEY = "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"
API_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = """
You are Nexora AI, a smart, futuristic, friendly AI assistant created by Nexora Tech Studio.
Give clear, useful, simple answers.
If file content is provided, use it in your answer.
"""

@app.route("/")
def home():
    return render_template("index.html")


def extract_pdf_text(file_storage):
    try:
        pdf_reader = PyPDF2.PdfReader(BytesIO(file_storage.read()))
        text = []
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
        return "\n".join(text).strip()
    except Exception:
        return ""


@app.route("/chat", methods=["POST"])
def chat():
    try:
        user_message = request.form.get("message", "").strip()
        model_name = request.form.get("model", "mistralai/mistral-7b-instruct:free").strip()

        if not user_message:
            return jsonify({"reply": "Please type a message."}), 400

        file_text = ""
        uploaded_file = request.files.get("file")

        if uploaded_file and uploaded_file.filename:
            filename = uploaded_file.filename.lower()

            if filename.endswith(".txt"):
                file_text = uploaded_file.read().decode("utf-8", errors="ignore").strip()

            elif filename.endswith(".pdf"):
                file_text = extract_pdf_text(uploaded_file).strip()

        final_user_message = user_message

        if file_text:
            final_user_message += (
                "\n\nAttached file content:\n"
                "--------------------\n"
                f"{file_text[:12000]}"
            )

        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://127.0.0.1:5000",
            "X-Title": "Nexora AI"
        }

        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": final_user_message}
            ]
        }

        response = requests.post(API_URL, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()

        ai_reply = result["choices"][0]["message"]["content"]
        return jsonify({"reply": ai_reply})

    except requests.exceptions.HTTPError:
        return jsonify({"reply": f"HTTP Error: {response.status_code} - {response.text}"}), 500
    except requests.exceptions.Timeout:
        return jsonify({"reply": "Request timed out. Please try again."}), 500
    except Exception as e:
        return jsonify({"reply": f"Error: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True)