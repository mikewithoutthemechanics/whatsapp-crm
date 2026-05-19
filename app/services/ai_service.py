"""
WhatsApp CRM SA — AI Auto-Response Engine
==========================================
Powered by Groq (free, 14,400 req/day) and/or OpenRouter (free fallback).
Handles: greeting responses, product inquiries, pricing questions,
hours/location queries, lead qualification, and conversation summaries.
"""

import time
import json
import os
import sys
import requests
from datetime import datetime
from typing import Optional, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import settings


class AIEngine:
    """AI-powered auto-response engine for WhatsApp CRM."""

    def __init__(self):
        self.groq_key = settings.GROQ_API_KEY
        self.or_key = settings.OPENROUTER_API_KEY
        self.provider = settings.AI_PROVIDER
        self.request_counts = {"groq": 0, "openrouter": 0}

    # ─── Groq API ──────────────────────────────────────────────
    def _call_groq(self, prompt: str, model: str = "llama-3.1-8b-instant",
                    max_tokens: int = 500) -> Optional[str]:
        """Call Groq Console API. Free: 30 RPM, 14,400 RPD."""
        url = "https://api.groq.com/openai/v1/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.5
        }

        headers = {"Content-Type": "application/json"}
        if self.groq_key:
            headers["Authorization"] = f"Bearer {self.groq_key}"

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=15)
            self.request_counts["groq"] += 1

            if resp.status_code == 429:
                time.sleep(5)
                return self._call_groq(prompt, model, max_tokens)
            if resp.status_code == 401:
                return None

            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"Groq error: {e}")
            return None

    # ─── OpenRouter API ────────────────────────────────────────
    def _call_openrouter(self, prompt: str,
                         model: str = "deepseek/deepseek-r1:free",
                         max_tokens: int = 500) -> Optional[str]:
        """Call OpenRouter Free Models. Free: 50 RPD, 20 RPM."""
        url = "https://openrouter.ai/api/v1/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.5
        }

        headers = {
            "Content-Type": "application/json",
            "HTTP-Referer": settings.APP_URL,
        }
        if self.or_key:
            headers["Authorization"] = f"Bearer {self.or_key}"

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=15)
            self.request_counts["openrouter"] += 1
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"OpenRouter error: {e}")
            return None

    # ─── Smart Routing ─────────────────────────────────────────
    def generate_response(self, user_message: str, context: Dict = None) -> Optional[str]:
        """Route to best available AI provider."""
        prompt = self._build_prompt(user_message, context)

        if self.provider == "groq":
            result = self._call_groq(prompt)
            if result is None and self.or_key:
                result = self._call_openrouter(prompt)
        elif self.provider == "openrouter":
            result = self._call_openrouter(prompt)
            if result is None and self.groq_key:
                result = self._call_groq(prompt)
        else:  # auto
            result = self._call_groq(prompt)
            if result is None:
                result = self._call_openrouter(prompt)

        if result is None:
            result = self._template_response(user_message)

        return result

    def _build_prompt(self, user_message: str, context: Dict = None) -> str:
        """Build the full prompt with business context."""
        ctx = context or {}
        business_name = ctx.get("business_name", "our business")
        business_type = ctx.get("business_type", "service")
        services = ctx.get("services", [])
        location = ctx.get("location", "South Africa")
        business_hours = f"{settings.BUSINESS_HOURS_START}:00-{settings.BUSINESS_HOURS_END}:00 SAST"

        services_text = ", ".join(services) if services else "our services"

        return f"""You are a helpful WhatsApp customer service agent for a South African business.

BUSINESS: {business_name}
TYPE: {business_type}
SERVICES: {services_text}
LOCATION: {location}
BUSINESS HOURS: {business_hours}
CURRENCY: ZAR (R)

Respond to this customer message in a friendly, professional South African tone:

CUSTOMER MESSAGE: "{user_message}"

Guidelines:
- Use South African English (colour, favourite, etc.)
- Be concise — WhatsApp messages should be short
- If asked about pricing, ask them to specify what they need so you can quote
- If asked outside business hours, acknowledge and mention when you're next available
- Always end with a helpful question or call-to-action
- If you don't understand, ask for clarification
- Never make up specific prices, addresses, or dates
- Use emojis sparingly (👋 💬 ✅ 📞)
- If they seem like a potential customer, try to qualify them (what service are they looking for?)

Respond in 1-3 short messages maximum."""

    def _system_prompt(self) -> str:
        return """You are a WhatsApp CRM agent for a South African SMME.
Respond in a helpful, friendly tone using South African English.
Keep messages short and actionable for mobile chat.
Always be honest — never make up pricing, availability, or details."""

    # ─── Intent Detection ─────────────────────────────────────
    def detect_intent(self, message: str) -> Dict:
        """Classify customer intent from their message."""
        message_lower = message.lower()

        intents = {
            "greeting": ["hi", "hello", "hey", "good morning", "good afternoon",
                        "howzit", "how are you", "yo", "sup"],
            "pricing": ["price", "cost", "how much", "quote", "quote me",
                        "what do you charge", "rates", "pricing"],
            "availability": ["available", "in stock", "do you have", "can i get",
                             "when will", "how long", "delivery time"],
            "booking": ["book", "make an appointment", "schedule", "when can you",
                        "i need", "can you come", "send someone"],
            "complaint": ["problem", "issue", "broken", "wrong", "refund",
                         "return", "not working", "damaged", "terrible"],
            "feedback": ["review", "feedback", "rate", "testimonial"],
            "goodbye": ["bye", "thanks", "thank you", "see you", "later",
                       "appreciate", "cheers"],
            "general": []  # catch-all
        }

        scores = {}
        for intent, keywords in intents.items():
            score = sum(1 for kw in keywords if kw in message_lower)
            scores[intent] = score

        # Normalize
        max_score = max(scores.values()) if scores else 0
        if max_score == 0:
            return {"intent": "general", "confidence": 0.0, "scores": scores}

        best = max(scores, key=scores.get)
        confidence = scores[best] / max(1, sum(1 for s in scores.values() if s > 0))

        return {
            "intent": best,
            "confidence": round(confidence, 2),
            "scores": scores,
        }

    def is_after_hours(self) -> bool:
        """Check if current time is outside business hours (SAST)."""
        now = datetime.now()
        hour = now.hour
        return hour < settings.BUSINESS_HOURS_START or hour >= settings.BUSINESS_HOURS_END

    def after_hours_reply(self) -> str:
        """Auto-reply for messages outside business hours."""
        return (
            "👋 Thanks for reaching out! We're currently outside business hours "
            f"({settings.BUSINESS_HOURS_START}:00–{settings.BUSINESS_HOURS_END}:00 SAST).\n\n"
            "We'll get back to you first thing tomorrow! 💬\n"
            "For urgent matters, feel free to call us."
        )

    # ─── Template Fallback ────────────────────────────────────
    def _template_response(self, user_message: str) -> str:
        """Template-based response when AI is unavailable."""
        greetings = ["Hi there! 👋", "Hello!", "Hey! How can I help?"]

        if any(w in user_message.lower() for w in ["hi", "hello", "hey"]):
            return "Hi! 👋 Thanks for messaging us. How can I help you today?"
        elif any(w in user_message.lower() for w in ["price", "cost", "how much"]):
            return "Thanks for your interest! Could you tell me a bit more about what you need? I'll send you a quote. 😊"
        elif any(w in user_message.lower() for w in ["thanks", "bye", "later"]):
            return "You're welcome! Feel free to reach out anytime. Have a great day! 👋"
        else:
            return (
                "Thanks for your message! 🙏\n"
                "We'll get back to you as soon as possible. "
                "Can you tell me a bit more about what you need?"
            )


# Convenience for direct import
ai_engine = AIEngine()


if __name__ == "__main__":
    # Test AI response
    engine = AIEngine()

    test_messages = [
        "Hi, how much for a plumbing job?",
        "Are you available tomorrow?",
        "I have a problem with my order",
    ]

    for msg in test_messages:
        print(f"\n🗨️  Customer: {msg}")
        response = engine.generate_response(msg, context={
            "business_name": "Test Plumbing",
            "business_type": "plumbing",
            "services": ["pipe repair", "installation", "maintenance"],
            "location": "Johannesburg, Gauteng",
        })
        print(f"🤖 Agent: {response}")