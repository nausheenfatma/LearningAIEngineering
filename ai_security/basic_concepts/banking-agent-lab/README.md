# Banking Agent Authentication Lab

A hands-on Python project demonstrating how to secure AI agent tools using **JWT authentication, Role-Based Access Control (RBAC), and agent-level tool permissions**.

The project simulates a simple banking environment with two agents:

- **Customer Greeting Agent:** Reads customer details to support customer interactions.
- **Transaction Agent:** Reads customer details, reads account balances, and updates demo balances.

The goal is to understand how authentication and authorization work together when an AI agent invokes tools or backend functions.

> **Disclaimer:** This is an educational demo. It uses mock customer data, in-memory balances, locally generated JWT keys, and a demo token endpoint. It is not suitable for production use or real financial transactions.

## Table of Contents

- [Architecture](#architecture)
- [Key Concepts](#key-concepts)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup and Installation](#setup-and-installation)
- [Run the Application](#run-the-application)
- [Demo Users and Permissions](#demo-users-and-permissions)
- [API Endpoints](#api-endpoints)
- [Testing the Application](#testing-the-application)
- [Authorization Flow](#authorization-flow)
- [Security Considerations](#security-considerations)
- [Future Enhancements](#future-enhancements)

## Architecture

```text
                         Client
                           |
                           | HTTP request + JWT
                           v
                   FastAPI Application
                           |
                           v
                    JWT Authentication
                     get_current_user()
                           |
                 Authentication succeeds?
                           |
                           v
                   Agent Tool Endpoint
                           |
                           v
                      Agent Harness
                           |
               +-----------+-----------+
               |                       |
               v                       v
         Agent Tool Allowlist     RBAC Permission
               |                       |
               +-----------+-----------+
                           |
                    Both checks pass
                           |
                           v
                     Tool Function
                           |
               +-----------+-----------+
               |           |           |
               v           v           v
          Read Customer  Read Balance  Update Balance
               |           |           |
               +-----------+-----------+
                           |
                           v
                    Mock Banking Data
```

The application separates three security responsibilities:

1. **Authentication:** Is the caller presenting a valid JWT?
2. **Agent-level authorization:** Is this tool available to the requested agent?
3. **User-level authorization:** Does the authenticated user's role grant the permission required by the tool?

A request can proceed only when all required checks succeed.

## Key Concepts

### 1. JWT Authentication

JSON Web Tokens (JWTs) carry claims about an authenticated identity.

In this project, the demo token endpoint issues signed JWTs containing claims such as:

- `sub`: User identity.
- `roles`: The user's assigned roles.
- `iss`: Token issuer.
- `aud`: Intended audience.
- `iat`: Token issue time.
- `exp`: Token expiry time.

The application uses RSA keys and the RS256 signing algorithm.

The `get_current_user()` FastAPI dependency validates the JWT signature, issuer, audience, expiry, and required claims before the protected endpoint handler executes.

### 2. Role-Based Access Control (RBAC)

RBAC maps roles to permissions.

| Role | Permissions |
|---|---|
| `customer_support` | `customer.read` |
| `transaction_operator` | `customer.read`, `balance.read`, `balance.update` |

Permissions are evaluated using the authenticated user's roles.

For example, a customer support user can read customer details but cannot update balances.

### 3. Agent-Level Tool Permissions

Each agent has its own tool allowlist.

| Tool | Customer Greeting Agent | Transaction Agent |
|---|---|---|
| `read_customer_details` | Allowed | Allowed |
| `read_balance` | Not allowed | Allowed |
| `update_balance` | Not allowed | Allowed |

The allowlist determines which tools an agent can invoke. RBAC independently determines whether the authenticated user has permission to invoke the selected tool.

This means that granting a user a permission does not automatically make every tool available to every agent.

### 4. Agent Harness

The agent harness is the control layer between an agent request and tool execution.

In this project, `run_agent_tool()`:

1. Verifies that the requested agent exists.
2. Checks whether the requested tool is in the agent's allowlist.
3. Checks the user's required RBAC permission.
4. Validates the tool arguments.
5. Executes the corresponding Python function.

## Technology Stack

- **Python:** Application implementation.
- **FastAPI:** HTTP API and dependency-based authentication.
- **PyJWT:** JWT creation and validation.
- **Cryptography:** RSA key generation.
- **Uvicorn:** ASGI development server.
- **uv:** Python project and dependency management.
- **Pydantic:** Request argument validation.

## Project Structure

```text
banking-agent-lab/
├── keys/
│   ├── private.pem
│   └── public.pem
├── main.py
├── generate_keys.py
├── pyproject.toml
├── uv.lock
└── README.md
```

- `main.py`: FastAPI application, JWT validation, RBAC rules, mock data, agent registry, tool functions, and API endpoints.
- `generate_keys.py`: Generates the RSA private and public keys.
- `keys/private.pem`: Used to sign demo JWTs.
- `keys/public.pem`: Used to verify JWT signatures.
- `pyproject.toml`: Project metadata and dependencies.
- `uv.lock`: Locked dependency versions, if generated by `uv`.

## Prerequisites

Install Python 3.10 or a compatible supported version, plus [`uv`](https://docs.astral.sh/uv/).

## Setup and Installation

### 1. Create the project

If starting from scratch:

```bash
uv init banking-agent-lab
cd banking-agent-lab
uv add fastapi uvicorn pyjwt cryptography
```

If you already have this project, run commands from its existing directory.

### 2. Generate RSA keys

Create the keys directory and generate the keys:

```bash
mkdir -p keys
uv run python generate_keys.py
```

Run this step once for the local demo. The generated files are used by the application to sign and verify JWTs.

**Never commit private keys or production secrets to source control.**

## Run the Application

Start the FastAPI development server:

```bash
uv run uvicorn main:app --reload
```

The API will be available at:

- Base URL: `http://localhost:8000`
- Interactive API documentation: `http://localhost:8000/docs`

Check that the application is running:

```bash
curl http://localhost:8000/
```

Expected response:

```json
{
  "status": "ok",
  "message": "Banking Agent API is running"
}
```

## Demo Users and Permissions

The application defines two demo users.

| Username | Role | Intended access |
|---|---|---|
| `alice_support` | `customer_support` | Read customer details |
| `bob_operator` | `transaction_operator` | Read customer details, read balances, update demo balances |

The demo token endpoint issues a JWT for a predefined user.

### Obtain a customer support token

```bash
curl -X POST \
  "http://localhost:8000/demo/token?username=alice_support"
```

Copy the returned `access_token` and set it in your terminal:

```bash
export TOKEN="paste_access_token_here"
```

### Obtain a transaction operator token

```bash
curl -X POST \
  "http://localhost:8000/demo/token?username=bob_operator"
```

Set the returned token in `TOKEN` before running the transaction operator tests.

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/` | Health check |
| `POST` | `/demo/token` | Issue a demo JWT for a predefined user |
| `POST` | `/agents/{agent_name}/tools/{tool_name}` | Invoke an agent tool |
 
### Available agent tools

| Agent | Tool | Required permission |
|---|---|---|
| `customer-greeting` | `read_customer_details` | `customer.read` |
| `transaction` | `read_customer_details` | `customer.read` |
| `transaction` | `read_balance` | `balance.read` |
| `transaction` | `update_balance` | `balance.update` |

## Testing the Application

All tool calls require a valid JWT in the `Authorization` header.

### Test 1: Read customer details

Use a valid token, such as the `alice_support` token:

```bash
curl -X POST \
  "http://localhost:8000/agents/customer-greeting/tools/read_customer_details" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"customer_id":"C1001"}'
```

Expected: `200 OK`, with the customer's details.

Example customer records:

- `C1001`: Alice Smith, Savings.
- `C1002`: Bob Jones, Checking.

### Test 2: Customer support cannot update balances

With the `alice_support` token:

```bash
curl -X POST \
  "http://localhost:8000/agents/transaction/tools/update_balance" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"customer_id":"C1001","amount":100}'
```

Expected: `403 Forbidden`, because the user lacks the `balance.update` permission.

### Test 3: Transaction operator can read balances

Set `TOKEN` to the `bob_operator` token, then run:

```bash
curl -X POST \
  "http://localhost:8000/agents/transaction/tools/read_balance" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"customer_id":"C1001"}'
```

Expected: `200 OK`, returning the current mock balance in CAD.

### Test 4: Transaction operator can update a demo balance

With the `bob_operator` token:

```bash
curl -X POST \
  "http://localhost:8000/agents/transaction/tools/update_balance" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"customer_id":"C1001","amount":100}'
```

Expected: `200 OK`, with the updated balance.

For example, a balance of CAD 1,500 becomes CAD 1,600 after adding CAD 100.

The change is stored only in the application's in-memory dictionary. Restarting the application resets the balances.

### Test 5: Customer Greeting Agent cannot read balances

Even with the transaction operator token, try:

```bash
curl -X POST \
  "http://localhost:8000/agents/customer-greeting/tools/read_balance" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"customer_id":"C1001"}'
```

Expected: `403 Forbidden`, because `read_balance` is not in the Customer Greeting Agent's tool allowlist.

This demonstrates that user permissions and agent permissions are separate checks.

## Authorization Flow

When a client calls an agent tool, the request follows this sequence:

1. **Extract the JWT:** FastAPI reads the bearer token from the HTTP Authorization header.
2. **Authenticate the caller:** `Depends(get_current_user)` invokes the JWT validation function before the endpoint handler runs.
3. **Check the agent allowlist:** The harness verifies that the requested tool is registered for the selected agent.
4. **Check RBAC:** The harness checks whether the authenticated user's roles grant the permission required by the tool.
5. **Validate arguments:** Pydantic validates the tool's input fields and constraints.
6. **Execute the tool:** The Python function runs only after the applicable checks succeed.

Typical outcomes:

| Scenario | Result |
|---|---|
| Missing, invalid, or expired token | `401 Unauthorized` |
| Valid token, but insufficient permission | `403 Forbidden` |
| Tool not allowed for the selected agent | `403 Forbidden` |
| Unknown customer ID | `404 Not Found` |
| Invalid amount | `400 Bad Request` or request validation error |
| Valid token and all checks pass | `200 OK` |

## Security Considerations

This project illustrates core security concepts but intentionally simplifies several production requirements.

- **Demo token issuance:** `/demo/token` is not a real login flow. Users and roles are hardcoded. Production roles must be derived from a trusted identity provider, not caller-supplied claims.
- **Key management:** Keep private signing keys protected. Production systems should use secure key management and appropriate rotation procedures.
- **JWT validation:** Production deployments should validate tokens according to the identity provider's configuration and key-discovery mechanism.
- **Defense in depth:** The harness checks tool access and user permissions. Critical transaction services should independently enforce authorization at their own API or service boundary.
- **Account-level authorization:** A role alone does not establish access to every customer's account. Resource ownership and account-specific permissions must also be checked.
- **Financial safeguards:** Real transactions require durable storage, atomic updates, transaction limits, audit trails, idempotency, fraud controls, and any required approval workflows.
- **Agent identity:** This demo uses the calling user's JWT and does not implement a separate agent workload identity or OAuth token exchange.
- **Production readiness:** The development server, local keys, in-memory data, and demo token issuer must not be treated as a production security architecture.

## Future Enhancements

Possible extensions to this lab include:

- Integrate an identity provider such as Microsoft Entra ID.
- Implement OAuth 2.0 token exchange for agent-to-service calls.
- Introduce a separate workload identity for each agent.
- Add resource-level authorization for customer accounts.
- Add audit logging and structured security events.
- Add unit and integration tests for authentication and authorization.
- Add human approval for sensitive transaction tools.
- Replace mock dictionaries with a database-backed service.
- Introduce an API gateway and centralized policy enforcement.

## Learning Outcomes

After completing this lab, you should be able to explain:

- How JWT authentication works in a FastAPI application.
- How FastAPI dependencies enforce authentication before endpoint execution.
- How RBAC maps user roles to permissions.
- Why an agent tool allowlist is distinct from user authorization.
- How an agent harness controls tool invocation.
- Why production systems need authorization checks beyond the agent layer.
