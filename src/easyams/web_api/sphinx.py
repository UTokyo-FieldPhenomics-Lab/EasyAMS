import os
import shutil
import sys
import subprocess

def copy_sphinx_config(save_path):
    if not os.path.exists(save_path):
        os.makedirs(save_path, exist_ok=True)

    conf_from_path = os.path.join(
        os.path.dirname(__file__), 'conf.py'
    )

    conf_to_path = os.path.join(save_path, 'conf.py')

    with open(conf_from_path, 'rb') as src, \
         open(conf_to_path,   'wb') as dst:
            dst.write(src.read())

def build_sphinx_html(source_dir, build_dir, rebuild=False):
    """Command to bulid Sphinx docs, modified from makefile & make.bat of sphinx project"""

    if not os.path.exists( os.path.join( source_dir, "conf.py" ) ):
        copy_sphinx_config(source_dir)

    if rebuild and os.path.exists( build_dir ):
        shutil.rmtree(build_dir)

    try:
        cmd = [
            "sphinx-build",
            '-M', "html",
            source_dir,
            build_dir
        ]
        
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Build sphinx html failed: {e}", file=sys.stderr)
        sys.exit(1)