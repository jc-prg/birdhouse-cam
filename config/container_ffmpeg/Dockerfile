FROM ubuntu:20.04

RUN apt-get update && apt-get -y upgrade

RUN DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC
RUN apt-get install -y tzdata

# https://trac.ffmpeg.org/wiki/CompilationGuide/Ubuntu
# FFmpeg build dependencies.
RUN apt-get update -qq && apt-get -y install --no-install-recommends \
  autoconf \
  automake \
  build-essential \
  cmake \
  git-core \
  libass-dev \
  libfreetype6-dev \
  libgnutls28-dev \
  libmp3lame-dev \
  libsdl2-dev \
  libtool \
  libva-dev \
  libvdpau-dev \
  libvorbis-dev \
  libxcb1-dev \
  libxcb-shm0-dev \
  libxcb-xfixes0-dev \
  meson \
  ninja-build \
  pkg-config \
  texinfo \
  wget \
  yasm \
  zlib1g-dev

RUN apt-get -y install libx264-dev
RUN apt-get -y install libfdk-aac-dev
RUN apt-get -y install libunistring-dev

RUN mkdir -p ~/ffmpeg_sources ~/bin
RUN cd ~/ffmpeg_sources &&  \
    wget -O  ffmpeg-snapshot.tar.bz2 https://ffmpeg.org/releases/ffmpeg-snapshot.tar.bz2 --no-check-certificate && \
    tar xjvf ffmpeg-snapshot.tar.bz2 && \
    PATH="$HOME/bin:$PATH" PKG_CONFIG_PATH="$HOME/ffmpeg_build/lib/pkgconfig" && cd ffmpeg && ./configure \
  --prefix="$HOME/ffmpeg_build" \
  --pkg-config-flags="--static" \
  --extra-cflags="-I$HOME/ffmpeg_build/include" \
  --extra-ldflags="-L$HOME/ffmpeg_build/lib" \
  --extra-libs="-lpthread -lm" \
  --ld="g++" \
  --bindir="$HOME/bin" \
  --enable-gpl \
  --enable-gnutls \
  --enable-libfdk-aac \
  --enable-libfreetype \
  --enable-libmp3lame \
  --enable-libx264 \
  --enable-nonfree && \
PATH="$HOME/bin:$PATH" make && \
make install && \
hash -r

RUN apt -y install locales
ENV PYTHONIOENCODING=utf-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

WORKDIR /usr/src/app

CMD [ "/bin/bash", "./server/stream_audio.ffmpeg" ]

