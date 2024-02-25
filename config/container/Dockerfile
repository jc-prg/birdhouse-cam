FROM ubuntu:22.04
#FROM debian:12.4

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get -y upgrade
RUN apt-get -y install locales --fix-missing
RUN apt-get -y install python3 python3-distutils python3-pip python3-apt apt-utils
RUN apt-get -y install python3-opencv python3-skimage python3-pyaudio
RUN apt-get -y install iputils-ping
RUN apt-get -y install libgpiod2
RUN apt-get -y install ffmpeg
RUN apt-get -y install v4l-utils
#RUN apt-get -y install rpi.gpio
#RUN apt-get -y install --reinstall libraspberrypi0 libraspberrypi-dev libraspberrypi-bin

#RUN apt-get install 'ffmpeg'\
#    'libsm6'\
#    'libxext6'  -y
#RUN rm /usr/lib/python3.11/EXTERNALLY-MANAGED
COPY ./requirements.txt ./requirements.txt
RUN export PYTHONPATH=/usr/bin/python3 \
    && pip3 install --upgrade pip \
    && pip3 install -r requirements.txt
RUN pip3 install ultralytics

ENV PYTHONIOENCODING=utf-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

WORKDIR /usr/src/app
CMD [ "/usr/bin/python3", "./server/server.py" ]
