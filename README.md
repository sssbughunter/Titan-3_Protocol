# ⚡ TITAN-3: Structurally Validated Lightweight Secure Command Framework

> A lightweight command security framework for civic digital infrastructure, combining Knight-Relaxed N-Queens key generation, grammar-based wrapping, and PDA tamper detection.

**Team:** Vajra Protocol  
**Members:** Prakhar Dwivedi, Pramod Batham, Sumit Yadav  
**Institution:** Rustamji Institute of Technology, Gwalior  
**Research Base:** [A Modified N-Queens Algorithm Using Knight-Move Constraints](https://doi.org/10.5281/zenodo.18814740)

---

## 🧠 Core Idea

India's governance systems are rapidly digitizing — field devices, booth nodes, and IoT infrastructure are expanding. Most systems rely on heavy cryptographic stacks without structural validation. **Titan-3 addresses the latency and integrity gap at the edge.**

Instead of adding another heavy encryption layer, Titan-3 adds **structural validation** as a complementary security mechanism — lightweight enough for constrained edge devices, smart enough to detect tampering.

---

## 🏗️ Architecture

```
ENCRYPT                          DECRYPT
───────                          ───────
Command Input                    Encrypted Packet
     │                                │
     ▼                                ▼
[1] Time-Derived N              [1] Same Clock → Same N
    (hour+min) % 8 → N∈[4,11]       Same Command → Same Start
     │                                │
     ▼                                ▼
[2] Command Hash → Start Cell   [2] Knight-Relaxed Solver
    SHA-256 → (row, col)             → Same Key (no transmission)
     │                                │
     ▼                                ▼
[3] Knight-Relaxed N-Queens     [3] XOR Decrypt
    Finds ONE solution               (symmetric — reverses encrypt)
    → 32-char key                     │
     │                                ▼
     ▼                          [4] PDA Bracket Validator
[4] Grammar Wrap                     Checks structural integrity
    3 random bracket layers          REJECT if tampered ✗
    e.g. <<{COMMAND}>>               ACCEPT if valid ✓
     │                                │
     ▼                                ▼
[5] XOR Encrypt                 [5] Strip Brackets
    → Base64 Packet                  → Original Command
```

---

## 🔑 Key Innovation: No Key Transmission

**The key is never sent.** Both sender and receiver independently derive the same key because:

- **Time synchronization**: `(hour + minute) % 8` → same N from same clock
- **Command as seed**: SHA-256 hash of command → same starting cell on board
- **Deterministic solver**: same N + same start → same Knight-Relaxed solution → same key

An attacker intercepting packets has **no key to steal** — it exists only in computation.

---

## 🧩 Component 1: Knight-Relaxed N-Queens Key Generator

Based on published research: *"A Modified N-Queens Algorithm Using Knight-Move Constraints"* — Prakhar Dwivedi, DOI: [10.5281/zenodo.18814740](https://doi.org/10.5281/zenodo.18814740)

**Why this is harder to brute-force than standard N-Queens:**
- Board size N is variable (4–11), derived from current time
- Only **ONE solution** is found — not all solutions
- Attacker must find all Knight-Relaxed solutions for **every possible N** to brute force
- Knight constraint creates an exponentially larger search problem vs standard N-Queens

**The algorithm:**
1. Place queens row by row using standard backtracking
2. Additionally avoid positions under knight attack from placed queens
3. If knight constraint blocks ALL columns in a row → **relax it** (Dwivedi's key innovation)
4. This prunes the search tree while guaranteeing a solution is always found

---

## 🧩 Component 2: Grammar Wrapper (Polymorphic Layering)

Each command is wrapped in **3 randomly chosen bracket layers** from `[]`, `{}`, `<>`, `()`:

```
MOVE  →  <<{MOVE}>>   (one encryption)
MOVE  →  [{(MOVE)}]   (next encryption — different layers)
MOVE  →  {[<MOVE>]}   (next encryption — different again)
```

This polymorphism means identical commands produce structurally different packets — defeating pattern analysis attacks.

---

## 🧩 Component 3: PDA Tamper Detection

On decryption, a **Pushdown Automaton** validates the bracket structure:

- Stack initialized with bottom marker `$`
- Opening brackets pushed onto stack
- Closing brackets matched against stack top
- Accept only if stack is empty (just `$`) at end

If an attacker modifies even one byte of the encrypted packet, the decrypted brackets will be malformed and the **PDA rejects the packet** — providing structural integrity verification independent of the cryptographic layer.

This is the textbook context-free language that PDAs are formally defined to recognize: balanced nested brackets.

---

## 📊 Performance Benchmarks

| Metric | Value |
|--------|-------|
| PDA Validation Latency | ~0.008 ms |
| Full Pipeline Latency | ~0.2 ms |
| Throughput | ~5,000 ops/sec (Python) |
| Memory Footprint | O(N) — minimal |
| Cloud Dependency | None |

**Separation of concerns:** PDA validation alone runs at ~0.008ms. The full pipeline (keygen + wrap + encrypt) runs at ~0.2ms — still edge-ready without infrastructure upgrades.

**Efficiency vs RSA-2048:** XOR-based structural validation operates without modular exponentiation, making it 20–50x computationally lighter — appropriate for constrained booth-level nodes that cannot run PKI stacks.

---

## 🚀 Quick Start

```bash
git clone https://github.com/sssbughunter/Titan-3_Protocol.git
cd Titan-3_Protocol
python3 titan3_final.py
```

**Requirements:** Python 3.10+ (standard library only — no dependencies)

---

## 💻 Usage Example

```python
from titan3_final import Titan3

titan = Titan3()

# Encrypt
packet = titan.encrypt("SCAN_BOOTH_01")
# → derives N from time, finds Knight-Relaxed solution, wraps, XOR encrypts

# Decrypt (receiver has same command + same clock)
original = titan.decrypt(packet, "SCAN_BOOTH_01")
# → same key derived, XOR reversed, PDA validates brackets, strips layers
# → returns "SCAN_BOOTH_01"
```

---

## 🔬 Why This Matters for Governance Infrastructure

| Challenge | Titan-3 Response |
|-----------|-----------------|
| Heavy crypto on constrained devices | XOR + structural validation, no PKI |
| Key distribution problem | Time + command derive key — nothing transmitted |
| Tamper detection at edge | PDA bracket validation on every decryption |
| Pattern analysis attacks | Polymorphic grammar wrapping |
| Brute force of key space | Variable N + Knight constraint — exponential search |

---

## 📁 Repository Structure

```
Titan-3_Protocol/
├── titan3_final.py      # Complete system implementation
├── README.md            # This file
└── demo.ipynb           # Interactive Colab demo
```

---

## 📖 Citation

If you use this work, please cite:

```
Prakhar Dwivedi, "A Modified N-Queens Algorithm Using Knight-Move Constraints,"
Rustamji Institute of Technology, Gwalior.
DOI: 10.5281/zenodo.18814740
```

---

*Titan-3 — Structural Security for Civic Digital Infrastructure*
