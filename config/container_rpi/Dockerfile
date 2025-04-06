FROM debian:12.4

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update
RUN apt-get -y upgrade
RUN apt-get -y install python3.11 python3-distutils python3-pip python3-apt apt-utils
RUN apt-get -y install rpi.gpio
RUN apt-get -y install iputils-ping
RUN apt-get -y install libgpiod2
RUN apt-get -y install ffmpeg
RUN apt-get -y install python3-opencv
RUN apt-get -y install python3-skimage
#RUN apt-get -y install --reinstall libraspberrypi0 libraspberrypi-dev libraspberrypi-bin
RUN apt-get -y install v4l-utils
RUN apt-get -y install usbutils

COPY ./requirements.txt ./requirements.txt
RUN rm /usr/lib/python3.11/EXTERNALLY-MANAGED
RUN pip3 install --upgrade pip --break-system-packages
RUN python3 -m pip install -r requirements.txt --break-system-packages

RUN apt -y install python3-pyaudio
RUN apt -y install locales --fix-missing
ENV PYTHONIOENCODING=utf-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

WORKDIR /usr/src/app
CMD [ "/usr/bin/python3", "./server/server.py" ]
