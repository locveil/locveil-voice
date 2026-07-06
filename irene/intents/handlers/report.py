"""
Problem Report Intent Handler — «сообщи о проблеме» (ARCH-30 design, ARCH-31 build).

Two-turn dialog: the intent fires → the handler arms a VERBATIM capture (the workflow consumes
the next utterance raw, before the QUAL-44 arbitration — a description like «свет не включается»
must never execute as a command) → the description lands back here and is handed to the report
service (the ARCH-32 delivery path). With reporting unconfigured the intent answers honestly at
turn one and never arms anything. Full design: docs/design/problem_reports.md.
"""

import logging
from typing import Any, Dict, List, Optional

from .base import IntentHandler
from ..models import Intent, IntentResult
from ..context_models import UnifiedConversationContext

logger = logging.getLogger(__name__)

# Recognition constants for ending the capture (not user-facing speech — replies come from
# templates). Matched against the whole trimmed utterance, casefolded, trailing punctuation off.
_CANCEL_WORDS = frozenset({
    "отмена", "отменить", "не важно", "неважно", "забудь",
    "cancel", "never mind", "nevermind", "forget it",
})


class ReportIntentHandler(IntentHandler):
    """Files user problem reports through the configured report service (ARCH-30)."""

    def __init__(self):
        super().__init__()
        # Injected by the composition root when [reports] is enabled (ARCH-32). None ⇒ the
        # intent answers that reporting isn't set up — the dialog is never armed half-working.
        self.report_service: Optional[Any] = None
        self.capture_ttl_seconds: float = 90.0

    def set_report_service(self, service: Optional[Any],
                           capture_ttl_seconds: float = 90.0) -> None:
        """Inject the delivery service + the D-5 capture window (from `[reports]`)."""
        self.report_service = service
        self.capture_ttl_seconds = capture_ttl_seconds

    @classmethod
    def get_python_dependencies(cls) -> List[str]:
        return []

    @classmethod
    def get_platform_dependencies(cls) -> Dict[str, List[str]]:
        return {"linux.ubuntu": [], "linux.alpine": [], "macos": [], "windows": []}

    async def execute(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        return await self.execute_with_donation_routing(intent, context)

    async def is_available(self) -> bool:
        return True

    @staticmethod
    def _is_cancel(text: str) -> bool:
        return text.strip().rstrip(".!,").casefold() in _CANCEL_WORDS

    async def _handle_problem(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        language = context.language
        if self.report_service is None:
            return IntentResult(
                text=self._get_template("err_unconfigured", language),
                should_speak=True, success=False,
                error="problem reporting not configured ([reports] disabled)")

        description = self.get_param(intent, "description", default=None)
        if not description:
            # Turn 1: arm the verbatim capture — the workflow hands the NEXT utterance straight
            # back to this intent as `description`, raw (design §2).
            context.set_pending_clarification(
                "report.problem", "description", intent.raw_text,
                mode="verbatim", ttl_seconds=self.capture_ttl_seconds)
            return IntentResult(
                text=self._get_template("ask_description", language),
                should_speak=True,
                metadata={"clarification": True, "clarification_reason": "report_description"})

        # Turn 2: the captured description (or an escape word).
        if self._is_cancel(str(description)):
            return IntentResult(text=self._get_template("cancelled", language),
                                should_speak=True)

        try:
            status = await self.report_service.submit(str(description), context)
        except Exception as e:
            logger.error(f"Problem report submission failed: {e}")
            return IntentResult(
                text=self._template_or("err_failed", language,
                                       "Не получилось отправить отчёт."),
                should_speak=True, success=False, error=str(e))

        key = "confirm_spooled" if status == "spooled" else "confirm_sent"
        return IntentResult(text=self._get_template(key, language), should_speak=True,
                            metadata={"report_status": status})
