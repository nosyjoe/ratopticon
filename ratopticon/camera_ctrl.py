import subprocess
import psutil
import signal
import os
from flask import render_template, jsonify, send_file, Blueprint, current_app
from datetime import datetime
import time

bp = Blueprint('camera_ctrl', __name__)

# config
recordings_dir = '/home/ratpi/recordings'
libcam_jpeg = '/usr/bin/libcamera-jpeg'
libcam_vid = '/usr/bin/libcamera-vid'
process_name = "libcamera-vid"

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
    update_preview_image()
    return render_template('index.html', state=get_state())

@bp.route('/start_recording', methods=['POST'])
def start_recording():
    global recording_process, recorded_video_path, recording_filename, recording_start, recording_is_stopping
    recording_is_stopping = False
    current_datetime = datetime.now()
    formatted_datetime = current_datetime.strftime("%Y-%m-%d_%H%M")
    recording_filename = 'test-'+formatted_datetime+'.flv'
    recorded_video_path = recordings_dir+"/"+recording_filename
    recording_start = current_datetime
    print("Recording to: "+recorded_video_path)
    recording_process = subprocess.Popen([libcam_vid,
        "--width", str(video_width),
        "--height", str(video_height),
        "--nopreview",
        "--exposure", "long",
        "--sharpness", "1.2",
        "--contrast", "1.4",
        "--brightness", "0.2",
        "--saturation", "1.0",
        "--awb", "auto",
        "--denoise", "auto",
        "--profile", "high",
        "--level", "4.2",
        "--codec", "libav",
        "--libav-format", "flv",
        "-n",
        "--framerate", str(video_fps),
        "-b", str(video_bitrate),
        "--autofocus-mode", "manual",
        "--lens-position", "0.5",
        "--inline",
        "--signal", "1",
        "-t", "0",
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
        return send_file(file_path, mimetype="video/x-flv", as_attachment=True)
    except Exception as e:
        return str(e)
        
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
    for filename in os.listdir(recordings_dir):
        if filename.endswith('.flv'):
            recordings.append(filename)
    recordings.sort(reverse = True)
    return recordings

def get_img_path(app):
    return os.path.join(current_app.root_path, 'static', 'img', 'preview.jpg')

def update_preview_image():
    if recording_process is None:
        img_preview_path = get_img_path(current_app)
        jpg_process = subprocess.Popen([libcam_jpeg,
            "--nopreview",
            "-o", img_preview_path,
            "--width", "640",
            "--height", "360",
            "-t", "50",
        ])
        jpg_process.poll()

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
        "previewFile": img_path,
    }
