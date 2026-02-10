import os
import sys
import uuid
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, Response, HTTPException, Depends, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

import asyncio

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    import_feedbacks
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
TEACHER_PASSWORD = os.getenv("TEACHER_PASSWORD", "admin123")


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()


def get_device_id(request: Request) -> str:
    """Get or create device ID from cookie."""
    device_id = request.cookies.get("device_id")
    if not device_id:
        device_id = str(uuid.uuid4())
    return device_id


def verify_teacher_token(request: Request) -> bool:
    """Verify teacher authentication token."""
    token = request.cookies.get("teacher_token")
    return token == SECRET_KEY


# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")


# Routes
@app.get("/", response_class=HTMLResponse)
async def student_page(request: Request):
    """Student feedback page."""
    device_id = get_device_id(request)
    can_submit, _ = check_device_limit(device_id)

    with open("app/static/index.html", "r", encoding="utf-8") as f:
        html = f.read()

    # Inject data (handle optional spaces in tags)
    import re
    html = re.sub(r'\{\{\s*device_id\s*\}\}', device_id, html)
    html = re.sub(r'\{\{\s*can_submit\s*\}\}', str(can_submit).lower(), html)

    response = Response(content=html, media_type="text/html")

    # Set device ID cookie if not present
    if not request.cookies.get("device_id"):
        response.set_cookie(
            key="device_id",
            value=device_id,
            max_age=365*24*60*60,  # 1 year
            httponly=True,
            samesite="lax"
        )

    return response


@app.get("/teacher", response_class=HTMLResponse)
async def teacher_page(request: Request):
    """Teacher dashboard page."""
    if not verify_teacher_token(request):
        with open("app/static/login.html", "r", encoding="utf-8") as f:
            return Response(content=f.read(), media_type="text/html")

    feedbacks = get_all_feedbacks()
    stats = get_feedback_stats()

    with open("app/static/dashboard.html", "r", encoding="utf-8") as f:
        html = f.read()

    response = Response(content=html, media_type="text/html")
    return response


# API Routes - Student
@app.post("/api/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    http_request: Request,
    response: Response
):
    """Submit a new feedback with optional emotion."""
    device_id = get_device_id(http_request)

    # Check if device has already submitted
    can_submit, count = check_device_limit(device_id)
    if not can_submit:
        raise HTTPException(status_code=403, detail="Vous avez déjà soumis un feedback")

    # Insert feedback with emotion
    feedback_id = insert_feedback(request.content, device_id, request.emotion)
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
@app.post("/api/teacher/login", response_model=TeacherLoginResponse)
async def teacher_login(login_data: TeacherLoginRequest, response: Response):
    """Authenticate teacher."""
    if login_data.password == TEACHER_PASSWORD:
        response.set_cookie(
            key="teacher_token",
            value=SECRET_KEY,
            max_age=24*60*60,  # 24 hours
            httponly=True,
            samesite="lax"
        )
        return TeacherLoginResponse(
            success=True,
            token=SECRET_KEY,
            message="Connexion réussie"
        )
    else:
        return TeacherLoginResponse(
            success=False,
            message="Mot de passe incorrect"
        )


@app.get("/api/feedbacks", response_model=FeedbackListResponse)
async def get_feedbacks_list(request: Request):
    """Get all feedbacks (teacher only)."""
    if not verify_teacher_token(request):
        raise HTTPException(status_code=401, detail="Non autorisé")

    feedbacks = get_all_feedbacks()
    return FeedbackListResponse(
        feedbacks=[FeedbackResponse(**fb) for fb in feedbacks],
        total=len(feedbacks)
    )


@app.put("/api/feedbacks/{feedback_id}/toggle", response_model=dict)
async def toggle_feedback(feedback_id: int, request: Request):
    """Toggle feedback inclusion in analysis (teacher only)."""
    if not verify_teacher_token(request):
        raise HTTPException(status_code=401, detail="Non autorisé")

    success = toggle_feedback_inclusion(feedback_id)
    if not success:
        raise HTTPException(status_code=404, detail="Feedback non trouvé")

    return {"success": True, "message": "Statut mis à jour"}


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_feedbacks_endpoint(request_data: AnalyzeRequest, request: Request):
    """Analyze selected feedbacks and generate wordcloud (teacher only)."""
    if not verify_teacher_token(request):
        raise HTTPException(status_code=401, detail="Non autorisé")

    if not request_data.feedback_ids:
        raise HTTPException(status_code=400, detail="Veuillez sélectionner au moins un feedback")

    # Get selected feedbacks
    feedbacks = get_feedbacks_by_ids(request_data.feedback_ids)

    if not feedbacks:
        raise HTTPException(status_code=404, detail="Aucun feedback trouvé")

    # Extract content and emotions
    feedbacks_text = " ".join([fb["content"] for fb in feedbacks])
    feedback_contents = [fb["content"] for fb in feedbacks]
    feedback_emotions = [fb.get("emotion") for fb in feedbacks]

    # Run wordcloud generation and AI analysis in parallel
    async def run_wordcloud():
        return create_wordcloud(feedbacks_text)

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

    wordcloud_image, word_frequencies = wordcloud_result

    if not summary:
        summary = "Erreur lors de la génération du résumé. Veuillez réessayer."

    return AnalyzeResponse(
        summary=summary,
        wordcloud_data={
            "image": wordcloud_image,
            "frequencies": word_frequencies
        }
    )


@app.post("/api/reset")
async def reset_database_endpoint(request: Request):
    """Reset the database (teacher only)."""
    if not verify_teacher_token(request):
        raise HTTPException(status_code=401, detail="Non autorisé")

    reset_database()
    return {"success": True, "message": "Base de données réinitialisée"}


@app.get("/api/export/csv")
async def export_csv(request: Request):
    """Export feedbacks as CSV (teacher only)."""
    if not verify_teacher_token(request):
        raise HTTPException(status_code=401, detail="Non autorisé")

    import pandas as pd

    feedbacks = get_all_feedbacks()

    if not feedbacks:
        raise HTTPException(status_code=404, detail="Aucun feedback à exporter")

    # Create DataFrame
    df = pd.DataFrame(feedbacks)
    df = df[["id", "content", "device_id", "created_at", "included_in_analysis"]]

    # Convert to CSV with UTF-8 BOM for Excel compatibility
    csv_buffer = df.to_csv(index=False, encoding="utf-8-sig")

    return Response(
        content=csv_buffer,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=feedny_feedbacks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )


@app.post("/api/teacher/logout")
async def teacher_logout(response: Response):
    """Logout teacher."""
    response.delete_cookie("teacher_token")
    return {"success": True, "message": "Déconnexion réussie"}


@app.get("/api/stats")
async def get_stats_endpoint(request: Request):
    """Get feedback statistics (teacher only)."""
    if not verify_teacher_token(request):
        raise HTTPException(status_code=401, detail="Non autorisé")

    return get_feedback_stats()


# Health check endpoints for Railway serverless
@app.get("/health")
async def health_check():
    """Health check endpoint for Railway."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/healthz")
async def healthz():
    """Alias health check endpoint."""
    return {"status": "healthy"}


# JSON Export/Import for data persistence
@app.get("/api/export/json")
async def export_json(request: Request):
    """Export feedbacks as JSON (teacher only)."""
    if not verify_teacher_token(request):
        raise HTTPException(status_code=401, detail="Non autorisé")

    feedbacks = get_all_feedbacks()

    if not feedbacks:
        raise HTTPException(status_code=404, detail="Aucun feedback à exporter")

    import json

    json_content = json.dumps({
        "exported_at": datetime.now().isoformat(),
        "feedbacks": feedbacks
    }, ensure_ascii=False, indent=2, default=str)

    return Response(
        content=json_content,
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=feedny_feedbacks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        }
    )


@app.post("/api/import")
async def import_json(request: Request):
    """Import feedbacks from JSON (teacher only)."""
    if not verify_teacher_token(request):
        raise HTTPException(status_code=401, detail="Non autorisé")

    try:
        import json
        body = await request.body()
        data = json.loads(body.decode('utf-8'))
        
        feedbacks_data = data.get('feedbacks', [])
        if not feedbacks_data:
            raise HTTPException(status_code=400, detail="Aucun feedback dans le fichier")
        
        imported_count = import_feedbacks(feedbacks_data)
        
        return {
            "success": True,
            "message": f"{imported_count} feedbacks importés avec succès",
            "count": imported_count
        }
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Format JSON invalide")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'import: {str(e)}")


# PDF Export Endpoint
@app.post("/api/export/pdf")
async def export_pdf(request: Request):
    """Generate PDF with wordcloud and analysis (teacher only)."""
    if not verify_teacher_token(request):
        raise HTTPException(status_code=401, detail="Non autorisé")

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


