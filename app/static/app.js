const state = { politicians: [], profiles: [], profileAsOf: "", records: [], selected: null, detail: null, discoveryComplete: true, discoveryIssue: null, analysisReady: null, analysisInFlight: false, analysisError: null };
const elapsedTimers = new Map();
const $ = (id) => document.getElementById(id);
const chatHistory = [];
let selectionRequest = 0;

async function getJSON(url, options) {
  const response = await fetch(url, options);
  let body;
  try {
    body = await response.json();
  } catch (_) {
    throw new Error(response.ok
      ? "The service returned an unreadable response. Please try again."
      : `The service could not complete that request (HTTP ${response.status}). Please try again.`);
  }
  if (!response.ok) throw new Error(body.detail || "The request failed.");
  return body;
}

async function getJSONWithTimeout(url, timeoutMs) {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await getJSON(url, { signal: controller.signal });
  } finally {
    window.clearTimeout(timer);
  }
}

function analysisUnavailableMessage() {
  return "AI analysis is not configured for this service. Add OPENAI_API_KEY (or PORTKEY_API_KEY) to its environment settings; speech browsing will still work.";
}

function toast(message) {
  const element = $("toast");
  element.textContent = message;
  element.classList.add("show");
  setTimeout(() => element.classList.remove("show"), 5000);
}

function setCorpusProgress(status, label = "", detail = "") {
  const panel = $("corpus-progress");
  const icon = $("corpus-progress-icon");
  const track = $("corpus-progress-track");
  panel.classList.remove("loading", "complete", "unavailable", "error", "hidden");
  if (status === "hidden") {
    panel.classList.add("hidden");
    track.removeAttribute("aria-valuenow");
    return;
  }
  panel.classList.add(status);
  $("corpus-progress-label").textContent = label;
  $("corpus-progress-detail").textContent = detail;
  icon.textContent = status === "complete" ? "✓" : status === "unavailable" || status === "error" ? "!" : "";
  track.setAttribute("aria-valuetext", `${label}. ${detail}`.trim());
  if (status === "complete") track.setAttribute("aria-valuenow", "100");
  else track.removeAttribute("aria-valuenow");
}

function formatElapsed(seconds) {
  const minutes = Math.floor(seconds / 60);
  const remainder = String(seconds % 60).padStart(2, "0");
  return `${String(minutes).padStart(2, "0")}:${remainder} elapsed`;
}

function startElapsedTimer(id) {
  stopElapsedTimer(id);
  const element = $(id);
  if (!element) return;
  const startedAt = Date.now();
  const update = () => {
    element.textContent = formatElapsed(Math.floor((Date.now() - startedAt) / 1000));
  };
  update();
  elapsedTimers.set(id, window.setInterval(update, 1000));
}

function stopElapsedTimer(id) {
  const timer = elapsedTimers.get(id);
  if (timer) window.clearInterval(timer);
  elapsedTimers.delete(id);
}

function syncAnalysisControls() {
  const speechButton = $("analyze");
  const topicButton = $("trace-phrase");
  if (!speechButton || !topicButton) return;
  const hasSpeech = Boolean(state.selected);
  const modelUnavailable = state.analysisReady === false;
  const topic = $("phrase-input").value.trim();
  speechButton.disabled = !hasSpeech || modelUnavailable || state.analysisInFlight;
  topicButton.disabled = !hasSpeech || modelUnavailable || !state.discoveryComplete || topic.length < 2 || state.analysisInFlight;

  const speechNote = $("analysis-availability");
  speechNote.classList.toggle("hidden", !state.analysisError && !modelUnavailable && !state.analysisInFlight);
  speechNote.textContent = state.analysisError
    || (modelUnavailable ? analysisUnavailableMessage()
      : state.analysisInFlight ? "An analysis is in progress. The timer below shows how long it has taken."
        : "");

  const topicNote = $("topic-action-status");
  if (!topicNote) return;
  topicNote.textContent = state.analysisError
    || (modelUnavailable ? analysisUnavailableMessage()
      : !hasSpeech ? "Choose a speech before searching for related wording."
        : state.analysisInFlight ? "Civic Lens is working on this request. The timer below shows how long it has taken."
          : !state.discoveryComplete ? "Civic Lens is still searching public sources. You can analyze this speech now; topic comparisons will be available when the search finishes."
            : topic.length < 2 ? "Enter a topic or choose a highlighted term to compare related wording."
              : state.discoveryIssue === "timeout" ? "Public-source search exceeded one minute. Comparisons use the statements already loaded."
                : state.discoveryIssue === "error" ? "Civic Lens could not refresh public sources. Comparisons use the statements already loaded."
                  : state.discoveryIssue === "unavailable" ? "Public-source search is unavailable. Comparisons use transcripts already collected."
                    : "Civic Lens compares your topic with related terms in the selected source set.");
}

function formatDate(iso) {
  return new Date(iso + "T12:00:00").toLocaleDateString(undefined, {
    year: "numeric", month: "long", day: "numeric"
  });
}

const STATE_NAMES = ["Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming", "District of Columbia"];
const STATE_ABBREVIATIONS = new Set("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC".split(" "));

function splitVenue(venue = "") {
  const clean = String(venue).replace(/\s*\((?:\d{4}\s+)?(?:U\.S\.\s+)?(?:House|Senate)?\s*campaign[^)]*\)\s*$/i, "").trim();
  const parts = clean.split(",").map((part) => part.trim()).filter(Boolean);
  const stateIndex = parts.findIndex((part) => STATE_NAMES.some((name) => part.toLocaleLowerCase() === name.toLocaleLowerCase()) || STATE_ABBREVIATIONS.has(part.toUpperCase()));
  if (stateIndex < 0) return { event: clean || "Public remarks", place: "Location not listed by source" };
  const placeStart = Math.max(0, stateIndex - 1);
  return {
    event: parts.slice(0, placeStart).join(", ") || "Public remarks",
    place: parts.slice(placeStart).join(", ") || "Location not listed by source"
  };
}

async function loadPeople() {
  const data = await getJSON("/api/politicians");
  state.politicians = data.politicians || [];
  state.profiles = data.profiles || [];
  state.profileAsOf = data.as_of || "";
  const options = $("politician");
  options.replaceChildren(new Option("Select a politician.", ""));
  for (const name of state.politicians) {
    const profile = state.profiles.find((item) => item.name === name);
    const label = profile ? profile.display_name : name;
    options.append(new Option(label, name));
  }
  try {
    const health = await getJSON("/api/health");
    state.analysisReady = health.analysis_ready === true;
    syncAnalysisControls();
  } catch (_) {
    state.analysisReady = null;
    syncAnalysisControls();
  }
}

function getPoliticianProfile(name) {
  return state.profiles.find((profile) => profile.name.toLocaleLowerCase() === String(name || "").toLocaleLowerCase()) || null;
}

function selectedPoliticianName() {
  return $("politician").value.trim();
}

function renderPoliticianProfile(profile) {
  const panel = $("politician-profile");
  if (!profile) {
    panel.classList.add("hidden");
    return;
  }
  panel.classList.remove("hidden");
  const photo = $("profile-photo");
  const initials = $("profile-initials");
  const credit = $("profile-photo-credit");
  const nameForInitials = profile.display_name.replace(/\s*\([^)]+\)\s*$/, "");
  initials.textContent = nameForInitials.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toLocaleUpperCase();
  initials.classList.add("hidden");
  photo.classList.remove("hidden");
  photo.alt = "Portrait of " + nameForInitials;
  photo.onerror = () => {
    photo.classList.add("hidden");
    initials.classList.remove("hidden");
    credit.classList.add("hidden");
  };
  if (profile.photo_url) {
    photo.src = profile.photo_url;
    credit.href = profile.photo_credit_url || profile.photo_url;
    credit.classList.remove("hidden");
  } else {
    photo.classList.add("hidden");
    initials.classList.remove("hidden");
    credit.classList.add("hidden");
  }
  $("profile-as-of").textContent = state.profileAsOf ? `as of ${state.profileAsOf}` : "current status";
  $("profile-name").textContent = profile.display_name;
  $("profile-summary").textContent = profile.summary;
  $("profile-party").textContent = `${profile.party_name} (${profile.party_code})`;
  $("profile-state").textContent = profile.state;
  $("profile-office").textContent = profile.office;
  $("profile-active").textContent = profile.office_status;
  $("profile-last-ran").textContent = profile.last_ran;
  $("profile-running-now").textContent = profile.running_now;
  const status = $("profile-status");
  status.textContent = profile.active ? "Currently serving" : "Former officeholder";
  status.classList.toggle("former", !profile.active);
  const focus = $("profile-focus-areas");
  focus.replaceChildren();
  for (const area of profile.focus_areas || []) {
    const tag = document.createElement("span");
    tag.textContent = area;
    focus.append(tag);
  }
  const sources = $("profile-sources");
  sources.replaceChildren();
  for (const source of profile.sources || []) {
    const link = document.createElement("a");
    link.href = source.url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = source.label;
    sources.append(link);
  }
}

function renderSpeechOptions(records) {
  const select = $("speech");
  const selectedId = select.value;
  select.replaceChildren(new Option("Select a date and statement.", ""));
  for (const record of records) {
    const dateLabel = /retrieval date used/i.test(record.transcript_status || "")
      ? "Speech date unavailable"
      : /publication date may differ/i.test(record.transcript_status || "")
        ? `Publisher date ${formatDate(record.date)}`
        : formatDate(record.date);
    const source = record.source_label || (record.source_category === "campaign" ? "Public speech or interview" : "Congressional Record");
    const pages = record.source_page_start ? `pages ${record.source_page_start}–${record.source_page_end}` : "source text";
    select.add(new Option(`${dateLabel} · ${source} · ${pages}`, record.record_id));
  }
  if (records.some((record) => record.record_id === selectedId)) select.value = selectedId;
  select.disabled = records.length === 0;
}

async function loadRecords() {
  const requestNumber = ++selectionRequest;
  setAnalysisExpanded(false);
  const name = selectedPoliticianName();
  state.records = [];
  $("speech").replaceChildren(new Option("Choose a politician first.", ""));
  const selectedProfile = getPoliticianProfile(name);
  if (selectedProfile) $("politician").value = selectedProfile.name;
  renderPoliticianProfile(selectedProfile);
  state.selected = null;
  state.detail = null;
  state.records = [];
  state.discoveryComplete = false;
  state.discoveryIssue = null;
  state.analysisError = null;
  stopElapsedTimer("corpus-progress-timer");
  $("remark").classList.add("hidden");
  $("topic-explorer").classList.add("hidden");
  $("analysis-controls").classList.add("hidden");
  $("phrase-results").classList.add("hidden");
  $("analysis").classList.add("hidden");
  $("analysis-empty").classList.remove("hidden");
  $("empty").classList.remove("hidden");
  $("phrase-input").value = "";
  delete $("analyze").dataset.topic;
  $("speech").replaceChildren(new Option(name ? "Civic Lens is loading statements." : "Choose a politician first.", ""));
  $("speech").disabled = true;
  $("analyze").disabled = true;
  $("source-leads").classList.add("hidden");
  $("source-leads").open = false;
  $("source-leads-content").replaceChildren();
  $("source-leads-summary").textContent = "Civic Lens is checking additional public speech sources.";
  if (!name) {
    state.discoveryComplete = true;
    $("coverage").textContent = "Select a politician to see the statements currently available for that person.";
    setCorpusProgress("hidden");
    stopElapsedTimer("corpus-progress-timer");
    syncAnalysisControls();
    return;
  }
  const discoveryStartedAt = Date.now();
  startElapsedTimer("corpus-progress-timer");
  $("coverage").textContent = "Civic Lens is searching public speech sources and loading Congressional Record statements.";
  setCorpusProgress("loading", "Civic Lens is loading the speech corpus.", "This search can take up to one minute. The timer shows how long it has been running.");
  const fetchCorpusData = () => getJSONWithTimeout(
    "/api/records?politician=" + encodeURIComponent(name),
    Math.max(1, 60000 - (Date.now() - discoveryStartedAt))
  );
  try {
    let data = await fetchCorpusData();
    while (requestNumber === selectionRequest) {
      state.records = data.records;
      renderSpeechOptions(data.records);
      const counts = data.source_counts || {};
      const publicCount = counts.public_transcripts || 0;
      const congressionalCount = counts.congressional_record || 0;
      if (data.search_status === "loading") {
        state.discoveryComplete = false;
        $("coverage").textContent = `Civic Lens is checking the listed election cycles. It has loaded ${publicCount} public transcripts and ${congressionalCount} Congressional Record statements so far.`;
        setCorpusProgress("loading", "Civic Lens is searching public sources.", `It has loaded ${publicCount} public transcripts and ${congressionalCount} Congressional Record statements so far. The search stops waiting after one minute.`);
        renderLeads({ cache_status: "loading" });
        syncAnalysisControls();
        if (Date.now() - discoveryStartedAt >= 60000) {
          state.discoveryComplete = true;
          state.discoveryIssue = "timeout";
          stopElapsedTimer("corpus-progress-timer");
          $("coverage").textContent = "Public-source search took longer than one minute. You can use the statements already loaded and choose the politician again to retry.";
          setCorpusProgress("unavailable", "Civic Lens could not finish the public-source search.", `It loaded ${publicCount} public transcripts and ${congressionalCount} Congressional Record statements. Topic comparisons use the statements already available.`);
          renderLeads({ cache_status: "search unavailable" });
          syncAnalysisControls();
          break;
        }
        await new Promise((resolve) => setTimeout(resolve, 1500));
        if (requestNumber !== selectionRequest) return;
        data = await fetchCorpusData();
        continue;
      }
      state.discoveryComplete = true;
      state.discoveryIssue = data.search_status === "unavailable" ? "unavailable" : null;
      stopElapsedTimer("corpus-progress-timer");
      $("coverage").textContent = data.search_status === "unavailable"
        ? `Public-source search is unavailable, so Civic Lens is showing ${publicCount} public transcripts and ${congressionalCount} Congressional Record statements already collected.`
        : `Civic Lens found ${publicCount} public, campaign, or interview transcripts and ${congressionalCount} Congressional Record statements. Public-source search is complete.`;
      setCorpusProgress(
        data.search_status === "unavailable" ? "unavailable" : "complete",
        data.search_status === "unavailable" ? "Civic Lens is using the transcripts already collected." : "Civic Lens has finished loading the speech corpus.",
        `Civic Lens has ${publicCount} public, campaign, or interview transcripts and ${congressionalCount} Congressional Record statements available.`
      );
      renderLeads(data.discovery || {});
      syncAnalysisControls();
      if (!data.records.length) toast("No statements were found in the local collection or public source search.");
      break;
    }
  } catch (error) {
    if (requestNumber !== selectionRequest) return;
    state.discoveryComplete = true;
    const searchTimedOut = Date.now() - discoveryStartedAt >= 60000;
    state.discoveryIssue = searchTimedOut ? "timeout" : "error";
    stopElapsedTimer("corpus-progress-timer");
    const loadedCount = state.records.length;
    $("coverage").textContent = searchTimedOut
      ? "Public-source search took longer than one minute. Statements already loaded remain available below."
      : loadedCount
        ? `Civic Lens could not refresh public sources. It has kept ${loadedCount} statements already loaded, which remain available below.`
        : "Civic Lens could not load statements. Check the connection and choose this politician again.";
    setCorpusProgress(searchTimedOut ? "unavailable" : "error",
      searchTimedOut ? "Public-source search reached its one-minute limit." : "Civic Lens could not refresh the speech corpus.",
      loadedCount
        ? "You can still read and analyze statements already loaded on this page."
        : "Check the connection, then choose this politician again.");
    if (loadedCount) renderLeads({ cache_status: "search unavailable" });
    else $("source-leads").classList.add("hidden");
    if (!loadedCount) $("speech").replaceChildren(new Option("Statements could not load.", ""));
    syncAnalysisControls();
    toast(error.message || "Civic Lens could not load the statements. Please try again.");
  }
}

function renderLeads(discovery) {
  const container = $("source-leads");
  const content = $("source-leads-content");
  const summary = $("source-leads-summary");
  content.replaceChildren();
  const leads = discovery.leads || [];
  const count = discovery.new_transcripts || 0;
  if (discovery.cache_status === "search unavailable") {
    summary.textContent = "Civic Lens could not reach public speech sources.";
    content.textContent = "The transcripts already collected are still available in the speech list.";
    container.classList.remove("hidden");
    return;
  }
  if (String(discovery.cache_status || "").startsWith("loading")) {
    summary.textContent = "Civic Lens is searching this politician’s listed election cycles.";
    content.textContent = "Civic Lens will add complete transcripts from public sources to the speech list.";
    container.classList.remove("hidden");
    return;
  }
  const additionalLeads = leads.filter((lead) => !lead.record_id);
  if (!additionalLeads.length) {
    container.classList.add("hidden");
    return;
  }
  summary.textContent = `Civic Lens added ${count} transcripts and found ${additionalLeads.length} additional source pages.`;
  const heading = document.createElement("p");
  heading.className = "source-leads-help";
  heading.textContent = "Load a result to add its transcript to the speech list. Civic Lens skips pages without a complete speech.";
  content.append(heading);
  for (const lead of additionalLeads.slice(0, 8)) {
    const row = document.createElement("div");
    row.className = "source-lead";
    const title = document.createElement("strong");
    title.textContent = lead.title || "Public speech source";
    row.append(title);
    const status = document.createElement("small");
    status.className = "source-lead-status";
    const sourceStatus = lead.status || "Civic Lens can retrieve this source page.";
    status.textContent = /does not identify a transcript|no full transcript text was extractable|short excerpt or article text/i.test(sourceStatus)
      ? "Full speech text was not found on this page."
      : /google news lead/i.test(sourceStatus)
        ? "Search result. Open the publisher page to check for a transcript."
        : /could not be fetched|could not be retrieve/i.test(sourceStatus)
          ? "This page could not be loaded. Try its original source link."
          : /review boundaries/i.test(sourceStatus)
            ? "Transcript loaded. Check its source and surrounding context."
            : sourceStatus;
    const actions = document.createElement("div");
    actions.className = "source-lead-actions";
    const load = document.createElement("button");
    load.type = "button";
    load.className = "source-lead-load";
    load.textContent = lead.record_id ? "Read the transcript in Civic Lens." : "Load the transcript into Civic Lens.";
    load.addEventListener("click", () => openPublicLead(lead, load, status));
    actions.append(load);
    const candidate = lead.source_url || lead.news_url;
    try {
      const url = new URL(candidate);
      if (url.protocol === "https:" || url.protocol === "http:") {
        const citation = document.createElement("a");
        citation.href = url.href;
        citation.target = "_blank";
        citation.rel = "noopener noreferrer";
        citation.textContent = "Original source ↗";
        actions.append(citation);
      }
    } catch (_) {}
    row.append(status, actions);
    content.append(row);
  }
  container.classList.remove("hidden");
}

async function openPublicLead(lead, button, status) {
  const politician = selectedPoliticianName();
  button.disabled = true;
  button.textContent = "Civic Lens is loading the transcript.";
  status.textContent = "Civic Lens is fetching the source page and extracting the speech text.";
  try {
    let record = state.records.find((item) => item.record_id === lead.record_id);
    if (!record) {
      const params = new URLSearchParams({
        politician,
        source_url: lead.news_url || lead.source_url
      });
      const result = await getJSON("/api/public-speeches/import?" + params.toString(), { method: "POST" });
      record = result.record;
    }
    if (!state.records.some((item) => item.record_id === record.record_id)) state.records.unshift(record);
    let option = [...$("speech").options].find((item) => item.value === record.record_id);
    if (!option) {
      option = document.createElement("option");
      option.value = record.record_id;
      option.textContent = `${formatDate(record.date)} · Public speech or interview · transcript`;
      $("speech").append(option);
    }
    $("speech").value = record.record_id;
    status.textContent = "The transcript text is shown below in the Civic Lens reader.";
    button.textContent = "The transcript is open in Civic Lens.";
    await loadDetail(record.record_id);
    $("remark").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    status.textContent = error.message || "Civic Lens could not retrieve a complete transcript from this page. Please try the original source link.";
    button.textContent = "Try loading the transcript again.";
    button.disabled = false;
  }
}

function normalizeWithMap(value) {
  let normalized = "";
  const positions = [];
  let inWhitespace = false;
  for (let i = 0; i < value.length; i += 1) {
    if (/\s/.test(value[i])) {
      if (!inWhitespace) {
        normalized += " ";
        positions.push(i);
        inWhitespace = true;
      }
    } else {
      normalized += value[i];
      positions.push(i);
      inWhitespace = false;
    }
  }
  return { normalized, positions };
}

function appendHighlightedText(element, text, phrases, clickablePhrases = []) {
  const mapped = normalizeWithMap(text);
  const searchable = mapped.normalized.toLocaleLowerCase();
  const ranges = [];
  const addRanges = (items, clickable) => {
    for (const item of items) {
    const phrase = typeof item === "string" ? item : item.phrase;
    const needle = String(phrase || "").replace(/\s+/g, " ").trim().toLocaleLowerCase();
    if (needle.length < 3) continue;
    let start = 0;
    while ((start = searchable.indexOf(needle, start)) !== -1) {
      const end = start + needle.length;
      ranges.push({
        start: mapped.positions[start],
        end: mapped.positions[end] ?? text.length,
        clickable,
        phrase: String(phrase),
        topic: typeof item === "string" ? "" : String(item.topic || "")
      });
      start = end;
    }
    }
  };
  addRanges(clickablePhrases, true);
  addRanges(phrases, false);
  ranges.sort((a, b) => a.start - b.start || Number(b.clickable) - Number(a.clickable) || b.end - a.end);
  let cursor = 0;
  for (const range of ranges) {
    if (range.start < cursor) continue;
    element.append(document.createTextNode(text.slice(cursor, range.start)));
    const mark = document.createElement("mark");
    mark.className = range.clickable ? "source-highlight phrase-highlight" : "source-highlight";
    mark.textContent = text.slice(range.start, range.end);
    if (range.clickable) {
      mark.dataset.phrase = range.phrase;
      mark.dataset.topic = range.topic;
      mark.tabIndex = 0;
      mark.setAttribute("role", "button");
      mark.setAttribute("aria-label", (range.topic ? range.topic + ": " : "") + range.phrase + ". Click to analyze this topic across earlier statements.");
      mark.title = (range.topic ? range.topic + " · " : "") + "Click to read the topic analysis";
    }
    element.append(mark);
    cursor = range.end;
  }
  element.append(document.createTextNode(text.slice(cursor)));
}

function renderPhraseIndex(phrases = []) {
  const list = $("phrase-list");
  list.replaceChildren();
  const groups = new Map();
  for (const item of phrases) {
    if (!item.topic) continue;
    if (!groups.has(item.topic)) groups.set(item.topic, []);
    if (!groups.get(item.topic).includes(item.phrase)) groups.get(item.topic).push(item.phrase);
  }
  if (!groups.size) {
    const empty = document.createElement("p");
    empty.className = "phrase-list-empty";
    empty.textContent = "No listed policy keywords were found in this transcript. You can still search a topic above.";
    list.append(empty);
    return;
  }
  for (const [topic, cues] of groups) {
    if (topic === "Statistical claim") continue;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "phrase-option";
    button.title = "Analyze " + topic.toLowerCase() + " in this speech and compare earlier statements";
    const label = document.createElement("span");
    label.className = "phrase-option-topic";
    label.textContent = topic;
    const cueList = document.createElement("span");
    cueList.className = "phrase-option-text";
    cueList.textContent = `Highlighted phrases: ${cues.slice(0, 4).map((cue) => `“${cue}”`).join(" · ")}.`;
    button.append(label, cueList);
    button.addEventListener("click", () => {
      $("phrase-input").value = topic;
      $("analyze").dataset.topic = topic;
      tracePhrase();
    });
    list.append(button);
  }
}

function renderTranscript(text, highlights = [], clickablePhrases = []) {
  const container = $("text");
  container.replaceChildren();
  const paragraphs = text.replace(/\r\n?/g, "\n").trim().split(/\n\s*\n/);
  for (const paragraph of paragraphs) {
    if (!paragraph.trim()) continue;
    const element = document.createElement("p");
    element.className = "transcript-paragraph";
    appendHighlightedText(element, paragraph, highlights, clickablePhrases);
    container.append(element);
  }
}

async function loadDetail(recordId) {
  if (!recordId) return;
  setAnalysisExpanded(false);
  try {
    const data = await getJSON("/api/records/" + encodeURIComponent(recordId));
    state.detail = data;
    state.selected = data.record;
    state.analysisError = null;
    $("empty").classList.add("hidden");
    $("analysis-empty").classList.add("hidden");
    $("analysis").classList.add("hidden");
    $("phrase-results").classList.add("hidden");
    $("remark").classList.remove("hidden");
    $("topic-explorer").classList.remove("hidden");
    $("analysis-controls").classList.remove("hidden");
    const select = $("speech");
    if (![...select.options].some((option) => option.value === recordId)) {
      const source = data.record.source_category === "campaign" ? "Public speech or interview" : "Congressional Record";
      select.add(new Option(`${formatDate(data.record.date)} · ${source} · source text`, recordId));
    }
    select.value = recordId;
    const dateLabel = /retrieval date used/i.test(data.record.transcript_status || "")
      ? "Speech date unavailable"
      : /publication date may differ/i.test(data.record.transcript_status || "")
        ? `Publisher date ${formatDate(data.record.date)}`
        : formatDate(data.record.date);
    $("date").textContent = dateLabel + " · " +
      (data.record.source_category === "campaign" ? "Public / campaign remarks" : "Congressional Record");
    const venue = splitVenue(data.record.venue);
    $("title").textContent = venue.event || (data.record.politician + " · statement");
    $("venue-location").textContent = venue.place;
    $("source").href = data.record.source_url;
    const sourceStatus = (data.record.transcript_status || "").toLowerCase();
    $("source-kind").textContent = /partial|excerpt/.test(sourceStatus)
      ? "This record contains partial text from the linked source."
      : data.record.source_category === "campaign"
        ? "This text comes from a public speech or interview transcript."
        : "This text comes from the Congressional Record.";
    const publicationDate = data.record.source_category === "campaign" && /publication date may differ/i.test(data.record.transcript_status || "");
    $("pages").textContent = publicationDate
      ? "The source page’s publication date may differ from the speech date."
      : data.record.source_page_start
        ? `Official Congressional Record · pages ${data.record.source_page_start}–${data.record.source_page_end}`
        : "The text shown here comes from the linked source. Check it for the publication date and context.";
    state.detail.phrase_candidates = data.phrase_candidates || [];
    renderPhraseIndex(state.detail.phrase_candidates);
    renderTranscript(data.text, [], state.detail.phrase_candidates);
    $("phrase-status").textContent = "Civic Lens is finding short topic cues in the speech.";
    $("analyze").querySelector("span").textContent = "Analyze selected speech";
    syncAnalysisControls();
    delete $("analyze").dataset.topic;
    loadRefinedPhraseCandidates(data.record.record_id);
  } catch (error) {
    toast(error.message || "We couldn’t open that statement. Please try again.");
  }
}

async function loadRefinedPhraseCandidates(recordId) {
  try {
    const params = new URLSearchParams({
      politician: state.selected.politician,
      record_id: recordId
    });
    const result = await getJSON("/api/phrase-candidates?" + params.toString(), { method: "POST" });
    if (!state.selected || state.selected.record_id !== recordId) return;
    const phrases = result.phrases || [];
    state.detail.phrase_candidates = phrases;
    renderPhraseIndex(phrases);
    renderTranscript(state.detail.text, [], phrases);
    $("phrase-status").textContent = phrases.length
      ? "Click a highlighted word or a topic chip to read the analysis and compare earlier statements."
      : "Civic Lens did not identify topic cues in this transcript. Enter a topic such as taxes or crime to analyze it.";
  } catch (error) {
    if (state.detail && state.selected && state.selected.record_id === recordId) {
      renderPhraseIndex(state.detail.phrase_candidates || []);
      $("phrase-status").textContent = "Enter a topic such as taxes or crime to find related speech passages.";
    }
  }
}

async function browseTopicMatches() {
  const topic = $("phrase-input").value.replace(/\s+/g, " ").trim();
  if (!state.selected) {
    toast("Choose a speech first, then choose a policy topic.");
    return;
  }
  if (!state.discoveryComplete) {
    syncAnalysisControls();
    return;
  }
  if (topic.length < 2) {
    toast("Choose or enter a topic, such as taxes or crime.");
    return;
  }
  const button = $("browse-topic");
  button.disabled = true;
  button.textContent = "Civic Lens is finding matching passages.";
  try {
    const params = new URLSearchParams({
      politician: state.selected.politician,
      topic,
      source_category: $("phrase-scope").value
    });
    const result = await getJSON("/api/topic-trace?" + params.toString());
    renderPhraseTrace(result);
  } catch (error) {
    state.analysisError = error.message || "Civic Lens could not finish the topic search. Please try again.";
    $("phrase-status").textContent = state.analysisError;
    syncAnalysisControls();
  } finally {
    button.disabled = false;
    button.textContent = "Browse all matching passages";
  }
}

async function tracePhrase() {
  const topic = $("phrase-input").value.replace(/\s+/g, " ").trim();
  if (!state.selected) {
    toast("Choose a speech first, then choose a policy topic.");
    return;
  }
  if (!state.discoveryComplete) {
    syncAnalysisControls();
    return;
  }
  if (state.analysisReady === false) {
    toast(analysisUnavailableMessage());
    return;
  }
  if (topic.length < 2) {
    toast("Choose or enter a topic, such as taxes or crime.");
    return;
  }
  $("analyze").dataset.topic = topic;
  await analyze();
}

function renderPhraseTrace(result) {
  const section = $("phrase-results");
  const records = result.records || [];
  section.classList.remove("hidden");
  $("phrase-heading").textContent = `Civic Lens searched these speeches for “${result.topic}”.`;
  $("phrase-count").textContent = `${result.record_count} speeches · ${result.total_occurrences} related mentions`;
  $("phrase-scope-label").textContent = {
    campaign: "Campaign, public, and interview transcripts",
    congressional_record: "Congressional Record",
    all: "All collected statements"
  }[result.source_category] || result.source_category;
  $("phrase-summary").textContent = result.record_count
    ? `Civic Lens found wording related to ${result.topic.toLowerCase()} in ${result.record_count} ${result.record_count === 1 ? "speech" : "speeches"}. Excerpts highlight the matching words, and the surrounding text keeps each mention in context.`
    : `No related wording about ${result.topic.toLowerCase()} was found in these sources. Change “Compare with” to search a wider collection.`;

  const timeline = $("phrase-timeline");
  timeline.replaceChildren();
  const line = document.createElement("div");
  line.className = "line";
  timeline.append(line);
  const dates = records.map((item) => new Date(item.record.date + "T12:00:00").getTime());
  const min = dates.length ? Math.min(...dates) : 0;
  const max = dates.length ? Math.max(...dates) : min;
  const span = Math.max(max - min, 86400000);
  records.forEach((item, index) => {
    const node = document.createElement("button");
    node.type = "button";
    node.className = "node phrase-node " + (item.record.source_category === "campaign" ? "public" : "congressional");
    node.style.left = (records.length === 1 || max === min ? 50 : 3 + (dates[index] - min) / span * 94) + "%";
    node.style.top = (index % 2 ? 65 : 43) + "px";
    node.title = `${formatDate(item.record.date)} · ${item.record.venue} · ${item.occurrence_count} related mention(s)`;
    const label = document.createElement("span");
    label.textContent = String(new Date(item.record.date + "T12:00:00").getFullYear());
    node.append(label);
    node.addEventListener("click", () => openTracedSpeech(item.record.record_id));
    timeline.append(node);
  });

  const list = $("phrase-occurrences");
  list.replaceChildren();
  for (const item of records) {
    const card = document.createElement("article");
    card.className = "phrase-occurrence";
    const header = document.createElement("div");
    header.className = "phrase-occurrence-head";
    const details = document.createElement("div");
    const date = document.createElement("strong");
    date.textContent = /retrieval date used/i.test(item.record.transcript_status || "")
      ? "Speech date unavailable"
      : formatDate(item.record.date);
    const title = document.createElement("span");
    title.textContent = `${item.record.venue} · ${item.record.source_category === "campaign" ? "Public speech/interview" : "Congressional Record"}`;
    details.append(date, title);
    const count = document.createElement("small");
    const sourceCount = (item.sources || []).length;
    count.textContent = `${item.occurrence_count} related mention${item.occurrence_count === 1 ? "" : "s"}${sourceCount > 1 ? ` · ${sourceCount} transcript sources` : ""}`;
    header.append(details, count);
    card.append(header);
    const matchedTerms = item.matched_terms || [];
    if (matchedTerms.length) {
      const terms = document.createElement("p");
      terms.className = "matched-terms";
      terms.textContent = `Matched wording: ${matchedTerms.join(", ")}`;
      card.append(terms);
    }
    for (const excerpt of item.excerpts || []) {
      const quote = document.createElement("p");
      quote.className = "phrase-excerpt";
      appendHighlightedText(quote, excerpt, matchedTerms);
      card.append(quote);
    }
    const open = document.createElement("button");
    open.type = "button";
    open.className = "read-match";
    open.textContent = "Read this speech in Civic Lens";
    open.addEventListener("click", () => openTracedSpeech(item.record.record_id));
    card.append(open);
    list.append(card);
  }
  section.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function openTracedSpeech(recordId) {
  await loadDetail(recordId);
  $("remark").scrollIntoView({ behavior: "smooth", block: "start" });
}

function createCitationCard(citation, earlier = false) {
  const card = document.createElement("article");
  card.className = "source-excerpt";
  const quote = document.createElement("blockquote");
  quote.textContent = citation.quote ? "“" + citation.quote + "”" : "No exact topic passage was returned for this statement.";
  const meta = document.createElement("p");
  meta.className = "evidence-meta";
  const sourceLabel = citation.source_category === "campaign" ? "Public speech or interview" : "Congressional Record";
  const pages = citation.page_start != null ? " · pages " + citation.page_start + "–" + citation.page_end : "";
  meta.textContent = formatDate(citation.date) + " · " + (citation.venue || sourceLabel) + pages;
  const actions = document.createElement("div");
  actions.className = "evidence-actions";
  const source = document.createElement("a");
  source.href = citation.source_url;
  source.target = "_blank";
  source.rel = "noopener noreferrer";
  source.textContent = "Original source ↗";
  actions.append(source);
  if (earlier && citation.record_id) {
    const open = document.createElement("button");
    open.type = "button";
    open.textContent = "Read this statement";
    open.addEventListener("click", () => openTracedSpeech(citation.record_id));
    actions.append(open);
  }
  card.append(quote, meta, actions);
  return card;
}

function appendCitationCard(container, citation, earlier = false) {
  container.append(createCitationCard(citation, earlier));
}

function normalizeTopicLabel(value) {
  return String(value || "").toLocaleLowerCase().replace(/[^a-z0-9]+/g, "");
}

function exactExcerptAround(text, phrase) {
  if (!text || !phrase) return "";
  const mapped = normalizeWithMap(text);
  const needle = String(phrase).replace(/\s+/g, " ").trim().toLocaleLowerCase();
  const index = mapped.normalized.toLocaleLowerCase().indexOf(needle);
  if (index < 0 || !needle.length) return "";
  const hitStart = mapped.positions[index];
  const hitEnd = mapped.positions[index + needle.length - 1] + 1;
  const paragraphStart = Math.max(text.lastIndexOf("\n\n", hitStart), text.lastIndexOf("\r\n\r\n", hitStart)) + 2;
  let paragraphEnd = text.indexOf("\n\n", hitEnd);
  if (paragraphEnd < 0) paragraphEnd = text.indexOf("\r\n\r\n", hitEnd);
  if (paragraphEnd < 0) paragraphEnd = text.length;
  let start = Math.max(paragraphStart, hitStart - 210);
  let end = Math.min(paragraphEnd, hitEnd + 260);
  if (start > paragraphStart) {
    const boundary = text.indexOf(" ", start);
    if (boundary >= 0 && boundary < hitStart) start = boundary + 1;
  }
  if (end < paragraphEnd) {
    const boundary = text.lastIndexOf(" ", end);
    if (boundary > hitEnd) end = boundary;
  }
  return text.slice(start, end).trim();
}

function selectedTopicCitation(result) {
  const selected = state.selected;
  if (!selected) return null;
  const speechEvidence = result.speech_analysis && result.speech_analysis.evidence || [];
  const verifiedEvidence = speechEvidence.find((item) => item.record_id === selected.record_id && item.quote)
    || speechEvidence.find((item) => item.quote);
  const topic = result.request.topic || result.request.phrase || "";
  const candidates = state.detail && state.detail.phrase_candidates || [];
  const topicCandidates = candidates.filter((item) =>
    normalizeTopicLabel(item.topic) === normalizeTopicLabel(topic)
  );
  const possiblePhrases = [...topicCandidates.map((item) => item.phrase), topic];
  let quote = "";
  for (const phrase of possiblePhrases) {
    quote = exactExcerptAround(state.detail && state.detail.text, phrase);
    if (quote) break;
  }
  quote = quote || (verifiedEvidence && verifiedEvidence.quote) || "";
  return {
    ...(verifiedEvidence || {}),
    record_id: selected.record_id,
    politician: selected.politician,
    date: selected.date,
    source_url: selected.source_url,
    venue: selected.venue,
    page_start: selected.source_page_start,
    page_end: selected.source_page_end,
    source_category: selected.source_category,
    quote
  };
}

function renderEvidenceConnections(container, current, earlier, topic) {
  container.replaceChildren();
  if (!earlier.length) {
    const empty = document.createElement("p");
    empty.className = "evidence-empty";
    empty.textContent = "The collected sources contain no earlier statement matching this topic before the selected speech.";
    container.append(empty);
    return;
  }

  const currentCard = createCitationCard(current);
  currentCard.classList.add("connection-origin");
  const currentLabel = document.createElement("p");
  currentLabel.className = "connection-label";
  currentLabel.textContent = current.quote
    ? "Selected statement · exact source passage"
    : "Selected statement · source record";
  currentCard.prepend(currentLabel);
  container.append(currentCard);

  const note = document.createElement("p");
  note.className = "connection-note";
  note.textContent = "Each link marks an earlier passage retrieved by the same topic search. It shows a source and date connection, not agreement or disagreement.";
  container.append(note);

  const branches = document.createElement("div");
  branches.className = "connection-branches";
  for (const citation of earlier) {
    const row = document.createElement("div");
    row.className = "evidence-connection";
    const relation = document.createElement("div");
    relation.className = "connection-relation";
    const label = document.createElement("span");
    label.textContent = "Earlier match for “" + topic + "”";
    const arrow = document.createElement("span");
    arrow.className = "connection-arrow";
    arrow.setAttribute("aria-hidden", "true");
    arrow.textContent = "↘";
    relation.append(label, arrow);
    row.append(relation, createCitationCard(citation, true));
    branches.append(row);
  }
  container.append(branches);
}

function setAnalysisExpanded(expanded) {
  const workspace = $("workspace");
  if (!workspace) return;
  workspace.classList.toggle("analysis-expanded", expanded);
  const toggle = $("analysis-width-toggle");
  if (!toggle) return;
  toggle.setAttribute("aria-expanded", String(expanded));
  toggle.textContent = expanded ? "Return to split view" : "Expand analysis";
}

function renderAnalysis(result) {
  const speech = result.speech_analysis;
  const longitudinal = result.longitudinal_analysis;
  $("analysis").classList.remove("hidden");
  $("analysis-empty").classList.add("hidden");
  $("analysis-title").textContent = result.request.topic || result.request.phrase || "This is what the record shows.";
  if (result.request.topic || result.request.phrase) $("phrase-results").classList.add("hidden");
  $("summary").textContent = speech.summary;
  $("headline").textContent = speech.headline || "";
  $("headline").classList.toggle("hidden", !speech.headline);
  const insights = speech.key_insights || [];
  const insightGrid = $("insights");
  insightGrid.replaceChildren();
  insights.forEach((item, index) => {
    const card = document.createElement("div");
    card.className = "insight-card";
    const num = document.createElement("span");
    num.className = "insight-num";
    num.textContent = String(index + 1).padStart(2, "0");
    const label = document.createElement("strong");
    label.textContent = item.label;
    const body = document.createElement("p");
    body.textContent = item.insight;
    card.append(num, label, body);
    insightGrid.append(card);
  });
  insightGrid.classList.toggle("hidden", insights.length === 0);
  $("framing").textContent = speech.framing || "";
  $("watch").textContent = speech.what_to_watch || "";
  $("framing").parentElement.classList.toggle("hidden", !speech.framing);
  $("watch").parentElement.classList.toggle("hidden", !speech.what_to_watch);
  $("framing-wrap").classList.toggle("hidden", !(speech.framing || speech.what_to_watch));
  const claims = speech.claims || [];
  const claimsList = $("claims");
  claimsList.replaceChildren();
  for (const claim of claims) {
    const item = document.createElement("li");
    item.textContent = claim;
    claimsList.append(item);
  }
  $("claims-wrap").classList.toggle("hidden", claims.length === 0);

  const evidence = speech.evidence || [];
  const evidenceList = $("evidence");
  evidenceList.replaceChildren();
  if (evidence.length) evidence.slice(0, 4).forEach((item) => appendCitationCard(evidenceList, item));
  else {
    const empty = document.createElement("p");
    empty.className = "evidence-empty";
    empty.textContent = "No exact quotation passed the source text check for this speech.";
    evidenceList.append(empty);
  }

  const hasTopicComparison = Boolean(result.request.topic || result.request.phrase);
  $("earlier-section").classList.toggle("hidden", !hasTopicComparison);
  $("comparison-section").classList.toggle("hidden", !hasTopicComparison);
  if (hasTopicComparison) {
    const earlier = longitudinal && longitudinal.earlier_statements || [];
    $("scope").textContent = earlier.length
      ? `Civic Lens found ${earlier.length} earlier ${earlier.length === 1 ? "statement" : "statements"} in ${result.request.source_category === "all" ? "all collected sources" : result.request.source_category === "campaign" ? "campaign speeches, public remarks, and interviews" : "the Congressional Record"}.`
      : "No earlier matching statement was found in this source set.";
    const earlierList = $("earlier-evidence");
    earlierList.replaceChildren();
    renderEvidenceConnections(
      earlierList,
      selectedTopicCitation(result),
      earlier,
      result.request.topic || result.request.phrase || "this topic"
    );
    $("comparison").textContent = longitudinal
      ? longitudinal.synthesis
      : "There is not enough earlier source material in this collection to compare the speaker’s wording.";
    const comparisonPoints = longitudinal && longitudinal.comparison_points || [];
    const pointsList = $("comparison-points");
    pointsList.replaceChildren();
    for (const point of comparisonPoints) {
      const item = document.createElement("li");
      item.textContent = point;
      pointsList.append(item);
    }
    pointsList.classList.toggle("hidden", comparisonPoints.length === 0);
  }
  const review = result.safety_review;
  $("safety-review").classList.toggle("hidden", !review);
  if (review) {
    const verdict = $("safety-verdict");
    verdict.textContent = review.approved
      ? "✓ Approved: the claims are supported by the quoted evidence and scope warnings are present."
      : "⚠ Flagged: the auditor found issues to review before relying on this answer.";
    verdict.classList.toggle("flagged", !review.approved);
    const list = $("safety-concerns");
    list.replaceChildren();
    for (const text of [...(review.concerns || []), ...(review.required_revisions || [])]) {
      const item = document.createElement("li");
      item.textContent = text;
      list.append(item);
    }
    list.classList.toggle("hidden", list.children.length === 0);
    $("safety-scope").textContent = review.scope_warning || "";
  }
  if (state.detail) {
    const quotes = evidence.map((item) => item.quote).filter(Boolean);
    const phrases = state.detail.phrase_candidates || [];
    renderTranscript(state.detail.text, quotes, phrases);
  }
  setAnalysisExpanded(true);
  $("analysis").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function analyze() {
  if (!state.selected) return;
  if (state.analysisReady === false || (state.analysisError && state.analysisError === analysisUnavailableMessage())) {
    syncAnalysisControls();
    return;
  }
  const speechButton = $("analyze");
  const topicButton = $("trace-phrase");
  const browseButton = $("browse-topic");
  const topic = speechButton.dataset.topic || null;
  if (topic && !state.discoveryComplete) {
    syncAnalysisControls();
    return;
  }
  const loading = $(topic ? "topic-analysis-loading" : "analysis-loading");
  const loadingLabel = $(topic ? "topic-analysis-loading-label" : "analysis-loading-label");
  const loadingDetail = $(topic ? "topic-analysis-loading-detail" : "analysis-loading-detail");
  const timerId = topic ? "topic-analysis-loading-timer" : "analysis-loading-timer";
  const busyPanel = $(topic ? "topic-explorer" : "analysis-controls");
  state.analysisInFlight = true;
  state.analysisError = null;
  speechButton.disabled = true;
  topicButton.disabled = true;
  browseButton.disabled = true;
  if (topic) $("phrase-scope").disabled = true;
  if (topic) topicButton.textContent = "Analyzing topic…";
  else speechButton.querySelector("span").textContent = "Analyzing speech…";
  busyPanel.setAttribute("aria-busy", "true");
  loadingLabel.textContent = topic ? `Civic Lens is comparing “${topic}” across statements.` : "Civic Lens is analyzing the selected speech.";
  loadingDetail.textContent = topic
    ? "One measured topic comparison took 34.5 seconds. This request may take longer."
    : "One measured speech analysis took 3.2 seconds. This request may take longer.";
  loading.classList.remove("hidden");
  startElapsedTimer(timerId);
  syncAnalysisControls();
  try {
    const result = await getJSON("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        politician: state.selected.politician,
        record_id: state.selected.record_id,
        topic,
        phrase: null,
        source_category: $("phrase-scope").value,
        analysis_mode: topic ? "related_records" : "speech"
      })
    });
    renderAnalysis(result);
  } catch (error) {
    state.analysisError = error.message || "Civic Lens could not finish the analysis. Please try again.";
    if (topic) $("phrase-status").textContent = state.analysisError;
  } finally {
    stopElapsedTimer(timerId);
    state.analysisInFlight = false;
    loading.classList.add("hidden");
    busyPanel.removeAttribute("aria-busy");
    speechButton.querySelector("span").textContent = "Analyze selected speech";
    topicButton.textContent = "Analyze topic";
    browseButton.textContent = "Show all matching passages";
    $("phrase-scope").disabled = false;
    syncAnalysisControls();
  }
}

function addChat(role, text) {
  const bubble = document.createElement("div");
  bubble.className = "chat-bubble " + role;
  bubble.textContent = text;
  $("chat-messages").append(bubble);
  $("chat-messages").scrollTop = $("chat-messages").scrollHeight;
  return bubble;
}

async function sendChat(message) {
  const clean = message.trim();
  if (!clean) return;
  addChat("user", clean);
  chatHistory.push({ role: "user", content: clean });
  $("chat-input").value = "";
  $("chat-input").disabled = true;
  const loading = addChat("assistant", "Thinking…");
  loading.classList.add("typing");
  try {
    const result = await getJSON("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: clean,
        history: chatHistory.slice(-8),
        selected_record_id: state.selected && state.selected.record_id || null
      })
    });
    loading.remove();
    addChat("assistant", result.message);
    chatHistory.push({ role: "assistant", content: result.message });
  } catch (error) {
    loading.remove();
    addChat("assistant", error.message || "I couldn’t connect to the guide. Please try again.");
  } finally {
    $("chat-input").disabled = false;
    $("chat-input").focus();
  }
}

$("politician").addEventListener("change", loadRecords);
$("speech").addEventListener("change", (event) => loadDetail(event.target.value));
$("text").addEventListener("click", (event) => {
  const mark = event.target.closest("mark.phrase-highlight");
  if (!mark) return;
  $("phrase-input").value = mark.dataset.topic || mark.dataset.phrase || mark.textContent;
  $("analyze").dataset.topic = mark.dataset.topic || "";
  tracePhrase();
});
$("text").addEventListener("keydown", (event) => {
  if ((event.key !== "Enter" && event.key !== " ") || !event.target.matches("mark.phrase-highlight")) return;
  event.preventDefault();
  $("phrase-input").value = event.target.dataset.topic || event.target.dataset.phrase || event.target.textContent;
  $("analyze").dataset.topic = event.target.dataset.topic || "";
  tracePhrase();
});
$("phrase-input").addEventListener("input", () => {
  state.analysisError = null;
  $("analyze").dataset.topic = $("phrase-input").value.trim();
  syncAnalysisControls();
});
$("phrase-scope").addEventListener("change", () => {
  state.analysisError = null;
  const topic = $("phrase-input").value.replace(/\s+/g, " ").trim();
  syncAnalysisControls();
  if (state.selected && topic.length >= 2) {
    tracePhrase();
  } else {
    $("phrase-status").textContent = "The comparison filter has been updated. Choose a topic to see matching earlier statements.";
  }
});
$("trace-phrase").addEventListener("click", tracePhrase);
$("browse-topic").addEventListener("click", browseTopicMatches);
$("analyze").addEventListener("click", () => { delete $("analyze").dataset.topic; analyze(); });
$("analysis-width-toggle").addEventListener("click", () => {
  setAnalysisExpanded(!$("workspace").classList.contains("analysis-expanded"));
});
$("chat-launcher").addEventListener("click", () => {
  $("chat-panel").classList.remove("hidden");
  $("chat-input").focus();
});
$("chat-close").addEventListener("click", () => $("chat-panel").classList.add("hidden"));
$("chat-form").addEventListener("submit", (event) => {
  event.preventDefault();
  sendChat($("chat-input").value);
});
for (const button of document.querySelectorAll(".chat-suggestions button")) {
  button.addEventListener("click", () => sendChat(button.textContent));
}
loadPeople().catch((error) => toast(error.message || "Could not load politicians."));
