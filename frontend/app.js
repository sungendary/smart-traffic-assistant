const state = {
  map: null,
  markers: [],
  center: { latitude: 37.5665, longitude: 126.9780 },
  accessToken: null,
  user: null,
  couple: null,
  plans: [],
  bookmarks: [],
  visits: [],
  report: null,
  mapSuggestions: [],
  llmSuggestions: [],
  isRightOpen: true,
  currentView: "map",
};

function handleLogout() {
  fetchJSON(`${AUTH_ENDPOINT}/logout`, { method: "POST" }).finally(() => {
    state.accessToken = null;
    state.user = null;
    state.couple = null;
    state.plans = [];
    state.bookmarks = [];
    state.visits = [];
    state.report = null;
    state.mapSuggestions = [];
    state.llmSuggestions = [];
    persistSession();
    renderApp();
    setStatus("로그아웃되었습니다.");
  });
}

const MAPS_CONFIG_ENDPOINT = "/api/config/maps";
const AUTH_ENDPOINT = "/api/auth";

function select(selector) {
  return document.querySelector(selector);
}

function selectAll(selector) {
  return Array.from(document.querySelectorAll(selector));
}

function setStatus(message, type = "info") {
  const overlay = select("#map-overlay");
  if (!overlay) return;
  overlay.textContent = message;
  overlay.dataset.type = type;
  overlay.classList.toggle("hidden", !message);
}

async function fetchJSON(url, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.accessToken) {
    headers["Authorization"] = `Bearer ${state.accessToken}`;
  }
  const response = await fetch(url, {
    credentials: "include",
    ...options,
    headers,
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail || `요청 실패 (${response.status})`);
  }
  return response.json();
}

async function loadKakaoMapsSdk(appKey) {
  if (!appKey) throw new Error("Kakao App Key가 필요합니다.");
  if (window.kakao && window.kakao.maps) return window.kakao.maps;
  await new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = `https://dapi.kakao.com/v2/maps/sdk.js?autoload=false&appkey=${appKey}`;
    script.async = true;
    script.onload = resolve;
    script.onerror = () => reject(new Error("카카오맵 SDK 로드 실패"));
    document.head.appendChild(script);
  });
  return new Promise((resolve) => {
    window.kakao.maps.load(() => resolve(window.kakao.maps));
  });
}

function clearMarkers() {
  state.markers.forEach((m) => m.setMap(null));
  state.markers = [];
}

function addMarkers(places) {
  if (!state.map) return;
  clearMarkers();
  places.forEach((place) => {
    const { latitude, longitude } = place.coordinates;
    const latlng = new window.kakao.maps.LatLng(latitude, longitude);
    const marker = new window.kakao.maps.Marker({ position: latlng });
    marker.setMap(state.map);
    state.markers.push(marker);
  });
}

async function initMap() {
  try {
    setStatus("지도 초기화 중...");
    const { kakaoMapAppKey } = await fetchJSON(MAPS_CONFIG_ENDPOINT);
    const kakaoMaps = await loadKakaoMapsSdk(kakaoMapAppKey);
    const container = select("#map");
    if (!container) throw new Error("지도 컨테이너를 찾을 수 없습니다.");
    const options = {
      center: new kakaoMaps.LatLng(state.center.latitude, state.center.longitude),
      level: 6,
    };
    state.map = new kakaoMaps.Map(container, options);
    setStatus("");
  } catch (error) {
    console.error(error);
    setStatus(error.message, "error");
  }
}

function updateNav() {
  selectAll(".nav-btn").forEach((btn) => {
    const view = btn.dataset.view;
    btn.classList.toggle("active", view === state.currentView);
  });
}

function renderRightPanel() {
  const sidebar = select("#right-sidebar");
  if (!sidebar) return;
  sidebar.classList.toggle("open", state.isRightOpen);
  const container = select("#right-content");
  container.innerHTML = "";

  if (!state.isRightOpen) {
    return;
  }

  if (state.currentView === "map") {
    if (!state.user) {
      container.innerHTML = `<div class="card"><h2 class="section-title">맞춤 추천</h2><p class="section-caption">로그인 후 AI 맞춤 제안을 확인하세요.</p></div>`;
      return;
    }
    const wrapper = document.createElement("div");
    wrapper.className = "stack";
    if (!state.llmSuggestions.length) {
      wrapper.innerHTML = `<div class="card"><h2 class="section-title">맞춤 추천</h2><p class="section-caption">필터를 설정하고 "추천 받기"를 눌러보세요.</p></div>`;
    } else {
      wrapper.innerHTML = `<div class="card"><h2 class="section-title">AI 추천 코스</h2><p class="section-caption">현재 감정과 선호를 반영한 제안입니다.</p></div>`;
      const template = select("#suggestion-template");
      state.llmSuggestions.forEach((item) => {
        const node = template.content.cloneNode(true);
        node.querySelector('[data-field="title"]').textContent = item.title;
        node.querySelector('[data-field="description"]').textContent = item.description;
        const placesList = node.querySelector('[data-field="places"]');
        item.suggested_places.forEach((text) => {
          const li = document.createElement("li");
          li.textContent = text;
          placesList.appendChild(li);
        });
        const tipsList = node.querySelector('[data-field="tips"]');
        item.tips.slice(0, 2).forEach((tip) => {
          const li = document.createElement("li");
          li.textContent = tip;
          tipsList.appendChild(li);
        });
        wrapper.appendChild(node);
      });
    }
    container.appendChild(wrapper);
    return;
  }

  if (state.currentView === "planner") {
    const wrap = document.createElement("div");
    wrap.className = "stack";
    const visitsCard = document.createElement("div");
    visitsCard.className = "card";
    visitsCard.innerHTML = `<h2 class="section-title">최근 방문 기록</h2>`;
    if (!state.visits.length) {
      visitsCard.innerHTML += `<p class="section-caption">아직 방문 기록이 없습니다. 체크인을 시작해보세요.</p>`;
    } else {
      const list = document.createElement("ul");
      list.className = "tip-list";
      state.visits.slice(0, 5).forEach((visit) => {
        const li = document.createElement("li");
        li.textContent = `${visit.place_name || visit.place_id} · ${visit.emotion || "감정 미입력"}`;
        list.appendChild(li);
      });
      visitsCard.appendChild(list);
    }
    wrap.appendChild(visitsCard);
    container.appendChild(wrap);
    return;
  }

  if (state.currentView === "couple") {
    const card = document.createElement("div");
    card.className = "card";
    const members = state.couple?.members || [];
    card.innerHTML = `
      <h2 class="section-title">커플 구성원</h2>
      <div class="inline-chips">
        ${members.map((m) => `<span class="inline-chip">${m.nickname} (${m.email})</span>`).join("")}
      </div>
    `;
    container.appendChild(card);
    return;
  }

  if (state.currentView === "reports" && state.report) {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <h2 class="section-title">감정 통계</h2>
      <ul class="tip-list">
        ${Object.entries(state.report.emotion_stats)
          .map(([emotion, count]) => `<li>${emotion}: ${count}회</li>`)
          .join("")}
      </ul>
      <h2 class="section-title">챌린지 진행</h2>
      <ul class="tip-list">
        ${state.report.challenge_progress
          .map((c) => `<li>${c.badge_icon} ${c.title} (${c.current}/${c.goal})</li>`)
          .join("")}
      </ul>
    `;
    container.appendChild(card);
  }
}

function renderMapView() {
  const sidebar = select("#left-sidebar");
  sidebar.innerHTML = "";

  if (!state.user) {
    const loginCard = document.createElement("div");
    loginCard.className = "card";
    loginCard.innerHTML = `
      <h2 class="section-title">로그인</h2>
      <form id="login-form" class="stack">
        <input type="email" name="email" placeholder="이메일" required />
        <input type="password" name="password" placeholder="비밀번호" required />
        <button type="submit" class="primary-btn">로그인</button>
      </form>
    `;

    const signupCard = document.createElement("div");
    signupCard.className = "card";
    signupCard.innerHTML = `
      <h2 class="section-title">회원가입</h2>
      <form id="signup-form" class="stack">
        <input type="email" name="email" placeholder="이메일" required />
        <input type="text" name="nickname" placeholder="닉네임" required />
        <input type="password" name="password" placeholder="비밀번호" required />
        <button type="submit" class="primary-outline">가입하기</button>
      </form>
    `;

    sidebar.appendChild(loginCard);
    sidebar.appendChild(signupCard);
    attachAuthListeners();
    return;
  }

  const formCard = document.createElement("div");
  formCard.className = "card";
  formCard.innerHTML = `
    <h2 class="section-title">데이트 추천 필터</h2>
    <form id="suggest-form" class="stack">
      <input type="text" name="location_text" placeholder="지역 설명 (예: 서울 종로구)" value="서울" required />
      <select name="emotion">
        <option value="설렘">설렘</option>
        <option value="힐링">힐링</option>
        <option value="편안함">편안함</option>
        <option value="위로">위로</option>
        <option value="즐거움">즐거움</option>
      </select>
      <input type="text" name="preferences" placeholder="선호 태그를 쉼표로 입력 (예: 카페, 야경)" />
      <textarea name="additional_context" rows="3" placeholder="추가 요청 사항 (선택)"></textarea>
      <button type="submit" class="primary-btn">추천 받기</button>
    </form>
  `;

  const resultCard = document.createElement("div");
  resultCard.className = "card";
  if (!state.mapSuggestions.length) {
    resultCard.innerHTML = `<h2 class="section-title">추천 장소</h2><p class="section-caption">추천 결과가 여기에 표시됩니다.</p>`;
  } else {
    resultCard.innerHTML = `<h2 class="section-title">추천 장소 (${state.mapSuggestions.length})</h2>`;
    const list = document.createElement("div");
    list.className = "stack";
    state.mapSuggestions.forEach((place) => {
      const card = document.createElement("div");
      card.className = "card sub";
      card.innerHTML = `
        <header class="card-header">
          <div>
            <h3 class="card-title">${place.name}</h3>
            <p class="subtext">${place.description || "설명이 없습니다."}</p>
          </div>
          <button class="primary-outline" data-action="bookmark" data-place='${JSON.stringify(place)}'>북마크</button>
        </header>
        <div class="pill-list">${place.tags.map((tag) => `<span class="inline-chip">${tag}</span>`).join("")}</div>
      `;
      list.appendChild(card);
    });
    resultCard.appendChild(list);
  }

  sidebar.appendChild(formCard);
  sidebar.appendChild(resultCard);

  select("#suggest-form").addEventListener("submit", handleSuggestForm);
  selectAll('[data-action="bookmark"]').forEach((btn) =>
    btn.addEventListener("click", () => handleBookmark(JSON.parse(btn.dataset.place)))
  );
}

function renderPlannerView() {
  const sidebar = select("#left-sidebar");
  sidebar.innerHTML = "";

  if (!state.user) {
    sidebar.innerHTML = `<div class="card"><h2 class="section-title">로그인 필요</h2><p class="section-caption">플래너 기능은 로그인 후 이용할 수 있습니다.</p></div>`;
    return;
  }

  const formCard = document.createElement("div");
  formCard.className = "card";
  formCard.innerHTML = `
    <h2 class="section-title">새 플랜 만들기</h2>
    <form id="plan-form" class="stack">
      <input type="text" name="title" placeholder="코스 제목" required />
      <input type="date" name="date" />
      <input type="text" name="emotion_goal" placeholder="감정 목표 (예: 힐링)" />
      <input type="text" name="budget_range" placeholder="예산 범위 (예: 중간)" />
      <textarea name="stops" rows="4" placeholder="장소ID:설명 형식으로 줄바꿈하여 입력"></textarea>
      <button type="submit" class="primary-btn">플랜 저장</button>
    </form>
  `;

  const listWrap = document.createElement("div");
  listWrap.className = "stack";
  if (!state.plans.length) {
    listWrap.innerHTML = `<div class="card"><h2 class="section-title">저장된 플랜</h2><p class="section-caption">플랜이 없습니다.</p></div>`;
  } else {
    const template = select("#plan-card-template");
    state.plans.forEach((plan) => {
      const node = template.content.cloneNode(true);
      node.querySelector("[data-field=\"title\"]").textContent = plan.title;
      node.querySelector("[data-field=\"meta\"]").textContent = `${plan.date || "미정"} · ${plan.emotion_goal || "감정 미정"}`;
      const stops = node.querySelector("[data-field=\"stops\"]");
      if (!plan.stops?.length) {
        const li = document.createElement("li");
        li.textContent = "저장된 경유지가 없습니다.";
        stops.appendChild(li);
      } else {
        plan.stops.forEach((stop) => {
          const li = document.createElement("li");
          li.textContent = `${stop.order}. ${stop.place_name || stop.place_id} ${stop.note ? `- ${stop.note}` : ""}`;
          stops.appendChild(li);
        });
      }
      const actions = node.querySelector("[data-field=\"actions\"]");
      const delBtn = document.createElement("button");
      delBtn.textContent = "삭제";
      delBtn.addEventListener("click", () => deletePlan(plan.id));
      actions.appendChild(delBtn);
      listWrap.appendChild(node);
    });
  }

  sidebar.appendChild(formCard);
  sidebar.appendChild(listWrap);
  select("#plan-form").addEventListener("submit", handlePlanForm);
}

function renderCoupleView() {
  const sidebar = select("#left-sidebar");
  sidebar.innerHTML = "";

  if (!state.user) {
    sidebar.innerHTML = `<div class="card"><h2 class="section-title">로그인 필요</h2><p class="section-caption">커플 설정은 로그인 후 이용할 수 있습니다.</p></div>`;
    return;
  }

  const couple = state.couple;
  const inviteCard = document.createElement("div");
  inviteCard.className = "card";
  inviteCard.innerHTML = `
    <h2 class="section-title">초대 코드</h2>
    <p class="section-caption">파트너가 입력할 초대 코드입니다.</p>
    <div class="inline-chips"><span class="inline-chip">${couple?.invite_code || "생성 중"}</span></div>
    <button id="regen-code" class="primary-outline">새 코드 생성</button>
  `;

  const joinCard = document.createElement("div");
  joinCard.className = "card";
  joinCard.innerHTML = `
    <h2 class="section-title">코드로 합류</h2>
    <form id="join-form" class="stack">
      <input type="text" name="code" placeholder="6자리 코드" maxlength="6" required />
      <button type="submit" class="primary-btn">합류하기</button>
    </form>
  `;

  const prefCard = document.createElement("div");
  prefCard.className = "card";
  const prefs = couple?.preferences || { tags: [], emotion_goals: [], budget: "medium" };
  prefCard.innerHTML = `
    <h2 class="section-title">커플 선호</h2>
    <form id="pref-form" class="stack">
      <input type="text" name="tags" placeholder="선호 태그 (쉼표로 구분)" value="${prefs.tags.join(", ")}" />
      <input type="text" name="emotion_goals" placeholder="감정 목표" value="${prefs.emotion_goals.join(", ")}" />
      <input type="text" name="budget" placeholder="예산" value="${prefs.budget}" />
      <button type="submit" class="primary-outline">저장</button>
    </form>
  `;

  sidebar.appendChild(inviteCard);
  sidebar.appendChild(joinCard);
  sidebar.appendChild(prefCard);

  select("#regen-code").addEventListener("click", regenerateInviteCode);
  select("#join-form").addEventListener("submit", handleJoinCouple);
  select("#pref-form").addEventListener("submit", handlePreferenceUpdate);
}

function renderReportsView() {
  const sidebar = select("#left-sidebar");
  sidebar.innerHTML = "";

  if (!state.user) {
    sidebar.innerHTML = `<div class="card"><h2 class="section-title">로그인 필요</h2><p class="section-caption">리포트 기능은 로그인 후 이용할 수 있습니다.</p></div>`;
    return;
  }

  const card = document.createElement("div");
  card.className = "card";
  const month = state.report?.month || new Date().toISOString().slice(0, 7);
  card.innerHTML = `
    <h2 class="section-title">월간 리포트</h2>
    <form id="report-form" class="stack">
      <input type="month" name="month" value="${month}" />
      <button type="submit" class="primary-btn">리포트 확인</button>
    </form>
    <div class="card" id="report-summary">
      ${state.report ? `<p class="card-desc">${state.report.summary}</p>` : '<p class="section-caption">리포트를 불러오세요.</p>'}
    </div>
  `;
  sidebar.appendChild(card);
  select("#report-form").addEventListener("submit", handleReportForm);
}

function renderLeftSidebar() {
  if (state.currentView === "map") {
    renderMapView();
  } else if (state.currentView === "planner") {
    renderPlannerView();
  } else if (state.currentView === "couple") {
    renderCoupleView();
  } else if (state.currentView === "reports") {
    renderReportsView();
  }
}

function renderApp() {
  updateNav();
  renderLeftSidebar();
  renderRightPanel();
  const label = select("#user-label");
  if (label) {
    label.textContent = state.user ? `${state.user.nickname}님` : "로그인 필요";
  }
  const logoutBtn = select("#logout-btn");
  if (logoutBtn) {
    if (state.user) {
      logoutBtn.classList.remove("hidden");
      if (!logoutBtn.dataset.bound) {
        logoutBtn.addEventListener("click", handleLogout);
        logoutBtn.dataset.bound = "true";
      }
    } else {
      logoutBtn.classList.add("hidden");
    }
  }
}

function switchView(view) {
  state.currentView = view;
  renderApp();
}

function attachNavListeners() {
  selectAll(".nav-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const view = btn.dataset.view;
      switchView(view);
    });
  });
  select("#toggle-right").addEventListener("click", () => {
    state.isRightOpen = !state.isRightOpen;
    renderRightPanel();
  });
}

function attachAuthListeners() {
  const loginForm = select("#login-form");
  const signupForm = select("#signup-form");
  loginForm?.addEventListener("submit", handleLogin);
  signupForm?.addEventListener("submit", handleSignup);
}

async function handleSignup(event) {
  event.preventDefault();
  const form = event.target;
  const payload = Object.fromEntries(new FormData(form).entries());
  try {
    await fetchJSON(`${AUTH_ENDPOINT}/signup`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    alert("회원가입이 완료되었습니다. 로그인해 주세요.");
    form.reset();
  } catch (error) {
    alert(error.message);
  }
}

async function handleLogin(event) {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(event.target).entries());
  try {
    const data = await fetchJSON(`${AUTH_ENDPOINT}/login`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.accessToken = data.access_token;
    state.user = data.user;
    persistSession();
    await loadInitialData();
    renderApp();
    setStatus("로그인 성공!");
  } catch (error) {
    alert(error.message);
  }
}

async function handleSuggestForm(event) {
  event.preventDefault();
  if (!state.user) {
    alert("로그인이 필요합니다.");
    return;
  }
  const formData = new FormData(event.target);
  const preferences = formData.get("preferences")
    ? formData.get("preferences").split(",").map((t) => t.trim()).filter(Boolean)
    : [];
  const payload = {
    latitude: state.center.latitude,
    longitude: state.center.longitude,
    location_text: formData.get("location_text"),
    emotion: formData.get("emotion"),
    preferences,
    additional_context: formData.get("additional_context") || "",
  };
  try {
    setStatus("맞춤 추천 생성 중...");
    const data = await fetchJSON("/api/map/suggestions", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.mapSuggestions = data.places;
    state.llmSuggestions = data.llm_suggestions;
    addMarkers(data.places);
    setStatus(data.summary, "success");
    renderApp();
  } catch (error) {
    console.error(error);
    setStatus(error.message, "error");
  }
}

async function handleBookmark(place) {
  try {
    await fetchJSON("/api/bookmarks/", {
      method: "POST",
      body: JSON.stringify({
        place_id: place.id,
        place_name: place.name,
        address: place.description,
        tags: place.tags,
      }),
    });
    alert("북마크에 추가되었습니다.");
    await loadBookmarks();
    renderRightPanel();
  } catch (error) {
    alert(error.message);
  }
}

function parseStops(raw) {
  if (!raw.trim()) return [];
  return raw.split(/\n+/).map((line, index) => {
    const [place_id, note] = line.split(":");
    return {
      place_id: place_id.trim(),
      place_name: note ? note.trim() : undefined,
      note: note ? note.trim() : undefined,
      order: index + 1,
    };
  });
}

async function handlePlanForm(event) {
  event.preventDefault();
  const form = event.target;
  const formData = new FormData(form);
  const payload = {
    title: formData.get("title"),
    date: formData.get("date") || null,
    emotion_goal: formData.get("emotion_goal") || null,
    budget_range: formData.get("budget_range") || null,
    stops: parseStops(formData.get("stops") || ""),
  };
  try {
    await fetchJSON("/api/planner/plans", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    form.reset();
    await loadPlans();
    renderApp();
  } catch (error) {
    alert(error.message);
  }
}

async function deletePlan(planId) {
  if (!confirm("플랜을 삭제할까요?")) return;
  try {
    await fetchJSON(`/api/planner/plans/${planId}`, { method: "DELETE" });
    await loadPlans();
    renderApp();
  } catch (error) {
    alert(error.message);
  }
}

async function regenerateInviteCode() {
  try {
    const data = await fetchJSON("/api/couples/invite", { method: "POST" });
    state.couple.invite_code = data.invite_code;
    renderApp();
  } catch (error) {
    alert(error.message);
  }
}

async function handleJoinCouple(event) {
  event.preventDefault();
  const formData = new FormData(event.target);
  const code = formData.get("code").toUpperCase();
  try {
    const data = await fetchJSON("/api/couples/join", {
      method: "POST",
      body: JSON.stringify({ code }),
    });
    state.couple = data;
    await loadInitialData();
    renderApp();
    alert("커플 연결이 완료되었습니다.");
  } catch (error) {
    alert(error.message);
  }
}

async function handlePreferenceUpdate(event) {
  event.preventDefault();
  const formData = new FormData(event.target);
  const payload = {
    tags: (formData.get("tags") || "")
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean),
    emotion_goals: (formData.get("emotion_goals") || "")
      .split(",")
      .map((e) => e.trim())
      .filter(Boolean),
    budget: formData.get("budget") || "medium",
  };
  try {
    const data = await fetchJSON("/api/couples/preferences", {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    state.couple = data;
    renderApp();
    alert("선호 설정이 업데이트되었습니다.");
  } catch (error) {
    alert(error.message);
  }
}

async function handleReportForm(event) {
  event.preventDefault();
  const month = new FormData(event.target).get("month") || new Date().toISOString().slice(0, 7);
  try {
    const data = await fetchJSON(`/api/reports/monthly?month=${month}`);
    state.report = data;
    renderApp();
  } catch (error) {
    alert(error.message);
  }
}

async function loadCouple() {
  const data = await fetchJSON("/api/couples/me");
  state.couple = data;
  if (data.members?.length) {
    const matched = state.user
      ? data.members.find((member) => member.id === state.user.id || member.email === state.user.email)
      : data.members[0];
    if (matched) {
      state.user = matched;
      persistSession();
    }
  }
}

async function loadPlans() {
  if (!state.user) return;
  const data = await fetchJSON("/api/planner/plans");
  state.plans = data;
}

async function loadBookmarks() {
  if (!state.user) return;
  const data = await fetchJSON("/api/bookmarks/");
  state.bookmarks = data;
}

async function loadVisits() {
  if (!state.user) return;
  const data = await fetchJSON("/api/visits/");
  state.visits = data;
}

async function loadReport(month) {
  if (!state.user) return;
  state.report = await fetchJSON(`/api/reports/monthly?month=${month || new Date().toISOString().slice(0, 7)}`);
}

async function loadInitialData() {
  try {
    const user = await fetchJSON(`${AUTH_ENDPOINT}/me`);
    state.user = user;
    persistSession();
  } catch (error) {
    console.error("사용자 정보를 불러오지 못했습니다.", error);
    state.accessToken = null;
    persistSession();
    return;
  }

  try {
    await loadCouple();
    await Promise.all([loadPlans(), loadBookmarks(), loadVisits(), loadReport()]);
  } catch (error) {
    console.error(error);
  }
}

function restoreSession() {
  const token = sessionStorage.getItem("sra-access-token");
  if (token) {
    state.accessToken = token;
  }
  const rawUser = sessionStorage.getItem("sra-user");
  if (rawUser) {
    try {
      state.user = JSON.parse(rawUser);
    } catch (error) {
      state.user = null;
    }
  }
}

function persistSession() {
  if (state.accessToken) {
    sessionStorage.setItem("sra-access-token", state.accessToken);
    if (state.user) {
      sessionStorage.setItem("sra-user", JSON.stringify(state.user));
    }
  } else {
    sessionStorage.removeItem("sra-access-token");
    sessionStorage.removeItem("sra-user");
  }
}

async function bootstrap() {
  restoreSession();
  attachNavListeners();
  await initMap();
  if (state.accessToken) {
    try {
      await loadInitialData();
    } catch (error) {
      state.accessToken = null;
      sessionStorage.removeItem("sra-access-token");
    }
  }
  renderApp();
}

document.addEventListener("DOMContentLoaded", bootstrap);
