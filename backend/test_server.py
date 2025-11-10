from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return 'IT WORKS!'

if __name__ == '__main__':
    print("Starting test server on port 5001...")
    app.run(host='0.0.0.0', port=5001, debug=True)