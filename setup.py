from setuptools import setup, find_packages

setup(
    name="superteam-vietnam",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "python-telegram-bot",
        "python-dotenv",
        "langchain",
        "chromadb",
    ],
)