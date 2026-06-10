const navItems = [...document.querySelectorAll(".nav-item")];
const views = [...document.querySelectorAll("[data-view]")];
const filterBar = document.querySelector(".filter-bar");
const noticeGrid = document.querySelector("#notice-grid");
const noticeCount = document.querySelector("#notice-count");
const dateJump = document.querySelector("#date-jump");
const expiredFilterBar = document.querySelector("#expired-filter-bar");
const expiredGrid = document.querySelector("#expired-grid");
const expiredCount = document.querySelector("#expired-count");
const bookmarkGrid = document.querySelector("#bookmark-grid");
const bookmarkCount = document.querySelector("#bookmark-count");
const noticeSearch = document.querySelector("#notice-search");
const noticeSearchClear = document.querySelector("#notice-search-clear");
const expiredSearch = document.querySelector("#expired-search");
const expiredSearchClear = document.querySelector("#expired-search-clear");
const regionalGrid = document.querySelector("#regional-grid");
const regionalCount = document.querySelector("#regional-count");
const regionalRegionFilter = document.querySelector("#regional-region-filter");
const regionalSearch = document.querySelector("#regional-search");
const regionalSearchClear = document.querySelector("#regional-search-clear");
const shortcutForm = document.querySelector("#shortcut-form");
const shortcutInput = document.querySelector("#shortcut-input");
const shortcutKeywords = document.querySelector("#shortcut-keywords");
const homeAlert = document.querySelector("#home-alert");
const todayNewCount = document.querySelector("#today-new-count");
const activeNoticeCount = document.querySelector("#active-notice-count");
const homeBookmarkCount = document.querySelector("#home-bookmark-count");
const followForm = document.querySelector("#follow-form");
const followInput = document.querySelector("#follow-input");
const followKeywords = document.querySelector("#follow-keywords");
const followMatchCount = document.querySelector("#follow-match-count");
const homeMatchList = document.querySelector("#home-match-list");
const trendTabs = document.querySelector("#trend-tabs");
const trendList = document.querySelector("#trend-list");
const noticeModal = document.querySelector("#notice-modal");
const noticeModalPanel = document.querySelector(".notice-modal-panel");
const noticeModalContent = document.querySelector("#notice-modal-content");

const FOLLOW_KEYWORDS_STORAGE_KEY = "gov_scrapper_follow_keywords";
const SEARCH_SHORTCUTS_STORAGE_KEY = "gov_scrapper_search_shortcuts";

const state = {
  notices: [],
  expiredNotices: [],
  regionalNotices: [],
  bookmarks: [],
  sources: [],
  expiredSources: [],
  regions: [],
  trends: null,
  loadingTrends: false,
  loadedTrends: false,
  selectedSource: "all",
  selectedExpiredSource: "all",
  selectedRegion: "all",
  searchQuery: "",
  expiredSearchQuery: "",
  regionalSearchQuery: "",
  followKeywords: readFollowKeywords(),
  searchShortcuts: readSearchShortcuts(),
  trendMonths: 1,
  loadingNotices: false,
  loadedNotices: false,
  loadingRegionalNotices: false,
  loadedRegionalNotices: false,
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

  if (viewName === "regional" && !state.loadedRegionalNotices) {
    loadRegionalNotices();
  }

  if (viewName === "regional") {
    renderRegionalNotices();
  }

  if (viewName === "bookmarks") {
    renderBookmarks();
  }

  if (viewName === "expired") {
    renderExpiredNotices();
  }

  if (viewName === "home") {
    loadTrends();
    renderHome();
  }
}

window.addEventListener("hashchange", setActiveNav);
setActiveNav();
renderSearchShortcuts();

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

if (shortcutForm && shortcutInput) {
  shortcutForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const keyword = normalizeKeyword(shortcutInput.value);
    if (!keyword) {
      return;
    }

    state.searchShortcuts = [...new Set([...state.searchShortcuts, keyword])];
    shortcutInput.value = "";
    writeSearchShortcuts();
    renderSearchShortcuts();
  });
}

if (regionalSearch) {
  regionalSearch.addEventListener("input", () => {
    state.regionalSearchQuery = regionalSearch.value;
    updateRegionalSearchClear();
    renderRegionalNotices();
  });
}

if (regionalSearchClear && regionalSearch) {
  regionalSearchClear.addEventListener("click", () => {
    state.regionalSearchQuery = "";
    regionalSearch.value = "";
    updateRegionalSearchClear();
    regionalSearch.focus();
    renderRegionalNotices();
  });
}

if (shortcutKeywords) {
  shortcutKeywords.addEventListener("click", (event) => {
    const removeButton = event.target.closest(".shortcut-remove");
    if (removeButton) {
      state.searchShortcuts = state.searchShortcuts.filter((keyword) => keyword !== removeButton.dataset.keyword);
      writeSearchShortcuts();
      renderSearchShortcuts();
      return;
    }

    const button = event.target.closest(".shortcut-chip");
    if (!button || !noticeSearch) {
      return;
    }

    state.searchQuery = appendSearchToken(state.searchQuery, button.dataset.keyword ?? "");
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

if (dateJump) {
  dateJump.addEventListener("click", (event) => {
    const button = event.target.closest("[data-date-target]");
    if (!button) {
      return;
    }

    document.querySelector(`#${button.dataset.dateTarget}`)?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  });
}

if (trendTabs) {
  trendTabs.addEventListener("click", (event) => {
    const button = event.target.closest(".trend-tab");
    if (!button) {
      return;
    }

    state.trendMonths = Number(button.dataset.months || "1");
    renderTrendPanel();
  });
}

if (trendList) {
  trendList.addEventListener("click", (event) => {
    const button = event.target.closest("[data-trend-keyword]");
    if (!button || !noticeSearch) {
      return;
    }

    const keyword = button.dataset.trendKeyword ?? "";
    state.searchQuery = keyword;
    noticeSearch.value = keyword;
    updateSearchClear();
    window.location.hash = "#notices";
    renderNotices();
  });
}

async function loadTrends() {
  if (state.loadingTrends || state.loadedTrends) {
    return;
  }

  state.loadingTrends = true;
  renderTrendPanel();

  try {
    const response = await fetch("/api/trends");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    state.trends = await response.json();
    state.loadedTrends = true;
    renderTrendPanel();
  } catch {
    state.trends = null;
    state.loadedTrends = true;
    renderTrendPanel();
  } finally {
    state.loadingTrends = false;
  }
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
    renderSearchShortcuts();
    renderHome();
    renderTrendPanel();
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

async function loadRegionalNotices() {
  if (state.loadingRegionalNotices) {
    return;
  }

  if (!regionalGrid || !regionalRegionFilter || !regionalCount) {
    return;
  }

  state.loadingRegionalNotices = true;
  regionalGrid.innerHTML = '<p class="empty-state">지역공고를 불러오는 중입니다.</p>';

  try {
    const response = await fetch("/api/regional-notices");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    state.regionalNotices = data.notices ?? [];
    state.regions = data.regions ?? [];
    state.loadedRegionalNotices = true;
    renderRegionalFilters();
    renderRegionalNotices();
  } catch {
    regionalGrid.innerHTML = '<p class="empty-state">지역공고를 불러오지 못했습니다.</p>';
  } finally {
    state.loadingRegionalNotices = false;
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

  filterBar.onclick = (event) => {
    const button = event.target.closest(".filter-chip");
    if (!button) {
      return;
    }

    state.selectedSource = button.dataset.source;
    renderNotices();
  };
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

  expiredFilterBar.onclick = (event) => {
    const button = event.target.closest(".filter-chip");
    if (!button) {
      return;
    }

    state.selectedExpiredSource = button.dataset.source;
    renderExpiredNotices();
  };
}

function renderRegionalFilters() {
  if (!regionalRegionFilter) {
    return;
  }

  const regionButtons = state.regions
    .map(
      (item) => `
        <button class="filter-chip" type="button" data-region="${escapeAttribute(item.region)}">
          ${escapeHtml(item.region)} ${escapeHtml(item.count)}
        </button>
      `,
    )
    .join("");

  regionalRegionFilter.innerHTML = `
    <button class="filter-chip active" type="button" data-region="all">전체</button>
    ${regionButtons}
  `;

  regionalRegionFilter.onclick = (event) => {
    const button = event.target.closest(".filter-chip");
    if (!button) {
      return;
    }

    state.selectedRegion = button.dataset.region;
    renderRegionalNotices();
  };
}

function renderNotices() {
  const searchTokens = parseSearchTokens(state.searchQuery);
  const filteredNotices = state.notices.filter((notice) => {
    const matchesSource = state.selectedSource === "all" || notice.source === state.selectedSource;
    const matchesSearch = matchesNoticeSearch(notice, searchTokens);

    return matchesSource && matchesSearch;
  });

  noticeCount.textContent = `${filteredNotices.length}건`;

  for (const button of filterBar.querySelectorAll(".filter-chip")) {
    button.classList.toggle("active", button.dataset.source === state.selectedSource);
  }

  if (filteredNotices.length === 0) {
    noticeGrid.innerHTML = '<p class="empty-state">표시할 공고가 없습니다.</p>';
    renderDateJump([]);
    return;
  }

  const groupedNotices = groupNoticesByDate(sortNoticesByPostedDate(filteredNotices));
  noticeGrid.innerHTML = renderNoticeDateSections(groupedNotices);
  renderDateJump(groupedNotices);
}

function renderRegionalNotices() {
  if (!regionalGrid || !regionalCount || !regionalRegionFilter) {
    return;
  }

  if (!state.loadedRegionalNotices) {
    regionalGrid.innerHTML = '<p class="empty-state">지역공고를 불러오는 중입니다.</p>';
    regionalCount.textContent = "0건";
    return;
  }

  const searchTokens = parseSearchTokens(state.regionalSearchQuery);
  const filteredNotices = state.regionalNotices.filter((notice) => {
    const region = notice.region || "지역 미상";
    const matchesRegion = state.selectedRegion === "all" || region === state.selectedRegion;
    const matchesSearch = matchesNoticeSearch(notice, searchTokens);
    return matchesRegion && matchesSearch;
  });

  regionalCount.textContent = `${filteredNotices.length}건`;

  for (const button of regionalRegionFilter.querySelectorAll(".filter-chip")) {
    button.classList.toggle("active", button.dataset.region === state.selectedRegion);
  }

  if (filteredNotices.length === 0) {
    regionalGrid.innerHTML = '<p class="empty-state">표시할 지역공고가 없습니다.</p>';
    return;
  }

  const groupedNotices = groupNoticesByDate(sortNoticesByPostedDate(filteredNotices));
  regionalGrid.innerHTML = renderNoticeDateSections(groupedNotices);
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

  const searchTokens = parseSearchTokens(state.expiredSearchQuery);
  const filteredNotices = state.expiredNotices.filter((notice) => {
    const matchesSource = state.selectedExpiredSource === "all" || notice.source === state.selectedExpiredSource;
    const matchesSearch = matchesNoticeSearch(notice, searchTokens);

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
  renderTrendPanel();

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

function renderTrendPanel() {
  if (!trendList || !trendTabs) {
    return;
  }

  for (const button of trendTabs.querySelectorAll(".trend-tab")) {
    button.classList.toggle("active", Number(button.dataset.months) === state.trendMonths);
  }

  if (state.loadingTrends || !state.loadedTrends) {
    trendList.innerHTML = '<p class="home-empty">트렌드를 불러오는 중입니다.</p>';
    return;
  }

  const windowReport = state.trends?.windows?.[String(state.trendMonths)];
  if (!windowReport) {
    trendList.innerHTML = '<p class="home-empty">표시할 키워드 트렌드가 없습니다.</p>';
    return;
  }

  const trends = windowReport.trend_notice_words ?? [];
  const emergingItems = windowReport.developer_emerging_words ?? [];
  const maxCount = Math.max(...trends.map((trend) => trend.count), 1);
  const trendItems = trends
    .map((trend) => {
      const width = Math.max(8, Math.round((trend.count / maxCount) * 100));
      return `
        <button class="trend-item" type="button" data-trend-keyword="${escapeAttribute(trend.keyword)}">
          <span class="trend-name">${escapeHtml(trend.keyword)}</span>
          <span class="trend-bar" aria-hidden="true"><span style="width: ${width}%"></span></span>
          <span class="trend-count">${trend.count}건</span>
        </button>
      `;
    })
    .join("");

  const emergingMarkup =
    emergingItems.length > 0
      ? `
        <div class="trend-emerging">
          <h3>개발 관련 신규 단어 소식</h3>
          <div class="trend-emerging-list">
            ${emergingItems
              .map(
                (item) => `
                  <button class="trend-emerging-chip" type="button" data-trend-keyword="${escapeAttribute(item.keyword)}" title="${escapeAttribute(item.reason)}">
                    ${escapeHtml(item.keyword)}
                  </button>
                `,
              )
              .join("")}
          </div>
        </div>
      `
      : "";

  trendList.innerHTML = `
    <div class="trend-generated">분석 기준 ${escapeHtml(windowReport.notice_count)}건 · ${escapeHtml(formatTrendGeneratedAt(state.trends?.generated_at))}</div>
    <div class="trend-items">${trendItems || '<p class="home-empty">트렌드 공고 단어가 없습니다.</p>'}</div>
    ${emergingMarkup}
  `;
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

function renderSearchShortcuts() {
  if (!shortcutKeywords) {
    return;
  }

  if (state.searchShortcuts.length === 0) {
    shortcutKeywords.innerHTML = '<span class="shortcut-placeholder">자주 쓰는 검색어를 추가해두세요.</span>';
    return;
  }

  shortcutKeywords.innerHTML = state.searchShortcuts.map((keyword) => `
      <span class="shortcut-item">
        <button class="shortcut-chip" type="button" data-keyword="${escapeAttribute(keyword)}">
          ${escapeHtml(keyword)}
        </button>
        <button
          class="shortcut-remove"
          type="button"
          data-keyword="${escapeAttribute(keyword)}"
          aria-label="${escapeAttribute(keyword)} shortcut 삭제"
        >
          ×
        </button>
      </span>
    `).join("");
}

function appendSearchToken(currentValue, keyword) {
  const cleanKeyword = normalizeKeyword(keyword);
  const normalized = normalizeSearchText(keyword);
  if (!normalized) {
    return currentValue;
  }

  const displayTokens = String(currentValue ?? "").trim().split(/\s+/).filter(Boolean);
  const normalizedTokens = displayTokens.map(normalizeSearchText);
  if (normalizedTokens.includes(normalized)) {
    return displayTokens.join(" ");
  }

  return [...displayTokens, cleanKeyword].join(" ");
}

function readSearchShortcuts() {
  try {
    const raw = localStorage.getItem(SEARCH_SHORTCUTS_STORAGE_KEY);
    const parsed = JSON.parse(raw ?? "[]");
    if (!Array.isArray(parsed)) {
      return [];
    }

    return [...new Set(parsed.map(normalizeKeyword).filter(Boolean))];
  } catch {
    return [];
  }
}

function writeSearchShortcuts() {
  localStorage.setItem(SEARCH_SHORTCUTS_STORAGE_KEY, JSON.stringify(state.searchShortcuts));
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

function updateRegionalSearchClear() {
  if (!regionalSearchClear) {
    return;
  }

  regionalSearchClear.hidden = state.regionalSearchQuery.trim() === "";
}

function renderNoticeDateSections(groupedNotices) {
  return groupedNotices
    .map(
      ([date, dateNotices]) => `
        <section class="notice-date-section" id="${escapeAttribute(getDateSectionId(date))}" aria-label="${escapeAttribute(date)} 공고">
          <div class="notice-date-header">
            <h2>${escapeHtml(date)}</h2>
            <span>${dateNotices.length}건</span>
          </div>
          <div class="notice-date-grid">
            ${dateNotices.map((notice) => renderNoticeCard(notice, { highlightFollow: true })).join("")}
          </div>
        </section>
      `,
    )
    .join("");
}

function renderDateJump(groupedNotices) {
  if (!dateJump) {
    return;
  }

  if (groupedNotices.length === 0) {
    dateJump.innerHTML = "";
    return;
  }

  dateJump.innerHTML = groupedNotices
    .map(
      ([date, dateNotices]) => `
        <button type="button" data-date-target="${escapeAttribute(getDateSectionId(date))}" title="${escapeAttribute(`${date} ${dateNotices.length}건`)}">
          ${escapeHtml(formatDateJumpLabel(date))}
        </button>
      `,
    )
    .join("");
}

function getDateSectionId(date) {
  return `notice-date-${String(date).replace(/[^a-zA-Z0-9_-]/g, "-")}`;
}

function formatDateJumpLabel(date) {
  const match = String(date).match(/^\d{4}-(\d{2})-(\d{2})$/);
  if (!match) {
    return String(date);
  }

  return `${match[1]}.${match[2]}`;
}

function groupNoticesByDate(notices) {
  const groups = new Map();
  for (const notice of notices) {
    const date = notice.posted_at || "등록일 미상";
    if (!groups.has(date)) {
      groups.set(date, []);
    }
    groups.get(date).push(notice);
  }

  return [...groups.entries()];
}

function sortNoticesByPostedDate(notices) {
  return notices
    .map((notice, index) => ({ notice, index }))
    .sort((left, right) => {
      const leftDate = Date.parse(left.notice.posted_at || "");
      const rightDate = Date.parse(right.notice.posted_at || "");
      const leftTime = Number.isNaN(leftDate) ? 0 : leftDate;
      const rightTime = Number.isNaN(rightDate) ? 0 : rightDate;

      if (rightTime !== leftTime) {
        return rightTime - leftTime;
      }

      return left.index - right.index;
    })
    .map(({ notice }) => notice);
}

function renderNoticeCard(notice, options = {}) {
  const deadlineValue = getDisplayDeadline(notice);
  const deadlineLabel = deadlineValue ? getDeadlineLabel(deadlineValue) : "";
  const deadlineText = getDisplayDeadlineText(notice);
  const noticeKey = getNoticeKey(notice);
  const markLabel = notice.marked ? "북마크 해제" : "북마크";
  const markClass = notice.marked ? "mark-button marked" : "mark-button";
  const cardClasses = ["notice-card"];
  if (options.highlightFollow && isFollowMatchedNotice(notice)) {
    cardClasses.push("follow-highlight");
  }
  if (notice.posted_at === getTodayString()) {
    cardClasses.push("today-highlight");
  }
  const cardClass = cardClasses.join(" ");

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
          <dd class="${notice.posted_at === getTodayString() ? "posted-today" : ""}">${escapeHtml(notice.posted_at)}</dd>
        </div>
        <div>
          <dt>마감일</dt>
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

  const expireButton = event.target.closest("[data-force-expire-key]");
  if (expireButton) {
    const confirmPanel = noticeModalContent?.querySelector(".notice-expire-confirm");
    if (confirmPanel) {
      confirmPanel.hidden = false;
      confirmPanel.querySelector("[data-confirm-expire]")?.focus();
    }
    return;
  }

  if (event.target.closest("[data-cancel-expire]")) {
    const confirmPanel = noticeModalContent?.querySelector(".notice-expire-confirm");
    if (confirmPanel) {
      confirmPanel.hidden = true;
    }
    return;
  }

  const confirmExpireButton = event.target.closest("[data-confirm-expire]");
  if (confirmExpireButton) {
    const notice = findNoticeByKey(confirmExpireButton.dataset.confirmExpire);
    if (notice) {
      confirmExpireButton.disabled = true;
      await forceExpireNotice(notice);
    }
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
        <dt>마감일</dt>
        <dd>${escapeHtml(deadlineText)}</dd>
      </div>
      ${
        notice.region
          ? `<div>
              <dt>지역</dt>
              <dd>${escapeHtml(notice.region)}</dd>
            </div>`
          : ""
      }
      ${
        notice.agency
          ? `<div>
              <dt>수행기관</dt>
              <dd>${escapeHtml(notice.agency)}</dd>
            </div>`
          : ""
      }
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
      ${
        notice.expired || isRegionalNotice(notice)
          ? ""
          : `<button class="notice-expire-button" type="button" data-force-expire-key="${escapeAttribute(getNoticeKey(notice))}">
              마감시키기
            </button>`
      }
      <a class="notice-origin-link" href="${escapeAttribute(notice.url)}" target="_blank" rel="noreferrer">원문 공고 열기</a>
    </div>
    ${
      notice.expired || isRegionalNotice(notice)
        ? ""
        : `<div class="notice-expire-confirm" hidden>
            <strong>이 공고를 정말 마감 처리할까요?</strong>
            <p>공고조회 목록에서 제거되고 마감공고로 이동합니다.</p>
            <div>
              <button class="notice-expire-confirm-button" type="button" data-confirm-expire="${escapeAttribute(getNoticeKey(notice))}">
                마감 처리
              </button>
              <button class="notice-expire-cancel-button" type="button" data-cancel-expire>
                취소
              </button>
            </div>
          </div>`
    }
  `;
}

function buildFallbackSummary(notice) {
  const source = notice.source_display_name ?? notice.source;
  const deadlineText = getDisplayDeadlineText(notice);
  return `${source}에서 수집한 공고입니다. 상세 요약은 아직 수집되지 않았으며, 등록일은 ${notice.posted_at}, 마감일은 ${deadlineText}입니다. 원문 공고에서 지원 대상과 신청 방법을 확인하세요.`;
}

function isRegionalNotice(notice) {
  return notice.source === "bizinfo_region" || Boolean(notice.region);
}

function findNoticeByKey(key) {
  return [...state.notices, ...state.expiredNotices, ...state.regionalNotices, ...state.bookmarks].find(
    (item) => getNoticeKey(item) === key,
  );
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

async function forceExpireNotice(notice) {
  const key = getNoticeKey(notice);

  try {
    const response = await fetch("/api/notices/expire", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(notice),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const expiredNotice = await response.json();
    state.notices = state.notices.filter((item) => getNoticeKey(item) !== key);
    state.expiredNotices = sortNoticesByPostedDate([
      { ...notice, ...expiredNotice, expired: true },
      ...state.expiredNotices.filter((item) => getNoticeKey(item) !== key),
    ]);
    state.sources = buildSourcesFromNotices(state.notices);
    state.expiredSources = buildSourcesFromNotices(state.expiredNotices);
    if (state.selectedSource !== "all" && !state.sources.some((source) => source.source === state.selectedSource)) {
      state.selectedSource = "all";
    }
    state.bookmarks = state.bookmarks.map((item) =>
      getNoticeKey(item) === key ? { ...item, ...expiredNotice, expired: true } : item,
    );

    closeNoticeModal();
    renderFilters();
    renderExpiredFilters();
    renderNotices();
    renderExpiredNotices();
    renderBookmarks();
    renderHome();
  } catch {
    const confirmPanel = noticeModalContent?.querySelector(".notice-expire-confirm");
    const confirmButton = confirmPanel?.querySelector("[data-confirm-expire]");
    if (confirmButton) {
      confirmButton.disabled = false;
    }
    if (confirmPanel) {
      confirmPanel.classList.add("error");
      confirmPanel.querySelector("p").textContent = "마감 처리에 실패했습니다. 잠시 후 다시 시도하세요.";
    }
  }
}

function buildSourcesFromNotices(notices) {
  return Object.entries(
    notices.reduce((acc, notice) => {
      acc[notice.source] = notice.source_display_name ?? notice.source;
      return acc;
    }, {}),
  )
    .map(([source, displayName]) => ({ source, display_name: displayName }))
    .sort((left, right) => left.display_name.localeCompare(right.display_name, "ko-KR"));
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

function parseSearchTokens(value) {
  return String(value ?? "")
    .split(/\s+/)
    .map(normalizeSearchText)
    .filter(Boolean);
}

function matchesNoticeSearch(notice, searchTokens) {
  if (searchTokens.length === 0) {
    return true;
  }

  const searchable = normalizeSearchText(
    [
      notice.title,
      notice.region,
      notice.agency,
      notice.department,
      notice.summary,
      notice.ai_deadline_text,
      ...(notice.keywords ?? []),
      ...(notice.detail_points ?? []),
    ].join(" "),
  );

  return searchTokens.some((token) => searchable.includes(token));
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

function formatTrendGeneratedAt(value) {
  if (!value) {
    return "아직 생성 전";
  }

  return formatDateTime(value);
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
