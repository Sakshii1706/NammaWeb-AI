from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from reach.db.compliance_models import (
    ConsentRecord,
    SuppressionRecord,
)


@dataclass(frozen=True)
class ComplianceDecision:
    allowed: bool
    reason: str


class ComplianceService:
    """Workspace-scoped consent and suppression enforcement."""

    def __init__(
        self,
        session,
        workspace_id: int,
    ) -> None:
        if workspace_id <= 0:
            raise ValueError(
                "workspace_id must be a positive integer."
            )

        self.session = session
        self.workspace_id = workspace_id

    # ------------------------------------------------------------------
    # Contact normalization
    # ------------------------------------------------------------------

    @staticmethod
    def normalize_contact(
        channel: str,
        contact_key: str,
    ) -> str:
        channel = channel.strip().lower()
        value = contact_key.strip()

        if not value:
            raise ValueError(
                "contact_key cannot be empty."
            )

        if channel == "email":
            return value.lower()

        if channel == "whatsapp":
            # Keep the phone number representation stable while
            # removing accidental surrounding whitespace.
            return value

        return value

    # ------------------------------------------------------------------
    # Consent
    # ------------------------------------------------------------------

    def grant_consent(
        self,
        *,
        channel: str,
        contact_key: str,
        source: str | None = None,
        notes: str | None = None,
    ) -> ConsentRecord:
        channel = channel.strip().lower()
        contact_key = self.normalize_contact(
            channel,
            contact_key,
        )

        existing = (
            self.session.query(ConsentRecord)
            .filter(
                ConsentRecord.workspace_id == self.workspace_id,
                ConsentRecord.channel == channel,
                ConsentRecord.contact_key == contact_key,
            )
            .first()
        )

        now = datetime.now(timezone.utc)

        if existing:
            existing.status = "granted"
            existing.consented_at = now
            existing.revoked_at = None
            existing.source = source
            existing.notes = notes
            self.session.commit()
            self.session.refresh(existing)
            return existing

        record = ConsentRecord(
            workspace_id=self.workspace_id,
            channel=channel,
            contact_key=contact_key,
            status="granted",
            source=source,
            consented_at=now,
            revoked_at=None,
            notes=notes,
        )

        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)

        return record

    def revoke_consent(
        self,
        *,
        channel: str,
        contact_key: str,
    ) -> ConsentRecord | None:
        channel = channel.strip().lower()
        contact_key = self.normalize_contact(
            channel,
            contact_key,
        )

        record = (
            self.session.query(ConsentRecord)
            .filter(
                ConsentRecord.workspace_id == self.workspace_id,
                ConsentRecord.channel == channel,
                ConsentRecord.contact_key == contact_key,
            )
            .first()
        )

        if record is None:
            return None

        record.status = "revoked"
        record.revoked_at = datetime.now(timezone.utc)

        self.session.commit()
        self.session.refresh(record)

        return record

    def has_valid_consent(
        self,
        *,
        channel: str,
        contact_key: str,
    ) -> bool:
        channel = channel.strip().lower()
        contact_key = self.normalize_contact(
            channel,
            contact_key,
        )

        record = (
            self.session.query(ConsentRecord)
            .filter(
                ConsentRecord.workspace_id == self.workspace_id,
                ConsentRecord.channel == channel,
                ConsentRecord.contact_key == contact_key,
            )
            .first()
        )

        if record is None:
            return False

        return (
            record.status == "granted"
            and record.revoked_at is None
        )

    # ------------------------------------------------------------------
    # Suppression
    # ------------------------------------------------------------------

    def suppress(
        self,
        *,
        channel: str,
        contact_key: str,
        reason: str,
        source: str | None = None,
        notes: str | None = None,
    ) -> SuppressionRecord:
        channel = channel.strip().lower()
        contact_key = self.normalize_contact(
            channel,
            contact_key,
        )

        if not reason.strip():
            raise ValueError(
                "Suppression reason cannot be empty."
            )

        existing = (
            self.session.query(SuppressionRecord)
            .filter(
                SuppressionRecord.workspace_id == self.workspace_id,
                SuppressionRecord.channel == channel,
                SuppressionRecord.contact_key == contact_key,
            )
            .first()
        )

        now = datetime.now(timezone.utc)

        if existing:
            existing.reason = reason.strip()
            existing.source = source
            existing.notes = notes
            existing.suppressed_at = now
            existing.lifted_at = None

            self.session.commit()
            self.session.refresh(existing)

            return existing

        record = SuppressionRecord(
            workspace_id=self.workspace_id,
            channel=channel,
            contact_key=contact_key,
            reason=reason.strip(),
            source=source,
            suppressed_at=now,
            lifted_at=None,
            notes=notes,
        )

        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)

        return record

    def lift_suppression(
        self,
        *,
        channel: str,
        contact_key: str,
    ) -> SuppressionRecord | None:
        channel = channel.strip().lower()
        contact_key = self.normalize_contact(
            channel,
            contact_key,
        )

        record = (
            self.session.query(SuppressionRecord)
            .filter(
                SuppressionRecord.workspace_id == self.workspace_id,
                SuppressionRecord.channel == channel,
                SuppressionRecord.contact_key == contact_key,
            )
            .first()
        )

        if record is None:
            return None

        record.lifted_at = datetime.now(timezone.utc)

        self.session.commit()
        self.session.refresh(record)

        return record

    def is_suppressed(
        self,
        *,
        channel: str,
        contact_key: str,
    ) -> bool:
        channel = channel.strip().lower()
        contact_key = self.normalize_contact(
            channel,
            contact_key,
        )

        record = (
            self.session.query(SuppressionRecord)
            .filter(
                SuppressionRecord.workspace_id == self.workspace_id,
                SuppressionRecord.channel == channel,
                SuppressionRecord.contact_key == contact_key,
            )
            .first()
        )

        if record is None:
            return False

        return record.lifted_at is None

    # ------------------------------------------------------------------
    # Final outbound decision
    # ------------------------------------------------------------------

    def check_can_send(
        self,
        *,
        channel: str,
        contact_key: str,
    ) -> ComplianceDecision:
        channel = channel.strip().lower()
        contact_key = self.normalize_contact(
            channel,
            contact_key,
        )

        if not self.has_valid_consent(
            channel=channel,
            contact_key=contact_key,
        ):
            return ComplianceDecision(
                allowed=False,
                reason="no_valid_consent",
            )

        if self.is_suppressed(
            channel=channel,
            contact_key=contact_key,
        ):
            return ComplianceDecision(
                allowed=False,
                reason="suppressed",
            )

        return ComplianceDecision(
            allowed=True,
            reason="allowed",
        )
