const state = {
  map: null,
  markers: [],
  accessToken: null,
  user: null,
  center: { latitude: 37.5665, longitude: 126.978 },
};

const MAP_CONTAINER_ID = "map";
const PLACES_ENDPOINT = "/api/places/nearby";
const MAPS_CONFIG_ENDPOINT = "/api/config/maps";
const LOGIN_ENDPOINT = "/api/auth/login";
const SIGNUP_ENDPOINT = "/api/auth/signup";
const REFRESH_ENDPOINT = "/api/auth/refresh";
const LOGOUT_ENDPOINT = "/api/auth/logout";

const mapStatusEl = document.getElementById("map-status");

function setStatus(message, type = "info") {
  if (!mapStatusEl) return;
  mapStatusEl.innerText = message;
  mapStatusEl.dataset.type = type;
}

async function fetchJSON(url, options = {}) {
  const method = (options.method || "GET").toUpperCase();
  const headers = {
    ...(options.headers || {}),
  };
  if (method !== "GET" && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  if (state.accessToken) {
    headers["Authorization"] = `Bearer ${state.accessToken}`;
  }

  const response = await fetch(url, {
    headers,
    credentials: "include",
    ...options,
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail || `요청 실패 (${response.status})`);
  }
  return response.json();
}

async function loadKakaoMapsSdk(appKey) {
  if (!appKey) {
    throw new Error("카카오맵 App Key가 설정되어 있지 않습니다 (.env의 KAKAO_MAP_APP_KEY).");
  }

  if (window.kakao && window.kakao.maps) {
    return window.kakao.maps;
  }

  await new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = `https://dapi.kakao.com/v2/maps/sdk.js?autoload=false&appkey=${appKey}`;
    script.async = true;
    script.onload = resolve;
    script.onerror = () => reject(new Error("카카오맵 SDK 로드에 실패했습니다."));
    document.head.appendChild(script);
  });

  return new Promise((resolve) => {
    window.kakao.maps.load(() => resolve(window.kakao.maps));
  });
}

function buildLatLng({ latitude, longitude }) {
  return new window.kakao.maps.LatLng(latitude, longitude);
}

function clearMarkers() {
  state.markers.forEach((marker) => marker.setMap(null));
  state.markers = [];
}

function renderPlaces(places) {
  const panel = document.getElementById("personalized-panel");
  if (!panel) return;

  if (!state.user) {
    panel.innerHTML = '<p class="placeholder">로그인 후 이용가능한 기능입니다.</p>';
    return;
  }

  panel.innerHTML = "";
  places.forEach((place) => {
    const template = document.getElementById("place-template");
    if (!template) return;
    const clone = template.content.cloneNode(true);
    clone.querySelector('[data-field="name"]').innerText = place.name;
    clone.querySelector('[data-field="description"]').innerText = place.description || "-";
    clone.querySelector('[data-field="tags"]').innerText = place.tags?.join(", ") || "";
    panel.appendChild(clone);
  });
}

function addMarkers(places) {
  if (!state.map) return;
  clearMarkers();

  places.forEach((place) => {
    const markerPosition = buildLatLng(place.coordinates);
    const marker = new window.kakao.maps.Marker({ position: markerPosition });
    marker.setMap(state.map);
    state.markers.push(marker);
  });
}

async function loadPlaces() {
  try {
    setStatus("주변 장소를 불러오는 중...");
    const params = new URLSearchParams({
      latitude: state.center.latitude,
      longitude: state.center.longitude,
      limit: "6",
    });
    if (state.user?.preferences?.length) {
      state.user.preferences.forEach((tag) => params.append("tags", tag));
    }
    const data = await fetchJSON(`${PLACES_ENDPOINT}?${params.toString()}`, {
      method: "GET",
    });
    addMarkers(data);
    renderPlaces(data);
    setStatus(`추천 장소 ${data.length}개를 불러왔습니다.`);
  } catch (error) {
    console.error(error);
    setStatus(error.message, "error");
  }
}

function updateAuthUi() {
  const loginForm = document.getElementById("login-form");
  if (!loginForm) return;

  const banner = loginForm.querySelector(".auth-banner");
  if (banner) banner.remove();

  if (state.user) {
    const info = document.createElement("div");
    info.className = "auth-banner";
    info.innerHTML = `👋 ${state.user.nickname}님 환영합니다! <button type="button" id="logout-btn">로그아웃</button>`;
    loginForm.prepend(info);

    const logoutBtn = info.querySelector("#logout-btn");
    logoutBtn?.addEventListener("click", async () => {
      try {
        await fetchJSON(LOGOUT_ENDPOINT, { method: "POST" });
        state.user = null;
        state.accessToken = null;
        updateAuthUi();
        renderPlaces([]);
        clearMarkers();
        setStatus("로그아웃되었습니다.");
      } catch (error) {
        setStatus(error.message, "error");
      }
    });
  }
}

async function handleSignup(event) {
  event.preventDefault();
  const formData = new FormData(event.target);
  const payload = Object.fromEntries(formData.entries());
  try {
    await fetchJSON(SIGNUP_ENDPOINT, {
      method: "POST",
      body: JSON.stringify({
        email: payload.email,
        nickname: payload.nickname,
        password: payload.password,
      }),
    });
    event.target.reset();
    setStatus("회원가입이 완료되었습니다. 로그인해 주세요.");
  } catch (error) {
    setStatus(error.message, "error");
  }
}

async function handleLogin(event) {
  event.preventDefault();
  const formData = new FormData(event.target);
  const payload = Object.fromEntries(formData.entries());
  try {
    const data = await fetchJSON(LOGIN_ENDPOINT, {
      method: "POST",
      body: JSON.stringify({
        email: payload.email,
        password: payload.password,
      }),
    });
    state.accessToken = data.access_token;
    state.user = data.user;
    setStatus("로그인 성공! 추천을 받아보세요.");
    updateAuthUi();
    await loadPlaces();
  } catch (error) {
    setStatus(error.message, "error");
  }
}

function initAuthListeners() {
  const loginForm = document.getElementById("login-form");
  const signupForm = document.getElementById("signup-form");
  loginForm?.addEventListener("submit", handleLogin);
  signupForm?.addEventListener("submit", handleSignup);
}

async function initMap() {
  try {
    setStatus("지도 초기화 중...");
    const { kakaoMapAppKey } = await fetchJSON(MAPS_CONFIG_ENDPOINT, { method: "GET" });
    const kakaoMaps = await loadKakaoMapsSdk(kakaoMapAppKey);
    const container = document.getElementById(MAP_CONTAINER_ID);
    if (!container) throw new Error("지도 컨테이너를 찾을 수 없습니다.");

    const options = {
      center: new kakaoMaps.LatLng(state.center.latitude, state.center.longitude),
      level: 5,
    };
    state.map = new kakaoMaps.Map(container, options);
    setStatus("지도 로드 완료.");
  } catch (error) {
    console.error(error);
    setStatus(error.message, "error");
  }
}

function attachControls() {
  document.getElementById("locate-me")?.addEventListener("click", () => {
    if (!navigator.geolocation) {
      setStatus("브라우저가 위치 정보를 지원하지 않습니다.", "error");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        state.center = {
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
        };
        if (state.map) {
          state.map.setCenter(buildLatLng(state.center));
        }
        setStatus("현재 위치로 이동했습니다.");
      },
      () => setStatus("위치 정보를 가져올 수 없습니다.", "error"),
    );
  });

  document.getElementById("load-places")?.addEventListener("click", async () => {
    if (!state.user) {
      setStatus("로그인 후 이용해주세요.", "error");
      return;
    }
    await loadPlaces();
  });
}

async function bootstrap() {
  initAuthListeners();
  attachControls();
  await initMap();
}

document.addEventListener("DOMContentLoaded", bootstrap);
