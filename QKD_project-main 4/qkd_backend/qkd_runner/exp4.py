import random
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
import os
from qiskit.visualization import circuit_drawer
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def xor_encrypt_decrypt(message_bytes, key_bits):
    msg_bits = []
    for byte in message_bytes:
        for i in range(8):
            msg_bits.append((byte >> (7-i)) & 1)
    if len(key_bits) < len(msg_bits):
        key = (key_bits * ((len(msg_bits)//len(key_bits))+1))[:len(msg_bits)]
    else:
        key = key_bits[:len(msg_bits)]
    cipher_bits = [m ^ k for m, k in zip(msg_bits, key)]
    cipher_bytes = bytearray()
    for i in range(0, len(cipher_bits), 8):
        byte = 0
        for j in range(8):
            if i+j < len(cipher_bits):
                byte = (byte << 1) | cipher_bits[i+j]
            else:
                byte = (byte << 1)
        cipher_bytes.append(byte)
    return bytes(cipher_bytes)

def run_exp4(message=None, n=20):
    # Alice prepares random bits and bases
    alice_bits = [random.randint(0, 1) for _ in range(n)]
    alice_bases = [random.randint(0, 1) for _ in range(n)]  # 0 = Z-basis, 1 = X-basis

    # Eve measures alternate bits (0, 2, 4, ...)
    eve_bases = [random.randint(0, 1) if i % 2 == 0 else None for i in range(n)]

    # Bob chooses random bases
    bob_bases = [random.randint(0, 1) for _ in range(n)]

    # Quantum circuit
    qc = QuantumCircuit(n, n)
    diagram_path = "static/circuit_exp4.png"
    fig = circuit_drawer(qc, output='mpl')
    fig.savefig(diagram_path)
    plt.close(fig)

    # Step 1: Alice encodes bits
    for i in range(n):
        if alice_bits[i] == 1:
            qc.x(i)
        if alice_bases[i] == 1:
            qc.h(i)

    # Step 2: Eve intercepts alternate bits (passive: just measures, doesn't resend)
    for i in range(n):
        if eve_bases[i] is not None:  
            if eve_bases[i] == 1:
                qc.h(i)
            qc.measure(i, i)
            qc.reset(i)
            if random.randint(0, 1) == 1:
                qc.x(i)
            if alice_bases[i] == 1:
                qc.h(i)

    # Step 3: Bob measures
    for i in range(n):
        if bob_bases[i] == 1:
            qc.h(i)
        qc.measure(i, i)

    # Run the circuit once
    sim = AerSimulator()
    result = sim.run(qc, shots=1024).result()
    bob_results = list(result.get_counts().keys())[0]  
    bob_bits = [int(b) for b in bob_results[::-1]]

    # Step 4: Find matching bases and generate sifted key if QBER ≤ 11%
    matching_indices = []
    sifted_alice = []
    sifted_bob = []

    for i in range(n):
        if alice_bases[i] == bob_bases[i]:
            matching_indices.append(i)
            sifted_alice.append(alice_bits[i])
            sifted_bob.append(bob_bits[i])

    # Step 5: QBER calculation
    errors = sum(1 for a, b in zip(sifted_alice, sifted_bob) if a != b)
    qber = (errors / len(sifted_alice)) * 100 if len(sifted_alice) > 0 else 0

    SECURITY_THRESHOLD = 11

    # Message encryption/decryption only if QBER is below threshold
    if message is not None and sifted_alice and qber <= SECURITY_THRESHOLD:
        message_bytes = message.encode('utf-8')
        encrypted_bytes = xor_encrypt_decrypt(message_bytes, sifted_alice)
        decrypted_bytes = xor_encrypt_decrypt(encrypted_bytes, sifted_bob)
        try:
            decrypted_message = decrypted_bytes.decode('utf-8')
        except Exception:
            decrypted_message = "<decryption failed>"
        encrypted_hex = encrypted_bytes.hex()
    else:
        encrypted_hex = ""
        decrypted_message = ""

    counts = result.get_counts()
    key = list(counts.keys())[0]
    emeas = list(key)
    ebits = [int(x) for x in emeas][::-1]

    counts2 = result.get_counts()
    key2 = list(counts2.keys())[0]
    bmeas = list(key2)
    bbits = [int(x) for x in bmeas][::-1]

    return {
        "Sender_bits": alice_bits,
        "Sender_bases": alice_bases,
        "Receiver_bases": bob_bases,
        "Receiver_bits": bbits,
        "agoodbits": sifted_alice,
        "bgoodbits": sifted_bob,
        "qber": qber,
        "fidelity": 100 - qber,
        "loss": qber,
        "circuit_diagram_url": "/static/circuit_exp4.png",
        "counts_eve": counts,
        "counts_bob": counts2
    }
