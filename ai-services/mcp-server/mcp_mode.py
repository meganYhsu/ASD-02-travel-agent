import json
import sys

from tools import (
    get_accessibility_needs,
    get_activity_start_times,
    get_travel_requirements,
    get_traveler_interests,
    get_traveler_profile,
    get_trip_activities_desc,
    get_trip_activities_for_day_desc,
    total_activities_count_a_day,
    total_activity_count,
)


MCP_TOOLS = {
    "total_activity_count": total_activity_count,
    "total_activities_count_a_day": total_activities_count_a_day,
    "get_trip_activities_desc": get_trip_activities_desc,
    "get_trip_activities_for_day_desc": get_trip_activities_for_day_desc,
    "get_activity_start_times": get_activity_start_times,
    "get_travel_requirements": get_travel_requirements,
    # student 1 - Traveler Preferences
    "get_traveler_profile": get_traveler_profile,
    "get_traveler_interests": get_traveler_interests,
    "get_accessibility_needs": get_accessibility_needs,
}


def run_mcp_tool(tool_name, **arguments):
    tool = MCP_TOOLS.get(tool_name)

    if tool is None:
        available_tools = ", ".join(sorted(MCP_TOOLS))
        raise ValueError(f"Unknown MCP tool: {tool_name}. Available tools: {available_tools}")

    return tool(**arguments)


def list_mcp_tools():
    return sorted(MCP_TOOLS)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 mcp_mode.py <tool_name> '{\"arg\": \"value\"}'")
        print("Available tools:")
        for tool_name in list_mcp_tools():
            print(f"- {tool_name}")
        return

    tool_name = sys.argv[1]
    arguments = {}

    if len(sys.argv) >= 3:
        arguments = json.loads(sys.argv[2])

    result = run_mcp_tool(tool_name, **arguments)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
