
from olibo import create_app

app = create_app()

@app.route('/', methods=['GET'])
def index():
    return "Welcome to Olibo API"

@app.route("/test")
def test():
    return "API is running"

app.run(host='127.0.0.1',debug=True,port=8000)