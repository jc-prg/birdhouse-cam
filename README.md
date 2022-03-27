# Birdhouse Camera

Raspberry Pi project to observe our birdhouse with multiple webcams (live stream, record images and videos, 
mark favorites ...).

## Main Features

* Use as web-app on an iPhones or in a browser
* Watch live stream via Raspberry Pi camera and USB web cam (e.g. RPi cam inside and USB web cam outside)
* Record photos e.g. every 20 seconds (configurable)
* Record and stream videos (mp4, works with iOS devices)
* Create video from all pictures of the current day
* Similarity detection, filter photos with movement in a defined area
* Mark photos as favorites and to be deleted
* Mark videos as favorites or to be deleted
* List favorite photos and videos in a list
* Hide / delete marked photos
* Recycle range of photos between two marked photos
* Archive photos with movement and favorite photos once a day
* Trim videos
* Get data from sensors connected to the Raspberry Pi (DHT11) and draw a chart: Temperature and Humidity
* Connect to audio stream from microphone (under construction)
* Deny recording and admin functionality for specific IP addresses (e.g. router or proxy, to deny for access from the internet)

## Birdhouse

* German instructions: [NABU - Nistkästen selber bauen](https://www.nabu.de/tiere-und-pflanzen/voegel/helfen/nistkaesten/index.html)
* English instructions: [Simple birdhouse](https://suncatcherstudio.com/birds/birdhouse-plans-simple/)

## Technology

* Raspberry Pi 3B+
* Camera module for RPi / HD with IR sensor
* USB camera
* Small USB Microphone
* DHT11 Sensor
* Python 3, PiCamera, CV2, imutils, JSON, Flask
* HTML, CSS, JavaScript, Pinch-Zoom, ffmpeg 
* jc://modules/, jc://app-framework/

## Installation

* Prepare a Raspberry Pi 3B or newer with the latest version of Rasbian
* Ensure Python 3 and pip3 is installed
* Install git: ```bash sudo apt-get install git ```
* Install birdhouse-cam:
```bash 
# Get source code
$ git clone http://github.com/jc-prg/birdhouse-cam.git
$ cd birdhouse-cam

# Install required Python modules and ffmpeg
$ ./config/install/install
$ ./config/install/install_ffmpeg

# Initial start, will create a config file
# -> check via http://<your-ip-address>:8000/ and stop via <Ctrl>+<C>
$ ./server/server.py

# Edit config file
$ nano data/config.json
```
* Add the following lines to crontab (start on boot):
```bash 
@reboot /usr/bin/python3 /<path_to_script>/server/server.py --logfile
@reboot /usr/bin/python3 /<path_to_script>/server/stream_video.py
```
* To start the audio streaming edit and link the file [stream.service](config/install/stream.service) to the folder /etc/systemd/systems and start as root (see instructions in the file):
``` bash
$ systemctl start stream.service
```

## Sources

Thanks for your inspiration, code snippets, images:

* [https://github.com/Freshman-tech/custom-html5-video](https://github.com/Freshman-tech/custom-html5-video)
* [https://github.com/manuelstofer/pinchzoom](https://github.com/manuelstofer/pinchzoom)
* [https://gifer.com/en/ZHug](https://gifer.com/en/ZHug)
* [https://github.com/szazo/DHT11_Python](https://github.com/szazo/DHT11_Python)

## Impressions

<img src="info/images/birdcam_05.PNG" width="30%"><img src="info/images/birdcam_09.PNG" width="30%"><img src="info/images/birdcam_10.PNG" width="30%">
<br/><br/>
<img src="info/images/birdcam_17.PNG" width="30%"><img src="info/images/birdcam_18.PNG" width="30%"><img src="info/images/birdcam_19.PNG" width="30%">
<br/><br/>
<img src="info/images/birdcam_07.PNG" width="30%"><img src="info/images/birdcam_08.PNG" width="30%"><img src="info/images/birdcam_06.PNG" width="30%">
<img src="info/images/birdcam_01.PNG" width="30%"><img src="info/images/birdcam_02.PNG" width="30%"><img src="info/images/birdcam_03.PNG" width="30%">
<img src="info/images/birdcam_11.PNG" width="30%"><img src="info/images/birdcam_12.PNG" width="30%"><img src="info/images/birdcam_13.PNG" width="30%">
<img src="info/images/birdcam_15.PNG" width="30%"><img src="info/images/birdcam_16.PNG" width="30%">
<br/><br/>
<img src="info/images/birdcam_14.PNG" width="90%">
