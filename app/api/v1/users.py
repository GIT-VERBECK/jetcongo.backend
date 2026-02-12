from typing import Any
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Response
from sqlalchemy.orm import Session

from app.db import models, schemas
from app.api import deps

router = APIRouter()


@router.get("/me", response_model=schemas.Utilisateur)
def read_user_me(
    current_user: models.Utilisateur = Depends(deps.get_current_user),
) -> Any:
    return current_user


@router.post("/me/avatar", status_code=status.HTTP_200_OK)
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(deps.get_db),
    current_user: models.Utilisateur = Depends(deps.get_current_user),
) -> Any:
    """
    Reçoit un fichier image et le stocke directement dans la table utilisateur
    (colonnes avatar + avatar_mime).
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seuls les fichiers image sont autorisés.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier envoyé est vide.",
        )

    current_user.avatar = content
    current_user.avatar_mime = file.content_type
    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return {"status": "avatar_updated"}


@router.get("/me/avatar")
def get_avatar(
    current_user: models.Utilisateur = Depends(deps.get_current_user),
) -> Response:
    """
    Renvoie l'avatar de l'utilisateur courant sous forme d'image binaire.
    Si aucun avatar n'est encore défini, renvoie 404 pour laisser le front afficher l'image par défaut.
    """
    if not current_user.avatar:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar non défini.")

    media_type = current_user.avatar_mime or "image/png"
    return Response(content=current_user.avatar, media_type=media_type)
