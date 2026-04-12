import re

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import (
    authenticate_admin,
    ensure_csrf_token,
    is_admin_authenticated,
    login_admin,
    logout_admin,
    pop_flash_message,
    set_flash_message,
    validate_csrf_token,
)
from app.models.lead import Lead
from app.models.property import Property
from app.models.realtor import Realtor
from app.schemas.property import PropertyFilterParams
from app.services.dashboard_service import (
    get_dashboard_leads,
    get_dashboard_metrics,
    get_dashboard_properties,
    get_dashboard_realtors,
)
from app.services.integration_service import get_catalog_entry, get_grouped_catalog_entries, save_integration_config
from app.services.settings_service import get_or_create_app_settings, update_app_settings
from app.web.templating import templates


router = APIRouter(prefix="/dashboard", include_in_schema=False)


def _redirect_to_login() -> RedirectResponse:
    return RedirectResponse(url="/dashboard/login", status_code=status.HTTP_303_SEE_OTHER)


def _redirect(url: str) -> RedirectResponse:
    return RedirectResponse(url=url, status_code=status.HTTP_303_SEE_OTHER)


def _dashboard_context(request: Request, *, active_page: str, db: Session, **kwargs) -> dict:
    app_settings = get_or_create_app_settings(db)
    return {
        "request": request,
        "active_page": active_page,
        "csrf_token": ensure_csrf_token(request),
        "flash": pop_flash_message(request),
        "app_settings": app_settings,
        **kwargs,
    }


def _require_dashboard_auth(request: Request) -> RedirectResponse | None:
    if not is_admin_authenticated(request):
        return _redirect_to_login()
    return None


def _parse_positive_int(value: str | None, default: int, minimum: int = 1, maximum: int = 100) -> int:
    try:
        parsed = int(value or default)
    except ValueError:
        parsed = default
    return max(minimum, min(parsed, maximum))


def _sanitize_redirect_path(value: str | None) -> str:
    if not value or not value.startswith("/dashboard"):
        return "/dashboard"
    if re.match(r"^/dashboard[A-Za-z0-9_/\-\?=&]*$", value):
        return value
    return "/dashboard"


@router.get("/login")
def dashboard_login_page(request: Request, db: Session = Depends(get_db)):
    if is_admin_authenticated(request):
        return _redirect("/dashboard")
    return templates.TemplateResponse(
        request,
        "dashboard/login.html",
        _dashboard_context(request, active_page="login", db=db),
    )


@router.post("/login")
async def dashboard_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
    next_path: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    validate_csrf_token(request, csrf_token)
    if not authenticate_admin(username, password):
        set_flash_message(request, "error", "Invalid admin credentials.")
        return templates.TemplateResponse(
            request,
            "dashboard/login.html",
            _dashboard_context(request, active_page="login", db=db),
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    login_admin(request)
    return _redirect(_sanitize_redirect_path(next_path))


@router.post("/logout")
async def dashboard_logout(request: Request, csrf_token: str = Form(...)):
    validate_csrf_token(request, csrf_token)
    logout_admin(request)
    return _redirect("/dashboard/login")


@router.get("")
@router.get("/")
def dashboard_home(request: Request, db: Session = Depends(get_db)):
    redirect_response = _require_dashboard_auth(request)
    if redirect_response:
        return redirect_response

    settings_snapshot = get_or_create_app_settings(db)
    integration_groups = []
    if settings_snapshot.feature_integrations_panel and settings_snapshot.feature_catalog_visibility:
        integration_groups = get_grouped_catalog_entries(db)
    default_realtor_name = db.scalar(
        select(Realtor.name).where(Realtor.id == settings_snapshot.default_realtor_id)
    ) or "Not assigned"
    metrics = get_dashboard_metrics(db)
    metrics["default_realtor_name"] = default_realtor_name

    return templates.TemplateResponse(
        request,
        "dashboard/home.html",
        _dashboard_context(
            request,
            active_page="overview",
            db=db,
            metrics=metrics,
            integration_groups=integration_groups,
        ),
    )


@router.get("/properties")
def dashboard_properties(
    request: Request,
    city: str | None = None,
    status_value: str | None = None,
    property_type: str | None = None,
    bedrooms: int | None = None,
    page: int = 1,
    db: Session = Depends(get_db),
):
    redirect_response = _require_dashboard_auth(request)
    if redirect_response:
        return redirect_response

    settings_snapshot = get_or_create_app_settings(db)
    filters = PropertyFilterParams(
        city=city or None,
        status=status_value or None,
        property_type=property_type or None,
        bedrooms=bedrooms,
    )
    properties, total_pages = get_dashboard_properties(
        db,
        filters=filters,
        page=page,
        page_size=settings_snapshot.dashboard_table_page_size,
    )
    return templates.TemplateResponse(
        request,
        "dashboard/properties.html",
        _dashboard_context(
            request,
            active_page="properties",
            db=db,
            properties=properties,
            filters=filters,
            current_page=page,
            total_pages=total_pages,
        ),
    )


@router.get("/properties/{property_id}")
def dashboard_property_detail(property_id: int, request: Request, db: Session = Depends(get_db)):
    redirect_response = _require_dashboard_auth(request)
    if redirect_response:
        return redirect_response

    property_record = db.scalar(
        select(Property).options(joinedload(Property.realtor)).where(Property.id == property_id)
    )
    if property_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return templates.TemplateResponse(
        request,
        "dashboard/property_detail.html",
        _dashboard_context(
            request,
            active_page="properties",
            db=db,
            property_record=property_record,
        ),
    )


@router.get("/leads")
def dashboard_leads(
    request: Request,
    status_value: str | None = None,
    city: str | None = None,
    page: int = 1,
    db: Session = Depends(get_db),
):
    redirect_response = _require_dashboard_auth(request)
    if redirect_response:
        return redirect_response

    settings_snapshot = get_or_create_app_settings(db)
    leads, total_pages = get_dashboard_leads(
        db,
        status=status_value or None,
        city=city or None,
        page=page,
        page_size=settings_snapshot.dashboard_table_page_size,
    )
    return templates.TemplateResponse(
        request,
        "dashboard/leads.html",
        _dashboard_context(
            request,
            active_page="leads",
            db=db,
            leads=leads,
            current_page=page,
            total_pages=total_pages,
            status_value=status_value or "",
            city=city or "",
        ),
    )


@router.get("/leads/{lead_id}")
def dashboard_lead_detail(lead_id: int, request: Request, db: Session = Depends(get_db)):
    redirect_response = _require_dashboard_auth(request)
    if redirect_response:
        return redirect_response

    lead = db.scalar(
        select(Lead)
        .options(joinedload(Lead.assigned_realtor), joinedload(Lead.property))
        .where(Lead.id == lead_id)
    )
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return templates.TemplateResponse(
        request,
        "dashboard/lead_detail.html",
        _dashboard_context(request, active_page="leads", db=db, lead=lead),
    )


@router.get("/realtors")
def dashboard_realtors(
    request: Request,
    city: str | None = None,
    page: int = 1,
    db: Session = Depends(get_db),
):
    redirect_response = _require_dashboard_auth(request)
    if redirect_response:
        return redirect_response

    settings_snapshot = get_or_create_app_settings(db)
    realtors, total_pages = get_dashboard_realtors(
        db,
        city=city or None,
        page=page,
        page_size=settings_snapshot.dashboard_table_page_size,
    )
    return templates.TemplateResponse(
        request,
        "dashboard/realtors.html",
        _dashboard_context(
            request,
            active_page="realtors",
            db=db,
            realtors=realtors,
            current_page=page,
            total_pages=total_pages,
            city=city or "",
        ),
    )


@router.get("/settings")
def dashboard_settings(request: Request, db: Session = Depends(get_db)):
    redirect_response = _require_dashboard_auth(request)
    if redirect_response:
        return redirect_response

    app_settings = get_or_create_app_settings(db)
    realtors = list(db.scalars(select(Realtor).order_by(Realtor.name.asc())).all())
    return templates.TemplateResponse(
        request,
        "dashboard/settings.html",
        _dashboard_context(
            request,
            active_page="settings",
            db=db,
            settings_record=app_settings,
            realtors=realtors,
        ),
    )


@router.post("/settings")
async def dashboard_settings_update(request: Request, db: Session = Depends(get_db)):
    redirect_response = _require_dashboard_auth(request)
    if redirect_response:
        return redirect_response

    form = await request.form()
    validate_csrf_token(request, form.get("csrf_token"))

    update_app_settings(
        db,
        fixed_contact_number=str(form.get("fixed_contact_number", "")).strip(),
        default_realtor_id=_parse_positive_int(str(form.get("default_realtor_id", "1")), 1),
        chat_result_limit=_parse_positive_int(str(form.get("chat_result_limit", "5")), 5, 1, 20),
        default_desired_city_fallback=str(form.get("default_desired_city_fallback", "")).strip() or None,
        dashboard_density=str(form.get("dashboard_density", "comfortable")).strip(),
        dashboard_table_page_size=_parse_positive_int(
            str(form.get("dashboard_table_page_size", "10")),
            10,
            5,
            50,
        ),
        feature_integrations_panel=form.get("feature_integrations_panel") == "on",
        feature_lead_routing_writes=form.get("feature_lead_routing_writes") == "on",
        feature_catalog_visibility=form.get("feature_catalog_visibility") == "on",
    )
    set_flash_message(request, "success", "Global settings saved.")
    return _redirect("/dashboard/settings")


@router.get("/integrations")
def dashboard_integrations(request: Request, db: Session = Depends(get_db)):
    redirect_response = _require_dashboard_auth(request)
    if redirect_response:
        return redirect_response

    app_settings = get_or_create_app_settings(db)
    if not app_settings.feature_integrations_panel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integrations panel disabled")

    return templates.TemplateResponse(
        request,
        "dashboard/integrations.html",
        _dashboard_context(
            request,
            active_page="integrations",
            db=db,
            integration_groups=get_grouped_catalog_entries(db),
            show_catalog_details=app_settings.feature_catalog_visibility,
        ),
    )


@router.get("/integrations/{catalog_id}")
def dashboard_integration_detail(catalog_id: int, request: Request, db: Session = Depends(get_db)):
    redirect_response = _require_dashboard_auth(request)
    if redirect_response:
        return redirect_response

    app_settings = get_or_create_app_settings(db)
    if not app_settings.feature_integrations_panel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integrations panel disabled")

    catalog = get_catalog_entry(db, catalog_id)
    if catalog is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found")

    return templates.TemplateResponse(
        request,
        "dashboard/integration_detail.html",
        _dashboard_context(
            request,
            active_page="integrations",
            db=db,
            catalog=catalog,
            show_catalog_details=app_settings.feature_catalog_visibility,
        ),
    )


@router.post("/integrations/{catalog_id}")
async def dashboard_integration_update(catalog_id: int, request: Request, db: Session = Depends(get_db)):
    redirect_response = _require_dashboard_auth(request)
    if redirect_response:
        return redirect_response

    app_settings = get_or_create_app_settings(db)
    if not app_settings.feature_integrations_panel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integrations panel disabled")

    catalog = get_catalog_entry(db, catalog_id)
    if catalog is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found")

    form = await request.form()
    validate_csrf_token(request, form.get("csrf_token"))
    save_integration_config(db, catalog=catalog, form_data=dict(form))
    set_flash_message(request, "success", f"{catalog.service_name} settings saved.")
    return _redirect(f"/dashboard/integrations/{catalog_id}")
