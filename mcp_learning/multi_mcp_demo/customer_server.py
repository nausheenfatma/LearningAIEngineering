from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Customer Server")


@mcp.tool()
def get_customer(customer_id: str) -> str:
    """Get customer information using a customer ID."""
    return f"Customer {customer_id}: Nausheen, Toronto"


if __name__ == "__main__":
    mcp.run()