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
    get_travel_requirements as get_travel_requirements_tool,
    get_traveler_profile as get_traveler_profile_tool,
    get_traveler_interests as get_traveler_interests_tool,
    get_accessibility_needs as get_accessibility_needs_tool
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
    "get_travel_requirements",
    "get_traveler_profile",
    "get_traveler_interests",
    "get_accessibility_needs"
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

# student 1 - Traveler Preferences tools:
@mcp.tool()
def get_traveler_profile(traveler_id: int):
    return get_traveler_profile_tool(traveler_id)

@mcp.tool()
def get_traveler_interests(traveler_id: int):
    return get_traveler_interests_tool(traveler_id)

@mcp.tool()
def get_accessibility_needs(traveler_id: int):
    return get_accessibility_needs_tool(traveler_id)

if __name__ == "__main__":
    print("Available tools:")
    for tool in AVAILABLE_TOOLS:
        print(f"- {tool}")
    mcp.run()
