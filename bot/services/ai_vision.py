import base64
import json
import logging
from dataclasses import dataclass

import anthropic

from bot.config import settings

logger = logging.getLogger(__name__)


@dataclass
class MeterReadingResult:
    value: float | None
    confidence: float
    meter_description: str
    raw_response: str


@dataclass
class AuditReportResult:
    report_text: str
    summary: str


class AIVisionService:
    def __init__(self):
        self._client: anthropic.AsyncAnthropic | None = None

    @property
    def client(self) -> anthropic.AsyncAnthropic:
        if self._client is None:
            self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        return self._client

    async def read_meter(
        self,
        photo_bytes: bytes,
        meter_type: str | None = None,
        reference_photo: bytes | None = None,
    ) -> MeterReadingResult:
        """Recognize meter value from a photo using Claude Vision."""
        content = []

        if reference_photo:
            content.append({
                "type": "text",
                "text": "Referencna fotka meraca (pre porovnanie):",
            })
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": base64.standard_b64encode(reference_photo).decode(),
                },
            })

        content.append({
            "type": "text",
            "text": "Aktualna fotka meraca na odcitanie:",
        })
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": base64.standard_b64encode(photo_bytes).decode(),
            },
        })

        meter_hint = ""
        if meter_type:
            type_sk = {"electricity": "elektromeru", "gas": "plynomeru", "water": "vodomeru"}
            meter_hint = f" Ide o fotku {type_sk.get(meter_type, 'meraca')}."

        content.append({
            "type": "text",
            "text": (
                f"Precitaj aktualnu hodnotu na meraci z fotky.{meter_hint}\n\n"
                "Odpoved STRIKTNE v JSON formate (nic ine):\n"
                '{"value": 12345.6, "confidence": 0.95, "meter_description": "kratky popis meraca"}\n\n'
                "- value: ciselna hodnota na meraci (ak je viac cifernikov, pouzi hlavny)\n"
                "- confidence: 0.0-1.0 ako si isty odcitanim\n"
                "- meter_description: co vidis na fotke (typ meraca, znacka ak vidno)"
            ),
        })

        try:
            response = await self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=300,
                messages=[{"role": "user", "content": content}],
            )

            raw = response.content[0].text
            # Extract JSON from response
            json_str = raw
            if "```" in raw:
                json_str = raw.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            json_str = json_str.strip()

            data = json.loads(json_str)
            return MeterReadingResult(
                value=float(data["value"]),
                confidence=float(data.get("confidence", 0.5)),
                meter_description=data.get("meter_description", ""),
                raw_response=raw,
            )
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.error("Failed to parse AI response: %s", e)
            return MeterReadingResult(
                value=None,
                confidence=0.0,
                meter_description="",
                raw_response=raw if "raw" in dir() else str(e),
            )
        except Exception as e:
            logger.error("AI Vision API error: %s", e)
            return MeterReadingResult(
                value=None,
                confidence=0.0,
                meter_description="",
                raw_response=str(e),
            )

    async def identify_meter(
        self,
        photo_bytes: bytes,
        known_meters: list[dict],
    ) -> int | None:
        """Identify which meter is in the photo. Returns meter_id or None."""
        if not known_meters:
            return None

        content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": base64.standard_b64encode(photo_bytes).decode(),
                },
            },
            {
                "type": "text",
                "text": (
                    "Mam tieto zaregistrovane merace:\n"
                    + "\n".join(
                        f"- ID {m['id']}: {m['name']} ({m['meter_type']}, {m.get('location', '?')})"
                        for m in known_meters
                    )
                    + "\n\nKtory merac je na fotke? Odpoved STRIKTNE v JSON:\n"
                    '{"meter_id": 1, "confidence": 0.9}\n'
                    "Ak si neisty alebo merac nerozpoznas, daj confidence < 0.5."
                ),
            },
        ]

        try:
            response = await self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=200,
                messages=[{"role": "user", "content": content}],
            )
            raw = response.content[0].text
            json_str = raw
            if "```" in raw:
                json_str = raw.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            data = json.loads(json_str.strip())
            if data.get("confidence", 0) >= 0.5:
                return int(data["meter_id"])
        except Exception as e:
            logger.error("AI meter identification error: %s", e)
        return None

    async def generate_weekly_report(
        self,
        entries: list[dict],
        photos: list[tuple[str, bytes]],
    ) -> AuditReportResult:
        """Generate weekly audit report from entries and photos."""
        content = []

        # Add photos with captions
        for caption, photo_bytes in photos:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": base64.standard_b64encode(photo_bytes).decode(),
                },
            })
            if caption:
                content.append({"type": "text", "text": f"Popis k fotke: {caption}"})

        # Add text entries
        entries_text = "\n\n".join(
            f"--- Zaznam #{e['id']} od {e['author']} ({e['date']}) ---\n{e.get('text', '(iba fotka)')}"
            for e in entries
        )

        content.append({
            "type": "text",
            "text": (
                "Z nasledujucich zaznamov z kontrol a auditov za tento tyzden "
                "vytvor strukturovany tyzdenny report v slovencine.\n\n"
                f"Zaznamy:\n{entries_text}\n\n"
                "Report ma obsahovat:\n"
                "1. Sumar zisteni (kratky prehlad)\n"
                "2. Detaily jednotlivych kontrol s popisom a vysledkami\n"
                "3. Odporucania (ak su relevantne)\n\n"
                "Format: cistý text bez Markdown, pouzivaj odrazky. Max 2000 znakov.\n\n"
                "Na konci pridaj KRATKY sumar (max 200 znakov) za oddelovacom ---SUMAR---"
            ),
        })

        try:
            response = await self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": content}],
            )
            raw = response.content[0].text

            if "---SUMAR---" in raw:
                report_text, summary = raw.split("---SUMAR---", 1)
            else:
                report_text = raw
                summary = raw[:200]

            return AuditReportResult(
                report_text=report_text.strip(),
                summary=summary.strip(),
            )
        except Exception as e:
            logger.error("AI report generation error: %s", e)
            return AuditReportResult(
                report_text=f"Chyba pri generovani reportu: {e}",
                summary="Chyba pri generovani reportu",
            )


ai_vision_service = AIVisionService()
