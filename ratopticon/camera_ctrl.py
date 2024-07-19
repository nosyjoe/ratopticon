import subprocess
import psutil
import signal
import os
from flask import render_template, jsonify, send_file, Blueprint, current_app, request
from datetime import datetime
import time

bp = Blueprint('camera_ctrl', __name__)

# config
recordings_dir = '/home/ratpi/recordings'

rpi_video_params_file = '/home/ratpi/rpicam_vid_params'
rpi_image_params_file = '/home/ratpi/rpicam_image_params'
# rpi_video_params_file = '/Users/philipp/rpicam_vid_params'
# rpi_image_params_file = '/Users/philipp/rpicam_image_params'
rpicam_jpeg = '/usr/bin/rpicam-jpeg'
rpicam_vid = '/usr/bin/rpicam-vid'
process_name = "rpicam-vid"

# video settings
default_video_options = {
    'timeout': 0,  # '0' means 'infinite
    'width': 1920,
    'height': 1080,
    'bitrate': 2000000,
    'framerate': 30,
    'exposure': 'long',
    'sharpness': 1.2,
    'contrast': 1.4,
    'brightness': 0.2,
    'saturation': 1.0,
    'awb': 'auto',
    'denoise': 'auto',
    'profile': 'high',
    'level': '4.2',
    'codec': 'libav',
    'libav-format': 'mp4',
    'autofocus-mode': 'manual',
    'lens-position': '0.5',
}

user_modifiable_video_settings = [
    'exposure',
    'sharpness',
    'contrast',
    'brightness',
    'saturation',
    'awb',
    'denoise',
    'autofocus-mode',
    'lens-position',
]

video_width=1920
video_height=1080
video_bitrate=2000000
video_fps=30


# global variables
recording_process = None
recorded_video_path = None
recording_filename = None
recording_start = None
recording_is_stopping = False

@bp.route('/')
def index():
    update_preview_image(get_img_path(current_app))
    return render_template('index.html', state=get_state())

@bp.route('/start_recording', methods=['POST'])
def start_recording():
    global recording_process, recorded_video_path, recording_filename, recording_start, recording_is_stopping
    recording_is_stopping = False
    current_datetime = datetime.now()
    formatted_datetime = current_datetime.strftime("%Y-%m-%d_%H%M")
    recording_filename = 'test-'+formatted_datetime+'.mp4'
    recorded_video_path = recordings_dir+"/"+recording_filename
    recording_start = current_datetime
    print("Recording to: "+recorded_video_path)
    recording_process = subprocess.Popen([rpicam_vid,
        "--config", rpi_video_params_file,
        "--inline",
        "--nopreview",
        "--signal",
        "-o", recorded_video_path
    ])
    return get_state()
    


@bp.route('/stop_recording', methods=['POST'])
def stop_recording():
    global recording_process, recording_is_stopping
    recording_is_stopping = True
    # Replace "process_name" with the name of the executable you're looking for
    
    # Replace "signal.SIGTERM" with the desired signal, such as signal.SIGKILL for termination
    #signal_code = signal.SIGTERM
    pid = find_process_by_name(process_name)
    # if pid is not None:
    if recording_process is not None:
        recording_process.send_signal(signal.SIGUSR1)
        time.sleep(0.2)
        recording_process.terminate()
        result = None
        while result is None:
            print("Waiting for recording process to terminate.")
            time.sleep(0.2)
            result = recording_process.poll()
        print(f'Recording process terminated, code: {result}')
    elif pid is not None:
        print(f"Sending signal to process with PID {pid}.")
        send_signal_to_process(pid, signal.SIGUSR1)
        time.sleep(2)
        send_signal_to_process(pid, signal.SIGTERM)
        # time.sleep(3)
        # send_signal_to_process(pid, signal.SIGKILL)
    else:
        print(f"Process with name '{process_name}' not found.")
    
    recording_process = None
    recording_is_stopping = False
    return get_state()

@bp.route('/update_state', methods=['GET'])
def update_state():
    return get_state()

@bp.route('/recordings', methods=['GET'])
def get_recordings():
    return jsonify(get_recordings_list())
    
@bp.route('/recordings/<filename>', methods=['DELETE'])
def delete_recordings(filename):
    try:
        file_path = os.path.join(recordings_dir, filename)
        os.remove(file_path)
        return "File "+file_path+" deleted successfully."
    except OSError as e:
        return f"Error deleting the file: {e}"
    
@bp.route('/download/<filename>', methods=['GET'])
def download(filename):
    try:
        file_path = os.path.join(recordings_dir, filename)
        print("Downloading file: "+file_path)
        return send_file(file_path, mimetype="video/x-mp4", as_attachment=True)
    except Exception as e:
        return str(e)
    
@bp.route('/preview_update', methods=['GET'])
def preview_update():
    try:
        img_preview_path = get_img_path(current_app,)
        update_preview_image(img_preview_path)
        return {
            "imgPreviewPath": "preview.jpg",
        }
    except Exception as e:
        return str(e)
    
@bp.route('/settings', methods=['POST'])
def update_settings():
    merged_options = default_video_options.copy()
    try:
        for key in default_video_options:
            if key in request.form:
                merged_options[key] = request.form[key]

        with open(rpi_video_params_file, 'w') as file:
            for key, value in merged_options.items():
                file.write(f"{key}={value}\n")
        with open(rpi_image_params_file, 'w') as file:
            for key, value in load_user_modifiable_video_settings(merged_options).items():
                file.write(f"{key}={value}\n")

        return load_user_modifiable_video_settings(merged_options)
    except Exception as e:
        return str(e)
    
@bp.route('/settings', methods=['GET'])
def get_settings():
    return load_user_modifiable_video_settings(load_video_settings())
        
def find_process_by_name(process_name):
    for process in psutil.process_iter(['pid', 'name']):
        if process.info['name'] == process_name:
            print("Found process with PID: "+str(process.pid))
            return process.pid
    return None

def send_signal_to_process(pid, signal_code):
    try:
        process = psutil.Process(pid)
        process.send_signal(signal_code)
        print(f"Signal {signal_code} sent to process with PID {pid}.")
    except psutil.NoSuchProcess:
        print(f"Process with PID {pid} not found.")
        
def get_recordings_list():
    recordings = []
    if not os.path.exists(recordings_dir):
        return [f"Folder {recordings_dir} not found."]
    for filename in os.listdir(recordings_dir):
        if filename.endswith('.mp4'):
            recordings.append(filename)
    recordings.sort(reverse = True)
    return recordings

def get_img_path(app, suffix=""):
    return os.path.join(current_app.root_path, 'static', 'img', f"preview{suffix}.jpg")

def update_preview_image(path):
    global recording_process, recording_is_stopping

    if not os.path.exists(rpicam_jpeg):
        return "rpicam-jpeg not found."

    if recording_process is None:
        jpg_process = subprocess.Popen([rpicam_jpeg,
            "--config", rpi_image_params_file,
            "--nopreview",
            "-o", path,
            "--width", "640",
            "--height", "360",
            "-t", "50",
        ])
        jpg_process.poll()
    else:
        print("Recording in progress, not updating preview image.")

def load_video_settings():
    merged_options = default_video_options.copy()
    try:
        with open(rpi_video_params_file, 'r') as file:
            lines = file.readlines()
            for line in lines:
                key, value = line.split('=')
                merged_options[key] = value.rstrip('\n\r')
        return merged_options
    except FileNotFoundError:
        return merged_options
    
def load_user_modifiable_video_settings(all_settings):
    return {key: value for key, value in all_settings.items() if key in user_modifiable_video_settings}

def get_state():
    global recording_process, recording_filename, recording_start, recording_is_stopping
    pid = find_process_by_name(process_name)
    startString = ""
    formatted_duration = ""
    if recording_start != None:
        startString = recording_start.strftime("%Y-%m-%d, %H:%M")
        duration = datetime.now() - recording_start
        formatted_duration = str(duration).split('.')[0]  # Removing microseconds


    img_path = "header.jpg"
    img_preview_path = get_img_path(current_app)
    if os.path.isfile(img_preview_path):
       img_path = "preview.jpg"


    return {
        "isRecording": pid != None,
        "canStartRecording": pid == None and recording_is_stopping == False,
        "recordingFilename": recording_filename,
        "recordingStartTime": startString,
        "recordingDuration": formatted_duration,
        "recordings": get_recordings_list(),
        "previewFile": img_path
    }
