  // Array of image URLs
  const imageUrls = [
    "images/image1.jpeg",
    "images/image2.jpeg",
    "images/image3.jpeg",
    "images/image4.jpeg",
    "images/image5.jpeg",
    "images/image6.jpeg",
    "images/image7.jpeg",
    "images/image8.jpeg",
    "images/image9.jpeg",
    "images/image10.jpeg"
  ];

  const overlay = document.getElementById("overlay");
  let currentIndex = 0;
  let touchStartX = 0;
  let initialScale = 1;

  // Function to show the overlay with the specified image
  function showOverlay(index) {
    overlay.innerHTML = `
      <div class="background"></div>
      <div class="left-arrow" onclick="prevImage()"></div>
      <div class="right-arrow" onclick="nextImage()"></div>
      <img src="${imageUrls[index]}" id="overlayImage">
    `;
    overlay.style.display = "block";
    addTouchListenersScale("overlayImage", 1);
    addTouchListenersSwipe("overlayImage");
  }

  // Function to handle touch events for scaling
  function addTouchListenersScale(div_id, initScale=1) {
    const overlayImage = document.getElementById(div_id);
    let initialPinchDistance = 0;
    initialScale = initScale;
    currentIndex = 0;
    touchStartX = 0;

    overlayImage.addEventListener("touchstart", function(event) {
      if (event.touches.length === 2) {
        initialPinchDistance = Math.hypot(
          event.touches[1].pageX - event.touches[0].pageX,
          event.touches[1].pageY - event.touches[0].pageY
        );

        const computedTransform = getComputedStyle(overlayImage).transform;

        if (computedTransform && computedTransform !== 'none') {
          // Extract the scale from the transformation matrix
          const matrixValues = computedTransform.split('(')[1].split(')')[0].split(',');
          initialScale = parseFloat(matrixValues[0]);
        }

      } else if (event.touches.length === 1) {
        touchStartX = event.touches[0].clientX;
      }
    });

    overlayImage.addEventListener("touchmove", function(event) {
      if (event.touches.length === 2) {
        const currentPinchDistance = Math.hypot(
          event.touches[1].pageX - event.touches[0].pageX,
          event.touches[1].pageY - event.touches[0].pageY
        );
        const scale = initialScale * (currentPinchDistance / initialPinchDistance);
        overlayImage.style.transform = `scale(${scale})`;
      }
    });
  }

  function addTouchListenersSwipe(div_id) {
      const overlayImage = document.getElementById(div_id);

      // Function to handle swiping left/right
      overlay.addEventListener("touchstart", function(event) {
        if (event.touches.length === 1) {
          touchStartX = event.touches[0].clientX;
        }
      });

      overlay.addEventListener("touchend", function(event) {
        if (event.changedTouches.length === 1) {
          const touchEndX = event.changedTouches[0].clientX;
          const deltaX = touchEndX - touchStartX;
          if (Math.abs(deltaX) > 150) {
            if (deltaX > 0) {
              nextImage();
            } else {
              prevImage();
            }
          }
        }
      });
  }

  // Function to show the next image
  function nextImage() {
    currentIndex = (currentIndex + 1) % imageUrls.length;
    showOverlay(currentIndex);
  }

  // Function to show the previous image
  function prevImage() {
    currentIndex = (currentIndex - 1 + imageUrls.length) % imageUrls.length;
    showOverlay(currentIndex);
  }


  // Show the first image initially
  //showOverlay(currentIndex);


app_scripts_loaded += 1;
