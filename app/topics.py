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
