from setuptools import setup, find_packages

setup(
    name="birth-time-rectifier",
    version="1.0.0",
    description="Astrological birth time rectification service",
    author="Birth Time Rectifier Team",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "httpx",
        "websockets",
        "pydantic",
        "python-multipart"
    ],
    python_requires=">=3.7",
)
