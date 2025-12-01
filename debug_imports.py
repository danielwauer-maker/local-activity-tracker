import os, sys

print("CWD:", os.getcwd())
print("sys.path:")
for p in sys.path:
    print("  ", p)

print("\nInhalt im CWD:", os.listdir("."))

try:
    import routes
    print("\n✔ routes importierbar:", routes)
except Exception as e:
    print("\n✘ routes nicht importierbar:", e)

try:
    import routes.deps
    print("✔ routes.deps importierbar:", routes.deps)
except Exception as e:
    print("✘ routes.deps nicht importierbar:", e)
