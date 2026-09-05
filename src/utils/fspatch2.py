import subprocess
import fireshape, pathlib
import os

project_dir = pathlib.Path(__file__).parent.parent.parent  # repo root


fireshape_dir = pathlib.Path(fireshape.__file__).parent.parent  # repo root
patch_file = pathlib.Path(os.path.join(project_dir, "src", "utils", "fspatch.patch")).resolve()


subprocess.run(["git", "apply", "-R", "--check", str(patch_file)], cwd=fireshape_dir, check=True)
subprocess.run(["git", "apply", "-R", str(patch_file)], cwd=fireshape_dir, check=True)