from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(
    __name__,
    template_folder=".",
    static_folder="css",
    static_url_path="/css"
)

app.secret_key = "travel-agent-secret"

# Demo accounts for Release 0
accounts = {
    "traveler": "travel123"
}


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/booking')
def booking():
    return redirect("http://127.0.0.1:5002/booking")

@app.route('/itinerary')
def itinerary():
    return redirect("http://127.0.0.1:5002/itinerary")




@app.route('/login', methods=['GET', 'POST'])
def login():

    error = None

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username in accounts and accounts[username] == password:
            session['username'] = username
            return redirect(url_for('welcome'))

        error = "Invalid username or password."

    return render_template(
        'login.html',
        error=error
    )


@app.route('/register', methods=['GET', 'POST'])
def register():

    message = None

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username in accounts:
            message = "Username already exists."
        else:
            accounts[username] = password
            return redirect(url_for('login'))

    return render_template(
        'register.html',
        message=message
    )


@app.route('/welcome')
def welcome():

    if 'username' not in session:
        return redirect(url_for('login'))

    return render_template(
        'welcome.html',
        username=session['username']
    )


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(
        host="0.0.0.0",
        port=5003,
        debug=True
    )