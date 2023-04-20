# Birdhouse Camera

Raspberry Pi project to observe our birdhouse with multiple webcams: live stream, record images, detect activity, record videos, 
mark favorites, analyze weather data, ...

1. [Birdhouse Construction](#birdhouse-construction)
3. [Technology](#technology)
2. [Main Software Features](#main-software-features)
4. [Software Installation](#software-installation)
   * [Clone sources to your project directory](#clone-sources-to-your-project-directory)
   * [Install as Docker version](#install-as-docker-version)
   * [Install directly](#install-directly)
   * [First run and device configuration](#first-run-and-device-configuration)
   * [Finalize database setup](#finalize-database-setup)
   * [Access images via WebDAV](Access-images-via-WebDAV)
   * [Add audio streaming](#add-audio-streaming)
   * [Optimize system configuration (Ubuntu 22.04)](#optimize-system-configuration--ubuntu-)
   * [Optimize system configuration (Raspbian / Raspberry OS)](#optimize-system-configuration--raspberry-os-)
   * [Sample proxy server configuration](#Sample-proxy-server-configuration)
5. [Helping stuff](#helping-stuff)
6. [Sources](#sources)
7. [Impressions](#impressions)


## Birdhouse Construction

* German instructions: [NABU - Nistkästen selber bauen](https://www.nabu.de/tiere-und-pflanzen/voegel/helfen/nistkaesten/index.html)
* English instructions: [Simple birdhouse](https://suncatcherstudio.com/birds/birdhouse-plans-simple/)

## Technology

* Hardware
  * Raspberry Pi 3B+ (or newer)
  * Camera module for RPi / HD with IR sensor
  * USB camera
  * Small USB Microphone
  * DHT11 / DHT22 Sensor
* Software
  * Python 3, CV2, imutils, JSON, Flask
  * python_weather, Weather by [Open-Meteo.com](https://open-meteo.com/), GeoPy
  * HTML, CSS, JavaScript, Pinch-Zoom, ffmpeg 
  * jc://modules/, jc://app-framework/

## Main Software Features

* Use as web-app on an iPhones or in a browser
* Watch **live stream** with 1 or 2 cameras 
  * via Raspberry Pi camera
  * USB web cam (e.g. RPi cam inside and USB web cam outside)
* **Record photos**
  * e.g. every 20 seconds from sunrise to 20:00 local time (configurable in the device settings)
  * Similarity detection, filter photos with movement in a defined area (visualize differences)
  * camera and image settings configurable (brightness, contrast, ...)
* **Manage photos**
  * Mark photos and videos as favorites and to be deleted
  * Mark a range of photos between two marked photos as to be deleted
  * List favorite photos and videos in a list
  * Delete marked photos
  * Archive photos with movement and favorite photos once a day
* **Record and stream videos**
  * create mp4 video, works with iOS devices
  * Create video from all pictures of the current day
  * Trim videos
* Get, archive, and visualize **weather data**:
  * from sensors connected to the Raspberry Pi (DHT11/DHT22)
  * via internet for a defined location (python_weather OR [Open Meteo](https://open-meteo.com/))
  * GPS lookup for cities or addresses via GeoPy to set weather location
* Connect to **audio stream** from microphone
  * under construction, currently browser only (no iPhone)
* **Admin functionality** via app
  * Deny recording and admin functionality for specific IP addresses (e.g. router or proxy, to deny for access from the internet)
  * edit server settings (partly, other settings define in file .env)
  * edit device settings (devices must be added via config file)
  * edit camera and image settings

## Software Installation

* Build a birdhouse incl. a Raspberry Pi or USB Camera inside the birdhouse (additional cameras and sensors are optional)
* Prepare a Raspberry Pi 3B or newer
  * Install a fresh image on an SDCard (https://www.raspberrypi.com/software/)
  * Recommend OS: Ubuntu 22.04 (32bit) Server OS
  * Install git: ```sudo apt-get install git```
  * Install raspi-config: ```sudo apt-get install raspi-config```
  * Install v4l2-ctl: ```sudo apt-get install v4l-utils```
  * Create and move to your project directory (e.g. /projects/prod/)
* Install software as docker version or directly
* Connect camera (and optional devices) with the Raspberry, start and enjoy

_NOTE: For an upgrade of an existing older version from v0.x to v1.x it is required
to rename (or remove) the file 'data/config.json' and restart after the update. 
Then change the new default configuration to your needs ..._

### Clone sources to your project directory

```bash 
$ git clone http://github.com/jc-prg/birdhouse-cam.git
$ cd birdhouse-cam
$ git submodule update --init --recursive
```

### Install as Docker version

* Install docker and docker-compose
```bash
$ sudo ./config/install/install_docker
```

* Create configuration and edit (if required)
```bash
$ sudo cp sample.env .env
$ sudo nano .env
```

* Build docker container and run the first time
```bash
$ docker-compose up --build
```
* Add the following lines to crontab (start on boot):
```bash 
@reboot /usr/sbin/docker-compose -f /<path_to_script>/docker-compose.yml up -d
```

### Install directly

* Install birdhouse-cam:
```bash 
# Install required Python modules and ffmpeg (this may take a while)
$ sudo ./config/install/install
$ sudo ./config/install/install_ffmpeg

# Initial start, will create a config file
$ ./server/server.py
```
* Add the following lines to crontab (start on boot):
```bash 
@reboot /usr/bin/python3 /<path_to_script>/server/server.py --logfile
@reboot /usr/bin/python3 /<path_to_script>/server/stream_video.py
```
### First run and device configuration

* Open your client (usually via http://your-hostname:8000/). 
When you run it the first time you'll be asked to check, change and save the settings.
After that open the device settings, check and save them also.
* NOTE: if you want to add devices at the moment you have to edit the config file directly. 
It's stored as ./data/config.json.

### Finalize database setup

The default configuration of the database works without change but produces several error messages.
To remove those open the admin tool via http://your-hostname:5100/_utils/ and login (default user:birdhouse, pwd:birdhouse).
Go to the settings and create a single node.

### Access images via WebDAV

To access image and video files via WebDAV define credentials and port in the .env-file and start docker container.

```
$ sudo docker-compose -f docker-compose-webdav.yml up -d
```

### Add audio streaming

* _under construction, not running on iOS devices yet_
* To start the audio streaming edit and link the file [stream.service](config/install/stream.service) to the folder /etc/systemd/systems and start as root (see instructions in the file):

``` bash
$ systemctl start stream.service
```

### Optimize system configuration (Ubuntu)

* Update swap memory (see also [https://bitlaunch.io/](https://bitlaunch.io/blog/how-to-create-and-adjust-swap-space-in-ubuntu-20-04/))

```commandline
free -h
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
free -h
```

### Optimize system configuration (Raspberry OS)

* Update swap memory (usually 100MiB is set as default)
```
$ sudo nano /etc/dphys-swapfile

# change the following values to:
CONF_SWAPSIZE=
CONF_SWAPFACTOR=2

$ sudo systemctl restart dphys-swapfile
```

### Sample proxy server configuration

If you want to give access via internet you properly want to use a proxy such as NGINX. 
Therefor it's required to enable access to the following ports (if not changed default port settings):

* **App**: 80, 443
* **API**: 8007
* **Videostream**: 8008
* **Audiostream**: 8009

See a sample configuration (e.g. to forward http://birdhouse.your.domain:443 to http://your-server-ip:8000) here: [sample.nginx.conf](sample.nginx.conf). Ensure, that all used ports are publicly shared via your router.

## Helping stuff

* Check attached cameras

```bash
# list video devices (install: apt-get install v4l2-ctl) 
$ v4l2-ctl --list-devices

# check available cameras
$ vcgencmd get_camera

# check available audio devices
$ arecord -l

# set audio level
$ amixer -c 2 -q set 'Mic',0 100%

# continuously watch logfile (2s, 40 lines)
$ watch 'head -n 2 log/server.log | tail -n 40 log/server.log'
```


## Sources

Thanks for your inspiration, code snippets, images:

* [https://github.com/Freshman-tech/custom-html5-video](https://github.com/Freshman-tech/custom-html5-video)
* [https://github.com/manuelstofer/pinchzoom](https://github.com/manuelstofer/pinchzoom)
* [https://gifer.com/en/ZHug](https://gifer.com/en/ZHug)
* [https://github.com/szazo/DHT11_Python](https://github.com/szazo/DHT11_Python)
* [https://github.com/bullet64/DHT22_Python](https://github.com/bullet64/DHT22_Python)
* [https://www.tunbury.org/audio-stream/](https://www.tunbury.org/audio-stream/)

## Impressions

<img src="info/images/birdcam_05.PNG" width="30%"><img src="info/images/birdcam_21.PNG" width="30%"><img src="info/images/birdcam_10.PNG" width="30%">
<br/><br/>
<img src="info/images/birdcam_17.PNG" width="30%"><img src="info/images/birdcam_18.PNG" width="30%"><img src="info/images/birdcam_19.PNG" width="30%">
<br/><br/>
<img src="info/images/birdcam_08.PNG" width="30%"><img src="info/images/birdcam_06.PNG" width="30%"><img src="info/images/birdcam_11.PNG" width="30%">


<img src="info/images/birdcam_12.PNG" width="30%"><img src="info/images/birdcam_13.PNG" width="30%"><img src="info/images/birdcam_22.PNG" width="30%">

<img src="info/images/birdcam_23.PNG" width="30%"><img src="info/images/birdcam_15.PNG" width="30%"><img src="info/images/birdcam_16.PNG" width="30%">

<img src="info/images/birdcam_01.PNG" width="30%"><img src="info/images/birdcam_02.PNG" width="30%"><img src="info/images/birdcam_24.PNG" width="30%">
<img src="info/images/birdcam_25.PNG" width="30%">

<br/><br/>
<img src="info/images/birdcam_14.PNG" width="90%">
