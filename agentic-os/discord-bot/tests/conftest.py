import os
import sys

# Make the discord-bot package dir importable as top-level modules in tests.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
