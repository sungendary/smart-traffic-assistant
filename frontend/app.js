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
  savedReports: [],
  isGeneratingReport: false,
  mapSuggestions: [],
  llmSuggestions: [],
  challengeStatus: null,
  isRightOpen: true,
  currentView: "map",
  // 추천 관련 상태
  currentWeather: null,
  selectedPreferences: [],
  selectedBudget: "medium",
  smartRecommendations: null,
  reportLoading: false,
  summaryLoading: false,
  savedReportsLoaded: false,
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

// 마크다운 **텍스트**를 <strong>텍스트</strong>로 변환하는 헬퍼 함수
function markdownToHTML(text) {
  if (!text) return "";
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>');
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
    // 401 Unauthorized인 경우 세션 만료로 간주하고 사용자 상태 초기화
    if (response.status === 401) {
      state.accessToken = null;
      state.user = null;
      persistSession();
      // 리포트나 다른 데이터도 초기화
      state.report = null;
      state.savedReports = [];
      state.reportLoading = false;
      state.savedReportsLoaded = false;
    }
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
      summaryCard.innerHTML += `<p class="section-caption">리포트를 불러오면 커플 매니저에게 편지를 부탁할 수 있어요.</p>`;
      container.appendChild(summaryCard);
      return;
    }
    const summaryBody = document.createElement("div");
    summaryBody.className = "report-summary-text";
    // 마크다운 **텍스트**를 <strong>텍스트</strong>로 변환하고 문단 구분
    let summaryText = state.report.summary
      ? state.report.summary.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      : "커플 매니저에게 칭찬 편지를 부탁해보세요.";
    
    // 문장을 문단으로 분리하여 들여쓰기 적용
    if (state.report.summary) {
      // 문장 단위로 분리 (마침표, 느낌표, 물음표 뒤 공백 기준)
      const sentences = summaryText.split(/([.!?。！？]\s+)/).filter(s => s.trim());
      let paragraphs = [];
      let currentPara = [];
      
      // 문장들을 2-3개씩 묶어서 문단으로 만들기
      for (let i = 0; i < sentences.length; i += 2) {
        const sentence = sentences[i];
        const punctuation = i + 1 < sentences.length ? sentences[i + 1] : '';
        const fullSentence = (sentence + punctuation).trim();
        
        if (fullSentence) {
          currentPara.push(fullSentence);
          
          // 2개 문장마다 문단 구분
          if (currentPara.length >= 2) {
            paragraphs.push(currentPara.join(' '));
            currentPara = [];
          }
        }
      }
      
      // 남은 문장들 처리
      if (currentPara.length > 0) {
        paragraphs.push(currentPara.join(' '));
      }
      
      // 문단이 없으면 전체를 하나의 문단으로
      if (paragraphs.length === 0) {
        paragraphs = [summaryText];
      }
      
      summaryText = paragraphs.map(para => `<p>${para}</p>`).join('');
    } else {
      summaryText = `<p>${summaryText}</p>`;
    }
    
    summaryBody.innerHTML = summaryText;
    summaryCard.appendChild(summaryBody);

    if (state.summaryLoading) {
      const loadingLine = document.createElement("p");
      loadingLine.className = "section-caption";
      loadingLine.textContent = "커플 매니저가 편지를 쓰는 중이에요...";
      summaryCard.appendChild(loadingLine);
    } else if (!state.report.summary) {
      const button = document.createElement("button");
      button.id = "generate-summary-btn";
      button.className = "primary-btn";
      button.textContent = "커플 매니저에게 칭찬 받기";
      summaryCard.appendChild(button);
    } else {
      const topEmotion = Object.entries(state.report.emotion_stats || {}).sort((a, b) => b[1] - a[1])[0];
      const childlikeLine = document.createElement("p");
      childlikeLine.className = "report-childlike";
      const emotionLine = topEmotion ? `${topEmotion[0]} 기분이 ${topEmotion[1]}번이나 나왔네요!` : "다음 기록도 궁금해요!";
      childlikeLine.textContent = `🍓 커플 매니저: "${emotionLine} 다음 데이트도 제가 응원할게요!"`;
      summaryCard.appendChild(childlikeLine);
      
      // 리포트 이름 변경 섹션 추가
      const nameSection = document.createElement("div");
      nameSection.className = "report-name-section";
      nameSection.style.marginTop = "1.5rem";
      nameSection.style.paddingTop = "1.5rem";
      nameSection.style.borderTop = "1px solid var(--border)";
      
      const nameLabel = document.createElement("label");
      nameLabel.textContent = "리포트 이름";
      nameLabel.style.display = "block";
      nameLabel.style.marginBottom = "0.5rem";
      nameLabel.style.fontSize = "0.9rem";
      nameLabel.style.color = "var(--text-muted)";
      
      const nameInput = document.createElement("input");
      nameInput.type = "text";
      nameInput.id = "report-name-input";
      nameInput.placeholder = `${state.report.month || new Date().toISOString().slice(0, 7)} 리포트`;
      nameInput.value = state.report.name || "";
      nameInput.className = "primary-input";
      nameInput.style.width = "100%";
      nameInput.style.marginBottom = "0.75rem";
      
      const saveNameBtn = document.createElement("button");
      saveNameBtn.id = "save-report-name-btn";
      saveNameBtn.className = "primary-btn";
      saveNameBtn.textContent = "이름 저장";
      saveNameBtn.style.width = "100%";
      
      nameSection.appendChild(nameLabel);
      nameSection.appendChild(nameInput);
      nameSection.appendChild(saveNameBtn);
      summaryCard.appendChild(nameSection);
      
      // 이름 저장 버튼 이벤트
      saveNameBtn.addEventListener("click", () => {
        const reportName = nameInput.value.trim() || `${state.report.month || new Date().toISOString().slice(0, 7)} 리포트`;
        saveReportWithName(state.report.month, reportName);
      });
    }
    container.appendChild(summaryCard);
    const summaryBtn = select("#generate-summary-btn");
    if (summaryBtn) {
      summaryBtn.addEventListener("click", () => loadReportSummary(state.report?.month));
    }
    
    // 저장된 리포트 섹션을 칭찬편지 아래에 추가
    const savedReportsCard = document.createElement("div");
    savedReportsCard.className = "card";
    savedReportsCard.style.marginTop = "1.5rem";
    const month = state.report?.month || new Date().toISOString().slice(0, 7);
    savedReportsCard.innerHTML = `
      <h2 class="section-title">저장된 리포트</h2>
      <form id="report-form" class="stack" style="margin-bottom: 1.5rem;">
        <input type="month" name="month" value="${month}" />
        <button type="submit" class="primary-btn" id="report-submit-btn" ${state.isGeneratingReport ? 'disabled' : ''}>
          ${state.isGeneratingReport ? '생성 중...' : '리포트 확인하기'}
        </button>
      </form>
      ${state.savedReports && state.savedReports.length > 0 ? `
        <div class="stack" style="max-height: 400px; overflow-y: auto;">
          ${state.savedReports.map(report => {
            const reportId = report.id || report._id || '';
            const reportName = report.name || `${report.month} 리포트`;
            return `
            <div class="card sub" style="cursor: pointer; transition: transform 0.2s ease, box-shadow 0.2s ease;" data-report-id="${reportId}">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                  <h3 style="margin: 0; font-size: 0.95rem; font-weight: 600;">${reportName}</h3>
                  <p style="margin: 0.25rem 0 0 0; font-size: 0.85rem; color: var(--text-muted);">
                    ${new Date(report.created_at).toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' })}
                  </p>
                </div>
                <span class="inline-chip">${report.visit_count}회 방문</span>
              </div>
            </div>
          `;
          }).join('')}
        </div>
      ` : `
        <p class="section-caption">아직 저장된 리포트가 없습니다. 리포트를 생성하면 여기에 표시됩니다.</p>
      `}
    `;
    container.appendChild(savedReportsCard);
    
    // 호버 효과 스타일 추가
    if (!document.querySelector('#report-hover-style')) {
      const style = document.createElement("style");
      style.id = 'report-hover-style';
      style.textContent = `
        .card.sub[data-report-id]:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(255, 90, 153, 0.15);
          border-color: rgba(255, 90, 153, 0.3);
        }
      `;
      document.head.appendChild(style);
    }
    
    select("#report-form")?.addEventListener("submit", handleReportForm);
    
    // 저장된 리포트 클릭 이벤트
    selectAll('[data-report-id]').forEach(el => {
      el.addEventListener('click', () => {
        const reportId = el.dataset.reportId;
        loadSavedReport(reportId);
      });
    });
    
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
  const hasCouple = couple && couple.members && couple.members.length >= 2;

  // 커플이 없는 경우에만 초대 코드 및 합류 섹션 표시
  if (!hasCouple) {
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

    sidebar.appendChild(inviteCard);
    sidebar.appendChild(joinCard);

    select("#regen-code")?.addEventListener("click", regenerateInviteCode);
    select("#join-form")?.addEventListener("submit", handleJoinCouple);
  }

  // 커플이 있는 경우에만 커플 선호 등록창 표시
  if (hasCouple) {
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

    sidebar.appendChild(prefCard);
    select("#pref-form")?.addEventListener("submit", handlePreferenceUpdate);
  }
}

function renderReportsView() {
  const sidebar = select("#left-sidebar");
  sidebar.innerHTML = "";

  if (!state.user) {
    sidebar.innerHTML = `<div class="card"><h2 class="section-title">로그인 필요</h2><p class="section-caption">리포트 기능은 로그인 후 이용할 수 있습니다.</p></div>`;
    return;
  }

  if (!state.report && !state.reportLoading && state.accessToken) {
    state.reportLoading = true;
    loadReport()
      .then(() => renderApp())
      .catch((error) => {
        console.error("리포트 로드 실패:", error);
        // 401 에러인 경우 이미 fetchJSON에서 상태가 초기화되었으므로 다시 렌더링
        if (!state.user || !state.accessToken) {
          renderApp();
        }
      });
  }

  if (state.reportLoading) {
    sidebar.innerHTML = `<div class="card"><h2 class="section-title">리포트를 불러오는 중</h2><p class="section-caption">커플 선호 · 플래너 감정 목표 · 방문 기록을 수집하고 있어요.</p></div>`;
    return;
  }

  if (!state.report) {
    sidebar.innerHTML = `<div class="card"><h2 class="section-title">리포트 데이터를 찾지 못했습니다</h2><p class="section-caption">잠시 후 다시 시도하거나, 방문 기록과 감정 목표를 먼저 추가해 주세요.</p></div>`;
    return;
  }

  const wrapper = document.createElement("div");
  wrapper.className = "stack";

  const report = state.report;
  const entries = Object.entries(report.emotion_stats || {});
  const topEmotion = entries.length ? entries.sort((a, b) => b[1] - a[1])[0] : null;
  const preferredTags = report.preferred_tags || [];
  const preferredEmotionGoals = report.preferred_emotion_goals || [];
  const preferredBudget = report.preferred_budget || "medium";
  const planEmotionGoals = report.plan_emotion_goals || [];
  
  // 예산 범위를 한글로 변환
  const budgetLabels = {
    "free": "무료",
    "low": "3만원 이하",
    "medium": "3~8만원",
    "high": "8~15만원",
    "premium": "15만원 이상"
  };
  const budgetLabel = budgetLabels[preferredBudget] || preferredBudget;

  const statsCard = document.createElement("div");
  statsCard.className = "card";
  const month = report.month || new Date().toISOString().slice(0, 7);
  
  const { visit_count, emotion_stats, top_tags, challenge_progress } = report;
  const totalEmotions = Object.values(emotion_stats || {}).reduce((a, b) => a + b, 0);
  const completedChallenges = (challenge_progress || []).filter(c => c.current >= c.goal).length;
  
  statsCard.innerHTML = `
    <h2 class="section-title">📊 ${month} 통계</h2>
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin: 1rem 0;">
      <div style="text-align: center; padding: 1rem; background: linear-gradient(135deg, #ff5a99, #ff80b2); border-radius: 12px; color: white;">
        <div style="font-size: 2rem; font-weight: bold;">${visit_count || 0}</div>
        <div style="font-size: 0.85rem; opacity: 0.9;">방문 횟수</div>
      </div>
      <div style="text-align: center; padding: 1rem; background: linear-gradient(135deg, #667eea, #764ba2); border-radius: 12px; color: white;">
        <div style="font-size: 2rem; font-weight: bold;">${completedChallenges}</div>
        <div style="font-size: 0.85rem; opacity: 0.9;">완료 챌린지</div>
      </div>
    </div>
    <div style="margin-top: 1rem;">
      <h3 style="font-size: 0.95rem; margin-bottom: 0.5rem; color: var(--text-muted);">주요 감정</h3>
      <div style="font-size: 1.2rem; font-weight: 600; color: var(--accent);">
        ${topEmotion ? `${topEmotion[0]} (${topEmotion[1]}회)` : '데이터 없음'}
      </div>
    </div>
    <div style="margin-top: 1rem;">
      <h3 style="font-size: 0.95rem; margin-bottom: 0.5rem; color: var(--text-muted);">인기 태그</h3>
      <div class="inline-chips">
        ${(top_tags || []).length > 0 ? top_tags.map(tag => `<span class="inline-chip">${tag}</span>`).join('') : '<span class="section-caption">태그 없음</span>'}
      </div>
    </div>
    <div style="margin-top: 1rem;">
      <h3 style="font-size: 0.95rem; margin-bottom: 0.5rem; color: var(--text-muted);">감정 분포</h3>
      <ul class="tip-list">
        ${Object.entries(emotion_stats || {}).map(([emotion, count]) => {
          const percentage = totalEmotions > 0 ? Math.round((count / totalEmotions) * 100) : 0;
          return `<li>${emotion}: ${count}회 (${percentage}%)</li>`;
        }).join('')}
      </ul>
    </div>
    <div style="margin-top: 1.5rem; padding-top: 1.5rem; border-top: 2px solid var(--border);">
      <h3 style="font-size: 1rem; margin-bottom: 1rem; color: var(--accent); font-weight: 600; display: flex; align-items: center; gap: 0.5rem;">
        <span>💕</span> 커플 선호 설정
      </h3>
      ${preferredTags.length > 0 || preferredEmotionGoals.length > 0 || preferredBudget ? `
        ${preferredTags.length > 0 ? `
          <div style="margin-bottom: 1rem;">
            <div style="font-size: 0.9rem; color: var(--text); margin-bottom: 0.5rem; font-weight: 500;">선호 태그</div>
            <div class="inline-chips">
              ${preferredTags.map(tag => `<span class="inline-chip" style="background: var(--accent-soft); color: var(--accent);">${tag}</span>`).join('')}
            </div>
          </div>
        ` : ''}
        ${preferredEmotionGoals.length > 0 ? `
          <div style="margin-bottom: 1rem;">
            <div style="font-size: 0.9rem; color: var(--text); margin-bottom: 0.5rem; font-weight: 500;">감정 목표</div>
            <div class="inline-chips">
              ${preferredEmotionGoals.map(goal => `<span class="inline-chip" style="background: var(--accent-soft); color: var(--accent);">${goal}</span>`).join('')}
            </div>
          </div>
        ` : ''}
        ${preferredBudget ? `
          <div>
            <div style="font-size: 0.9rem; color: var(--text); margin-bottom: 0.5rem; font-weight: 500;">예산 범위</div>
            <div class="inline-chips">
              <span class="inline-chip" style="background: var(--accent-soft); color: var(--accent);">${budgetLabel}</span>
            </div>
          </div>
        ` : ''}
      ` : `
        <div style="padding: 1rem; background: var(--surface-muted); border-radius: 8px; text-align: center;">
          <p class="section-caption" style="margin: 0;">커플 선호 설정이 없습니다.<br/>커플 페이지에서 선호를 등록해보세요!</p>
        </div>
      `}
    </div>
  `;
  wrapper.appendChild(statsCard);
  
  sidebar.appendChild(wrapper);
}

function renderChallengesView() {
  const sidebar = select("#left-sidebar");
  sidebar.innerHTML = "";

  if (!state.user) {
    sidebar.innerHTML = `<div class="card"><h2 class="section-title">로그인 필요</h2><p class="section-caption">챌린지 기능은 로그인 후 이용할 수 있습니다.</p></div>`;
    return;
  }

  const wrapper = document.createElement("div");
  wrapper.className = "stack";

  // 챌린지 장소 목록
  const listCard = document.createElement("div");
  listCard.className = "card";
  listCard.innerHTML = `<h2 class="section-title">챌린지 장소</h2>`;

  if (!state.challengeStatus) {
    listCard.innerHTML += `<p class="section-caption">챌린지 상태를 불러오는 중...</p>`;
    wrapper.appendChild(listCard);
    sidebar.appendChild(wrapper);
    return;
  }
  
  if (!state.challengeStatus.challenge_places || state.challengeStatus.challenge_places.length === 0) {
    listCard.innerHTML += `
      <p class="section-caption">챌린지 장소가 없습니다.</p>
      <p class="section-caption" style="font-size: 0.85rem; color: #888;">
        관리자가 챌린지 장소를 등록해야 합니다.<br/>
        또는 초기 데이터 삽입 스크립트를 실행해주세요.
      </p>
    `;
  } else {
    const list = document.createElement("div");
    list.className = "stack";
    
    state.challengeStatus.challenge_places.forEach((place) => {
      const placeCard = document.createElement("div");
      placeCard.className = "card sub";
      
      let statusBadge = "";
      let actionButton = "";
      
      if (place.review_completed) {
        statusBadge = `<span class="inline-chip" style="background: #4caf50; color: white;">완료</span>`;
      } else if (place.location_verified) {
        statusBadge = `<span class="inline-chip" style="background: #ff9800; color: white;">리뷰 작성 가능</span>`;
        actionButton = `<button class="primary-btn" data-action="review" data-place-id="${place.id}">리뷰 작성</button>`;
      } else {
        statusBadge = `<span class="inline-chip">미인증</span>`;
        actionButton = `<button class="primary-outline" data-action="verify" data-place-id="${place.id}">위치 인증</button>`;
      }
      
      placeCard.innerHTML = `
        <header class="card-header">
          <div>
            <h3 class="card-title">${place.name}</h3>
            <p class="subtext">${place.description}</p>
          </div>
          ${statusBadge}
        </header>
        <div class="pill-list">
          <span class="inline-chip">${place.badge_reward} 배지</span>
          <span class="inline-chip">${place.points_reward} 포인트</span>
        </div>
        <div style="margin-top: 0.5rem;">
          ${actionButton}
        </div>
      `;
      
      list.appendChild(placeCard);
    });
    
    listCard.appendChild(list);
  }

  wrapper.appendChild(listCard);
  sidebar.appendChild(wrapper);

  // 이벤트 리스너 등록
  selectAll('[data-action="verify"]').forEach((btn) => {
    btn.addEventListener("click", () => handleLocationVerify(btn.dataset.placeId));
  });
  
  selectAll('[data-action="review"]').forEach((btn) => {
    btn.addEventListener("click", () => handleReviewWrite(btn.dataset.placeId));
  });
}

function renderLeftSidebar() {
  if (state.currentView === "map") {
    renderMapView();
  } else if (state.currentView === "planner") {
    renderPlannerView();
  } else if (state.currentView === "couple") {
    renderCoupleView();
  } else if (state.currentView === "challenges") {
    renderChallengesView();
  } else if (state.currentView === "reports") {
    renderReportsView();
    if (state.user && !state.savedReportsLoaded && state.accessToken) {
      state.savedReportsLoaded = true;
      loadSavedReports().then(() => {
        renderReportsView();
      }).catch(() => {
        // 에러 발생 시 리포트 뷰만 다시 렌더링 (이미 fetchJSON에서 상태 초기화됨)
        renderReportsView();
      });
    }
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

async function switchView(view) {
  state.currentView = view;
  if (view !== "reports") {
    state.savedReportsLoaded = false;
  }
  
  // 챌린지 뷰로 전환 시 상태 새로고침
  if (view === "challenges" && state.user) {
    await loadChallengeStatus();
  }
  
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
    state.isGeneratingReport = true;
    renderApp();
    
    const data = await fetchJSON(`/api/reports/monthly?month=${month}`);
    state.report = data;
    state.isGeneratingReport = false;
    renderApp();
  } catch (error) {
    state.isGeneratingReport = false;
    renderApp();
    alert(error.message);
  }
}

async function handleSaveReport() {
  if (!state.report) return;
  
  try {
    const month = state.report.month;
    const saved = await fetchJSON(`/api/reports/monthly/save?month=${month}`, {
      method: "POST",
    });
    
    await loadSavedReports();
    renderApp();
    
    alert("리포트가 저장되었습니다!");
  } catch (error) {
    alert(error.message);
  }
}

async function saveReportWithName(month, name) {
  if (!state.report) return;
  
  // 즉시 UI 업데이트 (낙관적 업데이트)
  const originalName = state.report.name;
  state.report.name = name;
  
  // 저장된 리포트 목록에서도 즉시 업데이트
  if (state.savedReports) {
    const reportIndex = state.savedReports.findIndex(r => (r.id || r._id) === (state.report.id || state.report._id));
    if (reportIndex !== -1) {
      state.savedReports[reportIndex].name = name;
    }
  }
  
  // 우측 사이드바 즉시 업데이트
  renderRightPanel();
  // 좌측 사이드바도 즉시 업데이트
  if (state.currentView === "reports") {
    renderReportsView();
  }
  
  try {
    // 백그라운드에서 저장 (에러 발생 시 롤백)
    const saved = await fetchJSON(`/api/reports/monthly/save?month=${month}`, {
      method: "POST",
      body: JSON.stringify({
        ...state.report,
        name: name,
      }),
      headers: {
        "Content-Type": "application/json",
      },
    });
    
    // 저장 성공 시 상태 동기화
    if (saved.id || saved._id) {
      state.report.id = saved.id || saved._id;
    }
    
    // 성공 메시지 (alert 대신 더 빠른 피드백)
    const nameInput = select("#report-name-input");
    if (nameInput) {
      const originalText = nameInput.value;
      nameInput.style.borderColor = "var(--accent)";
      setTimeout(() => {
        nameInput.style.borderColor = "";
      }, 1000);
    }
  } catch (error) {
    // 에러 발생 시 롤백
    state.report.name = originalName;
    if (state.savedReports) {
      const reportIndex = state.savedReports.findIndex(r => (r.id || r._id) === (state.report.id || state.report._id));
      if (reportIndex !== -1) {
        state.savedReports[reportIndex].name = originalName;
      }
    }
    renderRightPanel();
    if (state.currentView === "reports") {
      renderReportsView();
    }
    alert(`저장 실패: ${error.message}`);
  }
}

async function loadSavedReports() {
  if (!state.user) return;
  try {
    state.savedReports = await fetchJSON("/api/reports/saved");
    state.savedReportsLoaded = true;
  } catch (error) {
    console.error("저장된 리포트를 불러오지 못했습니다.", error);
    // 401 에러인 경우 빈 배열로 설정하고 로그인 필요 상태로 전환
    state.savedReports = [];
    state.savedReportsLoaded = true;
    // 사용자 상태가 초기화되었으면 리포트 뷰를 다시 렌더링
    if (!state.user) {
      renderApp();
    }
  }
}

async function loadSavedReport(reportId) {
  if (!state.user) return;
  try {
    const report = await fetchJSON(`/api/reports/saved/${reportId}`);
    showReportModal(report);
  } catch (error) {
    alert(error.message);
  }
}

function showReportModal(report) {
  // 기존 모달이 있으면 제거
  const existingModal = select("#report-modal");
  if (existingModal) {
    existingModal.remove();
  }
  
  // 모달 오버레이 생성
  const modal = document.createElement("div");
  modal.id = "report-modal";
  modal.className = "report-modal-overlay";
  
  // 메모지 스타일 컨테이너
  const memoContainer = document.createElement("div");
  memoContainer.className = "report-memo-container";
  
  // 닫기 버튼
  const closeBtn = document.createElement("button");
  closeBtn.className = "report-modal-close";
  closeBtn.innerHTML = "×";
  closeBtn.addEventListener("click", () => {
    modal.remove();
  });
  
  // 오버레이 클릭 시 닫기
  modal.addEventListener("click", (e) => {
    if (e.target === modal) {
      modal.remove();
    }
  });
  
  // ESC 키로 닫기
  const handleEsc = (e) => {
    if (e.key === "Escape") {
      modal.remove();
      document.removeEventListener("keydown", handleEsc);
    }
  };
  document.addEventListener("keydown", handleEsc);
  
  // 리포트 내용
  const month = report.month || new Date().toISOString().slice(0, 7);
  const reportName = report.name || `${month} 리포트`;
  const entries = Object.entries(report.emotion_stats || {});
  const topEmotion = entries.length ? entries.sort((a, b) => b[1] - a[1])[0] : null;
  const { visit_count, emotion_stats, top_tags, challenge_progress } = report;
  const totalEmotions = Object.values(emotion_stats || {}).reduce((a, b) => a + b, 0);
  const completedChallenges = (challenge_progress || []).filter(c => c.current >= c.goal).length;
  
  // 마크다운 **텍스트**를 <strong>텍스트</strong>로 변환하고 문단 구분
  let summaryText = report.summary
    ? report.summary.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    : "리포트 요약이 없습니다.";
  
  // 문장을 문단으로 분리하여 들여쓰기 적용
  if (report.summary) {
    const sentences = summaryText.split(/([.!?。！？]\s+)/).filter(s => s.trim());
    let paragraphs = [];
    let currentPara = [];
    
    for (let i = 0; i < sentences.length; i += 2) {
      const sentence = sentences[i];
      const punctuation = i + 1 < sentences.length ? sentences[i + 1] : '';
      const fullSentence = (sentence + punctuation).trim();
      
      if (fullSentence) {
        currentPara.push(fullSentence);
        
        if (currentPara.length >= 2) {
          paragraphs.push(currentPara.join(' '));
          currentPara = [];
        }
      }
    }
    
    if (currentPara.length > 0) {
      paragraphs.push(currentPara.join(' '));
    }
    
    if (paragraphs.length === 0) {
      paragraphs = [summaryText];
    }
    
    summaryText = paragraphs.map(para => `<p>${para}</p>`).join('');
  } else {
    summaryText = `<p>${summaryText}</p>`;
  }
  
  memoContainer.innerHTML = `
    <div class="report-memo-header">
      <h1 class="report-memo-title">${reportName}</h1>
      <p class="report-memo-date">${new Date(report.created_at).toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' })}</p>
    </div>
    
    <div class="report-memo-stats">
      <div class="report-memo-stat-item">
        <span class="stat-label">방문 횟수</span>
        <span class="stat-value">${visit_count || 0}회</span>
      </div>
      <div class="report-memo-stat-item">
        <span class="stat-label">완료 챌린지</span>
        <span class="stat-value">${completedChallenges}개</span>
      </div>
      ${topEmotion ? `
      <div class="report-memo-stat-item">
        <span class="stat-label">주요 감정</span>
        <span class="stat-value">${topEmotion[0]} (${topEmotion[1]}회)</span>
      </div>
      ` : ''}
    </div>
    
    <div class="report-memo-summary">
      <h2 class="report-memo-section-title">커플 매니저의 칭찬 편지</h2>
      <div class="report-memo-summary-text">${summaryText}</div>
      ${topEmotion ? `
      <div class="report-memo-footer">
        <p class="report-childlike">🍓 커플 매니저: "${topEmotion[0]} 기분이 ${topEmotion[1]}번이나 나왔네요! 다음 데이트도 제가 응원할게요!"</p>
      </div>
      ` : ''}
    </div>
    
    ${top_tags && top_tags.length > 0 ? `
    <div class="report-memo-tags">
      <h3 class="report-memo-section-subtitle">인기 태그</h3>
      <div class="inline-chips">
        ${top_tags.map(tag => `<span class="inline-chip">${tag}</span>`).join('')}
      </div>
    </div>
    ` : ''}
    
    ${Object.keys(emotion_stats || {}).length > 0 ? `
    <div class="report-memo-emotions">
      <h3 class="report-memo-section-subtitle">감정 분포</h3>
      <ul class="tip-list">
        ${Object.entries(emotion_stats).map(([emotion, count]) => {
          const percentage = totalEmotions > 0 ? Math.round((count / totalEmotions) * 100) : 0;
          return `<li>${emotion}: ${count}회 (${percentage}%)</li>`;
        }).join('')}
      </ul>
    </div>
    ` : ''}
  `;
  
  memoContainer.appendChild(closeBtn);
  modal.appendChild(memoContainer);
  document.body.appendChild(modal);
  
  // 애니메이션을 위해 약간의 지연 후 표시
  setTimeout(() => {
    modal.classList.add("show");
  }, 10);
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
    // 401 에러인 경우 리포트 뷰를 다시 렌더링하여 "로그인 필요" 메시지 표시
    if (error.message.includes("401") || !state.user) {
      state.report = null;
      renderApp();
    }
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
    
    // 리포트 요약 생성 후 자동으로 DB에 저장 (이미 생성된 리포트 데이터 전달하여 중복 LLM 호출 방지)
    try {
      const defaultName = `${month || new Date().toISOString().slice(0, 7)} 리포트`;
      const saved = await fetchJSON(`/api/reports/monthly/save?month=${month || new Date().toISOString().slice(0, 7)}`, {
        method: "POST",
        body: JSON.stringify({
          ...data,
          name: defaultName,
        }),  // 이미 생성된 리포트 데이터 전달
      });
      // 리포트 상태에 이름 추가
      state.report.name = defaultName;
      // 저장된 리포트 목록 새로고침
      await loadSavedReports();
      console.log("리포트가 자동으로 저장되었습니다.");
    } catch (saveError) {
      console.error("리포트 저장 실패:", saveError);
      // 저장 실패해도 요약은 표시
    }
    } catch (error) {
      alert(error.message);
  } finally {
    state.summaryLoading = false;
    renderApp();
    }
}

async function loadChallengeStatus() {
  if (!state.user) return;
  try {
    state.challengeStatus = await fetchJSON("/api/challenges/status");
    console.log("챌린지 상태 로드 완료:", state.challengeStatus);
  } catch (error) {
    console.error("챌린지 상태를 불러오지 못했습니다.", error);
    state.challengeStatus = { points: 0, badges: [], challenge_places: [] };
    // 에러가 발생해도 빈 상태로 설정하여 UI가 계속 작동하도록 함
  }
}

async function handleLocationVerify(placeId) {
  if (!navigator.geolocation) {
    alert("이 브라우저는 위치 서비스를 지원하지 않습니다.");
    return;
  }
  
  setStatus("위치 확인 중...", "info");
  
  navigator.geolocation.getCurrentPosition(
    async (position) => {
      const { latitude, longitude } = position.coords;
      
      try {
        const result = await fetchJSON("/api/challenges/verify-location", {
          method: "POST",
          body: JSON.stringify({
            challenge_place_id: placeId,
            latitude,
            longitude,
          }),
        });
        
        if (result.verified) {
          setStatus(result.message, "success");
          // 위치 인증 완료 후 챌린지 상태 새로고침
          await loadChallengeStatus();
          renderApp();
          alert("위치 인증이 완료되었습니다! 이제 리뷰를 작성할 수 있습니다.");
        } else {
          setStatus(result.message, "error");
          alert(result.message);
        }
      } catch (error) {
        setStatus(error.message, "error");
        alert(error.message);
      }
    },
    (error) => {
      const message = error.code === 1 
        ? "위치 접근이 거부되었습니다. 브라우저 설정에서 위치 권한을 허용해주세요."
        : "위치를 확인할 수 없습니다.";
      setStatus(message, "error");
      alert(message);
    },
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
  );
}

async function handleReviewWrite(placeId) {
  const place = state.challengeStatus?.challenge_places?.find((p) => p.id === placeId);
  if (!place) {
    alert("챌린지 장소를 찾을 수 없습니다.");
    return;
  }
  
  // 리뷰 작성 모달
  const modal = document.createElement("div");
  modal.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.7);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  `;
  
  const form = document.createElement("form");
  form.className = "card";
  form.style.cssText = "max-width: 500px; width: 90%; max-height: 90vh; overflow-y: auto;";
  form.innerHTML = `
    <h2 class="section-title">${place.name} 리뷰 작성</h2>
    <div class="stack">
      <label>
        별점 (1-5점)
        <input type="number" name="rating" min="1" max="5" step="0.5" value="5" required />
      </label>
      <label>
        리뷰
        <textarea name="memo" rows="5" placeholder="이 장소에 대한 리뷰를 작성해주세요." required></textarea>
      </label>
      <label>
        감정
        <select name="emotion">
          <option value="설렘">설렘</option>
          <option value="힐링">힐링</option>
          <option value="편안함">편안함</option>
          <option value="위로">위로</option>
          <option value="즐거움">즐거움</option>
        </select>
      </label>
      <div style="display: flex; gap: 0.5rem;">
        <button type="submit" class="primary-btn" style="flex: 1;">제출</button>
        <button type="button" class="primary-outline" id="cancel-review" style="flex: 1;">취소</button>
      </div>
    </div>
  `;
  
  modal.appendChild(form);
  document.body.appendChild(modal);
  
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData(form);
    
    try {
      setStatus("리뷰 작성 중...", "info");
      
      await fetchJSON("/api/visits/checkin", {
        method: "POST",
        body: JSON.stringify({
          place_id: placeId,
          place_name: place.name,
          challenge_place_id: placeId,
          location_verified: true,
          rating: parseFloat(formData.get("rating")),
          memo: formData.get("memo"),
          emotion: formData.get("emotion"),
          tags: [],
        }),
      });
      
      document.body.removeChild(modal);
      setStatus("리뷰가 작성되었습니다!", "success");
      
      // 챌린지 상태 새로고침
      await loadChallengeStatus();
      await loadVisits();
      renderApp();
      
      alert(`리뷰 작성 완료! ${place.points_reward} 포인트와 ${place.badge_reward} 배지를 획득했습니다!`);
    } catch (error) {
      setStatus(error.message, "error");
      alert(error.message);
    }
  });
  
  select("#cancel-review").addEventListener("click", () => {
    document.body.removeChild(modal);
  });
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
    await Promise.all([loadPlans(), loadBookmarks(), loadVisits(), loadReport(), loadSavedReports(), loadChallengeStatus()]);
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
