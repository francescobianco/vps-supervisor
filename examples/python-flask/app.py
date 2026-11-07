import os
import socket

from flask import Flask, jsonify

app = Flask(__name__)


@app.get("/")
def index():
    return jsonify(message=os.environ.get("GREETING", "Hello"), host=socket.gethostname())


@app.get("/health")
def health():
    return "ok"
