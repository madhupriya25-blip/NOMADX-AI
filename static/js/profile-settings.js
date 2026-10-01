(function() {
    const state = {
        profile: window.NOMADX_PROFILE || {},
        languages: window.NOMADX_LANGUAGES || [],
        translations: {},
        googleLoading: null
    };

    const $ = (selector) => document.querySelector(selector);
    const $$ = (selector) => Array.from(document.querySelectorAll(selector));

    function initials(name) {
        return (name || "N")
            .trim()
            .split(/\s+/)
            .filter(Boolean)
            .slice(0, 2)
            .map((part) => part[0])
            .join("")
            .toUpperCase() || "N";
    }

    function displayName(profile) {
        return profile.username || profile.google_name || profile.email || "NomadX Traveler";
    }

    function profilePhoto(profile) {
        return profile.photo_url || profile.profile_image || profile.google_picture || "";
    }

    async function apiJson(url, options) {
        const response = await fetch(url, options || {});
        const data = await response.json().catch(() => ({}));
        if (!response.ok || data.success === false) {
            throw new Error(data.error || "Request failed");
        }
        return data;
    }

    function normalizeProfile(profile) {
        if (!profile) return;
        state.profile = {
            ...state.profile,
            ...profile,
            username: profile.username || "",
            email: profile.email || "",
            phone_number: profile.phone_number || profile.phone || "",
            theme: profile.theme || "dark",
            language: profile.language || "en",
            currency: profile.currency || "USD",
            notifications: profile.notifications !== false,
            email_prefs: profile.email_prefs !== false
        };
    }

    function renderAvatar(target, profile) {
        if (!target) return;
        const name = displayName(profile);
        const photo = profilePhoto(profile);
        target.innerHTML = "";
        if (photo) {
            const img = document.createElement("img");
            img.src = photo;
            img.alt = name;
            target.appendChild(img);
            return;
        }
        target.textContent = initials(name);
    }

    function ensureTrigger() {
        let trigger = $("#nxProfileTrigger");
        if (trigger) return trigger;

        const nav = $(".navbar-custom .container-fluid") ||
            $(".header .nav") ||
            $("header .nav") ||
            $("nav.navbar") ||
            $(".navbar") ||
            $(".nav") ||
            document.body;

        trigger = document.createElement("button");
        trigger.type = "button";
        trigger.id = "nxProfileTrigger";
        trigger.className = "nx-profile-trigger";
        trigger.innerHTML = `
            <span class="nx-avatar" data-profile-avatar></span>
            <span class="nx-profile-trigger__name" data-profile-name>NomadX Traveler</span>
            <i class="fas fa-chevron-down" aria-hidden="true"></i>
        `;
        nav.appendChild(trigger);
        return trigger;
    }

    function fillForm() {
        const profile = state.profile;
        if ($("#nxNameInput")) $("#nxNameInput").value = displayName(profile);
        if ($("#nxEmailInput")) $("#nxEmailInput").value = profile.email || "";
        if ($("#nxPhoneInput")) $("#nxPhoneInput").value = profile.phone_number || "";
        if ($("#nxThemeSelect")) $("#nxThemeSelect").value = profile.theme || "dark";
        if ($("#nxLanguageSelect")) $("#nxLanguageSelect").value = profile.language || "en";
        if ($("#nxCurrencySelect")) $("#nxCurrencySelect").value = profile.currency || "USD";
        if ($("#nxNotificationsInput")) $("#nxNotificationsInput").checked = profile.notifications !== false;
        if ($("#nxEmailPrefsInput")) $("#nxEmailPrefsInput").checked = profile.email_prefs !== false;
    }

    function updateProfileUI() {
        const profile = state.profile;
        const name = displayName(profile);
        const email = profile.email || profile.google_email || "";
        const firstName = name.trim().split(/\s+/)[0] || "NomadX";

        $$("[data-profile-name], #displayName, #profileName, .profile-name-nav, #navUserName").forEach((element) => {
            element.textContent = name;
        });
        $$("[data-profile-email], #profileEmail").forEach((element) => {
            element.textContent = email;
        });
        $$("[data-profile-avatar], #profileAvatar, #profileAvatarLarge, #navAvatar").forEach((element) => {
            renderAvatar(element, profile);
        });
        const welcomeName = $("#welcomeName");
        if (welcomeName) welcomeName.textContent = firstName;

        const googleStatus = $("#nxGoogleStatus");
        if (googleStatus) {
            googleStatus.textContent = profile.google_email || profile.google_name || profile.google_picture ? "Connected" : "Connect";
        }

        fillForm();
        applyTheme(profile.theme || "dark");
        applyLanguage(profile.language || "en");
    }

    function setStatus(message, isError) {
        const status = $("#nxProfileStatus");
        if (!status) return;
        status.textContent = message || "";
        status.style.color = isError ? "#f87171" : "";
    }

    function toast(message) {
        const container = $("#nxToastContainer") || $("#toastContainer");
        if (!container) return;
        const item = document.createElement("div");
        item.className = container.id === "nxToastContainer" ? "nx-toast" : "toast-custom";
        item.textContent = message;
        container.appendChild(item);
        setTimeout(() => item.remove(), 3600);
    }

    function openMenu() {
        const menu = $("#nxProfileMenu");
        if (menu) menu.hidden = false;
    }

    function closeMenu() {
        const menu = $("#nxProfileMenu");
        if (menu) menu.hidden = true;
    }

    function openSettings() {
        fillForm();
        const modal = $("#nxSettingsModal");
        if (modal) modal.hidden = false;
        closeMenu();
    }

    function closeSettings() {
        const modal = $("#nxSettingsModal");
        if (modal) modal.hidden = true;
        setStatus("");
    }

    function applyTheme(theme) {
        const resolved = theme === "auto"
            ? (window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark")
            : theme;
        document.documentElement.dataset.nxTheme = resolved;
        document.body.classList.toggle("nx-theme-light", resolved === "light");
        document.body.classList.toggle("nx-theme-dark", resolved !== "light");
    }

    async function loadTranslations() {
        if (Object.keys(state.translations).length) return;
        try {
            const response = await fetch("/static/i18n/app.json");
            state.translations = await response.json();
        } catch (error) {
            state.translations = {};
        }
    }

    function textFor(key, language) {
        const baseLanguage = (language || "en").split("-")[0];
        const pack = state.translations[language] || state.translations[baseLanguage] || state.translations.en || {};
        return pack[key] || (state.translations.en && state.translations.en[key]) || "";
    }

    async function applyLanguage(language) {
        await loadTranslations();
        const metadata = state.languages.find((item) => item.code === language) || state.languages.find((item) => item.code === "en");
        if (metadata) {
            document.documentElement.lang = metadata.code;
            document.documentElement.dir = metadata.dir || "ltr";
        }
        $$("[data-i18n]").forEach((element) => {
            const value = textFor(element.dataset.i18n, language);
            if (value) element.textContent = value;
        });
    }

    async function loadProfile() {
        try {
            const data = await apiJson("/api/profile");
            normalizeProfile(data.profile);
            if (Array.isArray(data.languages)) state.languages = data.languages;
        } catch (error) {
            console.error("Profile load failed:", error);
        }
        updateProfileUI();
    }

    async function saveProfileAndSettings(event) {
        event.preventDefault();
        setStatus("Saving...");
        const username = $("#nxNameInput").value.trim();
        const email = $("#nxEmailInput").value.trim();
        const phoneNumber = $("#nxPhoneInput").value.trim();
        const theme = $("#nxThemeSelect").value;
        const language = $("#nxLanguageSelect").value;
        const currency = $("#nxCurrencySelect").value;
        try {
            const profileData = await apiJson("/api/profile", {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, email, phone_number: phoneNumber })
            });
            normalizeProfile(profileData.profile);

            const settingsData = await apiJson("/api/settings", {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    theme,
                    language,
                    currency,
                    notifications: $("#nxNotificationsInput").checked,
                    email_prefs: $("#nxEmailPrefsInput").checked
                })
            });
            normalizeProfile(settingsData.profile);
            updateProfileUI();
            closeSettings();
            toast("Profile and settings saved.");
        } catch (error) {
            setStatus(error.message, true);
        }
    }

    async function uploadPhoto(file) {
        if (!file) return;
        if (!file.type.startsWith("image/")) {
            toast("Please choose an image file.");
            return;
        }
        const formData = new FormData();
        formData.append("file", file);
        try {
            const data = await apiJson("/api/profile/photo", { method: "POST", body: formData });
            normalizeProfile(data.profile);
            updateProfileUI();
            toast("Profile photo updated.");
        } catch (error) {
            toast(error.message);
        }
    }

    function loadGoogleIdentity() {
        const clientId = window.NOMADX_GOOGLE_CLIENT_ID || "";
        if (!clientId) return Promise.resolve(false);
        if (window.google && window.google.accounts && window.google.accounts.id) return Promise.resolve(true);
        if (state.googleLoading) return state.googleLoading;
        state.googleLoading = new Promise((resolve) => {
            const script = document.createElement("script");
            script.src = "https://accounts.google.com/gsi/client";
            script.async = true;
            script.defer = true;
            script.onload = () => resolve(Boolean(window.google && window.google.accounts && window.google.accounts.id));
            script.onerror = () => resolve(false);
            document.head.appendChild(script);
        });
        return state.googleLoading;
    }

    async function saveGoogle(payload) {
        const data = await apiJson("/api/profile/google", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        normalizeProfile(data.profile);
        updateProfileUI();
    }

    async function handleGoogle() {
        closeMenu();
        try {
            if (state.profile.google_email || state.profile.google_name || state.profile.google_picture) {
                const data = await apiJson("/api/profile/google", { method: "DELETE" });
                normalizeProfile(data.profile);
                updateProfileUI();
                toast("Google account unlinked.");
                return;
            }
            const ready = await loadGoogleIdentity();
            if (ready) {
                window.google.accounts.id.initialize({
                    client_id: window.NOMADX_GOOGLE_CLIENT_ID,
                    callback: async(response) => {
                        if (response && response.credential) {
                            await saveGoogle({ credential: response.credential });
                            toast("Google account linked.");
                        }
                    }
                });
                window.google.accounts.id.prompt();
                return;
            }
            const googleName = window.prompt("Google name", displayName(state.profile));
            if (!googleName) return;
            const googleEmail = window.prompt("Google email", state.profile.email || "");
            if (!googleEmail) return;
            await saveGoogle({ google_name: googleName.trim(), google_email: googleEmail.trim() });
            toast("Google account linked.");
        } catch (error) {
            toast(error.message);
        }
    }

    function bindEvents() {
        const trigger = ensureTrigger();
        trigger.addEventListener("click", (event) => {
            event.stopPropagation();
            const menu = $("#nxProfileMenu");
            if (menu) menu.hidden ? openMenu() : closeMenu();
        });
        $("#nxProfileMenu")?.addEventListener("click", (event) => event.stopPropagation());
        document.addEventListener("click", closeMenu);
        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape") {
                closeMenu();
                closeSettings();
            }
        });
        $("#nxEditProfileBtn")?.addEventListener("click", openSettings);
        $("#nxSettingsBtn")?.addEventListener("click", openSettings);
        $("#nxUploadPhotoBtn")?.addEventListener("click", () => $("#nxProfilePhotoInput")?.click());
        $("#nxProfilePhotoInput")?.addEventListener("change", (event) => uploadPhoto(event.target.files && event.target.files[0]));
        $("#nxGoogleBtn")?.addEventListener("click", handleGoogle);
        $("#nxCloseSettingsBtn")?.addEventListener("click", closeSettings);
        $("#nxCancelSettingsBtn")?.addEventListener("click", closeSettings);
        $("#nxSettingsModal")?.addEventListener("click", (event) => {
            if (event.target.id === "nxSettingsModal") closeSettings();
        });
        $("#nxSettingsForm")?.addEventListener("submit", saveProfileAndSettings);
        $("#nxThemeSelect")?.addEventListener("change", (event) => applyTheme(event.target.value));
        $("#nxLanguageSelect")?.addEventListener("change", (event) => applyLanguage(event.target.value));
    }

    document.addEventListener("DOMContentLoaded", () => {
        normalizeProfile(state.profile);
        bindEvents();
        updateProfileUI();
        loadProfile();
    });
})();
