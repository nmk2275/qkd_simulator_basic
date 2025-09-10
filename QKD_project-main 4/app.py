from flask import Flask, jsonify, render_template, request
from qkd_backend.qkd_runner import exp1, exp2, exp3, exp4

app = Flask(__name__, static_folder="static")
last_exp1_result = {}
last_exp2_result = {}

# ---- Serve index.html at root ----
@app.route("/")
def home():
    return render_template("index.html")  # Looks in templates/index.html

@app.route("/keyrate")
def keyrate():
    return render_template("keyrate.html")

@app.route("/KeyrateVsDistance")
def KeyrateVsDistance():
    return render_template("KeyrateVsDistance.html")

# ---- Experiment routes ----
@app.route("/run/exp1", methods=["POST"])
def exp1_route():
    global last_exp1_result
    data = request.get_json()
    message = data.get("message") if data else None
    if message is None:
        # Run experiment, store result (no message yet)
        result = exp1.run_exp1()
        last_exp1_result = result
        return jsonify(result)
    else:
        # Use previous key to encrypt/decrypt
        if not last_exp1_result:
            return jsonify({"error": "Run the experiment first!"}), 400
        result = exp1.encrypt_with_existing_key(last_exp1_result, message)
        return jsonify(result)

@app.route("/run/exp2", methods=["POST"])
def exp2_route():
    global last_exp2_result
    data = request.get_json()
    message = data.get("message") if data else None
    if message is None:
        result = exp2.run_exp2()
        last_exp2_result = result
        return jsonify(result)
    else:
        if not last_exp2_result:
            return jsonify({"error": "Run the experiment first!"}), 400
        result = exp2.encrypt_with_existing_key(last_exp2_result, message)
        return jsonify(result)

@app.route("/run/exp3", methods=["POST"])
def exp3_route():
    result = exp3.run_exp3()
    return jsonify(result)

@app.route("/run/exp4", methods=["POST"])
def exp4_route():
    result = exp4.run_exp4()
    return jsonify(result)
@app.route("/run/<exp>", methods=["POST"])
def run_exp(exp):
    # ... your existing code to run exp1, exp2, exp3, exp4 ...
    # After getting the result:
    global last_analysis
    last_analysis = result
    return jsonify(result)

@app.route("/analysis")
def analysis():
    return render_template("analysis.html")
@app.route("/shors")
def shors():
    return render_template("shors.html")


@app.route("/get_last_analysis")
def get_last_analysis():
    global last_analysis
    return jsonify(last_analysis)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)