"""
controllers/rebuild_demo_package.py

M26: single, deterministic entry point that regenerates every demo asset
listed in report/demo_script.md from scratch. Exists specifically as the
"simulation fallback" the master prompt requires (section 27) -- if a live
demo needs to be rebuilt on the spot, run this ONE script instead of
remembering which of the ~15 project scripts to run in which order.

Does NOT re-run the full validation suite (that's `python3 validate_*.py`
individually, if ever needed) -- only what's needed to regenerate the
demo-facing artifacts.
"""

import subprocess
import sys

STEPS = [
    ("Demo dashboard (success case: HOLD/TRACK/SEARCH under noise burst)",
     "build_demo_animation.py"),
    ("Demo shading-trap clip (honest limitation case)",
     "build_demo_shading.py"),
    ("Headline summary figure + master table",
     "final_summary.py"),
]


def main():
    for label, script in STEPS:
        print(f"\n=== {label} ({script}) ===")
        result = subprocess.run([sys.executable, script])
        if result.returncode != 0:
            print(f"FAILED at {script} -- stopping. Fall back to the "
                  f"already-saved static assets in results/figures/ and "
                  f"results/tables/, which do not depend on this rebuild.")
            sys.exit(1)
    print("\nAll demo assets rebuilt successfully.")


if __name__ == "__main__":
    main()
