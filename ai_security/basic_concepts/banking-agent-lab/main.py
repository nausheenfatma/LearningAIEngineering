
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import jwt
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field


# --------------------------------------------------
# 1. APP AND JWT CONFIGURATION
# --------------------------------------------------

app = FastAPI(title="Banking Agent Authentication Lab")

BASE_DIR = Path(__file__).resolve().parent
PRIVATE_KEY = (BASE_DIR / "keys" / "private.pem").read_text()
PUBLIC_KEY = (BASE_DIR / "keys" / "public.pem").read_text()

JWT_ALGORITHM = "RS256"
JWT_ISSUER = "http://localhost:8000"
JWT_AUDIENCE = "banking-agent-api"

security = HTTPBearer()

# DEMO ONLY: In production, roles come from a trusted identity provider.
DEMO_USERS = {
    "alice_support": {
        "sub": "alice_support",
        "roles": ["customer_support"],
    },
    "bob_operator": {
        "sub": "bob_operator",
        "roles": ["transaction_operator"],
    },
}


# --------------------------------------------------
# 2. RBAC: ROLE -> PERMISSIONS
# --------------------------------------------------

ROLE_PERMISSIONS = {
    "customer_support": {
        "customer.read",
    },
    "transaction_operator": {
        "customer.read",
        "balance.read",
        "balance.update",
    },
}


def get_permissions(roles: list[str]) -> set[str]:
    """Return the permissions granted by the user's roles."""
    permissions = set()

    for role in roles:
        permissions.update(ROLE_PERMISSIONS.get(role, set()))

    return permissions


def authorize(roles: list[str], required_permission: str) -> None:
    """Raise 403 when the user lacks the required permission."""
    permissions = get_permissions(roles)

    if required_permission not in permissions:
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: {required_permission}",
        )


# --------------------------------------------------
# 3. DEMO JWT ISSUER
# --------------------------------------------------

@app.post("/demo/token")
def create_demo_token(username: str):
    """
    DEMO ONLY.
    A real system must not let callers choose their own roles.
    """
    user = DEMO_USERS.get(username)

    if not user:
        raise HTTPException(status_code=401, detail="Unknown demo user")

    now = datetime.now(timezone.utc)

    payload = {
        "sub": user["sub"],
        "roles": user["roles"],
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": now,
        "exp": now + timedelta(minutes=30),
    }

    token = jwt.encode(
        payload,
        PRIVATE_KEY,
        algorithm=JWT_ALGORITHM,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "roles": user["roles"],
    }


# --------------------------------------------------
# 4. AUTHENTICATION: VALIDATE JWT
# --------------------------------------------------

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, Any]:
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            PUBLIC_KEY,
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
            options={
                "require": ["sub", "roles", "iss", "aud", "exp", "iat"]
            },
        )

        if not isinstance(payload["roles"], list):
            raise HTTPException(
                status_code=401,
                detail="Invalid roles claim",
            )

        return {
            "sub": payload["sub"],
            "roles": payload["roles"],
        }

    except jwt.PyJWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )


# --------------------------------------------------
# 5. FAKE BANK DATA
# --------------------------------------------------

CUSTOMERS = {
    "C1001": {
        "customer_id": "C1001",
        "name": "Alice Smith",
        "account_type": "Savings",
    },
    "C1002": {
        "customer_id": "C1002",
        "name": "Bob Jones",
        "account_type": "Checking",
    },
}

# In-memory balances for learning purposes only.
BALANCES = {
    "C1001": 1500.00,
    "C1002": 2500.00,
}


# --------------------------------------------------
# 6. TOOL IMPLEMENTATIONS
# --------------------------------------------------

def read_customer_details(customer_id: str) -> dict:
    customer = CUSTOMERS.get(customer_id)

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    return customer


def read_balance(customer_id: str) -> dict:
    balance = BALANCES.get(customer_id)

    if balance is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    return {
        "customer_id": customer_id,
        "balance": balance,
        "currency": "CAD",
    }


def update_balance(customer_id: str, amount: float) -> dict:
    if customer_id not in BALANCES:
        raise HTTPException(status_code=404, detail="Customer not found")

    if amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Amount must be greater than zero",
        )

    # Demo behavior: add money to the in-memory balance.
    BALANCES[customer_id] += amount

    return {
        "customer_id": customer_id,
        "amount_added": amount,
        "new_balance": BALANCES[customer_id],
        "currency": "CAD",
    }


# --------------------------------------------------
# 7. AGENT TOOL REGISTRY
# --------------------------------------------------
# Each agent has an allowlist of tools.
# Each tool also requires a user permission.

AGENT_TOOLS = {
    "customer-greeting": {
        "read_customer_details": {
            "permission": "customer.read",
            "execute": read_customer_details,
        },
    },
    "transaction": {
        "read_customer_details": {
            "permission": "customer.read",
            "execute": read_customer_details,
        },
        "read_balance": {
            "permission": "balance.read",
            "execute": read_balance,
        },
        "update_balance": {
            "permission": "balance.update",
            "execute": update_balance,
        },
    },
}


# --------------------------------------------------
# 8. TOOL INPUT SCHEMAS
# --------------------------------------------------

class CustomerRequest(BaseModel):
    customer_id: str


class UpdateBalanceRequest(BaseModel):
    customer_id: str
    amount: float = Field(gt=0)


# --------------------------------------------------
# 9. AGENT HARNESS: CHECK TOOL + PERMISSION
# --------------------------------------------------

def run_agent_tool(
    
    agent_name: str,
    tool_name: str,
    arguments: dict,
    user: dict,
):
    # Check 1: Is this tool allowed for this agent?
    agent_registry = AGENT_TOOLS.get(agent_name)

    if agent_registry is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    tool = agent_registry.get(tool_name)

    if tool is None:
        raise HTTPException(
            status_code=403,
            detail=f"{tool_name} is not allowed for {agent_name}",
        )

    # Check 2: Does the authenticated user have permission?
    authorize(user["roles"], tool["permission"])

    # Check 3: Validate tool arguments and execute the function.
    if tool_name in {"read_customer_details", "read_balance"}:
        request = CustomerRequest(**arguments)
        return tool["execute"](request.customer_id)

    if tool_name == "update_balance":
        request = UpdateBalanceRequest(**arguments)
        return tool["execute"](
            request.customer_id,
            request.amount,
        )

    raise HTTPException(status_code=400, detail="Unsupported tool")


# --------------------------------------------------
# 10. API ENDPOINTS FOR THE AGENTS
# --------------------------------------------------

@app.post("/agents/{agent_name}/tools/{tool_name}")
def invoke_agent_tool(
    agent_name: str,
    tool_name: str,
    arguments: dict,
    user: dict = Depends(get_current_user),
):
    result = run_agent_tool(
        agent_name=agent_name,
        tool_name=tool_name,
        arguments=arguments,
        user=user,
    )

    return {
        "agent": agent_name,
        "tool": tool_name,
        "called_by": user["sub"],
        "result": result,
    }


@app.get("/")
def health_check():
    return {"status": "ok", "message": "Banking Agent API is running"}
