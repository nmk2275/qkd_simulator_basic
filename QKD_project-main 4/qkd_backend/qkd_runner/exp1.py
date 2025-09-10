# qkd_backend/qkd_runner/exp1.py
def xor_encrypt_decrypt(message_bytes, key_bits):
    # Repeat key_bits to match the length of message_bytes
    key = (key_bits * ((len(message_bytes) // len(key_bits)) + 1))[:len(message_bytes)]
    key_bytes = bytes([int(b) for b in key])
    return bytes([mb ^ kb for mb, kb in zip(message_bytes, key_bytes)])
def run_exp1(message=None):
    # Qiskit patterns step 1: Map your problem to quantum circuit
    # Import some generic packages
    import numpy as np
    from qiskit import QuantumCircuit
    import matplotlib.pyplot as plt 
    from io import BytesIO
    import os
    import hashlib
    from qiskit.visualization import circuit_drawer
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    # Set up a random number generator and a quantum circuit. 
    rng = np.random.default_rng()
    bit_num = 20
    qc = QuantumCircuit(bit_num, bit_num)

    # QKD step 1: Random bits and bases for Sender
    abits = np.round(rng.random(bit_num))
    abase = np.round(rng.random(bit_num))

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

    qc.barrier()

    # QKD step 2: Random bases for Receiver
    bbase = np.round(rng.random(bit_num))

    for m in range(bit_num):
        if bbase[m] == 1:
            qc.h(m)
        qc.measure(m, m)

    print("Sender's bits are ", abits)
    print("Sender's bases are ", abase)
    print("Receiver's bases are ", bbase)

    

    from qiskit_ibm_runtime import QiskitRuntimeService
    service = QiskitRuntimeService()
    backend = service.backend("ibm_brisbane")
    print(backend.name)

    from qiskit.primitives import BackendSamplerV2
    from qiskit_aer import AerSimulator
    from qiskit_aer.noise import NoiseModel
    from qiskit_ibm_runtime import SamplerV2 as Sampler
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

    noise_model = NoiseModel.from_backend(backend)
    backend_sim = AerSimulator(noise_model=noise_model)
    sampler_sim = BackendSamplerV2(backend=backend_sim)

    target = backend.target
    pm = generate_preset_pass_manager(target=target, optimization_level=3)
    qc_isa = pm.run(qc)

    sampler = Sampler(mode=backend)
    job = sampler.run([qc_isa], shots=1024)

    counts = job.result()[0].data.c.get_counts()
    countsint = job.result()[0].data.c.get_int_counts()

    keys = counts.keys()
    key = list(keys)[0]
    bmeas = list(key)
    bmeas_ints = []
    for n in range(bit_num):
        bmeas_ints.append(int(bmeas[n]))
    bbits = bmeas_ints[::-1]

    print(bbits)

    # QKD step 3: Public discussion of bases
    agoodbits = []
    bgoodbits = []
    match_count = 0
    for n in range(bit_num):
        if abase[n] == bbase[n]:
            agoodbits.append(int(abits[n]))
            bgoodbits.append(bbits[n])
            if int(abits[n]) == bbits[n]:
                match_count += 1
    import hashlib

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

    print(agoodbits)
    print(bgoodbits)
    print("fidelity = ", match_count / len(agoodbits))
    print("loss = ", 1 - match_count / len(agoodbits))
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

    # Return results as string for UI
    return {
        "Sender_bits": abits.tolist(),
        "Sender_bases": abase.tolist(),
        "Receiver_bases": bbase.tolist(),
        "Receiver_bits": bbits,
        "agoodbits": agoodbits,
        "bgoodbits": bgoodbits,
        "fidelity": match_count / len(agoodbits),
        "loss": 1 - match_count / len(agoodbits),
         "error_corrected_key": error_corrected_key,
        "final_secret_key": secret_key,
        "original_message": message,
        "encrypted_message_hex": encrypted_hex,
        "decrypted_message": decrypted_message,
        "circuit_diagram_url": "/static/circuit_exp2.png",
        "counts": counts
    }
def encrypt_with_existing_key(exp_result, message):
    agoodbits = exp_result["agoodbits"]
    bgoodbits = exp_result["bgoodbits"]
    # Use the same error correction and privacy amplification as before if needed
    message_bytes = message.encode('utf-8')
    if agoodbits and len(agoodbits) >= 8:
        encrypted_bytes = xor_encrypt_decrypt(message_bytes, agoodbits)
        decrypted_bytes = xor_encrypt_decrypt(encrypted_bytes, bgoodbits)
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
        # Optionally, include other fields you want to show
    }

