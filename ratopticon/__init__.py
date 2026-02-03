from flask import Flask
from flask_bootstrap import Bootstrap

from ratopticon import camera_ctrl

app = Flask(__name__)
bootstrap = Bootstrap(app)
app.config['BOOTSTRAP_SERVE_LOCAL'] = True

app.register_blueprint(camera_ctrl.bp)
