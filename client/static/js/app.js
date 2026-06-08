const navItems = [...document.querySelectorAll(".nav-item")];
const views = [...document.querySelectorAll("[data-view]")];
const filterBar = document.querySelector(".filter-bar");
const noticeGrid = document.querySelector("#notice-grid");
const noticeCount = document.querySelector("#notice-count");
const noticeSearch = document.querySelector("#notice-search");
const recommendedToggle = document.querySelector("#recommended-toggle");
const recommendedKeywords = document.querySelector("#recommended-keywords");

const RECOMMENDED_KEYWORDS = ["#AI", "#보안", "#양자", "#R&D", "#클라우드"];

const state = {
  notices: [],
  sources: [],
  selectedSource: "all",
  searchQuery: "",
  recommendedVisible: false,
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

  if (viewName === "notices" && state.notices.length === 0) {
    loadNotices();
  }
}

window.addEventListener("hashchange", setActiveNav);
setActiveNav();

if (noticeSearch) {
  noticeSearch.addEventListener("input", () => {
    state.searchQuery = noticeSearch.value;
    renderNotices();
  });
}

if (recommendedToggle && recommendedKeywords) {
  recommendedToggle.addEventListener("click", () => {
    state.recommendedVisible = !state.recommendedVisible;
    renderRecommendedKeywords();
  });

  recommendedKeywords.addEventListener("click", (event) => {
    const button = event.target.closest(".keyword-chip");
    if (!button || !noticeSearch) {
      return;
    }

    state.searchQuery = button.dataset.keyword ?? "";
    noticeSearch.value = state.searchQuery;
    renderNotices();
  });
}

async function loadNotices() {
  if (!noticeGrid || !filterBar || !noticeCount) {
    return;
  }

  noticeGrid.innerHTML = '<p class="empty-state">공고를 불러오는 중입니다.</p>';

  try {
    const response = await fetch("/api/notices");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    state.notices = data.notices ?? [];
    state.sources = data.sources ?? [];
    renderFilters();
    renderRecommendedKeywords();
    renderNotices();
  } catch {
    noticeGrid.innerHTML = '<p class="empty-state">공고를 불러오지 못했습니다.</p>';
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

function renderRecommendedKeywords() {
  if (!recommendedToggle || !recommendedKeywords) {
    return;
  }

  recommendedToggle.classList.toggle("active", state.recommendedVisible);
  recommendedToggle.setAttribute("aria-expanded", String(state.recommendedVisible));
  recommendedKeywords.hidden = !state.recommendedVisible;

  recommendedKeywords.innerHTML = RECOMMENDED_KEYWORDS.map((keyword) => {
    const searchValue = keyword.replace(/^#+/, "");
    return `
      <button class="keyword-chip" type="button" data-keyword="${escapeAttribute(searchValue)}">
        ${escapeHtml(keyword)}
      </button>
    `;
  }).join("");
}

function renderNoticeCard(notice) {
  const deadlineLabel = notice.deadline ? getDeadlineLabel(notice.deadline) : "마감일 없음";
  const deadlineClass = notice.deadline ? "deadline" : "deadline muted";

  return `
    <article class="notice-card">
      <div class="notice-card-header">
        <span class="source-pill">${escapeHtml(notice.source_display_name ?? notice.source)}</span>
        <span class="${deadlineClass}">${escapeHtml(deadlineLabel)}</span>
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
