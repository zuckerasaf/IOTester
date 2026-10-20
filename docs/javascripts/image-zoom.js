(() => {
  const overlay = document.createElement("div");
  overlay.className = "image-zoom-overlay";
  overlay.setAttribute("role", "dialog");
  overlay.setAttribute("aria-modal", "true");
  overlay.setAttribute("aria-label", "Enlarged image");
  overlay.hidden = true;

  const enlargedImage = document.createElement("img");
  overlay.append(enlargedImage);
  document.body.append(overlay);

  const close = () => {
    overlay.hidden = true;
    enlargedImage.removeAttribute("src");
    enlargedImage.style.removeProperty("width");
  };

  document.addEventListener("click", (event) => {
    const image = event.target.closest(".md-typeset img");

    if (image && !overlay.contains(image)) {
      enlargedImage.src = image.currentSrc || image.src;
      enlargedImage.alt = image.alt;
      enlargedImage.style.width = `${image.getBoundingClientRect().width * 2}px`;
      overlay.hidden = false;
      return;
    }

    if (!overlay.hidden) {
      close();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !overlay.hidden) {
      close();
    }
  });
})();
