from setuptools import find_packages, setup
from typing import List

HYPEN_E_DOT = "-e ."


def get_requirements(file_path: str) -> List[str]:
    """
    Reads the requirements from a file and returns them as a list of strings.
    This function is designed to handle the case where the file contains a line '-e .',
    which is a common pattern in Python project requirements files to indicate
    that the project itself should be installed in editable mode. This line is removed
    from the list of requirements before returning.

    Parameters:
    file_path (str): The path to the file containing the requirements.

    Returns:
    List[str]: A list of strings, each representing a requirement.
    """
    requirements = []
    with open(file_path) as file_obj:
        requirements = file_obj.readlines()
        requirements = [req.replace("\n", "") for req in requirements]

        if HYPEN_E_DOT in requirements:
            requirements.remove(HYPEN_E_DOT)

    return requirements


setup(
    name="fin_Rag",
    version="0.0.1",
    author="Yuvraj Singh",
    author_email="ys2002github@gmail.com",
    packages=find_packages(),
    install_requires=get_requirements("requirements.txt"),
)
