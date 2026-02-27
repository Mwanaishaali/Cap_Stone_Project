"""API v1 router — assembles all endpoint sub-routers."""
from fastapi import APIRouter

from app.api.v1.endpoints import careers, courses, skills, risk, occupations, dashboard

api_router = APIRouter()

api_router.include_router(careers.router,     prefix="/careers",     tags=["Careers"])
api_router.include_router(skills.router,      prefix="/skills",      tags=["Skills Gap"])
api_router.include_router(courses.router,     prefix="/courses",     tags=["Courses"])
api_router.include_router(risk.router,        prefix="/risk",        tags=["AI Risk"])
api_router.include_router(occupations.router, prefix="/occupations", tags=["Occupations"])
api_router.include_router(dashboard.router,   prefix="/dashboard",   tags=["Dashboard"])
