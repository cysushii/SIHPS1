from datetime import datetime, timezone, timedelta
import jwt
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET_KEY = "sih26263_secret_super_key_for_hackathon_demo"
ALGORITHM = "HS256"

security = HTTPBearer(auto_error=False)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Creates a signed JWT with claims (e.g. role, institute_id, sub)."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=24)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired.")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authorization token.")

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing Authorization Bearer Header.")
    return decode_token(credentials.credentials)

def require_role(allowed_roles: list[str]):
    """
    Dependency factory to enforce RBAC based on user role claim.
    Roles:
      - 'aicte_admin'
      - 'institute_admin'
      - 'verifier'
    """
    def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        role = current_user.get("role")
        if role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Access forbidden: requires one of {allowed_roles}, but found '{role}'."
            )
        return current_user
    return role_checker

