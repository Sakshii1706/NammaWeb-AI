from __future__ import annotations

from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

import streamlit as st

IST = ZoneInfo("Asia/Kolkata")

from reach.db import get_session
from reach.campaigns.campaign_service import CampaignService
from reach.campaigns.compliance_service import ComplianceService
from reach.campaigns.campaign_execution_service import CampaignExecutionService
from reach.providers.fake_providers import FakeEmailProvider, FakeWhatsAppProvider
from reach.providers.registry import ProviderRegistry


def _contact_key(channel: str, email: str | None, phone: str | None) -> str:
    if channel == "email":
        return (email or "").strip().lower()
    return (phone or "").strip()


def render_campaigns_ui(workspace_id: int) -> None:
    st.divider()
    st.header("Campaigns")
    st.caption(
        "Create campaigns, manage recipients, and record channel consent. "
        "Test-mode execution is enabled; real sending is not."
    )

    session = get_session()

    try:
        campaigns = CampaignService(session, workspace_id)
        compliance = ComplianceService(session, workspace_id)

        create_tab, manage_tab, history_tab = st.tabs(
            [
                "Create campaign",
                "Manage campaign",
                "Delivery history",
            ]
        )

        with create_tab:
            st.subheader("Create campaign")

            with st.form("create_campaign_form", clear_on_submit=False):
                name = st.text_input(
                    "Campaign name",
                    placeholder="Example: October product update",
                )

                channel = st.selectbox(
                    "Channel",
                    options=["email", "whatsapp"],
                )

                subject = None
                if channel == "email":
                    subject = st.text_input(
                        "Email subject",
                        placeholder="Example: New product update",
                    )

                description = st.text_area(
                    "Description",
                    placeholder="Optional campaign description",
                )

                message_template = st.text_area(
                    "Message template",
                    placeholder=(
                        "Hello {{full_name}},\n\n"
                        "We have an important update for you."
                    ),
                    height=180,
                    help=(
                        "Supported placeholders: "
                        "{{full_name}}, {{email}}, {{phone}}"
                    ),
                )

                st.markdown("#### Delivery")

                delivery_mode = st.radio(
                    "Campaign mode",
                    options=[
                        "Save as draft",
                        "Schedule campaign",
                    ],
                    horizontal=True,
                )

                schedule_date = st.date_input(
                    "Schedule date (IST)",
                    value=datetime.now(IST).date(),
                )

                schedule_time = st.time_input(
                    "Schedule time (IST)",
                    value=time(
                        hour=datetime.now(IST).hour,
                        minute=datetime.now(IST).minute,
                    ),
                )

                submitted = st.form_submit_button(
                    "Create campaign",
                    type="primary",
                )

                if submitted:
                    if not name.strip():
                        st.error("Campaign name is required.")
                    elif not message_template.strip():
                        st.error("Message template is required.")
                    elif channel == "email" and not (subject or "").strip():
                        st.error("Email subject is required.")
                    else:
                        scheduled_at = None

                        if delivery_mode == "Schedule campaign":
                            scheduled_at_ist = datetime.combine(
                                schedule_date,
                                schedule_time,
                            ).replace(tzinfo=IST)

                            scheduled_at = scheduled_at_ist.astimezone(timezone.utc)
                            now_utc = datetime.now(timezone.utc)

                            if scheduled_at <= now_utc:
                                st.error(
                                    "Scheduled time must be in the future."
                                )
                                scheduled_at = None
                            else:
                                campaign = campaigns.create_campaign(
                                    name=name.strip(),
                                    message_template=message_template.strip(),
                                    channel=channel,
                                    description=description.strip() or None,
                                    subject=(
                                        subject.strip()
                                        if subject
                                        else None
                                    ),
                                    scheduled_at=scheduled_at,
                                )

                                campaigns.update_campaign_status(
                                    campaign.id,
                                    "scheduled",
                                )

                                st.success(
                                    f"Campaign #{campaign.id} scheduled "
                                    f"for {scheduled_at.astimezone(IST).strftime('%Y-%m-%d %H:%M IST')}."
                                )

                        if (
                            delivery_mode == "Save as draft"
                            and scheduled_at is None
                        ):
                            campaign = campaigns.create_campaign(
                                name=name.strip(),
                                message_template=message_template.strip(),
                                channel=channel,
                                description=description.strip() or None,
                                subject=(
                                    subject.strip()
                                    if subject
                                    else None
                                ),
                                scheduled_at=None,
                            )

                            st.success(
                                f"Draft campaign created: "
                                f"#{campaign.id} — {campaign.name}"
                            )

            st.info(
                "Scheduling stores the campaign with a future UTC time. "
                "The separate campaign scheduler process must be running "
                "for scheduled campaigns to execute."
            )

        with manage_tab:
            st.subheader("Manage campaign")

            available_campaigns = campaigns.list_campaigns()

            if not available_campaigns:
                st.info("No campaigns created yet.")
            else:
                campaign_options = {
                    f"#{item.id} — {item.name} ({item.status})": item.id
                    for item in available_campaigns
                }

                selected_label = st.selectbox(
                    "Select campaign",
                    options=list(campaign_options.keys()),
                    key="campaign_manage_select",
                )

                selected_campaign = campaigns.get_campaign(
                    campaign_options[selected_label]
                )

                if selected_campaign is None:
                    st.error("Selected campaign could not be found.")
                else:
                    st.markdown(
                        f"**Channel:** `{selected_campaign.channel}`"
                    )
                    st.markdown(
                        f"**Status:** `{selected_campaign.status}`"
                    )

                    if selected_campaign.scheduled_at:
                        st.markdown(
                            "**Scheduled for:** "
                            f"`{(selected_campaign.scheduled_at.replace(tzinfo=timezone.utc) if selected_campaign.scheduled_at.tzinfo is None else selected_campaign.scheduled_at).astimezone(IST).strftime('%Y-%m-%d %H:%M IST')}`"
                        )

                    if selected_campaign.description:
                        st.markdown(
                            f"**Description:** "
                            f"{selected_campaign.description}"
                        )

                    if selected_campaign.subject:
                        st.markdown(
                            f"**Subject:** {selected_campaign.subject}"
                        )

                    st.markdown("##### Message preview")
                    st.code(
                        selected_campaign.message_template,
                        language="text",
                    )

                    st.divider()

                    st.markdown("##### Add recipient")

                    with st.form(
                        "add_campaign_recipient_form",
                        clear_on_submit=True,
                    ):
                        full_name = st.text_input(
                            "Full name",
                            placeholder="Example: John Doe",
                        )

                        email = None
                        phone = None

                        if selected_campaign.channel == "email":
                            email = st.text_input(
                                "Email",
                                placeholder="john@example.com",
                            )
                        else:
                            phone = st.text_input(
                                "Phone",
                                placeholder="+919876543210",
                            )

                        grant_consent = st.checkbox(
                            "Grant consent for this channel",
                            value=False,
                        )

                        consent_source = st.text_input(
                            "Consent source",
                            placeholder="Example: website form",
                        )

                        add_recipient = st.form_submit_button(
                            "Add recipient",
                            type="primary",
                        )

                        if add_recipient:
                            try:
                                recipient = campaigns.add_recipient(
                                    selected_campaign.id,
                                    full_name=full_name.strip() or None,
                                    email=email.strip() if email else None,
                                    phone=phone.strip() if phone else None,
                                )

                                if grant_consent:
                                    contact = _contact_key(
                                        selected_campaign.channel,
                                        email,
                                        phone,
                                    )

                                    compliance.grant_consent(
                                        channel=selected_campaign.channel,
                                        contact_key=contact,
                                        source=(
                                            consent_source.strip()
                                            or "campaign UI"
                                        ),
                                    )

                                session.commit()

                                st.success(
                                    f"Recipient #{recipient.id} added."
                                )
                                st.rerun()

                            except Exception as exc:
                                session.rollback()
                                st.error(
                                    f"Could not add recipient: {exc}"
                                )

                    recipients = campaigns.list_recipients(
                        selected_campaign.id
                    )

                    st.divider()

                    st.markdown("##### Campaign execution — TEST MODE")

                    st.caption(
                        "Execution uses only fake providers. "
                        "No real email or WhatsApp messages are sent."
                    )

                    if selected_campaign.status == "cancelled":
                        st.warning(
                            "Cancelled campaigns cannot be executed."
                        )
                    else:
                        eligible = 0
                        blocked = 0

                        for recipient in recipients:
                            contact = _contact_key(
                                selected_campaign.channel,
                                recipient.email,
                                recipient.phone,
                            )

                            decision = compliance.check_can_send(
                                channel=selected_campaign.channel,
                                contact_key=contact,
                            )

                            if decision.allowed:
                                eligible += 1
                            else:
                                blocked += 1

                        metric_col1, metric_col2 = st.columns(2)

                        metric_col1.metric(
                            "Eligible",
                            eligible,
                        )

                        metric_col2.metric(
                            "Blocked",
                            blocked,
                        )

                        if st.button(
                            "Run test execution",
                            key=f"execute_campaign_{selected_campaign.id}",
                            type="primary",
                        ):
                            try:
                                fake_email_provider = FakeEmailProvider()
                                fake_whatsapp_provider = FakeWhatsAppProvider()

                                provider_registry = ProviderRegistry()
                                provider_registry.register(
                                    fake_email_provider
                                )
                                provider_registry.register(
                                    fake_whatsapp_provider
                                )

                                execution_service = (
                                    CampaignExecutionService(
                                        campaigns,
                                        compliance,
                                        provider_registry,
                                    )
                                )

                                execution_result = (
                                    execution_service.execute_campaign(
                                        workspace_id=workspace_id,
                                        campaign_id=selected_campaign.id,
                                    )
                                )

                                st.success(
                                    "Test campaign execution completed."
                                )

                                result_col1, result_col2, result_col3 = (
                                    st.columns(3)
                                )

                                result_col1.metric(
                                    "Sent",
                                    execution_result.sent,
                                )

                                result_col2.metric(
                                    "Skipped",
                                    execution_result.skipped,
                                )

                                result_col3.metric(
                                    "Failed",
                                    execution_result.failed,
                                )

                                st.caption(
                                    f"Processed "
                                    f"{execution_result.total_recipients} "
                                    "recipient(s) using the fake provider."
                                )

                                if selected_campaign.channel == "email":
                                    fake_messages = (
                                        fake_email_provider.sent_messages
                                    )
                                else:
                                    fake_messages = (
                                        fake_whatsapp_provider.sent_messages
                                    )

                                if fake_messages:
                                    st.markdown(
                                        "##### Fake provider activity"
                                    )

                                    st.dataframe(
                                        [
                                            {
                                                "Recipient": request.recipient,
                                                "Name": (
                                                    request.recipient_name
                                                    or ""
                                                ),
                                                "Subject": (
                                                    request.subject
                                                    or ""
                                                ),
                                                "Message": request.message,
                                            }
                                            for request in fake_messages
                                        ],
                                        use_container_width=True,
                                        hide_index=True,
                                    )

                                if execution_result.skipped:
                                    st.warning(
                                        f"{execution_result.skipped} "
                                        "recipient(s) were blocked by "
                                        "the compliance gate."
                                    )

                                if execution_result.failed:
                                    st.error(
                                        f"{execution_result.failed} "
                                        "recipient(s) failed during "
                                        "test execution."
                                    )

                            except Exception as exc:
                                session.rollback()
                                st.error(
                                    f"Test campaign execution failed: {exc}"
                                )

                    if not recipients:
                        st.info("No recipients have been added yet.")
                    else:
                        rows = []

                        for recipient in recipients:
                            contact = _contact_key(
                                selected_campaign.channel,
                                recipient.email,
                                recipient.phone,
                            )

                            decision = compliance.check_can_send(
                                channel=selected_campaign.channel,
                                contact_key=contact,
                            )

                            rows.append(
                                {
                                    "ID": recipient.id,
                                    "Name": recipient.full_name or "",
                                    "Email": recipient.email or "",
                                    "Phone": recipient.phone or "",
                                    "Status": recipient.status,
                                    "Compliance": (
                                        "Eligible"
                                        if decision.allowed
                                        else decision.reason
                                    ),
                                }
                            )

                        st.dataframe(
                            rows,
                            use_container_width=True,
                            hide_index=True,
                        )

        with history_tab:
            st.subheader("Delivery attempts")

            available = campaigns.list_campaigns()

            if not available:
                st.info("No campaigns available.")
            else:
                recipient_options = []
                recipient_map = {}

                for item in available:
                    for recipient in campaigns.list_recipients(item.id):
                        label = (
                            f"Campaign #{item.id} — {item.name} / "
                            f"Recipient #{recipient.id} — "
                            f"{recipient.full_name or recipient.email or recipient.phone or 'Unnamed'}"
                        )

                        recipient_options.append(label)
                        recipient_map[label] = recipient.id

                if not recipient_options:
                    st.info(
                        "Add recipients to a campaign to view history."
                    )
                else:
                    selected_recipient = st.selectbox(
                        "Select recipient",
                        options=recipient_options,
                        key="campaign_history_recipient",
                    )

                    attempts = campaigns.list_delivery_attempts(
                        recipient_map[selected_recipient]
                    )

                    if not attempts:
                        st.info("No delivery attempts recorded.")
                    else:
                        st.dataframe(
                            [
                                {
                                    "Provider": attempt.provider,
                                    "Channel": attempt.channel,
                                    "Status": attempt.status,
                                    "Provider message ID": (
                                        attempt.provider_message_id or ""
                                    ),
                                    "Error": (
                                        attempt.error_message or ""
                                    ),
                                    "Attempted at": str(
                                        attempt.attempted_at
                                    ),
                                }
                                for attempt in attempts
                            ],
                            use_container_width=True,
                            hide_index=True,
                        )

        st.info(
            "Test mode only: Campaign execution uses fake providers. "
            "No real email or WhatsApp messages are sent."
        )

    finally:
        session.close()
