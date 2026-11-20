"""Tests for the NLP layer (KAN-19). No network: providers are faked."""

import json
import unittest
from dataclasses import dataclass

from gloss_sequence import GlossToken, GlossSequence
from nlp import GeminiProvider, LLMError, NLPService, SentenceStatus, build_provider
from nlp.prompt import MISSING_MARKER, UNCERTAIN_MARKER, build_user_prompt

# Armenian test sentences (written as escapes to keep this file ASCII).
SENTENCE_OK = "Ես ջուր եմ ուզում։"
GLOSS_I, GLOSS_WATER, GLOSS_WANT = "ԵՍ", "ՋՈՒՐ", "ՈՒԶԵԼ"


def token(gloss, status="accepted", start=0):
    return GlossToken(gloss=gloss, confidence=0.9, start_ms=start, end_ms=start + 500, status=status)


def sequence(glosses=(GLOSS_I, GLOSS_WATER, GLOSS_WANT), gaps=(), statuses=None):
    statuses = statuses or ["accepted"] * len(glosses)
    tokens = [token(g, s, i * 1000) for i, (g, s) in enumerate(zip(glosses, statuses))]
    return GlossSequence(session_id="s1", utterance_id=1, tokens=tokens, gaps=list(gaps))


class FakeProvider:
    name = "fake"
    model = "fake-1"

    def __init__(self, answer=None, error=None):
        self.answer, self.error, self.calls = answer, error, []

    def generate(self, system, user):
        self.calls.append((system, user))
        if self.error:
            raise self.error
        return self.answer


def answer(sentence=SENTENCE_OK, complete=True, omitted=()):
    return json.dumps({"sentence": sentence, "complete": complete, "omitted": list(omitted)})


class PromptTests(unittest.TestCase):
    def test_lists_glosses_in_order_with_markers(self):
        seq = sequence(statuses=["accepted", "uncertain", "accepted"], gaps=[1])
        text = build_user_prompt(seq.tokens, seq.gaps, ["earlier one"])
        lines = text.splitlines()
        self.assertEqual(lines[1], f"1. {GLOSS_I}")
        self.assertEqual(lines[2], f"2. {MISSING_MARKER}")
        self.assertEqual(lines[3], f"3. {GLOSS_WATER} {UNCERTAIN_MARKER}")
        self.assertEqual(lines[4], f"4. {GLOSS_WANT}")
        self.assertIn("- earlier one", text)

    def test_gap_after_last_gloss(self):
        seq = sequence(gaps=[3])
        self.assertTrue(build_user_prompt(seq.tokens, seq.gaps, []).endswith(MISSING_MARKER))

    def test_no_context_block_when_empty(self):
        self.assertNotIn("Context", build_user_prompt(sequence().tokens, [], []))


class NLPServiceTests(unittest.TestCase):
    def run_service(self, provider, seq=None, context=()):
        return NLPService(provider).generate_sync(seq or sequence(), context)

    def test_clean_sequence_is_ok(self):
        provider = FakeProvider(answer())
        result = self.run_service(provider)
        self.assertEqual(result.status, SentenceStatus.OK)
        self.assertEqual(result.text, SENTENCE_OK)
        self.assertEqual(result.warnings, [])
        self.assertEqual((result.session_id, result.utterance_id), ("s1", 1))
        self.assertEqual((result.provider, result.model), ("fake", "fake-1"))
        self.assertEqual(len(provider.calls), 1)

    def test_gaps_and_uncertain_make_it_partial(self):
        seq = sequence(statuses=["accepted", "uncertain", "accepted"], gaps=[1])
        result = self.run_service(FakeProvider(answer()), seq)
        self.assertEqual(result.status, SentenceStatus.PARTIAL)
        self.assertEqual(result.warnings, ["missing_glosses", "uncertain_glosses"])

    def test_model_reports_incomplete_or_omitted(self):
        result = self.run_service(FakeProvider(answer(complete=False, omitted=[GLOSS_WATER])))
        self.assertEqual(result.status, SentenceStatus.PARTIAL)
        self.assertEqual(result.warnings, ["omitted_glosses", "incomplete"])

    def test_json_in_code_fence_is_accepted(self):
        fenced = "```json\n" + answer() + "\n```"
        self.assertEqual(self.run_service(FakeProvider(fenced)).status, SentenceStatus.OK)

    def test_context_is_limited_and_sent(self):
        provider = FakeProvider(answer())
        self.run_service(provider, context=["c1", "c2", "c3", "c4"])
        prompt = provider.calls[0][1]
        self.assertNotIn("- c1", prompt)
        self.assertIn("- c2", prompt)
        self.assertIn("- c4", prompt)

    def test_not_configured_falls_back_to_glosses(self):
        result = self.run_service(None)
        self.assertEqual(result.status, SentenceStatus.FALLBACK)
        self.assertEqual(result.text, f"{GLOSS_I} {GLOSS_WATER} {GLOSS_WANT}")
        self.assertIn("llm_not_configured", result.warnings)
        self.assertIsNone(result.provider)

    def test_provider_error_falls_back(self):
        result = self.run_service(FakeProvider(error=LLMError("timeout")))
        self.assertEqual(result.status, SentenceStatus.FALLBACK)
        self.assertIn("llm_timeout", result.warnings)
        self.assertEqual(result.text, f"{GLOSS_I} {GLOSS_WATER} {GLOSS_WANT}")

    def test_invalid_outputs_fall_back(self):
        bad = {
            "not json": "hello",
            "no sentence": json.dumps({"complete": True}),
            "empty": answer(""),
            "not armenian": answer("I want water."),
            "invented digits": answer("Ես 5 ջուր եմ ուզում։"),
            "far too long": answer(" ".join(["բարեւ"] * 30)),
        }
        for name, raw in bad.items():
            with self.subTest(name):
                result = self.run_service(FakeProvider(raw))
                self.assertEqual(result.status, SentenceStatus.FALLBACK)
                self.assertIn("invalid_output", result.warnings)

    def test_digits_allowed_when_glosses_have_digits(self):
        seq = sequence(glosses=("ԵՍ", "5"))
        raw = answer("Ես 5 հոգի եմ։")
        self.assertEqual(self.run_service(FakeProvider(raw), seq).status, SentenceStatus.OK)

    def test_message_format(self):
        msg = self.run_service(FakeProvider(answer())).to_message()
        self.assertEqual(msg["type"], "sentence")
        self.assertEqual(msg["status"], "ok")
        self.assertEqual(msg["text"], SENTENCE_OK)
        self.assertEqual(msg["utteranceId"], 1)
        self.assertEqual(msg["sessionId"], "s1")
        self.assertEqual(msg["glossText"], f"{GLOSS_I} {GLOSS_WATER} {GLOSS_WANT}")
        for key in ("warnings", "provider", "model", "latencyMs"):
            self.assertIn(key, msg)


class GeminiProviderTests(unittest.TestCase):
    def make(self, responses, **kwargs):
        calls = []

        def transport(url, headers, body, timeout):
            calls.append((url, dict(headers), json.loads(body), timeout))
            item = responses.pop(0)
            if isinstance(item, Exception):
                raise item
            return item

        provider = GeminiProvider("KEY", model="m1", transport=transport, retry_delay=0, **kwargs)
        return provider, calls

    @staticmethod
    def ok(text):
        body = {"candidates": [{"content": {"parts": [{"text": text}]}}]}
        return 200, json.dumps(body).encode()

    def test_request_shape_and_text(self):
        provider, calls = self.make([self.ok("hello")])
        self.assertEqual(provider.generate("SYS", "USER"), "hello")
        url, headers, body, _ = calls[0]
        self.assertTrue(url.endswith("/models/m1:generateContent"))
        self.assertNotIn("KEY", url)  # the key is only in a header
        self.assertEqual(headers["x-goog-api-key"], "KEY")
        self.assertEqual(body["systemInstruction"]["parts"][0]["text"], "SYS")
        self.assertEqual(body["contents"][0]["parts"][0]["text"], "USER")
        self.assertEqual(body["generationConfig"]["responseMimeType"], "application/json")

    def test_thought_parts_are_ignored(self):
        body = {"candidates": [{"content": {"parts": [{"text": "x", "thought": True}, {"text": "ANSWER"}]}}]}
        provider, _ = self.make([(200, json.dumps(body).encode())])
        self.assertEqual(provider.generate("s", "u"), "ANSWER")

    def test_retries_on_429_then_succeeds(self):
        provider, calls = self.make([(429, b"{}"), self.ok("fine")], max_retries=1)
        self.assertEqual(provider.generate("s", "u"), "fine")
        self.assertEqual(len(calls), 2)

    def test_rate_limit_after_retries(self):
        provider, calls = self.make([(429, b"{}"), (429, b"{}")], max_retries=1)
        with self.assertRaises(LLMError) as ctx:
            provider.generate("s", "u")
        self.assertEqual(ctx.exception.code, "rate_limited")
        self.assertEqual(len(calls), 2)

    def test_client_error_is_not_retried(self):
        provider, calls = self.make([(400, b"{}")], max_retries=3)
        with self.assertRaises(LLMError) as ctx:
            provider.generate("s", "u")
        self.assertEqual(ctx.exception.code, "http_error")
        self.assertEqual(len(calls), 1)

    def test_timeout(self):
        provider, _ = self.make([TimeoutError(), TimeoutError()], max_retries=1)
        with self.assertRaises(LLMError) as ctx:
            provider.generate("s", "u")
        self.assertEqual(ctx.exception.code, "timeout")

    def test_blocked_and_empty_answers(self):
        blocked = {"promptFeedback": {"blockReason": "SAFETY"}}
        provider, _ = self.make([(200, json.dumps(blocked).encode())])
        with self.assertRaises(LLMError) as ctx:
            provider.generate("s", "u")
        self.assertEqual(ctx.exception.code, "blocked")

        provider, _ = self.make([(200, b'{"candidates": []}')])
        with self.assertRaises(LLMError) as ctx:
            provider.generate("s", "u")
        self.assertEqual(ctx.exception.code, "bad_response")

        provider, _ = self.make([(200, b"not json")])
        with self.assertRaises(LLMError) as ctx:
            provider.generate("s", "u")
        self.assertEqual(ctx.exception.code, "bad_response")

    def test_error_text_never_contains_the_key(self):
        provider, _ = self.make([(403, b'{"error": "KEY is invalid"}')])
        with self.assertRaises(LLMError) as ctx:
            provider.generate("s", "u")
        self.assertNotIn("KEY", str(ctx.exception))


class BuildProviderTests(unittest.TestCase):
    def test_gemini_with_key(self):
        provider = build_provider({"LLM_PROVIDER": "gemini", "GEMINI_API_KEY": "k", "LLM_MODEL": "m2"})
        self.assertIsInstance(provider, GeminiProvider)
        self.assertEqual(provider.model, "m2")

    def test_defaults_to_gemini(self):
        self.assertIsInstance(build_provider({"GEMINI_API_KEY": "k"}), GeminiProvider)

    def test_missing_key_disabled_or_unknown_gives_none(self):
        self.assertIsNone(build_provider({"LLM_PROVIDER": "gemini"}))
        self.assertIsNone(build_provider({"LLM_PROVIDER": "none", "GEMINI_API_KEY": "k"}))
        self.assertIsNone(build_provider({"LLM_PROVIDER": "something", "GEMINI_API_KEY": "k"}))

    def test_bad_timeout_value_uses_default(self):
        provider = build_provider({"GEMINI_API_KEY": "k", "LLM_TIMEOUT_SECONDS": "abc"})
        self.assertEqual(provider.timeout, 10.0)


if __name__ == "__main__":
    unittest.main()
