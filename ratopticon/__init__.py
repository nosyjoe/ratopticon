from flask import Flask

from ratopticon import camera_ctrl

app = Flask(__name__)

app.register_blueprint(camera_ctrl.bp)

