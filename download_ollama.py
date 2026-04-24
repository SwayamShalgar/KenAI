import urllib.request
import os

url = "https://ollama.com/download/ollama-linux-amd64"
# Install right into the current folder as 'ollama_cmd' (to avoid conflict with the ollama/ directory)
dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ollama_cmd")

print(f"Downloading Ollama to {dest}...")
urllib.request.urlretrieve(url, dest)
os.chmod(dest, 0o755)
print("Done! You can now start 'ollama serve' in a new terminal.")
