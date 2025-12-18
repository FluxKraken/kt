import re
import subprocess
from jinja2 import Environment, nodes, meta, Template as JinjaTemplate

def extract_nested_variables(content):
    """
    Analyzes a Jinja2 template content and returns a dictionary of all
    undeclared variables, supporting nested dot-notation paths.
    """
    env = Environment()
    ast = env.parse(content)

    undeclared = meta.find_undeclared_variables(ast)
    paths = set()
    
    def get_path(node):
        if isinstance(node, nodes.Name):
            return [node.name]
        elif isinstance(node, nodes.Getattr):
            base_path = get_path(node.node)
            if base_path:
                return base_path + [node.attr]
        elif isinstance(node, nodes.Getitem):
            base_path = get_path(node.node)
            if base_path and isinstance(node.arg, nodes.Const):
                return base_path + [str(node.arg.value)]
        return None

    # We want to find all access paths
    for node in ast.find_all((nodes.Getattr, nodes.Getitem, nodes.Name)):
        path = get_path(node)
        if path:
            # Only include if the root is an undeclared variable
            if path[0] in undeclared:
                paths.add(tuple(path))
            
    return build_nested_dict(paths)

def build_nested_dict(paths):
    """
    Converts a list of tuples representing paths into a nested dictionary.
    """
    result = {}
    # Sort paths by length to ensure we create parents before children
    for path in sorted(paths, key=len):
        current = result
        for i, part in enumerate(path):
            if i == len(path) - 1:
                # If this is a leaf and already exists as a dict, don't overwrite it with ""
                if part not in current:
                    current[part] = ""
            else:
                if part not in current or not isinstance(current[part], dict):
                    current[part] = {}
                current = current[part]
    return result

def merge_recursive(target, source):
    """
    Deeply merges source dictionary into target.
    """
    for k, v in source.items():
        if k in target and isinstance(target[k], dict) and isinstance(v, dict):
            merge_recursive(target[k], v)
        else:
            target[k] = v

def check_missing(skel, ctx):
    """
    Checks if all keys/structures in skel are present in ctx.
    Returns True if anything is missing.
    """
    for k, v in skel.items():
        if k not in ctx:
            return True
        if isinstance(v, dict):
            if not isinstance(ctx[k], dict):
                return True
            if check_missing(v, ctx[k]):
                return True
        # If it's a leaf, and it's present in ctx, we consider it not missing 
        # (even if it's an empty string, as the user might want that)
    return False


def render_template_with_shell(template_content, context):
    """
    Renders a Jinja2 template and then processes shell command tags {>command<}.
    Supports Jinja variables within shell commands.
    """
    # 1. First Pass: Render Jinja2 variables
    # This allows things like {>echo {{name}}<}
    env = Environment()
    template = env.from_string(template_content)
    intermediate_content = template.render(context)

    # 2. Second Pass: Process shell commands {>...<}
    def replace_shell(match):
        command = match.group(1).strip()
        try:
            # Execute command and return output
            result = subprocess.run(
                command,
                shell=True,
                check=True,
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            return f"ERROR: Command '{command}' failed with exit code {e.returncode}: {e.stderr.strip()}"
        except Exception as e:
            return f"ERROR: Failed to execute command '{command}': {str(e)}"

    # Regex to find {>command<}
    # Using a non-greedy match to avoid capturing across multiple tags
    pattern = r'\{>(.*?)<\}'
    
    final_content = re.sub(pattern, replace_shell, intermediate_content)
    
    return final_content
