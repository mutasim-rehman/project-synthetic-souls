import sys
import argparse

try:
    from src.moderator import ModeratorInterface
except ImportError:
    print("Please run this script from the root project directory.")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Synthetic Souls: False Mind Engine")
    # For future extensions, we can add silent mode, auto-defaults, etc.
    args = parser.parse_args()

    try:
        mod = ModeratorInterface()
        mod.start()
    except KeyboardInterrupt:
        print("\n\nSimulation forcibly aborted by Moderator.")
        sys.exit(0)

if __name__ == "__main__":
    main()
