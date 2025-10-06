from setuptools import setup, find_packages

setup(
    name="offer-agent",
    version="0.1.0",
    description="AI Offer Agent for IT Consulting",
    author="Aigentics Corp",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.12",
    install_requires=[
        line.strip()
        for line in open("requirements.txt")
        if line.strip() and not line.startswith("#")
    ],
)
