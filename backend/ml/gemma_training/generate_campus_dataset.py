"""
Backward compatibility re-export shim.
Canonical dataset generator has been renamed to generate_echosphere_dataset.py.
"""
import os
import sys

from generate_echosphere_dataset import *

if __name__ == "__main__":
    generate_dataset(5000)
