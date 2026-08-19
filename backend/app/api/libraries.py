from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Library
from app.schemas.library import LibraryCreate, LibraryDetailResponse, LibraryResponse, LibraryUpdate

router = APIRouter()


@router.get("", response_model=list[LibraryDetailResponse])
async def list_libraries(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Library).options(selectinload(Library.folders)).order_by(Library.name)
    )
    return result.scalars().all()


@router.post("", response_model=LibraryResponse, status_code=201)
async def create_library(body: LibraryCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Library).where(Library.name == body.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Library name already exists")

    library = Library(name=body.name)
    db.add(library)
    await db.commit()
    await db.refresh(library)
    return library


@router.patch("/{library_id}", response_model=LibraryResponse)
async def update_library(library_id: int, body: LibraryUpdate, db: AsyncSession = Depends(get_db)):
    library = await db.get(Library, library_id)
    if not library:
        raise HTTPException(status_code=404, detail="Library not found")

    if body.name is not None:
        library.name = body.name

    await db.commit()
    await db.refresh(library)
    return library


@router.delete("/{library_id}", status_code=204)
async def delete_library(library_id: int, db: AsyncSession = Depends(get_db)):
    library = await db.get(Library, library_id)
    if not library:
        raise HTTPException(status_code=404, detail="Library not found")

    await db.delete(library)
    await db.commit()
