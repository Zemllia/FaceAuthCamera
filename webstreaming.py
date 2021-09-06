import json
import os
import random
import string

import requests
from imutils.video import VideoStream
from flask import Response
from flask import Flask
from flask import render_template
import threading
import argparse
import datetime
import imutils
import time
import cv2

from motion_detection import SingleMotionDetector

outputFrame = None
lock = threading.Lock()
# initialize a flask object
app = Flask(__name__)
# initialize the video stream and allow the camera sensor to
# warmup
vs = VideoStream(usePiCamera=1).start()
# vs = VideoStream(src=0).start()
time.sleep(2.0)
with open('config.json') as json_file:
    CONFIG = json.load(json_file)
request_address = CONFIG.get("server_protocol") + \
                      "://" + CONFIG.get("server_ip") + \
                      ":" + CONFIG.get("server_port") + \
                      "/api/base/get-my-name/"
headers = {'Authorization': "Token " + CONFIG.get("camera_token")}
response = requests.get(request_address, headers=headers)
json_response = json.loads(response.text)
my_name = str(json_response.get("data").get("name"))


@app.route("/")
def index():
    # return the rendered template
    return render_template("index.html")


def detect_motion(frameCount):
    # grab global references to the video stream, output frame, and
    # lock variables
    global vs, outputFrame, lock
    # initialize the motion detector and the total number of frames
    # read thus far
    md = SingleMotionDetector(accumWeight=0.1)
    total = 0

    while True:
        # read the next frame from the video stream, resize it,
        # convert the frame to grayscale, and blur it
        frame = vs.read()
        frame = imutils.resize(frame, width=400)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (7, 7), 0)
        # grab the current timestamp and draw it on the frame
        timestamp = datetime.datetime.now()
        cv2.putText(frame, timestamp.strftime(
            "%A %d %B %Y %I:%M:%S%p    " + my_name), (10, frame.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

        # if the total number of frames has reached a sufficient
        # number to construct a reasonable background model, then
        # continue to process the frame
        if total > frameCount:
            # detect motion in the image
            motion = md.detect(gray)
            # check to see if motion was found in the frame
            if motion is not None:
                # unpack the tuple and draw the box surrounding the
                # "motion area" on the output frame
                (thresh, (minX, minY, maxX, maxY)) = motion
                cv2.rectangle(frame, (minX, minY), (maxX, maxY),
                              (0, 0, 255), 2)
                send_frame_to_server(frame)

        # update the background model and increment the total number
        # of frames read thus far
        md.update(gray)
        total += 1
        # acquire the lock, set the output frame, and release the
        # lock
        with lock:

            outputFrame = frame.copy()


def generate():
    # grab global references to the output frame and lock variables
    global outputFrame, lock
    # loop over frames from the output stream
    while True:
        # wait until the lock is acquired
        with lock:
            # check if the output frame is available, otherwise skip
            # the iteration of the loop
            if outputFrame is None:
                continue
            # encode the frame in JPEG format
            (flag, encodedImage) = cv2.imencode(".jpg", outputFrame)
            # ensure the frame was successfully encoded
            if not flag:
                continue
        # yield the output frame in the byte format
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' +
               bytearray(encodedImage) + b'\r\n')


@app.route("/video_feed")
def video_feed():
    # return the response generated along with the specific media
    # type (mime type)
    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")


def send_frame_to_server(frame):
    all_symbols = string.ascii_lowercase + string.ascii_uppercase
    file_name = "tmp/tmp_"
    for i in range(0, 15):
        file_name += random.choice(all_symbols)

    cv2.imwrite(file_name + ".jpg", frame)

    # Do stuff with image
    request_address = CONFIG.get("server_protocol") + \
                      "://" + CONFIG.get("server_ip") + \
                      ":" + CONFIG.get("server_port") + \
                      "/api/base/check-image/"
    headers = {'Authorization': "Token " + CONFIG.get("camera_token")}
    with open(file_name + '.jpg', 'rb') as f:
        files = {'image': (file_name + '.jpg', f)}
        request = requests.post(request_address, files=files, headers=headers)
        request.encoding = "UTF-8"
        print(request.text)
    os.remove(file_name + ".jpg")


# check to see if this is the main thread of execution
if __name__ == '__main__':
    # construct the argument parser and parse command line arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--ip", type=str, required=True,
                    help="ip address of the device")
    ap.add_argument("-o", "--port", type=int, required=True,
                    help="ephemeral port number of the server (1024 to 65535)")
    ap.add_argument("-f", "--frame-count", type=int, default=32,
                    help="# of frames used to construct the background model")
    args = vars(ap.parse_args())
    # start a thread that will perform motion detection
    t = threading.Thread(target=detect_motion, args=(
        args["frame_count"],))
    t.daemon = True
    t.start()
    # start the flask app
    app.run(host=args["ip"], port=args["port"], debug=True,
            threaded=True, use_reloader=False)
# release the video stream pointer
vs.stop()
