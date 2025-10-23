def load_env_file(env_path):
    config = {}
    with open(env_path, 'r') as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                # Remove quotes if present
                value = value.strip('"')
                config[key] = value
    return config

def get_email_config():
    config = load_env_file('/home/hasabir/42_projects/taskmaster/env')
    return {
        'smtp_server': config['smtp_server'],
        'smtp_port': int(config['smtp_port']),
        'username': config['username'],
        'password': config['password'],
        'recipients': [config['recipients']] 
    }