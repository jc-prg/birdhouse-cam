
// Select elements here
var video = undefined;
var videoControls = undefined;
var playButton = undefined;
var playbackIcons = undefined;
var timeElapsed = undefined;
var vDuration = undefined;
var progressBar = undefined;
var seek = undefined;
var seekTooltip = undefined;
var volumeButton = undefined;
var volumeIcons = undefined;
var volumeMute = undefined;
var volumeLow = undefined;
var volumeHigh = undefined;
var volume = undefined;
var playbackAnimation = undefined;
var fullscreenButton = undefined;
var videoContainer = undefined;
var fullscreenIcons = undefined;
var pipButton = undefined;
var nullvideoWorks = undefined;

// Set initial vars for video player
function videoSetVars() {
    video = document.getElementById('video');
    videoControls = document.getElementById('video-controls');
    playButton = document.getElementById('play');
    playbackIcons = document.querySelectorAll('.playback-icons use');
    timeElapsed = document.getElementById('time-elapsed');
    vDuration = document.getElementById('duration');
    progressBar = document.getElementById('progress-bar');
    seek = document.getElementById('seek');
    seekTooltip = document.getElementById('seek-tooltip');
    volumeButton = document.getElementById('volume-button');
    volumeIcons = document.querySelectorAll('.volume-button use');
    volumeMute = document.querySelector('use[href="#volume-mute"]');
    volumeLow = document.querySelector('use[href="#volume-low"]');
    volumeHigh = document.querySelector('use[href="#volume-high"]');
    volume = document.getElementById('volume');
    playbackAnimation = document.getElementById('playback-animation');
    fullscreenButton = document.getElementById('fullscreen-button');
    videoContainer = document.getElementById('video-container');
    fullscreenIcons = fullscreenButton.querySelectorAll('use');
    pipButton = document.getElementById('pip-button');

    // Get the seek input and tooltip elements
    /*
    nullseek = document.getElementById('seek');
    nullseekTooltip = document.getElementById('seek-tooltip');
    */
    videoWorks = !!document.createElement('video').canPlayType;
    if (videoWorks) {
      video.controls = false;
      videoControls.classList.remove('hidden');
    }

    initButtons();
    videoAddEventListeners();
}

// Add functions here

// the TC IN / TC OUT fields per default are colored in lightred
// if this JS file is loaded, the following changes it to white as indicator that everything is fine
function initButtons() {
  tcOut = document.getElementById("tc-out");
  tcOut.style.background = "white";
  tcIn  = document.getElementById("tc-in");
  tcIn.style.background = "white";
}

// togglePlay toggles the playback state of the video.
// If the video playback is paused or ended, the video is played
// otherwise, the video is paused
function togglePlay() {
  if (video.paused || video.ended) {
    video.play();
  } else {
    video.pause();
  }
}

// updatePlayButton updates the playback icon and tooltip
// depending on the playback state
function updatePlayButton() {
  playbackIcons.forEach((icon) => icon.classList.toggle('hidden'));

  if (video.paused) {
    playButton.setAttribute('data-title', 'Play (k)');
  } else {
    playButton.setAttribute('data-title', 'Pause (k)');
  }
}

// formatTime takes a time length in seconds and returns the time in
// minutes and seconds
function formatTime(timeInSeconds) {

  if (!timeInSeconds) { timeInSeconds = 0; }

  const result       = new Date(timeInSeconds * 1000).toISOString().substr(11, 12);
  const totalseconds = (Math.round(timeInSeconds * 100)/100)
  return {
    minutes: result.substr(3, 2),
    seconds: result.substr(6, 2),
    mseconds: result.substr(10, 3),
    tseconds: totalseconds,
  };
}

// initializeVideo sets the video duration, and maximum value of the
// progressBar
function initializeVideo() {
  const videoDuration = Math.round(video.duration);
//  seek.setAttribute('max', videoDuration);
//  progressBar.setAttribute('max', videoDuration);
  const time = formatTime(videoDuration);
  vDuration.innerText = `${time.minutes}:${time.seconds}`;
  vDuration.setAttribute('datetime', `${time.minutes}m ${time.seconds}s`);
}

// updateTimeElapsed indicates how far through the video
// the current playback is by updating the timeElapsed element
function updateTimeElapsed() {
  const time = formatTime(Math.round(video.currentTime));
  timeElapsed.innerText = `${time.minutes}:${time.seconds}`;
  timeElapsed.setAttribute('datetime', `${time.minutes}m ${time.seconds}s`);
}

// updateProgress indicates how far through the video
// the current playback is by updating the progress bar
function updateProgress() {
  seek.value = Math.floor(video.currentTime*100/video.duration);
  seek.value = Math.round(video.currentTime*100/video.duration*100)/100;
  progressBar.value = Math.round(video.currentTime/video.duration*100)/100;
}

// updateSeekTooltip uses the position of the mouse on the progress bar to
// roughly work out what point in the video the user will skip to if
// the progress bar is clicked at that point
function updateSeekTooltip(event) {
  const skipTo = Math.round(
    (event.offsetX / event.target.clientWidth) * video.duration * 100
  )/100;

  const t = formatTime(skipTo);
  seekTooltip.textContent = `${t.minutes}:${t.seconds}`;
  seekTooltip.style.left = `${(skipTo / video.duration) * 100}%`;
}

// Skip to a new time when the user interacts with the timeline
function skipAhead(event) {
  // Get the new time based on the input position

  var seekTo = event.target.value;
  var skipTo = event.target.value * video.duration / 100;

  // Update the video's current time
  video.currentTime = skipTo;

  // Update the progress bar value
  seek.value = seekTo;
  const time = formatTime(skipTo);
  seekTooltip.textContent = `${time.minutes}:${time.seconds}`;
}

// updateVolume updates the video's volume
// and disables the muted state if active
function updateVolume() {
  if (video.muted) {
    video.muted = false;
  }

  video.volume = volume.value;
}

// updateVolumeIcon updates the volume icon so that it correctly reflects
// the volume of the video
function updateVolumeIcon() {
  volumeIcons.forEach((icon) => {
    icon.classList.add('hidden');
  });

  volumeButton.setAttribute('data-title', 'Mute (m)');

  if (video.muted || video.volume === 0) {
    volumeMute.classList.remove('hidden');
    volumeButton.setAttribute('data-title', 'Unmute (m)');
  } else if (video.volume > 0 && video.volume <= 0.5) {
    volumeLow.classList.remove('hidden');
  } else {
    volumeHigh.classList.remove('hidden');
  }
}

// toggleMute mutes or unmutes the video when executed
// When the video is unmuted, the volume is returned to the value
// it was set to before the video was muted
function toggleMute() {
  video.muted = !video.muted;

  if (video.muted) {
    volume.setAttribute('data-volume', volume.value);
    volume.value = 0;
  } else {
    volume.value = volume.dataset.volume;
  }
}

// animatePlayback displays an animation when
// the video is played or paused
function animatePlayback() {
  playbackAnimation.animate(
    [
      {
        opacity: 1,
        transform: 'scale(1)',
      },
      {
        opacity: 0,
        transform: 'scale(1.3)',
      },
    ],
    {
      duration: 500,
    }
  );
}

// toggleFullScreen toggles the full screen state of the video
// If the browser is currently in fullscreen mode,
// then it should exit and vice versa.
function toggleFullScreen() {
  if (document.fullscreenElement) {
    document.exitFullscreen();
  } else if (document.webkitFullscreenElement) {
    // Need this to support Safari
    document.webkitExitFullscreen();
  } else if (videoContainer.webkitRequestFullscreen) {
    // Need this to support Safari
    videoContainer.webkitRequestFullscreen();
  } else {
    videoContainer.requestFullscreen();
  }
}

// updateFullscreenButton changes the icon of the full screen button
// and tooltip to reflect the current full screen state of the video
function updateFullscreenButton() {
  fullscreenIcons.forEach((icon) => icon.classList.toggle('hidden'));

  if (document.fullscreenElement) {
    fullscreenButton.setAttribute('data-title', 'Exit full screen (f)');
  } else {
    fullscreenButton.setAttribute('data-title', 'Full screen (f)');
  }
}

// togglePip toggles Picture-in-Picture mode on the video
async function togglePip() {
  try {
    if (video !== document.pictureInPictureElement) {
      pipButton.disabled = true;
      await video.requestPictureInPicture();
    } else {
      await document.exitPictureInPicture();
    }
  } catch (error) {
    console.error(error);
  } finally {
    pipButton.disabled = false;
  }
}

// hideControls hides the video controls when not in use
// if the video is paused, the controls must remain visible
function hideControls() {
  if (video.paused) {
    return;
  }

  videoControls.classList.add('hide');
}

// showControls displays the video controls
function showControls() {

  videoControls.classList.remove('hide');
}

// set timecode IN and out
function setTCin() {
  const time = formatTime(video.currentTime);
  tcIn = document.getElementById("tc-in");
  //tcIn.value = `${time.minutes}:${time.seconds}.${time.mseconds}`;
  tcIn.value = `${time.tseconds}`;
  console.log("TC-IN: " + tcIn.value);
}
function setTCout() {
  const time = formatTime(video.currentTime);
  tcOut = document.getElementById("tc-out");
  //tcOut.value = `${time.minutes}:${time.seconds}.${time.mseconds}`;
  tcOut.value = `${time.tseconds}`;
  console.log("TC-OUT: " + tcOut.value);
}

// keyboardShortcuts executes the relevant functions for
// each supported shortcut key
function keyboardShortcuts(event) {
  const { key } = event;
  switch (key) {
    case 'k':
      togglePlay();
      animatePlayback();
      if (video.paused) {
        showControls();
      } else {
        setTimeout(() => {
          hideControls();
        }, 2000);
      }
      break;
    case 'm':
      toggleMute();
      break;
    case 'f':
      toggleFullScreen();
      break;
    case 'i':
      setTCin();
      break;
    case 'o':
      setTCout();
      break;
    case 'Escape':
      toggleVideoEdit(false);
      break;
    case ' ':
      togglePlay();
      animatePlayback();
      if (video.paused) {
        showControls();
      } else {
        setTimeout(() => {
          hideControls();
        }, 2000);
      }
      break;
  }
}

// Add eventlisteners here
function videoAddEventListeners() {
    playButton.addEventListener('click', togglePlay);
    video.addEventListener('play', updatePlayButton);
    video.addEventListener('pause', updatePlayButton);
    video.addEventListener('loadedmetadata', initializeVideo);
    video.addEventListener('timeupdate', updateTimeElapsed);
    video.addEventListener('timeupdate', updateProgress);
    video.addEventListener('volumechange', updateVolumeIcon);
    video.addEventListener('click', togglePlay);
    video.addEventListener('click', animatePlayback);
    video.addEventListener('mouseenter', showControls);
    video.addEventListener('mouseleave', hideControls);
    videoControls.addEventListener('mouseenter', showControls);
    videoControls.addEventListener('mouseleave', hideControls);
    seek.addEventListener('mousemove', updateSeekTooltip);
    seek.addEventListener('input', skipAhead);
    volume.addEventListener('input', updateVolume);
    volumeButton.addEventListener('click', toggleMute);
    fullscreenButton.addEventListener('click', toggleFullScreen);
    videoContainer.addEventListener('fullscreenchange', updateFullscreenButton);
    document.addEventListener('DOMContentLoaded', () => {
      if (!('pictureInPictureEnabled' in document)) {
        pipButton.classList.add('hidden');
      }
    });
    document.addEventListener('keyup', keyboardShortcuts);
    }

// remove all eventListeners
function videoRemoveEventListeners() {
    playButton.removeEventListener('click', togglePlay);
    video.removeEventListener('play', updatePlayButton);
    video.removeEventListener('pause', updatePlayButton);
    video.removeEventListener('loadedmetadata', initializeVideo);
    video.removeEventListener('timeupdate', updateTimeElapsed);
    video.removeEventListener('timeupdate', updateProgress);
    video.removeEventListener('volumechange', updateVolumeIcon);
    video.removeEventListener('click', togglePlay);
    video.removeEventListener('click', animatePlayback);
    video.removeEventListener('mouseenter', showControls);
    video.removeEventListener('mouseleave', hideControls);
    videoControls.removeEventListener('mouseenter', showControls);
    videoControls.removeEventListener('mouseleave', hideControls);
    seek.removeEventListener('mousemove', updateSeekTooltip);
    seek.removeEventListener('input', skipAhead);
    volume.removeEventListener('input', updateVolume);
    volumeButton.removeEventListener('click', toggleMute);
    fullscreenButton.removeEventListener('click', toggleFullScreen);
    videoContainer.removeEventListener('fullscreenchange', updateFullscreenButton);
    document.removeEventListener('DOMContentLoaded', () => {
      if (!('pictureInPictureEnabled' in document)) {
        pipButton.classList.add('hidden');
      }
    });
    document.removeEventListener('keyup', keyboardShortcuts);
    }

app_scripts_loaded += 1;
videoplayer_script_loaded = true;

