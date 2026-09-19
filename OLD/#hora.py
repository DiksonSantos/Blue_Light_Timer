# novo_script.py

from datetime import datetime
from hora_certa import daily_transitions

def get_transitions_for_today():
    """
    Retorna os horários de transição (manhã e noite) para o dia atual.
    """
    today = datetime.now().day
    return daily_transitions.get(today, {
        "MORNING_START": None,
        "EVENING_START": None
    })

# Exemplo de uso:
if __name__ == "__main__":
    transitions = get_transitions_for_today()
    print(f"Transição manhã: {transitions['MORNING_START']}")
    print(f"Transição noite: {transitions['EVENING_START']}")
