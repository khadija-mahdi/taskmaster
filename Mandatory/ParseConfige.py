import yaml
import os
import sys


class ConfigError(Exception):
    """Custom exception for configuration errors"""
    pass


class ConfigParser:
    VALID_SIGNALS = ['TERM', 'HUP', 'INT', 'QUIT', 'KILL', 'USR1', 'USR2']
    VALID_AUTORESTART = ['always', 'never', 'unexpected', True, False]
    # DEFAULT_CONFIG = {
    #     'numprocs': 1,
    #     'autostart': False,
    #     'autorestart': 'unexpected',
    #     'exitcodes': [0],
    #     'starttime': 1,
    #     'startretries': 3,
    #     'stopsignal': 'TERM',
    #     'stoptime': 10,
    #     'stdout': None,
    #     'stderr': None,
    #     'env': {},
    #     'workingdir': None,
    #     'umask': 0o022
    # }
    REQUIRED_FIELDS = ['cmd']

    def parse_config_file(file_path="../../configs/configMan.yml"):
        """Parse and validate configuration file"""
        try:
            if not os.path.exists(file_path):
                raise ConfigError(f"Configuration file not found: {file_path}")

            if not os.access(file_path, os.R_OK):
                raise ConfigError(
                    f"Configuration file is not readable: {file_path}")

            with open(file_path, 'r') as file:
                config_data = yaml.safe_load(file)

            if not isinstance(config_data, dict):
                raise ConfigError(
                    "Configuration file must be a YAML dictionary")

            if "programs" in config_data:
                programs = config_data["programs"]
            else:
                programs = config_data

            if not isinstance(programs, dict):
                raise ConfigError("'programs' must be a dictionary")

            if not programs:
                raise ConfigError("No programs defined in configuration")

            parsed_programs = {}
            for name, config in programs.items():
                try:
                    parsed_programs[name] = ConfigParser.parse_program(name, config)
                except ConfigError as e:
                    raise ConfigError(f"Error in program '{name}': {e}")

            return parsed_programs

        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML syntax: {e}")
        except ConfigError:
            raise
        except Exception as e:
            raise ConfigError(f"Unexpected error: {e}")

    def parse_program(name, config):
        """Parse and validate a single program configuration"""
        try:
            if not isinstance(config, dict):
                raise ConfigError(f"Configuration must be a dictionary")

            parsed = {}
            
            for field in config:
                if field not in ConfigParser.VALID_FIELDS:
                    raise ConfigError(f"Unknown field: '{field}'")
            
            for field in ConfigParser.REQUIRED_FIELDS:
                if field not in config or not config[field]:
                    raise ConfigError(
                        f"Missing or empty required field: '{field}'")

            parsed['cmd'] = ConfigParser._validate_cmd(config['cmd'])

            if 'numprocs' in config:
                parsed['numprocs'] = ConfigParser._validate_numprocs(
                    config['numprocs'])

            if 'autostart' in config:
                parsed['autostart'] = ConfigParser._validate_autostart(
                    config['autostart'])

            if 'autorestart' in config:
                parsed['autorestart'] = ConfigParser._validate_autorestart(
                    config['autorestart'])

            if 'exitcodes' in config:
                parsed['exitcodes'] = ConfigParser._validate_exitcodes(
                    config['exitcodes'])

            if 'starttime' in config:
                parsed['starttime'] = ConfigParser._validate_positive_int(
                    config['starttime'], 'starttime')

            if 'startretries' in config:
                parsed['startretries'] = ConfigParser._validate_non_negative_int(
                    config['startretries'], 'startretries')

            if 'stopsignal' in config:
                parsed['stopsignal'] = ConfigParser._validate_signal(
                    config['stopsignal'])

            if 'stoptime' in config:
                parsed['stoptime'] = ConfigParser._validate_positive_int(
                    config['stoptime'], 'stoptime')

            if 'stdout' in config:
                parsed['stdout'] = ConfigParser._validate_file_path(
                    config['stdout'], 'stdout')

            if 'stderr' in config:
                parsed['stderr'] = ConfigParser._validate_file_path(
                    config['stderr'], 'stderr')

            if 'env' in config:
                parsed['env'] = ConfigParser._validate_env(config['env'])

            if 'workingdir' in config:
                parsed['workingdir'] = ConfigParser._validate_directory(
                    config['workingdir'])

            if 'umask' in config:
                parsed['umask'] = ConfigParser._validate_umask(config['umask'])

            return parsed
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    def _validate_cmd(value):
        """Validate command"""
        if not isinstance(value, str):
            raise ConfigError("'cmd' must be a string")

        if not value or not value.strip():
            raise ConfigError("'cmd' cannot be empty")

        return value.strip()

    def _validate_numprocs(value):
        """Validate number of processes"""
        if not isinstance(value, int):
            raise ConfigError("'numprocs' must be an integer")

        if value < 1:
            raise ConfigError("'numprocs' must be at least 1")

        if value >= 10:
            raise ConfigError("'numprocs' cannot exceed 10")

        return value

    def _validate_autostart(value):
        """Validate autostart"""
        if not isinstance(value, bool):
            raise ConfigError("'autostart' must be a boolean (true/false)")

        return value

    def _validate_autorestart(value):
        """Validate autorestart"""
        if value not in ConfigParser.VALID_AUTORESTART:
            raise ConfigError(
                f"'autorestart' must be one of: always, never, unexpected, true, or false"
            )

        if value is True:
            return 'always'
        elif value is False:
            return 'never'

        return value

    def _validate_exitcodes(value):
        """Validate exit codes"""
        if isinstance(value, int):
            if not (0 <= value <= 255):
                raise ConfigError("Exit codes must be between 0 and 255")
            return [value]

        if isinstance(value, list):
            if not value:
                raise ConfigError("'exitcodes' list cannot be empty")

            codes = []
            for code in value:
                if not isinstance(code, int):
                    raise ConfigError("All exit codes must be integers")
                if not (0 <= code <= 255):
                    raise ConfigError("Exit codes must be between 0 and 255")
                codes.append(code)

            return codes

        raise ConfigError(
            "'exitcodes' must be an integer or a list of integers")

    def _validate_positive_int(value, field_name):
        """Validate positive integer"""
        if not isinstance(value, int):
            raise ConfigError(f"'{field_name}' must be an integer")

        if value < 1:
            raise ConfigError(f"'{field_name}' must be at least 1")

        return value

    def _validate_non_negative_int(value, field_name):
        """Validate non-negative integer"""
        if not isinstance(value, int):
            raise ConfigError(f"'{field_name}' must be an integer")

        if value < 0:
            raise ConfigError(f"'{field_name}' cannot be negative")

        return value

    def _validate_signal(value):
        """Validate signal name"""
        if not isinstance(value, str):
            raise ConfigError("'stopsignal' must be a string")

        value = value.upper()

        if value not in ConfigParser.VALID_SIGNALS:
            raise ConfigError(
                f"'stopsignal' must be one of: {', '.join(ConfigParser.VALID_SIGNALS)}"
            )

        return value

    def _validate_file_path(value, field_name):
        """Validate file path"""
        if value is None:
            return None

        if not isinstance(value, str):
            raise ConfigError(f"'{field_name}' must be a string")

        if not value.strip():
            raise ConfigError(f"'{field_name}' cannot be empty")

        directory = os.path.dirname(value)
        if directory and not os.path.exists(directory):
            raise ConfigError(
                f"'{field_name}': directory does not exist: {directory}")

        return value

    def _validate_directory(value):
        """Validate working directory"""
        if value is None:
            return None

        if not isinstance(value, str):
            raise ConfigError("'workingdir' must be a string")

        if not value.strip():
            raise ConfigError("'workingdir' cannot be empty")

        if not os.path.exists(value):
            raise ConfigError(f"'workingdir' does not exist: {value}")

        if not os.path.isdir(value):
            raise ConfigError(f"'workingdir' is not a directory: {value}")

        return value

    def _validate_env(value):
        """Validate environment variables"""
        if not isinstance(value, dict):
            raise ConfigError("'env' must be a dictionary")

        env = {}
        for key, val in value.items():
            if not isinstance(key, str):
                raise ConfigError(
                    f"Environment variable name must be string: {key}")

            env[key] = str(val)

        return env

    def _validate_umask(value):
        """Validate umask"""
        if isinstance(value, int):
            umask_value = value

        elif isinstance(value, str):
            if not value.strip():
                raise ConfigError("'umask' cannot be empty")

            try:
                umask_value = int(value, 8)
            except ValueError:
                raise ConfigError(
                    f"'umask' must be a valid octal number: {value}")

        else:
            raise ConfigError("'umask' must be an integer or octal string")

        if not (0 <= umask_value <= 0o777):
            raise ConfigError(
                f"'umask' must be between 0 and 0777 (octal): {oct(umask_value)}")

        return umask_value