import asyncio
import json
from contextlib import AsyncExitStack

from openai import OpenAI

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# ---------------------------------------------------------
# OpenAI client
# ---------------------------------------------------------

openai_client = OpenAI()


# ---------------------------------------------------------
# MCP server configurations
# ---------------------------------------------------------

weather_params = StdioServerParameters(
    command="uv",
    args=["run", "weather_server.py"],
)

customer_params = StdioServerParameters(
    command="uv",
    args=["run", "customer_server.py"],
)


# ---------------------------------------------------------
# Convert MCP tool definition -> OpenAI tool definition
# ---------------------------------------------------------

def convert_mcp_tool_to_openai(tool):

    return {
        "type": "function",
        "name": tool.name,
        "description": tool.description or "",
        "parameters": tool.inputSchema,
    }


# ---------------------------------------------------------
# Main agent
# ---------------------------------------------------------

async def main():

    # AsyncExitStack lets us keep multiple independent
    # MCP connections alive at the same time.
    async with AsyncExitStack() as stack:

        # =================================================
        # 1. Connect to Weather MCP server
        # =================================================

        weather_read, weather_write = await stack.enter_async_context(
            stdio_client(weather_params)
        )

        weather_session = await stack.enter_async_context(
            ClientSession(weather_read, weather_write)
        )

        await weather_session.initialize()


        # =================================================
        # 2. Connect to Customer MCP server
        # =================================================

        customer_read, customer_write = await stack.enter_async_context(
            stdio_client(customer_params)
        )

        customer_session = await stack.enter_async_context(
            ClientSession(customer_read, customer_write)
        )

        await customer_session.initialize()


        # =================================================
        # 3. Discover tools from both MCP servers
        # =================================================

        weather_tools = await weather_session.list_tools()

        customer_tools = await customer_session.list_tools()


        # =================================================
        # 4. Build:
        #
        #       tool name -> MCP session
        #
        # This tells our agent which MCP client should
        # execute a tool after the LLM selects it.
        # =================================================

        tool_to_session = {}

        all_openai_tools = []


        # ---- Weather tools ----

        for tool in weather_tools.tools:

            print("Discovered Weather tool:", tool.name)

            tool_to_session[tool.name] = weather_session

            all_openai_tools.append(
                convert_mcp_tool_to_openai(tool)
            )


        # ---- Customer tools ----

        for tool in customer_tools.tools:

            print("Discovered Customer tool:", tool.name)

            tool_to_session[tool.name] = customer_session

            all_openai_tools.append(
                convert_mcp_tool_to_openai(tool)
            )


        # =================================================
        # 5. Show everything discovered
        # =================================================

        print("\nAvailable tools:")
        print("----------------")

        for tool in all_openai_tools:

            print(
                f"- {tool['name']}: "
                f"{tool['description']}"
            )


        # =================================================
        # 6. User question
        # =================================================

        user_question = """
        What is the weather in Toronto?
        """

        print("\nUser:")
        print(user_question)


        # =================================================
        # 7. Send question + tools to OpenAI
        # =================================================

        response = openai_client.responses.create(

            model="gpt-5",

            input=user_question,

            tools=all_openai_tools
        )


        # =================================================
        # 8. Inspect what the LLM decided
        # =================================================

        print("\nLLM output:")
        print("-----------")

        for item in response.output:

            print(item)


        # =================================================
        # 9. Find function/tool calls
        # =================================================

        tool_outputs = []


        for item in response.output:

            if item.type != "function_call":
                continue


            # ---------------------------------------------
            # LLM selected this tool
            # ---------------------------------------------

            tool_name = item.name


            # ---------------------------------------------
            # Arguments generated by the LLM
            # ---------------------------------------------

            arguments = json.loads(
                item.arguments
            )


            print("\nLLM selected tool:")
            print(tool_name)

            print("\nArguments:")
            print(arguments)


            # =================================================
            # 10. Find which MCP client owns this tool
            # =================================================

            mcp_session = tool_to_session.get(tool_name)


            if mcp_session is None:

                raise RuntimeError(
                    f"No MCP server found for tool: {tool_name}"
                )


            # =================================================
            # 11. Execute the tool through MCP
            # =================================================

            print("\nCalling MCP tool...")

            result = await mcp_session.call_tool(
                tool_name,
                arguments
            )


            print("\nMCP result:")
            print(result)


            # =================================================
            # 12. Convert MCP result into text
            #     to send back to OpenAI
            # =================================================

            result_text = ""

            for content in result.content:

                if hasattr(content, "text"):

                    result_text += content.text


            # =================================================
            # 13. Send tool result back to OpenAI
            # =================================================

            tool_outputs.append({

                "type": "function_call_output",

                "call_id": item.call_id,

                "output": result_text
            })


        # =================================================
        # 14. Ask OpenAI for final answer
        # =================================================

        final_response = openai_client.responses.create(

            model="gpt-5",

            input=response.output + tool_outputs,

            tools=all_openai_tools
        )


        # =================================================
        # 15. Final answer
        # =================================================

        print("\nFinal answer:")
        print("-------------")

        print(final_response.output_text)


# ---------------------------------------------------------
# Run agent
# ---------------------------------------------------------

if __name__ == "__main__":

    asyncio.run(main())