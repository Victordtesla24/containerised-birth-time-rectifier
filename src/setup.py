from setuptools import setup, find_packages

setup(
    name="birth-time-rectifier-ai",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "torch>=2.1.1",
        "transformers>=4.38.2",
        "numpy>=1.24.3",
        "pandas>=2.1.4",
        "redis>=5.0.1",
        "fastapi>=0.109.0",
        "uvicorn>=0.27.0",
        "python-dotenv>=1.0.0",
        "pydantic>=2.5.3",
        "prometheus-client>=0.20.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-cov>=4.1.0",
            "black>=23.12.1",
            "isort>=5.13.2",
            "mypy>=1.8.0",
            "ruff>=0.1.11",
        ]
    },
    python_requires=">=3.10",
) 