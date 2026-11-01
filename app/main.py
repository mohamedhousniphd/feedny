import html
import json
import time
import os
import sys
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Request, Response, HTTPException, Depends, Form, Body, File, UploadFile, Cookie, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError

import asyncio

# Default question asked to students (used when a teacher has not set a custom one).
# Focused on AI: needs, interest and expectations, to prepare training sessions.
DEFAULT_QUESTION = (
    "Quels sont vos besoins, votre intérêt et vos attentes concernant l'IA ? "
    "Que souhaitez-vous apprendre ou améliorer en priorité ?"
)

# Default class code for the main admin account
DEFAULT_ADMIN_CODE = "HOUSNI"

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from app.database import (
    init_db,
    insert_feedback,
    get_all_feedbacks,
    get_feedbacks_with_context,
    get_feedback_by_id,
    toggle_feedback_inclusion,
    get_feedbacks_by_ids,
    get_feedbacks_by_ids_and_teacher,
    check_device_limit,
    increment_device_feedback,
    reset_database,
    create_db_backup,
    list_db_backups,
    purge_client_events,
    maybe_backup_daily,
    get_feedback_stats,
    get_technical_insights,
    get_client_errors,
    save_client_error,
    save_client_event,
    import_feedbacks,
    get_setting,
    set_setting,
    create_teacher,
    get_teacher_by_email,
    get_teacher_by_code,
    get_teacher_by_id,
    deduct_credit,
    add_credits,
    update_teacher_password,
    update_teacher_code,
    save_analysis,
    get_analysis_history
)
from app.models import (
    FeedbackRequest,
    ClientInfoRequest,
    ClientInfoResponse,
    ClientErrorRequest,
    FeedbackResponse,
    FeedbackListResponse,
    TeacherLoginRequest,
    TeacherLoginResponse,
    AnalyzeRequest,
    AnalyzeResponse,
    StatusResponse,
    ErrorResponse,
    ImportFeedbackItem,
    ReceiptApprovalRequest
)
from app.services.analysis import process_feedback_analysis
from app.services.charts import build_charts
from app.services.client_info import (
    collect_client_context,
    request_country,
    summarize_technical,
)

# Initialize FastAPI app
APP_VERSION = "1.2.24"
app = FastAPI(title="Feedny", version=APP_VERSION)

def inject_common(html_content: str) -> str:
    """Inject common template variables like version."""
    import re
    # Replace version in CSS links and footers
    html_content = re.sub(r'\{\{\s*version\s*\}\}', APP_VERSION, html_content)
    # Also handle the old hardcoded versions if they exist (fail-safe)
    html_content = re.sub(r'\?v=v?[\d\.]+', f'?v={APP_VERSION}', html_content)
    return html_content


# CORS middleware
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",")] if allowed_origins_str else []

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

# Template cache
template_cache = {}

async def get_template(filepath: str) -> str:
    """Read file content with in-memory caching and async support."""
    if filepath in template_cache:
        return template_cache[filepath]

    def read_file_sync():
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

    content = await asyncio.to_thread(read_file_sync)
    template_cache[filepath] = content
    return content


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()
    sync_admin_account()
    # Safety net: one automatic DB snapshot per day (kept on the volume)
    try:
        backup = await asyncio.to_thread(maybe_backup_daily)
        if backup:
            print(f"Daily DB backup created: {backup['name']} ({backup['size']} bytes)")
    except Exception as exc:  # noqa: BLE001
        print(f"Daily DB backup skipped: {exc}")

def sync_admin_account():
    """Ensure the main admin account exists and matches environment variables."""
    admin_email = "mohamedhousni@afeedny.com"
    # Read password from environment, default to 'password123' if not set
    admin_password = os.getenv("TEACHER_PASSWORD", "password123")
    # Class code for the admin account (can be overridden by env)
    admin_code = os.getenv("ADMIN_CODE", DEFAULT_ADMIN_CODE).strip().upper()

    admin_hash = get_password_hash(admin_password)

    existing = get_teacher_by_email(admin_email)
    if not existing:
        # Create default admin with a fixed code
        create_teacher("Mohamed HOUSNI", admin_email, admin_hash, admin_code, is_admin=True)
        # We don't have the ID here directly without re-querying,
        # but create_teacher handles insertion.
        # Let's ensure it has credits
        new_admin = get_teacher_by_email(admin_email)
        if new_admin:
            add_credits(new_admin['id'], 1000)
    else:
        # Check if password needs synchronization (or just update it to be safe)
        update_teacher_password(admin_email, admin_hash)
        # Keep the admin class code aligned with the expected value
        if admin_code and (existing.get('unique_code') or '').upper() != admin_code:
            update_teacher_code(existing['id'], admin_code)


def get_device_id(request: Request) -> str:
    """Get or create device ID from cookie."""
    device_id = request.cookies.get("device_id")
    if not device_id:
        device_id = str(uuid.uuid4())
    return device_id


async def get_current_teacher(request: Request) -> dict:
    """Get current logged-in teacher."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    teacher = get_teacher_by_email(payload.get("sub"))
    if not teacher:
        raise HTTPException(status_code=401, detail="Teacher not found")
        
    return teacher


# Uploads must survive redeploys: store them on the Railway volume when available
UPLOAD_ROOT = os.getenv("UPLOAD_DIR", "/app/data/uploads")
try:
    os.makedirs(os.path.join(UPLOAD_ROOT, "receipts"), exist_ok=True)
except OSError:
    UPLOAD_ROOT = os.path.join("app", "static", "uploads")
    os.makedirs(os.path.join(UPLOAD_ROOT, "receipts"), exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOAD_ROOT), name="uploads")

# Template Cache
template_cache = {}

async def get_template(path: str) -> str:
    """Read a template from disk or cache it."""
    if path not in template_cache:
        def _read_file():
            with open(path, "r", encoding="utf-8") as f:
                return f.read()

        template_cache[path] = await asyncio.to_thread(_read_file)

    return template_cache[path]


# Routes

@app.get("/", response_class=HTMLResponse)
async def student_page(request: Request, code: Optional[str] = Query(None)):
    """Student feedback page."""
    # Check for code in query param or cookie (last used code)
    if not code:
        code = request.cookies.get("teacher_code")
        
    # If still no code, serve landing page
    if not code:
        html_content = await get_template("app/static/student_landing.html")
        return HTMLResponse(content=inject_common(html_content))
            
    # Verify code
    teacher = get_teacher_by_code(code.upper())
    if not teacher:
        # Invalid code, go back to landing
        response = Response(status_code=302, headers={"Location": "/"})
        response.delete_cookie("teacher_code")
        return response

    device_id = get_device_id(request)
    can_submit, _ = check_device_limit(device_id)

    html_content = await get_template("app/static/index.html")
    # Inject data (handle optional spaces in tags)
    import re
    # Fetch teacher's specific question
    question = get_setting(f"question_{teacher['id']}", DEFAULT_QUESTION)
    
    html_content = re.sub(r'\{\{\s*device_id\s*\}\}', html.escape(str(device_id)), html_content)
    html_content = re.sub(r'\{\{\s*can_submit\s*\}\}', str(can_submit).lower(), html_content)
    html_content = re.sub(r'\{\{\s*question\s*\}\}', html.escape(str(question)), html_content)
    
    # Common injections (version, etc.)
    html_content = inject_common(html_content)

    # Personalize header with escaping
    html_content = html_content.replace('Feedny', f"Afeedny — {html.escape(str(teacher['name']))}")
    html_content = html_content.replace('Afeedny', f"Afeedny — {html.escape(str(teacher['name']))}")

    response = Response(content=html_content, media_type="text/html")

    # Set device ID cookie if not present
    if not request.cookies.get("device_id"):
        response.set_cookie(
            key="device_id",
            value=device_id,
            max_age=365*24*60*60,
            httponly=True,
            secure=COOKIE_SECURE,
            samesite="strict"
        )
    
    # Set teacher code cookie for convenience
    response.set_cookie(
        key="teacher_code",
        value=code.upper(),
        max_age=30*24*60*60, # 30 days
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="strict"
    )

    return response


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """Login page."""
    html_content = await get_template("app/static/login.html")
    return HTMLResponse(content=inject_common(html_content))


@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page():
    """Forgot password page."""
    html_content = await get_template("app/static/forgot_password.html")
    return HTMLResponse(content=inject_common(html_content))


SIGNUP_ENABLED = os.getenv("ENABLE_SIGNUP", "false").strip().lower() in {"1", "true", "yes", "on"}

# Cookies are Secure by default; disable only for local HTTP testing
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "true").strip().lower() not in {"0", "false", "no", "off"}


@app.get("/signup", response_class=HTMLResponse)
async def signup_page():
    """Signup page — disabled unless ENABLE_SIGNUP=true."""
    if not SIGNUP_ENABLED:
        return Response(status_code=302, headers={"Location": "/login"})
    html_content = await get_template("app/static/signup.html")
    return HTMLResponse(content=inject_common(html_content))


@app.get("/teacher", response_class=HTMLResponse)
@app.get("/teacher/dashboard", response_class=HTMLResponse)
async def teacher_dashboard(request: Request):
    """Teacher dashboard page."""
    try:
        teacher = await get_current_teacher(request)
    except HTTPException:
        return Response(status_code=302, headers={"Location": "/login"})

    html_content = await get_template("app/static/dashboard.html")
    # Inject teacher info
    html_content = html_content.replace('{{name}}', html.escape(str(teacher['name'])))
    html_content = html_content.replace('{{unique_code}}', html.escape(str(teacher['unique_code'])))
    
    # Handle credits display
    credits_display = '∞' if teacher['is_admin'] else str(teacher['credits'])
    html_content = html_content.replace('{{credits}}', html.escape(credits_display))

    return HTMLResponse(content=inject_common(html_content))


# Auth API

class TeacherSignup(FeedbackRequest.__base__): # Inherit BaseModel
    name: str
    email: str
    password: str
    invitation_code: str

@app.post("/api/auth/signup")
async def signup(data: TeacherSignup):
    """Register a new teacher (disabled unless ENABLE_SIGNUP=true)."""
    if not SIGNUP_ENABLED:
        raise HTTPException(status_code=403, detail="Les inscriptions sont désactivées.")

    # Validate invitation code
    # 1. Check against master admin code
    ADMIN_INVITE_CODE = os.getenv("ADMIN_INVITE_CODE", "FEEDNY2024")
    
    # 2. Check against existing teacher codes
    referrer = None
    if data.invitation_code != ADMIN_INVITE_CODE:
        referrer = get_teacher_by_code(data.invitation_code.upper())
        if not referrer:
             raise HTTPException(status_code=400, detail="Code d'invitation invalide")

    # Generate unique code
    import random, string
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    
    pwd_hash = get_password_hash(data.password)
    teacher_id = create_teacher(data.name, data.email, pwd_hash, code)
    
    if not teacher_id:
        raise HTTPException(status_code=400, detail="Email déjà enregistré")
        
    # Reward referrer (optional - maybe give credit?)
    if referrer:
        add_credits(referrer['id'], 1) # Bonus credit for inviting
        
    # Auto login? For now just return success
    return {"status": "success", "unique_code": code}


@app.post("/api/auth/login")
async def login(username: str = Form(...), password: str = Form(...), response: Response = None):
    """Login teacher."""
    teacher = get_teacher_by_email(username)
    if not teacher or not verify_password(password, teacher['password_hash']):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
        
    access_token = create_access_token(data={"sub": teacher['email']})
    
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=COOKIE_SECURE,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="strict"
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/api/teacher/logout")
async def logout(response: Response):
    """Logout teacher."""
    response.delete_cookie("access_token")
    return {"status": "success"}


# API Routes - Student
@app.post("/api/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    http_request: Request,
    response: Response
):
    """Submit a new feedback with optional emotion."""
    device_id = get_device_id(http_request)
    
    # Get teacher from cookie
    code = http_request.cookies.get("teacher_code")
    if not code:
         raise HTTPException(status_code=400, detail="Teacher code missing")
         
    teacher = get_teacher_by_code(code)
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    # Check if device has already submitted
    can_submit, count = check_device_limit(device_id)
    if not can_submit:
        raise HTTPException(status_code=403, detail="Vous avez déjà soumis un feedback")

    # Insert feedback with emotion and teacher_id
    feedback_id = insert_feedback(request.content, device_id, request.emotion, teacher['id'])
    increment_device_feedback(device_id)

    # Anonymous technical context (device, browser, network, typing timings)
    try:
        context = collect_client_context(
            request.client_info,
            user_agent=http_request.headers.get("user-agent", ""),
            country_hint=request_country(http_request),
            referrer=http_request.headers.get("referer"),
            fill_seconds=request.fill_seconds,
        )
        save_client_event("submit", teacher['id'], device_id, context)
    except Exception as exc:  # never block a submission for telemetry
        print(f"Client context skipped: {exc}")

    # Get the created feedback
    feedback = get_feedback_by_id(feedback_id)

    # Set device ID cookie
    response.set_cookie(
        key="device_id",
        value=device_id,
        max_age=365*24*60*60,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="strict"
    )

    return FeedbackResponse(**feedback)


@app.get("/api/student/logout")
async def student_logout(response: Response):
    """Clear student teacher code cookie."""
    response = Response(status_code=302)
    response.headers["Location"] = "/"
    response.delete_cookie("teacher_code")
    return response


@app.post("/api/client-info", response_model=ClientInfoResponse)
async def collect_client_info(
    request: ClientInfoRequest,
    http_request: Request,
):
    """Record anonymous technical context when a student opens a session."""
    code = http_request.cookies.get("teacher_code")
    if not code:
        return ClientInfoResponse(status="ignored")

    teacher = get_teacher_by_code(code)
    if not teacher:
        return ClientInfoResponse(status="ignored")

    try:
        device_id = get_device_id(http_request)
        context = collect_client_context(
            request.client_info,
            user_agent=http_request.headers.get("user-agent", ""),
            country_hint=request_country(http_request),
            referrer=http_request.headers.get("referer"),
            fill_seconds=request.fill_seconds,
        )
        event_type = (request.event or "").strip().lower()
        if event_type not in {"join", "leave"}:
            event_type = "leave" if context.get("left_without_submit") else "join"
        save_client_event(event_type, teacher['id'], device_id, context)
    except Exception as exc:  # telemetry must never break the student flow
        print(f"Client context skipped: {exc}")

    return ClientInfoResponse(status="ok")


@app.post("/api/client-errors", response_model=ClientInfoResponse)
async def collect_client_error(
    request: ClientErrorRequest,
    http_request: Request,
):
    """Record a JS error from the student page (anonymous, rate-limited)."""
    code = http_request.cookies.get("teacher_code")
    teacher = get_teacher_by_code(code) if code else None
    if not teacher:
        return ClientInfoResponse(status="ignored")

    try:
        save_client_error(
            teacher['id'],
            get_device_id(http_request),
            {
                "message": request.message,
                "source": request.source,
                "line": request.line,
                "column": request.column,
                "stack": request.stack,
                "url": request.url,
                "user_agent": http_request.headers.get("user-agent", ""),
            },
        )
    except Exception as exc:
        print(f"Client error skipped: {exc}")

    return ClientInfoResponse(status="ok")


@app.get("/api/insights/technical")
async def technical_insights(
    teacher: dict = Depends(get_current_teacher)
):
    """Anonymous technical context: devices, network, timing, participation."""
    insights = await asyncio.to_thread(get_technical_insights, teacher['id'])
    errors = await asyncio.to_thread(get_client_errors, teacher['id'])
    return {
        "insights": insights,
        "summary": summarize_technical(insights),
        "errors": errors,
    }


_CHARTS_CACHE: dict = {}
_CHARTS_TTL_SECONDS = 120


@app.get("/api/insights/charts")
async def technical_charts(
    refresh: bool = False,
    teacher: dict = Depends(get_current_teacher),
):
    """Slide-ready PNG charts (data URI) built from the anonymous metrics."""
    cache_key = teacher['id']
    cached = _CHARTS_CACHE.get(cache_key)
    now = time.time()
    if not refresh and cached and now - cached["at"] < _CHARTS_TTL_SECONDS:
        return cached["payload"]

    insights = await asyncio.to_thread(get_technical_insights, teacher['id'])
    charts = await asyncio.to_thread(build_charts, insights)
    payload = {
        "charts": charts,
        "count": len(charts),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    if charts:  # never cache an empty result (new data would never show)
        _CHARTS_CACHE[cache_key] = {"at": now, "payload": payload}
    return payload


@app.get("/api/question")
async def get_question(
    teacher: dict = Depends(get_current_teacher)
):
    """Get the current teacher question."""
    question = get_setting(f"question_{teacher['id']}", DEFAULT_QUESTION)
    return {"question": question}


@app.post("/api/question")
async def update_question(
    request: Request,
    teacher: dict = Depends(get_current_teacher)
):
    """Update the teacher question."""
    data = await request.json()
    question = data.get("question", "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="La question ne peut pas être vide")
    
    # Per-teacher setting
    set_setting(f"question_{teacher['id']}", question)
    return {"status": "success", "question": question}


@app.get("/api/stats")
async def get_stats(teacher: dict = Depends(get_current_teacher)):
    """Get feedback statistics for the dashboard."""
    stats = await asyncio.to_thread(get_feedback_stats, teacher['id'])
    return stats


@app.get("/api/status", response_model=StatusResponse)
async def get_status(request: Request):
    """Check if feedback collection is open."""
    device_id = get_device_id(request)
    can_submit, count = check_device_limit(device_id)

    if can_submit:
        return StatusResponse(
            collection_open=True,
            message="La collecte de feedbacks est ouverte"
        )
    else:
        return StatusResponse(
            collection_open=False,
            message="Vous avez déjà soumis un feedback. Veuillez attendre que l'enseignant ouvre une nouvelle collecte."
        )


# API Routes - Teacher
# (Other routes like /api/teacher/login, /api/auth/signup are already implemented)


@app.get("/api/feedbacks/details")
async def list_feedbacks_with_context(teacher: dict = Depends(get_current_teacher)):
    """Feedbacks with their anonymous device/network/timing context (teacher only)."""
    feedbacks = await asyncio.to_thread(get_feedbacks_with_context, teacher['id'])
    return {"feedbacks": feedbacks, "total": len(feedbacks)}


@app.get("/api/feedbacks", response_model=FeedbackListResponse)
async def get_feedbacks_list(
    request: Request,
    teacher: dict = Depends(get_current_teacher)
):
    """Get all feedbacks (teacher only)."""
    feedbacks = get_all_feedbacks(teacher['id'])
    return FeedbackListResponse(
        feedbacks=[FeedbackResponse(**fb) for fb in feedbacks],
        total=len(feedbacks)
    )


@app.put("/api/feedbacks/{feedback_id}/toggle", response_model=dict)
async def toggle_feedback(
    feedback_id: int, 
    request: Request,
    teacher: dict = Depends(get_current_teacher)
):
    """Toggle feedback inclusion in analysis (teacher only)."""
    # Verify feedback belongs to teacher
    feedback = get_feedback_by_id(feedback_id)
    if not feedback or feedback['teacher_id'] != teacher['id']:
        raise HTTPException(status_code=404, detail="Feedback non trouvé")

    success = toggle_feedback_inclusion(feedback_id)
    return {"success": True, "message": "Statut mis à jour"}


@app.post("/api/analyze")
async def analyze_feedbacks_endpoint(
    request_data: AnalyzeRequest, 
    request: Request,
    teacher: dict = Depends(get_current_teacher)
):
    """Analyze selected feedbacks and generate wordcloud (teacher only)."""
    try:
        # Admin has unlimited credits
        if not teacher.get('is_admin') and teacher['credits'] <= 0:
            raise HTTPException(status_code=403, detail="Crédits insuffisants. Veuillez recharger votre compte.")

        if not request_data.feedback_ids:
            raise HTTPException(status_code=400, detail="Veuillez sélectionner au moins un feedback")

        # Get selected feedbacks
        feedbacks = get_feedbacks_by_ids(request_data.feedback_ids)

        if not feedbacks:
            raise HTTPException(status_code=404, detail="Aucun feedback trouvé")

        # Verify ownership - use .get() to avoid KeyError
        for fb in feedbacks:
            if fb.get('teacher_id') and fb['teacher_id'] != teacher['id']:
                raise HTTPException(status_code=403, detail="Accès non autorisé à certains feedbacks")

        # Anonymous technical context (device, network, timing) — included in the report
        insights = await asyncio.to_thread(get_technical_insights, teacher['id'])
        technical = summarize_technical(insights)
        errors = await asyncio.to_thread(get_client_errors, teacher['id'], 5)
        if errors.get("total"):
            technical["lines"].append(f"Erreurs JS signalées par les navigateurs : {errors['total']}.")

        # Process feedback analysis (wordcloud and DeepSeek AI analysis)
        summary, wordcloud_base64 = await process_feedback_analysis(
            feedbacks,
            request_data.context,
            technical_lines=technical["lines"],
        )
        
        # Deduct credit if not admin
        if not teacher.get('is_admin'):
            deduct_credit(teacher['id'])
        
        # Save to analysis history
        try:
            save_analysis(
                teacher_id=teacher['id'],
                summary=summary,
                wordcloud_image=wordcloud_base64,
                feedback_count=len(feedbacks),
                context=request_data.context or "",
                technical_context=json.dumps(technical, ensure_ascii=False),
            )
        except Exception as e:
            print(f"Save analysis history error (non-fatal): {e}")
        
        return {
            "summary": summary,
            "wordcloud_data": {"image": wordcloud_base64},
            "technical": technical,
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "summary": f"Erreur lors de l'analyse: {str(e)}",
            "wordcloud_data": {"image": ""}
        }


@app.get("/api/analyses")
async def get_analyses(
    teacher: dict = Depends(get_current_teacher)
):
    """Get analysis history for the current teacher."""
    history = get_analysis_history(teacher['id'])
    return {"analyses": history}


@app.delete("/api/analyses/{analysis_id}")
async def delete_analysis(
    analysis_id: int,
    teacher: dict = Depends(get_current_teacher)
):
    """Delete an analysis from history."""
    from app.database import delete_analysis_by_id
    success = delete_analysis_by_id(analysis_id, teacher['id'])
    if not success:
        raise HTTPException(status_code=404, detail="Analyse non trouvée")
    return {"success": True}


@app.post("/api/teacher/update_code")
async def update_code(
    request: Request,
    data: dict = Body(...),
    teacher: dict = Depends(get_current_teacher)
):
    """Update teacher's unique invite code."""
    new_code = (data.get("code") or "").strip().upper()
    if len(new_code) < 3:
        raise HTTPException(status_code=400, detail="Code trop court (min 3 caractères)")
    if len(new_code) > 20:
        raise HTTPException(status_code=400, detail="Code trop long (max 20 caractères)")
    if not all(char.isalnum() for char in new_code):
        raise HTTPException(status_code=400, detail="Lettres et chiffres uniquement (sans espace ni accent)")

    success = update_teacher_code(teacher['id'], new_code)
    if not success:
        raise HTTPException(status_code=400, detail="Ce code est déjà utilisé, veuillez en choisir un autre")
    
    return {"status": "success", "new_code": new_code.upper()}


@app.post("/api/admin/telemetry/purge")
async def purge_telemetry(
    data: dict = Body(default={}),
    teacher: dict = Depends(get_current_teacher),
):
    """Delete anonymous telemetry (admin only).

    Body (optional): {"before": "YYYY-MM-DD"} to keep recent events only.
    """
    if not teacher.get('is_admin'):
        raise HTTPException(status_code=403, detail="Non autorisé")

    before = (data or {}).get("before")
    if before:
        try:
            datetime.strptime(before, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Format attendu : YYYY-MM-DD")

    # Snapshot first: telemetry purge is a destructive operation
    backup = await asyncio.to_thread(create_db_backup, "avant-purge-tech")
    deleted = await asyncio.to_thread(purge_client_events, before, None)
    return {"success": True, "deleted": deleted, "before": before, "backup": backup["name"]}


@app.post("/api/backup")
async def create_backup_endpoint(teacher: dict = Depends(get_current_teacher)):
    """Create a snapshot of the database (teachers: their own data included)."""
    backup = await asyncio.to_thread(create_db_backup, "manuel")
    return {"success": True, "backup": backup}


@app.get("/api/backups")
async def list_backups_endpoint(teacher: dict = Depends(get_current_teacher)):
    """List available DB snapshots (admin only)."""
    if not teacher.get('is_admin'):
        raise HTTPException(status_code=403, detail="Non autorisé")
    backups = await asyncio.to_thread(list_db_backups)
    return {"backups": backups, "count": len(backups)}


class ResetRequest(BaseModel):
    confirm: str = ""


@app.post("/api/reset")
async def reset_database_endpoint(
    data: Optional[ResetRequest] = Body(None),
    teacher: dict = Depends(get_current_teacher)
):
    """Delete feedbacks permanently.

    Requires an explicit {"confirm": "SUPPRIMER"} body and always stores a
    database snapshot first, so nothing is lost by accident.
    """
    if not data or (data.confirm or "").strip().upper() != "SUPPRIMER":
        raise HTTPException(
            status_code=400,
            detail='Confirmation requise: envoyez {"confirm": "SUPPRIMER"}',
        )

    backup = await asyncio.to_thread(create_db_backup, "avant-suppression")

    if teacher.get('is_admin'):
        reset_database()
        return {
            "success": True,
            "message": "Base de données réinitialisée (Admin)",
            "backup": backup["name"],
        }
    else:
        reset_database(teacher['id'])
        return {
            "success": True,
            "message": "Vos données ont été réinitialisées",
            "backup": backup["name"],
        }


def _generate_csv(feedbacks_list: list) -> str:
    """Helper to generate CSV from a list of feedback objects."""
    import pandas as pd
    if not feedbacks_list:
        return ""
    
    # Create DataFrame
    df = pd.DataFrame(feedbacks_list)
    # Filter columns to export
    columns = ["id", "content", "device_id", "created_at", "included_in_analysis", "emotion"]
    # Only keep columns that exist
    df = df[[c for c in columns if c in df.columns]]

    # Convert to CSV with UTF-8 BOM for Excel compatibility
    return df.to_csv(index=False, encoding="utf-8-sig")

@app.get("/api/export/csv")
async def export_csv(
    request: Request,
    teacher: dict = Depends(get_current_teacher),
    feedbacks: Optional[str] = Query(None)  # comma-separated IDs
):
    """Export feedbacks as CSV (teacher only)."""
    if feedbacks:
        # Export only selected feedbacks
        try:
            feedback_ids = [int(id.strip()) for id in feedbacks.split(",") if id.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="Identifiants de feedback invalides (doivent être des nombres)")

        if not feedback_ids:
            raise HTTPException(status_code=400, detail="Aucun ID de feedback valide fourni")
        
        all_feedbacks = get_feedbacks_by_ids_and_teacher(feedback_ids, teacher['id'])
    else:
        # Export all feedbacks for the teacher
        all_feedbacks = get_all_feedbacks(teacher['id'])

    if not all_feedbacks:
        raise HTTPException(status_code=404, detail="Aucun feedback à exporter")

    # Run blocking pandas CPU/IO operations in a threadpool
    from fastapi.concurrency import run_in_threadpool
    csv_buffer = await run_in_threadpool(_generate_csv, all_feedbacks)

    return Response(
        content=csv_buffer,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=feedny_feedbacks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )


# Health check endpoints for Railway serverless
# Password Reset & Email
import resend

@app.post("/api/auth/forgot-password")
async def forgot_password(data: dict = Body(...)):
    """Send password reset email."""
    email = data.get("email")
    teacher = get_teacher_by_email(email)
    if not teacher:
        # Don't reveal if email exists, fake success
        return {"message": "Si cet email existe, un lien a été envoyé."}
        
    # Generate reset token (simple implementation: use JWT with short expiry)
    reset_token = create_access_token(data={"sub": email, "type": "reset"}, expires_delta=timedelta(minutes=15))
    
    # Send email via Resend
    RESEND_API_KEY = os.getenv("RESEND_API_KEY")
    if not RESEND_API_KEY:
        print(f"Warning: RESEND_API_KEY not set. Reset token for {email}: {reset_token}")
        return {"message": "Email envoyé (Mode Dev: vérifier logs serveur pour le token)"}
    
    try:
        resend.api_key = RESEND_API_KEY
        # In a real app, strict reset URL. Here assuming localhost or deployed URL
        # We need a frontend page to handle the token, let's call it /reset-password?token=...
        # For this MVP, we will send a new temporary password directly or a link if we had a page
        
        # Option A: Send temporary password
        # Option B: Link to reset page
        
        # Let's go with Option A for simplicity in MVP, OR link to a reset page we create
        # Creating a reset page is better UX.
        # Let's create /reset-password page in main.py serving static file
        
        public_base_url = os.getenv("PUBLIC_BASE_URL", "https://afeedny.com")
        reset_link = f"{public_base_url}/reset-password?token={reset_token}"
        
        resend.Emails.send({
            "from": "Afeedny <onboarding@resend.dev>", # or verified domain
            "to": email,
            "subject": "Réinitialisation de mot de passe - Afeedny",
            "html": f"""
                <p>Bonjour {teacher['name']},</p>
                <p>Vous avez demandé une réinitialisation de mot de passe.</p>
                <p>Cliquez sur le lien suivant pour définir un nouveau mot de passe :</p>
                <a href="{reset_link}">Réinitialiser mon mot de passe</a>
                <p>Ce lien expire dans 15 minutes.</p>
            """
        })
        return {"message": "Email de réinitialisation envoyé."}
    except Exception as e:
        print(f"Resend error: {e}")
        return {"message": "Erreur lors de l'envoi de l'email."}


@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(token: str):
    """Serve reset password page."""
    # We can reuse forgot_password.html layout or create new
    # Let's assume we create 'reset_password.html'
    html_content = await get_template("app/static/reset_password.html")
    # Inject token into JS
    # Inject token and common data
    html_content = html_content.replace('{{token}}', html.escape(str(token)))
    html_content = inject_common(html_content)
    return HTMLResponse(content=html_content)


@app.post("/api/auth/reset-password")
async def reset_password_confirm(data: dict = Body(...)):
    """Confirm password reset."""
    token = data.get("token")
    new_password = data.get("password")
    
    payload = decode_access_token(token)
    if not payload or payload.get("type") != "reset":
         raise HTTPException(status_code=400, detail="Lien invalide ou expiré")
         
    email = payload.get("sub")
    pwd_hash = get_password_hash(new_password)
    update_teacher_password(email, pwd_hash)
    
    return {"message": "Mot de passe modifié avec succès."}


# Payment & Receipts API

@app.post("/api/payment/upload")
async def upload_receipt(
    file: UploadFile = File(...),
    teacher: dict = Depends(get_current_teacher)
):
    """Upload a payment receipt (images/PDF only, max 5 MB)."""
    # Ensure uploads directory exists
    UPLOAD_DIR = os.path.join(UPLOAD_ROOT, "receipts")
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    ALLOWED_RECEIPT_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
    MAX_RECEIPT_BYTES = 5 * 1024 * 1024

    # Save file (extension whitelist: never serve HTML/JS from /static)
    file_ext = os.path.splitext(file.filename or "")[1].lower()
    if file_ext not in ALLOWED_RECEIPT_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Format non autorisé. Formats acceptés : PDF, JPG, PNG, WEBP.",
        )

    filename = f"{uuid.uuid4()}{file_ext}"
    file_path = f"{UPLOAD_DIR}/{filename}"

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Fichier vide.")
    if len(content) > MAX_RECEIPT_BYTES:
        raise HTTPException(status_code=400, detail="Fichier trop volumineux (max 5 Mo).")

    with open(file_path, "wb") as buffer:
        buffer.write(content)
        
    # Create receipt record
    # Store relative path for serving
    relative_path = f"/uploads/receipts/{filename}"
    from app.database import create_payment_receipt
    create_payment_receipt(teacher['id'], relative_path)
    
    return {"status": "success", "message": "Reçu envoyé avec succès"}


@app.get("/api/payment/instructions")
async def get_payment_instructions(
    teacher: dict = Depends(get_current_teacher)
):
    """Get payment instructions."""
    instructions = get_setting("payment_instructions", "Veuillez contacter l'administrateur pour les instructions de paiement.")
    return {"instructions": instructions}


# Admin API

@app.post("/api/admin/instructions")
async def save_payment_instructions(
    request: Request,
    teacher: dict = Depends(get_current_teacher)
):
    """Save payment instructions (Admin only)."""
    if not teacher['is_admin']:
        raise HTTPException(status_code=403, detail="Admin only")
        
    data = await request.json()
    instructions = data.get("instructions")
    set_setting("payment_instructions", instructions)
    return {"status": "success"}


@app.get("/api/admin/receipts")
async def list_receipts(
    teacher: dict = Depends(get_current_teacher)
):
    """List all receipts (Admin only)."""
    if not teacher['is_admin']:
        raise HTTPException(status_code=403, detail="Admin only")
        
    from app.database import get_all_receipts
    return {"receipts": get_all_receipts()}


@app.post("/api/admin/receipts/{receipt_id}/approve")
async def approve_receipt(
    receipt_id: int,
    data: ReceiptApprovalRequest = Body(...),
    teacher: dict = Depends(get_current_teacher)
):
    """Approve a receipt and add credits (Admin only)."""
    if not teacher['is_admin']:
        raise HTTPException(status_code=403, detail="Admin only")
        
    from app.database import get_receipt_by_id, update_receipt_status, add_credits
    
    receipt = get_receipt_by_id(receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Reçu non trouvé")
        
    if receipt['status'] == 'approved':
        return {"status": "success", "message": "Déjà approuvé"}
        
    # Approve and add credits
    credits_to_add = data.amount
    
    update_receipt_status(receipt_id, 'approved')
    add_credits(receipt['teacher_id'], credits_to_add)
    
    return {"status": "success", "message": f"Reçu validé, {credits_to_add} crédits ajoutés"}


@app.post("/api/admin/receipts/{receipt_id}/reject")
async def reject_receipt(
    receipt_id: int,
    teacher: dict = Depends(get_current_teacher)
):
    """Reject a receipt (Admin only)."""
    if not teacher['is_admin']:
        raise HTTPException(status_code=403, detail="Admin only")
        
    from app.database import update_receipt_status
    update_receipt_status(receipt_id, 'rejected')
    return {"status": "success", "message": "Reçu rejeté"}


@app.get("/api/admin/teachers")
async def list_teachers(
    teacher: dict = Depends(get_current_teacher)
):
    """List all teachers (Admin only)."""
    if not teacher['is_admin']:
        raise HTTPException(status_code=403, detail="Admin only")
        
    from app.database import get_all_teachers
    teachers = get_all_teachers()
    # Mask passwords
    for t in teachers:
        t.pop('password_hash', None)
    return {"teachers": teachers}




@app.get("/health")
@app.get("/healthz")
async def health_check():
    """Health check endpoint for Railway."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# JSON Export/Import for data persistence
@app.get("/api/export/json")
async def export_json(
    request: Request,
    teacher: dict = Depends(get_current_teacher)
):
    """Export feedbacks as JSON (teacher only)."""
    feedbacks = get_all_feedbacks(teacher['id'])

    if not feedbacks:
        raise HTTPException(status_code=404, detail="Aucun feedback à exporter")

    import json

    json_content = json.dumps({
        "exported_at": datetime.now().isoformat(),
        "teacher_email": teacher['email'],
        "feedbacks": feedbacks
    }, ensure_ascii=False, indent=2, default=str)

    return Response(
        content=json_content,
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=feedny_feedbacks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        }
    )


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    """Admin dashboard page."""
    try:
        teacher = await get_current_teacher(request)
        if not teacher.get('is_admin'):
            raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    except HTTPException:
        return Response(status_code=302, headers={"Location": "/login"})

    html_content = await get_template("app/static/admin.html")
    return HTMLResponse(content=html_content)


class CreditUpdate(FeedbackRequest.__base__):
    email: str
    amount: int

@app.post("/api/admin/credits")
async def add_credits_endpoint(
    data: CreditUpdate,
    teacher: dict = Depends(get_current_teacher)
):
    """Add credits to a teacher (admin only)."""
    if not teacher.get('is_admin'):
        raise HTTPException(status_code=403, detail="Non autorisé")
        
    target_teacher = get_teacher_by_email(data.email)
    if not target_teacher:
         raise HTTPException(status_code=404, detail="Enseignant non trouvé")
         
    add_credits(target_teacher['id'], data.amount)
    return {"success": True, "message": f"{data.amount} crédits ajoutés à {data.email}"}



@app.post("/api/import")
async def import_json(
    request: Request,
    teacher: dict = Depends(get_current_teacher)
):
    """Import feedbacks from JSON (teacher only)."""
    try:
        data = await request.json()
        
        feedbacks_data = data.get("feedbacks", [])
        if not feedbacks_data:
            # Maybe it's a list directly?
            if isinstance(data, list):
                feedbacks_data = data
            else:
                return {"success": False, "message": "Aucun feedback trouvé dans le fichier"}

        # Add teacher_id to each feedback before importing
        for fb in feedbacks_data:
            fb['teacher_id'] = teacher['id']

        count = import_feedbacks(feedbacks_data)
        return {"success": True, "message": f"{count} feedbacks importés avec succès"}
            
    except Exception as e:
        print(f"Import error: {e}")
        raise HTTPException(status_code=400, detail="Format JSON invalide")


# PDF Export Endpoint
@app.post("/api/export/pdf")
async def export_pdf(
    request: Request,
    teacher: dict = Depends(get_current_teacher)
):
    """Generate PDF with wordcloud and analysis (teacher only)."""
    try:
        import json
        from app.services.pdf import create_analysis_pdf

        body = await request.body()
        data = json.loads(body.decode('utf-8'))

        wordcloud_image = data.get('wordcloud_image', '')
        analysis_text = data.get('analysis_text', '')
        context = data.get('context', '')
        technical = data.get('technical') or {}

        if not wordcloud_image or not analysis_text:
            raise HTTPException(status_code=400, detail="Données manquantes pour générer le PDF")

        if not technical:
            # Fall back to the live anonymous metrics if the client did not send them
            insights = await asyncio.to_thread(get_technical_insights, teacher['id'])
            technical = summarize_technical(insights)

        # Generate PDF (offloaded to threadpool)
        pdf_bytes = await run_in_threadpool(
            create_analysis_pdf,
            wordcloud_image_base64=wordcloud_image,
            analysis_text=analysis_text,
            context=context,
            technical=technical,
        )

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=feedny_analyse_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            }
        )
    except Exception as e:
        print(f"Error generating PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération du PDF: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, proxy_headers=True, forwarded_allow_ips="*")


