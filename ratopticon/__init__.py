from flask import Flask
from flask_bootstrap import Bootstrap5

from ratopticon import camera_ctrl

app = Flask(__name__)
bootstrap = Bootstrap5(app)

app.register_blueprint(camera_ctrl.bp)
