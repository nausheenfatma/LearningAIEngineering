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

1. Verifies that the requested agent