import subprocess
import re

def log_message(message):
    print(message)

def get_current_gamma_primary():
    try:
        output = subprocess.check_output("xrandr --verbose", shell=True, text=True)
        current_output = None
        gamma = None
        for line in output.splitlines():
            if line.startswith("eDP") or line.startswith("LVDS") or "connected" in line:
                current_output = line.split()[0]
            if current_output and "Gamma:" in line:
                match = re.search(r"Gamma:\s*([\d.]+):([\d.]+):([\d.]+)", line)
                if match:
                    gamma = f"{match.group(1)}:{match.group(2)}:{match.group(3)}"
                    break  # Para no primeiro gamma (principal)
        return gamma
    except Exception as e:
        log_message(f"Erro ao ler gamma: {e}")
        return None

if __name__ == '__main__':
    x = get_current_gamma_primary()
    print(f"Gamma atual principal: {x}")
