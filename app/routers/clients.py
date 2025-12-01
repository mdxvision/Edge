from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db import get_db, Client
from app.schemas.clients import ClientCreate, ClientUpdate, ClientRead
from app.config import RISK_PROFILES

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.post("/", response_model=ClientRead)
def create_client(client_data: ClientCreate, db: Session = Depends(get_db)):
    if client_data.risk_profile not in RISK_PROFILES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid risk profile. Must be one of: {RISK_PROFILES}"
        )
    
    client = Client(
        name=client_data.name,
        bankroll=client_data.bankroll,
        risk_profile=client_data.risk_profile
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


@router.get("/{client_id}", response_model=ClientRead)
def get_client(client_id: int, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.id == client_id).first()
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.get("/", response_model=List[ClientRead])
def list_clients(db: Session = Depends(get_db)):
    return db.query(Client).all()


@router.patch("/{client_id}", response_model=ClientRead)
def update_client(
    client_id: int, 
    client_data: ClientUpdate, 
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(Client.id == client_id).first()
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if client_data.name is not None:
        client.name = client_data.name
    
    if client_data.bankroll is not None:
        client.bankroll = client_data.bankroll
    
    if client_data.risk_profile is not None:
        if client_data.risk_profile not in RISK_PROFILES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid risk profile. Must be one of: {RISK_PROFILES}"
            )
        client.risk_profile = client_data.risk_profile
    
    db.commit()
    db.refresh(client)
    return client


@router.delete("/{client_id}")
def delete_client(client_id: int, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.id == client_id).first()
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    
    db.delete(client)
    db.commit()
    return {"message": "Client deleted successfully"}
