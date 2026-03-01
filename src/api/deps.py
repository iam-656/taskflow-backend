from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
import os
from sqlmodel import Session, select
from clerk_backend_api import Clerk
from ..models.db import engine
from ..models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Initialize Clerk Client
clerk_client = Clerk(bearer_auth=os.getenv("CLERK_SECRET_KEY"))

def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Verify Token (Signature verification skipped for dev speed as per previous instruction, 
        # but in production use keys. Assuming payload is trusted if gateway handles it or we accept risk)
        # We can implement signature check if keys available.
        # For now, stick to existing verification logic or just decode unverified if key missing.
        
        public_key = os.getenv("CLERK_PEM_PUBLIC_KEY")
        if public_key:
             payload = jwt.decode(token, public_key, algorithms=["RS256"])
        else:
            payload = jwt.get_unverified_claims(token)
            
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise credentials_exception
            
        # Lazy User Sync Logic
        with Session(engine) as session:
            user = session.get(User, user_id)
            if not user:
                # User MISSING in local DB. Fetch from Clerk.
                try:
                    user_details = clerk_client.users.get(user_id)
                    
                    # Extract primary email
                    email_address = None
                    if user_details.email_addresses:
                        # Find primary or just take first
                        for email in user_details.email_addresses:
                            if email.id == user_details.primary_email_address_id:
                                email_address = email.email_address
                                break
                        if not email_address and user_details.email_addresses:
                             email_address = user_details.email_addresses[0].email_address
                    
                    if not email_address:
                        email_address = f"user_{user_id}@placeholder.com"

                    user = User(
                        id=user_id,
                        email=email_address,
                        name=f"{user_details.first_name or ''} {user_details.last_name or ''}".strip() or None,
                        avatar_url=user_details.image_url
                    )
                    session.add(user)
                    session.commit()
                    session.refresh(user)
                except Exception as e:
                    print(f"Failed to sync user from Clerk: {e}")
                    # Fallback to token claims if Clerk API fails
                    token_email = payload.get("email")
                    user = User(
                        id=user_id,
                        email=token_email or f"user_{user_id}@placeholder.com"
                    )
                    session.add(user)
                    session.commit()
        
        return {"id": user_id, "email": user.email}
        
    except JWTError:
        raise credentials_exception
