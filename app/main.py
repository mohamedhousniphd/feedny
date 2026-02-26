import os
import sys
import uuid
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, Response, HTTPException, Depends, Form, Body, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

import asyncio

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
    get_feedback_by_id,
    toggle_feedback_inclusion,
    get_feedbacks_by_ids,
    check_device_limit,
    increment_device_feedback,
    reset_database,
    get_feedback_stats,
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
    update_teacher_code
)
from app.models import (
    FeedbackRequest,
    FeedbackResponse,
    FeedbackListResponse,
    TeacherLoginRequest,
    TeacherLoginResponse,
    AnalyzeRequest,
    AnalyzeResponse,
    StatusResponse,
    ErrorResponse,
    ImportFeedbackItem
)
from app.services.wordcloud import create_wordcloud
from app.services.deepseek import analyze_feedbacks
from datetime import timedelta
from fastapi import Cookie, Query

# Initialize FastAPI app
app = FastAPI(title="Feedny", version="1.0.0")


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()
    sync_admin_account()

def sync_admin_account():
    """Ensure the main admin account exists and matches environment variables."""
    admin_email = "mohamedhousni@afeedny.com"
    # Read password from environment, default to 'password123' if not set
    admin_password = os.getenv("TEACHER_PASSWORD", "password123")
    
    admin_hash = get_password_hash(admin_password)
    
    existing = get_teacher_by_email(admin_email)
    if not existing:
        # Create default admin with a fixed code
        create_teacher("Mohamed HOUSNI", admin_email, admin_hash, "ADMIN", is_admin=True)
        # We don't have the ID here directly without re-querying, 
        # but create_teacher handles insertion.
        # Let's ensure it has credits
        new_admin = get_teacher_by_email(admin_email)
        if new_admin:
            add_credits(new_admin['id'], 1000)
    else:
        # Check if password needs synchronization (or just update it to be safe)
        update_teacher_password(admin_email, admin_hash)


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


# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")


# Routes

@app.get("/", response_class=HTMLResponse)
async def student_page(request: Request, code: Optional[str] = Query(None)):
    """Student feedback page."""
    # Check for code in query param or cookie (last used code)
    if not code:
        code = request.cookies.get("teacher_code")
        
    # If still no code, serve landing page
    if not code:
        with open("app/static/student_landing.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
            
    # Verify code
    teacher = get_teacher_by_code(code.upper())
    if not teacher:
        # Invalid code, go back to landing
        response = Response(status_code=302, headers={"Location": "/"})
        response.delete_cookie("teacher_code")
        return response

    device_id = get_device_id(request)
    can_submit, _ = check_device_limit(device_id)

    with open("app/static/index.html", "r", encoding="utf-8") as f:
        html = f.read()

    # Inject data (handle optional spaces in tags)
    import re
    # Fetch teacher's specific question
    question = get_setting(f"question_{teacher['id']}", "Comment s'est passé votre cours ?")
    
    html = re.sub(r'\{\{\s*device_id\s*\}\}', device_id, html)
    html = re.sub(r'\{\{\s*can_submit\s*\}\}', str(can_submit).lower(), html)
    html = re.sub(r'\{\{\s*question\s*\}\}', question, html)
    html = html.replace('Feedny', f"Afeedny - {teacher['name']}") # Personalize header
    html = html.replace('Afeedny', f"Afeedny - {teacher['name']}") # Handle rebranded name

    response = Response(content=html, media_type="text/html")

    # Set device ID cookie if not present
    if not request.cookies.get("device_id"):
        response.set_cookie(
            key="device_id",
            value=device_id,
            max_age=365*24*60*60,
            httponly=True,
            samesite="lax"
        )
    
    # Set teacher code cookie for convenience
    response.set_cookie(
        key="teacher_code",
        value=code.upper(),
        max_age=30*24*60*60, # 30 days
        httponly=True,
        samesite="lax"
    )

    return response


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """Login page."""
    with open("app/static/login.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page():
    """Forgot password page."""
    with open("app/static/forgot_password.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/signup", response_class=HTMLResponse)
async def signup_page():
    """Signup page."""
    with open("app/static/signup.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/teacher", response_class=HTMLResponse)
@app.get("/teacher/dashboard", response_class=HTMLResponse)
async def teacher_dashboard(request: Request):
    """Teacher dashboard page."""
    try:
        teacher = await get_current_teacher(request)
    except HTTPException:
        return Response(status_code=302, headers={"Location": "/login"})

    with open("app/static/dashboard.html", "r", encoding="utf-8") as f:
        html = f.read()
    
    # Inject teacher info
    html = html.replace('{{name}}', teacher['name'])
    html = html.replace('{{unique_code}}', teacher['unique_code'])
    
    # Handle credits display
    credits_display = '∞' if teacher['is_admin'] else str(teacher['credits'])
    html = html.replace('{{credits}}', credits_display)

    return HTMLResponse(content=html)


# Auth API

class TeacherSignup(FeedbackRequest.__base__): # Inherit BaseModel
    name: str
    email: str
    password: str
    invitation_code: str

@app.post("/api/auth/signup")
async def signup(data: TeacherSignup):
    """Register a new teacher."""
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
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"
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

    # Get the created feedback
    feedback = get_feedback_by_id(feedback_id)

    # Set device ID cookie
    response.set_cookie(
        key="device_id",
        value=device_id,
        max_age=365*24*60*60,
        httponly=True,
        samesite="lax"
    )

    return FeedbackResponse(**feedback)


@app.get("/api/student/logout")
async def student_logout(response: Response):
    """Clear student teacher code cookie."""
    response = Response(status_code=302)
    response.headers["Location"] = "/"
    response.delete_cookie("teacher_code")
    return response


@app.get("/api/question")
async def get_question(
    teacher: dict = Depends(get_current_teacher)
):
    """Get the current teacher question."""
    question = get_setting(f"question_{teacher['id']}", "Comment s'est passé votre cours ?")
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
    feedbacks = get_all_feedbacks(teacher['id'])
    total = len(feedbacks)
    selected = sum(1 for fb in feedbacks if fb['included_in_analysis'])
    return {"total": total, "selected": selected}


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


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_feedbacks_endpoint(
    request_data: AnalyzeRequest, 
    request: Request,
    teacher: dict = Depends(get_current_teacher)
):
    """Analyze selected feedbacks and generate wordcloud (teacher only)."""
    # Admin has unlimited credits
    if not teacher.get('is_admin') and teacher['credits'] <= 0:
        raise HTTPException(status_code=403, detail="Crédits insuffisants. Veuillez recharger votre compte.")

    if not request_data.feedback_ids:
        raise HTTPException(status_code=400, detail="Veuillez sélectionner au moins un feedback")

    # Get selected feedbacks
    feedbacks = get_feedbacks_by_ids(request_data.feedback_ids)

    # Verify ownership
    for fb in feedbacks:
        if fb['teacher_id'] != teacher['id']:
             raise HTTPException(status_code=403, detail="Accès non autorisé à certains feedbacks")

    if not feedbacks:
        raise HTTPException(status_code=404, detail="Aucun feedback trouvé")

    try:
        # Extract content and emotions
        feedbacks_text = " ".join([fb["content"] for fb in feedbacks])
        feedback_contents = [fb["content"] for fb in feedbacks]
        feedback_emotions = [fb.get("emotion") for fb in feedbacks]

        # Run wordcloud (sync, CPU-bound) in thread pool so it doesn't block
        # the event loop, allowing the DeepSeek HTTP call to run concurrently
        async def run_wordcloud():
            return await asyncio.to_thread(create_wordcloud, feedbacks_text)

        async def run_ai_analysis():
            return await analyze_feedbacks(
                feedbacks=feedback_contents,
                context=request_data.context,
                emotions=feedback_emotions
            )

        wordcloud_result, summary = await asyncio.gather(
            run_wordcloud(),
            run_ai_analysis()
        )

        wordcloud_base64, word_frequencies = wordcloud_result

        if not summary:
            summary = "L'analyse IA n'est pas disponible. Le nuage de mots a été généré."
        
        # Deduct credit if not admin
        if not teacher.get('is_admin'):
            deduct_credit(teacher['id'])
        
        return {
            "summary": summary,
            "wordcloud_data": {"image": wordcloud_base64}
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'analyse: {str(e)}")


@app.post("/api/teacher/update_code")
async def update_code(
    request: Request,
    data: dict = Body(...),
    teacher: dict = Depends(get_current_teacher)
):
    """Update teacher's unique invite code."""
    new_code = data.get("code")
    if not new_code or len(new_code) < 3:
        raise HTTPException(status_code=400, detail="Code trop court (min 3 caractères)")
    
    success = update_teacher_code(teacher['id'], new_code)
    if not success:
        raise HTTPException(status_code=400, detail="Ce code est déjà utilisé, veuillez en choisir un autre")
    
    return {"status": "success", "new_code": new_code.upper()}


@app.post("/api/reset")
async def reset_database_endpoint(
    request: Request,
    teacher: dict = Depends(get_current_teacher)
):
    """Reset the database (teacher only)."""
    # For now, maybe restrict reset to admin or implement per-teacher reset (delete WHERE teacher_id=...)
    # Implementing per-teacher delete for safety
    # TODO: Refactor `reset_database` to accept teacher_id
    if teacher['is_admin']:
        reset_database()
        return {"success": True, "message": "Base de données réinitialisée (Admin)"}
    else:
        # For regular teachers, we might want a different function to clear only their data
        # For MVP, disabling reset for non-admins to prevent data loss
        raise HTTPException(status_code=403, detail="Action réservée aux administrateurs")


@app.get("/api/export/csv")
async def export_csv(
    request: Request,
    teacher: dict = Depends(get_current_teacher)
):
    """Export feedbacks as CSV (teacher only)."""
    import pandas as pd

    feedbacks = get_all_feedbacks(teacher['id'])

    if not feedbacks:
        raise HTTPException(status_code=404, detail="Aucun feedback à exporter")

    # Create DataFrame
    df = pd.DataFrame(feedbacks)
    # Filter columns to export
    columns = ["id", "content", "device_id", "created_at", "included_in_analysis", "emotion"]
    # Only keep columns that exist
    df = df[[c for c in columns if c in df.columns]]

    # Convert to CSV with UTF-8 BOM for Excel compatibility
    csv_buffer = df.to_csv(index=False, encoding="utf-8-sig")

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
        
        reset_link = f"https://afeedny.up.railway.app/reset-password?token={reset_token}" # Replace with env var for domain
        
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
    with open("app/static/reset_password.html", "r", encoding="utf-8") as f:
        html = f.read()
    # Inject token into JS
    html = html.replace('{{token}}', token)
    return HTMLResponse(content=html)


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
    """Upload a payment receipt."""
    # Ensure uploads directory exists
    UPLOAD_DIR = "app/static/uploads/receipts"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    # Save file
    file_ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4()}{file_ext}"
    file_path = f"{UPLOAD_DIR}/{filename}"
    
    with open(file_path, "wb") as buffer:
        import shutil
        shutil.copyfileobj(file.file, buffer)
        
    # Create receipt record
    # Store relative path for serving
    relative_path = f"/static/uploads/receipts/{filename}"
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
        
    # Approve and add credits (e.g., 5 credits per valid payment)
    # TODO: Make credit amount configurable or part of the request
    CREDITS_PER_PAYMENT = 10 
    
    update_receipt_status(receipt_id, 'approved')
    add_credits(receipt['teacher_id'], CREDITS_PER_PAYMENT)
    
    return {"status": "success", "message": f"Reçu validé, {CREDITS_PER_PAYMENT} crédits ajoutés"}


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

    with open("app/static/admin.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


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

        if not wordcloud_image or not analysis_text:
            raise HTTPException(status_code=400, detail="Données manquantes pour générer le PDF")

        # Generate PDF
        pdf_bytes = create_analysis_pdf(
            wordcloud_image_base64=wordcloud_image,
            analysis_text=analysis_text,
            context=context
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
    uvicorn.run(app, host="0.0.0.0", port=8000)


