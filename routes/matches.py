from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
import database

router = APIRouter()

@router.get("/")
async def get_all_matches(db: AsyncSession = Depends(database.get_db)):
    query = text("SELECT * FROM playerz.matches ORDER BY id DESC")
    result = await db.execute(query)
    matches = result.fetchall()

    if not matches:
        return {"message": "MATCHES_NOT_FOUND", "matches": []}

    columns = result.keys()
    matches_list = [dict(zip(columns, match)) for match in matches]
    return {"message": "SUCCESS", "matches": matches_list}

@router.get("/{id}")
async def get_match_by_id(id: int, db: AsyncSession = Depends(database.get_db)):
    query = text("SELECT * FROM playerz.matches WHERE id = :id")
    result = await db.execute(query, {"id": id})
    match = result.fetchone()

    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="MATCH_NOT_FOUND"
        )

    columns = result.keys()
    match_dict = dict(zip(columns, match))
    return {"message": "SUCCESS", "match": match_dict}

@router.post("/")
async def create_match(match_data: dict, db: AsyncSession = Depends(database.get_db)):
    try:
        keys = ", ".join(match_data.keys())
        values = ", ".join([f":{key}" for key in match_data.keys()])
        query = text(
            f"INSERT INTO playerz.matches ({keys}) VALUES ({values}) RETURNING id"
        )
        result = await db.execute(query, match_data)
        new_match_id = result.scalar()
        await db.commit()
        return {"message": "MATCH_CREATED", "match_id": new_match_id}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )

@router.put("/{id}")
async def update_match(id: int, match_data: dict, db: AsyncSession = Depends(database.get_db)):
    try:
        set_clause = ", ".join([f"{key} = :{key}" for key in match_data.keys()])
        query = text(
            f"UPDATE playerz.matches SET {set_clause} WHERE id = :id RETURNING *"
        )
        result = await db.execute(query, {**match_data, "id": id})
        updated_match = result.fetchone()
        await db.commit()
        if updated_match is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="MATCH_NOT_FOUND"
            )
        columns = result.keys()
        match_dict = dict(zip(columns, updated_match))
        return {"message": "MATCH_UPDATED", "match": match_dict}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )

@router.delete("/{id}")
async def delete_match(id: int, db: AsyncSession = Depends(database.get_db)):
    try:
        query = text("DELETE FROM playerz.matches WHERE id = :id RETURNING *")
        result = await db.execute(query, {"id": id})
        deleted_match = result.fetchone()
        await db.commit()
        if deleted_match is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="MATCH_NOT_FOUND"
            )
        columns = result.keys()
        match_dict = dict(zip(columns, deleted_match))
        return {"message": "MATCH_DELETED", "match": match_dict}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) 