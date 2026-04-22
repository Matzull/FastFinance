"""FastFinance - Personal net-worth manager."""

def main():
	"""CLI entrypoint wrapper with lazy import."""
	from patrimonio.cli import main as cli_main

	return cli_main()

__version__ = "0.1.0"
