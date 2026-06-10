const navItems = [...document.querySelectorAll(".nav-item")];
const views = [...document.querySelectorAll("[data-view]")];
const filterBar = document.querySelector(".filter-bar");
const noticeGrid = document.querySelector("#notice-grid");
const noticeCount = document.querySelector("#notice-count");
const expiredFilterBar = document.querySelector("#expired-filter-bar");
const expiredGrid = document.querySelector("#expired-grid");
const expiredCount = document.querySelector("#expired-count");
const bookmarkGrid = document.querySelector("#bookmark-grid");
const bookmarkCount = document.querySelector("#bookmark-count");
const noticeSearch = document.querySelector("#notice-search");
const noticeSearchClear = document.querySelector("#notice-search-clear");
const expiredSearch = document.querySelector("#expired-search");
const expiredSearchClear = document.querySelector("#expired-search-clear");
const recommendedKeywords = document.querySelector("#recommended-keywords");
const homeAlert = document.querySelector("#home-alert");
const todayNewCount = document.querySelector("#today-new-count");
const activeNoticeCount = document.querySelector("#active-notice-count");
const homeBookmarkCount = document.querySelector("#home-bookmark-count");
const followForm = document.querySelector("#follow-form");
const followInput = document.querySelector("#follow-input");
const followKeywords = document.querySelector("#follow-keywords");
const followMatchCount = document.querySelector("#follow-match-count");
const homeMatchList = document.querySelector("#home-match-list");
const noticeModal = document.querySelector("#notice-modal");
const noticeModalPanel = document.querySelector(".notice-modal-panel");
const noticeModalContent = document.querySelector("#notice-modal-content");

const RECOMMENDED_KEYWORDS = ["#AI", "#보안", "#양자", "#R&D", "#클라우드"];
const FOLLOW_KEYWORDS_STORAGE_KEY = "gov_scrapper_follow_keywords";

const state = {
  notices: [],
  expiredNotices: [],
  bookmarks: [],
  sources: [],
  expiredSources: [],
  selectedSource: "all",
  selectedExpiredSource: "all",
  searchQuery: "",
  expiredSearchQuery: "",
  followKeywords: readFollowKeywords(),
  loadingNotices: false,
  loadedNotices: false,
};

function setActiveNav() {
  const currentHash = window.location.hash || "#home";
  const viewName = currentHash.replace("#", "");

  for (const item of navItems) {
    const isActive = item.getAttribute("href") === currentHash;
    item.classList.toggle("active", isActive);

    if (isActive) {
      item.setAttribute("aria-current", "page");
    } else {
      item.removeAttribute("aria-current");
    }
  }

  for (const view of views) {
    view.hidden = view.dataset.view !== viewName;
  }

  if (
    (viewName === "home" || viewName === "notices" || viewName === "bookmarks" || viewName === "expired") &&
    !state.loadedNotices
  ) {
    loadNotices();
  }

  if (viewName === "bookmarks") {
    renderBookmarks();
  }

  if (viewName === "expired") {
    renderExpiredNotices();
  }

  if (viewName === "home") {
    renderHome();
  }
}

window.addEventListener("hashchange", setActiveNav);
setActiveNav();

if (noticeSearch) {
  noticeSearch.addEventListener("input", () => {
    state.searchQuery = noticeSearch.value;
    updateSearchClear();
    renderNotices();
  });
}

if (noticeSearchClear && noticeSearch) {
  noticeSearchClear.addEventListener("click", () => {
    state.searchQuery = "";
    noticeSearch.value = "";
    updateSearchClear();
    noticeSearch.focus();
    renderNotices();
  });
}

if (expiredSearch) {
  expiredSearch.addEventListener("input", () => {
    state.expiredSearchQuery = expiredSearch.value;
    updateExpiredSearchClear();
    renderExpiredNotices();
  });
}

if (expiredSearchClear && expiredSearch) {
  expiredSearchClear.addEventListener("click", () => {
    state.expiredSearchQuery = "";
    expiredSearch.value = "";
    updateExpiredSearchClear();
    expiredSearch.focus();
    renderExpiredNotices();
  });
}

if (recommendedKeywords) {
  recommendedKeywords.addEventListener("click", (event) => {
    const button = event.target.closest(".keyword-chip");
    if (!button || !noticeSearch) {
      return;
    }

    state.searchQuery = button.dataset.keyword ?? "";
    noticeSearch.value = state.searchQuery;
    updateSearchClear();
    renderNotices();
  });
}

if (followForm && followInput) {
  followForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const keyword = normalizeKeyword(followInput.value);
    if (!keyword) {
      return;
    }

    state.followKeywords = [...new Set([...state.followKeywords, keyword])];
    followInput.value = "";
    writeFollowKeywords();
    renderHome();
  });
}

if (followKeywords) {
  followKeywords.addEventListener("click", (event) => {
    const button = event.target.closest(".follow-remove");
    if (!button) {
      return;
    }

    state.followKeywords = state.followKeywords.filter((keyword) => keyword !== button.dataset.keyword);
    writeFollowKeywords();
    renderHome();
  });
}

async function loadNotices() {
  if (state.loadingNotices) {
    return;
  }

  if (!noticeGrid || !filterBar || !noticeCount) {
    return;
  }

  state.loadingNotices = true;
  noticeGrid.innerHTML = '<p class="empty-state">공고를 불러오는 중입니다.</p>';
  if (expiredGrid) {
    expiredGrid.innerHTML = '<p class="empty-state">마감공고를 불러오는 중입니다.</p>';
  }
  if (bookmarkGrid) {
    bookmarkGrid.innerHTML = '<p class="empty-state">북마크를 불러오는 중입니다.</p>';
  }

  try {
    const response = await fetch("/api/notices");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    state.notices = data.notices ?? [];
    state.expiredNotices = data.expired_notices ?? [];
    state.bookmarks = data.bookmarks ?? [];
    state.sources = data.sources ?? [];
    state.expiredSources = data.expired_sources ?? [];
    state.loadedNotices = true;
    renderFilters();
    renderExpiredFilters();
    renderRecommendedKeywords();
    renderHome();
    renderNotices();
    renderExpiredNotices();
    renderBookmarks();
  } catch {
    noticeGrid.innerHTML = '<p class="empty-state">공고를 불러오지 못했습니다.</p>';
    if (expiredGrid) {
      expiredGrid.innerHTML = '<p class="empty-state">마감공고를 불러오지 못했습니다.</p>';
    }
    if (bookmarkGrid) {
      bookmarkGrid.innerHTML = '<p class="empty-state">북마크를 불러오지 못했습니다.</p>';
    }
  } finally {
    state.loadingNotices = false;
  }
}

function renderFilters() {
  const sourceButtons = state.sources
    .map(
      (source) => `
        <button class="filter-chip" type="button" data-source="${escapeHtml(source.source)}">
          ${escapeHtml(source.display_name)}
        </button>
      `,
    )
    .join("");

  filterBar.innerHTML = `
    <button class="filter-chip active" type="button" data-source="all">전체</button>
    ${sourceButtons}
  `;

  filterBar.addEventListener("click", (event) => {
    const button = event.target.closest(".filter-chip");
    if (!button) {
      return;
    }

    state.selectedSource = button.dataset.source;
    renderNotices();
  });
}

function renderExpiredFilters() {
  if (!expiredFilterBar) {
    return;
  }

  const sourceButtons = state.expiredSources
    .map(
      (source) => `
        <button class="filter-chip" type="button" data-source="${escapeHtml(source.source)}">
          ${escapeHtml(source.display_name)}
        </button>
      `,
    )
    .join("");

  expiredFilterBar.innerHTML = `
    <button class="filter-chip active" type="button" data-source="all">전체</button>
    ${sourceButtons}
  `;

  expiredFilterBar.addEventListener("click", (event) => {
    const button = event.target.closest(".filter-chip");
    if (!button) {
      return;
    }

    state.selectedExpiredSource = button.dataset.source;
    renderExpiredNotices();
  });
}

function renderNotices() {
  const normalizedQuery = normalizeSearchText(state.searchQuery);
  const filteredNotices = state.notices.filter((notice) => {
    const matchesSource = state.selectedSource === "all" || notice.source === state.selectedSource;
    const matchesSearch =
      normalizedQuery === "" || normalizeSearchText(notice.title).includes(normalizedQuery);

    return matchesSource && matchesSearch;
  });

  noticeCount.textContent = `${filteredNotices.length}건`;

  for (const button of filterBar.querySelectorAll(".filter-chip")) {
    button.classList.toggle("active", button.dataset.source === state.selectedSource);
  }

  if (filteredNotices.length === 0) {
    noticeGrid.innerHTML = '<p class="empty-state">표시할 공고가 없습니다.</p>';
    return;
  }

  noticeGrid.innerHTML = filteredNotices
    .map((notice) => renderNoticeCard(notice, { highlightFollow: true }))
    .join("");
}

function renderBookmarks() {
  if (!bookmarkGrid || !bookmarkCount) {
    return;
  }

  const markedNotices = state.bookmarks;
  bookmarkCount.textContent = `${markedNotices.length}건`;

  if (!state.loadedNotices) {
    bookmarkGrid.innerHTML = '<p class="empty-state">북마크를 불러오는 중입니다.</p>';
    return;
  }

  if (markedNotices.length === 0) {
    bookmarkGrid.innerHTML = '<p class="empty-state">북마크된 공고가 없습니다.</p>';
    return;
  }

  bookmarkGrid.innerHTML = markedNotices.map(renderNoticeCard).join("");
}

function renderExpiredNotices() {
  if (!expiredGrid || !expiredCount || !expiredFilterBar) {
    return;
  }

  const normalizedQuery = normalizeSearchText(state.expiredSearchQuery);
  const filteredNotices = state.expiredNotices.filter((notice) => {
    const matchesSource = state.selectedExpiredSource === "all" || notice.source === state.selectedExpiredSource;
    const matchesSearch =
      normalizedQuery === "" || normalizeSearchText(notice.title).includes(normalizedQuery);

    return matchesSource && matchesSearch;
  });

  expiredCount.textContent = `${filteredNotices.length}건`;

  for (const button of expiredFilterBar.querySelectorAll(".filter-chip")) {
    button.classList.toggle("active", button.dataset.source === state.selectedExpiredSource);
  }

  if (!state.loadedNotices) {
    expiredGrid.innerHTML = '<p class="empty-state">마감공고를 불러오는 중입니다.</p>';
    return;
  }

  if (filteredNotices.length === 0) {
    expiredGrid.innerHTML = '<p class="empty-state">표시할 마감공고가 없습니다.</p>';
    return;
  }

  expiredGrid.innerHTML = filteredNotices.map(renderNoticeCard).join("");
}

function renderHome() {
  if (
    !homeAlert ||
    !todayNewCount ||
    !activeNoticeCount ||
    !homeBookmarkCount ||
    !followKeywords ||
    !followMatchCount ||
    !homeMatchList
  ) {
    return;
  }

  renderFollowKeywords();

  if (!state.loadedNotices) {
    homeAlert.textContent = "공고 데이터를 불러오는 중입니다.";
    homeMatchList.innerHTML = '<p class="home-empty">관심 공고를 불러오는 중입니다.</p>';
    return;
  }

  const today = getTodayString();
  const todayNotices = state.notices.filter((notice) => notice.posted_at === today);
  const matchedNotices = getFollowMatchedNotices();

  todayNewCount.textContent = String(todayNotices.length);
  activeNoticeCount.textContent = String(state.notices.length);
  homeBookmarkCount.textContent = String(state.bookmarks.length);
  followMatchCount.textContent = `${matchedNotices.length}건`;
  homeAlert.textContent =
    todayNotices.length > 0
      ? `오늘 새로운 공고가 ${todayNotices.length}건 있습니다.`
      : "오늘 새로 등록된 공고는 아직 없습니다.";

  if (state.followKeywords.length === 0) {
    homeMatchList.innerHTML = '<p class="home-empty">Follow 단어를 등록하면 관련 공고가 여기에 표시됩니다.</p>';
    return;
  }

  if (matchedNotices.length === 0) {
    homeMatchList.innerHTML = '<p class="home-empty">현재 지원 가능한 공고 중 follow 단어와 매칭되는 항목이 없습니다.</p>';
    return;
  }

  homeMatchList.innerHTML = matchedNotices.slice(0, 12).map(renderHomeMatchItem).join("");
}

function renderFollowKeywords() {
  if (!followKeywords) {
    return;
  }

  if (state.followKeywords.length === 0) {
    followKeywords.innerHTML = '<span class="follow-placeholder">등록된 단어가 없습니다.</span>';
    return;
  }

  followKeywords.innerHTML = state.followKeywords
    .map(
      (keyword) => `
        <button class="follow-chip" type="button">
          <span>#${escapeHtml(keyword)}</span>
          <span class="follow-remove" data-keyword="${escapeAttribute(keyword)}" aria-label="${escapeAttribute(keyword)} 삭제">×</span>
        </button>
      `,
    )
    .join("");
}

function getFollowMatchedNotices() {
  const keywords = state.followKeywords.map(normalizeSearchText).filter(Boolean);
  if (keywords.length === 0) {
    return [];
  }

  return state.notices.filter(isFollowMatchedNotice);
}

function renderHomeMatchItem(notice) {
  const matchedKeywords = state.followKeywords.filter((keyword) =>
    normalizeSearchText(`${notice.title} ${(notice.keywords ?? []).join(" ")}`).includes(normalizeSearchText(keyword)),
  );
  const deadlineLabel = notice.deadline ? getDeadlineLabel(notice.deadline) : "확인 필요";

  return `
    <article class="home-match-item" data-notice-key="${escapeAttribute(getNoticeKey(notice))}">
      <div class="home-match-main">
        <div class="home-match-meta">
          <span>${escapeHtml(notice.source_display_name ?? notice.source)}</span>
          <span>${escapeHtml(notice.posted_at)}</span>
          <span>${escapeHtml(deadlineLabel)}</span>
        </div>
        <button class="home-match-title" type="button" data-detail-key="${escapeAttribute(getNoticeKey(notice))}">
          ${escapeHtml(notice.title)}
        </button>
      </div>
      <div class="home-match-tags">
        ${matchedKeywords.map((keyword) => `<span>#${escapeHtml(keyword)}</span>`).join("")}
      </div>
    </article>
  `;
}

function renderRecommendedKeywords() {
  if (!recommendedKeywords) {
    return;
  }

  recommendedKeywords.innerHTML = RECOMMENDED_KEYWORDS.map((keyword) => {
    const searchValue = keyword.replace(/^#+/, "");
    return `
      <button class="keyword-chip" type="button" data-keyword="${escapeAttribute(searchValue)}">
        ${escapeHtml(keyword)}
      </button>
    `;
  }).join("");
}

function updateSearchClear() {
  if (!noticeSearchClear) {
    return;
  }

  noticeSearchClear.hidden = state.searchQuery.trim() === "";
}

function updateExpiredSearchClear() {
  if (!expiredSearchClear) {
    return;
  }

  expiredSearchClear.hidden = state.expiredSearchQuery.trim() === "";
}

function renderNoticeCard(notice, options = {}) {
  const deadlineValue = getDisplayDeadline(notice);
  const deadlineLabel = deadlineValue ? getDeadlineLabel(deadlineValue) : "";
  const deadlineText = getDisplayDeadlineText(notice);
  const deadlineTerm = notice.deadline ? "마감일" : notice.ai_deadline ? "AI 추정" : "마감일";
  const noticeKey = getNoticeKey(notice);
  const markLabel = notice.marked ? "북마크 해제" : "북마크";
  const markClass = notice.marked ? "mark-button marked" : "mark-button";
  const cardClass =
    options.highlightFollow && isFollowMatchedNotice(notice) ? "notice-card follow-highlight" : "notice-card";

  return `
    <article class="${cardClass}" data-notice-key="${escapeAttribute(noticeKey)}">
      <div class="notice-card-header">
        <span class="source-pill">${escapeHtml(notice.source_display_name ?? notice.source)}</span>
        <div class="notice-card-actions">
          ${deadlineLabel ? `<span class="deadline">${escapeHtml(deadlineLabel)}</span>` : ""}
          <button class="${markClass}" type="button" data-mark-key="${escapeAttribute(noticeKey)}" aria-label="${markLabel}" title="${markLabel}">
            ★
          </button>
        </div>
      </div>
      <h2 class="notice-title">
        <button type="button" data-detail-key="${escapeAttribute(noticeKey)}">
          ${escapeHtml(notice.title)}
        </button>
      </h2>
      <dl class="notice-meta">
        <div>
          <dt>등록일</dt>
          <dd>${escapeHtml(notice.posted_at)}</dd>
        </div>
        <div>
          <dt>${escapeHtml(deadlineTerm)}</dt>
          <dd>${escapeHtml(deadlineText)}</dd>
        </div>
      </dl>
    </article>
  `;
}

function isFollowMatchedNotice(notice) {
  const keywords = state.followKeywords.map(normalizeSearchText).filter(Boolean);
  if (keywords.length === 0) {
    return false;
  }

  const searchable = normalizeSearchText(`${notice.title} ${(notice.keywords ?? []).join(" ")}`);
  return keywords.some((keyword) => searchable.includes(keyword));
}

document.addEventListener("click", async (event) => {
  const detailButton = event.target.closest("[data-detail-key]");
  if (detailButton) {
    event.preventDefault();
    const notice = findNoticeByKey(detailButton.dataset.detailKey);
    if (notice) {
      openNoticeModal(notice);
    }
    return;
  }

  const cardLink = event.target.closest(".notice-card a, .home-match-item a");
  if (cardLink && !cardLink.classList.contains("notice-origin-link")) {
    event.preventDefault();
    const card = cardLink.closest("[data-notice-key]");
    const notice = findNoticeByKey(card?.dataset.noticeKey);
    if (notice) {
      openNoticeModal(notice);
    }
    return;
  }

  if (event.target.closest("[data-modal-close]")) {
    closeNoticeModal();
    return;
  }

  const button = event.target.closest(".mark-button");
  if (!button) {
    return;
  }

  const notice = [...state.notices, ...state.expiredNotices, ...state.bookmarks].find(
    (item) => getNoticeKey(item) === button.dataset.markKey,
  );
  if (!notice || button.disabled) {
    return;
  }

  button.disabled = true;
  await toggleNoticeMark(notice);
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && noticeModal && !noticeModal.hidden) {
    closeNoticeModal();
  }
});

function openNoticeModal(notice) {
  if (!noticeModal || !noticeModalContent || !noticeModalPanel) {
    window.open(notice.url, "_blank", "noreferrer");
    return;
  }

  noticeModalContent.innerHTML = renderNoticeDetail(notice);
  noticeModal.hidden = false;
  document.body.classList.add("modal-open");
  noticeModalPanel.focus();
}

function closeNoticeModal() {
  if (!noticeModal) {
    return;
  }

  noticeModal.hidden = true;
  document.body.classList.remove("modal-open");
}

function renderNoticeDetail(notice) {
  const deadlineValue = getDisplayDeadline(notice);
  const deadlineText = getDisplayDeadlineText(notice);
  const deadlineLabel = deadlineValue ? getDeadlineLabel(deadlineValue) : "";
  const deadlineTerm = notice.deadline ? "마감일" : notice.ai_deadline ? "AI 추정 마감일" : "마감일";
  const keywords = Array.isArray(notice.keywords) ? notice.keywords.filter(Boolean) : [];
  const detailPoints = Array.isArray(notice.detail_points) ? notice.detail_points.filter(Boolean) : [];
  const summary = String(notice.summary ?? "").trim();
  const fetchedAt = notice.detail_fetched_at ? formatDateTime(notice.detail_fetched_at) : "";

  return `
    <div class="notice-detail-header">
      <span class="source-pill">${escapeHtml(notice.source_display_name ?? notice.source)}</span>
      ${deadlineLabel ? `<span class="deadline">${escapeHtml(deadlineLabel)}</span>` : ""}
    </div>
    <h2 id="notice-modal-title">${escapeHtml(notice.title)}</h2>
    <dl class="notice-detail-meta">
      <div>
        <dt>등록일</dt>
        <dd>${escapeHtml(notice.posted_at)}</dd>
      </div>
      <div>
        <dt>${escapeHtml(deadlineTerm)}</dt>
        <dd>${escapeHtml(deadlineText)}</dd>
      </div>
      ${
        fetchedAt
          ? `<div>
              <dt>상세 수집</dt>
              <dd>${escapeHtml(fetchedAt)}</dd>
            </div>`
          : ""
      }
    </dl>
    <section class="notice-detail-section">
      <h3>요약</h3>
      <p>${escapeHtml(summary || buildFallbackSummary(notice))}</p>
    </section>
    ${
      !notice.deadline && notice.ai_deadline_text
        ? `<section class="notice-detail-section">
            <h3>마감일 근거</h3>
            <p>${escapeHtml(notice.ai_deadline_text)} (${escapeHtml(getAiDeadlineConfidenceLabel(notice.ai_deadline_confidence))})</p>
          </section>`
        : ""
    }
    ${
      detailPoints.length > 0
        ? `<section class="notice-detail-section">
            <h3>핵심 내용</h3>
            <ul class="notice-detail-points">
              ${detailPoints.map((point) => `<li>${escapeHtml(point)}</li>`).join("")}
            </ul>
          </section>`
        : ""
    }
    ${
      keywords.length > 0
        ? `<div class="notice-detail-keywords">
            ${keywords.map((keyword) => `<span>#${escapeHtml(keyword)}</span>`).join("")}
          </div>`
        : ""
    }
    <div class="notice-detail-actions">
      <a class="notice-origin-link" href="${escapeAttribute(notice.url)}" target="_blank" rel="noreferrer">원문 공고 열기</a>
    </div>
  `;
}

function buildFallbackSummary(notice) {
  const source = notice.source_display_name ?? notice.source;
  const deadlineText = getDisplayDeadlineText(notice);
  return `${source}에서 수집한 공고입니다. 상세 요약은 아직 수집되지 않았으며, 등록일은 ${notice.posted_at}, 마감일은 ${deadlineText}입니다. 원문 공고에서 지원 대상과 신청 방법을 확인하세요.`;
}

function findNoticeByKey(key) {
  return [...state.notices, ...state.expiredNotices, ...state.bookmarks].find((item) => getNoticeKey(item) === key);
}

async function toggleNoticeMark(notice) {
  const key = getNoticeKey(notice);
  const previousMarked = Boolean(notice.marked);

  notice.marked = !previousMarked;
  if (!notice.marked) {
    delete notice.mark;
  }
  syncBookmarkState(notice);
  renderNotices();
  renderExpiredNotices();
  renderBookmarks();
  renderHome();

  try {
    const response = await fetch(previousMarked ? "/api/notices/marks/remove" : "/api/notices/marks", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(previousMarked ? { key } : notice),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    if (!previousMarked) {
      notice.marked = true;
      notice.mark = data.mark;
      syncBookmarkState(notice);
      renderNotices();
      renderExpiredNotices();
      renderBookmarks();
      renderHome();
    }
  } catch {
    notice.marked = previousMarked;
    syncBookmarkState(notice);
    renderNotices();
    renderExpiredNotices();
    renderBookmarks();
    renderHome();
  }
}

function syncBookmarkState(notice) {
  const key = getNoticeKey(notice);
  state.notices = state.notices.map((item) => {
    if (getNoticeKey(item) !== key) {
      return item;
    }

    const updated = {
      ...item,
      marked: notice.marked,
    };

    if (notice.mark) {
      updated.mark = notice.mark;
    } else {
      delete updated.mark;
    }

    return updated;
  });
  state.expiredNotices = state.expiredNotices.map((item) => {
    if (getNoticeKey(item) !== key) {
      return item;
    }

    const updated = {
      ...item,
      marked: notice.marked,
    };

    if (notice.mark) {
      updated.mark = notice.mark;
    } else {
      delete updated.mark;
    }

    return updated;
  });

  if (notice.marked) {
    const exists = state.bookmarks.some((item) => getNoticeKey(item) === key);
    if (!exists) {
      state.bookmarks = [notice, ...state.bookmarks];
    } else {
      state.bookmarks = state.bookmarks.map((item) => (getNoticeKey(item) === key ? notice : item));
    }
    return;
  }

  state.bookmarks = state.bookmarks.filter((item) => getNoticeKey(item) !== key);
}

function getDeadlineLabel(deadline) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const deadlineDate = new Date(`${deadline}T00:00:00`);
  const diffDays = Math.ceil((deadlineDate - today) / 86400000);

  if (diffDays < 0) {
    return "마감";
  }
  if (diffDays === 0) {
    return "오늘 마감";
  }
  return `D-${diffDays}`;
}

function getDisplayDeadline(notice) {
  if (notice.deadline) {
    return notice.deadline;
  }

  if (notice.ai_deadline && notice.ai_deadline_confidence === "high") {
    return notice.ai_deadline;
  }

  return "";
}

function getDisplayDeadlineText(notice) {
  if (notice.deadline) {
    return notice.deadline;
  }

  if (notice.ai_deadline && notice.ai_deadline_confidence === "high") {
    return `${notice.ai_deadline} (AI 추정)`;
  }

  return "확인 필요";
}

function getAiDeadlineConfidenceLabel(confidence) {
  if (confidence === "high") {
    return "신뢰도 높음";
  }
  if (confidence === "medium") {
    return "신뢰도 보통";
  }
  if (confidence === "low") {
    return "신뢰도 낮음";
  }
  return "신뢰도 없음";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttribute(value) {
  return escapeHtml(value).replaceAll("`", "&#096;");
}

function normalizeSearchText(value) {
  return String(value ?? "")
    .replaceAll("#", "")
    .trim()
    .toLocaleLowerCase("ko-KR");
}

function normalizeKeyword(value) {
  return String(value ?? "").replaceAll("#", "").trim();
}

function readFollowKeywords() {
  try {
    const raw = localStorage.getItem(FOLLOW_KEYWORDS_STORAGE_KEY);
    const parsed = JSON.parse(raw ?? "[]");
    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed.map(normalizeKeyword).filter(Boolean);
  } catch {
    return [];
  }
}

function writeFollowKeywords() {
  localStorage.setItem(FOLLOW_KEYWORDS_STORAGE_KEY, JSON.stringify(state.followKeywords));
}

function getTodayString() {
  const date = new Date();
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function formatDateTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return date.toLocaleString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getNoticeKey(notice) {
  if (notice.mark?.key) {
    return notice.mark.key;
  }

  if (notice.source === "nia" && notice.title && notice.posted_at) {
    return `${notice.source}:${notice.title}:${notice.posted_at}`;
  }

  if (notice.url) {
    return `${notice.source}:url:${notice.url}`;
  }

  return `${notice.source}:${notice.title ?? ""}:${notice.deadline ?? ""}`;
}
