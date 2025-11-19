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
  // 추천 관련 상태
  currentWeather: null,
  selectedPreferences: [],
  selectedBudget: "medium",
  smartRecommendations: null,
  reportLoading: false,
  summaryLoading: false,
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
    state.reportLoading = false;
    state.summaryLoading = false;
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

// frontend/app.js
async function initMap() {
  try {
    // 1. 백엔드에서 API 키 가져오기
    const config = await fetchJSON(MAPS_CONFIG_ENDPOINT);
    
    // 2. SDK 로드 (수정해주신 loadKakaoMapsSdk 사용)
    await loadKakaoMapsSdk(config.kakaoMapAppKey);
    
    // 3. 지도 생성
    const container = document.getElementById("map");
    if (!container) {
        console.warn("지도 컨테이너(#map)를 찾을 수 없습니다.");
        return;
    }

    const options = {
      center: new window.kakao.maps.LatLng(state.center.latitude, state.center.longitude),
      level: 3,
    };

    state.map = new window.kakao.maps.Map(container, options);
    
    // 4. 줌 컨트롤 추가 (선택 사항)
    const zoomControl = new window.kakao.maps.ZoomControl();
    state.map.addControl(zoomControl, window.kakao.maps.ControlPosition.RIGHT);

    console.log("지도 초기화 완료");
  } catch (error) {
    console.error("지도 초기화 실패:", error);
    setStatus("지도를 불러오지 못했습니다: " + error.message, "error");
  }
}

async function loadKakaoMapsSdk(appKey) {
  if (!appKey) throw new Error("Kakao App Key가 필요합니다.");
  
  // 이미 로드되어 있고 services 라이브러리까지 있다면 재사용
  if (window.kakao && window.kakao.maps && window.kakao.maps.services) {
    return window.kakao.maps;
  }

  await new Promise((resolve, reject) => {
    const script = document.createElement("script");
    // 주의: 반드시 숫자 1번 옆에 있는 백틱(`)을 사용해야 합니다!
    script.src = `https://dapi.kakao.com/v2/maps/sdk.js?autoload=false&appkey=${appKey}&libraries=services`;
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

/**
 * Kakao Geocoding API를 사용해 지역명을 좌표로 변환
 * @param {string} locationName - 변환할 지역명 (예: "강남역", "서울")
 * @returns {Promise<{lat: number, lon: number, name: string} | null>}
 */
// frontend/app.js

/**
 * [수정됨] Kakao Maps SDK의 Places(키워드 검색) 라이브러리 사용
 */
async function geocodeLocation(locationName) {
  // 라이브러리가 로드되지 않았거나 검색어가 없으면 중단
  if (!locationName || !window.kakao || !window.kakao.maps || !window.kakao.maps.services) {
    console.warn("Kakao Maps Services 라이브러리가 로드되지 않았습니다.");
    return null;
  }

  // 장소 검색 객체 생성
  const ps = new window.kakao.maps.services.Places();

  return new Promise((resolve) => {
    ps.keywordSearch(locationName, (data, status) => {
      if (status === window.kakao.maps.services.Status.OK) {
        const result = data[0];
        console.log(`검색 성공: ${result.place_name}`);
        resolve({
          lat: parseFloat(result.y),
          lon: parseFloat(result.x),
          name: result.place_name
        });
      } else {
        console.warn(`장소 검색 실패: ${locationName}, status: ${status}`);
        resolve(null);
      }
    });
  });
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

  if (state.currentView === "reports") {
    const summaryCard = document.createElement("div");
    summaryCard.className = "card report-summary-card";
    summaryCard.innerHTML = `<h2 class="section-title">꼬마 매니저의 칭찬 편지</h2>`;
    if (!state.report) {
      summaryCard.innerHTML += `<p class="section-caption">리포트를 불러오면 토토에게 편지를 부탁할 수 있어요.</p>`;
      container.appendChild(summaryCard);
      return;
    }
    const summaryBody = document.createElement("p");
    summaryBody.className = "report-summary-text";
    summaryBody.textContent = state.report.summary
      ? state.report.summary
      : "토토에게 칭찬 편지를 부탁해보세요.";
    summaryCard.appendChild(summaryBody);

    if (state.summaryLoading) {
      const loadingLine = document.createElement("p");
      loadingLine.className = "section-caption";
      loadingLine.textContent = "토토가 편지를 쓰는 중이에요...";
      summaryCard.appendChild(loadingLine);
    } else if (!state.report.summary) {
      const button = document.createElement("button");
      button.id = "generate-summary-btn";
      button.className = "primary-btn";
      button.textContent = "토토에게 칭찬 받기";
      summaryCard.appendChild(button);
    } else {
      const topEmotion = Object.entries(state.report.emotion_stats || {}).sort((a, b) => b[1] - a[1])[0];
      const childlikeLine = document.createElement("p");
      childlikeLine.className = "report-childlike";
      const emotionLine = topEmotion ? `${topEmotion[0]} 기분이 ${topEmotion[1]}번이나 나왔네요!` : "다음 기록도 궁금해요!";
      childlikeLine.textContent = `🍓 토토 매니저: "${emotionLine} 다음 데이트도 제가 응원할게요!"`;
      summaryCard.appendChild(childlikeLine);
    }
    container.appendChild(summaryCard);
    const summaryBtn = select("#generate-summary-btn");
    if (summaryBtn) {
      summaryBtn.addEventListener("click", () => loadReportSummary(state.report?.month));
    }
    return;
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
    <h2 class="section-title">스마트 데이트 추천 받기</h2>
    <form id="suggest-form" class="stack">
      <label>
        <strong>예산 범위</strong>
        <select name="budget_range" required>
          <option value="free">무료</option>
          <option value="low">3만원 이하</option>
          <option value="medium" selected>3~8만원</option>
          <option value="high">8~15만원</option>
          <option value="premium">15만원 이상</option>
        </select>
      </label>
      <label>
        <strong>취향 선택 (다중 선택 가능)</strong>
        <div class="preference-tags" id="preference-tags">
          <button type="button" class="tag-btn" data-tag="romantic">낭만적인</button>
          <button type="button" class="tag-btn" data-tag="energetic">활동적인</button>
          <button type="button" class="tag-btn" data-tag="relaxing">힐링</button>
          <button type="button" class="tag-btn" data-tag="food">맛집</button>
          <button type="button" class="tag-btn" data-tag="nature">자연</button>
          <button type="button" class="tag-btn" data-tag="indoor">실내</button>
          <button type="button" class="tag-btn" data-tag="outdoor">야외</button>
          <button type="button" class="tag-btn" data-tag="quiet">조용한</button>
          <button type="button" class="tag-btn" data-tag="trendy">트렌디</button>
        </div>
      </label>
      <select name="emotion">
        <option value="">감정 선택 (선택사항)</option>
        <option value="행복한">행복한</option>
        <option value="설레는">설레는</option>
        <option value="평온한">평온한</option>
        <option value="힐링">힐링</option>
        <option value="편안함">편안함</option>
        <option value="위로">위로</option>
        <option value="즐거움">즐거움</option>
      </select>
      <input type="text" name="location_desc" placeholder="지역 설명 (예: 강남역)" value="서울" />
      <button type="submit" class="primary-btn">💡 스마트 추천 받기</button>
    </form>
  `;

  // 날씨 정보 카드
  const weatherCard = document.createElement("div");
  weatherCard.className = "card";
  weatherCard.id = "weather-card";
  if (state.currentWeather) {
    const w = state.currentWeather;
    weatherCard.innerHTML = `
      <h3 class="section-title">🌤️ 현재 날씨</h3>
      <p>${w.description} · ${w.temperature}°C (체감 ${w.feels_like}°C)</p>
      <p class="subtext">습도 ${w.humidity}% · 바람 ${w.wind_speed}m/s</p>
    `;
  } else {
    weatherCard.innerHTML = `<h3 class="section-title">🌤️ 날씨 정보</h3><p class="subtext">추천을 받으면 날씨 정보가 표시됩니다</p>`;
  }

  const resultCard = document.createElement("div");
  resultCard.className = "card";
  if (!state.smartRecommendations) {
    resultCard.innerHTML = `<h2 class="section-title">추천 결과</h2><p class="section-caption">위 폼을 작성하고 추천 받기를 눌러주세요.</p>`;
  } else {
    const rec = state.smartRecommendations;
    resultCard.innerHTML = `
      <h2 class="section-title">🎯 추천 장소 (${rec.recommended_places.length}개)</h2>
      <p class="subtext">${rec.budget_info.description}</p>
    `;
    const list = document.createElement("div");
    list.className = "stack";
    rec.recommended_places.slice(0, 10).forEach((place) => {
      const card = document.createElement("div");
      card.className = "card sub";
      card.innerHTML = `
        <header class="card-header">
          <div>
            <h3 class="card-title">${place.place_name}</h3>
            <p class="subtext">${place.description || place.category_name}</p>
            <div class="pill-list">${place.tags.map((tag) => `<span class="inline-chip">${tag}</span>`).join("")}</div>
            <p class="subtext" style="margin-top:8px;">
              점수: ${(place.recommendation_score * 100).toFixed(0)}점 | 
              예상비용: ${place.estimated_cost.toLocaleString()}원 | 
              평점: ⭐${place.rating}
            </p>
          </div>
        </header>
      `;
      list.appendChild(card);
    });
    resultCard.appendChild(list);
  }

  sidebar.appendChild(formCard);
  sidebar.appendChild(weatherCard);
  sidebar.appendChild(resultCard);

  // 태그 선택 기능
  selectAll(".tag-btn").forEach((btn) => {
    if (state.selectedPreferences.includes(btn.dataset.tag)) {
      btn.classList.add("active");
    }
    btn.addEventListener("click", () => {
      btn.classList.toggle("active");
      const tag = btn.dataset.tag;
      if (state.selectedPreferences.includes(tag)) {
        state.selectedPreferences = state.selectedPreferences.filter((t) => t !== tag);
      } else {
        state.selectedPreferences.push(tag);
      }
    });
  });

  select("#suggest-form").addEventListener("submit", handleSmartRecommendation);
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

  if (!state.report && !state.reportLoading) {
    state.reportLoading = true;
    loadReport()
      .then(() => renderApp())
      .catch((error) => console.error(error));
  }

  if (state.reportLoading) {
    sidebar.innerHTML = `<div class="card"><h2 class="section-title">리포트를 불러오는 중</h2><p class="section-caption">커플 선호 · 플래너 감정 목표 · 방문 기록을 수집하고 있어요.</p></div>`;
    return;
  }

  if (!state.report) {
    sidebar.innerHTML = `<div class="card"><h2 class="section-title">리포트 데이터를 찾지 못했습니다</h2><p class="section-caption">잠시 후 다시 시도하거나, 방문 기록과 감정 목표를 먼저 추가해 주세요.</p></div>`;
    return;
  }

  const report = state.report;
  const entries = Object.entries(report.emotion_stats || {});
  const topEmotion = entries.length ? entries.sort((a, b) => b[1] - a[1])[0] : null;
  const preferredTags = report.preferred_tags || [];
  const preferredEmotionGoals = report.preferred_emotion_goals || [];
  const planEmotionGoals = report.plan_emotion_goals || [];

  const highlightCard = document.createElement("div");
  highlightCard.className = "card report-highlight-card";
  highlightCard.innerHTML = `
    <h2 class="section-title">${report.month} 하이라이트</h2>
    <p class="section-caption">커플 선호, 플래너 감정 목표, 방문 기록 데이터를 한눈에 정리했어요.</p>
  `;
  const highlightGrid = document.createElement("div");
  highlightGrid.className = "report-highlight-grid";
  [
    { label: "이번 달 방문", value: `${report.visit_count ?? 0}회`, caption: "방문 기록 기준" },
    {
      label: "선호 태그",
      value: preferredTags.slice(0, 2).join(" · ") || "등록된 태그 없음",
      caption: "커플 설정",
    },
    {
      label: "커플 감정 목표",
      value: preferredEmotionGoals.slice(0, 2).join(" · ") || "등록된 목표 없음",
      caption: "커플 설정",
    },
    {
      label: "플래너 감정 목표",
      value: planEmotionGoals.slice(0, 2).join(" · ") || "플랜 없음",
      caption: "플래너",
    },
  ].forEach((metric) => {
    const pill = document.createElement("div");
    pill.className = "report-highlight-pill";
    pill.innerHTML = `
      <p class="pill-label">${metric.label}</p>
      <p class="pill-value">${metric.value}</p>
      <p class="pill-caption">${metric.caption}</p>
    `;
    highlightGrid.appendChild(pill);
  });
  highlightCard.appendChild(highlightGrid);
  sidebar.appendChild(highlightCard);

  const preferenceCard = document.createElement("div");
  preferenceCard.className = "card";
  const chipSections = [
    { title: "커플 선호 태그", items: preferredTags, empty: "커플 창에서 태그를 추가해보세요." },
    { title: "커플 감정 목표", items: preferredEmotionGoals, empty: "커플 창에서 감정 목표를 입력하세요." },
    { title: "플래너 감정 목표", items: planEmotionGoals, empty: "플래너에 감정 목표가 있는 플랜을 만들어보세요." },
  ];
  chipSections.forEach((section) => {
    const block = document.createElement("div");
    block.className = "report-chip-section";
    const title = document.createElement("p");
    title.className = "pill-label";
    title.textContent = section.title;
    block.appendChild(title);
    if (!section.items.length) {
      const empty = document.createElement("p");
      empty.className = "section-caption";
      empty.textContent = section.empty;
      block.appendChild(empty);
    } else {
      const chips = document.createElement("div");
      chips.className = "inline-chips";
      section.items.forEach((item) => {
        const chip = document.createElement("span");
        chip.className = "inline-chip";
        chip.textContent = item;
        chips.appendChild(chip);
      });
      block.appendChild(chips);
    }
    preferenceCard.appendChild(block);
  });
  sidebar.appendChild(preferenceCard);

  const detailGrid = document.createElement("div");
  detailGrid.className = "report-detail-grid";

  const emotionCard = document.createElement("div");
  emotionCard.className = "card report-detail-card";
  emotionCard.innerHTML = `<h2 class="section-title">감정 분포</h2>`;
  if (entries.length) {
    const emotionList = document.createElement("ul");
    emotionList.className = "report-emotion-list";
    entries.forEach(([emotion, count]) => {
      const li = document.createElement("li");
      li.textContent = `${emotion} 기분 ${count}회`;
      emotionList.appendChild(li);
    });
    emotionCard.appendChild(emotionList);
  } else {
    emotionCard.innerHTML += `<p class="section-caption">아직 감정 기록이 없습니다.</p>`;
  }
  detailGrid.appendChild(emotionCard);

  const challengeCard = document.createElement("div");
  challengeCard.className = "card report-detail-card";
  challengeCard.innerHTML = `<h2 class="section-title">챌린지 진행</h2>`;
  const progressList = document.createElement("ul");
  progressList.className = "tip-list";
  (report.challenge_progress || []).forEach((c) => {
    const li = document.createElement("li");
    li.textContent = `${c.badge_icon} ${c.title} (${c.current}/${c.goal})`;
    progressList.appendChild(li);
  });
  if ((report.challenge_progress || []).length === 0) {
    challengeCard.innerHTML += `<p class="section-caption">아직 완료한 챌린지가 없습니다.</p>`;
  } else {
    challengeCard.appendChild(progressList);
  }
  detailGrid.appendChild(challengeCard);

  sidebar.appendChild(detailGrid);

  const formCard = document.createElement("div");
  formCard.className = "card";
  const month = report.month || new Date().toISOString().slice(0, 7);
  formCard.innerHTML = `
    <h2 class="section-title">다른 달 리포트 보기</h2>
    <p class="section-caption">월을 변경하면 커플 선호 · 플래너 감정 목표 · 방문 기록을 다시 수집합니다.</p>
    <form id="report-form" class="stack">
      <input type="month" name="month" value="${month}" />
      <button type="submit" class="primary-btn">리포트 확인</button>
    </form>
  `;
  sidebar.appendChild(formCard);
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
    renderApp();
    await loadInitialData();
    switchView("map");
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

async function handleSmartRecommendation(event) {
  event.preventDefault();
  if (!state.user) {
    alert("로그인이 필요합니다.");
    return;
  }
  
  const formData = new FormData(event.target);
  let locationDesc = formData.get("location_desc") || "";
  
  // 지역명이 입력되었으면 확인
  if (!locationDesc) {
    alert("지역을 입력해주세요. (예: 강남역, 광교역, 서울)");
    return;
  }
  
  setStatus(`📍 "${locationDesc}" 위치 검색 중...`, "info");
  
  const params = new URLSearchParams({
    lat: state.center.latitude,  // 기본값만 전달 (백엔드에서 location_desc로 변환)
    lon: state.center.longitude,
    budget_range: formData.get("budget_range") || "medium",
    emotion: formData.get("emotion") || "",
    location_desc: locationDesc  // 지역명 전달 - 백엔드에서 변환 처리
  });
  
  // 선택된 취향 태그 추가
  state.selectedPreferences.forEach(tag => {
    params.append("preferences", tag);
  });
  
  try {
    setStatus("🔍 스마트 추천 생성 중... (지역 확인, 날씨 확인, 장소 분석)", "info");
    
    const data = await fetchJSON(`/api/recommendations/recommend?${params.toString()}`, {
      method: "POST"
    });
    
    state.smartRecommendations = data;
    state.currentWeather = data.weather;
    state.llmSuggestions = data.ai_course_suggestions || [];
    
    // 지도를 추천 위치로 이동 (응답에서 첫 번째 장소 기반)
    if (data.recommended_places && data.recommended_places.length > 0) {
      const firstPlace = data.recommended_places[0];
      const kakaoMaps = window.kakao.maps;
      if (kakaoMaps && state.map && firstPlace.coordinates) {
        const newCenter = new kakaoMaps.LatLng(
          firstPlace.coordinates.latitude,
          firstPlace.coordinates.longitude
        );
        state.map.setCenter(newCenter);
        state.center = {
          latitude: firstPlace.coordinates.latitude,
          longitude: firstPlace.coordinates.longitude
        };
      }
      
      // 지도에 마커 표시
      const placesForMap = data.recommended_places.map(p => ({
        coordinates: p.coordinates,
        name: p.place_name,
        description: p.description,
        tags: p.tags
      }));
      addMarkers(placesForMap);
    }
    
    const summary = `✨ ${data.recommended_places.length}개 장소 추천 완료! (지역: ${locationDesc}, 날씨: ${data.weather.description})`;
    setStatus(summary, "success");
    renderApp();
    
  } catch (error) {
    console.error("스마트 추천 오류:", error);
    setStatus(`추천 실패: ${error.message}`, "error");
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
    await loadReport(month);
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
  state.reportLoading = true;
  state.summaryLoading = false;
  try {
    state.report = await fetchJSON(`/api/reports/monthly?month=${month || new Date().toISOString().slice(0, 7)}`);
  } catch (error) {
    console.error("리포트 불러오기 실패", error);
    throw error;
  } finally {
    state.reportLoading = false;
  }
}

async function loadReportSummary(month) {
  if (!state.user) return;
  state.summaryLoading = true;
  renderApp();
  try {
    const data = await fetchJSON(`/api/reports/monthly/summary?month=${month || new Date().toISOString().slice(0, 7)}`, {
      method: "POST",
    });
    state.report = data;
  } catch (error) {
    alert(error.message);
  } finally {
    state.summaryLoading = false;
    renderApp();
  }
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
    renderApp();
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
  renderApp();
  if (state.accessToken) {
    try {
      await loadInitialData();
    } catch (error) {
      state.accessToken = null;
      sessionStorage.removeItem("sra-access-token");
    }
  }
  switchView(state.currentView);
}

document.addEventListener("DOMContentLoaded", bootstrap);
