# routes/public/userdb.py
from __future__ import annotations
from typing import Optional, Dict, Any, List, Generic, TypeVar, Iterable, Tuple
from functools import singledispatchmethod
from abc import ABC, abstractmethod
from dataclasses import dataclass
import math
from urllib.parse import quote_plus
import mysql.connector
from fastapi import APIRouter, Request, Depends, Form, Query, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from models.database import get_db_connection
from pathlib import Path

router = APIRouter(tags=["dashboard"])

BACKEND_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"
TEMPLATES_DIR = FRONTEND_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

STATIC_URL_PREFIX = "/static"
ALLOWED_TAGS = ["asian", "western", "khmer", "japanese", "korean", "pub", "club", "bar"]

def to_public_image_url(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    s = str(raw).strip().replace("\\", "/")
    if s.startswith(("http://", "https://", "data:")):
        return s
    if s.startswith("/static/"):
        return s
    if s.startswith("static/"):
        return f"{STATIC_URL_PREFIX}/{s[len('static/'):]}"
    if s.startswith("/uploads/"):
        return f"{STATIC_URL_PREFIX}/uploads/{s[len('/uploads/'):]}"
    if s.startswith("uploads/"):
        return f"{STATIC_URL_PREFIX}/{s}"
    return f"{STATIC_URL_PREFIX}/{s.lstrip('/')}"

def normalize_coords(lat, lng) -> Tuple[Optional[float], Optional[float]]:
    try:
        lat = float(lat) if lat is not None else None
        lng = float(lng) if lng is not None else None
    except Exception:
        return (None, None)
    if lat is None or lng is None:
        return (None, None)
    if abs(lat) <= 90 and abs(lng) <= 180:
        return (lat, lng)
    if abs(lng) <= 90 and abs(lat) <= 180:
        return (lng, lat)
    return (None, None)

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    to_rad = math.pi / 180.0
    dlat = (lat2 - lat1) * to_rad
    dlon = (lon2 - lon1) * to_rad
    a = math.sin(dlat/2)**2 + math.cos(lat1*to_rad) * math.cos(lat2*to_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def bubble_sort(items: List[Dict[str, Any]], key: str, reverse: bool = False) -> List[Dict[str, Any]]:
    n = len(items)
    while True:
        swapped = False
        for i in range(1, n):
            a = items[i-1].get(key, None)
            b = items[i].get(key, None)
            if a is None: a = float("inf") if not reverse else float("-inf")
            if b is None: b = float("inf") if not reverse else float("-inf")
            if (a < b) if reverse else (a > b):
                items[i-1], items[i] = items[i], items[i-1]
                swapped = True
        n -= 1
        if not swapped or n <= 1:
            break
    return items

class BaseEntity(ABC):
    def __init__(self, entity_id: int):
        self._id = int(entity_id)

    @property
    def id(self) -> int:
        return self._id

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        ...

@dataclass(frozen=True)
class GeoPoint:
    lat: Optional[float]
    lng: Optional[float]

    def is_valid(self) -> bool:
        return self.lat is not None and self.lng is not None

class Venue(BaseEntity):
    def __init__(self, entity_id: int, name: str, description: str, location: GeoPoint):
        super().__init__(entity_id)
        self._name = name.strip()
        self._description = description or ""
        self._location = location

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        if not value or not value.strip():
            raise ValueError("Name cannot be empty")
        self._name = value.strip()

    @property
    def description(self) -> str:
        return self._description

    @description.setter
    def description(self, value: str) -> None:
        self._description = (value or "").strip()

    @property
    def location(self) -> GeoPoint:
        return self._location

    @location.setter
    def location(self, value: GeoPoint) -> None:
        if not isinstance(value, GeoPoint):
            raise TypeError("location must be a GeoPoint")
        self._location = value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self._name,
            "description": self._description,
            "latitude": self._location.lat,
            "longitude": self._location.lng,
        }

class Restaurant(Venue):
    def __init__(
        self,
        entity_id: int,
        name: str,
        description: str,
        location: GeoPoint,
        price_range: Optional[int],
        tag: Optional[str],
        ratings: float = 0.0,
        image_url: Optional[str] = None,
    ):
        super().__init__(entity_id, name, description, location)
        self._price_range = int(price_range) if price_range is not None else None
        self._tag = (tag or "").strip().lower() or None
        self._ratings = float(ratings or 0.0)
        self._image_url = to_public_image_url(image_url)

    @property
    def price_range(self) -> Optional[int]:
        return self._price_range

    @price_range.setter
    def price_range(self, value: Optional[int]) -> None:
        if value is not None and (value < 1 or value > 4):
            raise ValueError("price_range must be 1..4 or None")
        self._price_range = value

    @property
    def tag(self) -> Optional[str]:
        return self._tag

    @tag.setter
    def tag(self, value: Optional[str]) -> None:
        v = (value or "").strip().lower() or None
        self._tag = v

    @property
    def ratings(self) -> float:
        return self._ratings

    def update_rating(self, new_value: float) -> None:
        nv = max(0.0, min(5.0, float(new_value)))
        self._ratings = nv

    @property
    def image_url(self) -> Optional[str]:
        return self._image_url

    @image_url.setter
    def image_url(self, raw: Optional[str]) -> None:
        self._image_url = to_public_image_url(raw)

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "price_range": self._price_range,
            "tag": self._tag,
            "ratings": self._ratings,
            "picture": {"image_path": self._image_url} if self._image_url else {"image_path": None},
        })
        return data

class MenuItem(BaseEntity):
    def __init__(self, entity_id: int, item_name: str, description: str, price: float, image_url: Optional[str]):
        super().__init__(entity_id)
        self._item_name = item_name.strip()
        self._description = description or ""
        self._price = float(price)
        if self._price < 0:
            raise ValueError("price cannot be negative")
        self._image_url = to_public_image_url(image_url)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "item_name": self._item_name,
            "description": self._description,
            "price": self._price,
            "image_url": self._image_url,
        }

T = TypeVar("T", bound=BaseEntity)

class AbstractRepository(ABC, Generic[T]):
    @abstractmethod
    def get(self, entity_id: int) -> Optional[T]:
        ...

    @abstractmethod
    def list(self, *, price_range: Optional[int] = None, tag: Optional[str] = None, order_by_ratings: bool = False) -> List[T]:
        ...

    @abstractmethod
    def search_by_name(self, term: str) -> List[T]:
        ...

class RestaurantRepository(AbstractRepository[Restaurant]):
    def __init__(self, db: mysql.connector.MySQLConnection):
        self.db = db

    def _row_to_restaurant(self, row: Dict[str, Any]) -> Restaurant:
        lat, lng = normalize_coords(row.get("latitude"), row.get("longitude"))
        cur = self.db.cursor(dictionary=True)
        cur.execute(
            "SELECT image_url AS image_path FROM newestone.image_for_restaurant WHERE restaurant_id = %s LIMIT 1",
            (row["id"],),
        )
        pic = cur.fetchone()
        cur.close()
        return Restaurant(
            entity_id=row["id"],
            name=row["name"],
            description=row.get("description") or "",
            location=GeoPoint(lat, lng),
            price_range=row.get("price_range"),
            tag=row.get("tag"),
            ratings=row.get("ratings") or 0.0,
            image_url=(pic["image_path"] if pic and pic.get("image_path") else None),
        )

    def get(self, entity_id: int) -> Optional[Restaurant]:
        cur = self.db.cursor(dictionary=True)
        cur.execute(
            """
            SELECT id, name, description, COALESCE(ratings,0) AS ratings,
                   price_range, tag, latitude, longitude
            FROM newestone.restaurants WHERE id = %s
            """,
            (entity_id,),
        )
        row = cur.fetchone()
        cur.close()
        return self._row_to_restaurant(row) if row else None

    def list(self, *, price_range: Optional[int] = None, tag: Optional[str] = None, order_by_ratings: bool = False) -> List[Restaurant]:
        cur = self.db.cursor(dictionary=True)
        where, params = [], []
        if price_range is not None:
            where.append("r.price_range = %s")
            params.append(price_range)
        if tag:
            where.append("LOWER(r.tag) = LOWER(%s)")
            params.append(tag)
        base_sql = """
            SELECT r.id, r.name, r.description, COALESCE(r.ratings,0) AS ratings,
                   r.price_range, r.tag, r.latitude, r.longitude
            FROM newestone.restaurants r
        """
        if where:
            base_sql += " WHERE " + " AND ".join(where)
        base_sql += " ORDER BY r.ratings DESC, r.name ASC" if order_by_ratings else " ORDER BY r.name ASC"
        cur.execute(base_sql, tuple(params))
        rows = cur.fetchall()
        cur.close()
        return [self._row_to_restaurant(r) for r in rows]

    def search_by_name(self, term: str) -> List[Restaurant]:
        cur = self.db.cursor(dictionary=True)
        cur.execute(
            """
            SELECT id, name, description, COALESCE(ratings,0) AS ratings,
                   price_range, tag, latitude, longitude
            FROM newestone.restaurants
            WHERE LOWER(name) LIKE LOWER(%s)
            ORDER BY name
            """,
            (f"%{term}%",),
        )
        rows = cur.fetchall()
        cur.close()
        return [self._row_to_restaurant(r) for r in rows]

    def get_menu(self, restaurant_id: int) -> List[MenuItem]:
        cur = self.db.cursor(dictionary=True)
        cur.execute(
            """
            SELECT id, item_name, description, price, image_url
            FROM newestone.menu_items
            WHERE restaurant_id = %s
            ORDER BY item_name
            """,
            (restaurant_id,),
        )
        rows = cur.fetchall()
        cur.close()
        return [MenuItem(r["id"], r["item_name"], r.get("description") or "", r["price"], r.get("image_url")) for r in rows]

    def set_rating(self, restaurant_id: int, rating: float) -> None:
        cur = self.db.cursor()
        cur.execute("UPDATE newestone.restaurants SET ratings = %s WHERE id = %s", (rating, restaurant_id))
        self.db.commit()
        cur.close()

    def tag_counts(self, price_range: Optional[int] = None) -> Dict[str, int]:
        cur = self.db.cursor(dictionary=True)
        where, params = [], []
        if price_range is not None:
            where.append("r.price_range = %s")
            params.append(price_range)
        sql = "SELECT LOWER(r.tag) AS tag, COUNT(*) AS cnt FROM newestone.restaurants r"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " GROUP BY LOWER(r.tag)"
        cur.execute(sql, tuple(params))
        rows = cur.fetchall()
        cur.close()
        counts = { (row["tag"] or "").lower(): int(row["cnt"]) for row in rows }
        return { t: counts.get(t.lower(), 0) for t in ALLOWED_TAGS }

class AbstractRestaurantService(ABC):
    @abstractmethod
    def list_for_dashboard(
        self,
        *,
        price_range: Optional[int],
        tag: Optional[str],
        sort: Optional[str],
        user_lat: Optional[float],
        user_lng: Optional[float],
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        ...

    @abstractmethod
    def details(self, restaurant_id: int) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        ...

class RestaurantService(AbstractRestaurantService):
    def __init__(self, repo: RestaurantRepository):
        self.repo = repo

    @singledispatchmethod
    def _filter_key(self, key) -> Dict[str, Any]:
        return {}

    @_filter_key.register
    def _(self, key: int) -> Dict[str, Any]:
        return {"price_range": key}

    @_filter_key.register
    def _(self, key: str) -> Dict[str, Any]:
        return {"tag": key}

    def _distance_enrich(
        self,
        items: Iterable[Restaurant],
        user_lat: Optional[float],
        user_lng: Optional[float],
    ) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        ulat = float(user_lat) if user_lat is not None else None
        ulng = float(user_lng) if user_lng is not None else None
        for r in items:
            d: Optional[float] = None
            if ulat is not None and ulng is not None and r.location.is_valid():
                d = round(haversine_km(ulat, ulng, r.location.lat, r.location.lng), 3)
            data = r.to_dict()
            data["distance_km"] = d
            out.append(data)
        return out

    def list_for_dashboard(
        self,
        *,
        price_range: Optional[int],
        tag: Optional[str],
        sort: Optional[str],
        user_lat: Optional[float],
        user_lng: Optional[float],
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        items = self.repo.list(
            price_range=price_range,
            tag=tag,
            order_by_ratings=True if sort == "ratings" else False,
        )
        enriched = self._distance_enrich(items, user_lat, user_lng)
        if sort == "distance" and user_lat is not None and user_lng is not None:
            enriched = bubble_sort(enriched, key="distance_km", reverse=False)
        counts = self.repo.tag_counts(price_range=price_range)
        return enriched, counts

    def details(self, restaurant_id: int) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        r = self.repo.get(restaurant_id)
        if not r:
            return None, []
        menu = [m.to_dict() for m in self.repo.get_menu(restaurant_id)]
        return r.to_dict() | {"images": [r.image_url] if r.image_url else []}, menu

def _service(db) -> RestaurantService:
    return RestaurantService(RestaurantRepository(db))

@router.get("/userdash")
async def userdash(
    request: Request,
    sort: Optional[str] = Query(None),
    price_range: Optional[int] = Query(None),
    tag: Optional[str] = Query(None),
    user_lat: Optional[float] = Query(None),
    user_lng: Optional[float] = Query(None),
    show_menu: bool = False,
    db: mysql.connector.MySQLConnection = Depends(get_db_connection),
):
    if show_menu:
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT e.id, e.event_name AS name, e.event_description AS description,
                   e.event_datetime AS datetime, r.name AS restaurant_name, r.id AS restaurant_id
            FROM newestone.events e
            JOIN newestone.restaurants r ON e.restaurant_id = r.id
            ORDER BY e.event_datetime ASC
            """
        )
        events = cursor.fetchall()
        for ev in events:
            cursor.execute(
                "SELECT image_url AS image_path FROM newestone.image_for_restaurant WHERE restaurant_id = %s LIMIT 1",
                (ev["restaurant_id"],),
            )
            pic = cursor.fetchone()
            ev["picture"] = {"image_path": to_public_image_url(pic["image_path"])} if pic and pic.get("image_path") else {"image_path": None}
        cursor.close()
        return templates.TemplateResponse(
            "userdash.html",
            {
                "request": request,
                "events": events,
                "show_events": True,
                "active_tag": tag,
                "sort_by": sort,
                "selected_price": price_range,
                "available_tags": ALLOWED_TAGS,
                "tag_counts": {t: 0 for t in ALLOWED_TAGS},
            },
        )
    service = _service(db)
    restaurants, tag_counts = service.list_for_dashboard(
        price_range=price_range, tag=tag, sort=sort, user_lat=user_lat, user_lng=user_lng
    )
    return templates.TemplateResponse(
        "userdash.html",
        {
            "request": request,
            "restaurant_client_data": restaurants,
            "active_tag": tag,
            "sort_by": sort,
            "selected_price": price_range,
            "user_lat": user_lat,
            "user_lng": user_lng,
            "available_tags": ALLOWED_TAGS,
            "tag_counts": tag_counts,
            "show_events": False,
        },
    )

@router.get("/details/{restaurant_id}")
async def details(
    request: Request,
    restaurant_id: int,
    db: mysql.connector.MySQLConnection = Depends(get_db_connection),
):
    service = _service(db)
    restaurant, menu_items = service.details(restaurant_id)
    if restaurant:
        return templates.TemplateResponse("details.html", {"request": request, "restaurant": restaurant, "menu_items": menu_items})
    return templates.TemplateResponse("details.html", {"request": request, "restaurant": None, "menu_items": [], "error": "Restaurant not found"})

@router.post("/filter-restaurants")
async def filter_restaurants(price_range: Optional[int] = Form(None)):
    if price_range is None:
        return RedirectResponse(url="/userdash", status_code=303)
    return RedirectResponse(url=f"/userdash?price_range={price_range}", status_code=303)

@router.post("/filter-by-tag")
async def filter_by_tag(tag: Optional[str] = Form(None)):
    if not tag:
        return RedirectResponse(url="/userdash", status_code=303)
    return RedirectResponse(url=f"/userdash?tag={quote_plus(tag)}", status_code=303)

@router.post("/search")
async def search_restaurants(
    request: Request,
    search_term: str = Form(...),
    db: mysql.connector.MySQLConnection = Depends(get_db_connection),
):
    service = _service(db)
    results = service.repo.search_by_name(search_term)
    if not results:
        return RedirectResponse(url="/userdash", status_code=303)
    data = [r.to_dict() for r in results]
    return templates.TemplateResponse(
        "userdash.html",
        {"request": request, "restaurant_client_data": data, "search_term": search_term, "show_events": False},
    )

@router.post("/userdb/book")
def book(
    people: int = Form(...),
    date: str = Form(...),
    time: str = Form(...),
    restaurant_id: int = Form(...),
    db: mysql.connector.MySQLConnection = Depends(get_db_connection),
):
    cursor = db.cursor()
    user_id = "userwefw"
    status = "pending"
    booking_datetime = f"{date.strip()} {time.strip()}:00"
    cursor.execute(
        """
        INSERT INTO newestone.bookings
          (order_id, restaurant_id, number_of_guests, booking_datetime, status)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (user_id, restaurant_id, people, booking_datetime, status),
    )
    db.commit()
    cursor.close()
    return {"success": True, "message": f"Booking confirmed, status: {status}"}

@router.post("/rate-restaurant")
async def rate_restaurant(
    restaurant_id: int = Form(...),
    rating: float = Form(...),
    db: mysql.connector.MySQLConnection = Depends(get_db_connection),
):
    rating = max(1.0, min(5.0, float(rating)))
    service = _service(db)
    service.repo.set_rating(restaurant_id, rating)
    return RedirectResponse(url=f"/details/{restaurant_id}?rated=1", status_code=303)
