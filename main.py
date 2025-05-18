from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import List, Optional
import pandas as pd
import os
from dotenv import load_dotenv
from pydantic import BaseModel
import json

from scraper import OLXScraper
from scheduler import ScrapingScheduler

load_dotenv()

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI(title="OLX Scraper API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

scraper = OLXScraper()
scheduler = ScrapingScheduler()

try:
    scraper.existing_listings = [] 
except Exception as e:
    print(f"Error initializing scraper: {e}")

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class User(BaseModel):
    username: str
    disabled: Optional[bool] = None

class Listing(BaseModel):
    id: str
    title: str
    price: str
    location: str
    date: str
    link: str
    image_url: Optional[str]
    scraped_at: str
    is_new: bool
    seen: bool

class ScrapeResponse(BaseModel):
    new_listings: List[Listing]
    total_listings: int
    unseen_listings: int

def verify_password(plain_password, hashed_password):
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        print(f"Password verification error: {e}")
        return False

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(username: str, password: str):
    stored_username = os.getenv("ADMIN_USERNAME", "admin")
    stored_password = os.getenv("ADMIN_PASSWORD", "admin123")
    
    if os.getenv("ENVIRONMENT") == "development":
        return username == stored_username and password == stored_password
    
    # For production, use proper password hashing
    if username != stored_username:
        return False
    
    # If the stored password is not hashed, hash it and update the environment variable
    if not stored_password.startswith("$2b$"):
        hashed_password = get_password_hash(stored_password)
        # Note: In a real application, you would update this in a secure database
        # For now, I'll just use the hashed version for comparison
        return pwd_context.verify(password, hashed_password)
    
    return verify_password(password, stored_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    if token_data.username != os.getenv("ADMIN_USERNAME", "admin"):
        raise credentials_exception
    return token_data

# Routes
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_listings(current_user: TokenData = Depends(get_current_user)):
    try:
        new_listings = scraper.scrape()
        
        all_listings = scraper.existing_listings
        unseen_listings = scraper.get_unseen_listings()
        
        return {
            "new_listings": new_listings,
            "total_listings": len(all_listings),
            "unseen_listings": len(unseen_listings)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/listings", response_model=List[Listing])
async def get_listings(
    include_seen: bool = True,
    current_user: TokenData = Depends(get_current_user)
):
    try:
        if not hasattr(scraper, 'existing_listings'):
            scraper.existing_listings = []
        
        listings = scraper.existing_listings if include_seen else scraper.get_unseen_listings()
        
        if not listings:
            return []
        
        formatted_listings = []
        seen_ids = set() 
        
        for index, listing in enumerate(listings):
            try:
                base_id = str(listing.get("id", ""))
                unique_id = f"{base_id}-{index}" if base_id in seen_ids else base_id
                seen_ids.add(base_id)
                
                formatted_listing = {
                    "id": unique_id,
                    "title": str(listing.get("title", "")),
                    "price": str(listing.get("price", "")),
                    "location": str(listing.get("location", "")),
                    "date": str(listing.get("date", "")),
                    "link": str(listing.get("link", "")),
                    "image_url": str(listing.get("image_url", "")) if listing.get("image_url") else None,
                    "scraped_at": str(listing.get("scraped_at", datetime.now().isoformat())),
                    "is_new": bool(listing.get("is_new", False)),
                    "seen": bool(listing.get("seen", False))
                }
                
                if not all([formatted_listing["id"], formatted_listing["title"], 
                          formatted_listing["price"], formatted_listing["location"], 
                          formatted_listing["link"]]):
                    print(f"Skipping invalid listing: {listing}")
                    continue
                    
                formatted_listings.append(formatted_listing)
            except Exception as e:
                print(f"Error formatting listing: {e}")
                continue
        
        return formatted_listings
    except Exception as e:
        print(f"Error in get_listings: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch listings: {str(e)}"
        )

@app.post("/listings/mark-seen")
async def mark_listings_seen(
    listing_ids: List[str],
    current_user: TokenData = Depends(get_current_user)
):
    try:
        scraper.mark_as_seen(listing_ids)
        return {"message": f"Marked {len(listing_ids)} listings as seen"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/listings/export")
async def export_listings(
    format: str = "csv",
    include_seen: bool = True,
    current_user: TokenData = Depends(get_current_user)
):
    try:
        if format.lower() == "csv":
            filename = "listings.csv" if include_seen else "unseen_listings.csv"
            scraper.export_to_csv(filename, include_seen)
        elif format.lower() == "excel":
            filename = "listings.xlsx" if include_seen else "unseen_listings.xlsx"
            scraper.export_to_excel(filename, include_seen)
        else:
            raise HTTPException(status_code=400, detail="Invalid format. Use 'csv' or 'excel'")
        
        return {"message": f"Exported listings to {filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    scheduler.start()

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.stop()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 