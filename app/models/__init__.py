"""
WhatsApp CRM SA — Database Models
==================================
Supabase/PostgreSQL models for SA SMME WhatsApp CRM.
All prices in ZAR. All times in SAST (Africa/Johannesburg).
"""

import os
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime,
    ForeignKey, JSON, Enum as SQLEnum, Index
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


def sa_now():
    """Current time in SAST (UTC+2)."""
    return datetime.now(timezone.utc)


class Business(Base):
    """SA SMME / business account."""
    __tablename__ = "businesses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    industry = Column(String(100))  # e.g. "plumbing", "salon", "restaurant"
    registration_number = Column(String(50))
    vat_number = Column(String(20))
    province = Column(String(50))  # Gauteng, Western Cape, etc.
    city = Column(String(100))
    address = Column(Text)
    phone = Column(String(20), nullable=False)
    email = Column(String(255))
    currency = Column(String(3), default="ZAR")
    timezone = Column(String(50), default="Africa/Johannesburg")
    business_hours_start = Column(Integer, default=8)
    business_hours_end = Column(Integer, default=18)
    whatsapp_connected = Column(Boolean, default=False)
    whatsapp_phone_number_id = Column(String(50))
    meta_access_token = Column(Text)
    settings = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    contacts = relationship("Contact", back_populates="business")
    conversations = relationship("Conversation", back_populates="business")
    campaigns = relationship("Campaign", back_populates="business")
    team_members = relationship("TeamMember", back_populates="business")
    tags = relationship("Tag", back_populates="business")
    templates = relationship("MessageTemplate", back_populates="business")

    __table_args__ = (
        Index("idx_businesses_industry", "industry"),
        Index("idx_businesses_province", "province"),
    )


class Contact(Base):
    """Customer/lead contact in SA business CRM."""
    __tablename__ = "contacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    whatsapp_number = Column(String(20), index=True)  # e.g. 27821234567
    email = Column(String(255))
    display_name = Column(String(200))

    # Lead scoring
    lead_score = Column(Integer, default=0)
    lead_status = Column(String(20), default="new")  # new, contacted, qualified, converted, inactive
    lead_source = Column(String(50))  # whatsapp, website, referral, ad, walk-in
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("team_members.id"))

    # SA-specific fields
    preferred_language = Column(String(10), default="en")  # en, af, zu, xh
    province = Column(String(50))
    city = Column(String(100))
    id_number = Column(String(13))  # SA ID number (13 digits)

    business = relationship("Business", back_populates="contacts")
    tags = relationship("ContactTag", back_populates="contact")
    conversations = relationship("Conversation", back_populates="contact")
    notes = relationship("ContactNote", back_populates="contact")
    orders = relationship("Order", back_populates="customer")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_contacts_whatsapp", "whatsapp_number"),
        Index("idx_contacts_lead_status", "lead_status"),
        Index("idx_contacts_business", "business_id"),
    )


class Conversation(Base):
    """WhatsApp conversation thread."""
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=False)
    whatsapp_id = Column(String(100))  # WhatsApp conversation ID
    channel = Column(String(20), default="whatsapp")  # whatsapp, sms

    status = Column(String(20), default="open")  # open, pending, resolved, closed
    category = Column(String(50))  # inquiry, complaint, order, follow-up, quote
    priority = Column(String(10), default="normal")  # low, normal, high, urgent
    last_message_at = Column(DateTime(timezone=True), server_default=func.now())
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("team_members.id"))
    ai_handled = Column(Boolean, default=False)
    human_took_over = Column(Boolean, default=False)

    business = relationship("Business", back_populates="conversations")
    contact = relationship("Contact", back_populates="conversations")
    assigned_team_member = relationship("TeamMember", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")
    notes = relationship("ConversationNote", back_populates="conversation")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_conv_business", "business_id"),
        Index("idx_conv_contact", "contact_id"),
        Index("idx_conv_status", "status"),
    )


class Message(Base):
    """Individual WhatsApp message."""
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id"))
    sent_by = Column(String(20), default="customer")  # customer, agent, ai, system

    message_type = Column(String(20), default="text")  # text, image, document, location, button, template
    content = Column(Text)
    media_url = Column(Text)  # URL to uploaded image/document
    whatsapp_message_id = Column(String(100))

    is_read = Column(Boolean, default=False)
    ai_generated = Column(Boolean, default=False)
    extra_data = Column(JSON, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    conversation = relationship("Conversation", back_populates="messages")

    __table_args__ = (
        Index("idx_msg_conversation", "conversation_id"),
        Index("idx_msg_created", "created_at"),
    )


class TeamMember(Base):
    """Staff member who handles conversations."""
    __tablename__ = "team_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    name = Column(String(200), nullable=False)
    email = Column(String(255))
    phone = Column(String(20))
    role = Column(String(30), default="agent")  # admin, agent
    whatsapp_connected = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    business = relationship("Business", back_populates="team_members")
    conversations = relationship("Conversation", back_populates="assigned_team_member")
    notes = relationship("AgentNote", back_populates="author")

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Tag(Base):
    """Tags for organizing contacts and conversations."""
    __tablename__ = "tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    name = Column(String(50), nullable=False)
    color = Column(String(7), default="#3B82F6")  # hex color
    usage_count = Column(Integer, default=0)

    business = relationship("Business", back_populates="tags")


class ContactTag(Base):
    """Many-to-many: Contact <-> Tag."""
    __tablename__ = "contact_tags"
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id"), primary_key=True)
    tag_id = Column(UUID(as_uuid=True), ForeignKey("tags.id"), primary_key=True)

    contact = relationship("Contact", back_populates="tags")
    tag = relationship("Tag")


class Campaign(Base):
    """Drip campaign / broadcast campaign."""
    __tablename__ = "campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    name = Column(String(200), nullable=False)
    campaign_type = Column(String(20), default="drip")  # drip, broadcast, reminder

    trigger_event = Column(String(50))  # new_lead, purchase, inquiry, birthday, inactivity
    trigger_delay_hours = Column(Integer, default=0)

    messages_sequence = Column(JSON, default=list)  # [{"delay_hours": 1, "template_id": "..."}, ...]
    target_audience = Column(String(20), default="all")  # all, new_leads, inactive, segment
    target_tags = Column(JSON, default=list)  # List of tag UUIDs (stored as JSON for SQLite compat)

    status = Column(String(20), default="draft")  # draft, active, paused, completed
    sent_count = Column(Integer, default=0)
    delivered_count = Column(Integer, default=0)
    replied_count = Column(Integer, default=0)
    active_subscribers = Column(Integer, default=0)

    business = relationship("Business", back_populates="campaigns")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CampaignSubscriber(Base):
    """Tracks which contacts are in which campaign step."""
    __tablename__ = "campaign_subscribers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=False)
    current_step = Column(Integer, default=0)
    next_send_at = Column(DateTime(timezone=True))
    status = Column(String(20), default="active")  # active, replied, unsubscribed, completed
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MessageTemplate(Base):
    """Pre-approved WhatsApp message templates."""
    __tablename__ = "message_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    name = Column(String(200), nullable=False)
    category = Column(String(30))  # marketing, utility, authentication
    language = Column(String(10), default="en")
    header_type = Column(String(20))  # text, image, document, video
    body = Column(Text, nullable=False)
    buttons = Column(JSON, default=list)  # [{"type": "url", "text": "...", "url": "..."}, ...]
    is_approved = Column(Boolean, default=False)
    whatsapp_template_id = Column(String(100))
    variables = Column(JSON, default=list)  # ["{{1}}", "{{2}}", ...]

    business = relationship("Business", back_populates="templates")


class Order(Base):
    """Customer order / purchase tracking."""
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id"))
    order_number = Column(String(50), unique=True)
    status = Column(String(20), default="pending")  # pending, confirmed, paid, shipped, delivered, cancelled
    subtotal_cents = Column(Integer, default=0)  # stored in cents to avoid float issues
    tax_cents = Column(Integer, default=0)
    total_cents = Column(Integer, default=0)
    currency = Column(String(3), default="ZAR")
    notes = Column(Text)
    order_metadata = Column(JSON, default=dict)

    customer = relationship("Contact", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class OrderItem(Base):
    """Line item in an order."""
    __tablename__ = "order_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    product_name = Column(String(300))
    sku = Column(String(100))
    quantity = Column(Integer, default=1)
    unit_price_cents = Column(Integer, default=0)
    total_cents = Column(Integer, default=0)

    order = relationship("Order", back_populates="items")


# Conversation notes / agent notes
class ConversationNote(Base):
    __tablename__ = "conversation_notes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("team_members.id"), nullable=False)
    content = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=True)  # internal note vs customer-visible
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    conversation = relationship("Conversation", back_populates="notes")
    author = relationship("TeamMember")


class ContactNote(Base):
    __tablename__ = "contact_notes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("team_members.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    contact = relationship("Contact", back_populates="notes")


class AgentNote(Base):
    __tablename__ = "agent_notes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    author_id = Column(UUID(as_uuid=True), ForeignKey("team_members.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    author = relationship("TeamMember", back_populates="notes")