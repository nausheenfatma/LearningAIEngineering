from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Weather Server")


@mcp.tool()
def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    return f"The weather in {city} is 20°C and sunny."


if __name__ == "__main__":
    mcp.run()