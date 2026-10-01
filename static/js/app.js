(function() {
    const jsonHeaders = { "Content-Type": "application/json" };

    async function api(url, options = {}) {
        const response = await fetch(url, options);
        const data = await response.json().catch(() => ({}));
        if (!response.ok || data.success === false) {
            throw new Error(data.error || "NomadX request failed");
        }
        return data;
    }

    function escapeHtml(value) {
        return String(value || "").replace(/[&<>"']/g, (char) => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#039;"
        }[char]));
    }

    function money(value, suffix) {
        const amount = Number(value || 0).toLocaleString("en-IN", { maximumFractionDigits: 0 });
        return `Rs ${amount}<span>${suffix}</span>`;
    }

    function setupChatbot() {
        const form = document.getElementById("chatForm");
        const input = document.getElementById("messageInput");
        const chatBox = document.getElementById("chatBox");
        if (!form || !input || !chatBox) return;

        const storageKey = "nomadx_chat_history";
        let historyLoaded = false;

        const add = (text, sender) => {
            const msg = document.createElement("div");
            msg.className = `message ${sender}`;
            msg.innerHTML = `<div class="bubble">${escapeHtml(text)}</div>`;
            chatBox.appendChild(msg);
            chatBox.scrollTop = chatBox.scrollHeight;
            return msg;
        };

        const readStoredHistory = () => {
            try {
                const raw = sessionStorage.getItem(storageKey) || localStorage.getItem(storageKey);
                const turns = JSON.parse(raw || "[]");
                return Array.isArray(turns) ? turns.slice(-12) : [];
            } catch (_) {
                return [];
            }
        };

        const writeStoredHistory = (turns) => {
            try {
                const compact = JSON.stringify(turns.slice(-12));
                sessionStorage.setItem(storageKey, compact);
                localStorage.setItem(storageKey, compact);
            } catch (_) {}
        };

        const rememberTurn = (message, reply) => {
            const turns = readStoredHistory();
            turns.push({ message, reply, created_at: new Date().toISOString() });
            writeStoredHistory(turns);
        };

        const startTyping = () => {
            const msg = add("NomadX AI is typing", "ai");
            const bubble = msg.querySelector(".bubble");
            let dots = 0;
            const timer = setInterval(() => {
                dots = (dots + 1) % 4;
                bubble.textContent = `NomadX AI is typing${".".repeat(dots)}`;
            }, 280);
            return { msg, bubble, stop: () => clearInterval(timer) };
        };

        const storedHistory = readStoredHistory();
        if (storedHistory.length) {
            historyLoaded = true;
            storedHistory.slice(-6).forEach((item) => {
                if (item.message) add(item.message, "user");
                if (item.reply) add(item.reply, "ai");
            });
        }

        api("/api/chat/history").then((data) => {
            if (historyLoaded || !data.history.length) return;
            historyLoaded = true;
            data.history.reverse().slice(-6).forEach((item) => {
                add(item.message, "user");
                add(item.reply, "ai");
            });
            writeStoredHistory(data.history);
        }).catch(() => {});

        form.addEventListener("submit", async(event) => {
            event.preventDefault();
            event.stopImmediatePropagation();
            const message = input.value.trim();
            if (!message) return;

            add(message, "user");
            input.value = "";
            const typing = startTyping();

            try {
                const data = await api("/api/chat", {
                    method: "POST",
                    headers: jsonHeaders,
                    body: JSON.stringify({ message })
                });
                const reply = data.reply || data.response || data.message || "I am ready to help. Try asking about hotels, restaurants, weather, trip plans, or emergency contacts.";
                const delay = Number(data.typing_delay_ms || 350);
                await new Promise((resolve) => setTimeout(resolve, Math.min(900, Math.max(180, delay))));
                typing.stop();
                typing.bubble.textContent = reply;
                rememberTurn(message, reply);
            } catch (error) {
                typing.stop();
                const reply = "I am still here. Please try that again, or ask about hotels, restaurants, weather, trip plans, rentals, or emergency contacts.";
                typing.bubble.textContent = reply;
                rememberTurn(message, reply);
            }
        }, true);

        window.quickMessage = function(text) {
            input.value = text;
            input.focus();
            form.requestSubmit();
        };
    }

    function setupHotels() {
        const grid = document.querySelector(".hotel-grid");
        const search = document.querySelector("form.search-box");
        if (!grid || !document.title.toLowerCase().includes("hotel")) return;

        const render = (items) => {
            grid.innerHTML = items.map((item) => `
                <div class="hotel-card">
                    <div class="hotel-content">
                        <h3>${escapeHtml(item.name)}</h3>
                        <div class="rating">Rating ${escapeHtml(item.rating)}</div>
                        <p>${escapeHtml(item.description)}</p>
                        <p><strong>Location:</strong> ${escapeHtml(item.address)}, ${escapeHtml(item.city)}</p>
                        <p><strong>Contact:</strong> ${escapeHtml(item.owner_phone)}</p>
                        <p><strong>Availability:</strong> ${escapeHtml(item.available_rooms)} rooms</p>
                        <div class="price">${money(item.price, "/night")}</div>
                        <button class="book-btn" data-id="${item.id}">Book Now</button>
                    </div>
                </div>
            `).join("");
        };

        const load = async() => {
            const params = new URLSearchParams(new FormData(search || document.createElement("form")));
            const data = await api(`/api/hotels/search?${params}`);
            render(data.hotels);
        };

        if (search) {
            search.addEventListener("submit", (event) => {
                event.preventDefault();
                load().catch((error) => alert(error.message));
            });
        }

        grid.addEventListener("click", async(event) => {
            const button = event.target.closest(".book-btn");
            if (!button || !button.dataset.id) return;
            const data = await api("/api/hotels/book", {
                method: "POST",
                headers: jsonHeaders,
                body: JSON.stringify({ hotel_id: button.dataset.id })
            });
            alert(data.message || "Hotel booking confirmed.");
        });
    }

    function setupRestaurants() {
        const grid = document.querySelector(".cards");
        const search = document.querySelector(".search-box");
        if (!grid || !search || !document.title.toLowerCase().includes("restaurant")) return;

        const render = (items) => {
            grid.innerHTML = items.map((item) => `
                <div class="card">
                    <img src="${escapeHtml(item.image)}" alt="Restaurant">
                    <div class="card-content">
                        <h3>${escapeHtml(item.name)}</h3>
                        <div class="rating">Rating ${escapeHtml(item.rating)}</div>
                        <p><strong>Cuisine:</strong> ${escapeHtml(item.cuisine)}</p>
                        <p><strong>Price:</strong> ${escapeHtml(item.price_range)}</p>
                        <p><strong>Location:</strong> ${escapeHtml(item.location)}, ${escapeHtml(item.city)}</p>
                        <p><strong>Contact:</strong> ${escapeHtml(item.contact_phone)}</p>
                        <p><strong>Tables:</strong> ${escapeHtml(item.available_tables)} available</p>
                        <p>${escapeHtml(item.description)}</p>
                        <button class="reserve-btn" data-id="${item.id}" data-name="${escapeHtml(item.name)}" data-location="${escapeHtml(item.location)}" data-price="${escapeHtml(item.price_range)}">Reserve Table</button>
                    </div>
                </div>
            `).join("");
        };

        const load = async() => {
            const inputs = search.querySelectorAll("input");
            const selects = search.querySelectorAll("select");
            const params = new URLSearchParams({
                location: inputs[1] ? .value || "",
                cuisine: selects[0] ? .value ? .replace("Select Cuisine", "") || "",
                price: selects[1] ? .value ? .replace("Price Range", "") || ""
            });
            const data = await api(`/api/restaurants?${params}`);
            render(data.restaurants);
        };

        search.addEventListener("click", (event) => {
            if (event.target.classList.contains("search-btn")) {
                event.preventDefault();
                load().catch((error) => alert(error.message));
            }
        });

        grid.addEventListener("click", async(event) => {
            const button = event.target.closest(".reserve-btn");
            if (!button) return;
            const payload = {
                booking_type: "restaurant",
                item_id: button.dataset.id,
                item_name: button.dataset.name,
                location: button.dataset.location,
                price: button.dataset.price,
                booking_date: new Date().toISOString().slice(0, 10)
            };
            const data = await api("/api/restaurants/book", {
                method: "POST",
                headers: jsonHeaders,
                body: JSON.stringify({ restaurant_id: payload.item_id })
            }).catch(() => api("/api/bookings", { method: "POST", headers: jsonHeaders, body: JSON.stringify(payload) }));
            alert(data.message || "Restaurant table reserved.");
        });

        load().catch(() => {});
    }

    function setupRentals() {
        const grid = document.querySelector(".rentals-grid");
        if (!grid) return;

        const render = (items) => {
            grid.innerHTML = items.map((item) => `
                <div class="rental-card">
                    <div class="rental-image"><img src="${escapeHtml(item.image)}" alt="${escapeHtml(item.vehicle)}"></div>
                    <div class="rental-content">
                        <div class="rental-top">
                            <h3>${escapeHtml(item.vehicle)}</h3>
                            <span class="rating">Rating ${escapeHtml(item.rating)}</span>
                        </div>
                        <p class="category">${escapeHtml(item.vehicle_type)}</p>
                        <div class="rental-info">
                            <p><i class="fa-solid fa-location-dot"></i> ${escapeHtml(item.location)}, ${escapeHtml(item.city)}</p>
                            <p><i class="fa-solid fa-gas-pump"></i> ${escapeHtml(item.fuel_type)}</p>
                            <p><i class="fa-solid fa-gear"></i> ${escapeHtml(item.transmission)}</p>
                            <p><i class="fa-solid fa-building"></i> ${escapeHtml(item.rental_agency)}</p>
                            <p><i class="fa-solid fa-phone"></i> ${escapeHtml(item.owner_phone)}</p>
                            <p><i class="fa-solid fa-map-pin"></i> ${escapeHtml(item.pickup_address)}</p>
                            <p><i class="fa-solid fa-signal"></i> ${escapeHtml(item.availability)}</p>
                        </div>
                        <p class="description">${escapeHtml(item.description)}</p>
                        <div class="rental-bottom">
                            <div class="price">${money(item.price, "/day")}</div>
                            <button class="book-btn" data-id="${item.id}" data-name="${escapeHtml(item.vehicle)}" data-location="${escapeHtml(item.pickup_address)}" data-price="Rs ${escapeHtml(item.price)}/day">Book Now</button>
                        </div>
                    </div>
                </div>
            `).join("");
        };

        const load = async(params = new URLSearchParams()) => {
            const data = await api(`/api/rentals/search?${params}`);
            render(data.rentals);
        };

        load().catch(() => {});

        grid.addEventListener("click", async(event) => {
            const button = event.target.closest(".book-btn");
            if (!button) return;
            const data = await api("/api/rentals/book", {
                method: "POST",
                headers: jsonHeaders,
                body: JSON.stringify({ rental_id: button.dataset.id })
            }).catch(() => api("/api/bookings", {
                method: "POST",
                headers: jsonHeaders,
                body: JSON.stringify({
                    booking_type: "rental",
                    item_id: button.dataset.id,
                    item_name: button.dataset.name,
                    location: button.dataset.location,
                    price: button.dataset.price,
                    booking_date: new Date().toISOString().slice(0, 10)
                })
            }));
            alert(data.message || "Rental booking confirmed.");
        });
    }

    function setupTripPlanner() {
        if (!document.getElementById("aiResult")) return;

        window.generateTrip = async function() {
            const destination = document.getElementById("destination").value.trim();
            const travelDate = document.getElementById("travelDate").value;
            const budget = document.getElementById("budget").value;
            const result = document.getElementById("aiResult");

            if (!destination || !travelDate || !budget) {
                alert("Please fill all fields");
                return;
            }

            result.innerHTML = "Generating realtime AI travel plan...";
            try {
                const data = await api("/api/trip-plan", {
                    method: "POST",
                    headers: jsonHeaders,
                    body: JSON.stringify({ destination, travel_date: travelDate, budget })
                });
                const plan = data.plan;
                result.innerHTML = `
                    <h3>Trip Plan Generated Successfully</h3>
                    <p><strong>Destination:</strong> ${escapeHtml(plan.destination)}</p>
                    <p><strong>Date:</strong> ${escapeHtml(plan.travel_date)}</p>
                    <p><strong>Budget:</strong> ${escapeHtml(plan.budget)} | Estimated Daily Spend: $${escapeHtml(plan.daily_budget)}</p>
                    <br>
                    <p><strong>Hotels:</strong> ${plan.hotels.map(h => escapeHtml(h.name)).join(", ") || "AI will suggest nearby stays."}</p>
                    <p><strong>Restaurants:</strong> ${plan.restaurants.map(r => escapeHtml(r.name)).join(", ") || "Local dining recommendations pending."}</p>
                    <p><strong>Attractions:</strong> ${plan.attractions.map(escapeHtml).join(", ")}</p>
                    <p><strong>Routes:</strong> ${plan.routes.map(escapeHtml).join(" &rarr; ")}</p>
                    <p><strong>Weather:</strong> ${escapeHtml(plan.weather.temperature)}&deg;C, ${escapeHtml(plan.weather.condition)}. ${escapeHtml(plan.weather.recommendation)}</p>
                `;
            } catch (error) {
                result.textContent = error.message;
            }
        };
    }

    function setupWeather() {
        if (!document.getElementById("cityInput")) return;

        const loading = document.getElementById("loading");
        const cityInput = document.getElementById("cityInput");
        const countryInput = document.getElementById("countryInput");
        const forecastSection = document.querySelector(".forecast-section");
        const forecastGrid = forecastSection ? forecastSection.querySelector(".forecast-grid") : null;
        const analyticsSpans = document.querySelectorAll(".analytics .analytics-card span");
        let lastWeatherQuery = null;
        let lastLatLon = null;
        let refreshTimer = null;

        const showLoading = (message = "Loading realtime weather...") => {
            if (!loading) return;
            loading.textContent = message;
            loading.style.display = "block";
        };

        const hideLoading = () => {
            if (!loading) return;
            loading.style.display = "none";
            loading.textContent = "Loading realtime weather...";
        };

        const displayError = (message) => {
            if (!loading) return;
            loading.textContent = message;
            loading.style.display = "block";
            setTimeout(hideLoading, 5000);
        };

        const renderForecast = (daily = [], hourly = []) => {
            if (!forecastGrid) return;
            forecastGrid.innerHTML = "";

            daily.slice(0, 7).forEach((day) => {
                const card = document.createElement("div");
                card.className = "forecast-card";
                card.innerHTML = `
                    <h3>${escapeHtml(day.day || day.date || "Day")}</h3>
                    <i class="fa-solid fa-cloud-sun fa-2x"></i>
                    <p>${escapeHtml(day.temp ?? "--")}&deg;C</p>
                    <p>${escapeHtml(day.condition || "Unavailable")}</p>
                    <p>Rain ${escapeHtml(day.rain_probability ?? 0)}%</p>
                `;
                forecastGrid.appendChild(card);
            });

            if (!forecastSection) return;
            let hourlyHolder = document.getElementById("hourly-forecast");
            if (!hourlyHolder) {
                hourlyHolder = document.createElement("div");
                hourlyHolder.id = "hourly-forecast";
                hourlyHolder.style.marginTop = "22px";
                hourlyHolder.style.display = "grid";
                hourlyHolder.style.gridTemplateColumns = "repeat(auto-fit, minmax(140px, 1fr))";
                hourlyHolder.style.gap = "16px";
                forecastSection.insertBefore(hourlyHolder, forecastGrid.nextSibling);
            }

            hourlyHolder.innerHTML = "";
            hourly.slice(0, 6).forEach((hour) => {
                const card = document.createElement("div");
                card.className = "forecast-card";
                card.innerHTML = `
                    <h3>${escapeHtml(hour.hour || hour.time || "Now")}</h3>
                    <i class="fa-solid fa-clock fa-2x"></i>
                    <p>${escapeHtml(hour.temperature ?? "--")}&deg;C</p>
                    <p>${escapeHtml(hour.condition || "Unavailable")}</p>
                    <p>Rain ${escapeHtml(hour.rain_probability ?? 0)}%</p>
                `;
                hourlyHolder.appendChild(card);
            });
        };

        const updateAnalytics = (weather) => {
            if (analyticsSpans.length < 4) return;
            const aqiText = weather.air_quality ? .label || (weather.air_quality ? .aqi ? `AQI ${weather.air_quality.aqi}` : "Unavailable");
            const travelSafety = Math.round(Math.max(50, 100 - (weather.air_quality ? .aqi || 0) - (weather.rain_probability || 0) / 1.5));
            const travelScore = Math.max(4.5, Math.min(9.8, 10 - (weather.air_quality ? .aqi || 0) / 30 - (weather.rain_probability || 0) / 30)).toFixed(1);
            analyticsSpans[0].textContent = `${travelSafety}%`;
            analyticsSpans[1].textContent = "98%";
            analyticsSpans[2].textContent = aqiText;
            analyticsSpans[3].textContent = `${travelScore}`;
        };

        const refreshWeather = async() => {
            if (lastLatLon) {
                const { latitude, longitude } = lastLatLon;
                try {
                    showLoading("Refreshing live weather...");
                    const data = await api(`/api/weather?lat=${latitude}&lon=${longitude}`);
                    update(data.weather);
                } catch (error) {
                    displayError(error.message || "Unable to refresh weather.");
                }
                return;
            }
            if (lastWeatherQuery) {
                try {
                    showLoading("Refreshing search weather...");
                    const data = await api(`/api/weather?${lastWeatherQuery}`);
                    update(data.weather);
                } catch (error) {
                    displayError(error.message || "Unable to refresh weather.");
                }
            }
        };

        const update = (weather) => {
            const feels = weather.feels_like !== undefined && weather.feels_like !== null ? `Feels like ${weather.feels_like}&deg;C` : "";
            const uvIndex = weather.uv_index !== undefined && weather.uv_index !== null ? `UV ${weather.uv_index}` : "UV unavailable";
            const aqiLabel = weather.air_quality ? .label || "AQI unavailable";
            const sunrise = weather.sunrise ? `Sunrise ${weather.sunrise}` : "";
            const sunset = weather.sunset ? `Sunset ${weather.sunset}` : "";
            const rain = weather.rain_probability !== undefined ? `${weather.rain_probability}%` : "Unavailable";
            const conditionText = weather.condition || "Weather data unavailable";
            const recommendation = weather.recommendation || weather.recommendations ? .summary || "Weather looks suitable for sightseeing.";
            const safetyNote = weather.recommendations ? .traffic_note || "No major outdoor travel restrictions.";

            document.getElementById("temperature").innerHTML = `${weather.temperature ?? "--"}&deg;C`;
            document.getElementById("condition").innerHTML = `${escapeHtml(conditionText)}<br><small>${escapeHtml(feels)}</small>`;
            document.getElementById("humidity").innerHTML = `${weather.humidity ?? "--"}%<br><small>${escapeHtml(aqiLabel)} · ${escapeHtml(uvIndex)}</small>`;
            document.getElementById("wind").innerHTML = `${weather.wind ?? "--"} km/h<br><small>${escapeHtml(sunrise)} · ${escapeHtml(sunset)}</small>`;
            document.getElementById("locationName").innerHTML = escapeHtml(weather.location || "Unknown");
            document.getElementById("countryName").innerHTML = `${escapeHtml(weather.country || "")}<br><small>Rain ${escapeHtml(rain)} · ${escapeHtml(recommendation)}</small>`;
            updateAnalytics(weather);
            renderForecast(weather.daily || weather.forecast || [], weather.hourly || []);
            if (loading) {
                loading.textContent = `${safetyNote}`;
            }
        };

        window.getWeather = async function() {
            const city = cityInput.value.trim();
            const country = countryInput.value.trim();
            if (!city && !country) {
                alert("Please enter city name or select a country.");
                return;
            }
            const query = city ? `city=${encodeURIComponent(city)}` : `city=${encodeURIComponent(country)}`;
            const countryParam = city && country ? `&country=${encodeURIComponent(country)}` : "";
            lastWeatherQuery = `${query}${countryParam}`;
            lastLatLon = null;
            if (!refreshTimer) {
                refreshTimer = setInterval(refreshWeather, 10 * 60 * 1000);
            }
            showLoading("Fetching weather for your search...");
            try {
                const data = await api(`/api/weather?${query}${countryParam}`);
                update(data.weather);
            } catch (error) {
                displayError(error.message || "Unable to load weather data.");
            } finally {
                setTimeout(hideLoading, 1500);
            }
        };

        window.detectLocation = function(auto = false) {
            if (!navigator.geolocation) {
                if (auto) {
                    displayError("Location services are unavailable.");
                    return;
                }
                alert("Geolocation not supported.");
                return;
            }

            if (auto) {
                showLoading("Detecting your live location...");
            }

            navigator.geolocation.getCurrentPosition(
                async(position) => {
                    showLoading("Fetching live weather for your current location...");
                    const { latitude, longitude } = position.coords;
                    lastLatLon = { latitude, longitude };
                    lastWeatherQuery = null;
                    if (!refreshTimer) {
                        refreshTimer = setInterval(refreshWeather, 10 * 60 * 1000);
                    }
                    try {
                        const data = await api(`/api/weather?lat=${latitude}&lon=${longitude}`);
                        update(data.weather);
                    } catch (error) {
                        displayError(error.message || "Location weather fetch failed.");
                    }
                },
                (geoFail) => {
                    if (auto) {
                        displayError("Location permission denied. Search by city manually.");
                    } else {
                        alert("Unable to detect location.");
                    }
                }, { timeout: 15000 }
            );
        };

        if (!cityInput.value.trim()) {
            detectLocation(true);
        }
    }

    function setupEmergency() {
        const emergencyPage = document.querySelector(".quick-actions");
        if (!emergencyPage || !document.body.textContent.includes("Emergency")) return;

        const send = async(category, lat, lon) => {
            const payload = {
                category,
                latitude: lat,
                longitude: lon,
                location_text: lat && lon ? `${lat}, ${lon}` : "Location not shared"
            };
            const data = await api("/api/emergency", {
                method: "POST",
                headers: jsonHeaders,
                body: JSON.stringify(payload)
            });
            alert(`Emergency request ${data.request_id} logged. Status: ${data.status}`);
        };

        emergencyPage.addEventListener("click", (event) => {
            const button = event.target.closest("button");
            if (!button) return;
            const category = button.textContent.replace("Call ", "").trim();
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    (pos) => send(category, pos.coords.latitude, pos.coords.longitude),
                    () => send(category)
                );
            } else {
                send(category);
            }
        });

        const searchButton = document.querySelector(".search-grid button");
        if (searchButton) {
            searchButton.addEventListener("click", () => {
                const loadServices = (lat, lon) => {
                    const query = lat && lon ? `?lat=${lat}&lon=${lon}` : "";
                    api(`/api/nearby-services${query}`).then((data) => {
                        const counts = Object.entries(data.services).map(([key, items]) => `${key}: ${items.length}`).join(", ");
                        alert(`Nearby emergency services loaded. ${counts}. Helpline: ${data.helplines.universal}`);
                    }).catch((error) => alert(error.message));
                };
                if (navigator.geolocation) {
                    navigator.geolocation.getCurrentPosition(
                        (pos) => loadServices(pos.coords.latitude, pos.coords.longitude),
                        () => loadServices()
                    );
                } else {
                    loadServices();
                }
            });
        }
    }



    function setupBookings() {
        document.querySelectorAll(".quick-actions button").forEach((button) => {
            const text = button.textContent.trim().toLowerCase();
            if (text.includes("book hotels")) button.addEventListener("click", () => location.href = "/hotels");
            if (text.includes("reserve restaurants")) button.addEventListener("click", () => location.href = "/restaurants");
            if (text.includes("rent vehicles")) button.addEventListener("click", () => location.href = "/rentals");
            if (text.includes("travel planner")) button.addEventListener("click", () => location.href = "/tripplanner");
            if (text.includes("download tickets")) {
                button.addEventListener("click", async() => {
                    try {
                        const data = await api("/api/bookings");
                        const booking = data.bookings.find((item) => item.status !== "Cancelled") || data.bookings[0];
                        if (!booking) {
                            alert("No tickets available yet.");
                            return;
                        }
                        location.href = `/api/bookings/${booking.id}/ticket`;
                    } catch (error) {
                        alert(error.message);
                    }
                });
            }
        });
    }

    function setupSmartMap() {
        const mapEl = document.getElementById("map");
        const searchInput = document.getElementById("locationInput");
        if (!mapEl || !searchInput || !window.L) return;

        const map = window.nomadxMap;
        if (!map) return;

        L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
            attribution: "&copy; OpenStreetMap contributors &copy; CARTO",
            maxZoom: 19
        }).addTo(map);

        let routeLine = null;
        let userMarker = null;
        let destinationMarker = null;
        let locationWatchId = null;
        const nearbyLayers = [];

        const clearNearby = () => {
            while (nearbyLayers.length) {
                const layer = nearbyLayers.pop();
                map.removeLayer(layer);
            }
            if (routeLine) {
                map.removeLayer(routeLine);
                routeLine = null;
            }
        };

        const setInfo = (lat, lng, status) => {
            const latEl = document.getElementById("latitude");
            const lngEl = document.getElementById("longitude");
            const gpsEl = document.getElementById("gpsStatus");
            if (latEl) latEl.innerText = Number(lat).toFixed(5);
            if (lngEl) lngEl.innerText = Number(lng).toFixed(5);
            if (gpsEl) gpsEl.innerText = status;
        };

        const popupHtml = (place) => {
            const details = place.details || {};
            const lines = [
                `<strong>${escapeHtml(place.name)}</strong>`,
                `${escapeHtml(place.type || "place")} | ${escapeHtml(place.distance_km ?? "--")} km | ${escapeHtml(place.eta_min ?? "--")} min`,
                details.address ? escapeHtml(details.address) : "",
                details.pickup_address ? `Pickup: ${escapeHtml(details.pickup_address)}` : "",
                details.owner_name ? `Owner: ${escapeHtml(details.owner_name)}` : "",
                details.phone ? `Phone: ${escapeHtml(details.phone)}` : "",
                details.availability ? escapeHtml(details.availability) : "",
                details.price_per_day ? escapeHtml(details.price_per_day) : "",
                details.price ? escapeHtml(details.price) : ""
            ].filter(Boolean);
            return lines.join("<br>");
        };

        const saveLiveLocation = (coords) => api("/live_location", {
            method: "POST",
            headers: jsonHeaders,
            body: JSON.stringify({
                latitude: coords.latitude,
                longitude: coords.longitude,
                accuracy: coords.accuracy,
                heading: coords.heading,
                speed: coords.speed
            })
        }).catch(() => {});

        const updateUserLocation = async(position, recenter = false) => {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;
            window.nomadxCurrentLocation = { lat, lng };
            setInfo(lat, lng, "GPS Live");
            saveLiveLocation(position.coords);

            if (userMarker) {
                userMarker.setLatLng([lat, lng]);
            } else {
                userMarker = L.marker([lat, lng]).addTo(map).bindPopup("You are here");
                userMarker.openPopup();
            }

            if (recenter) {
                map.setView([lat, lng], 14);
                await showSmartNearby(lat, lng);
            }
        };

        const addNearbyMarkers = async(lat, lng, type) => {
            const data = await api(`/nearby_places?lat=${lat}&lon=${lng}&type=${encodeURIComponent(type)}`);
            data.places.forEach((place) => {
                const layer = L.marker([place.lat, place.lon])
                    .addTo(map)
                    .bindPopup(popupHtml(place));
                layer.on("click", async() => {
                    if (!window.nomadxCurrentLocation) return;
                    const route = await api(`/route_navigation?start_lat=${window.nomadxCurrentLocation.lat}&start_lon=${window.nomadxCurrentLocation.lng}&end_lat=${place.lat}&end_lon=${place.lon}`);
                    if (routeLine) map.removeLayer(routeLine);
                    routeLine = L.polyline(route.route.points, { color: "#61A5C2", weight: 5, opacity: 0.92 }).addTo(map);
                    routeLine.bindPopup(`Distance: ${route.route.distance_km} km<br>ETA: ${route.route.eta_min} min<br>${escapeHtml(route.route.mode)}`).openPopup();
                });
                nearbyLayers.push(layer);
            });
            return data.places;
        };

        const showSmartNearby = async(lat, lng) => {
            clearNearby();
            const types = ["hotels", "restaurants", "hospitals", "police", "attractions", "rentals", "fuel"];
            for (const type of types) {
                await addNearbyMarkers(lat, lng, type);
            }
        };

        window.detectLocation = function() {
            if (!navigator.geolocation) {
                alert("Geolocation not supported.");
                return;
            }

            if (locationWatchId !== null) {
                navigator.geolocation.clearWatch(locationWatchId);
            }

            navigator.geolocation.getCurrentPosition(
                (position) => updateUserLocation(position, true).catch((error) => console.warn(error.message)),
                () => alert("Unable to access location."), { enableHighAccuracy: true, timeout: 12000, maximumAge: 5000 }
            );

            locationWatchId = navigator.geolocation.watchPosition(
                (position) => updateUserLocation(position, false).catch((error) => console.warn(error.message)),
                () => setInfo(window.nomadxCurrentLocation ? .lat || 0, window.nomadxCurrentLocation ? .lng || 0, "GPS Signal Waiting"), { enableHighAccuracy: true, maximumAge: 3000, timeout: 15000 }
            );
        };

        window.searchLocation = async function() {
            const location = searchInput.value.trim();
            if (!location) {
                alert("Please enter location");
                return;
            }

            try {
                const data = await api(`/search_location?q=${encodeURIComponent(location)}`);
                if (!data.places.length) {
                    alert("Location not found.");
                    return;
                }
                clearNearby();
                const place = data.places[0];
                const lat = Number(place.lat);
                const lon = Number(place.lon);
                window.nomadxDestination = { lat, lng: lon, name: place.display_name };
                map.setView([lat, lon], 13);
                setInfo(lat, lon, "Location Found");
                if (destinationMarker) {
                    destinationMarker.setLatLng([lat, lon]).setPopupContent(escapeHtml(place.display_name)).openPopup();
                } else {
                    destinationMarker = L.marker([lat, lon]).addTo(map).bindPopup(escapeHtml(place.display_name)).openPopup();
                }
                await showSmartNearby(lat, lon);

                if (window.nomadxCurrentLocation) {
                    const route = await api(`/route_navigation?start_lat=${window.nomadxCurrentLocation.lat}&start_lon=${window.nomadxCurrentLocation.lng}&end_lat=${lat}&end_lon=${lon}`);
                    routeLine = L.polyline(route.route.points, { color: "#61A5C2", weight: 5, opacity: 0.92 }).addTo(map);
                    routeLine.bindPopup(`Distance: ${route.route.distance_km} km<br>ETA: ${route.route.eta_min} min<br>${escapeHtml(route.route.mode)}`).openPopup();
                }
            } catch (error) {
                alert(error.message);
            }
        };

        searchInput.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
                event.preventDefault();
                window.searchLocation();
            }
        });

        document.querySelectorAll(".feature-card").forEach((card) => {
            card.addEventListener("click", async() => {
                const current = window.nomadxCurrentLocation || window.nomadxDestination || { lat: 20.5937, lng: 78.9629 };
                const text = card.textContent.toLowerCase();
                const type = text.includes("hotel") ? "hotels" : text.includes("restaurant") ? "restaurants" : text.includes("route") ? "attractions" : "places";
                clearNearby();
                await addNearbyMarkers(current.lat, current.lng, type);
                map.setView([current.lat, current.lng], 14);
            });
        });
    }

    document.addEventListener("DOMContentLoaded", () => {
        setupChatbot();
        setupHotels();
        setupRestaurants();
        setupRentals();
        setupTripPlanner();
        setupWeather();
        setupEmergency();

        setupBookings();
        setupSmartMap();
    });
})(); // Example fetch calls to replace localStorage:
async function loadProfile() {
    const response = await fetch('/api/profile');
    const data = await response.json();
    userProfile = data;
    updateProfileUI();
}

async function saveProfile() {
    await fetch('/api/profile/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(userProfile)
    });
}

async function saveSettings() {
    await fetch('/api/settings/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(userSettings)
    });
}