FROM debian:12.4

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update
RUN apt-get -y upgrade
RUN apt-get -y install python3 python3-distutils python3-pip python3-apt apt-utils
RUN apt-get -y install rpi.gpio
RUN apt-get -y install iputils-ping
RUN apt-get -y install libgpiod2
RUN apt-get -y install ffmpeg
RUN apt-get -y install python3-opencv
RUN apt-get -y install python3-skimage
#RUN apt-get -y install --reinstall libraspberrypi0 libraspberrypi-dev libraspberrypi-bin
RUN apt-get -y install v4l-utils

# Try out picamera and libcamera; together with "FROM navikey/raspbian-bullseye"
# -------------------------------------
#RUN apt-get -y install libcap-dev python3-libcamera python3-kms++ssssss
#RUN apt-get -y install meson cmake
#RUN git clone https://git.libcamera.org/libcamera/libcamera.git \
#    && cd libcamera  \
#    && meson setup build \
#    && ninja -C build install
#RUN apt-get remove meson cmake

COPY ./requirements.txt ./requirements.txt
RUN pip3 install --upgrade pip
RUN python3 -m pip install -r requirements.txt

RUN apt -y install python3-pyaudio
RUN apt -y install locales
ENV PYTHONIOENCODING=utf-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8
ENV LD_PRELOAD=/usr/local/lib/python3.8/dist-packages/torch.libs/libgomp-6e1a1d1b.so.1.0.0

WORKDIR /usr/src/app
CMD [ "/usr/bin/python3", "./server/server.py" ]
