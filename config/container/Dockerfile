FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get -y update && apt-get install -y python3 python3-distutils python3-pip python3-apt apt-utils
#RUN apt-get -y install rpi.gpio
RUN apt -y install iputils-ping

RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install -U setuptools
RUN python3 -m pip install -U wheel
#RUN python3 -m pip install -U scikit-image

COPY ./requirements.txt ./requirements.txt
RUN python3 -m pip install -r requirements.txt

RUN apt-get install 'ffmpeg'\
    'libsm6'\ 
    'libxext6'  -y

RUN apt -y install locales locales-all
ENV PYTHONIOENCODING=utf-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

WORKDIR /usr/src/app
CMD [ "/usr/bin/python3", "./server.py" ]
