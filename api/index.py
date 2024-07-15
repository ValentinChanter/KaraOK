from flask import Flask
from flask_cors import CORS

from api.separate import separate
from api.transcribe import transcribe
from api.render import render

app = Flask(__name__)
app.register_blueprint(separate)
app.register_blueprint(transcribe)
app.register_blueprint(render)