"""Shared policy topic vocabulary for searches and source-backed analysis."""

from __future__ import annotations

import re


TOPIC_TERMS = {
    "Healthcare": ["healthcare", "health care", "medicare", "medicaid", "obamacare", "affordable care act", "aca", "health insurance", "insurance premiums", "prescription drug", "prescription drugs", "preexisting condition", "public option", "health", "insurer"],
    "Immigration": ["immigration", "immigrant", "migrant", "border", "asylum", "deportation", "deport", "undocumented", "citizenship", "visa", "refugee", "ice", "sanctuary city", "border wall", "green card", "immigration reform"],
    "Taxes & budget": ["income tax", "corporate tax", "property tax", "payroll tax", "tax credit", "tax cut", "tax hike", "tax relief", "taxpayer", "taxpayers", "taxation", "taxes", "tax", "irs", "internal revenue service", "deduction", "loophole", "capital gains", "estate tax", "earned income tax credit", "tax exemption", "tax increase", "tax bracket", "budget", "deficit", "national debt", "fiscal", "appropriations", "spending", "revenue", "outlays"],
    "Economy & jobs": ["unemployment", "inflation", "cost of living", "small business", "business", "economy", "economic", "job", "wage", "prices", "growth", "manufacturing", "investment", "paycheck"],
    "Crime & justice": ["criminal justice", "law enforcement", "gun violence", "violent crime", "public safety", "incarceration", "sentencing", "sentencing reform", "justice reform", "juvenile justice", "mass incarceration", "prosecutor", "policing", "police", "firearm", "firearms", "homicide", "murder", "assault", "theft", "prison", "bail", "crime", "criminal", "guns"],
    "Education": ["higher education", "student loan", "public school", "education", "school", "student", "teacher", "college", "university", "tuition", "classroom"],
    "Climate & energy": ["greenhouse gas", "renewable energy", "clean energy", "fossil fuel", "climate", "carbon", "emissions", "energy", "environment", "pollution", "solar", "wind"],
    "Labor": ["collective bargaining", "minimum wage", "labor", "worker", "union", "workplace", "overtime", "paid leave"],
    "National security": ["foreign policy", "national security", "terrorism", "terror", "defense", "military", "war", "veteran", "veterans", "nato", "intelligence"],
}


def normalize_topic(value: str) -> str | None:
    label = " ".join(value.casefold().split())
    for topic in TOPIC_TERMS:
        if label == topic.casefold():
            return topic
    matches = []
    for topic, terms in TOPIC_TERMS.items():
        if any(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", label) for term in terms):
            matches.append(topic)
    return matches[0] if len(matches) == 1 else None


# ---------------------------------------------------------------------------
# Transcript highlighting vocabulary.
# Highlights should mark recognisable political language (policy terms,
# slogans, framing phrases, and statistical claims), not every civic-sounding
# word. Generic single words that collide with names and history ("war" in
# "World War II", "university" in "Fisk University", "job", "school") are
# deliberately excluded here; they remain available for topic search above.
# ---------------------------------------------------------------------------
TOPIC_TERMS.update({
    "Inequality & opportunity": ["american dream", "wealth gap", "income inequality", "inequality", "middle class", "working families", "working americans", "working people", "working class", "poverty", "billionaires", "the wealthy", "economic opportunity", "upward mobility", "the one percent", "1 percent", "top 1%", "rigged economy"],
    "Civil rights & democracy": ["civil rights", "voting rights", "right to vote", "jim crow", "racial justice", "systemic racism", "equal justice", "equal rights", "democracy", "the constitution", "rule of law", "freedom of speech", "free and fair elections", "voter suppression"],
    "Housing & cost of living": ["affordable housing", "housing crisis", "eviction", "evictions", "losing their homes", "homelessness", "rent", "mortgage", "cost of living", "child care", "childcare", "food insecurity", "enough to eat"],
})

HIGHLIGHT_PHRASES: dict[str, list[str]] = {
    "Inequality & opportunity": [
        "American Dream", "wealth gap", "income inequality", "economic inequality", "middle class",
        "working families", "working Americans", "working people", "working class", "working men and women",
        "lifted my family out of poverty", "out of poverty", "lives in poverty", "poverty persists", "poverty",
        "billionaire class", "billionaires", "the wealthiest", "the 1 percent", "the one percent", "top 1 percent",
        "rigged economy", "economy is rigged", "economic opportunity", "upward mobility", "dignity of work",
        "dignity of all working Americans", "corporate greed", "Wall Street", "special interests",
    ],
    "Labor": [
        "union job", "union jobs", "labor union", "labor unions", "the UAW", "UAW", "collective bargaining",
        "right to organize", "minimum wage", "living wage", "$15 an hour", "paid family leave", "paid leave",
        "overtime pay", "assembly line", "assembly lines", "workers' rights", "essential workers", "full time job",
    ],
    "Economy & jobs": [
        "our economy", "the economy", "economic growth", "unemployment", "unemployed", "inflation",
        "cost of living", "small businesses", "small business", "good-paying jobs", "good paying jobs",
        "manufacturing jobs", "supply chain", "supply chains", "trade deal", "trade agreement", "tariffs",
        "recession", "the depression", "great depression", "stimulus", "jobs report",
    ],
    "Healthcare": [
        "healthcare", "health care", "Medicare for All", "Medicare", "Medicaid", "Affordable Care Act",
        "Obamacare", "pre-existing conditions", "preexisting conditions", "prescription drug", "prescription drugs",
        "drug prices", "health insurance", "public option", "uninsured", "lost their healthcare",
    ],
    "Housing & cost of living": [
        "losing their homes", "affordable housing", "housing crisis", "eviction", "evictions", "homelessness",
        "aren't getting enough to eat", "enough to eat", "food insecurity", "hunger", "child care", "childcare",
    ],
    "Civil rights & democracy": [
        "Jim Crow", "civil rights", "voting rights", "right to vote", "voter suppression", "racial justice",
        "systemic racism", "equal justice", "equal rights", "our democracy", "democracy", "rule of law",
        "the Constitution", "free and fair elections", "peaceful transfer of power", "Great Migration",
    ],
    "Taxes & budget": [
        "tax cuts", "tax cut", "tax breaks", "tax relief", "tax increase", "raise taxes", "corporate tax",
        "pay their fair share", "fair share", "national debt", "the deficit", "balanced budget",
        "government spending", "wasteful spending", "taxpayer dollars", "taxpayers", "the IRS",
    ],
    "Immigration": [
        "immigration reform", "comprehensive immigration reform", "border security", "the border",
        "southern border", "border wall", "illegal immigration", "illegal immigrants", "undocumented immigrants",
        "Dreamers", "DACA", "asylum seekers", "asylum", "deportation", "deportations", "path to citizenship",
        "sanctuary cities", "open borders", "migrants", "immigrants",
    ],
    "Crime & justice": [
        "criminal justice reform", "criminal justice", "mass incarceration", "police reform", "law enforcement",
        "gun violence", "gun safety", "background checks", "Second Amendment", "violent crime", "public safety",
        "defund the police", "bail reform", "sentencing reform", "First Step Act",
    ],
    "Education": [
        "student debt", "student loans", "student loan", "public schools", "public education", "free college",
        "tuition-free", "college affordability", "school choice", "teach our children", "teachers",
    ],
    "Climate & energy": [
        "climate change", "climate crisis", "clean energy", "renewable energy", "fossil fuels", "fossil fuel",
        "Green New Deal", "carbon emissions", "greenhouse gas", "energy independence", "Paris Agreement",
        "oil and gas", "drill", "fracking",
    ],
    "National security": [
        "national security", "foreign policy", "our troops", "our military", "veterans", "terrorism",
        "terrorist", "counterterrorism", "NATO", "our allies", "Iran", "China", "Russia", "Ukraine",
        "Israel", "endless wars", "forever wars", "war on terror", "nuclear weapons", "strategic partnership",
    ],
}

# Statistical claims are core political language ("40 million Americans").
STAT_CLAIM_PATTERN = re.compile(
    r"\b\d[\d,.]*\s*(?:million|billion|trillion|percent|%)\s+(?:Americans|people|families|workers|children|jobs|dollars)\b",
    re.IGNORECASE,
)


# Corpus-wide pass: phrases mined from all 281 public-source speeches and a
# 300-remark Congressional Record sample that the first list missed.
TOPIC_TERMS.update({
    "Public health & COVID": ["covid", "covid-19", "coronavirus", "pandemic", "vaccine", "vaccines", "public health", "mental health", "opioid", "opioids", "fentanyl", "addiction"],
    "Social issues": ["abortion", "roe v. wade", "pro-life", "reproductive rights", "right to choose", "religious liberty", "religious freedom", "marriage equality", "lgbtq", "equal pay", "women's rights", "sexual assault"],
})
_EXTRA_HIGHLIGHTS = {
    "Inequality & opportunity": ["wealth inequality", "paycheck to paycheck", "low-income", "low income", "hardworking families", "hard-working families", "hard working families", "big banks", "drug companies", "pharmaceutical companies", "big pharma", "corporate America", "greed"],
    "Economy & jobs": ["back to work", "private sector", "free market", "free enterprise", "job creators", "regulations", "red tape", "infrastructure", "roads and bridges", "broadband", "farmers", "agriculture", "jobs and the economy", "stimulus checks", "unemployment insurance", "Paycheck Protection Program"],
    "Taxes & budget": ["debt ceiling", "government shutdown", "federal government", "big government", "billions of dollars", "trillions of dollars", "Social Security", "entitlements", "earmarks"],
    "Healthcare": ["mental health", "seniors", "retirement security", "pensions", "long-term care"],
    "Education": ["higher education", "tuition free", "tuition-free college", "community college", "Pell Grants", "student debt crisis", "charter schools"],
    "Civil rights & democracy": ["Supreme Court", "Citizens United", "human rights", "Black Lives Matter", "police brutality", "George Floyd", "racial equity", "reparations", "January 6th", "January 6", "the election was stolen", "stolen election", "dark money", "campaign finance", "a more perfect union", "freedom of religion"],
    "National security": ["Middle East", "Vladimir Putin", "Putin", "Xi Jinping", "Chinese Communist Party", "Communist Party", "North Korea", "Taiwan", "Hong Kong", "Venezuela", "Cuba", "Maduro", "Castro regime", "Hamas", "ISIS", "al Qaeda", "Afghanistan", "Iraq", "Syria", "cybersecurity", "national guard", "the VA", "service members", "men and women in uniform"],
    "Immigration": ["the cartels", "cartels", "human trafficking", "border crisis", "Remain in Mexico", "catch and release"],
    "Public health & COVID": ["COVID-19", "COVID", "coronavirus", "the pandemic", "pandemic", "vaccines", "vaccine", "public health", "opioid epidemic", "opioid crisis", "opioids", "fentanyl", "addiction", "masks"],
    "Social issues": ["Roe v. Wade", "abortion", "pro-life", "reproductive rights", "reproductive freedom", "right to choose", "women's health", "Planned Parenthood", "religious liberty", "religious freedom", "marriage equality", "LGBTQ", "equal pay", "women's rights", "sexual assault", "MeToo"],
}
for _topic, _phrases in _EXTRA_HIGHLIGHTS.items():
    HIGHLIGHT_PHRASES.setdefault(_topic, []).extend(p for p in _phrases if p not in HIGHLIGHT_PHRASES.get(_topic, []))

STAT_CLAIM_PATTERN = re.compile(
    r"\b(?:\d[\d,.]*\s*(?:million|billion|trillion|thousand|percent|%)|millions of|billions of|hundreds of thousands of|tens of millions of)\s+"
    r"(?:Americans|people|families|workers|children|kids|jobs|dollars|seniors|veterans|students|immigrants|women|men)\b",
    re.IGNORECASE,
)
