# BB84 protocol without Eve, executed on IBM Quantum backend using SamplerV2.

import numpy as np
from qiskit import QuantumCircuit
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
import os
import hashlib
from qiskit.visualization import circuit_drawer
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


service = QiskitRuntimeService()
backend = service.backend("ibm_brisbane")
print(backend.name)

def xor_encrypt_decrypt(message_bytes, key_bits):
    # message_bytes: bytes
    # key_bits: list of 0/1
    msg_bits = []
    for byte in message_bytes:
        for i in range(8):
            msg_bits.append((byte >> (7-i)) & 1)
    # Pad or trim key to message length
    if len(key_bits) < len(msg_bits):
        key = (key_bits * ((len(msg_bits)//len(key_bits))+1))[:len(msg_bits)]
    else:
        key = key_bits[:len(msg_bits)]
    # XOR
    cipher_bits = [m ^ k for m, k in zip(msg_bits, key)]
    # Convert bits back to bytes
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

def run_exp2(message=None, bit_num=20, shots=1024, rng_seed=None):
    rng = np.random.default_rng(rng_seed)

    # Step 1: Sender's random bits and bases
    abits = np.round(rng.random(bit_num))
    abase = np.round(rng.random(bit_num))

    # Step 2: Receiver's random measurement bases
    bbase = np.round(rng.random(bit_num))

    # Sender prepares and sends qubits
    qc = QuantumCircuit(bit_num, bit_num)
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

    # Receiver's measurement
    for m in range(bit_num):
        if bbase[m] == 1:
            qc.h(m)
        qc.measure(m, m)

    # Transpile for backend
    target = backend.target
    pm = generate_preset_pass_manager(target=target, optimization_level=3)
    qc_isa = pm.run(qc)
    diagram_path = "static/circuit_exp2.svg"
    import matplotlib.pyplot as plt
    os.makedirs("static", exist_ok=True)
    diagram_path = "static/circuit_exp2.png"
    fig = circuit_drawer(qc_isa, output='mpl')
    fig.savefig(diagram_path)
    plt.close(fig)

    # Run on IBM Quantum backend using SamplerV2
    sampler = Sampler(mode=backend)
    job = sampler.run([qc_isa], shots=1024)
    counts = job.result()[0].data.c.get_counts()
    key = list(counts.keys())[0]
    bmeas = list(key)
    bbits = [int(x) for x in bmeas][::-1]

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

    fidelity = match_count / len(agoodbits) if agoodbits else 0
    loss = 1 - fidelity if agoodbits else 1

    diagram_path = "static/circuit_exp2.png"
    fig = circuit_drawer(qc_isa, output='mpl')
    fig.savefig(diagram_path)
    plt.close(fig)
        # --- Error Correction (Simple Parity) ---
    block_size = 4  # adjust as needed
    corrected_bbits = []

    for i in range(0, len(agoodbits), block_size):
        a_block = agoodbits[i:i+block_size]
        b_block = bgoodbits[i:i+block_size]

        # Compute parity
        a_parity = sum(a_block) % 2
        b_parity = sum(b_block) % 2

        # If parity differs, flip last bit in Bob's block
        if a_parity != b_parity and len(b_block) > 0:
            b_block[-1] ^= 1  # flip last bit

        corrected_bbits.extend(b_block)

    # Display key after error correction
    error_corrected_key = ''.join(map(str, corrected_bbits))
    print("Key after Error Correction:", error_corrected_key)

    # --- Privacy Amplification ---
    secret_key = hashlib.sha256(error_corrected_key.encode()).hexdigest()
    secret_key = secret_key[:64]  # shorten for demonstration

    print("Final Secret Key:", secret_key)

    # --- Message encryption/decryption ---
    if message is None:
        message = "QKD demo"
    message_bytes = message.encode('utf-8')
    if agoodbits and len(agoodbits) >= 8:
        # Encrypt
        encrypted_bytes = xor_encrypt_decrypt(message_bytes, agoodbits)
        # Decrypt using Bob's key
        decrypted_bytes = xor_encrypt_decrypt(encrypted_bytes, bgoodbits)
        try:
            decrypted_message = decrypted_bytes.decode('utf-8')
        except Exception:
            decrypted_message = "<decryption failed>"
        encrypted_hex = encrypted_bytes.hex()
    else:
        encrypted_hex = ""
        decrypted_message = ""
    counts = job.result()[0].data.c.get_counts()
    key = list(counts.keys())[0]
    bmeas = list(key)
    bbits = [int(x) for x in bmeas][::-1]
    
    return {
        "Sender_bits": abits.tolist(),
        "Sender_bases": abase.tolist(),
        "Receiver_bases": bbase.tolist(),
        "Receiver_bits": bbits,
        "agoodbits": agoodbits,
        "bgoodbits": bgoodbits,
        "fidelity": fidelity,
        "loss": loss,
        "error_corrected_key": error_corrected_key,
        "final_secret_key": secret_key,
        "original_message": message,
        "encrypted_message_hex": encrypted_hex,
        "decrypted_message": decrypted_message,
        "circuit_diagram_url": "/static/circuit_exp2.png",
        "counts": counts # <-- add this line,
        
        
    }

def encrypt_with_existing_key(exp_result, message):
    # Use error-corrected key if available, else fallback to agoodbits
    corrected_bbits = exp_result.get("error_corrected_key")
    if corrected_bbits:
        # Convert string to list of ints
        key_bits = [int(b) for b in corrected_bbits]
    else:
        key_bits = exp_result["agoodbits"]

    message_bytes = message.encode('utf-8')
    if key_bits and len(key_bits) >= 8:
        encrypted_bytes = xor_encrypt_decrypt(message_bytes, key_bits)
        decrypted_bytes = xor_encrypt_decrypt(encrypted_bytes, key_bits)
        try:
            decrypted_message = decrypted_bytes.decode('utf-8')
        except Exception:
            decrypted_message = "<decryption failed>"
        encrypted_hex = encrypted_bytes.hex()
    else:
        encrypted_hex = ""
        decrypted_message = ""
    return {
        "original_message": message,
        "encrypted_message_hex": encrypted_hex,
        "decrypted_message": decrypted_message,
        "error_corrected_key": exp_result.get("error_corrected_key"),
        "final_secret_key": exp_result.get("final_secret_key"),
    }
