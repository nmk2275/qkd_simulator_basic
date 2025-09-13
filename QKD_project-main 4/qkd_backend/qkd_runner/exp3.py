# qkd_backend/qkd_runner/exp3.py
# BB84 with Eve intercept-resend, executed on IBM Quantum backend using SamplerV2.

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
import os
from qiskit.visualization import circuit_drawer
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


# Login: make sure you've done `qiskit-ibm-runtime login --token YOUR_API_KEY`
service = QiskitRuntimeService()
backend = service.backend("ibm_brisbane")
print(backend.name)

def run_exp3(message=None, bit_num=20, shots=1024, rng_seed=None):
    rng = np.random.default_rng(rng_seed)

    # Step 1: Sender's random bits and bases
    abits = np.round(rng.random(bit_num))
    abase = np.round(rng.random(bit_num))

    # Step 2: Eve's random measurement bases
    ebase = np.round(rng.random(bit_num))

    # Step 3: Receiver's random measurement bases
    bbase = np.round(rng.random(bit_num))

    # --- Sender prepares and sends qubits ---
    qr = QuantumRegister(bit_num, "q")
    cr = ClassicalRegister(bit_num, "c")
    qc = QuantumCircuit(qr, cr)
    for n in range(bit_num):
        if abits[n] == 0:
            if abase[n] == 1:
                qc.h(n)
        if abits[n] == 1:
            if abase[n] == 0:
                qc.x(n)
            if abase[n] == 1:
                qc.x(n)
                qc.h(n)

    # --- Eve intercepts and measures ---
    for m in range(bit_num):
        if ebase[m] == 1:
            qc.h(m)
        qc.measure(qr[m], cr[m])

    # Transpile for backend
    target = backend.target
    pm = generate_preset_pass_manager(target=target, optimization_level=3)
    qc_isa = pm.run(qc)

    # Eve's measurement using SamplerV2
    sampler = Sampler(mode=backend)
    job = sampler.run([qc_isa], shots=1024)
    counts = job.result()[0].data.c.get_counts()
    key = list(counts.keys())[0]
    emeas = list(key)
    ebits = [int(x) for x in emeas][::-1]

    # --- Eve resends to Receiver ---
    qr2 = QuantumRegister(bit_num, "q")
    cr2 = ClassicalRegister(bit_num, "c")
    qc2 = QuantumCircuit(qr2, cr2)
    for n in range(bit_num):
        if ebits[n] == 0:
            if ebase[n] == 1:
                qc2.h(n)
        if ebits[n] == 1:
            if ebase[n] == 0:
                qc2.x(n)
            if ebase[n] == 1:
                qc2.x(n)
                qc2.h(n)

    # Receiver's measurement
    for m in range(bit_num):
        if bbase[m] == 1:
            qc2.h(m)
        qc2.measure(qr2[m], cr2[m])

    qc2_isa = pm.run(qc2)
    job2 = sampler.run([qc2_isa], shots=1024)
    counts2 = job2.result()[0].data.c.get_counts()
    key2 = list(counts2.keys())[0]
    bmeas = list(key2)
    bbits = [int(x) for x in bmeas][::-1]
    

    diagram_path = "static/circuit_exp3.png"
    fig = circuit_drawer(qc2_isa, output='mpl')
    fig.savefig(diagram_path)
    plt.close(fig)

    # Sifting: keep only positions where Sender & Receiver used same basis
    agoodbits = []
    bgoodbits = []
    match_count = 0
    for i in range(bit_num):
        if abase[i] == bbase[i]:
            agoodbits.append(int(abits[i]))
            bgoodbits.append(int(bbits[i]))
            if int(abits[i]) == int(bbits[i]):
                match_count += 1

    # After sifting and before returning the result:
    fidelity = match_count / len(agoodbits) if agoodbits else 0
    loss = 1 - fidelity if agoodbits else 1

    # Define abort reason first
    abort_reason = None
    if loss > 0.15:
        abort_reason = "Error too high! Key generation aborted."

    return {
        "Sender_bits": abits.tolist(),
        "Sender_bases": abase.tolist(),
        "Receiver_bases": bbase.tolist(),
        "Receiver_bits": bbits,
        "agoodbits": agoodbits,  # Return the non-empty list
        "bgoodbits": bgoodbits,  # Return the non-empty list
        "fidelity": fidelity,
        "loss": loss,
        "circuit_diagram_url": "/static/circuit_exp3.png",
        "counts_eve": counts,
        "counts_bob": counts2,
        "abort_reason": abort_reason
    }

def run(message=None):
    return run_exp3(message)
