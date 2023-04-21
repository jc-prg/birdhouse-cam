FROM debian:11.6-slim

RUN apt-get update
RUN apt-get -y upgrade
RUN apt-get -y install ffmpeg
RUN ffmpeg -version

RUN apt -y install locales
ENV PYTHONIOENCODING=utf-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

WORKDIR /usr/src/app

CMD [ "/bin/bash", "./server/stream_audio.ffmpeg" ]

