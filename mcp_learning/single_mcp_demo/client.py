import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


server_params = StdioServerParameters(
    command="python",
    args=["server.py"]
)


async def main():

    async with stdio_client(server_params) as (read, write):

        async with ClientSession(read, write) as session:

            # Initialize connection
            await session.initialize()

            # Discover tools
            tools = await session.list_tools()

            print("Available tools:")

            for tool in tools.tools:
                print(tool.name)
                print(tool.description)

            # Call a tool
            result = await session.call_tool(
                "add_numbers",
                {
                    "a": 10,
                    "b": 20
                }
            )

            print("Result:")
            print(result)


if __name__ == "__main__":
    asyncio.run(main())