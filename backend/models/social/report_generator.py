from __future__ import annotations

from collections import Counter
import os
from typing import Dict, List

import config


class SocialReportGenerator:
    def __init__(self, genai_handler=None) -> None:
        self.genai_handler = genai_handler
        self.use_llm = config.GENAI_USE_LLM and bool(os.getenv("OPENAI_API_KEY", "").strip())

    def _get_genai_handler(self):
        if not self.use_llm:
            return None
        if self.genai_handler is None:
            from models.genai_handler import GenAIHandler
            self.genai_handler = GenAIHandler()
        return self.genai_handler

    @staticmethod
    def _default_summary(area: str, overall_sentiment: str, aspect_analysis: Dict[str, Dict]) -> str:
        positive_aspects = [name for name, data in aspect_analysis.items() if data.get("label") == "positive"]
        negative_aspects = [name for name, data in aspect_analysis.items() if data.get("label") == "negative"]
        mixed_aspects = [name for name, data in aspect_analysis.items() if data.get("label") == "mixed"]

        if not positive_aspects and not negative_aspects and not mixed_aspects:
            return f"Limited social data available around {area}, so there isn't enough signal to confidently profile the area."

        # Create more realistic, balanced summaries
        parts = []

        if positive_aspects:
            positive_text = ", ".join(positive_aspects[:2]) if len(positive_aspects) <= 2 else f"{positive_aspects[0]} and {positive_aspects[1]}"
            parts.append(f"People praise {positive_text}")

        if negative_aspects:
            negative_text = ", ".join(negative_aspects[:2]) if len(negative_aspects) <= 2 else f"{negative_aspects[0]} and {negative_aspects[1]}"
            parts.append(f"but express concerns around {negative_text}")

        if mixed_aspects and not negative_aspects:
            mixed_text = ", ".join(mixed_aspects[:1])
            parts.append(f"discussions are mixed on {mixed_text}")

        if not parts:
            return f"Mixed opinions about {area} with no clear consensus in available discussions."

        summary = ". ".join(parts) + "."
        return f"Reddit conversations paint a nuanced picture of {area}. {summary}"

    @staticmethod
    def _extract_key_insights(posts: List[Dict], aspect_analysis: Dict[str, Dict]) -> List[str]:
        subreddit_counts = Counter(post.get("subreddit", "reddit") for post in posts)
        insights = []

        if subreddit_counts:
            top_subreddit, _ = subreddit_counts.most_common(1)[0]
            insights.append(f"Most of the discussion volume came from r/{top_subreddit}.")

        for aspect, data in aspect_analysis.items():
            label = data.get("label")
            mentions = data.get("mentions", 0)
            if mentions <= 0 or label == "limited_data":
                continue
            insights.append(f"{aspect.capitalize()} is viewed as {label} across {mentions} relevant mentions.")

        for post in posts[:2]:
            text = post.get("text", "").strip()
            if text:
                trimmed = text[:140].rstrip()
                if len(text) > 140:
                    trimmed += "..."
                insights.append(trimmed)

        return insights[:5]

    @staticmethod
    def _build_verdict(area: str, aspect_analysis: Dict[str, Dict]) -> Dict[str, object]:
        positives = [name for name, data in aspect_analysis.items() if data.get("label") == "positive"]
        negatives = [name for name, data in aspect_analysis.items() if data.get("label") == "negative"]
        mixed = [name for name, data in aspect_analysis.items() if data.get("label") == "mixed"]

        # More realistic best_for statements
        if "safety" in positives and "traffic" in negatives and "cost" in negatives:
            best_for = "professionals prioritizing safety who are comfortable with traffic and can afford premium pricing"
        elif "safety" in negatives and "cost" in negatives:
            best_for = "budget buyers with concerns about safety - needs on-ground verification"
        elif "traffic" in negatives and "cost" in positives:
            best_for = "budget-conscious renters willing to tolerate traffic congestion"
        elif "lifestyle" in positives and "cost" in negatives:
            best_for = "young professionals who value lifestyle and nightlife over affordability"
        elif "safety" in positives and "lifestyle" in positives and "traffic" in negatives:
            best_for = "families prioritizing safety and lifestyle despite traffic concerns"
        elif all(v.get("label") == "positive" for v in aspect_analysis.values() if v.get("mentions", 0) > 0):
            best_for = "anyone - this area rates well across most factors"
        else:
            best_for = "those willing to trade off one factor for another - recommend on-ground site visits"

        pros = [item.capitalize() for item in positives[:3]] if positives else []
        cons = [item.capitalize() for item in negatives[:3]] if negatives else []

        if mixed and not cons:
            cons.extend([f"Mixed opinions on {item}" for item in mixed[:1]])

        # More realistic verdict text
        if not pros and not cons:
            verdict_text = f"Limited data on {area}. Recommend on-ground visits to form your own opinion."
        elif not cons:
            verdict_text = f"{area} is well-regarded for {', '.join(pros).lower()}. Good for {best_for}."
        elif not pros:
            verdict_text = f"{area} has significant concerns around {', '.join(cons).lower()}. Only suitable for {best_for}."
        else:
            verdict_text = (
                f"{area} offers {', '.join(pros).lower()} but faces challenges with {', '.join(cons).lower()}. "
                f"Best suited for {best_for}."
            )

        return {
            "best_for": best_for,
            "pros": pros,
            "cons": cons,
            "text": verdict_text,
        }

    def generate_report(
        self,
        area: str,
        normalized_locations: List[str],
        posts: List[Dict],
        overall_sentiment: str,
        aspect_analysis: Dict[str, Dict],
    ) -> Dict:
        summary = self._default_summary(area, overall_sentiment, aspect_analysis)
        insights = self._extract_key_insights(posts, aspect_analysis)
        verdict = self._build_verdict(area, aspect_analysis)

        fallback_report = (
            f"Area: {area}\n\n"
            f"Summary:\n{summary}\n\n"
            f"Key Insights:\n" + "\n".join(f"- {item}" for item in insights) + "\n\n"
            "Aspect Analysis:\n" +
            "\n".join(
                f"- {aspect.capitalize()}: {data.get('label', 'limited_data')}"
                for aspect, data in aspect_analysis.items()
            ) + "\n\n"
            f"Verdict:\n{verdict['text']}"
        )

        instruction = (
            f"Generate a concise structured social intelligence report for {area}. "
            "Use only the provided Reddit-style discussion excerpts and aspect analysis. "
            "Return sections: Summary, Key Insights, Aspect Analysis, Verdict. "
            "Do not invent new facts."
        )
        context_chunks = [
            f"Area input: {area}",
            f"Normalized locations: {', '.join(normalized_locations) if normalized_locations else area}",
            f"Overall sentiment: {overall_sentiment}",
        ]
        context_chunks.extend(
            f"{aspect.capitalize()}: {data.get('label')} ({data.get('mentions', 0)} mentions)"
            for aspect, data in aspect_analysis.items()
        )
        context_chunks.extend(post.get("text", "")[:220] for post in posts[:5])

        handler = self._get_genai_handler()
        if handler is None:
            report_markdown = fallback_report
        else:
            report_markdown = handler._generate_with_guardrails(
                task="chat",
                instruction=instruction,
                fallback_text=fallback_report,
                context_chunks=context_chunks,
                verify_grounding=True,
            )

        return {
            "summary": summary,
            "key_insights": insights,
            "aspect_analysis": aspect_analysis,
            "verdict": verdict,
            "report_markdown": report_markdown,
        }
