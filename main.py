import subprocess
import psutil
import signal
import os
from flask import Flask, render_template, request, jsonify, send_file
from datetime import datetime

app = Flask(__name__)

recordings_dir = './recordings'
recording_process = None
recorded_video_path = None
recording_filename = None
process_name = "libcamera-vid"

state = {
    "recording": False,
    "recordings_list": []
}

@app.route('/')
def index():
    return render_template('index.html', state=get_state())

@app.route('/start_recording', methods=['POST'])
def start_recording():
    global recording_process, recorded_video_path, recording_filename
    current_datetime = datetime.now()
    formatted_datetime = current_datetime.strftime("%Y-%m-%d_%H%M")
    recording_filename = 'test-'+formatted_datetime+'.flv'
    recorded_video_path = recordings_dir+"/"+recording_filename
    recording_process = subprocess.Popen(['libcamera-vid',
        "--width", "1920",
        "--height", "1080",
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
        "--framerate", "30",
        "-b", "2000000",
        "--autofocus-mode", "manual",
        "--lens-position", "0.5",
        "--inline",
        "--signal", "1",
        "-t", "0",
        "-o", recorded_video_path
    ])
    return get_state()
    


@app.route('/stop_recording', methods=['POST'])
def stop_recording():
    global recording_process
    # Replace "process_name" with the name of the executable you're looking for
    
    # Replace "signal.SIGTERM" with the desired signal, such as signal.SIGKILL for termination
    #signal_code = signal.SIGTERM
    pid = find_process_by_name(process_name)
    #if pid is not None:
    if recording_process is not None:
        recording_process.send_signal(signal.SIGUSR1)
        recording_process.terminate()
    #    send_signal_to_process(pid, signal_code)
    elif pid != None:
        send_signal_to_process(pid, signal.SIGUSR1)
        send_signal_to_process(pid, signal.SIGKILL) 
    else:
        print(f"Process with name '{process_name}' not found.")
    
    return get_state()

@app.route('/check_recording')
def check_recording():
    global recording_process
    if recording_process and recording_process.poll() is None:
        return "true"
    else:
        return "false"

@app.route('/recordings', methods=['GET'])
def get_recordings():
    return jsonify(get_recordings_list())
    
@app.route('/recordings/<filename>', methods=['DELETE'])
def delete_recordings(filename):
    try:
        file_path = os.path.join(recordings_dir, filename)
        os.remove(file_path)
        return "File "+file_path+" deleted successfully."
    except OSError as e:
        return f"Error deleting the file: {e}"
    
@app.route('/download/<filename>', methods=['GET'])
def download(filename):
    try:
        return send_file(os.path.join(recordings_dir, filename), mimetype="video/x-flv", as_attachment=False)
    except Exception as e:
        return str(e)
        
def find_process_by_name(process_name):
    for process in psutil.process_iter(['pid', 'name']):
        if process.info['name'] == process_name:
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
    
def get_state():
    global recording_process, recording_filename
    pid = find_process_by_name(process_name)
    return {
        "is_recording": pid != None,
        "recording_filename": recording_filename,
        "recordings_list": get_recordings_list(),
        "preview_file":"",
    }

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

