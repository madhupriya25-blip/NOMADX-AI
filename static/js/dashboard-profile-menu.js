(function() {
        let userProfile = {
            name: "NomadX Traveler",
            email: "traveler@nomadx.ai",
            photo: "",
            googleLinked: false,
            googleName: "",
            googleEmail: "",
            googlePhoto: "",
            theme: "dark",
            language: "en",
            notifications: true,
            emailPrefs: true,
            currency: "USD",
            ...(window.NOMADX_DASHBOARD_PROFILE || {})
        };

        let googleIdentityLoading = null;

        function initialsFor(name) {
            return (name || "N")
                .trim()
                .split(/\s+/)
                .filter(Boolean)
                .slice(0, 2)
                .map(part => part[0])
                .join("")
                .toUpperCase() || "N";
        }

        function firstName(name) {
            return (name || "NomadX").trim().split(/\s+/)[0] || "NomadX";
        }

        function normalizeProfile(profile) {
            if (!profile) return;
            const displayName = profile.username || profile.google_name || profile.email || userProfile.name;
            userProfile = {
                ...userProfile,
                name: displayName,
                email: profile.email || profile.google_email || userProfile.email,
                photo: profile.photo_url || profile.profile_image || profile.google_picture || "",
                googleLinked: Boolean(profile.google_email || profile.google_name || profile.google_picture),
                googleName: profile.google_name || "",
                googleEmail: profile.google_email || "",
                googlePhoto: profile.google_picture || "",
                theme: profile.theme || userProfile.theme || "dark",
                language: profile.language || userProfile.language || "en",
                notifications: profile.notifications !== undefined ? Boolean(profile.notifications) : userProfile.notifications,
                emailPrefs: profile.email_prefs !== undefined ? Boolean(profile.email_prefs) : userProfile.emailPrefs,
                currency: profile.currency || userProfile.currency || "USD"
            };
        }

        async function apiJson(url, options = {}) {
            const response = await fetch(url, options);
            const data = await response.json().catch(() => ({}));
            if (!response.ok || data.success === false) {
                const error = new Error(data.error || "Request failed");
                error.status = response.status;
                throw error;
            }
            return data;
        }

        function updateAvatar(container, photoUrl, initials) {
            container.innerHTML = "";
            if (photoUrl) {
                const image = document.createElement("img");
                image.src = photoUrl;
                image.alt = userProfile.name;
                container.appendChild(image);
                return;
            }

            const fallback = document.createElement(container.id === "profileAvatarLarge" ? "div" : "span");
            fallback.textContent = initials;
            if (container.id === "profileAvatarLarge") {
                fallback.className = "avatar-placeholder";
                fallback.id = "avatarPlaceholder";
            } else {
                fallback.id = "avatarInitials";
            }
            container.appendChild(fallback);
        }

        function updateProfileUI() {
            const initials = initialsFor(userProfile.name);
            const displayName = document.getElementById("displayName");
            const profileName = document.getElementById("profileName");
            const welcomeName = document.getElementById("welcomeName");
            const profileEmail = document.getElementById("profileEmail");
            const profileAvatar = document.getElementById("profileAvatar");
            const profileAvatarLarge = document.getElementById("profileAvatarLarge");
            const badge = document.getElementById("googleBadge");

            if (displayName) displayName.textContent = userProfile.name;
            if (profileName) profileName.textContent = userProfile.name;
            if (welcomeName) welcomeName.textContent = firstName(userProfile.name);
            if (profileEmail) profileEmail.textContent = userProfile.email;
            if (profileAvatar) updateAvatar(profileAvatar, userProfile.photo, initials);
            if (profileAvatarLarge) updateAvatar(profileAvatarLarge, userProfile.photo, initials);

            if (badge) {
                badge.textContent = userProfile.googleLinked ? "Connected" : "+ Connect";
                badge.className = userProfile.googleLinked ? "google-badge connected" : "google-badge";
            }
        }

        function updateSettingsInputs() {
            const theme = document.getElementById("themeSelect");
            const language = document.getElementById("languageSelect");
            const notifications = document.getElementById("notifToggle");
            const emailPrefs = document.getElementById("emailToggle");
            const currency = document.getElementById("currencySelect");

            if (theme) theme.value = userProfile.theme || "dark";
            if (language) language.value = userProfile.language || "en";
            if (notifications) notifications.checked = Boolean(userProfile.notifications);
            if (emailPrefs) emailPrefs.checked = Boolean(userProfile.emailPrefs);
            if (currency) currency.value = userProfile.currency || "USD";
        }

        async function loadProfileFromFlask() {
            try {
                const data = await apiJson("/api/profile");
                normalizeProfile(data.profile);
                updateProfileUI();
                updateSettingsInputs();
            } catch (error) {
                console.error("Error loading profile:", error);
            }
        }

        async function editProfileName() {
            const newName = prompt("Enter your full name:", userProfile.name);
            if (!newName || !newName.trim()) return;

            const username = newName.trim();
            try {
                const data = await apiJson("/api/profile", {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ username })
                });
                normalizeProfile(data.profile);
                updateProfileUI();
                showToast("Profile name updated.", "Success");
            } catch (error) {
                if (error.status === 404) {
                    try {
                        const formData = new FormData();
                        formData.append("username", username);
                        const response = await fetch(url, options);
                        method: "POST",
                            body: formData
                    });
                if (!response.ok) {
                    throw new Error("Profile name could not be saved.");
                }
                userProfile.name = username;
                updateProfileUI();
                showToast("Profile name updated.", "Success");
                return;
            } catch (fallbackError) {
                showToast(fallbackError.message, "Error");
                return;
            }
        }
        showToast(error.message, "Error");
    }
}

async function uploadProfilePhoto(file) {
    if (!file.type.startsWith("image/")) {
        throw new Error("Please select an image file.");
    }
    if (file.size > 5 * 1024 * 1024) {
        throw new Error("Image size should be less than 5MB.");
    }

    const formData = new FormData();
    formData.append("file", file);
    const data = await apiJson("/api/profile/photo", {
        method: "POST",
        body: formData
    });
    normalizeProfile(data.profile);
}

function loadGoogleIdentity() {
    const clientId = window.NOMADX_GOOGLE_CLIENT_ID || "";
    if (!clientId) return Promise.resolve(false);
    if (window.google && window.google.accounts && window.google.accounts.id) {
        return Promise.resolve(true);
    }
    if (googleIdentityLoading) return googleIdentityLoading;

    googleIdentityLoading = new Promise(resolve => {
        const script = document.createElement("script");
        script.src = "https://accounts.google.com/gsi/client";
        script.async = true;
        script.defer = true;
        script.onload = () => resolve(Boolean(window.google && window.google.accounts && window.google.accounts.id));
        script.onerror = () => resolve(false);
        document.head.appendChild(script);
    });
    return googleIdentityLoading;
}

async function saveGoogleProfile(payload) {
    const data = await apiJson("/api/profile/google", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });
    normalizeProfile(data.profile);
}

async function promptForGoogleDetails() {
    const googleName = prompt("Enter your Google name:", userProfile.googleName || userProfile.name);
    if (!googleName || !googleName.trim()) return false;
    const googleEmail = prompt("Enter your Google email:", userProfile.googleEmail || userProfile.email);
    if (!googleEmail || !googleEmail.trim()) return false;

    await saveGoogleProfile({
        google_name: googleName.trim(),
        google_email: googleEmail.trim()
    });
    return true;
}

async function handleGoogleLink() {
    try {
        if (userProfile.googleLinked) {
            if (!confirm("Do you want to unlink your Google account?")) return;
            const data = await apiJson("/api/profile/google", { method: "DELETE" });
            normalizeProfile(data.profile);
            updateProfileUI();
            showToast("Google account unlinked.", "Success");
            return;
        }

        const ready = await loadGoogleIdentity();
        if (ready) {
            window.google.accounts.id.initialize({
                client_id: window.NOMADX_GOOGLE_CLIENT_ID,
                callback: async response => {
                    try {
                        await saveGoogleProfile({ credential: response.credential });
                        updateProfileUI();
                        showToast("Google account linked.", "Success");
                    } catch (error) {
                        showToast(error.message, "Error");
                    }
                }
            });
            window.google.accounts.id.prompt();
            showToast("Choose your Google account to continue.", "Google Connect");
            return;
        }

        const saved = await promptForGoogleDetails();
        if (saved) {
            updateProfileUI();
            showToast("Google account linked.", "Success");
        }
    } catch (error) {
        showToast(error.message, "Error");
    }
}

function openSettings() {
    updateSettingsInputs();
    document.getElementById("settingsModal").classList.add("show");
}

function closeSettings() {
    document.getElementById("settingsModal").classList.remove("show");
}

async function saveSettings() {
    const settings = {
        theme: document.getElementById("themeSelect").value,
        language: document.getElementById("languageSelect").value,
        notifications: document.getElementById("notifToggle").checked,
        email_prefs: document.getElementById("emailToggle").checked,
        currency: document.getElementById("currencySelect").value
    };

    try {
        const data = await apiJson("/api/settings", {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(settings)
        });
        normalizeProfile(data.profile);
        updateSettingsInputs();
        closeSettings();
        showToast("Settings saved.", "Success");
    } catch (error) {
        showToast(error.message, "Error");
    }
}

function handleLogout() {
    if (confirm("Are you sure you want to logout?")) {
        showToast("Logging out...", "Goodbye");
        setTimeout(() => {
            window.location.href = "/logout";
        }, 600);
    }
}

function showToast(message, title = "") {
    const container = document.getElementById("toastContainer");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = "toast-custom";

    const closeButton = document.createElement("button");
    closeButton.className = "toast-close";
    closeButton.type = "button";
    closeButton.textContent = "x";
    closeButton.addEventListener("click", () => toast.remove());

    const titleEl = document.createElement("div");
    titleEl.className = "toast-title";
    titleEl.textContent = title || "Notification";

    const messageEl = document.createElement("div");
    messageEl.className = "toast-message";
    messageEl.textContent = message;

    toast.append(closeButton, titleEl, messageEl);
    container.appendChild(toast);

    setTimeout(() => {
        if (toast.parentElement) {
            toast.style.opacity = "0";
            toast.style.transition = "opacity 0.4s";
            setTimeout(() => toast.remove(), 400);
        }
    }, 4000);
}

document.addEventListener("DOMContentLoaded", function() {
const profileToggle = document.getElementById("profileToggle");
const profileMenu = document.getElementById("profileMenu");
const profileImageInput = document.getElementById("profileImageInput");

if (!profileToggle || !profileMenu) return;

updateProfileUI();
updateSettingsInputs();
loadProfileFromFlask();

profileToggle.addEventListener("click", function(event) {
    event.stopPropagation();
    profileMenu.classList.toggle("show");
});

document.addEventListener("click", function(event) {
    if (!profileToggle.contains(event.target) && !profileMenu.contains(event.target)) {
        profileMenu.classList.remove("show");
    }
});

document.getElementById("editNameBtn").addEventListener("click", function(event) {
    event.stopPropagation();
    profileMenu.classList.remove("show");
    editProfileName();
});

document.getElementById("uploadPhotoBtn").addEventListener("click", function(event) {
    event.stopPropagation();
    profileMenu.classList.remove("show");
    profileImageInput.click();
});

profileImageInput.addEventListener("change", async function() {
    const file = this.files && this.files[0];
    if (!file) return;
    try {
        await uploadProfilePhoto(file);
        updateProfileUI();
        showToast("Profile picture updated.", "Success");
    } catch (error) {
        showToast(error.message, "Error");
    } finally {
        this.value = "";
    }
});

document.getElementById("linkGoogleBtn").addEventListener("click", function(event) {
    event.stopPropagation();
    profileMenu.classList.remove("show");
    handleGoogleLink();
});

document.getElementById("settingsBtn").addEventListener("click", function(event) {
    event.stopPropagation();
    profileMenu.classList.remove("show");
    openSettings();
});

document.getElementById("logoutBtn").addEventListener("click", function(event) {
    event.stopPropagation();
    profileMenu.classList.remove("show");
    handleLogout();
});

document.getElementById("closeSettingsBtn").addEventListener("click", closeSettings);
document.getElementById("saveSettingsBtn").addEventListener("click", saveSettings);
document.getElementById("settingsModal").addEventListener("click", function(event) {
    if (event.target === this) closeSettings();
});
document.addEventListener("keydown", function(event) {
    if (event.key === "Escape") closeSettings();
});
});
})();