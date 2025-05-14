FROM ubuntu:24.04
#FROM debian:12.9

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get -y upgrade
RUN apt-get -y install locales --fix-missing
RUN apt-get -y install python3 python3-pip python3-apt apt-utils
RUN apt-get -y install iputils-ping
RUN apt-get -y install libgpiod2
RUN apt-get -y install ffmpeg
RUN apt-get -y install v4l-utils
RUN apt-get -y install usbutils
#RUN apt-get -y install rpi.gpio
#RUN apt-get -y install --reinstall libraspberrypi0 libraspberrypi-dev libraspberrypi-bin

RUN apt-get -y install python3-numpy python3-flask python3-psutil python3-setuptools python3-requests
RUN apt-get -y install python3-opencv python3-pyaudio
RUN rm /usr/lib/python3.12/EXTERNALLY-MANAGED

COPY ./requirements.txt ./requirements.txt
RUN export PYTHONPATH=/usr/bin/python3 \
    && pip3 install -r requirements.txt --ignore-installed

ENV PYTHONIOENCODING=utf-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

WORKDIR /usr/src/app
CMD [ "/usr/bin/python3", "./server/server.py" ]
