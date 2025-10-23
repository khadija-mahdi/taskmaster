import os
from termcolor import colored
from ParseConfige import ConfigParser

class ReloadHandler:
    def __init__(self, commands_instance):
        self.commands = commands_instance

    def delete_process_info_entries(self, program_name):
        """Delete all process_info entries for a given program name."""
        keys_to_delete = []
        for key, info in self.commands.process_info.items():
            if info.get('program_name') == program_name:
                keys_to_delete.append(key)

        for key in keys_to_delete:
            master_fd = self.commands.process_info[key].get('master_fd')
            if master_fd:
                try:
                    os.close(master_fd)
                except:
                    pass
            del self.commands.process_info[key]

        if program_name in self.commands.running_processes:
            del self.commands.running_processes[program_name]

    def program_has_changed(self, old_config, new_config, program_name):
        """Check if the configuration of a program has changed."""
        old_program = old_config.get(program_name, {})
        new_program = new_config.get(program_name, {})

        if bool(old_program) != bool(new_program):
            return True

        if not old_program and not new_program:
            return False

        ignore_keys = {'name'}

        all_keys = (set(old_program.keys()) | set(
            new_program.keys())) - ignore_keys

        for key in all_keys:
            old_val = old_program.get(key)
            new_val = new_program.get(key)

            if old_val is None and new_val is None:
                continue
            if old_val is None or new_val is None:
                print(
                    f"DEBUG: '{program_name}' - key '{key}' changed: {old_val} -> {new_val}")
                return True

            if old_val != new_val:
                print(
                    f"DEBUG: '{program_name}' - key '{key}' changed: {old_val} -> {new_val}")
                return True

        return False

    def reload_single_program(self, program_name, new_programs):
        """Reload a single program if its configuration has changed."""
        out = []
        
        if program_name not in new_programs:
            out.append(colored(f"ERROR: Program '{program_name}' not found in new configuration.", "red"))
            return out

        if self.program_has_changed(self.commands.programs, new_programs, program_name):
            out.append(f"Detected changes in '{program_name}' configuration")
            self.commands.stop_command(self.commands.programs, program_name, True)
            self.delete_process_info_entries(program_name)
            self.commands.programs[program_name] = new_programs[program_name]

            result = self.commands.start_command(self.commands.programs, program_name)
            out.append(result)
            out.append(colored(f"Program '{program_name}' reloaded successfully.", "green"))
        else:
            out.append(colored(f"No changes detected for program '{program_name}'.", "yellow"))
        
        return out

    def remove_deleted_programs(self, new_programs):
        """Remove programs that no longer exist in the new configuration."""
        out = []
        for pname in list(self.commands.programs.keys()):
            if pname not in new_programs:
                out.append(f"Removing program '{pname}'...")
                self.commands.stop_command(self.commands.programs, pname, True)
                self.delete_process_info_entries(pname)
                del self.commands.programs[pname]
                out.append(colored(f"Program '{pname}' removed.", "yellow"))
        return out

    def update_or_add_programs(self, new_programs):
        """Update existing programs or add new ones based on the new configuration."""
        out = []
        for pname, pdata in new_programs.items():
            if pname not in self.commands.programs:
                out.append(f"Adding new program '{pname}'...")
                self.commands.programs[pname] = pdata
                result = self.commands.start_command(self.commands.programs, pname)
                out.append(result)
                out.append(colored(f"Program '{pname}' added and started.", "green"))
            elif self.program_has_changed(self.commands.programs, new_programs, pname):
                out.append(f"Detected changes in '{pname}' configuration")
                self.commands.stop_command(self.commands.programs, pname, True)
                self.delete_process_info_entries(pname)
                self.commands.programs[pname] = pdata
                result = self.commands.start_command(self.commands.programs, pname)
                out.append(result)
                out.append(colored(f"Program '{pname}' reloaded successfully.", "green"))
            else:
                out.append(colored(f"No changes detected for program '{pname}'.", "yellow"))
        return out

    def reload_command(self, program_name=None, config_path='../../configs/config.yml'):
        """Reload the configuration and restart affected programs."""
        out = []
        out.append(colored("Reloading configuration...", "cyan"))

        try:
            new_programs = ConfigParser.parse_config_file(config_path)

            if program_name and program_name.lower() != 'all':
                reload_output = self.reload_single_program(program_name, new_programs)
                out.extend(reload_output)
            else:
                remove_output = self.remove_deleted_programs(new_programs)
                update_output = self.update_or_add_programs(new_programs)
                out.extend(remove_output)
                out.extend(update_output)

            out.append(colored("\nReload completed.", "green"))

        except Exception as e:
            err = f"ERROR: Failed to reload configuration: {e}"
            out.append(colored(err, "red"))
            print(err)

        return "\n".join(out)