document.addEventListener('DOMContentLoaded', () => {
  // Event delegation for dynamically added buttons
  document.body.addEventListener('click', handleFavoriteToggle);
});

async function handleFavoriteToggle(e) {
  const btn = e.target.closest('.favorite-toggle');
  if (!btn) return;

  e.preventDefault();
  
  // Visual feedback: Disable button during processing
  btn.disabled = true;
  const icon = btn.querySelector('i');
  const tooltip = btn.querySelector('.tooltip');
  
  // Add loading state
  icon.classList.add('opacity-75');
  
  try {
    const response = await fetch("/property/favorite/", {
      method: "POST",
      headers: {
        "X-CSRFToken": getCSRFToken(),
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: `property_id=${btn.dataset.id}`,
    });

    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data = await response.json();

    // Update UI based on response
    updateButtonState(btn, icon, tooltip, data.status);
    
    // Visual confirmation
    if (data.status === 'added') {
      icon.classList.add('animate-pop');
      setTimeout(() => icon.classList.remove('animate-pop'), 300);
    }
  } catch (err) {
    console.error('Favorite toggle failed:', err);
    showErrorFeedback(btn);
  } finally {
    btn.disabled = false;
    icon.classList.remove('opacity-75');
  }
}

// Helper functions
function updateButtonState(btn, icon, tooltip, action) {
  const isAdded = action === 'added';
  
  // Toggle classes more efficiently
  icon.classList.toggle('icon-save', !isAdded);
  icon.classList.toggle('icon-save-filled', isAdded);
  icon.classList.toggle('text-gray-400', !isAdded);
  icon.classList.toggle('text-red-500', isAdded);
  
  // Update accessibility attributes
  btn.setAttribute('aria-pressed', isAdded);
  btn.title = isAdded ? 'Remove from Favorites (click to undo)' : 'Add to Favorites';
  tooltip.textContent = isAdded ? 'Remove Favorite' : 'Add Favorite';
}

function showErrorFeedback(element) {
  element.classList.add('animate-shake');
  setTimeout(() => element.classList.remove('animate-shake'), 500);
}

function getCSRFToken() {
  return document.querySelector('[name=csrfmiddlewaretoken]')?.value;
}




document.addEventListener("DOMContentLoaded", function () {
  const favoritesContainer = document.getElementById("favorites-button-container");
  const favoritesCountSpan = document.getElementById("favorites-count");

  document.body.addEventListener("click", function (e) {
    const btn = e.target.closest(".favorite-toggle");
    if (!btn) return;

    e.preventDefault();
    const propertyId = btn.dataset.id;
    const icon = btn.querySelector("i");
    const tooltip = btn.querySelector(".tooltip");

    fetch(`/property/${propertyId}/favorite/toggle/`, {
      method: "POST",
      headers: {
        "X-CSRFToken": getCSRFToken(),
        "Content-Type": "application/x-www-form-urlencoded",
      },
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.status === "added") {
          icon.classList.remove("icon-save");
          icon.classList.add("icon-save-filled", "text-red-500");
          tooltip.textContent = "Remove Favorite";
          btn.setAttribute("aria-pressed", "true");
        } else {
          icon.classList.remove("icon-save-filled", "text-red-500");
          icon.classList.add("icon-save");
          tooltip.textContent = "Add Favorite";
          btn.setAttribute("aria-pressed", "false");
        }

        // Update the favorites count in navbar
        if (favoritesCountSpan) {
          let currentCount = parseInt(favoritesCountSpan.textContent || "0");
          if (data.status === "added") {
            currentCount += 1;
          } else if (currentCount > 0) {
            currentCount -= 1;
          }
          favoritesCountSpan.textContent = currentCount;

          // Show/hide the button based on count
          if (favoritesContainer) {
            favoritesContainer.style.display = currentCount > 0 ? "block" : "none";
          }
        }
      })
      .catch((err) => console.error("Favorite toggle failed:", err));
  });

  function getCSRFToken() {
    return document.querySelector("[name=csrfmiddlewaretoken]")?.value;
  }
});
