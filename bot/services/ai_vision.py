import json
import logging
from dataclasses import dataclass

from google import genai
from google.genai import types

from bot.config import settings

logger = logging.getLogger(__name__)


@dataclass
class MeterReadingResult:
    value: float | None        # sucet VT+NT alebo jednoduchy odcit
    value_vt: float | None     # vysoky tarif (None ak nie je dual)
    value_nt: float | None     # nizky tarif (None ak nie je dual)
    confidence: float
    meter_description: str
    raw_response: str


@dataclass
class AuditReportResult:
    report_text: str
    summary: str


def _make_image_part(photo_bytes: bytes) -> types.Part:
    return types.Part.from_bytes(data=photo_bytes, mime_type="image/jpeg")


def _extract_json(raw: str) -> dict:
    json_str = raw
    if "```" in raw:
        json_str = raw.split("```")[1]
        if json_str.startswith("json"):
            json_str = json_str[4:]
    return json.loads(json_str.strip())


class AIVisionService:
    def __init__(self):
        self._client: genai.Client | None = None

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        return self._client

    async def read_meter(
        self,
        photo_bytes: bytes,
        meter_type: str | None = None,
        dual_tariff: bool = False,
        reference_photo: bytes | None = None,
    ) -> MeterReadingResult:
        """Recognize meter value from a photo using Gemini Vision."""
        parts: list[types.Part] = []

        if reference_photo:
            parts.append(types.Part.from_text(text="Referencna fotka meraca (pre porovnanie):"))
            parts.append(_make_image_part(reference_photo))

        parts.append(types.Part.from_text(text="Aktualna fotka meraca na odcitanie:"))
        parts.append(_make_image_part(photo_bytes))

        meter_hint = ""
        if meter_type:
            type_sk = {"electricity": "elektromeru", "gas": "plynomeru", "water": "vodomeru"}
            meter_hint = f" Ide o fotku {type_sk.get(meter_type, 'meraca')}."

        if dual_tariff:
            prompt = (
                f"Precitaj hodnoty na elektromeri z fotky.{meter_hint}\n"
                "Tento elektromer ma DVA tarify - VT (vysoky tarif) a NT (nizky tarif).\n"
                "Mozu byt oznacene ako T1/T2, VT/NT, alebo 1/2.\n\n"
                "Odpoved STRIKTNE v JSON formate (nic ine):\n"
                '{"value_vt": 12345.6, "value_nt": 6789.0, "confidence": 0.95, '
                '"meter_description": "kratky popis"}\n\n'
                "- value_vt: hodnota vysokeho tarifu (denne hodiny)\n"
                "- value_nt: hodnota nizkeho tarifu (nocne hodiny)\n"
                "- confidence: 0.0-1.0 ako si isty odcitanim\n"
                "- meter_description: co vidis na fotke"
            )
        else:
            prompt = (
                f"Precitaj aktualnu hodnotu na meraci z fotky.{meter_hint}\n\n"
                "Odpoved STRIKTNE v JSON formate (nic ine):\n"
                '{"value": 12345.6, "confidence": 0.95, "meter_description": "kratky popis"}\n\n'
                "- value: ciselna hodnota na meraci (ak je viac cifernikov, pouzi hlavny)\n"
                "- confidence: 0.0-1.0 ako si isty odcitanim\n"
                "- meter_description: co vidis na fotke"
            )

        parts.append(types.Part.from_text(text=prompt))

        raw = ""
        try:
            response = await self.client.aio.models.generate_content(
                model="gemini-2.0-flash",
                contents=types.Content(role="user", parts=parts),
                config=types.GenerateContentConfig(max_output_tokens=400),
            )
            raw = response.text or ""
            data = _extract_json(raw)

            if dual_tariff:
                vt = float(data["value_vt"])
                nt = float(data["value_nt"])
                return MeterReadingResult(
                    value=vt + nt,
                    value_vt=vt,
                    value_nt=nt,
                    confidence=float(data.get("confidence", 0.5)),
                    meter_description=data.get("meter_description", ""),
                    raw_response=raw,
                )
            else:
                return MeterReadingResult(
                    value=float(data["value"]),
                    value_vt=None,
                    value_nt=None,
                    confidence=float(data.get("confidence", 0.5)),
                    meter_description=data.get("meter_description", ""),
                    raw_response=raw,
                )
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.error("Failed to parse AI response: %s | raw: %s", e, raw)
            return MeterReadingResult(
                value=None, value_vt=None, value_nt=None,
                confidence=0.0, meter_description="", raw_response=raw or str(e),
            )
        except Exception as e:
            logger.error("AI Vision API error: %s", e)
            return MeterReadingResult(
                value=None, value_vt=None, value_nt=None,
                confidence=0.0, meter_description="", raw_response=str(e),
            )

    async def identify_meter(
        self,
        photo_bytes: bytes,
        known_meters: list[dict],
    ) -> int | None:
        """Identify which meter is in the photo. Returns meter_id or None."""
        if not known_meters:
            return None

        parts = [
            _make_image_part(photo_bytes),
            types.Part.from_text(
                text="Mam tieto zaregistrovane merace:\n"
                + "\n".join(
                    f"- ID {m['id']}: {m['name']} ({m['meter_type']}, {m.get('location', '?')})"
                    for m in known_meters
                )
                + "\n\nKtory merac je na fotke? Odpoved STRIKTNE v JSON:\n"
                '{"meter_id": 1, "confidence": 0.9}\n'
                "Ak si neisty alebo merac nerozpoznas, daj confidence < 0.5."
            ),
        ]

        try:
            response = await self.client.aio.models.generate_content(
                model="gemini-2.0-flash",
                contents=types.Content(role="user", parts=parts),
                config=types.GenerateContentConfig(max_output_tokens=200),
            )
            data = _extract_json(response.text or "")
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
        parts: list[types.Part] = []

        for caption, photo_bytes in photos:
            parts.append(_make_image_part(photo_bytes))
            if caption:
                parts.append(types.Part.from_text(text=f"Popis k fotke: {caption}"))

        entries_text = "\n\n".join(
            f"--- Zaznam #{e['id']} od {e['author']} ({e['date']}) ---\n{e.get('text', '(iba fotka)')}"
            for e in entries
        )

        parts.append(types.Part.from_text(
            text="Z nasledujucich zaznamov z kontrol a auditov za tento tyzden "
            "vytvor strukturovany tyzdenny report v slovencine.\n\n"
            f"Zaznamy:\n{entries_text}\n\n"
            "Report ma obsahovat:\n"
            "1. Sumar zisteni (kratky prehlad)\n"
            "2. Detaily jednotlivych kontrol s popisom a vysledkami\n"
            "3. Odporucania (ak su relevantne)\n\n"
            "Format: cisty text bez Markdown, pouzivaj odrazky. Max 2000 znakov.\n\n"
            "Na konci pridaj KRATKY sumar (max 200 znakov) za oddelovacom ---SUMAR---"
        ))

        try:
            response = await self.client.aio.models.generate_content(
                model="gemini-2.0-flash",
                contents=types.Content(role="user", parts=parts),
                config=types.GenerateContentConfig(max_output_tokens=2000),
            )
            raw = response.text or ""

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
