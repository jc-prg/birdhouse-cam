#!/usr/bin/python3

import os
import re
from modules.presets import *
from flask import Flask
from flask import Response, request
app = Flask(__name__)


directories = birdhouse_directories
main_directory = os.path.dirname(os.path.abspath(__file__))
media_path = os.path.join(main_directory, directories["data"], directories["videos"])

video_logging = logging.getLogger("video-srv")
video_logging.setLevel(birdhouse_loglevel_module["video-srv"])
video_logging.addHandler(birdhouse_loghandler)
video_logging.info("Starting Streaming Server (directory: '" + media_path + "') ...")


def serve_ios(full_path):

    print(full_path)
    file_size = os.stat(full_path).st_size
    start = 0
    length = 10240  # can be any default length you want

    range_header = request.headers.get('Range', None)
    if range_header:
        m = re.search('([0-9]+)-([0-9]*)', range_header)  # example: 0-1000 or 1250-
        g = m.groups()
        byte1, byte2 = 0, None
        if g[0]:
            byte1 = int(g[0])
        if g[1]:
            byte2 = int(g[1])
        if byte1 < file_size:
            start = byte1
        if byte2:
            length = byte2 + 1 - byte1
        else:
            length = file_size - start

    with open(full_path, 'rb') as f:
        f.seek(start)
        chunk = f.read(length)

    rv = Response(chunk, 206, mimetype='video/mp4', content_type='video/mp4', direct_passthrough=True)
    rv.headers.add('Content-Range', 'bytes {0}-{1}/{2}'.format(start, start + length - 1, file_size))
    return rv


@app.route('/<vid_name>')
def serve(vid_name):
    video_logging.info("... start video-streaming")
    vid_path = os.path.join(media_path, vid_name)
    return serve_ios(vid_path)


@app.after_request
def after_request(response):
    response.headers.add('Accept-Ranges', 'bytes')
    return response
    

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8008)
