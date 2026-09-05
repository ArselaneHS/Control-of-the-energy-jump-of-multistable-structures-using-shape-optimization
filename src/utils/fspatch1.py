import subprocess
import fireshape, pathlib
import os

project_dir = pathlib.Path(__file__).parent.parent.parent  # repo root

fireshape_dir = pathlib.Path(fireshape.__file__).parent.parent  # repo root
print(f"fireshape_dir: {fireshape_dir}")
patch_file = pathlib.Path(os.path.join(project_dir, "src", "utils", "fspatch.patch")).resolve()

subprocess.run(["git", "apply", "--check", str(patch_file)], cwd=fireshape_dir, check=True)  # dry run, fails loudly if patch doesn't apply cleanly
subprocess.run(["git", "apply", str(patch_file)],    cwd=fireshape_dir, check=True)


