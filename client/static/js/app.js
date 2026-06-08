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

const RECOMMENDED_KEYWORDS = ["#AI", "#보안", "#양자", "#R&D", "#클라우드"];

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
  loadingNotices: false,
  loadedNotices: false,
};

function setActiveNav() {
  const currentHash = window.location.hash || "#bookmarks";
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
    (viewName === "notices" || viewName === "bookmarks" || viewName === "expired") &&
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

  noticeGrid.innerHTML = filteredNotices.map(renderNoticeCard).join("");
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

function renderNoticeCard(notice) {
  const deadlineLabel = notice.deadline ? getDeadlineLabel(notice.deadline) : "마감일 없음";
  const deadlineClass = notice.deadline ? "deadline" : "deadline muted";
  const noticeKey = getNoticeKey(notice);
  const markLabel = notice.marked ? "북마크 해제" : "북마크";
  const markClass = notice.marked ? "mark-button marked" : "mark-button";

  return `
    <article class="notice-card" data-notice-key="${escapeAttribute(noticeKey)}">
      <div class="notice-card-header">
        <span class="source-pill">${escapeHtml(notice.source_display_name ?? notice.source)}</span>
        <div class="notice-card-actions">
          <span class="${deadlineClass}">${escapeHtml(deadlineLabel)}</span>
          <button class="${markClass}" type="button" data-mark-key="${escapeAttribute(noticeKey)}" aria-label="${markLabel}" title="${markLabel}">
            ★
          </button>
        </div>
      </div>
      <h2 class="notice-title">
        <a href="${escapeAttribute(notice.url)}" target="_blank" rel="noreferrer">
          ${escapeHtml(notice.title)}
        </a>
      </h2>
      <dl class="notice-meta">
        <div>
          <dt>등록일</dt>
          <dd>${escapeHtml(notice.posted_at)}</dd>
        </div>
        <div>
          <dt>마감일</dt>
          <dd>${escapeHtml(notice.deadline ?? "-")}</dd>
        </div>
      </dl>
    </article>
  `;
}

document.addEventListener("click", async (event) => {
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

async function toggleNoticeMark(notice) {
  const key = getNoticeKey(notice);
  const previousMarked = Boolean(notice.marked);

  notice.marked = !previousMarked;
  if (!notice.marked) {
    delete notice.mark;
  }
  syncBookmarkState(notice);
  renderNotices();
  renderBookmarks();

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
      renderBookmarks();
    }
  } catch {
    notice.marked = previousMarked;
    syncBookmarkState(notice);
    renderNotices();
    renderBookmarks();
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
