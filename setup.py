import shutil
import subprocess
import sys
from pathlib import Path

from setuptools import Distribution, setup
from setuptools.command.bdist_wheel import bdist_wheel as _bdist_wheel
from setuptools.command.build_py import build_py as _build_py

from _build_backend import bundle_library


class BinaryDistribution(Distribution):
    def has_ext_modules(self):
        return bundle_library()


class BuildPy(_build_py):
    def run(self):
        super().run()
        if not bundle_library():
            # A previous bundled build may have left a library in the build tree.
            bundled = Path(self.build_lib) / "ghostty" / "_lib"
            if bundled.exists():
                shutil.rmtree(bundled)


class BinaryWheel(_bdist_wheel):
    def get_tag(self):
        if not bundle_library():
            return super().get_tag()
        _, _, plat = super().get_tag()
        return "py3", "none", plat

    def run(self):
        if bundle_library():
            subprocess.run(
                [sys.executable, str(Path(__file__).with_name("build_lib.py"))],
                check=True,
            )
        super().run()


setup(
    cmdclass={"bdist_wheel": BinaryWheel, "build_py": BuildPy},
    distclass=BinaryDistribution,
    exclude_package_data={} if bundle_library() else {"ghostty": ["_lib/*"]},
)
