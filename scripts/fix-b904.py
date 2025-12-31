#!/usr/bin/env python3
"""Script to fix B904 errors (exception chaining)."""

import re
import sys
from pathlib import Path

def fix_b904_in_file(file_path: Path) -> int:
    """Fix B904 errors in a single file."""
    content = file_path.read_text()
    original_content = content
    fixes = 0

    # Pattern pour trouver "raise Exception" dans un bloc except
    # On cherche les raise qui ne sont pas déjà avec "from"
    lines = content.split('\n')
    new_lines = []
    in_except = False
    except_var = None

    for i, line in enumerate(lines):
        # Détecte un bloc except avec une variable
        except_match = re.match(r'^(\s*)except\s+\w+(?:\s+as\s+(\w+))?:', line)
        if except_match:
            in_except = True
            except_var = except_match.group(2)
            new_lines.append(line)
            continue

        # Détecte la fin d'un bloc except
        if in_except and line and not line[0].isspace():
            in_except = False
            except_var = None

        # Fix raise statements dans except blocks
        if in_except and 'raise ' in line and ' from ' not in line:
            # Ne pas modifier les "raise" sans argument (re-raise)
            if re.search(r'raise\s*$', line.strip()):
                new_lines.append(line)
                continue

            # Ajouter "from e" ou "from None"
            indent = len(line) - len(line.lstrip())
            if except_var:
                # Si on a une variable d'exception, utiliser "from <var>"
                new_line = line.rstrip() + f' from {except_var}'
            else:
                # Sinon, utiliser "from None" pour supprimer le contexte
                new_line = line.rstrip() + ' from None'

            new_lines.append(new_line)
            fixes += 1
        else:
            new_lines.append(line)

    if fixes > 0:
        new_content = '\n'.join(new_lines)
        file_path.write_text(new_content)
        print(f"Fixed {fixes} B904 errors in {file_path}")

    return fixes

def main():
    """Main function."""
    src_dir = Path(__file__).parent.parent / 'src' / 'backend' / 'src'

    if not src_dir.exists():
        print(f"Error: {src_dir} does not exist")
        return 1

    total_fixes = 0
    for py_file in src_dir.rglob('*.py'):
        fixes = fix_b904_in_file(py_file)
        total_fixes += fixes

    print(f"\nTotal: Fixed {total_fixes} B904 errors")
    return 0

if __name__ == '__main__':
    sys.exit(main())
