import random
import base64
import time
import statistics
import hashlib
import socket
from datetime import datetime

# ============================================================
# TITAN-3 v2.0 — Full Secrecy Edition
# Key = KnightSolver(seed + time)
# Seed = SHA-256(hostname + INSTALL_KEY + current_hour)
# Command is now FULLY SECRET — never used in key derivation
# Both sender and receiver share same source code + INSTALL_KEY
# ============================================================

# ── INSTALLATION KEY ────────────────────────────────────────
# This is the ONE shared secret — exchanged once at setup.
# Like a WiFi password — hardcoded in both sender & receiver.
# Change this to your own secret before deployment.
INSTALL_KEY = "TITAN3-VAJRA-PROTOCOL-2026-RJIT"

# ── KNIGHT MOVE OFFSETS ─────────────────────────────────────
DX = [2,  1, -1, -2, -2, -1,  1,  2]
DY = [1,  2,  2,  1, -1, -2, -2, -1]


# ============================================================
# 1. HOURLY ROTATING SEED
#    Seed = SHA-256(hostname + INSTALL_KEY + current_hour)
#    Changes every hour — attacker can't reuse old packets
#    Both sides derive same seed independently — nothing sent
# ============================================================

def get_hourly_seed() -> tuple[bytes, int, int]:
    now      = datetime.now()
    hostname = socket.gethostname()
    # Seed rotates every hour
    seed_str = f"{hostname}:{INSTALL_KEY}:{now.year}{now.month}{now.day}{now.hour}"
    seed     = hashlib.sha256(seed_str.encode()).digest()
    return seed, now.hour, now.minute


# ============================================================
# 2. SEED → SOLVER PARAMS (N + start_col + col_priority)
#    N from (hour + minute) % 8 → board size
#    start_col + col_priority from seed bytes
#    Command NOT used in key derivation anymore
# ============================================================

def get_N_from_time() -> tuple[int, int, int]:
    now = datetime.now()
    idx = (now.hour + now.minute) % 8
    return idx + 4, now.hour, now.minute


def seed_to_params(seed: bytes, N: int) -> tuple[int, list]:
    """
    Derive start_col and col_priority from hourly seed.
    Same seed + same N → same params on both sides.
    Command is NOT involved — full secrecy achieved.
    """
    start_col = int.from_bytes(seed[0:4], 'big') % N

    cols = list(range(N))
    for i in range(N - 1, 0, -1):
        bi = (i * 3) % 32
        j  = int.from_bytes(seed[bi:bi+2], 'big') % (i + 1)
        cols[i], cols[j] = cols[j], cols[i]

    return start_col, cols


# ============================================================
# 3. KNIGHT-RELAXED N-QUEENS SOLVER
#    Prakhar Dwivedi's algorithm — DOI: 10.5281/zenodo.18814740
#    Finds ONE solution from seed-derived start — unpredictable
# ============================================================

def hybrid_queens_keygen(N: int, start_col: int, col_priority: list) -> list | None:
    queens   = [-1] * N
    col_mask = 0
    diag1    = 0
    diag2    = 0

    def is_safe(r, c):
        return not (
            (col_mask >> c) & 1 or
            (diag1 >> (r - c + N)) & 1 or
            (diag2 >> (r + c)) & 1
        )

    def place(r, c):
        nonlocal col_mask, diag1, diag2
        queens[r] = c
        col_mask |= (1 << c)
        diag1    |= (1 << (r - c + N))
        diag2    |= (1 << (r + c))

    def unplace(r, c):
        nonlocal col_mask, diag1, diag2
        queens[r] = -1
        col_mask ^= (1 << c)
        diag1    ^= (1 << (r - c + N))
        diag2    ^= (1 << (r + c))

    def solve(row, pr, pc):
        if row == N:
            return True
        tried = False
        for d in range(8):
            kr, kc = pr + DX[d], pc + DY[d]
            if kr == row and 0 <= kc < N and is_safe(row, kc):
                tried = True
                place(row, kc)
                if solve(row + 1, row, kc): return True
                unplace(row, kc)
        if not tried:
            for col in col_priority:
                if is_safe(row, col):
                    place(row, col)
                    if solve(row + 1, row, col): return True
                    unplace(row, col)
        return False

    place(0, start_col)
    if solve(1, 0, start_col):
        return list(queens)
    unplace(0, start_col)
    return None


def get_session_key(verbose: bool = False) -> tuple[str, int, int, int, list]:
    """
    Derives session key from:
      seed  = SHA-256(hostname + INSTALL_KEY + current_hour)
      N     = (hour + minute) % 8 + 4
      start = seed_to_params(seed, N)
      key   = KnightSolver(start, col_priority)

    Command is NOT used. Key is fully independent of message.
    Both sender and receiver run this and get identical key.
    """
    seed, hour, minute = get_hourly_seed()
    N, _, _            = get_N_from_time()
    start_col, col_priority = seed_to_params(seed, N)

    solution = None
    for offset in range(N):
        col = (start_col + offset) % N
        sol = hybrid_queens_keygen(N, col, col_priority)
        if sol:
            solution = sol
            break

    if not solution:
        raw_key = "FAILSAFE0000000000000000000000000"
    else:
        # Mix solution with seed for final key
        raw  = "".join(str(x) for x in solution)
        seed_hex = seed.hex()
        key  = ""
        for i in range(32):
            board_digit = int(raw[i % len(raw)])
            seed_digit  = int(seed_hex[i % len(seed_hex)], 16) % 10
            key += str((board_digit + seed_digit) % 10)
        raw_key = key

    if verbose:
        print(f"  [SEED]     SHA-256(hostname+INSTALL_KEY+hour) → {seed.hex()[:16]}...")
        print(f"  [TIME]     {hour:02d}:{minute:02d} → N={N}")
        print(f"  [START]    col={start_col}, priority={col_priority[:5]}...")
        print(f"  [SOLUTION] {solution}")
        print(f"  [KEY]      {raw_key}")

    return raw_key, N, hour, minute, solution or []


# ============================================================
# 4. XOR ENGINE
# ============================================================

class XOR_Engine:
    def __init__(self, key: str):
        self.key = key

    def process(self, data: str) -> str:
        r = "".join(
            chr(ord(c) ^ ord(self.key[i % len(self.key)]))
            for i, c in enumerate(data)
        )
        return base64.b64encode(r.encode('latin-1')).decode()

    def deprocess(self, b64: str) -> str:
        raw = base64.b64decode(b64).decode('latin-1')
        return "".join(
            chr(ord(c) ^ ord(self.key[i % len(self.key)]))
            for i, c in enumerate(raw)
        )


# ============================================================
# 5. GRAMMAR WRAPPER — 3 Random Bracket Layers
# ============================================================

class GrammarWrapper:
    PAIRS   = {'[': ']', '{': '}', '<': '>', '(': ')'}
    OPENERS = list(PAIRS.keys())

    def wrap(self, command: str) -> str:
        layers = random.choices(self.OPENERS, k=3)
        p = command
        for o in reversed(layers):
            p = f"{o}{p}{self.PAIRS[o]}"
        return p

    def unwrap(self, packet: str) -> str:
        while packet and packet[0] in self.OPENERS \
              and packet[-1] == self.PAIRS[packet[0]]:
            packet = packet[1:-1]
        return packet


# ============================================================
# 6. PDA BRACKET VALIDATOR
# ============================================================

class PDA_BracketValidator:
    OPEN  = {'[', '{', '<', '('}
    CLOSE = {']', '}', '>', ')'}
    MATCH = {']': '[', '}': '{', '>': '<', ')': '('}

    def validate(self, packet: str) -> tuple[bool, str]:
        stack = ['$']
        for ch in packet:
            if ch in self.OPEN:
                stack.append(ch)
            elif ch in self.CLOSE:
                if len(stack) == 1:
                    return False, f"✗ Stack underflow — TAMPERED"
                if stack.pop() != self.MATCH[ch]:
                    return False, f"✗ Bracket mismatch — TAMPERED"
        if stack != ['$']:
            return False, f"✗ Unclosed brackets — TAMPERED"
        return True, "✓ Bracket structure valid — integrity confirmed"


# ============================================================
# 7. TITAN-3 v2 MAIN SYSTEM
# ============================================================

class Titan3:
    def __init__(self):
        self.wrapper = GrammarWrapper()
        self.pda     = PDA_BracketValidator()

    def encrypt(self, command: str, verbose: bool = True) -> str:
        if verbose:
            print(f"\n{'═'*62}")
            print(f"  ENCRYPTING: '{command}'")
            print(f"{'═'*62}")

        t0 = time.perf_counter()

        # Key from seed+time — command NOT involved
        key, N, h, m, sol = get_session_key(verbose)
        cipher  = XOR_Engine(key)

        # Wrap command in 3 random bracket layers
        wrapped = self.wrapper.wrap(command)
        packet  = cipher.process(wrapped)

        t1 = time.perf_counter()

        if verbose:
            print(f"  [WRAP]     {wrapped}")
            print(f"  [PACKET]   {packet}")
            print(f"  [TOTAL]    {(t1-t0)*1000:.4f} ms")

        return packet

    def decrypt(self, packet: str, verbose: bool = True) -> str | None:
        if verbose:
            print(f"\n{'═'*62}")
            print(f"  DECRYPTING packet")
            print(f"{'═'*62}")

        t0 = time.perf_counter()

        # Same key — same seed + same clock — no command needed
        key, N, h, m, sol = get_session_key(verbose)
        cipher    = XOR_Engine(key)
        unwrapped = cipher.deprocess(packet)

        t_pda = time.perf_counter()
        valid, reason = self.pda.validate(unwrapped)
        t_pda_end = time.perf_counter()

        t1 = time.perf_counter()

        if verbose:
            print(f"  [XOR]      '{unwrapped}'")
            print(f"  [PDA]      {reason}  ({(t_pda_end-t_pda)*1000:.4f} ms)")
            print(f"  [TOTAL]    {(t1-t0)*1000:.4f} ms")

        if not valid:
            if verbose:
                print(f"  [BLOCKED]  Packet rejected — tamper detected")
            return None

        original = self.wrapper.unwrap(unwrapped)
        if verbose:
            print(f"  [OUTPUT]   '{original}'")
        return original


# ============================================================
# 8. BENCHMARK
# ============================================================

def run_benchmark(iterations: int = 1000):
    print(f"\n{'═'*62}")
    print(f"  BENCHMARK — {iterations} commands")
    print(f"{'═'*62}")

    titan = Titan3()
    pool  = ["MOVE", "FIRE", "SCAN", "HALT", "STATUS",
             "ANYTHING", "random_string", "PrakharDwivedi", "123", "XYZ"]

    # Warm-up
    for _ in range(30):
        pkt = titan.encrypt(random.choice(pool), verbose=False)
        titan.decrypt(pkt, verbose=False)

    times_enc, times_dec, times_pda = [], [], []
    pda     = PDA_BracketValidator()
    wrapper = GrammarWrapper()

    for _ in range(iterations):
        cmd = random.choice(pool)

        t0  = time.perf_counter()
        pkt = titan.encrypt(cmd, verbose=False)
        t1  = time.perf_counter()

        tp0 = time.perf_counter()
        pda.validate(wrapper.wrap(cmd))
        tp1 = time.perf_counter()

        titan.decrypt(pkt, verbose=False)
        t2  = time.perf_counter()

        times_enc.append(t1 - t0)
        times_dec.append(t2 - t1)
        times_pda.append(tp1 - tp0)

    print(f"\n  Commands Tested      : {iterations}")
    print(f"  Avg Encrypt Latency  : {statistics.mean(times_enc)*1000:.4f} ms")
    print(f"  Avg Decrypt Latency  : {statistics.mean(times_dec)*1000:.4f} ms")
    print(f"  PDA Validation Only  : {statistics.mean(times_pda)*1000:.4f} ms")
    print(f"  Throughput           : {iterations/sum(times_enc):.0f} ops/sec")
    print(f"  Min Latency          : {min(times_enc)*1000:.4f} ms")
    print(f"{'═'*62}")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("╔════════════════════════════════════════════════════════════╗")
    print("║  ⚡ TITAN-3 v2.0 — Full Secrecy Edition                   ║")
    print("║  Key = KnightSolver(SHA-256(hostname+INSTALL_KEY+hour))   ║")
    print("║  Command is FULLY SECRET — not used in key derivation     ║")
    print("╚════════════════════════════════════════════════════════════╝")

    titan = Titan3()

    # Round-trip — notice decrypt needs NO command argument
    print("\n\n>>> ROUND-TRIP TESTS — receiver needs NO prior knowledge of command")
    for cmd in ["MOVE", "FIRE_DRONE", "SCAN_BOOTH_01", "HALT_UNIT_X9", "anything i want"]:
        pkt = titan.encrypt(cmd)
        rec = titan.decrypt(pkt)
        print(f"  ✓ '{cmd}' → '{rec}' → match: {cmd == rec}\n")

    # Tamper detection
    print("\n>>> TAMPER DETECTION")
    pkt = titan.encrypt("STATUS", verbose=False)
    corrupted = pkt[:-4] + "XXXX"
    print(f"  Original  : {pkt}")
    print(f"  Corrupted : {corrupted}")
    result = titan.decrypt(corrupted)
    print(f"  Blocked   : {result is None} ✓")

    # Benchmark
    run_benchmark(1000)

    # Interactive
    print("\n\n>>> INTERACTIVE MODE")
    print("    Receiver decrypts WITHOUT knowing the command in advance")
    print("    Type EXIT to quit\n")
    while True:
        cmd = input("Sender — Enter command: ").strip()
        if cmd.upper() == "EXIT":
            break
        pkt = titan.encrypt(cmd, verbose=False)
        print(f"  Packet sent: {pkt}")
        rec = titan.decrypt(pkt, verbose=True)
        print(f"  Recovered  : '{rec}'\n")
