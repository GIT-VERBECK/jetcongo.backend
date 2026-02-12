from typing import Any
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Response
from sqlalchemy.orm import Session

from app.db import models, schemas, crud
from app.api import deps
from app.core import security

router = APIRouter()


@router.get("/me", response_model=schemas.Utilisateur)
def read_user_me(
    current_user: models.Utilisateur = Depends(deps.get_current_user),
) -> Any:
    return current_user


@router.put("/me", response_model=schemas.Utilisateur)
def update_user_me(
    user_in: schemas.UtilisateurUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.Utilisateur = Depends(deps.get_current_user),
) -> Any:
    """
    Permet à l'utilisateur de mettre à jour ses informations
    d'identification (nom, email) dans la section 'Informations personnelles'.
    """
    # Si l'email change, vérifier qu'il n'est pas déjà utilisé
    if user_in.email and user_in.email != current_user.email:
        existing = crud.get_user_by_email(db, email=user_in.email)
        if existing and existing.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un utilisateur avec cet email existe déjà.",
            )

    return crud.update_user(db, current_user, user_in)


@router.post("/me/password", status_code=status.HTTP_200_OK)
def change_password_me(
    payload: schemas.ChangePassword,
    db: Session = Depends(deps.get_db),
    current_user: models.Utilisateur = Depends(deps.get_current_user),
) -> Any:
    """
    Changement de mot de passe depuis l'onglet Sécurité.
    """
    if not security.verify_password(payload.old_password, current_user.mot_de_passe):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mot de passe actuel incorrect.",
        )

    crud.change_user_password(db, current_user, payload.new_password)
    return {"status": "password_updated"}


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
