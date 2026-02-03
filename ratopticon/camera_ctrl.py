import subprocess
import psutil
import signal
import os
from flask import render_template, jsonify, send_file, Blueprint, current_app, request
from datetime import datetime
import time
import re

bp = Blueprint('camera_ctrl', __name__)

# config
recordings_dir = os.environ.get('RATOPTICON_RECORDINGS_DIR', '/home/ratpi/recordings')

rpi_video_params_file = os.environ.get('RATOPTICON_VIDEO_PARAMS_FILE', '/home/ratpi/rpicam_vid_params')
rpi_image_params_file = os.environ.get('RATOPTICON_IMAGE_PARAMS_FILE', '/home/ratpi/rpicam_image_params')
lockfile_preview = os.environ.get('RATOPTICON_PREVIEW_LOCK', '/home/ratpi/preview.lock')
lockfile_recording = os.environ.get('RATOPTICON_RECORDING_LOCK', '/home/ratpi/recording.lock')
# rpi_video_params_file = '/Users/philipp/rpicam_vid_params'
# rpi_image_params_file = '/Users/philipp/rpicam_image_params'
rpicam_jpeg = '/usr/bin/rpicam-jpeg'
rpicam_vid = '/usr/bin/rpicam-vid'
process_name = "rpicam-vid"


# video settings
DEFAULT_VIDEO_OPTIONS = {
    'timeout': 0,  # '0' means 'infinite
    'width': 1920,
    'height': 1080,
    'bitrate': 4000000,
    'framerate': 15,
    'exposure': 'long',
    # 0.0 - open end. 1.0 is default sharpness, < is less, > is more
    'sharpness': 1.0,
    # spectrum from 0.0 to Double.max. 1.0 is default, value < 1.0 is less, value > is more
    'contrast': 1.4,
    # spectrum from -1.0 to 1.0. 0.0 is standard, value < 1.0 is less, value > is more
    'brightness': 0.0,
    # spectrum from 0.0 to Double.max. 1.0 is default, value < 1.0 is less, value > is more
    'saturation': 1.0,
    'awb': 'auto',
    'denoise': 'auto',
    'autofocus-mode': 'continuous',
    'lens-position': '0.5',
}

user_modifiable_video_settings = [
    'bitrate',
    'framerate',
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

user_modifiable_image_settings = [
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

user_modifiable_video_settings_info = {
    'bitrate': {
        'type': 'number',
        'hint': ""
    },
    'framerate': {
        'type': 'number',
        'hint': ""
    },
    'exposure': {
        'type': 'select',
        'options': ['sport', 'normal', 'long'],
        'hint': ""
    },
    'sharpness': {
        'type': 'number',
        'hint': "0.0 - 10. 1.0: default, < 1: less, > 1 is more"
    },
    'contrast': {
        'type': 'number',
        'hint': ""
    },
    'brightness': {
        'type': 'number',
        'hint': ""
    },
    'saturation': {
        'type': 'number',
        'hint': ""
    },
    'awb': {
        'type': 'select',
        'options': ['auto', 'incandescent', 'tungsten', 'fluorescent', 'indoor', 'daylight', 'cloudy'],
        'hint': ""
    },
    'denoise': {
        'type': 'select',
        'options': ['auto', 'off', 'cdn_off', 'cdn_fast', 'cdn_hq'],
        'hint': "",
    },
    'autofocus-mode': {
        'type': 'select',
        'options': ['default', 'manual', 'auto', 'continuous'],
        'hint': "",
    },
    'lens-position': {
        'type': 'number',
        'hint': "0.0: infinity, 1 / number = focus distance, e.g. 2.0 = 0.5m"
    }
}


# global variables
recording_process = None
recorded_video_path = None
recording_filename = None
recording_start = None
recording_is_stopping = False

@bp.route('/')
def index():
    return render_template('index.html', state=get_state(), ratpi_nr=get_host_number(), 
                           currentSettings=get_current_settings_and_info())

def augment_setting_with_hint(key, value):
    new_value = user_modifiable_video_settings_info[key]
    new_value['value'] = value
    return new_value

@bp.route('/start_recording', methods=['POST'])
def start_recording():
    global recording_process, recorded_video_path, recording_filename, recording_start, recording_is_stopping
    stop_recording()
    lock_recording()
    time.sleep(1.5)
    
    recording_is_stopping = False

    current_datetime = datetime.now()
    formatted_datetime = current_datetime.strftime("%Y-%m-%d_%H%M%S")
    base_name = 'recording-'+formatted_datetime
    recording_start = current_datetime
    
    record_params = []
    if is_pi5():
        print("Raspberry Pi 5 detected.")
        recording_filename = base_name+'.mp4'
        recorded_video_path = recordings_dir+"/"+recording_filename
        record_params = [rpicam_vid,
            "--config", rpi_video_params_file,
            "--inline",
            "--nopreview",
            "--signal",
            '--profile', 'high',
            '--level', '4.2',
            '--codec', 'libav',
            '--libav-format', 'mp4',
            "-o", recorded_video_path
        ]
    else:
        print("Raspberry Pi 4 or lower detected.")
        recording_filename = base_name+'.h264'
        recorded_video_path = recordings_dir+"/"+recording_filename
        record_params = [rpicam_vid,
            "--config", rpi_video_params_file,
            "--nopreview",
            "--signal",
            "-o", recorded_video_path
        ]

    print("Recording to: "+recorded_video_path)

    

    recording_process = subprocess.Popen(record_params)
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
        recording_process.send_signal(signal.SIGUSR2)
        time.sleep(0.5)
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
    

    # if not is_pi5():
        # mkv_process = subprocess.Popen(['mkvmerge', '-o', 'test.mkv', '--timecodes', '0:timestamps.txt', h264file])

    recording_process = None
    recording_is_stopping = False
    unlock_recording()
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
        file_path = resolve_recording_path(filename)
        if file_path is None:
            return jsonify({"error": "Invalid filename."}), 400
        os.remove(file_path)
        return "File "+file_path+" deleted successfully."
    except OSError as e:
        return jsonify({"error": f"Error deleting the file: {e}"}), 500
    
@bp.route('/download/<filename>', methods=['GET'])
def download(filename):
    try:
        file_path = resolve_recording_path(filename)
        if file_path is None:
            return jsonify({"error": "Invalid filename."}), 400
        print("Downloading file: "+file_path)
        file_root, file_extension = os.path.splitext(filename)
        # return send_file(file_path, mimetype="video/x-"+file_extension.lstrip('.'), as_attachment=True)
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@bp.route('/preview_update', methods=['GET'])
def preview_update():
    if is_recording_locked():
        return "Recording in progress, not updating preview image."
    try:
        img_preview_path = get_img_path(current_app)
        update_preview_image(img_preview_path)
        return {
            "imgPreviewPath": "preview.jpg",
        }
    except Exception as e:
        return str(e)
    
@bp.route('/settings', methods=['POST'])
def update_settings():
    try:
        merged_options = {}
        for key in DEFAULT_VIDEO_OPTIONS:
            merged_options[key] = DEFAULT_VIDEO_OPTIONS[key]
            if key in request.form:
                merged_options[key] = request.form[key]

        write_settings_to_files(merged_options)

        return get_settings()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@bp.route('/settings', methods=['GET'])
def get_settings():
    return {
        "currentSettings": load_user_modifiable_video_settings(load_video_settings()),
        "defaultSettings": load_user_modifiable_video_settings(DEFAULT_VIDEO_OPTIONS)
    }

@bp.route('/settings', methods=['DELETE'])
def delete_settings():
    try:
        write_settings_to_files(DEFAULT_VIDEO_OPTIONS)
        return {'success': True}
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
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
        if filename.endswith('.mp4') or filename.endswith('.h264') or filename.endswith('.mkv'):
            recordings.append(filename)
    recordings.sort(reverse = True)
    return recordings

def resolve_recording_path(filename):
    if os.path.sep in filename or (os.path.altsep and os.path.altsep in filename):
        return None
    base_dir = os.path.abspath(recordings_dir)
    candidate_path = os.path.abspath(os.path.join(base_dir, filename))
    if os.path.commonpath([base_dir, candidate_path]) != base_dir:
        return None
    return candidate_path

def get_img_path(app, suffix=""):
    return os.path.join(current_app.root_path, 'static', 'img', f"preview{suffix}.jpg")

def update_preview_image(path):
    global recording_process, recording_is_stopping
    if is_recording_locked():
        return "Recording in progress, not updating preview image."

    lock_preview()

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
        return_code = jpg_process.poll()
        print(f"Return code: {return_code}")
        unlock_preview()
    else:
        print("Recording in progress, not updating preview image.")
        unlock_preview()

def load_video_settings():
    try:
        merged_options = {}
        for key in DEFAULT_VIDEO_OPTIONS:
            merged_options[key] = DEFAULT_VIDEO_OPTIONS[key]
        with open(rpi_video_params_file, 'r') as file:
            lines = file.readlines()
            for line in lines:
                key, value = line.split('=')
                merged_options[key] = value.rstrip('\n\r')
        return merged_options
    except FileNotFoundError:
        return DEFAULT_VIDEO_OPTIONS
    except ValueError:
        print(f"ValueError")
        return DEFAULT_VIDEO_OPTIONS
    
def load_user_modifiable_video_settings(all_settings):
    return {key: value for key, value in all_settings.items() if key in user_modifiable_video_settings}

def load_user_modifiable_image_settings(all_settings):
    return {key: value for key, value in all_settings.items() if key in user_modifiable_image_settings}

def is_pi5():
    with open('/proc/device-tree/model') as f:
        model = f.read()
    return model.startswith('Raspberry Pi 5')

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
        "isRecording": is_recording_locked(),
        "canStartRecording": pid == None and recording_is_stopping == False,
        "recordingFilename": recording_filename,
        "recordingStartTime": startString,
        "recordingDuration": formatted_duration,
        "recordings": get_recordings_list(),
        "previewFile": img_path
    }

def get_host_number(): 
    hostname = os.uname()[1]

    match = re.search(r'(\d+)$', hostname)
    if match:
        return match.group(1)
    else:
        return "?"

def get_current_settings_and_info():
    currentSettings = load_user_modifiable_video_settings(load_video_settings())
    return {k: augment_setting_with_hint(k, v) for k, v in currentSettings.items()}

def create_lock_file(lock_file_path):
    ensure_parent_dir(lock_file_path)
    with open(lock_file_path, 'w') as lock_file:
        lock_file.write('lock')

def remove_lock_file(lock_file_path):
    if os.path.exists(lock_file_path):
        os.remove(lock_file_path)

def is_locked(lock_file_path):
    return os.path.exists(lock_file_path)

def is_recording_locked():
    return is_locked(lockfile_recording)

def lock_recording():
    create_lock_file(lockfile_recording)

def unlock_recording():
    remove_lock_file(lockfile_recording)

def is_preview_locked():
    return is_locked(lockfile_preview)

def lock_preview():
    create_lock_file(lockfile_preview)

def unlock_preview():
    remove_lock_file(lockfile_preview)

def write_settings_to_files(settings):
    print(settings)
    print("")
    print(f"defaults: {DEFAULT_VIDEO_OPTIONS}")

    ensure_parent_dir(rpi_video_params_file)
    with open(rpi_video_params_file, 'w') as file:
            for key, value in settings.items():
                file.write(f"{key}={value}\n")
    ensure_parent_dir(rpi_image_params_file)
    with open(rpi_image_params_file, 'w') as file:
        for key, value in load_user_modifiable_image_settings(settings).items():
            file.write(f"{key}={value}\n")

def ensure_parent_dir(path):
    parent_dir = os.path.dirname(path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
