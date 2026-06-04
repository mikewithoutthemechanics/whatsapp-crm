"""
WhatsApp CRM SA — Theo Business Platform Service
=================================================
Manages TheoBrand, BusinessUnit, and BusinessLocation entities
for multi-tenant Theo business management.
"""

import os
import sys
import time
import json
import logging
import hashlib
from datetime import datetime
from typing import Optional, Dict, List, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import settings


logger = logging.getLogger(__name__)


class BusinessPlatformService:
    """
    Service layer for Theo business platform operations.

    Usage::

        svc = BusinessPlatformService(db=db, business_id=biz_id)
        brand = svc.create_brand({...})
        units = svc.list_units(brand_id)
    """

    def __init__(self, db=None, business_id: Optional[str] = None):
        self.db = db
        self.business_id = business_id

    # ── TheoBrand ───────────────────────────────────────────────

    def create_brand(self, brand_data: Dict, business_id: Optional[str] = None) -> Dict:
        """Create a new TheoBrand entry."""
        bid = business_id or self.business_id
        if not bid:
            return {"error": "business_id required"}

        payload = {
            "id": str(hashlib.sha256(
                f"{bid}:{brand_data.get('name', '')}".encode()
            ).hexdigest()[:16]),
            "business_id": bid,
            "name": brand_data.get("name", ""),
            "legal_name": brand_data.get("legal_name", ""),
            "tagline": brand_data.get("tagline", ""),
            "logo_url": brand_data.get("logo_url", ""),
            "primary_color": brand_data.get("primary_color", "#25D366"),
            "secondary_color": brand_data.get("secondary_color", "#128C7E"),
            "industry": brand_data.get("industry", ""),
            "province": brand_data.get("province", ""),
            "city": brand_data.get("city", ""),
            "address": brand_data.get("address", ""),
            "phone": brand_data.get("phone", ""),
            "email": brand_data.get("email", ""),
            "website": brand_data.get("website", ""),
            "vat_registered": brand_data.get("vat_registered", False),
            "vat_number": brand_data.get("vat_number", ""),
            "reg_number": brand_data.get("reg_number", ""),
            "currency": brand_data.get("currency", "ZAR"),
            "timezone": brand_data.get("timezone", "Africa/Johannesburg"),
            "business_hours": brand_data.get("business_hours", {}),
            "settings": brand_data.get("settings", {}),
            "is_active": brand_data.get("is_active", True),
            "created_at": datetime.utcnow().isoformat(),
        }

        if not self.db:
            payload["id"] = f"brand_{int(time.time())}"
            return payload

        try:
            q = self.db.table("theo_brands").insert(payload).execute()
            return payload
        except Exception as exc:
            logger.error("create_brand failed: %s", exc)
            return {"error": str(exc), "partial": payload}

    def get_brand(self, brand_id: str) -> Optional[Dict]:
        """Fetch a single TheoBrand by ID."""
        if not self.db:
            return None
        try:
            q = self.db.table("theo_brands").select("*").eq("id", brand_id).single().execute()
            data = getattr(q, "data", None) or getattr(q, "_response", None)
            if hasattr(data, "data"):
                data = data.data
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    def list_brands(self, business_id: Optional[str] = None,
                    active_only: bool = True) -> List[Dict]:
        """List TheoBrands for a business."""
        bid = business_id or self.business_id
        if not self.db:
            return []

        try:
            q = self.db.table("theo_brands").select("*")
            if bid:
                q = q.eq("business_id", bid)
            if active_only:
                q = q.eq("is_active", True)
            q = q.execute()
            data = getattr(q, "data", None) or getattr(q, "_response", None)
            if hasattr(data, "data"):
                data = data.data
            rows = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
            return [r for r in rows if r]
        except Exception:
            return []

    def update_brand(self, brand_id: str, updates: Dict) -> Dict:
        """Update an existing TheoBrand."""
        if not self.db:
            return {"error": "Database not available"}
        safe = {k: v for k, v in updates.items()
                if k in {
                    "name", "tagline", "logo_url", "primary_color",
                    "secondary_color", "industry", "province", "city",
                    "address", "phone", "email", "website",
                    "vat_registered", "vat_number", "reg_number",
                    "currency", "timezone", "business_hours", "settings",
                    "is_active",
                }}
        safe["updated_at"] = datetime.utcnow().isoformat()
        try:
            self.db.table("theo_brands").update(safe).eq("id", brand_id).execute()
            return {"success": True, "updated": safe}
        except Exception as exc:
            return {"error": str(exc)}

    # ── BusinessUnit ────────────────────────────────────────────

    def create_unit(self, unit_data: Dict) -> Dict:
        """Create a BusinessUnit."""
        payload = {
            "id": str(hashlib.sha256(
                f"{unit_data.get('brand_id')}:{unit_data.get('name', '')}".encode()
            ).hexdigest()[:16]),
            "brand_id": unit_data.get("brand_id"),
            "business_id": unit_data.get("business_id") or self.business_id,
            "name": unit_data.get("name", ""),
            "unit_type": unit_data.get("unit_type", ""),
            "description": unit_data.get("description", ""),
            "manager_name": unit_data.get("manager_name", ""),
            "manager_email": unit_data.get("manager_email", ""),
            "manager_phone": unit_data.get("manager_phone", ""),
            "settings": unit_data.get("settings", {}),
            "is_active": unit_data.get("is_active", True),
            "created_at": datetime.utcnow().isoformat(),
        }
        if not self.db:
            payload["id"] = f"unit_{int(time.time())}"
            return payload
        try:
            self.db.table("business_units").insert(payload).execute()
            return payload
        except Exception as exc:
            logger.error("create_unit failed: %s", exc)
            return {"error": str(exc), "partial": payload}

    def list_units(self, brand_id: str) -> List[Dict]:
        """List BusinessUnits for a TheoBrand."""
        if not self.db:
            return []
        try:
            q = self.db.table("business_units").select("*").eq(
                "brand_id", brand_id
            ).eq("is_active", True).execute()
            data = getattr(q, "data", None) or getattr(q, "_response", None)
            if hasattr(data, "data"):
                data = data.data
            rows = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
            return [r for r in rows if r]
        except Exception:
            return []

    def update_unit(self, unit_id: str, updates: Dict) -> Dict:
        """Update BusinessUnit fields."""
        if not self.db:
            return {"error": "Database not available"}
        safe = {k: v for k, v in updates.items()
                if k in {
                    "name", "unit_type", "description",
                    "manager_name", "manager_email", "manager_phone",
                    "settings", "is_active",
                }}
        safe["updated_at"] = datetime.utcnow().isoformat()
        try:
            self.db.table("business_units").update(safe).eq("id", unit_id).execute()
            return {"success": True, "updated": safe}
        except Exception as exc:
            return {"error": str(exc)}

    # ── BusinessLocation ─────────────────────────────────────────

    def create_location(self, loc_data: Dict) -> Dict:
        """Create a BusinessLocation."""
        payload = {
            "id": str(hashlib.sha256(
                f"{loc_data.get('brand_id')}:{loc_data.get('name', '')}".encode()
            ).hexdigest()[:16]),
            "brand_id": loc_data.get("brand_id"),
            "unit_id": loc_data.get("unit_id"),
            "business_id": loc_data.get("business_id") or self.business_id,
            "name": loc_data.get("name", ""),
            "location_type": loc_data.get("location_type", ""),
            "address": loc_data.get("address", ""),
            "city": loc_data.get("city", ""),
            "province": loc_data.get("province", ""),
            "postal_code": loc_data.get("postal_code", ""),
            "phone": loc_data.get("phone", ""),
            "email": loc_data.get("email", ""),
            "whatsapp_number": loc_data.get("whatsapp_number", ""),
            "whatsapp_connected": loc_data.get("whatsapp_connected", False),
            "whatsapp_session_id": loc_data.get("whatsapp_session_id", ""),
            "latitude": loc_data.get("latitude"),
            "longitude": loc_data.get("longitude"),
            "settings": loc_data.get("settings", {}),
            "is_active": loc_data.get("is_active", True),
            "created_at": datetime.utcnow().isoformat(),
        }
        if not self.db:
            payload["id"] = f"loc_{int(time.time())}"
            return payload
        try:
            self.db.table("business_locations").insert(payload).execute()
            return payload
        except Exception as exc:
            logger.error("create_location failed: %s", exc)
            return {"error": str(exc), "partial": payload}

    def list_locations(self, brand_id: str,
                       unit_id: Optional[str] = None) -> List[Dict]:
        """List BusinessLocations for a brand (optionally filtered by unit)."""
        if not self.db:
            return []
        try:
            q = self.db.table("business_locations").select("*").eq(
                "brand_id", brand_id
            ).eq("is_active", True)
            if unit_id:
                q = q.eq("unit_id", unit_id)
            q = q.execute()
            data = getattr(q, "data", None) or getattr(q, "_response", None)
            if hasattr(data, "data"):
                data = data.data
            rows = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
            return [r for r in rows if r]
        except Exception:
            return []

    def update_location(self, location_id: str, updates: Dict) -> Dict:
        """Update BusinessLocation fields."""
        if not self.db:
            return {"error": "Database not available"}
        safe = {k: v for k, v in updates.items()
                if k in {
                    "name", "location_type", "address", "city", "province",
                    "postal_code", "phone", "email", "whatsapp_number",
                    "whatsapp_connected", "whatsapp_session_id",
                    "latitude", "longitude", "settings", "is_active",
                }}
        safe["updated_at"] = datetime.utcnow().isoformat()
        try:
            self.db.table("business_locations").update(safe).eq("id", location_id).execute()
            return {"success": True, "updated": safe}
        except Exception as exc:
            return {"error": str(exc)}

    # ── Platform summary ────────────────────────────────────────

    def platform_summary(self) -> Dict[str, Any]:
        """Return a high-level summary of the business platform."""
        brands = self.list_brands()
        summary = {
            "business_id": self.business_id,
            "brands_count": len(brands),
            "units_count": 0,
            "locations_count": 0,
            "brands": brands,
        }
        for b in brands:
            try:
                units = self.list_units(b["id"])
                summary["units_count"] += len(units)
                for u in units:
                    locs = self.list_locations(b["id"], u["id"])
                    summary["locations_count"] += len(locs)
            except Exception:
                pass
        return summary
