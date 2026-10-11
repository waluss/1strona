import re
from typing import List, Dict, Any
from pydantic import BaseModel

class MatchDecision(BaseModel):
    decision: str  # MATCH, REJECT, MANUAL_REVIEW
    score: float
    reasons: List[str]
    matched_keywords: List[str]
    matched_cpvs: List[str]
    matched_regions: List[str]
    exclusion_triggers: List[str]


def match_tender_against_profile(
    tender_title: str,
    tender_description: str,
    tender_cpvs: List[str],
    tender_region: str,
    profile_keywords: List[str],
    profile_exclusions: List[str],
    profile_cpvs: List[str],
    profile_regions: List[str]
) -> MatchDecision:
    text_content = f"{tender_title or ''} {tender_description or ''}".lower()

    exclusion_triggers = []
    for ex in profile_exclusions:
        if ex and ex.lower() in text_content:
            exclusion_triggers.append(ex)

    if exclusion_triggers:
        return MatchDecision(
            decision="REJECT",
            score=0.0,
            reasons=[f"Exclusion trigger matched: {ex}" for ex in exclusion_triggers],
            matched_keywords=[],
            matched_cpvs=[],
            matched_regions=[],
            exclusion_triggers=exclusion_triggers
        )

    matched_keywords = []
    for kw in profile_keywords:
        if kw and kw.lower() in text_content:
            matched_keywords.append(kw)

    matched_cpvs = []
    if profile_cpvs:
        for cpv in tender_cpvs:
            for p_cpv in profile_cpvs:
                if cpv.startswith(p_cpv) or p_cpv.startswith(cpv):
                    matched_cpvs.append(cpv)

    matched_regions = []
    if profile_regions and tender_region:
        for reg in profile_regions:
            if reg.lower() in tender_region.lower() or tender_region.lower() in reg.lower():
                matched_regions.append(reg)

    kw_score = min(len(matched_keywords) * 20.0, 50.0)
    cpv_score = 30.0 if matched_cpvs else 0.0
    region_score = 20.0 if matched_regions or not profile_regions else 0.0

    total_score = kw_score + cpv_score + region_score

    reasons = []
    if matched_keywords:
        reasons.append(f"Matched keywords: {', '.join(matched_keywords)}")
    if matched_cpvs:
        reasons.append(f"Matched CPV codes: {', '.join(matched_cpvs)}")
    if matched_regions:
        reasons.append(f"Matched region: {', '.join(matched_regions)}")

    if total_score >= 50.0:
        decision = "MATCH"
    elif total_score >= 20.0:
        decision = "MANUAL_REVIEW"
    else:
        decision = "REJECT"
        if not reasons:
            reasons.append("Insufficient keyword and domain criteria match")

    return MatchDecision(
        decision=decision,
        score=total_score,
        reasons=reasons,
        matched_keywords=matched_keywords,
        matched_cpvs=matched_cpvs,
        matched_regions=matched_regions,
        exclusion_triggers=[]
    )
