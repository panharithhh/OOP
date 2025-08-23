# routes/public/userdb.py
from typing import Optional, Annotated, Dict, Any, List
import mysql.connector
from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from models.database import get_db_connection
from pathlib import Path

router = APIRouter(tags=["dashboard"])

# ---- Resolve template folder robustly (independent of where uvicorn is started) ----
# This file is .../backend/routes/public/userdb.py
BACKEND_DIR = Path(__file__).resolve().parents[2]          # .../backend
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"             # .../frontend
TEMPLATES_DIR = FRONTEND_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# We assume main.py mounts: app.mount("/static", directory=FRONTEND_DIR/"static")
STATIC_URL_PREFIX = "/static"

def to_public_image_url(raw: Optional[str]) -> Optional[str]:
    """
    Turn whatever is stored in DB (filename, 'static/..', '/static/..', full URL)
    into a URL the browser can load.
    """
    if not raw:
        return None
    s = str(raw).strip().replace("\\", "/")

    # Already a full URL or data URI
    if s.startswith(("http://", "https://", "data:")):
        return s

    # If it already begins with /static or static/, keep/normalize it
    if s.startswith("/static/"):
        return s
    if s.startswith("static/"):
        return f"{STATIC_URL_PREFIX}/{s[len('static/'):]}"

    # Otherwise treat it as a filename that lives under /static
    return f"{STATIC_URL_PREFIX}/{s}"


# ---------------- /userdash ----------------
@router.get("/userdash")
async def userdash(
    request: Request,
    sort: Optional[str] = None,
    show_menu: bool = False,
    db: mysql.connector.MySQLConnection = Depends(get_db_connection),
):
    cursor = db.cursor(dictionary=True)

    if show_menu:
        # Events view
        cursor.execute(
            """
            SELECT e.id,
                   e.event_name        AS name,
                   e.event_description AS description,
                   e.event_datetime    AS datetime,
                   r.name              AS restaurant_name,
                   r.id                AS restaurant_id
            FROM newestone.events e
            JOIN newestone.restaurants r ON e.restaurant_id = r.id
            ORDER BY e.event_datetime ASC
            """
        )
        events = cursor.fetchall()

        for ev in events:
            cursor.execute(
                """
                SELECT image_url AS image_path
                FROM newestone.image_for_restaurant
                WHERE restaurant_id = %s
                LIMIT 1
                """,
                (ev["restaurant_id"],),
            )
            pic = cursor.fetchone()
            # keep your existing "picture.image_path" shape, but normalized
            ev["picture"] = {
                "image_path": to_public_image_url(pic["image_path"]) if pic and pic.get("image_path") else None
            }

        cursor.close()
        return templates.TemplateResponse(
            "userdash.html",
            {
                "request": request,
                "events": events,
                "show_events": True,
                "active_tag": None,
                "sort_by": sort,
            },
        )

    # Restaurants view
    base_sql = """
        SELECT r.id,
               r.name,
               r.description,
               COALESCE(r.ratings, 0) AS ratings,
               r.price_range,
               COALESCE(r.tag, '')    AS tag,
               r.latitude,
               r.longitude
        FROM newestone.restaurants r
    """
    base_sql += " ORDER BY r.ratings DESC" if sort == "ratings" else " ORDER BY r.name ASC"

    cursor.execute(base_sql)
    restaurants: List[Dict[str, Any]] = cursor.fetchall()

    # 1 image per restaurant (if any)
    for r in restaurants:
        cursor.execute(
            """
            SELECT image_url AS image_path
            FROM newestone.image_for_restaurant
            WHERE restaurant_id = %s
            LIMIT 1
            """,
            (r["id"],),
        )
        pic = cursor.fetchone()
        r["picture"] = {
            "image_path": to_public_image_url(pic["image_path"]) if pic and pic.get("image_path") else None
        }

    cursor.close()
    return templates.TemplateResponse(
        "userdash.html",
        {
            "request": request,
            "restaurant_client_data": restaurants,
            "active_tag": None,
            "sort_by": sort,
            "show_events": False,
        },
    )


# ---------------- /details/{restaurant_id} ----------------
@router.get("/details/{restaurant_id}")
async def details(
    request: Request,
    restaurant_id: int,
    db: mysql.connector.MySQLConnection = Depends(get_db_connection),
):
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT id,
               name,
               description,
               COALESCE(ratings,0) AS ratings,
               price_range,
               tag,
               latitude,
               longitude
        FROM newestone.restaurants
        WHERE id = %s
        """,
        (restaurant_id,),
    )
    restaurant = cursor.fetchone()

    cursor.execute(
        """
        SELECT id, item_name, description, price, image_url
        FROM newestone.menu_items
        WHERE restaurant_id = %s
        ORDER BY item_name
        """,
        (restaurant_id,),
    )
    menu_items = cursor.fetchall()

    cursor.execute(
        """
        SELECT image_url
        FROM newestone.image_for_restaurant
        WHERE restaurant_id = %s
        """,
        (restaurant_id,),
    )
    images = cursor.fetchall()

    cursor.close()

    if restaurant:
        restaurant_data = {
            "restaurant_id": restaurant["id"],
            "name": restaurant["name"],
            "description": restaurant["description"],
            "ratings": restaurant["ratings"],
            "price_range": restaurant.get("price_range"),
            "tag": restaurant.get("tag"),
            "latitude": restaurant.get("latitude"),
            "longitude": restaurant.get("longitude"),
            # normalize every image URL
            "images": [to_public_image_url(row["image_url"]) for row in images] if images else [],
        }
        return templates.TemplateResponse(
            "details.html",
            {"request": request, "restaurant": restaurant_data, "menu_items": menu_items},
        )

    return templates.TemplateResponse(
        "details.html",
        {"request": request, "restaurant": None, "menu_items": [], "error": "Restaurant not found"},
    )


# ---------------- /filter-by-tag ----------------
@router.api_route("/filter-restaurants", methods=["GET", "POST"])
async def filter_restaurants(
    request: Request,
    # accept from form (POST) or query (?price_range=2 on GET)
    price_range_form: Optional[int] = Form(None),
    price_range_query: Optional[int] = Query(None),
    db: mysql.connector.MySQLConnection = Depends(get_db_connection),
):
    price_range = price_range_form if price_range_form is not None else price_range_query

    cursor = db.cursor(dictionary=True)
    if price_range is not None:
        cursor.execute(
            """
            SELECT id, name, description,
                   COALESCE(ratings,0) AS ratings,
                   price_range, tag,
                   latitude, longitude
            FROM newestone.restaurants
            WHERE price_range = %s
            ORDER BY name
            """,
            (price_range,),
        )
    else:
        cursor.execute(
            """
            SELECT id, name, description,
                   COALESCE(ratings,0) AS ratings,
                   price_range, tag,
                   latitude, longitude
            FROM newestone.restaurants
            ORDER BY name
            """
        )

    rows = cursor.fetchall()

    for r in rows:
        cursor.execute(
            "SELECT image_url AS image_path FROM newestone.image_for_restaurant WHERE restaurant_id = %s LIMIT 1",
            (r["id"],),
        )
        pic = cursor.fetchone()
        r["picture"] = {"image_path": to_public_image_url(pic["image_path"]) if pic and pic.get("image_path") else None}

    cursor.close()
    return templates.TemplateResponse(
        "userdash.html",
        {"request": request, "restaurant_client_data": rows, "selected_price": price_range, "show_events": False},
    )

# ---------------- /filter-restaurants ----------------
@router.post("/filter-restaurants")
async def filter_restaurants(
    request: Request,
    price_range: Annotated[Optional[int], Form()] = None,
    db: mysql.connector.MySQLConnection = Depends(get_db_connection),
):
    cursor = db.cursor(dictionary=True)

    if price_range is not None:
        cursor.execute(
            """
            SELECT id, name, description,
                   COALESCE(ratings,0) AS ratings,
                   price_range, tag,
                   latitude, longitude
            FROM newestone.restaurants
            WHERE price_range = %s
            ORDER BY name
            """,
            (price_range,),
        )
    else:
        cursor.execute(
            """
            SELECT id, name, description,
                   COALESCE(ratings,0) AS ratings,
                   price_range, tag,
                   latitude, longitude
            FROM newestone.restaurants
            ORDER BY name
            """
        )

    rows = cursor.fetchall()

    for r in rows:
        cursor.execute(
            "SELECT image_url AS image_path FROM newestone.image_for_restaurant WHERE restaurant_id = %s LIMIT 1",
            (r["id"],),
        )
        pic = cursor.fetchone()
        r["picture"] = {
            "image_path": to_public_image_url(pic["image_path"]) if pic and pic.get("image_path") else None
        }

    cursor.close()
    return templates.TemplateResponse(
        "userdash.html",
        {"request": request, "restaurant_client_data": rows, "selected_price": price_range, "show_events": False},
    )


# ---------------- /search ----------------
@router.post("/search")
async def search_restaurants(
    request: Request,
    search_term: Annotated[str, Form(...)],
    db: mysql.connector.MySQLConnection = Depends(get_db_connection),
):
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id, name, description,
                   COALESCE(ratings,0) AS ratings,
                   price_range, tag,
                   latitude, longitude
            FROM newestone.restaurants
            WHERE LOWER(name) LIKE LOWER(%s)
            ORDER BY name
            """,
            (f"%{search_term}%",),
        )
        results = cursor.fetchall()

        for r in results:
            cursor.execute(
                "SELECT image_url AS image_path FROM newestone.image_for_restaurant WHERE restaurant_id = %s LIMIT 1",
                (r["id"],),
            )
            pic = cursor.fetchone()
            r["picture"] = {
                "image_path": to_public_image_url(pic["image_path"]) if pic and pic.get("image_path") else None
            }

        cursor.close()

        if not results:
            return RedirectResponse(url="/userdash", status_code=303)

        return templates.TemplateResponse(
            "userdash.html",
            {"request": request, "restaurant_client_data": results, "search_term": search_term, "show_events": False},
        )

    except Exception:
        return RedirectResponse(url="/userdash", status_code=303)


# ---------------- booking ----------------
@router.post("/userdb/book")
def book(
    people: Annotated[int, Form(...)],
    date: Annotated[str, Form(...)],
    time: Annotated[str, Form(...)],
    restaurant_id: Annotated[int, Form(...)],
    db: mysql.connector.MySQLConnection = Depends(get_db_connection),
):
    cursor = db.cursor()
    user_id = "userwefw"        # TODO: replace with real user/session
    status = "pending"
    booking_datetime = "2025-12-12"  # TODO: compose from date + time

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


