# Birdhouse Camera

Raspberry Pi project to observe our birdhouse with multiple webcams (live stream, record images and videos, mark favorits ...)
Hint: The descriptions in the web client are all in German at the moment.

## Features

* Use as web-app on iPhones
* Watch live stream via Raspberry Pi camera and USB web cam (e.g. RPi cam inside and USB web cam outside)
* Record photos e.g. every 20 seconds (configurable)
* Record and stream videos (mp4, works with iOS devices)
* Similarity detection, filter photos with movement in a defined area
* Mark photos as favorits and to be deleted
* Mark videos as favorits or to be deleted
* List favorit photos and videos in a list
* Hide / delete marked photos
* Recylce range of photos between two marked photos
* Archive photos with movement and favorit photos once a day
* Trim videos
* Deny recording and admin functionality for specific IP adresses (e.g. router or proxy, to deny for access from the internet)

## Birdhouse

* German instructions: [NABU - Nistkästen selber bauen](https://www.nabu.de/tiere-und-pflanzen/voegel/helfen/nistkaesten/index.html)
* English instructions: [Simple birdhouse](https://suncatcherstudio.com/birds/birdhouse-plans-simple/)

## Technology

* Raspberry Pi 3B+
* Camera module for RPi / HD with IR sensor
* USB camera
* Python 3, PiCamera, CV2, imutils, JSON, Flask
* HTML, CSS, JavaScript, Pinch-Zoom
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
$ ./info/install
$ ./info/install_ffmpeg

# Initial start -> check via http://<your-ip-address>:8000/ and stop via <Ctrl>+<C>
$ ./stream.py

# Edit config file
$ nano config.json
```
* Add the following lines to crontab (start on boot):
```bash 
@reboot /usr/bin/python3 /<path_to_script>/stream.py --logfile
@reboot /usr/bin/python3 /<path_to_script>/videostream.py
```

## Sources

Thanks for your inspiration, code snippets, images:

* [https://github.com/Freshman-tech/custom-html5-video](https://github.com/Freshman-tech/custom-html5-video)
* [https://github.com/manuelstofer/pinchzoom](https://github.com/manuelstofer/pinchzoom)
* [https://gifer.com/en/ZHug](https://gifer.com/en/ZHug)

## Impressions
![Screenshot 01](info/screenshot_06.png)
![Screenshot 02](info/screenshot_07.png)
![Screenshot 03](info/screenshot_08.png)
![Screenshot 04](info/screenshot_09.png)
![Screenshot 05](info/screenshot_10.png)

