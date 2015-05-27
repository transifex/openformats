from string import ascii_letters, digits
from random import choice

def generate_random_string(length=20):
    return ''.join(choice(ascii_letters + digits) for _ in range(length))
