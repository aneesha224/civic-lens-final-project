const state = { politicians: [], profiles: [], profileAsOf: "", records: [], selected: null, detail: null, discoveryComplete: true };
const $ = (id) => document.getElementById(id);
const chatHistory = [];
let selectionRequest = 0;

async function getJSON(url, options) {
  const response = await fetch(url, options);
  const body = await response.json();
  if (!response.ok) throw new Error(body.detail || "The request failed.");
  return body;
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
  options.replaceChildren(new Option("Select a politician...", ""));
  for (const name of state.politicians) {
    const profile = state.profiles.find((item) => item.name === name);
    const label = profile ? profile.display_name : name;
    options.append(new Option(label, name));
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
  select.replaceChildren(new Option("Select a date and statement...", ""));
  for (const record of records) {
    const dateLabel = /retrieval date used/i.test(record.transcript_status || "")
      ? "Speech date unavailable"
      : /publication date may differ/i.test(record.transcript_status || "")
        ? `Publisher date ${formatDate(record.date)}`
        : formatDate(record.date);
    const source = record.source_label || (record.source_category === "campaign" ? "Campaign / public speech" : "Congressional Record");
    const pages = record.source_page_start ? `pages ${record.source_page_start}–${record.source_page_end}` : "full text";
    select.add(new Option(`${dateLabel} · ${source} · ${pages}`, record.record_id));
  }
  if (records.some((record) => record.record_id === selectedId)) select.value = selectedId;
  select.disabled = records.length === 0;
}

async function loadRecords() {
  const requestNumber = ++selectionRequest;
  setAnalysisExpanded(false);
  const name = selectedPoliticianName();
  const selectedProfile = getPoliticianProfile(name);
  if (selectedProfile) $("politician").value = selectedProfile.name;
  renderPoliticianProfile(selectedProfile);
  state.selected = null;
  state.detail = null;
  state.discoveryComplete = false;
  $("remark").classList.add("hidden");
  $("topic-explorer").classList.add("hidden");
  $("analysis-controls").classList.add("hidden");
  $("phrase-results").classList.add("hidden");
  $("analysis").classList.add("hidden");
  $("analysis-empty").classList.remove("hidden");
  $("empty").classList.remove("hidden");
  $("phrase-input").value = "";
  delete $("analyze").dataset.topic;
  $("speech").disabled = true;
  $("analyze").disabled = true;
  $("source-leads").classList.add("hidden");
  $("source-leads").open = false;
  $("source-leads-content").replaceChildren();
  $("source-leads-summary").textContent = "More public speech sources";
  if (!name) {
    $("coverage").textContent = "Select a politician to see their collected statements.";
    setCorpusProgress("hidden");
    return;
  }
  $("coverage").textContent = "Searching public speech sources and loading Congressional Record statements…";
  setCorpusProgress("loading", "Loading speech corpus…", "Gathering this politician’s available campaign, public, and Congressional Record speeches.");
  try {
    let data = await getJSON("/api/records?politician=" + encodeURIComponent(name));
    while (requestNumber === selectionRequest) {
      state.records = data.records;
      renderSpeechOptions(data.records);
      const counts = data.source_counts || {};
      const publicCount = counts.public_transcripts || 0;
      const congressionalCount = counts.congressional_record || 0;
      if (data.search_status === "loading") {
        state.discoveryComplete = false;
        $("coverage").textContent = `Searching all mapped election cycles · ${publicCount} public transcripts and ${congressionalCount} Congressional Record statements loaded so far`;
        setCorpusProgress("loading", "Searching mapped election cycles…", `${publicCount} public transcripts and ${congressionalCount} Congressional Record statements loaded so far.`);
        $("analyze").querySelector("span").textContent = "Loading the politician’s speech corpus…";
        renderLeads({ cache_status: "loading" });
        await new Promise((resolve) => setTimeout(resolve, 1500));
        if (requestNumber !== selectionRequest) return;
        data = await getJSON("/api/records?politician=" + encodeURIComponent(name));
        continue;
      }
      state.discoveryComplete = true;
      $("coverage").textContent = data.search_status === "unavailable"
        ? `Public-source search is unavailable · showing ${publicCount} public transcripts and ${congressionalCount} Congressional Record statements already collected`
        : `${publicCount} public/campaign transcripts · ${congressionalCount} Congressional Record statements · public search complete`;
      setCorpusProgress(
        data.search_status === "unavailable" ? "unavailable" : "complete",
        data.search_status === "unavailable" ? "Using transcripts already collected" : "Speech corpus ready",
        `${publicCount} public/campaign transcripts and ${congressionalCount} Congressional Record statements are available.`
      );
      renderLeads(data.discovery || {});
      $("analyze").querySelector("span").textContent = "Analyze selected speech";
      if (state.selected) $("analyze").disabled = false;
      if (!data.records.length) toast("No statements were found in the local collection or public source search.");
      break;
    }
  } catch (error) {
    if (requestNumber !== selectionRequest) return;
    toast(error.message || "We couldn’t load that list. Please try again.");
    $("coverage").textContent = "Could not load statements. Check the connection and try again.";
    setCorpusProgress("error", "Could not load speech corpus", "Check the connection, then choose the politician again.");
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
    summary.textContent = "Could not reach public speech sources";
    content.textContent = "The transcripts already collected are still available in the speech list.";
    container.classList.remove("hidden");
    return;
  }
  if (String(discovery.cache_status || "").startsWith("loading")) {
    summary.textContent = "Searching this politician’s listed election cycles…";
    content.textContent = "Full transcripts found in public sources will appear in the speech list.";
    container.classList.remove("hidden");
    return;
  }
  const additionalLeads = leads.filter((lead) => !lead.record_id);
  if (!additionalLeads.length) {
    container.classList.add("hidden");
    return;
  }
  summary.textContent = `${count} transcripts added · ${additionalLeads.length} more source pages`;
  const heading = document.createElement("p");
  heading.className = "source-leads-help";
  heading.textContent = "Load a result to add its transcript to the speech list. Pages without a complete speech are skipped.";
  content.append(heading);
  for (const lead of additionalLeads.slice(0, 8)) {
    const row = document.createElement("div");
    row.className = "source-lead";
    const title = document.createElement("strong");
    title.textContent = lead.title || "Public speech source";
    row.append(title);
    const status = document.createElement("small");
    status.className = "source-lead-status";
    const sourceStatus = lead.status || "Source page available to retrieve";
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
    load.textContent = lead.record_id ? "Read transcript in Civic Lens" : "Load transcript into Civic Lens";
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
  button.textContent = "Loading transcript into Civic Lens…";
  status.textContent = "Fetching the source page and extracting speech text…";
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
      option.textContent = `${formatDate(record.date)} · Campaign / public speech · full transcript`;
      $("speech").append(option);
    }
    $("speech").value = record.record_id;
    status.textContent = "Full speech text loaded below in the Civic Lens reader.";
    button.textContent = "Transcript open in Civic Lens";
    await loadDetail(record.record_id);
    $("remark").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    status.textContent = error.message || "Civic Lens could not retrieve a complete transcript from this page.";
    button.textContent = "Try loading transcript again";
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
    const button = document.createElement("button");
    button.type = "button";
    button.className = "phrase-option";
    button.title = "Analyze " + topic.toLowerCase() + " in this speech and compare earlier statements";
    const label = document.createElement("span");
    label.className = "phrase-option-topic";
    label.textContent = topic;
    const cueList = document.createElement("span");
    cueList.className = "phrase-option-text";
    cueList.textContent = `${cues.slice(0, 4).map((cue) => `“${cue}”`).join(" · ")} highlighted`;
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
    $("empty").classList.add("hidden");
    $("analysis-empty").classList.add("hidden");
    $("analysis").classList.add("hidden");
    $("phrase-results").classList.add("hidden");
    $("remark").classList.remove("hidden");
    $("topic-explorer").classList.remove("hidden");
    $("analysis-controls").classList.remove("hidden");
    const select = $("speech");
    if (![...select.options].some((option) => option.value === recordId)) {
      const source = data.record.source_category === "campaign" ? "Campaign / public speech" : "Congressional Record";
      select.add(new Option(`${formatDate(data.record.date)} · ${source} · full text`, recordId));
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
    $("source-kind").textContent = data.record.source_category === "campaign"
      ? "Campaign / public transcript · full text loaded from source"
      : "Congressional Record transcript · full text shown here";
    const publicationDate = data.record.source_category === "campaign" && /publication date may differ/i.test(data.record.transcript_status || "");
    $("pages").textContent = publicationDate
      ? "Publisher publication date; the speech may have been delivered on a different date."
      : data.record.source_page_start
        ? `Official Congressional Record · pages ${data.record.source_page_start}–${data.record.source_page_end}`
        : "Full transcript from the listed source. Check the source for date and transcript context.";
    state.detail.phrase_candidates = data.phrase_candidates || [];
    renderPhraseIndex(state.detail.phrase_candidates);
    renderTranscript(data.text, [], state.detail.phrase_candidates);
    $("phrase-status").textContent = "Finding short topic cues in the speech…";
    $("analyze").disabled = !state.discoveryComplete;
    $("analyze").querySelector("span").textContent = "Analyze selected speech";
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
      : "No topic cues found in this transcript. Enter a topic such as taxes or crime to analyze it.";
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
    toast("Civic Lens is still loading this politician’s speech corpus. Topic search will be ready when it finishes.");
    return;
  }
  if (topic.length < 2) {
    toast("Choose or enter a topic, such as taxes or crime.");
    return;
  }
  const button = $("browse-topic");
  button.disabled = true;
  button.textContent = "Finding passages…";
  try {
    const params = new URLSearchParams({
      politician: state.selected.politician,
      topic,
      source_category: $("phrase-scope").value
    });
    const result = await getJSON("/api/topic-trace?" + params.toString());
    renderPhraseTrace(result);
  } catch (error) {
    $("phrase-status").textContent = error.message || "Topic search failed.";
    toast(error.message || "Topic search failed.");
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
    toast("Civic Lens is still collecting this politician’s statements. Topic analysis will be ready when it finishes.");
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
  $("phrase-heading").textContent = `${result.topic} across speeches`;
  $("phrase-count").textContent = `${result.record_count} speeches · ${result.total_occurrences} related mentions`;
  $("phrase-scope-label").textContent = {
    campaign: "Campaign & public speeches",
    congressional_record: "Congressional Record",
    all: "All collected statements"
  }[result.source_category] || result.source_category;
  $("phrase-summary").textContent = result.record_count
    ? `Found wording related to ${result.topic.toLowerCase()} in ${result.record_count} ${result.record_count === 1 ? "speech" : "speeches"}. Excerpts highlight the words that matched; surrounding text keeps each mention in context.`
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
    title.textContent = `${item.record.venue} · ${item.record.source_category === "campaign" ? "Campaign/public" : "Congressional Record"}`;
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

function appendCitationCard(container, citation, earlier = false) {
  const card = document.createElement("article");
  card.className = "source-excerpt";
  const quote = document.createElement("blockquote");
  quote.textContent = "“" + citation.quote + "”";
  const meta = document.createElement("p");
  meta.className = "evidence-meta";
  const sourceLabel = citation.source_category === "campaign" ? "Public / campaign speech" : "Congressional Record";
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
  container.append(card);
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
  const safety = result.safety_review;
  $("analysis").classList.remove("hidden");
  $("analysis-empty").classList.add("hidden");
  $("analysis-title").textContent = result.request.topic || result.request.phrase || "What the record shows";
  if (result.request.topic || result.request.phrase) $("phrase-results").classList.add("hidden");
  $("pill").textContent = safety.approved ? "Source text checked" : "Source text needs review";
  $("pill").style.background = safety.approved ? "#e8f8f0" : "#fff0f3";
  $("pill").style.color = safety.approved ? "#245b42" : "#9d2945";
  $("summary").textContent = speech.summary;
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
      ? earlier.length + " earlier " + (earlier.length === 1 ? "statement" : "statements") + " · " + (result.request.source_category === "all" ? "all collected sources" : result.request.source_category === "campaign" ? "campaign and public speeches" : "Congressional Record")
      : "No earlier matching statement was found in this source set.";
    const earlierList = $("earlier-evidence");
    earlierList.replaceChildren();
    if (earlier.length) earlier.forEach((item) => appendCitationCard(earlierList, item, true));
    else {
      const empty = document.createElement("p");
      empty.className = "evidence-empty";
      empty.textContent = "The collected sources contain no earlier statement matching this topic before the selected speech.";
      earlierList.append(empty);
    }
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
  const button = $("analyze");
  const topicButton = $("trace-phrase");
  const browseButton = $("browse-topic");
  const topic = button.dataset.topic || null;
  const loading = $(topic ? "topic-analysis-loading" : "analysis-loading");
  const loadingLabel = $(topic ? "topic-analysis-loading-label" : "analysis-loading-label");
  const loadingDetail = $(topic ? "topic-analysis-loading-detail" : "analysis-loading-detail");
  const busyPanel = $(topic ? "topic-explorer" : "analysis-controls");
  button.disabled = true;
  topicButton.disabled = Boolean(topic);
  browseButton.disabled = Boolean(topic);
  if (topic) $("phrase-scope").disabled = true;
  button.querySelector("span").textContent = "Analyzing source text…";
  busyPanel.setAttribute("aria-busy", "true");
  loadingLabel.textContent = topic ? "Analyzing “" + topic + "”…" : "Analyzing the selected speech…";
  loadingDetail.textContent = topic
    ? "Reading this speech, finding earlier statements, and preparing a comparison."
    : "Reading the selected transcript and checking its source excerpts.";
  loading.classList.remove("hidden");
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
    toast(error.message || "Analysis failed. Please try again.");
  } finally {
    button.disabled = false;
    topicButton.disabled = false;
    browseButton.disabled = false;
    $("phrase-scope").disabled = false;
    loading.classList.add("hidden");
    busyPanel.removeAttribute("aria-busy");
    button.querySelector("span").textContent = "Analyze selected speech";
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
        history: chatHistory.slice(-20),
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
  $("analyze").dataset.topic = $("phrase-input").value.trim();
});
$("phrase-scope").addEventListener("change", () => {
  const topic = $("phrase-input").value.replace(/\s+/g, " ").trim();
  if (state.selected && topic.length >= 2) {
    tracePhrase();
  } else {
    $("phrase-status").textContent = "Comparison filter updated. Choose a topic to see matching earlier statements.";
  }
});
$("trace-phrase").addEventListener("click", tracePhrase);
$("browse-topic").addEventListener("click", browseTopicMatches);
$("analyze").addEventListener("click", analyze);
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
