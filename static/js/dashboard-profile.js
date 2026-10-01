(function() {
    const root = document.getElementById("dashboardProfile");
    if (!root) return;

    const state = {
        profile: window.NOMADX_PROFILE || {},
        googleReady: false,
        googleLoading: false
    };

    const toggle = document.getElementById("profileToggle");
    const dropdown = document.getElementById("profileDropdown");
    const avatar = document.getElementById("profileAvatar");
    const nameText = document.getElementById("profileName");
    const nameInput = document.getElementById("profileNameInput");
    const photoInput = document.getElementById("profilePhotoInput");
    const form = document.getElementById("profileForm");
    const removePhotoButton = document.getElementById("removeProfilePhoto");
    const googleButton = document.getElementById("googleConnectButton");
    const googleForm = document.getElementById("googleProfileForm");
    const googleNameInput = document.getElementById("googleNameInput");
    const googleEmailInput = document.getElementById("googleEmailInput");
    const googlePictureInput = document.getElementById("googlePictureInput");
    const saveGoogleButton = document.getElementById("saveGoogleProfile");
    const status = document.getElementById("profileStatus");

    function setStatus(message, isError) {
        status.textContent = message || "";
        status.style.color = isError ? "#ffd1d1" : "#d8f3ff";
    }

    async function api(url, options) {
        const response = await fetch(url, options || {});
        const data = await response.json().catch(() => ({}));
        if (!response.ok || data.success === false) {
            throw new Error(data.error || "Profile update failed");
        }
        return data;
    }

    function updateProfile(profile) {
        if (!profile) return;
        state.profile = profile;
        const displayName = profile.username || profile.google_name || profile.email || "NomadX Traveler";
        const initial = profile.initial || displayName.trim().slice(0, 1).toUpperCase() || "N";
        const photoUrl = profile.photo_url || profile.profile_image || profile.google_picture || "";

        nameText.textContent = displayName;
        nameInput.value = profile.username || "";
        googleNameInput.value = profile.google_name || "";
        googleEmailInput.value = profile.google_email || "";
        googlePictureInput.value = profile.google_picture || "";

        avatar.innerHTML = "";
        if (photoUrl) {
            const image = document.createElement("img");
            image.src = photoUrl;
            image.alt = "Profile photo";
            avatar.appendChild(image);
        } else {
            const span = document.createElement("span");
            span.id = "profileInitial";
            span.textContent = initial;
            avatar.appendChild(span);
        }
    }

    function openDropdown() {
        dropdown.hidden = false;
        toggle.setAttribute("aria-expanded", "true");
    }

    function closeDropdown() {
        dropdown.hidden = true;
        toggle.setAttribute("aria-expanded", "false");
    }

    function toggleDropdown() {
        if (dropdown.hidden) {
            openDropdown();
        } else {
            closeDropdown();
        }
    }

    async function saveName() {
        const username = nameInput.value.trim();
        if (!username) {
            throw new Error("Please enter a profile name");
        }
        const data = await api("/api/profile", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username })
        });
        updateProfile(data.profile);
    }

    async function uploadPhoto() {
        const file = photoInput.files && photoInput.files[0];
        if (!file) return;
        const formData = new FormData();
        formData.append("file", file);
        const data = await api("/api/profile/photo", {
            method: "POST",
            body: formData
        });
        photoInput.value = "";
        updateProfile(data.profile);
    }

    async function saveGoogleDetails(payload) {
        const data = await api("/api/profile/google", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        updateProfile(data.profile);
        setStatus("Google profile saved.");
    }

    function loadGoogleIdentity() {
        const clientId = window.NOMADX_GOOGLE_CLIENT_ID || "";
        if (!clientId) {
            return Promise.resolve(false);
        }
        if (state.googleReady) {
            return Promise.resolve(true);
        }
        if (state.googleLoading) {
            return new Promise((resolve) => {
                const timer = setInterval(() => {
                    if (state.googleReady) {
                        clearInterval(timer);
                        resolve(true);
                    }
                }, 100);
            });
        }

        state.googleLoading = true;
        return new Promise((resolve) => {
            const script = document.createElement("script");
            script.src = "https://accounts.google.com/gsi/client";
            script.async = true;
            script.defer = true;
            script.onload = function() {
                if (!window.google || !window.google.accounts || !window.google.accounts.id) {
                    resolve(false);
                    return;
                }
                window.google.accounts.id.initialize({
                    client_id: clientId,
                    callback: function(response) {
                        if (response && response.credential) {
                            saveGoogleDetails({ credential: response.credential }).catch((error) => {
                                setStatus(error.message, true);
                            });
                        }
                    }
                });
                state.googleReady = true;
                resolve(true);
            };
            script.onerror = function() {
                resolve(false);
            };
            document.head.appendChild(script);
        });
    }

    toggle.addEventListener("click", function(event) {
        event.stopPropagation();
        toggleDropdown();
    });

    dropdown.addEventListener("click", function(event) {
        event.stopPropagation();
    });

    document.addEventListener("click", closeDropdown);
    document.addEventListener("keydown", function(event) {
        if (event.key === "Escape") {
            closeDropdown();
        }
    });

    form.addEventListener("submit", async function(event) {
        event.preventDefault();
        setStatus("Saving profile...");
        try {
            await saveName();
            await uploadPhoto();
            setStatus("Profile saved.");
        } catch (error) {
            setStatus(error.message, true);
        }
    });

    removePhotoButton.addEventListener("click", async function() {
        setStatus("Removing photo...");
        try {
            const data = await api("/api/profile/photo", { method: "DELETE" });
            updateProfile(data.profile);
            setStatus("Profile photo removed.");
        } catch (error) {
            setStatus(error.message, true);
        }
    });

    googleForm.addEventListener("submit", async function(event) {
        event.preventDefault();
        setStatus("Saving Google details...");
        try {
            await saveGoogleDetails({
                google_name: googleNameInput.value.trim(),
                google_email: googleEmailInput.value.trim(),
                google_picture: googlePictureInput.value.trim()
            });
        } catch (error) {
            setStatus(error.message, true);
        }
    });

    googleButton.addEventListener("click", async function() {
        setStatus("Opening Google...");
        const ready = await loadGoogleIdentity();
        if (!ready) {
            setStatus("Google sign-in is not configured. You can save Google details below.", true);
            googleNameInput.focus();
            return;
        }
        window.google.accounts.id.prompt();
        setStatus("Choose your Google account to connect.");
    });

    updateProfile(state.profile);
})();
