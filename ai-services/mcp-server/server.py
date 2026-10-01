try:
    from mcp.server.mcpserver import MCPServer
except ImportError:
    from mcp.server.fastmcp import FastMCP as MCPServer

#importing al the required functions which we can mamke as a tool for the MCP server to use them.
from tools import (
    total_activity_count as total_activity_count_tool,
    total_activities_count_a_day as total_activities_count_a_day_tool,
    get_trip_activities_desc as get_trip_activities_desc_tool,
    get_trip_activities_for_day_desc as get_trip_activities_for_day_desc_tool,
    get_activity_start_times as get_activity_start_times_tool,
    get_travel_requirements as get_travel_requirements_tool
    )


#naming the MCP server:
mcp = MCPServer("Travel Planner MCP Server")

# list of all the avalable tools.
AVAILABLE_TOOLS = [
    "total_activity_count",
    "total_activities_count_a_day",
    "get_trip_activities_desc",
    "get_trip_activities_for_day_desc",
    "get_activity_start_times",
    "get_travel_requirements"
]

# making MCP tools:
@mcp.tool()
def total_activity_count(itinerary_id):
    return total_activity_count_tool(itinerary_id)


@mcp.tool()
def total_activities_count_a_day(itinerary_id, day_no):
    return total_activities_count_a_day_tool(itinerary_id, day_no)

@mcp.tool()
def get_trip_activities_desc(itinerary_id):
    return get_trip_activities_desc_tool(itinerary_id)

@mcp.tool()
def get_trip_activities_for_day_desc(itinerary_id , day_no):
    return get_trip_activities_for_day_desc_tool(itinerary_id , day_no)

@mcp.tool()
def get_activity_start_times(itinerary_id):
    return get_activity_start_times_tool(itinerary_id)

@mcp.tool()
def get_travel_requirements(itinerary_id):
    return get_travel_requirements_tool(itinerary_id)

if __name__ == "__main__":
    print("Available tools:")
    for tool in AVAILABLE_TOOLS:
        print(f"- {tool}")
    mcp.run()
