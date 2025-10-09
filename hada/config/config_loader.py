import yaml 

def load_config(config_path="./config/config.yaml"):
    """
    Carica un file di configurazione YAML.

    Args:
        config_path (str): Percorso al file di configurazione YAML.

    Returns:
        dict: Configurazione caricata come dizionario.
    """
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
    return config