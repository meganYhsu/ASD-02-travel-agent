from unittest import result

from flask import Flask, render_template, request, redirect, url_for
from markupsafe import escape
import requests
import os

app = Flask(__name__)

BACKEND_URL = os.getenv("BACKEND_URL") or "http://127.0.0.1:5001"

print("BACKEND_URL =", BACKEND_URL)


@app.route('/itinerary')
def itinerary():
    response = requests.get(f"{BACKEND_URL}/itineraries",timeout=15)
    itinerary_list = response.json()

    return render_template(
        'itinerary.html',
        itineraries=itinerary_list
    )


@app.route('/itinerary/add', methods=['POST'])
def add_itinerary():
    data = {
        'trip_id': request.form['trip_id'],
        'date': request.form['date'],
        'time': request.form['time'],
        'activity': request.form['activity'],
        'location': request.form['location'],
        'notes': request.form['notes']
    }

    requests.post(
        f"{BACKEND_URL}/itineraries",
        json=data,
        timeout=15
    )

    return redirect(url_for('itinerary'))


@app.route('/itinerary/update/<int:itinerary_id>', methods=['POST'])
def update_itinerary(itinerary_id):
    data = {
        'trip_id': request.form['trip_id'],
        'date': request.form['date'],
        'time': request.form['time'],
        'activity': request.form['activity'],
        'location': request.form['location'],
        'notes': request.form['notes']
    }

    requests.put(
        f"{BACKEND_URL}/itineraries/{itinerary_id}",
        json=data,
        timeout=15
    )


    return redirect(url_for('itinerary'))


@app.route('/itinerary/delete/<int:itinerary_id>', methods=['POST'])
def delete_itinerary(itinerary_id):

    requests.delete(
        f"{BACKEND_URL}/itineraries/{itinerary_id}", timeout=15
    )

    return redirect(url_for('itinerary'))



@app.route('/booking')
def booking():
    #booking_response = requests.get(f"{BACKEND_URL}/bookings")
    booking_response = requests.get(f"{BACKEND_URL}/bookings",timeout=15)
    bookings = booking_response.json()

    #provider_response = requests.get(f"{BACKEND_URL}/provider")
    provider_response = requests.get(f"{BACKEND_URL}/provider",timeout=15)
    providers = provider_response.json()

    #itinerary_response = requests.get(f"{BACKEND_URL}/itineraries")
    itinerary_response = requests.get(f"{BACKEND_URL}/itineraries",timeout=15)
    itineraries = itinerary_response.json()

    #booking_item_response = requests.get( f"{BACKEND_URL}/booking_items")
    booking_item_response = requests.get( f"{BACKEND_URL}/booking_items",timeout=15)
    booking_items = booking_item_response.json()

    provider_names = {
    provider['provider_id']: provider['name']
    for provider in providers
    }

    itinerary_activities = {
    itinerary['itinerary_id']: itinerary['activity']
    for itinerary in itineraries
    }

    booking_activities = {}

    for item in booking_items:
        booking_id = item['booking_id']
        itinerary_id = item['itinerary_id']

        booking_activities[booking_id] = (
            itinerary_activities.get (
                itinerary_id,
                'Unknown Activity'
            )
        )

    return render_template(
        'booking.html',
        bookings=bookings,
        providers=providers,
        itineraries=itineraries,
        provider_names=provider_names,
        booking_activities=booking_activities
    )



@app.route('/booking/add', methods=['POST'])
def add_booking():
    data = {
        'trip_id': int(request.form['trip_id']),
        'provider_id': int(request.form['provider_id']),
        'itinerary_id': int(request.form['itinerary_id']),
        'booking_date': request.form['booking_date'],
        'status': request.form['status'],
        'cost': float(request.form['cost']),
        'create_time': request.form['create_time'],
        'quantity': int(request.form['quantity'])
    }

    response = requests.post(
        f"{BACKEND_URL}/bookings/from-itinerary",
        json=data,
        timeout=15
    )

    print("ADD STATUS:", response.status_code)
    print("ADD RESPONSE:", response.text)

    return redirect(url_for('booking'))


@app.route('/booking/update/<int:booking_id>', methods=['POST'])
def update_booking(booking_id):
    data = {
        'trip_id': int(request.form['trip_id']),
        'provider_id': int(request.form['provider_id']),
        'booking_date': request.form['booking_date'],
        'status': request.form['status'],
        'cost': float(request.form['cost']),
        'create_time': request.form['create_time']
    }

    response = requests.put(
        f"{BACKEND_URL}/bookings/{booking_id}",
        json=data,
        timeout=15
    )

    print("UPDATE STATUS:", response.status_code)
    print("UPDATE RESPONSE:", response.text)

    return redirect(url_for('booking'))

@app.route('/booking/delete/<int:booking_id>', methods=['POST'])
def delete_booking(booking_id):

    response = requests.delete(
        f"{BACKEND_URL}/bookings/{booking_id}", timeout=15
    )

    print("DELETE STATUS:", response.status_code)
    print("DELETE RESPONSE:", response.text)

    return redirect(url_for('booking'))


#booking AI agent
@app.route('/booking/ai-match', methods=['POST'])
def ai_match_provider():
    itinerary_id = request.form.get('itinerary_id')

    if not itinerary_id:
        return """
            <div>
                <strong>Error:</strong> Please select an itinerary.
            </div>
        """, 400

    try:
        response = requests.post(
            f"{BACKEND_URL}/ai/match-provider",
            json={
                "itinerary_id": int(itinerary_id)
            },
            timeout=30
        )

        data = response.json()

    except requests.RequestException:
        return """
            <div>
                <strong>Error:</strong> AI service is unavailable.
            </div>
        """, 503

    if response.status_code == 422:
            return """
            <div>
            <h3>AI Booking Recommendation</h3>
            <p><strong>No suitable provider found.</strong></p>
            <p>
                The AI could not find a suitable provider for this itinerary
                from the currently available providers.
            </p>
            </div>
            """

    if response.status_code != 200:
        error_message = data.get(
            'error',
            'Unable to generate recommendation.'
        )

        return f"""
            <div>
                <strong>Error:</strong> {error_message}
            </div>
        """, response.status_code

    provider = data['recommended_provider']
    reason = data['reason']
    itinerary_id = data['itinerary']['itinerary_id']

    return f"""
    <div>
        <h3>AI Booking Recommendation</h3>

        <p>
            <strong>Recommended Provider:</strong>
            {provider['name']}
        </p>

        <p>
            <strong>Provider Type:</strong>
            {provider['type']}
        </p>

        <p>
            <strong>Reason:</strong>
            {reason}
        </p>

        <button
            type="button"
            onclick="useAIProvider(
                {itinerary_id},
                {provider['provider_id']}
            )"
        >
            Use This Provider
        </button>
    </div>
    """


# RAG integration
@app.route('/booking/rag', methods=['POST'])
def booking_rag():
    query = request.form.get('query', '').strip()

    if not query:
        return """
        <div>
            <strong>Error:</strong> Please enter a question.
        </div>
        """, 400

    try:
        response = requests.post(
            f"{BACKEND_URL}/rag/answer",
            json={
                "query": query
            },
            timeout=340
        )

        data = response.json()

    except requests.Timeout:
        return """
        <div>
            <strong>Error:</strong> RAG request timed out.
        </div>
        """, 504

    except (requests.RequestException, ValueError):
        return """
        <div>
            <strong>Error:</strong> RAG service is unavailable.
        </div>
        """, 503

    if response.status_code != 200:
        error_message = data.get(
            'error',
            'Unable to answer the question.'
        )

        return f"""
        <div>
            <strong>Error:</strong> {error_message}
        </div>
        """, response.status_code

    answer = data.get('answer', 'No answer returned.')
    confidence = data.get('confidence_category', 'Unknown')
    citations = data.get('citations', [])

    sources_html = ""

    if citations:
        sources_html = "<ul>"

        for citation in citations:
            source = (
                citation.get('chunk_id')
                or citation.get('id')
                or citation.get('source')
                or 'Unknown source'
            )

            sources_html += f"<li>{source}</li>"

        sources_html += "</ul>"
    else:
        sources_html = "<p>No sources returned.</p>"

    return f"""
    <div>
        <h3>RAG Answer</h3>

        <p>{answer}</p>

        <p>
            <strong>Confidence:</strong>
            {confidence}
        </p>

        <p><strong>Sources:</strong></p>
        {sources_html}
    </div>
    """


# MCP integration
@app.route('/booking/mcp', methods=['POST'])
def booking_mcp():
    action = request.form.get('action')
    itinerary_id = request.form.get('itinerary_id')

    if not itinerary_id:
        return """
        <div>
            <strong>Error:</strong> Please enter an itinerary ID.
        </div>
        """, 400

    tool_map = {
        'itinerary': 'get_trip_activities_desc',
        'schedule': 'get_activity_start_times',
        'requirements': 'get_travel_requirements'
    }

    tool_labels = {
        'itinerary': 'Trip Activities',
        'schedule': 'Activity Schedule',
        'requirements': 'Travel Requirements'
    }

    tool_name = tool_map.get(action)

    if not tool_name:
        return """
        <div>
            <strong>Error:</strong> Invalid MCP action.
        </div>
        """, 400

    try:
        response = requests.post(
            f"{BACKEND_URL}/mcp/tool",
            json={
                "tool_name": tool_name,
                "arguments": {
                    "itinerary_id": int(itinerary_id)
                }
            },
            timeout=30
        )

        data = response.json()

    except ValueError:
        return """
        <div>
            <strong>Error:</strong> Invalid itinerary ID or MCP response.
        </div>
        """, 400

    except requests.Timeout:
        return """
        <div>
            <strong>Error:</strong> MCP request timed out.
        </div>
        """, 504

    except requests.RequestException:
        return """
        <div>
            <strong>Error:</strong> MCP service is unavailable.
        </div>
        """, 503

    if response.status_code != 200:
        error_message = data.get(
            'error',
            'Unable to execute MCP tool.'
        )

        return f"""
        <div>
            <strong>Error:</strong> {error_message}
        </div>
        """, response.status_code

    result = data.get('result', data)

    tool_display_name = tool_labels.get(
        action,
        tool_name.replace('_', ' ').title()
    )

    if isinstance(result, dict):
        result_html = ""

        for key, value in result.items():
            label = key.replace('_', ' ').title()

            if isinstance(value, list):
                list_items = "".join(
                    f"<li>{item}</li>"
                    for item in value
                )

                result_html += f"""
                <div>
                    <strong>{label}:</strong>
                    <ol>
                        {list_items}
                    </ol>
                </div>
                """
            else:
                result_html += (
                    f"<p><strong>{label}:</strong> {value}</p>"
                )

    elif isinstance(result, list):
        list_items = "".join(
            f"<li>{item}</li>"
            for item in result
        )

        result_html = f"""
        <ol>
            {list_items}
        </ol>
        """

    else:
        result_html = f"<p>{result}</p>"

    return f"""
    <div>
        <h3>MCP Result</h3>

        <p>
            <strong>Tool:</strong>
            {tool_display_name}
        </p>

        {result_html}
    </div>
    """


# Multi-Agent Booking Review
@app.route('/booking/multi-agent', methods=['POST'])
def booking_multi_agent():
    
    booking_id_raw = request.form.get('booking_id', '').strip()
    
    booking_id = None
    
    if booking_id_raw:
        try:
            booking_id = int(booking_id_raw)
            if booking_id <= 0:
                return "<p>Please select a valid Booking ID.</p>", 400
        except ValueError:
            return "<p>Invalid Booking ID.</p>", 400

    user_request = request.form.get('user_request', '').strip()
    
    if not user_request:
        return "<p>Please enter a review request.</p>", 400

    try:
        response = requests.post(
            f"{BACKEND_URL}/multi-agent/workflow",
            json={
                "booking_id": booking_id,
                "user_request": user_request
            },
            timeout=800
        )

    except requests.Timeout:
        return "<p>Multi-Agent workflow timed out.</p>", 504

    except requests.RequestException as exc:
        app.logger.error("Backend connection failed: %s", exc)
        return "<p>Unable to connect to Backend API.</p>", 503

    try:
        data = response.json()

    except ValueError:
        app.logger.error(
            "Backend returned non-JSON response: HTTP %s",
            response.status_code
        )
        return (
            "<p>Backend returned an invalid response. "
            "Please check Backend logs.</p>",
            502
        )
    
    if response.status_code != 200:
        message = escape(
            str(data.get('error', 'Unable to run workflow.'))
        )
        return f"<p>Error: {message}</p>", response.status_code

    workflow_id = escape(str(data.get('workflow_id', '')))

    if not workflow_id:
        return "<p>Workflow ID is missing.</p>", 502

    planner = data.get('planner_result') or {}
    worker = data.get('worker_result') or {}
    reviewer = data.get('reviewer_result') or {}

    planner_status = escape(str(planner.get('status', 'unknown')))
    worker_status = escape(str(worker.get('status', 'unknown')))
    reviewer_status = escape(str(reviewer.get('status', 'unknown')))
    planner_error = escape(str(planner.get('error', '')))

    planner_text = escape(str(planner.get('plan', 'No plan returned.')))
    worker_text = escape(str(worker.get('output', 'No output returned.')))
    reviewer_text = escape(str(reviewer.get('review', 'No review returned.')))
    workflow_status = escape(str(data.get('status', 'unknown')))
    
    planner_error_html = (
        f'<p><strong>Error:</strong> {planner_error}</p>'
        if planner_error else ''
    )

    return f"""
    <div class="section-card">
        <h3>Multi-Agent Booking Review</h3>

        <p><strong>Workflow ID:</strong> {workflow_id}</p>
        <p><strong>Workflow Status:</strong> {workflow_status}</p>

        <h4>Planner Agent</h4>
        <p><strong>Status:</strong> {planner_status}</p>
        <p style="white-space:pre-wrap;">{planner_text}</p>
        {planner_error_html}
        
        <h4>Worker Agent</h4>
        <p><strong>Status:</strong> {worker_status}</p>
        <p style="white-space:pre-wrap;">{worker_text}</p>
        
        <h4>Reviewer Agent</h4>
        <p><strong>Status:</strong> {reviewer_status}</p>
        <p style="white-space:pre-wrap;">{reviewer_text}</p>

        <hr>

        <h4>Human Review</h4>

        <form hx-post="/booking/multi-agent/review"
              hx-target="#human-review-result"
              hx-swap="innerHTML">

            <input type="hidden"
                   name="workflow_id"
                   value="{workflow_id}">

            <fieldset class="human-review-decisions">
                <legend>Decision:</legend>
                <label>
                   <input
                       type="radio" 
                       name="decision"
                       value="Accept"
                       required>
                    Accept
                </label>
                
                <label>
                    <input
                        type="radio"
                        name="decision"
                        value="Partially Accept">
                    Partially Accept
                </label>
                
                <label>
                    <input
                        type="radio"
                        name="decision"
                        value="Reject">
                    Reject
                </label>
            </fieldset>

            <label>Reason:</label>
            <textarea name="reason"
                      minlength="20"
                      required
                      placeholder="Explain your decision (at least 20 characters)."></textarea>

            <label>Evidence (optional):</label>
            <textarea name="evidence"
                      placeholder="Supporting evidence"></textarea>

            <button type="submit">Submit Human Review</button>
        </form>

        <div id="human-review-result"></div>
    </div>
    """


# Submit Human Review Decision
@app.route('/booking/multi-agent/review', methods=['POST'])
def booking_multi_agent_review():

    workflow_id = request.form.get('workflow_id', '').strip()
    decision = request.form.get('decision', '').strip()
    reason = request.form.get('reason', '').strip()
    evidence = request.form.get('evidence', '').strip()

    if not workflow_id:
        return "<p>Workflow ID is required.</p>", 400

    if decision not in ['Accept', 'Partially Accept', 'Reject']:
        return "<p>Invalid decision.</p>", 400

    if len(reason) < 20:
        return "<p>Reason must contain at least 20 characters.</p>", 400

    try:
        response = requests.post(
            f"{BACKEND_URL}/multi-agent/workflows/{workflow_id}/review",
            json={
                "decision": decision,
                "reason": reason,
                "evidence": evidence
            },
            timeout=20
        )

    except requests.Timeout:
        return "<p>Human Review request timed out.</p>", 504

    except requests.RequestException as exc:
        app.logger.error("Human Review request failed: %s", exc)
        return "<p>Unable to connect to Backend API.</p>", 503

    try:
        data = response.json()

    except ValueError:
        app.logger.error(
            "Human Review returned non-JSON response: HTTP %s",
            response.status_code
        )
        return (
            "<p>Backend returned an invalid Human Review response.</p>",
            502
        )

   
    if response.status_code != 200:
        message = escape(
            str(data.get('error', 'Human Review submission failed.'))
        )
        return f"<p>Error: {message}</p>", response.status_code

    return f"""
    <div>
        <h4>Human Review Recorded</h4>
        <p><strong>Decision:</strong> {escape(decision)}</p>
        <p><strong>Reason:</strong> {escape(reason)}</p>
        <p>The review was successfully saved to the shared Multi-Agent Server.</p>
    </div>
    """


if __name__ == '__main__':
     # Required for communication between Docker containers.
    app.run(host='0.0.0.0', port=5002, debug=False) # noqa: S104